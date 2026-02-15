"""Document extraction, OCR fallback, checklist detection, and query prediction."""

import json
import re
import shutil
from datetime import datetime
from io import BytesIO
from pathlib import Path

from app.models.schemas import ObligationRow, PendingFormItem, PredictedQuery, SalaryRow

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
PDF_TEXT_THRESHOLD = 40
OCR_MIN_CONFIDENCE = 0.55
MONTH_NAMES = ("jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec")
SALARY_TABLE_LABELS = ("salary slip", "salary summary", "salary statement")


def _load_json(filename: str) -> dict:
    with (DATA_DIR / filename).open("r", encoding="utf-8") as f:
        return json.load(f)


def _is_pan_match(text: str) -> bool:
    return bool(re.search(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b", text.upper()))


def classify_document_type(filename: str, extracted_text: str = "") -> str:
    lower = filename.lower()
    text_lower = extracted_text.lower()

    if (
        "pan" in lower
        or "permanent account number" in lower
        or "pan" in text_lower
        or "permanent account number" in text_lower
        or _is_pan_match(extracted_text)
    ):
        return "pan_card"

    if "bank" in lower or "statement" in lower:
        return "bank_statement"
    if "salary" in lower or "payslip" in lower:
        return "salary_slip"
    if "aadhaar" in lower or "aadhar" in lower or "id" in lower:
        return "id_proof"
    if "itr" in lower:
        return "itr"
    return "other"


def is_tesseract_available() -> bool:
    return shutil.which("tesseract") is not None


def _read_pdf_text(content: bytes) -> str:
    try:
        from pypdf import PdfReader  # type: ignore

        reader = PdfReader(BytesIO(content))
        return "\n".join((page.extract_text() or "") for page in reader.pages)
    except Exception:
        return ""


def _ocr_image_bytes(content: bytes) -> tuple[str, float]:
    try:
        import pytesseract  # type: ignore
        from PIL import Image  # type: ignore

        image = Image.open(BytesIO(content))
        data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
        words: list[str] = []
        conf_values: list[float] = []
        for idx, token in enumerate(data.get("text", [])):
            txt = (token or "").strip()
            conf_raw = str(data.get("conf", ["-1"])[idx])
            try:
                conf = float(conf_raw)
            except Exception:
                conf = -1
            if txt:
                words.append(txt)
            if conf >= 0:
                conf_values.append(conf / 100.0)
        if not words:
            return "", 0.0
        avg_conf = sum(conf_values) / len(conf_values) if conf_values else 0.0
        return " ".join(words), round(avg_conf, 2)
    except Exception:
        return "", 0.0


def _ocr_pdf_bytes(content: bytes) -> tuple[str, float]:
    """
    Render PDF pages to images and OCR them.
    Uses pypdfium2 so no external poppler dependency is required.
    """
    try:
        import pypdfium2 as pdfium  # type: ignore

        pdf = pdfium.PdfDocument(BytesIO(content))
        page_texts: list[str] = []
        conf_scores: list[float] = []
        for idx in range(len(pdf)):
            page = pdf.get_page(idx)
            bitmap = page.render(scale=2.0)
            pil_image = bitmap.to_pil()
            buf = BytesIO()
            pil_image.save(buf, format="PNG")
            txt, conf = _ocr_image_bytes(buf.getvalue())
            if txt.strip():
                page_texts.append(txt)
            conf_scores.append(conf)
            page.close()
        merged = "\n".join(page_texts)
        avg_conf = sum(conf_scores) / len(conf_scores) if conf_scores else 0.0
        return merged, round(avg_conf, 2)
    except Exception:
        return "", 0.0


def _read_text_from_document(filename: str, content: bytes) -> tuple[str, dict]:
    suffix = Path(filename).suffix.lower()
    ocr_used = False
    ocr_conf = 0.0

    if suffix == ".pdf":
        text = _read_pdf_text(content)
        # Scanned PDFs often have little/no embedded text.
        if len(text.strip()) >= PDF_TEXT_THRESHOLD:
            return text, {"ocr_used": False, "ocr_confidence": 1.0}
        ocr_used = True
        text, ocr_conf = _ocr_pdf_bytes(content)
        return text, {"ocr_used": ocr_used, "ocr_confidence": ocr_conf}

    if suffix in {".png", ".jpg", ".jpeg", ".tif", ".tiff"}:
        ocr_used = True
        text, ocr_conf = _ocr_image_bytes(content)
        return text, {"ocr_used": ocr_used, "ocr_confidence": ocr_conf}

    return "", {"ocr_used": False, "ocr_confidence": 0.0}


def _to_amount(raw: str) -> float:
    return float(raw.replace(",", "").strip())


def _find_amount_after_keywords(text: str, keywords: list[str]) -> float | None:
    for keyword in keywords:
        m = re.search(
            rf"(?is){re.escape(keyword)}.{{0,120}}?((?:₹|rs\.?|inr)\s*)?([0-9][0-9,]*(?:\.\d+)?)",
            text,
        )
        if m:
            return _to_amount(m.group(2))
    return None


def _find_credit_score(text: str) -> int | None:
    m = re.search(r"(?is)(?:credit|cibil)\s*score.{0,30}?([3-9][0-9]{2})", text)
    return int(m.group(1)) if m else None


def _extract_month_keys_from_named_months(text: str) -> set[str]:
    pattern = r"(?i)\b(" + "|".join(MONTH_NAMES) + r")[a-z]*[\s\-/,]*(20[0-9]{2})?\b"
    matches = re.findall(pattern, text)
    keys: set[str] = set()
    for month_name, year in matches:
        month_idx = MONTH_NAMES.index(month_name[:3].lower()) + 1
        yr = year if year else "0000"
        keys.add(f"{yr}-{month_idx:02d}")
    return keys


def _extract_month_keys_from_dates(text: str) -> set[str]:
    # Matches dates like 12/01/2026, 12-1-26, 2026/01/12
    dmy = re.findall(r"\b([0-3]?\d)[/\-]([0-1]?\d)[/\-]((?:20)?\d{2})\b", text)
    ymd = re.findall(r"\b((?:20)?\d{2})[/\-]([0-1]?\d)[/\-]([0-3]?\d)\b", text)
    keys: set[str] = set()
    for _, month, year in dmy:
        mm = int(month)
        if 1 <= mm <= 12:
            yy = int(year)
            yy = 2000 + yy if yy < 100 else yy
            keys.add(f"{yy:04d}-{mm:02d}")
    for year, month, _ in ymd:
        mm = int(month)
        if 1 <= mm <= 12:
            yy = int(year)
            yy = 2000 + yy if yy < 100 else yy
            keys.add(f"{yy:04d}-{mm:02d}")
    return keys


def _transaction_statement_months(text: str) -> set[str]:
    # Prefer transaction evidence: lines with date + amount patterns.
    tx_months: set[str] = set()
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    amount_like = re.compile(r"(?i)(?:₹|rs\.?|inr)?\s*[0-9][0-9,]*(?:\.\d{1,2})?")
    for line in lines:
        has_amount = bool(amount_like.search(line))
        if not has_amount:
            continue
        keys = _extract_month_keys_from_dates(line)
        if keys:
            tx_months.update(keys)
            continue
        keys = _extract_month_keys_from_named_months(line)
        if keys:
            tx_months.update(keys)
    return tx_months


def _summary_statement_months(text: str) -> set[str]:
    # Fallback: parse only labeled summary table section.
    m = re.search(r"(?is)bank\s*statement\s*summary(.{0,2500})", text)
    if not m:
        return set()
    section = m.group(1)
    keys = _extract_month_keys_from_dates(section)
    keys.update(_extract_month_keys_from_named_months(section))
    return keys


def _estimate_statement_months(text: str, bank_doc_count: int) -> int:
    tx_months = _transaction_statement_months(text)
    if tx_months:
        return max(1, min(12, len(tx_months)))

    summary_months = _summary_statement_months(text)
    if len(summary_months) >= 3:
        return max(1, min(12, len(summary_months)))

    return max(1, bank_doc_count)


def _build_salary_breakdown(salary: float, confidence: float) -> list[SalaryRow]:
    now = datetime.utcnow()
    rows: list[SalaryRow] = []
    for i in range(3, 0, -1):
        month = ((now.month - i - 1) % 12) + 1
        year = now.year if now.month > i else now.year - 1
        rows.append(
            SalaryRow(
                month=f"{year}-{month:02d}",
                employer="Extracted Employer",
                amount=round(salary, 2),
                confidence=confidence,
            )
        )
    return rows


def _month_to_num(month_text: str) -> int:
    short = month_text.strip()[:3].lower()
    return MONTH_NAMES.index(short) + 1 if short in MONTH_NAMES else 0


def _extract_salary_rows_from_labeled_tables(raw_text: str) -> list[SalaryRow]:
    """
    Parse salary rows from sections labeled Salary Slip / Summary / Statement.
    Expected row shape: Month, Employer, Amount (delimiter-separated or spaced).
    """
    lowered = raw_text.lower()
    if not any(label in lowered for label in SALARY_TABLE_LABELS):
        return []

    lines = [ln.strip() for ln in raw_text.splitlines() if ln.strip()]
    rows: list[SalaryRow] = []

    # Pattern for delimiter-based rows:
    # Jan 2026 | Acme Corp | INR 55,000
    delim_pattern = re.compile(
        r"(?i)\b("
        + "|".join(MONTH_NAMES)
        + r")[a-z]*\s*(20\d{2})?\s*[\|,;\t]\s*([^|,;\t]{2,80})\s*[\|,;\t]\s*((?:₹|rs\.?|inr)?\s*[0-9][0-9,]*(?:\.\d+)?)"
    )
    # Pattern for whitespace-based rows:
    # Jan 2026 Acme Corp INR 55,000
    space_pattern = re.compile(
        r"(?i)\b("
        + "|".join(MONTH_NAMES)
        + r")[a-z]*\s*(20\d{2})?\s+([A-Za-z][A-Za-z0-9&.,'()\- ]{2,80}?)\s+((?:₹|rs\.?|inr)?\s*[0-9][0-9,]*(?:\.\d+)?)\b"
    )

    for line in lines:
        match = delim_pattern.search(line) or space_pattern.search(line)
        if not match:
            continue
        month_txt = match.group(1)
        year_txt = match.group(2) or str(datetime.utcnow().year)
        employer = match.group(3).strip(" :-|")
        amount_txt = match.group(4)
        try:
            amount = _to_amount(re.sub(r"(?i)(₹|rs\.?|inr)", "", amount_txt).strip())
        except Exception:
            continue
        month_num = _month_to_num(month_txt)
        if month_num == 0:
            continue
        rows.append(
            SalaryRow(
                month=f"{int(year_txt):04d}-{month_num:02d}",
                employer=employer or "Extracted Employer",
                amount=round(amount, 2),
                confidence=0.92,
            )
        )

    # Dedupe by month+employer keeping last parsed entry.
    dedup: dict[tuple[str, str], SalaryRow] = {}
    for row in rows:
        dedup[(row.month, row.employer)] = row
    return list(dedup.values())


def extract_structured_data(documents: list[dict]) -> tuple[dict, list[SalaryRow], list[ObligationRow], dict]:
    filenames = [doc["filename"] for doc in documents]
    doc_types: list[str] = []

    all_text: list[str] = []
    ocr_flags: list[bool] = []
    ocr_conf_scores: list[float] = []
    for doc in documents:
        text, info = _read_text_from_document(doc["filename"], doc["content"])
        doc_types.append(classify_document_type(doc["filename"], text))
        if text.strip():
            all_text.append(text)
        ocr_flags.append(bool(info["ocr_used"]))
        ocr_conf_scores.append(float(info["ocr_confidence"]))

    merged_text_raw = "\n".join(all_text)
    merged_text = merged_text_raw.lower()

    salary_rows = _extract_salary_rows_from_labeled_tables(merged_text_raw)
    salary_source = "keyword"
    salary = None
    if salary_rows:
        # Multi-month handling:
        # 1) monthly_salary = average of detected months
        # 2) latest_monthly_salary is also preserved in extracted_data
        salary_rows.sort(key=lambda r: r.month)
        salary_values = [r.amount for r in salary_rows]
        salary = round(sum(salary_values) / len(salary_values), 2)
        salary_source = "structured_table"

    if salary is None:
        salary = _find_amount_after_keywords(
            merged_text,
            ["monthly salary", "net salary", "net pay", "salary credited", "take home", "gross salary", "income"],
        )
    emi = _find_amount_after_keywords(
        merged_text,
        ["emi", "monthly installment", "loan emi", "total emi", "obligation"],
    )
    outstanding = _find_amount_after_keywords(
        merged_text,
        ["outstanding", "principal outstanding", "loan outstanding", "total due"],
    )
    credit_score = _find_credit_score(merged_text)
    bank_statement_months = _estimate_statement_months(merged_text, doc_types.count("bank_statement"))

    salary = salary if salary is not None else 0.0
    emi = emi if emi is not None else 0.0
    outstanding = outstanding if outstanding is not None else 0.0
    credit_score = credit_score if credit_score is not None else 0
    emi_ratio = round((emi / salary) * 100, 2) if salary > 0 else 0.0

    ocr_used = any(ocr_flags)
    ocr_avg_conf = round(sum(ocr_conf_scores) / len(ocr_conf_scores), 2) if ocr_conf_scores else 0.0
    parsed_fields = sum(1 for v in (salary, emi, outstanding, credit_score) if v > 0)
    parse_conf = min(0.95, 0.5 + (0.1 * parsed_fields))
    text_conf = 0.92 if merged_text.strip() else 0.0
    base_conf = ocr_avg_conf if ocr_used else text_conf
    final_conf = round((base_conf + parse_conf) / 2, 2)

    if salary_rows:
        for idx, row in enumerate(salary_rows):
            salary_rows[idx] = SalaryRow(
                month=row.month,
                employer=row.employer,
                amount=row.amount,
                confidence=max(row.confidence, final_conf),
            )
        salary_breakdown = salary_rows
    else:
        salary_breakdown = _build_salary_breakdown(salary, final_conf) if salary > 0 else []

    latest_monthly_salary = 0.0
    average_monthly_salary = 0.0
    if salary_breakdown:
        ordered = sorted(salary_breakdown, key=lambda r: r.month)
        latest_monthly_salary = round(ordered[-1].amount, 2)
        average_monthly_salary = round(sum(r.amount for r in ordered) / len(ordered), 2)
    obligations = (
        [
            ObligationRow(
                lender="Extracted Lender",
                obligation_type="Loan EMI",
                monthly_amount=round(emi, 2),
                outstanding_amount=round(outstanding, 2),
            )
        ]
        if emi > 0 or outstanding > 0
        else []
    )

    extracted = {
        "monthly_salary": round(salary, 2),
        "latest_monthly_salary": latest_monthly_salary,
        "average_monthly_salary": average_monthly_salary,
        "monthly_obligations": round(emi, 2),
        "annual_income": round(salary * 12, 2),
        "emi_ratio_percent": emi_ratio,
        "credit_score": int(credit_score),
        "bank_statement_months": int(bank_statement_months),
        "documents_uploaded": filenames,
        "document_types_detected": doc_types,
        "ocr_average_confidence": final_conf,
        "name_match_score": 0.9,
        "salary_extraction_source": salary_source,
    }
    processing = {
        "ocr_used": ocr_used,
        "ocr_confidence": ocr_avg_conf,
        "text_length": len(merged_text.strip()),
        "low_quality": ocr_used and (ocr_avg_conf < OCR_MIN_CONFIDENCE),
    }
    return extracted, salary_breakdown, obligations, processing


def detect_missing_documents(doc_types: list[str]) -> list[str]:
    checklist = _load_json("document_checklist.json")
    required = checklist.get("required_documents", [])
    return [doc for doc in required if doc not in doc_types]


def detect_pending_forms(extracted_data: dict, missing_documents: list[str]) -> list[PendingFormItem]:
    forms = _load_json("pending_forms.json").get("forms", [])
    pending: list[PendingFormItem] = []
    for form in forms:
        rule = form.get("trigger_rule", "")
        if rule == "if_missing_income_proof" and any(
            d in missing_documents for d in ("salary_slip", "itr", "bank_statement")
        ):
            pending.append(
                PendingFormItem(
                    form_code=form["code"],
                    form_name=form["name"],
                    reason="Income proof documents are incomplete",
                )
            )
        elif rule == "if_credit_score_below_700" and extracted_data.get("credit_score", 0) < 700:
            pending.append(
                PendingFormItem(
                    form_code=form["code"],
                    form_name=form["name"],
                    reason="Credit score below preferred threshold",
                )
            )
        elif rule == "if_name_match_below_0_9" and extracted_data.get("name_match_score", 1) < 0.9:
            pending.append(
                PendingFormItem(
                    form_code=form["code"],
                    form_name=form["name"],
                    reason="Name mismatch risk in submitted documents",
                )
            )
    return pending


def predict_credit_queries(
    extracted_data: dict,
    missing_documents: list[str],
    pending_forms: list[PendingFormItem],
) -> list[PredictedQuery]:
    rows = _load_json("historical_queries.json").get("queries", [])
    tokens = set(re.findall(r"[a-z_]+", " ".join(missing_documents).lower()))
    tokens.update(re.findall(r"[a-z_]+", " ".join(f.form_code for f in pending_forms).lower()))
    if extracted_data.get("emi_ratio_percent", 0) > 40:
        tokens.add("high_emi")
    if extracted_data.get("credit_score", 0) < 700:
        tokens.add("low_credit")

    scored: list[tuple[float, dict]] = []
    for row in rows:
        tag_set = set(row.get("tags", []))
        overlap = len(tokens.intersection(tag_set))
        score = min(0.99, row.get("base_confidence", 0.5) + (0.08 * overlap))
        if overlap > 0:
            scored.append((score, row))

    scored.sort(key=lambda item: item[0], reverse=True)
    top = scored[:3] if scored else [(0.62, rows[0])] if rows else []
    return [
        PredictedQuery(
            query=item[1]["query"],
            confidence=round(item[0], 2),
            rationale=f"Matched tags: {', '.join(item[1].get('tags', []))}",
        )
        for item in top
    ]


def build_confidence_summary(extracted_data: dict, missing_documents: list[str]) -> dict:
    ocr_conf = float(extracted_data.get("ocr_average_confidence", 0.8))
    name_score = float(extracted_data.get("name_match_score", 0.85))
    penalty = min(0.2, 0.04 * len(missing_documents))
    overall = max(0.0, min(1.0, ((ocr_conf + name_score) / 2) - penalty))
    return {
        "ocr_average_confidence": round(ocr_conf, 2),
        "name_match_score": round(name_score, 2),
        "missing_document_penalty": round(penalty, 2),
        "overall_confidence": round(overall, 2),
    }

import { useEffect, useMemo, useState } from 'react'
import { api } from './api/client'
import './App.css'

const allowedTypes = ['pdf', 'png', 'jpg', 'jpeg', 'tiff', 'tif']
const moneyFmt = new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 })

function App() {
  const [backendOk, setBackendOk] = useState(null)
  const [files, setFiles] = useState([])
  const [userId, setUserId] = useState('')
  const [category, setCategory] = useState('personal_loan')
  const [uploadResult, setUploadResult] = useState(null)
  const [reportDetail, setReportDetail] = useState(null)
  const [loading, setLoading] = useState(false)
  const [processingMessage, setProcessingMessage] = useState('')
  const [error, setError] = useState(null)
  const [dragOver, setDragOver] = useState(false)

  useEffect(() => {
    api
      .testConnection()
      .then(() => setBackendOk(true))
      .catch(() => setBackendOk(false))
  }, [])

  const fileNames = useMemo(() => files.map((f) => f.name), [files])
  const extracted = reportDetail?.extracted_data || {}
  const summaryItems = useMemo(() => {
    if (!reportDetail) return []
    return [
      { label: 'Monthly Salary', value: moneyFmt.format(Number(extracted.monthly_salary || 0)) },
      { label: 'Monthly EMI', value: moneyFmt.format(Number(extracted.monthly_obligations || 0)) },
      { label: 'Credit Score', value: String(extracted.credit_score || 0) },
      { label: 'EMI Ratio', value: `${Number(extracted.emi_ratio_percent || 0)}%` },
    ]
  }, [reportDetail, extracted])

  const addFiles = (incoming) => {
    const incomingList = Array.from(incoming || [])
    const filtered = incomingList.filter((file) => {
      const ext = file.name.split('.').pop()?.toLowerCase() || ''
      return allowedTypes.includes(ext)
    })
    const dedup = new Map()
    ;[...files, ...filtered].forEach((file) => dedup.set(file.name, file))
    setFiles(Array.from(dedup.values()))
  }

  const removeFile = (name) => {
    setFiles((prev) => prev.filter((f) => f.name !== name))
  }

  const handleDrop = (e) => {
    e.preventDefault()
    setDragOver(false)
    addFiles(e.dataTransfer.files)
  }

  const handleUpload = async () => {
    if (!files.length) {
      setError('Upload at least one KYC/Income document')
      return
    }
    setLoading(true)
    setError(null)
    const hasPdf = files.some((f) => f.name.toLowerCase().endsWith('.pdf'))
    setProcessingMessage(
      hasPdf
        ? 'Scanned document detected. Running OCR to extract text. This may take a few seconds.'
        : 'Processing uploaded documents...'
    )
    setUploadResult(null)
    setReportDetail(null)
    try {
      const result = await api.uploadReport(files, {
        user_id: userId || undefined,
        category: category || undefined,
      })
      setUploadResult(result)
      const detail = await api.getReport(result.report_id)
      setReportDetail(detail)
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Processing failed')
    } finally {
      setLoading(false)
      setProcessingMessage('')
    }
  }

  const reset = () => {
    setFiles([])
    setUploadResult(null)
    setReportDetail(null)
    setError(null)
    setProcessingMessage('')
  }

  return (
    <div className="app" role="main">
      <header className="hero">
        <div className="hero-text">
          <h1>In-House AI Document Processing Platform</h1>
          <p>
            Drag-and-drop KYC and income documents, then generate a consolidated eligibility report PDF in one click.
          </p>
          <p className={`backend-status ${backendOk ? 'ok' : 'fail'}`}>
            Backend: {backendOk === null ? 'Checking...' : backendOk ? 'Connected' : 'Unreachable'}
          </p>
        </div>
      </header>

      <div className="layout">
        <div className="primary-column">
          <section className="card">
            <div className="section-head">
              <h2>Secure Upload Layer</h2>
              <span className="pill">PDF, JPG, PNG, TIFF</span>
            </div>
            <p className="muted">Drag and drop KYC and income documents. Files are validated and fingerprinted for traceability.</p>

            <div
              className={`dropzone ${dragOver ? 'drag-over' : ''} ${files.length ? 'has-files' : ''}`}
              onDrop={handleDrop}
              onDragOver={(e) => {
                e.preventDefault()
                setDragOver(true)
              }}
              onDragLeave={() => setDragOver(false)}
              onClick={() => document.getElementById('file-input')?.click()}
            >
              <input
                id="file-input"
                type="file"
                multiple
                accept=".pdf,.png,.jpg,.jpeg,.tif,.tiff"
                onChange={(e) => addFiles(e.target.files)}
                style={{ display: 'none' }}
              />
              {files.length ? <span>{files.length} document(s) attached</span> : <span>Drop documents here or click to browse</span>}
            </div>

            {!!files.length && (
              <div className="chip-list">
                {fileNames.map((name) => (
                  <span key={name} className="chip">
                    {name}
                    <button className="chip-remove" type="button" onClick={() => removeFile(name)}>
                      x
                    </button>
                  </span>
                ))}
              </div>
            )}

            <div className="form-row">
              <label>
                <span>User ID</span>
                <input value={userId} onChange={(e) => setUserId(e.target.value)} placeholder="emp_1001" />
              </label>
              <label>
                <span>Category</span>
                <input value={category} onChange={(e) => setCategory(e.target.value)} placeholder="personal_loan" />
              </label>
            </div>

            {error && <p className="error">{error}</p>}
            {loading && (
              <div className="ocr-progress">
                <p className="ocr-message">{processingMessage}</p>
                <div className="progress-track">
                  <div className="progress-bar" />
                </div>
              </div>
            )}
            <div className="actions">
              <button className="btn btn-primary" onClick={handleUpload} disabled={loading || !files.length}>
                {loading ? 'Processing...' : 'Generate Consolidated Report'}
              </button>
              <button className="btn btn-ghost" onClick={reset}>
                Clear
              </button>
            </div>
          </section>

          {uploadResult && reportDetail && (
            <section className="card">
              <div className="section-head">
                <h2>Consolidated Eligibility Output</h2>
                <div className={`eligibility-badge ${reportDetail.eligibility ? 'eligible' : 'ineligible'}`}>
                  {reportDetail.eligibility ? 'Eligible' : 'Not Eligible'}
                </div>
              </div>
              <p className="muted report-id">Report ID: {uploadResult.report_id}</p>

              <div className="summary-grid">
                {summaryItems.map((item) => (
                  <article key={item.label} className="summary-card">
                    <p>{item.label}</p>
                    <h4>{item.value}</h4>
                  </article>
                ))}
              </div>

              <h3>Eligibility Check Result</h3>
              <ul className="flat-list">
                {reportDetail.decisions.map((decision) => (
                  <li key={decision.rule_id}>
                    {decision.passed ? 'PASS' : 'FAIL'} - {decision.rule_name} ({decision.message})
                  </li>
                ))}
              </ul>

              <h3>Monthly Salary Breakdown Table</h3>
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Month</th>
                      <th>Employer</th>
                      <th>Amount</th>
                      <th>Confidence</th>
                    </tr>
                  </thead>
                  <tbody>
                    {reportDetail.salary_breakdown.map((row, idx) => (
                      <tr key={idx}>
                        <td>{row.month}</td>
                        <td>{row.employer}</td>
                        <td>{moneyFmt.format(Number(row.amount || 0))}</td>
                        <td>{Math.round(Number(row.confidence || 0) * 100)}%</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <h3>Current Obligations Table</h3>
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Lender</th>
                      <th>Type</th>
                      <th>Monthly</th>
                      <th>Outstanding</th>
                    </tr>
                  </thead>
                  <tbody>
                    {reportDetail.obligations.map((row, idx) => (
                      <tr key={idx}>
                        <td>{row.lender}</td>
                        <td>{row.obligation_type}</td>
                        <td>{moneyFmt.format(Number(row.monthly_amount || 0))}</td>
                        <td>{moneyFmt.format(Number(row.outstanding_amount || 0))}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <h3>Pending Documents List</h3>
              <ul className="flat-list">
                {reportDetail.missing_documents.length ? (
                  reportDetail.missing_documents.map((doc) => <li key={doc}>{doc}</li>)
                ) : (
                  <li>No pending documents</li>
                )}
              </ul>

              <h3>Pending Form Details</h3>
              <ul className="flat-list">
                {reportDetail.pending_forms.length ? (
                  reportDetail.pending_forms.map((form) => (
                    <li key={form.form_code}>
                      {form.form_code} - {form.form_name} ({form.reason})
                    </li>
                  ))
                ) : (
                  <li>No pending forms</li>
                )}
              </ul>

              <h3>Probable Credit-Team Queries</h3>
              <ul className="flat-list">
                {reportDetail.predicted_queries.length ? (
                  reportDetail.predicted_queries.map((q, idx) => (
                    <li key={idx}>
                      {q.query} (confidence: {q.confidence})
                    </li>
                  ))
                ) : (
                  <li>No queries predicted</li>
                )}
              </ul>

              <div className="actions">
                <a href={api.getReportPdfUrl(uploadResult.report_id)} className="btn btn-secondary">
                  Download Standardized PDF
                </a>
              </div>
            </section>
          )}
        </div>

        <aside className="secondary-column">
          <section className="card grid-card sticky-card">
            <h2>Enterprise Blueprint</h2>
            <div className="grid">
              <article>
                <h3>Recommended Architecture</h3>
                <p>Upload API gateway, OCR/document understanding workers, externalized rule engine, intelligence layer, and PDF service.</p>
              </article>
              <article>
                <h3>Suggested Stack</h3>
                <p>Frontend: React/Vite. Backend: FastAPI. OCR: Tesseract + LayoutLM/Donut. Store: PostgreSQL + object storage. Queue: Redis/Celery.</p>
              </article>
              <article>
                <h3>Data Privacy Strategy</h3>
                <p>Private VPC, encryption at rest/in transit, internal IAM/RBAC, no outbound data egress, private model hosting.</p>
              </article>
              <article>
                <h3>Step-by-Step Workflow</h3>
                <p>Ingest -&gt; Validate -&gt; OCR/parse -&gt; Rules -&gt; Missing docs/forms -&gt; Query prediction -&gt; Standardized PDF generation.</p>
              </article>
              <article>
                <h3>Timeline</h3>
                <p>Prototype: 3-5 weeks. Production hardening: 8-14 additional weeks including audit, monitoring, and performance testing.</p>
              </article>
              <article>
                <h3>Scalability & Accuracy Controls</h3>
                <p>Autoscaled workers, async queues, confidence thresholds, human-review fallback, and failure-safe retries with dead-letter queue.</p>
              </article>
            </div>
          </section>
        </aside>
      </div>
    </div>
  )
}

export default App

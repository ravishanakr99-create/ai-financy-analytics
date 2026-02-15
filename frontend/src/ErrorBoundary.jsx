import { Component } from 'react'

export class ErrorBoundary extends Component {
  state = { error: null }

  static getDerivedStateFromError(error) {
    return { error }
  }

  render() {
    if (this.state.error) {
      return (
        <div style={{
          padding: '2rem',
          fontFamily: 'system-ui, sans-serif',
          background: '#1e293b',
          color: '#f87171',
          minHeight: '100vh',
        }}>
          <h1>Something went wrong</h1>
          <pre style={{ background: '#0f172a', padding: '1rem', overflow: 'auto' }}>
            {this.state.error?.message || String(this.state.error)}
          </pre>
          <p style={{ color: '#94a3b8' }}>Check the browser console for details.</p>
        </div>
      )
    }
    return this.props.children
  }
}

import { useState } from 'react'

const styles = {
  wrapper: {
    display: 'flex',
    flexDirection: 'column',
    gap: '12px',
    width: '100%',
    maxWidth: '640px',
  },
  label: {
    fontSize: '14px',
    fontWeight: '600',
    color: '#374151',
  },
  inputRow: {
    display: 'flex',
    gap: '10px',
  },
  input: {
    flex: 1,
    padding: '10px 14px',
    fontSize: '14px',
    border: '1px solid #d1d5db',
    borderRadius: '8px',
    outline: 'none',
    fontFamily: 'inherit',
  },
  button: {
    padding: '10px 22px',
    fontSize: '14px',
    fontWeight: '600',
    color: '#fff',
    background: '#4f46e5',
    border: 'none',
    borderRadius: '8px',
    cursor: 'pointer',
    whiteSpace: 'nowrap',
  },
  buttonDisabled: {
    background: '#a5b4fc',
    cursor: 'not-allowed',
  },
  hint: {
    fontSize: '12px',
    color: '#6b7280',
  },
  error: {
    fontSize: '13px',
    color: '#dc2626',
    background: '#fef2f2',
    padding: '8px 12px',
    borderRadius: '6px',
    border: '1px solid #fecaca',
  },
}

export default function UploadDocument({ onResult, loading, setLoading }) {
  const [url, setUrl] = useState('')
  const [error, setError] = useState('')

  async function handleAnalyze() {
    const trimmed = url.trim()
    if (!trimmed) return
    setError('')
    setLoading(true)
    try {
      const { analyzeRepo } = await import('../../services/analyzerApi.js')
      const result = await analyzeRepo(trimmed)
      onResult(result)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  function handleKeyDown(e) {
    if (e.key === 'Enter') handleAnalyze()
  }

  const isDisabled = loading || !url.trim()

  return (
    <div style={styles.wrapper}>
      <label style={styles.label}>GitHub Repository URL</label>
      <div style={styles.inputRow}>
        <input
          style={styles.input}
          type="url"
          placeholder="https://github.com/owner/repo"
          value={url}
          onChange={e => setUrl(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={loading}
        />
        <button
          style={{ ...styles.button, ...(isDisabled ? styles.buttonDisabled : {}) }}
          onClick={handleAnalyze}
          disabled={isDisabled}
        >
          {loading ? 'Analyzing…' : 'Analyze'}
        </button>
      </div>
      <p style={styles.hint}>Paste any public GitHub repo URL. We'll scan the code and explain it.</p>
      {error && <p style={styles.error}>{error}</p>}
    </div>
  )
}

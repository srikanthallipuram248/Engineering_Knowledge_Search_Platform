import { useState } from 'react'
import UploadDocument from '../components/Documents/UploadDocument'

const s = {
  page: {
    minHeight: '100vh',
    background: '#f9fafb',
    fontFamily: "'Inter', system-ui, sans-serif",
    padding: '40px 24px',
  },
  hero: {
    maxWidth: '860px',
    margin: '0 auto 40px',
    textAlign: 'center',
  },
  heroTitle: {
    fontSize: '32px',
    fontWeight: '700',
    color: '#111827',
    margin: '0 0 12px',
  },
  heroSub: {
    fontSize: '16px',
    color: '#6b7280',
    margin: '0 0 32px',
  },
  inputCenter: {
    display: 'flex',
    justifyContent: 'center',
  },
  card: {
    maxWidth: '980px',
    margin: '0 auto',
    background: '#fff',
    border: '1px solid #e5e7eb',
    borderRadius: '8px',
    padding: '32px',
    boxShadow: '0 1px 4px rgba(0,0,0,0.06)',
  },
  cardTitle: {
    fontSize: '24px',
    fontWeight: '700',
    color: '#111827',
    margin: '0 0 6px',
  },
  readmeBadge: (found) => ({
    display: 'inline-block',
    fontSize: '11px',
    fontWeight: '600',
    padding: '2px 8px',
    borderRadius: '999px',
    marginBottom: '24px',
    background: found ? '#d1fae5' : '#fef3c7',
    color: found ? '#065f46' : '#92400e',
  }),
  section: {
    marginBottom: '28px',
  },
  sectionTitle: {
    fontSize: '13px',
    fontWeight: '700',
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
    color: '#6b7280',
    marginBottom: '10px',
  },
  paragraph: {
    fontSize: '15px',
    color: '#374151',
    lineHeight: '1.65',
    margin: 0,
    whiteSpace: 'pre-line',
  },
  tagList: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: '8px',
  },
  tag: {
    fontSize: '12px',
    fontWeight: '600',
    padding: '4px 10px',
    borderRadius: '999px',
    background: '#ede9fe',
    color: '#4c1d95',
  },
  table: {
    width: '100%',
    borderCollapse: 'collapse',
    fontSize: '14px',
  },
  th: {
    textAlign: 'left',
    padding: '8px 12px',
    background: '#f3f4f6',
    color: '#374151',
    fontWeight: '600',
    fontSize: '12px',
    borderBottom: '1px solid #e5e7eb',
  },
  td: {
    padding: '10px 12px',
    borderBottom: '1px solid #f3f4f6',
    color: '#374151',
    verticalAlign: 'top',
    lineHeight: '1.55',
  },
  tdName: {
    padding: '10px 12px',
    borderBottom: '1px solid #f3f4f6',
    color: '#4f46e5',
    fontFamily: 'monospace',
    fontWeight: '600',
    verticalAlign: 'top',
    width: '220px',
  },
  featureList: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))',
    gap: '12px',
  },
  featureItem: {
    border: '1px solid #e5e7eb',
    borderRadius: '8px',
    padding: '14px',
    background: '#ffffff',
  },
  featureTitle: {
    fontSize: '14px',
    fontWeight: '700',
    color: '#111827',
    margin: '0 0 6px',
  },
  featureText: {
    fontSize: '14px',
    color: '#374151',
    lineHeight: '1.55',
    margin: '0 0 8px',
  },
  evidence: {
    fontSize: '12px',
    color: '#6b7280',
    lineHeight: '1.45',
    margin: 0,
  },
  list: {
    margin: 0,
    paddingLeft: '20px',
    color: '#374151',
    fontSize: '14px',
    lineHeight: '1.65',
  },
  commandList: {
    listStyle: 'none',
    margin: 0,
    padding: 0,
    display: 'flex',
    flexDirection: 'column',
    gap: '8px',
  },
  command: {
    fontFamily: 'monospace',
    fontSize: '13px',
    color: '#1e40af',
    background: '#eff6ff',
    padding: '4px 8px',
    borderRadius: '6px',
    display: 'inline-block',
    marginRight: '8px',
  },
  commandPurpose: {
    fontSize: '14px',
    color: '#374151',
  },
  spinner: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: '16px',
    padding: '60px 0',
    color: '#6b7280',
    fontSize: '15px',
  },
  spinnerDot: {
    width: '36px',
    height: '36px',
    border: '3px solid #e5e7eb',
    borderTopColor: '#4f46e5',
    borderRadius: '50%',
    animation: 'spin 0.8s linear infinite',
  },
}

function ListSection({ title, items }) {
  if (!items?.length) return null
  return (
    <div style={s.section}>
      <p style={s.sectionTitle}>{title}</p>
      <ul style={s.list}>
        {items.map((item, i) => <li key={i}>{item}</li>)}
      </ul>
    </div>
  )
}

export default function Home() {
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)

  function handleResult(data) {
    setResult(data)
  }

  return (
    <div style={s.page}>
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>

      <div style={s.hero}>
        <h1 style={s.heroTitle}>Engineering Knowledge Search</h1>
        <p style={s.heroSub}>
          Paste a public GitHub repo URL and get a detailed architecture overview.
        </p>
        <div style={s.inputCenter}>
          <UploadDocument
            onResult={handleResult}
            loading={loading}
            setLoading={setLoading}
          />
        </div>
      </div>

      {loading && (
        <div style={s.spinner}>
          <div style={s.spinnerDot} />
          <span>Cloning repo and analyzing with AI...</span>
        </div>
      )}

      {!loading && result && (
        <div style={s.card}>
          <h2 style={s.cardTitle}>{result.repo_name}</h2>
          <div style={s.readmeBadge(result.readme_found)}>
            {result.readme_found ? 'README found' : 'No README - inferred from structure'}
          </div>

          <div style={s.section}>
            <p style={s.sectionTitle}>Summary</p>
            <p style={s.paragraph}>{result.summary}</p>
          </div>

          {result.detailed_overview && (
            <div style={s.section}>
              <p style={s.sectionTitle}>Detailed Overview</p>
              <p style={s.paragraph}>{result.detailed_overview}</p>
            </div>
          )}

          <div style={s.section}>
            <p style={s.sectionTitle}>Architecture</p>
            <p style={s.paragraph}>{result.architecture}</p>
          </div>

          <div style={s.section}>
            <p style={s.sectionTitle}>Tech Stack</p>
            <div style={s.tagList}>
              {(result.tech_stack ?? []).map(tech => (
                <span key={tech} style={s.tag}>{tech}</span>
              ))}
            </div>
          </div>

          {result.core_features?.length > 0 && (
            <div style={s.section}>
              <p style={s.sectionTitle}>Core Features</p>
              <div style={s.featureList}>
                {result.core_features.map((feature, i) => (
                  <div key={i} style={s.featureItem}>
                    <h3 style={s.featureTitle}>{feature.name}</h3>
                    <p style={s.featureText}>{feature.description}</p>
                    <p style={s.evidence}>Evidence: {feature.evidence}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {result.key_modules?.length > 0 && (
            <div style={s.section}>
              <p style={s.sectionTitle}>Key Modules</p>
              <table style={s.table}>
                <thead>
                  <tr>
                    <th style={s.th}>Module</th>
                    <th style={s.th}>Responsibility</th>
                  </tr>
                </thead>
                <tbody>
                  {result.key_modules.map((m, i) => (
                    <tr key={i}>
                      <td style={s.tdName}>{m.name}</td>
                      <td style={s.td}>{m.role}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          <ListSection title="Data Flow" items={result.data_flow} />
          <ListSection title="Setup Steps" items={result.setup_steps} />
          <ListSection title="Design Decisions" items={result.notable_design_decisions} />

          {result.commands?.length > 0 && (
            <div style={s.section}>
              <p style={s.sectionTitle}>Important Commands</p>
              <ul style={s.commandList}>
                {result.commands.map((cmd, i) => (
                  <li key={i}>
                    <span style={s.command}>{cmd.command}</span>
                    <span style={s.commandPurpose}>{cmd.purpose}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {result.testing && (
            <div style={s.section}>
              <p style={s.sectionTitle}>Testing</p>
              <p style={s.paragraph}>{result.testing}</p>
            </div>
          )}

          <ListSection title="Limitations" items={result.limitations} />
          <ListSection title="Entry Points" items={result.entry_points} />
        </div>
      )}
    </div>
  )
}

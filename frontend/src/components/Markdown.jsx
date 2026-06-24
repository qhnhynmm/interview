import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

const components = {
  h1: ({ children }) => (
    <div style={{ fontSize: 15, fontWeight: 700, color: 'var(--color-text)', margin: '0 0 8px' }}>
      {children}
    </div>
  ),
  h2: ({ children }) => (
    <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--color-text)', margin: '14px 0 6px' }}>
      {children}
    </div>
  ),
  h3: ({ children }) => (
    <div style={{
      fontSize: 11,
      fontWeight: 700,
      color: 'var(--color-accent)',
      margin: '14px 0 5px',
      textTransform: 'uppercase',
      letterSpacing: '0.07em',
    }}>
      {children}
    </div>
  ),
  p: ({ children }) => (
    <p style={{ margin: '0 0 8px', color: 'var(--color-text)', lineHeight: 1.65 }}>
      {children}
    </p>
  ),
  ul: ({ children }) => (
    <ul style={{ margin: '0 0 8px', paddingLeft: 18, listStyle: 'disc' }}>
      {children}
    </ul>
  ),
  ol: ({ children }) => (
    <ol style={{ margin: '0 0 8px', paddingLeft: 18 }}>
      {children}
    </ol>
  ),
  li: ({ children }) => (
    <li style={{ margin: '3px 0', color: 'var(--color-text)', lineHeight: 1.6 }}>
      {children}
    </li>
  ),
  strong: ({ children }) => (
    <strong style={{ fontWeight: 700, color: 'var(--color-text)' }}>{children}</strong>
  ),
  em: ({ children }) => (
    <em style={{ fontStyle: 'italic', color: 'var(--color-text)' }}>{children}</em>
  ),
  code: ({ children, className }) => {
    if (className) {
      return (
        <pre style={{
          background: '#0d1117',
          padding: '8px 10px',
          borderRadius: 4,
          overflowX: 'auto',
          fontSize: 11,
          margin: '6px 0',
        }}>
          <code style={{ color: '#e6edf3', fontFamily: "'JetBrains Mono', monospace" }}>
            {children}
          </code>
        </pre>
      )
    }
    return (
      <code style={{
        background: 'rgba(255,255,255,0.08)',
        padding: '1px 5px',
        borderRadius: 3,
        fontSize: 12,
        fontFamily: "'JetBrains Mono', monospace",
        color: 'var(--color-text)',
      }}>
        {children}
      </code>
    )
  },
  blockquote: ({ children }) => (
    <blockquote style={{
      borderLeft: '3px solid var(--color-border)',
      paddingLeft: 10,
      margin: '8px 0',
      color: 'var(--color-muted)',
    }}>
      {children}
    </blockquote>
  ),
  a: ({ href, children }) => (
    <a href={href} target="_blank" rel="noopener noreferrer"
      style={{ color: 'var(--color-accent)', textDecoration: 'underline' }}>
      {children}
    </a>
  ),
  hr: () => (
    <hr style={{ border: 'none', borderTop: '1px solid var(--color-border)', margin: '10px 0' }} />
  ),
}

export default function Markdown({ children, style }) {
  return (
    <div style={{ fontSize: 13, lineHeight: 1.65, color: 'var(--color-text)', ...style }}>
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>
        {children ?? ''}
      </ReactMarkdown>
    </div>
  )
}

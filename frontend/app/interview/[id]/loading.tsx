export default function LoadingInterview() {
  return (
    <div style={{
      height: '100vh',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      background: '#090407',
      color: '#9a7b82',
      fontSize: 15,
    }}>
      <div style={{ marginBottom: 16, fontSize: 13, letterSpacing: '1px' }}>PREPARING INTERVIEW</div>
      <div style={{ fontSize: 18, color: '#f4728b' }}>Loading Aurelia session…</div>
    </div>
  )
}

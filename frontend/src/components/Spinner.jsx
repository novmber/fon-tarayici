export default function Spinner({ label = 'Yükleniyor...' }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 14, padding: 48 }}>
      <div style={{
        width: 48, height: 48,
        border: '3px solid #1e293b',
        borderTopColor: '#00C2A8',
        borderRadius: '50%',
        animation: 'spin 0.8s linear infinite'
      }} />
      <span style={{ color: '#64748b', fontSize: 13 }}>{label}</span>
      <style>{`@keyframes spin { to { transform: rotate(360deg) } }`}</style>
    </div>
  )
}

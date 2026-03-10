import { useState } from 'react'

export default function UploadZone({ onFiles, compact, onClick }) {
  const [dragOver, setDragOver] = useState(false)

  const handleDrop = (e) => {
    e.preventDefault()
    setDragOver(false)
    onFiles(e.dataTransfer.files)
  }

  if (compact) {
    return (
      <div
        onDrop={handleDrop}
        onDragOver={e => { e.preventDefault(); setDragOver(true) }}
        onDragLeave={() => setDragOver(false)}
        onClick={onClick}
        style={{
          border: `1px dashed ${dragOver ? '#00C2A8' : '#1e293b'}`,
          borderRadius: 12,
          padding: '12px 20px',
          marginBottom: 24,
          display: 'flex',
          alignItems: 'center',
          gap: 12,
          cursor: 'pointer',
          background: dragOver ? 'rgba(0,194,168,0.04)' : 'transparent',
          transition: 'all 0.2s',
        }}
      >
        <span style={{ fontSize: 20 }}>📄</span>
        <div>
          <div style={{ color: '#64748b', fontSize: 13 }}>Yeni PDF ekle</div>
          <div style={{ color: '#334155', fontSize: 11 }}>Yeni fon veya mevcut fona yeni dönem — birden fazla PDF desteklenir</div>
        </div>
      </div>
    )
  }

  return (
    <div
      onDrop={handleDrop}
      onDragOver={e => { e.preventDefault(); setDragOver(true) }}
      onDragLeave={() => setDragOver(false)}
      onClick={onClick}
      style={{
        border: `2px dashed ${dragOver ? '#00C2A8' : '#1e293b'}`,
        borderRadius: 18,
        padding: '72px 32px',
        marginBottom: 28,
        textAlign: 'center',
        cursor: 'pointer',
        background: dragOver ? 'rgba(0,194,168,0.04)' : '#0f172a',
        transition: 'all 0.2s',
      }}
    >
      <div style={{ fontSize: 52, marginBottom: 12 }}>📄</div>
      <h2 style={{ color: '#334155', fontSize: 18, margin: '0 0 8px', fontFamily: 'Space Grotesk' }}>
        KAP Fon PDF'lerini Buraya Yükleyin
      </h2>
      <p style={{ color: '#475569', fontSize: 13, margin: 0 }}>
        Birden fazla fonun PDF'ini aynı anda sürükleyebilirsiniz
      </p>
      <p style={{ color: '#334155', fontSize: 12, marginTop: 8 }}>
        Her PDF otomatik analiz edilir → fon kartı oluşturulur → SQLite'a kaydedilir
      </p>
    </div>
  )
}

import { useState, useEffect } from 'react'
import { learnManualPrice } from '../api.js'

export default function ManualPrice({ fundCode, fundName, pdfPrice, pdfMonth, onSave }) {
  const [price, setPrice] = useState('')
  const [evolverMsg, setEvolverMsg] = useState(null)
  const [tweetCopied, setTweetCopied] = useState(false)

  const storageKey = `manual_price_${fundCode}`

  const [current, setCurrent] = useState(() => {
    try { return JSON.parse(localStorage.getItem(storageKey)) } catch { return null }
  })

  // Sayfa açılınca localStorage'da fiyat varsa Evolver'a bildir (sessiz)
  useEffect(() => {
    if (!current) return
    const chg = (((current.price - pdfPrice) / pdfPrice) * 100).toFixed(2)
    learnManualPrice(fundCode, {
      pdfPrice,
      currentPrice: current.price,
      changePct: parseFloat(chg),
      pdfMonth,
      date: current.date,
    }).then(res => {
      if (res?.insight) setEvolverMsg(res.insight)
    }).catch(() => {})
  }, []) // sadece mount'ta bir kez

  const changePct = current
    ? (((current.price - pdfPrice) / pdfPrice) * 100).toFixed(2)
    : null
  const changeColor = changePct == null ? '#64748b' : Number(changePct) >= 0 ? '#00C2A8' : '#EF476F'

  const handleSave = async () => {
    const p = parseFloat(price.replace(',', '.'))
    if (!p || p <= 0) return
    const today = new Date().toISOString().split('T')[0]
    const chg = (((p - pdfPrice) / pdfPrice) * 100).toFixed(2)
    const data = { price: p, date: today, changePct: parseFloat(chg) }
    localStorage.setItem(storageKey, JSON.stringify(data))
    setCurrent(data)
    setPrice('')
    try {
      const res = await learnManualPrice(fundCode, {
        pdfPrice, currentPrice: p,
        changePct: parseFloat(chg), pdfMonth, date: today,
      })
      if (res?.insight) setEvolverMsg(res.insight)
    } catch (e) {}
    onSave?.(data)
  }

  const tweetText = current ? [
    `📊 ${fundCode} — ${fundName || 'Fon Güncelleme'}`,
    ``,
    `📄 PDF (${pdfMonth}): ${pdfPrice?.toFixed(4)} TL`,
    `📡 Güncel (${current.date}): ${current.price.toFixed(4)} TL`,
    ``,
    `${Number(changePct) >= 0 ? '🟢' : '🔴'} PDF'den bu yana: ${Number(changePct) >= 0 ? '+' : ''}${changePct}%`,
    ``,
    `#KAP #Fon #Yatırım #BIST #${fundCode}`,
  ].join('\n') : null

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>

      {/* Özet kartlar */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12 }}>
        <div style={{ background: '#1e293b', borderRadius: 10, padding: '12px 14px' }}>
          <div style={{ color: '#64748b', fontSize: 10, textTransform: 'uppercase', letterSpacing: 0.8 }}>PDF Fiyatı ({pdfMonth})</div>
          <div style={{ color: '#94a3b8', fontWeight: 700, fontSize: 16, marginTop: 3, fontFamily: 'JetBrains Mono, monospace' }}>
            {pdfPrice?.toFixed(4)} TL
          </div>
        </div>
        <div style={{
          background: '#1e293b', borderRadius: 10, padding: '12px 14px',
          border: current ? '1px solid rgba(0,194,168,0.3)' : '1px dashed #334155'
        }}>
          <div style={{ color: current ? '#00C2A8' : '#475569', fontSize: 10, textTransform: 'uppercase', letterSpacing: 0.8 }}>
            {current ? `Güncel Fiyat (${current.date})` : 'Henüz Girilmedi'}
          </div>
          <div style={{ color: '#f1f5f9', fontWeight: 700, fontSize: 16, marginTop: 3, fontFamily: 'JetBrains Mono, monospace' }}>
            {current ? `${current.price.toFixed(4)} TL` : '—'}
          </div>
        </div>
        <div style={{ background: '#1e293b', borderRadius: 10, padding: '12px 14px' }}>
          <div style={{ color: '#64748b', fontSize: 10, textTransform: 'uppercase', letterSpacing: 0.8 }}>PDF'den Bu Yana</div>
          <div style={{ color: changeColor, fontWeight: 700, fontSize: 26, marginTop: 3 }}>
            {changePct != null ? `${Number(changePct) >= 0 ? '+' : ''}${changePct}%` : '—'}
          </div>
        </div>
      </div>

      {/* Fiyat giriş */}
      <div style={{ background: '#1e293b', borderRadius: 12, padding: '18px 20px' }}>
        <p style={{ color: '#64748b', fontSize: 12, textTransform: 'uppercase', letterSpacing: 1, margin: '0 0 10px' }}>
          📝 Güncel Pay Fiyatı Gir
        </p>
        <p style={{ color: '#475569', fontSize: 12, margin: '0 0 14px', lineHeight: 1.6 }}>
          TEFAS sitesinden veya aracı kurumunuzdan öğrendiğiniz fiyatı girin.
          Kaydedilince Evolver'a öğretilir, Twitter postu güncellenir.
        </p>
        <div style={{ display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap' }}>
          <input
            value={price}
            onChange={e => setPrice(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleSave()}
            placeholder={current ? current.price.toFixed(4) : 'Örn: 3.1240'}
            style={{
              background: '#0f172a', border: '1px solid #334155', borderRadius: 8,
              padding: '10px 14px', color: '#f1f5f9', fontSize: 15, width: 160,
              fontFamily: 'JetBrains Mono, monospace', outline: 'none',
            }}
          />
          <span style={{ color: '#475569', fontSize: 14 }}>TL</span>
          <button onClick={handleSave} disabled={!price} style={{
            background: price ? '#00C2A8' : '#1e293b',
            color: price ? '#020817' : '#475569',
            border: 'none', borderRadius: 8, padding: '10px 20px',
            cursor: price ? 'pointer' : 'default', fontSize: 13, fontWeight: 700
          }}>
            Kaydet & Öğret
          </button>
          {current && (
            <button onClick={() => {
              localStorage.removeItem(storageKey)
              setCurrent(null)
              setEvolverMsg(null)
            }} style={{
              background: 'rgba(239,71,111,0.1)', color: '#EF476F',
              border: '1px solid rgba(239,71,111,0.2)', borderRadius: 8,
              padding: '10px 14px', cursor: 'pointer', fontSize: 12
            }}>Sıfırla</button>
          )}
        </div>

        {current && (
          <div style={{ marginTop: 14, padding: '10px 14px', background: 'rgba(0,194,168,0.06)', borderRadius: 8, border: '1px solid rgba(0,194,168,0.15)' }}>
            <div style={{ color: '#64748b', fontSize: 11, marginBottom: 4 }}>Hesaplama:</div>
            <div style={{ color: '#94a3b8', fontSize: 13, fontFamily: 'JetBrains Mono, monospace' }}>
              ({current.price.toFixed(4)} − {pdfPrice.toFixed(4)}) ÷ {pdfPrice.toFixed(4)} × 100 =&nbsp;
              <span style={{ color: changeColor, fontWeight: 700 }}>{Number(changePct) >= 0 ? '+' : ''}{changePct}%</span>
            </div>
          </div>
        )}
      </div>

      {/* Evolver bildirimi */}
      {evolverMsg && (
        <div style={{ background: 'rgba(131,56,236,0.1)', border: '1px solid rgba(131,56,236,0.3)', borderRadius: 10, padding: '12px 16px', display: 'flex', gap: 10, alignItems: 'flex-start' }}>
          <span style={{ fontSize: 18 }}>🔮</span>
          <div>
            <div style={{ color: '#8338EC', fontSize: 12, fontWeight: 600, marginBottom: 4 }}>Evolver Öğrendi</div>
            <div style={{ color: '#cbd5e1', fontSize: 13 }}>{evolverMsg}</div>
          </div>
        </div>
      )}

      {/* Twitter postu */}
      {tweetText && (
        <div style={{ background: '#0a0a0a', border: '1px solid #2f3336', borderRadius: 16, padding: 20 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 14 }}>
            <div style={{ width: 40, height: 40, borderRadius: '50%', background: 'linear-gradient(135deg,#00C2A8,#118AB2)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 18 }}>📊</div>
            <div>
              <div style={{ color: '#f1f5f9', fontWeight: 700, fontSize: 14 }}>Fon Tarayıcı</div>
              <div style={{ color: '#64748b', fontSize: 12 }}>@FonTarayici · Güncel Fiyat Postu</div>
            </div>
          </div>
          <pre style={{ color: '#e7e9ea', fontSize: 14, lineHeight: 1.7, whiteSpace: 'pre-wrap', margin: '0 0 14px', fontFamily: 'system-ui' }}>
            {tweetText}
          </pre>
          <button
            onClick={() => { navigator.clipboard.writeText(tweetText); setTweetCopied(true); setTimeout(() => setTweetCopied(false), 2000) }}
            style={{
              background: tweetCopied ? '#00C2A8' : '#1d9bf0', color: 'white', border: 'none',
              borderRadius: 20, padding: '9px 22px', cursor: 'pointer', fontSize: 13, fontWeight: 600
            }}
          >
            {tweetCopied ? '✓ Kopyalandı!' : '📋 Twitter\'a Kopyala'}
          </button>
        </div>
      )}

      {/* Nereden bulunur */}
      <div style={{ background: '#0f172a', border: '1px dashed #1e293b', borderRadius: 10, padding: '14px 18px' }}>
        <p style={{ color: '#475569', fontSize: 12, margin: '0 0 8px', fontWeight: 600 }}>📌 Güncel fiyatı nereden bulabilirsiniz?</p>
        {[
          ['TEFAS', `tefas.gov.tr → Fon Analiz → ${fundCode}`],
          ['Aracı Kurum', 'Kullandığınız uygulama veya platform'],
          ['KAP', 'kap.org.tr → fon bildirimleri'],
        ].map(([src, detail]) => (
          <div key={src} style={{ display: 'flex', gap: 8, fontSize: 12, marginBottom: 4 }}>
            <span style={{ color: '#00C2A8', fontWeight: 600, minWidth: 90 }}>{src}</span>
            <span style={{ color: '#475569' }}>{detail}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

import { useState, useEffect } from 'react'

export default function DailyTweets() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [copied, setCopied] = useState(null)

  useEffect(() => {
    fetch('/api/daily-tweets')
      .then(r => r.json())
      .then(d => { setData(d); setLoading(false) })
      .catch(() => setLoading(false))
  }, [])

  const copy = (text, idx) => {
    if (navigator.clipboard) {
      navigator.clipboard.writeText(text)
    } else {
      const el = document.createElement('textarea')
      el.value = text
      document.body.appendChild(el)
      el.select()
      document.execCommand('copy')
      document.body.removeChild(el)
    }
    setCopied(idx)
    setTimeout(() => setCopied(null), 2000)
  }

  const twitterUrl = (text) => {
    return `https://twitter.com/intent/tweet?text=${encodeURIComponent(text)}`
  }

  if (loading) return <div style={{padding:40,textAlign:'center',color:'#475569'}}>Yükleniyor...</div>
  if (!data) return <div style={{padding:40,textAlign:'center',color:'#f87171'}}>Veri alınamadı</div>

  return (
    <div style={{padding:'24px 28px'}}>
      {/* Başlık */}
      <div style={{display:'flex',alignItems:'center',justifyContent:'space-between',marginBottom:24}}>
        <div>
          <div style={{fontWeight:800,fontSize:20,marginBottom:4}}>🐦 Günlük Tweet Paketi</div>
          <div style={{color:'#475569',fontSize:12}}>{data.ay} · {data.count} tweet hazır · Kopyala ve paylaş</div>
        </div>
        <div style={{background:'rgba(0,194,168,0.1)',border:'1px solid rgba(0,194,168,0.2)',
          borderRadius:10,padding:'8px 16px',fontSize:12,color:'#00C2A8',fontWeight:600}}>
          {data.date}
        </div>
      </div>

      {/* Tweet kartları */}
      <div style={{display:'flex',flexDirection:'column',gap:16}}>
        {data.tweets.map((tweet, idx) => (
          <div key={idx} style={{background:'#0f172a',border:'1px solid #1e293b',borderRadius:16,overflow:'hidden'}}>
            {/* Kart başlık */}
            <div style={{padding:'12px 20px',borderBottom:'1px solid #1e293b',
              display:'flex',alignItems:'center',justifyContent:'space-between'}}>
              <span style={{fontWeight:700,fontSize:13,color:'#f1f5f9'}}>{tweet.title}</span>
              <div style={{display:'flex',gap:8}}>
                {/* Twitter'da aç */}
                <a href={twitterUrl(tweet.text)} target="_blank" rel="noopener noreferrer"
                  style={{background:'rgba(29,161,242,0.15)',border:'1px solid rgba(29,161,242,0.3)',
                    borderRadius:8,padding:'5px 12px',fontSize:12,fontWeight:600,
                    color:'#1da1f2',textDecoration:'none',display:'flex',alignItems:'center',gap:5}}>
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-4.714-6.231-5.401 6.231H2.744l7.73-8.835L1.254 2.25H8.08l4.253 5.622 5.911-5.622zm-1.161 17.52h1.833L7.084 4.126H5.117z"/>
                  </svg>
                  Tweet At
                </a>
                {/* Kopyala */}
                <button onClick={() => copy(tweet.text, idx)} style={{
                  background: copied===idx ? 'rgba(74,222,128,0.15)' : 'rgba(255,255,255,0.05)',
                  border: `1px solid ${copied===idx ? 'rgba(74,222,128,0.3)' : 'rgba(255,255,255,0.1)'}`,
                  borderRadius:8,padding:'5px 12px',fontSize:12,fontWeight:600,
                  color: copied===idx ? '#4ade80' : '#94a3b8',cursor:'pointer',transition:'all 0.15s'
                }}>
                  {copied===idx ? '✅ Kopyalandı' : '📋 Kopyala'}
                </button>
              </div>
            </div>
            {/* Tweet metni */}
            <div style={{padding:'16px 20px'}}>
              <pre style={{
                fontFamily:'Space Grotesk,system-ui,sans-serif',
                fontSize:14,lineHeight:1.7,color:'#e2e8f0',
                whiteSpace:'pre-wrap',wordBreak:'break-word',margin:0
              }}>{tweet.text}</pre>
            </div>
            {/* Karakter sayısı */}
            <div style={{padding:'8px 20px',borderTop:'1px solid #1e293b',
              display:'flex',justifyContent:'space-between',alignItems:'center'}}>
              <span style={{fontSize:11,color:'#334155'}}>
                {tweet.text.length} karakter
              </span>
              <span style={{fontSize:11,color: tweet.text.length > 4000 ? '#f87171' : tweet.text.length > 280 ? '#facc15' : '#4ade80'}}>
                {tweet.text.length > 4000 ? '⚠️ Çok uzun' : tweet.text.length > 280 ? '✓ Premium (4000 limit)' : '✓ Standard (280 limit)'}
              </span>
            </div>
          </div>
        ))}
      </div>

      {/* Alt not */}
      <div style={{marginTop:20,padding:'12px 16px',background:'rgba(0,194,168,0.05)',
        border:'1px solid rgba(0,194,168,0.1)',borderRadius:10,fontSize:12,color:'#475569',textAlign:'center'}}>
        💡 "Tweet At" butonu Twitter compose sayfasını açar · Mavi tıksan 4000 karaktere kadar tweet atabilirsin
      </div>
    </div>
  )
}

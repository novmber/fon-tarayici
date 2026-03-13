import { useState, useEffect } from 'react'

const API = ''

export default function Top5({ onSelectFund }) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [period, setPeriod] = useState('1m')

  useEffect(() => {
    fetch(`${API}/api/top5`)
      .then(r => r.json())
      .then(d => { setData(d); setLoading(false) })
      .catch(() => setLoading(false))
  }, [])

  const periodMap = {
    '1m':  { key: 'top5_1m',           label: 'Son 1 Ay',               retKey: 'return1m' },
    '3m':  { key: 'top5_3m',           label: 'Son 3 Ay',               retKey: 'return3m' },
    '6m':  { key: 'top5_6m',           label: 'Son 6 Ay',               retKey: 'return6m' },
    '1y':  { key: 'top5_1y',           label: 'Son 1 Yıl',              retKey: 'return1y' },
    'flow':{ key: 'top5_flow',         label: 'Para Girişi (30g)',       retKey: 'moneyFlow30d' },
    'part':{ key: 'top5_participants', label: 'Yatırımcı Artışı (30g)', retKey: 'participantChange30d' },
  }

  const fmt = (v, key) => {
    if (v == null) return '—'
    if (key === 'moneyFlow30d') {
      const abs = Math.abs(v)
      const s = abs >= 1e9 ? (abs/1e9).toFixed(2)+'B' : (abs/1e6).toFixed(0)+'M'
      return (v > 0 ? '+' : '-') + '₺' + s
    }
    if (key === 'participantChange30d') return (v > 0 ? '+' : '') + Math.round(v).toLocaleString('tr-TR') + ' kişi'
    return (v > 0 ? '+' : '') + v.toFixed(2) + '%'
  }

  const riskColor = r => ({'1':'#4ade80','2':'#4ade80','3':'#a3e635','4':'#facc15','5':'#fb923c','6':'#f87171','7':'#ef4444'}[String(r)] || '#94a3b8')

  if (loading) return <div style={{padding:40,textAlign:'center',color:'#475569'}}>Yükleniyor...</div>
  if (!data) return <div style={{padding:40,textAlign:'center',color:'#f87171'}}>Veri alınamadı</div>

  const { key, label, retKey } = periodMap[period]
  const funds = data[key] || []

  return (
    <div style={{padding:'24px 28px'}}>
      <div style={{display:'flex',alignItems:'center',justifyContent:'space-between',marginBottom:24,flexWrap:'wrap',gap:12}}>
        <div>
          <div style={{fontWeight:800,fontSize:20,marginBottom:4}}>🏆 Top 5 Fon</div>
          <div style={{color:'#475569',fontSize:12}}>Takip ettiğin fonlar arasında dönemsel sıralama</div>
        </div>
        <div style={{display:'flex',gap:6,flexWrap:'wrap'}}>
          {Object.entries(periodMap).map(([k,v]) => (
            <button key={k} onClick={() => setPeriod(k)} style={{
              background: period===k ? 'rgba(0,194,168,0.15)' : 'rgba(255,255,255,0.05)',
              color: period===k ? '#00C2A8' : '#94a3b8',
              border: `1px solid ${period===k ? 'rgba(0,194,168,0.3)' : 'rgba(255,255,255,0.1)'}`,
              borderRadius:8, padding:'6px 12px', cursor:'pointer', fontSize:12, fontWeight:600
            }}>{v.label}</button>
          ))}
        </div>
      </div>

      <div style={{display:'flex',flexDirection:'column',gap:12}}>
        {funds.map((f, i) => (
          <div key={f.code} onClick={() => onSelectFund && onSelectFund(f.code)}
            style={{background:'#0f172a',border:'1px solid #1e293b',borderRadius:14,padding:'16px 20px',
              cursor:'pointer',display:'flex',alignItems:'center',gap:16,flexWrap:'wrap'}}>
            <div style={{width:36,height:36,borderRadius:10,flexShrink:0,
              background: i===0?'linear-gradient(135deg,#FFD700,#FFA500)':i===1?'linear-gradient(135deg,#C0C0C0,#A8A8A8)':i===2?'linear-gradient(135deg,#CD7F32,#8B4513)':'#1e293b',
              display:'flex',alignItems:'center',justifyContent:'center',fontWeight:800,fontSize:16}}>
              {i===0?'🥇':i===1?'🥈':i===2?'🥉':i+1}
            </div>
            <div style={{background:'rgba(0,194,168,0.1)',border:'1px solid rgba(0,194,168,0.2)',
              borderRadius:8,padding:'4px 10px',fontWeight:700,fontSize:13,color:'#00C2A8',flexShrink:0,minWidth:48,textAlign:'center'}}>
              {f.code}
            </div>
            <div style={{flex:1,minWidth:160}}>
              <div style={{fontWeight:600,fontSize:14,marginBottom:2,whiteSpace:'nowrap',overflow:'hidden',textOverflow:'ellipsis'}}>
                {f.name}
              </div>
              <div style={{color:'#475569',fontSize:11}}>{f.fundType || 'Yatırım Fonu'}</div>
            </div>
            {f.riskScore && (
              <div style={{textAlign:'center',flexShrink:0}}>
                <div style={{color:riskColor(f.riskScore),fontWeight:700,fontSize:14}}>{f.riskScore}/7</div>
                <div style={{color:'#475569',fontSize:10}}>Risk</div>
              </div>
            )}
            <div style={{textAlign:'center',flexShrink:0}}>
              <div style={{color:'#f1f5f9',fontWeight:700,fontSize:14}}>
                {f.totalValue >= 1e9 ? (f.totalValue/1e9).toFixed(1)+'B' : (f.totalValue/1e6).toFixed(0)+'M'} ₺
              </div>
              <div style={{color:'#475569',fontSize:10}}>Portföy</div>
            </div>
            <div style={{textAlign:'center',flexShrink:0}}>
              <div style={{color:'#f1f5f9',fontWeight:700,fontSize:14}}>{Math.round(f.participantCount).toLocaleString('tr-TR')}</div>
              <div style={{color:'#475569',fontSize:10}}>Yatırımcı</div>
            </div>
            <div style={{textAlign:'right',flexShrink:0,minWidth:100}}>
              <div style={{color:(f[retKey]||0)>0?'#4ade80':'#f87171',fontWeight:800,fontSize:22}}>
                {fmt(f[retKey], retKey)}
              </div>
              <div style={{color:'#475569',fontSize:10}}>{label}</div>
            </div>
          </div>
        ))}
      </div>

      {funds[0]?.dexterRecommendations?.length > 0 && (
        <div style={{marginTop:24,background:'#0f172a',border:'1px solid rgba(0,194,168,0.2)',borderRadius:14,padding:'16px 20px'}}>
          <div style={{color:'#00C2A8',fontWeight:700,fontSize:13,marginBottom:12}}>
            🤖 Dexter — {funds[0].code} için öneri
          </div>
          {funds[0].dexterRecommendations.map((r,i) => (
            <div key={i} style={{color:'#94a3b8',fontSize:13,padding:'6px 0',
              borderBottom:i<funds[0].dexterRecommendations.length-1?'1px solid #1e293b':'none'}}>
              • {r}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

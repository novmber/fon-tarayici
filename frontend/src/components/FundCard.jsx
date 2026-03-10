import { useState } from 'react'

const COLORS = ['#00C2A8','#3A86FF','#FFD166','#EF476F','#8338EC','#06D6A0','#FB5607','#FFBE0B','#43AA8B','#F72585']
const RISK_COLORS = ['','#22c55e','#84cc16','#eab308','#f97316','#ef4444','#dc2626','#991b1b']

export default function FundCard({ fund, onClick, onRefresh }) {
  const [hover, setHover] = useState(false)
  const [refreshing, setRefreshing] = useState(false)

  const manualData = (() => {
    try { return JSON.parse(localStorage.getItem(`manual_price_${fund.code}`)) } catch { return null }
  })()
  const changePct = manualData
    ? (((manualData.price - fund.unitPrice) / fund.unitPrice) * 100).toFixed(2)
    : null

  const handleRefresh = async (e) => {
    e.stopPropagation()
    setRefreshing(true)
    await onRefresh?.()
    setRefreshing(false)
  }

  return (
    <button
      onClick={onClick}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      style={{
        background: '#0f172a',
        border: `1px solid ${hover ? '#00C2A8' : '#1e293b'}`,
        borderRadius: 16, padding: '18px 20px', cursor: 'pointer', textAlign: 'left',
        display: 'flex', flexDirection: 'column', gap: 12, position: 'relative', overflow: 'hidden',
        transform: hover ? 'translateY(-2px)' : 'none', transition: 'all 0.15s',
        boxShadow: hover ? '0 8px 32px rgba(0,194,168,0.1)' : 'none',
      }}
    >
      {/* PDF rozeti */}
      {fund.hasPdfAnalysis && (
        <div style={{ position: 'absolute', top: 10, right: 10, background: 'rgba(255,209,102,0.15)', color: '#FFD166', borderRadius: 6, padding: '2px 7px', fontSize: 10, fontWeight: 700 }}>
          📄 AI
        </div>
      )}

      {/* Accent bar */}
      <div style={{ position: 'absolute', top: 0, left: 0, right: 0, height: 3, background: fund.monthlyReturn >= 0 ? '#00C2A8' : '#EF476F', borderRadius: '16px 16px 0 0' }} />

      {/* Başlık */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', paddingTop: 4 }}>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 5, flexWrap: 'wrap' }}>
            <span style={{ background: '#1e293b', color: '#00C2A8', borderRadius: 6, padding: '2px 8px', fontSize: 12, fontWeight: 700 }}>{fund.code}</span>
            <span style={{ color: '#475569', fontSize: 11 }}>{fund.latestDate}</span>
            {fund.riskScore && (
              <span style={{ background: `${RISK_COLORS[fund.riskScore]}22`, color: RISK_COLORS[fund.riskScore], borderRadius: 6, padding: '2px 6px', fontSize: 10, fontWeight: 700 }}>
                Risk {fund.riskScore}/7
              </span>
            )}
          </div>
          <div style={{ color: '#f1f5f9', fontWeight: 600, fontSize: 13, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: 220 }}>
            {fund.name}
          </div>
          {fund.fundType && <div style={{ color: '#475569', fontSize: 11, marginTop: 2 }}>{fund.fundType}</div>}
        </div>

        {/* Getiri (sadece PDF analizi varsa göster) */}
        {fund.monthlyReturn != null && (
          <div style={{ textAlign: 'right', flexShrink: 0, marginLeft: 10 }}>
            <div style={{ color: fund.monthlyReturn >= 0 ? '#00C2A8' : '#EF476F', fontWeight: 700, fontSize: 18 }}>
              {fund.monthlyReturn >= 0 ? '+' : ''}{fund.monthlyReturn}%
            </div>
            <div style={{ color: '#475569', fontSize: 10 }}>aylık</div>
            {fund.yearlyReturn != null && (
              <div style={{ color: '#FFD166', fontSize: 11, fontWeight: 600 }}>{fund.yearlyReturn}% yıllık</div>
            )}
          </div>
        )}
      </div>

      {/* Fiyat kartları */}
      <div style={{ display: 'flex', background: '#1e293b', borderRadius: 10, overflow: 'hidden' }}>
        <div style={{ flex: 1, padding: '9px 12px', borderRight: manualData ? '1px solid #0f172a' : 'none' }}>
          <div style={{ color: '#475569', fontSize: 10, marginBottom: 2 }}>TEFAS ({fund.latestDate})</div>
          <div style={{ color: '#f1f5f9', fontWeight: 700, fontSize: 14, fontFamily: 'JetBrains Mono, monospace' }}>
            {fund.unitPrice?.toFixed(6)} TL
          </div>
        </div>
        {manualData && (
          <div style={{ flex: 1, padding: '9px 12px' }}>
            <div style={{ color: '#00C2A8', fontSize: 10, marginBottom: 2 }}>Manuel ({manualData.date})</div>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: 6 }}>
              <span style={{ color: '#f1f5f9', fontWeight: 700, fontSize: 14, fontFamily: 'JetBrains Mono, monospace' }}>
                {manualData.price.toFixed(4)} TL
              </span>
              <span style={{ color: Number(changePct) >= 0 ? '#00C2A8' : '#EF476F', fontSize: 11, fontWeight: 700 }}>
                {Number(changePct) >= 0 ? '+' : ''}{changePct}%
              </span>
            </div>
          </div>
        )}
      </div>

      {/* Portföy + Değer */}
      <div style={{ display: 'flex', gap: 16, alignItems: 'center' }}>
        <div>
          <div style={{ color: '#475569', fontSize: 10 }}>Portföy</div>
          <div style={{ color: '#94a3b8', fontSize: 12, fontWeight: 600 }}>
            {fund.totalValue >= 1e9 ? `₺${(fund.totalValue/1e9).toFixed(2)}B` : `₺${(fund.totalValue/1e6).toFixed(1)}M`}
          </div>
        </div>
        {fund.participantCount > 0 && (
          <div>
            <div style={{ color: '#475569', fontSize: 10 }}>Yatırımcı</div>
            <div style={{ color: '#94a3b8', fontSize: 12, fontWeight: 600 }}>
              {fund.participantCount.toLocaleString('tr-TR', { maximumFractionDigits: 0 })}
            </div>
          </div>
        )}
        {/* Yenile butonu */}
        <button
          onClick={handleRefresh}
          disabled={refreshing}
          title="TEFAS'tan güncelle"
          style={{ marginLeft: 'auto', background: 'none', border: 'none', color: '#334155', cursor: 'pointer', fontSize: 14, padding: 4 }}
        >
          {refreshing ? '⏳' : '🔄'}
        </button>
      </div>

      {/* Mini portföy bar */}
      {fund.portfolioItems?.length > 0 && (
        <div style={{ display: 'flex', height: 4, borderRadius: 4, overflow: 'hidden', gap: 1 }}>
          {fund.portfolioItems.filter(i => i.value > 0).map((item, i) => (
            <div key={i} title={`${item.name}: ${item.value}%`} style={{ flex: item.value, background: COLORS[i % COLORS.length] }} />
          ))}
        </div>
      )}
    </button>
  )
}

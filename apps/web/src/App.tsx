import { useEffect, useState } from 'react'

type Health = {
  status: string
  service: string
  version: string
}

export default function App() {
  const [health, setHealth] = useState<Health | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetch('http://127.0.0.1:8765/api/health')
      .then((response) => {
        if (!response.ok) throw new Error(`HTTP ${response.status}`)
        return response.json() as Promise<Health>
      })
      .then(setHealth)
      .catch((err: Error) => setError(err.message))
  }, [])

  return (
    <main className="shell">
      <section className="hero">
        <p className="eyebrow">HT-CN LOCAL</p>
        <h1>A 股谐波研究与辅助决策系统</h1>
        <p className="subtitle">本地优先 · 零订阅 · Agent First</p>
      </section>

      <section className="status-card" aria-label="system-status">
        <div>
          <span className="label">Web</span>
          <strong>运行中</strong>
        </div>
        <div>
          <span className="label">API</span>
          <strong>{health ? '已连接' : error ? '连接失败' : '检查中'}</strong>
        </div>
        <div>
          <span className="label">版本</span>
          <strong>{health?.version ?? '0.1.0'}</strong>
        </div>
      </section>

      {error && <p className="error">API 未连接：{error}</p>}

      <section className="placeholder">
        <h2>M0 工程骨架</h2>
        <p>下一阶段将接入 A 股历史数据、K 线和 HT-CN Core。</p>
      </section>
    </main>
  )
}

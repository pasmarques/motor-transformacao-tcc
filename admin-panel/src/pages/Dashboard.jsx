import { useEffect, useState } from 'react'
import { apiJSON } from '../api/client'
import styles from './Dashboard.module.css'

export default function Dashboard() {
  const [status, setStatus] = useState(null)
  const [erro, setErro] = useState('')

  useEffect(() => { carregar() }, [])

  async function carregar() {
    try {
      const data = await apiJSON('/admin/status')
      setStatus(data)
    } catch (err) {
      setErro(err.message)
    }
  }

  async function handleReload() {
    try {
      const data = await apiJSON('/admin/reload', { method: 'POST' })
      alert(data.mensagem)
      carregar()
    } catch (err) {
      alert('Erro: ' + err.message)
    }
  }

  return (
    <div>
      <div className={styles.header}>
        <div>
          <h1 className={styles.title}>Dashboard</h1>
          <p className={styles.subtitle}>Status do motor de transformação</p>
        </div>
        <button className={styles.reloadBtn} onClick={handleReload}>
          ↺ Recarregar motor
        </button>
      </div>

      {erro && <div className={styles.erro}>{erro}</div>}

      {status && (
        <div className={styles.grid}>
          <div className={styles.card}>
            <div className={styles.cardLabel}>Status</div>
            <div className={styles.cardValue} style={{ color: 'var(--green)' }}>
              ● {status.motor}
            </div>
          </div>
          <div className={styles.card}>
            <div className={styles.cardLabel}>Plugins ativos</div>
            <div className={styles.cardValue}>{status.n_plugins}</div>
          </div>
        </div>
      )}

      {status?.plugins?.length > 0 && (
        <div className={styles.section}>
          <h2 className={styles.sectionTitle}>Plugins carregados</h2>
          <div className={styles.pluginList}>
            {status.plugins.map(p => (
              <div key={p.name} className={styles.pluginCard}>
                <div className={styles.pluginName}>⬡ {p.name}</div>
                <div className={styles.pluginProvides}>
                  Gera: {p.provides.join(', ')}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

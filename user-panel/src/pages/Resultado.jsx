import { useState } from 'react'
import styles from './Resultado.module.css'

const PAGE_SIZE = 10

export default function Resultado({ estado }) {
  const [pagina, setPagina] = useState(0)
  const { tabela = [], colunas = [], n_pacientes, n_janelas, n_colunas, perfil_ativo } = estado

  const totalPags = Math.ceil(tabela.length / PAGE_SIZE)
  const linhas = tabela.slice(pagina * PAGE_SIZE, (pagina + 1) * PAGE_SIZE)

  function baixarCSV() {
    const csv = [colunas.join(','), ...tabela.map(r => colunas.map(c => r[c] ?? '').join(','))].join('\n')
    const blob = new Blob([csv], { type: 'text/csv' })
    const a = document.createElement('a'); a.href = URL.createObjectURL(blob)
    a.download = 'dataset_transformado.csv'; a.click()
  }

  function baixarJSON() {
    const blob = new Blob([JSON.stringify(tabela, null, 2)], { type: 'application/json' })
    const a = document.createElement('a'); a.href = URL.createObjectURL(blob)
    a.download = 'dataset_transformado.json'; a.click()
  }

  return (
    <div>
      {/* Métricas */}
      <div className={styles.metrics}>
        {[
          ['Pacientes', n_pacientes, 'transformados'],
          ['Janelas', n_janelas, 'observadas'],
          ['Colunas', n_colunas, 'variáveis geradas'],
          ['Perfil', perfil_ativo ? 'mock ativo' : 'ausente', 'MEP'],
        ].map(([label, value, sub]) => (
          <div key={label} className={styles.metricCard}>
            <div className={styles.metricLabel}>{label}</div>
            <div className={styles.metricValue}>{value}</div>
            <div className={styles.metricSub}>{sub}</div>
          </div>
        ))}
      </div>

      {/* Tabela */}
      <div className={styles.tableWrap}>
        <table>
          <thead>
            <tr>{colunas.map(c => <th key={c}>{c}</th>)}</tr>
          </thead>
          <tbody>
            {linhas.map((row, i) => (
              <tr key={i}>
                {colunas.map(c => <td key={c}>{row[c] ?? ''}</td>)}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Paginação */}
      {totalPags > 1 && (
        <div className={styles.paginacao}>
          <button onClick={() => setPagina(p => Math.max(0, p - 1))} disabled={pagina === 0}>← Anterior</button>
          <span>Página {pagina + 1} de {totalPags}</span>
          <button onClick={() => setPagina(p => Math.min(totalPags - 1, p + 1))} disabled={pagina === totalPags - 1}>Próxima →</button>
        </div>
      )}

      {/* Downloads */}
      <div className={styles.downloads}>
        <button className={styles.dlBtn} onClick={baixarCSV}>⬇ Baixar CSV</button>
        <button className={styles.dlBtn} onClick={baixarJSON}>⬇ Baixar JSON</button>
      </div>
    </div>
  )
}

import { useState } from 'react'
import styles from './Validacao.module.css'

export default function Validacao({ estado }) {
  const [expandido, setExpandido] = useState(false)
  const { report_metricas: m = {}, report_texto } = estado

  if (!m || Object.keys(m).length === 0) {
    return (
      <div className={styles.info}>
        Arquivo de referência não encontrado. A validação requer o CSV de referência no servidor.
      </div>
    )
  }

  const iguais   = m['Colunas iguais'] || 0
  const difs     = m['Colunas com diferenca de valor'] || 0
  const ausentes = m['Colunas esperadas ausentes'] || 0
  const pcts     = m['Pacientes comparados'] || 0

  const diagLabels = [
    ['Diagnostico', 'Diagnóstico geral'],
    ['Nao comparaveis neste modo', 'Não comparáveis (sem perfil)'],
    ['Diferencas possivelmente ligadas a perfil/peso/sexo', 'Ligadas a perfil/sexo/peso'],
    ['Diferencas possivelmente ligadas a recorte/internacao', 'Ligadas a recorte/internação'],
    ['Diferencas em regras longitudinais a calibrar', 'Regras longitudinais a calibrar'],
  ]

  return (
    <div>
      <div className={styles.cards}>
        {[
          [pcts,     'Pacientes comparados', ''],
          [iguais,   'Colunas iguais',       'green'],
          [difs,     'Com divergência',      difs > 0 ? 'red' : 'green'],
          [ausentes, 'Ausentes',             ausentes > 0 ? 'red' : ''],
        ].map(([val, label, cor]) => (
          <div key={label} className={`${styles.card} ${styles[cor] || ''}`}>
            <div className={styles.cardVal}>{val}</div>
            <div className={styles.cardLabel}>{label}</div>
          </div>
        ))}
      </div>

      {diagLabels.map(([key, label]) => m[key] && (
        <div key={key} className={styles.diagBlock}>
          <strong>{label}:</strong> {m[key]}
        </div>
      ))}

      {report_texto && (
        <div className={styles.rawWrap}>
          <button className={styles.rawToggle} onClick={() => setExpandido(e => !e)}>
            {expandido ? '▲ Ocultar' : '▼ Ver relatório completo'}
          </button>
          {expandido && <pre className={styles.raw}>{report_texto}</pre>}
        </div>
      )}
    </div>
  )
}

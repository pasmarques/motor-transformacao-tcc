import { useState, useEffect } from 'react'
import { apiPost } from '../api/client'
import styles from './JsonViewer.module.css'

function highlight(json) {
  return json
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(
      /("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+\-]?\d+)?)/g,
      match => {
        let cls = 'jv-num'
        if (/^"/.test(match)) cls = /:$/.test(match) ? 'jv-key' : 'jv-str'
        else if (/true|false/.test(match)) cls = 'jv-bool'
        else if (/null/.test(match)) cls = 'jv-null'
        return `<span class="${cls}">${match}</span>`
      }
    )
}

export default function JsonViewer({ estado }) {
  const { pacientes_ids = [], preview_json } = estado
  const [pid, setPid] = useState(pacientes_ids[0] || '')
  const [dados, setDados] = useState(preview_json || {})
  const [carregando, setCarregando] = useState(false)

  useEffect(() => {
    if (pid) carregarJson(pid)
  }, [pid])

  async function carregarJson(id) {
    setCarregando(true)
    try {
      const data = await apiPost('/api/paciente_json', { subject_id: id })
      setDados(data)
    } catch {
      setDados(preview_json || {})
    } finally {
      setCarregando(false)
    }
  }

  function copiar() {
    navigator.clipboard.writeText(JSON.stringify(dados, null, 2))
  }

  return (
    <div>
      <div className={styles.toolbar}>
        <div className={styles.seletor}>
          <label>Paciente:</label>
          <select value={pid} onChange={e => setPid(parseInt(e.target.value))}>
            {pacientes_ids.map(id => <option key={id} value={id}>{id}</option>)}
          </select>
        </div>
        <button className={styles.copyBtn} onClick={copiar}>📋 Copiar JSON</button>
      </div>

      <div
        className={styles.viewer}
        dangerouslySetInnerHTML={{
          __html: carregando ? 'Carregando...' : highlight(JSON.stringify(dados, null, 2))
        }}
      />
    </div>
  )
}

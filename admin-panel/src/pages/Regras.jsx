import { useEffect, useState } from 'react'
import CodeMirror from '@uiw/react-codemirror'
import { json } from '@codemirror/lang-json'
import { apiJSON } from '../api/client'
import styles from './Regras.module.css'

export default function Regras() {
  const [conteudo, setConteudo] = useState('')
  const [msg, setMsg] = useState(null)
  const [carregando, setCarregando] = useState(false)

  useEffect(() => { carregar() }, [])

  async function carregar() {
    try {
      const data = await apiJSON('/api/regras')
      setConteudo(JSON.stringify(data, null, 2))
    } catch (err) {
      setMsg({ tipo: 'erro', texto: 'Erro ao carregar regras: ' + err.message })
    }
  }

  async function handleSalvar() {
    setMsg(null)
    let payload
    try {
      payload = JSON.parse(conteudo)
    } catch {
      setMsg({ tipo: 'erro', texto: 'JSON inválido. Corrija antes de salvar.' })
      return
    }
    setCarregando(true)
    try {
      const data = await apiJSON('/admin/regras', {
        method: 'PUT',
        body: JSON.stringify(payload),
      })
      setMsg({ tipo: 'ok', texto: data.mensagem })
    } catch (err) {
      setMsg({ tipo: 'erro', texto: err.message })
    } finally {
      setCarregando(false)
    }
  }

  return (
    <div>
      <div className={styles.header}>
        <div>
          <h1 className={styles.title}>Regras Clínicas</h1>
          <p className={styles.subtitle}>Limiares clínicos usados pelo motor — edite e salve sem reiniciar</p>
        </div>
        <button className={styles.saveBtn} onClick={handleSalvar} disabled={carregando}>
          {carregando ? 'Salvando...' : '✓ Salvar e recarregar'}
        </button>
      </div>

      {msg && (
        <div className={msg.tipo === 'ok' ? styles.msgOk : styles.msgErro}>
          {msg.texto}
        </div>
      )}

      <div className={styles.editorWrap}>
        <CodeMirror
          value={conteudo}
          extensions={[json()]}
          onChange={setConteudo}
          theme="dark"
          height="600px"
        />
      </div>
    </div>
  )
}

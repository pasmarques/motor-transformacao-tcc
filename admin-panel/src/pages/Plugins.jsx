import { useEffect, useState } from 'react'
import CodeMirror from '@uiw/react-codemirror'
import { python } from '@codemirror/lang-python'
import { apiJSON, apiFetch } from '../api/client'
import styles from './Plugins.module.css'

const TEMPLATE = `from etl_motor.base import BaseModule, PatientContext
from typing import Any


class MeuModulo(BaseModule):
    name = "meu_modulo"
    provides = ("minhaVariavel",)

    def transform(self, context: PatientContext) -> dict[str, Any]:
        # context.windows   → DataFrame com as janelas do paciente
        # context.features  → dict com variáveis já calculadas
        # context.patient   → dados do perfil
        return {
            "minhaVariavel": 0.0,
        }
`

export default function Plugins() {
  const [plugins, setPlugins] = useState([])
  const [nome, setNome] = useState('')
  const [codigo, setCodigo] = useState(TEMPLATE)
  const [msg, setMsg] = useState(null)
  const [carregando, setCarregando] = useState(false)

  useEffect(() => { carregar() }, [])

  async function carregar() {
    try {
      const data = await apiJSON('/admin/plugins')
      setPlugins(data.plugins_ativos || [])
    } catch (err) {
      setMsg({ tipo: 'erro', texto: err.message })
    }
  }

  async function handleUpload(e) {
    e.preventDefault()
    setMsg(null)
    setCarregando(true)
    try {
      const data = await apiJSON('/admin/plugins/upload', {
        method: 'POST',
        body: JSON.stringify({ nome, codigo }),
      })
      setMsg({ tipo: 'ok', texto: data.mensagem })
      setNome('')
      setCodigo(TEMPLATE)
      carregar()
    } catch (err) {
      setMsg({ tipo: 'erro', texto: err.message })
    } finally {
      setCarregando(false)
    }
  }

  async function handleRemover(pluginNome) {
    if (!confirm(`Remover plugin '${pluginNome}'?`)) return
    try {
      const data = await apiJSON(`/admin/plugins/${pluginNome}`, { method: 'DELETE' })
      setMsg({ tipo: 'ok', texto: data.mensagem })
      carregar()
    } catch (err) {
      setMsg({ tipo: 'erro', texto: err.message })
    }
  }

  return (
    <div>
      <h1 className={styles.title}>Plugins</h1>
      <p className={styles.subtitle}>Gerencie módulos customizados do motor</p>

      {/* Lista de plugins ativos */}
      <div className={styles.section}>
        <h2 className={styles.sectionTitle}>Plugins ativos ({plugins.length})</h2>
        {plugins.length === 0
          ? <p className={styles.empty}>Nenhum plugin ativo.</p>
          : plugins.map(p => (
            <div key={p.name} className={styles.pluginRow}>
              <div className={styles.pluginInfo}>
                <span className={styles.pluginName}>⬡ {p.name}</span>
                <span className={styles.pluginProvides}>Gera: {p.provides.join(', ')}</span>
              </div>
              <button className={styles.removeBtn} onClick={() => handleRemover(p.name)}>
                Remover
              </button>
            </div>
          ))
        }
      </div>

      {/* Upload de novo plugin */}
      <div className={styles.section}>
        <h2 className={styles.sectionTitle}>Novo plugin</h2>
        <form onSubmit={handleUpload}>
          <div className={styles.field}>
            <label className={styles.label}>Nome do arquivo</label>
            <input
              className={styles.input}
              value={nome}
              onChange={e => setNome(e.target.value)}
              placeholder="ex: score_sepse.py"
              required
            />
          </div>
          <div className={styles.field}>
            <label className={styles.label}>Código Python</label>
            <div className={styles.editor}>
              <CodeMirror
                value={codigo}
                extensions={[python()]}
                onChange={setCodigo}
                theme="dark"
                height="360px"
              />
            </div>
          </div>

          {msg && (
            <div className={msg.tipo === 'ok' ? styles.msgOk : styles.msgErro}>
              {msg.texto}
            </div>
          )}

          <button className={styles.uploadBtn} type="submit" disabled={carregando}>
            {carregando ? 'Instalando...' : '⬆ Instalar plugin'}
          </button>
        </form>
      </div>
    </div>
  )
}

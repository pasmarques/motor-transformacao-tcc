import { useState, useEffect } from 'react'
import { apiPost, apiGet } from '../api/client'
import styles from './Sidebar.module.css'

export default function Sidebar({ executando, setExecutando, onResultado }) {
  const [entradasDir, setEntradasDir]   = useState('entradas')
  const [subjectId, setSubjectId]       = useState('')
  const [perfilMode, setPerfilMode]     = useState('mock')
  const [mockFile, setMockFile]         = useState('ICUpatients21D.csv')
  const [cortar, setCortar]             = useState(1)
  const [maxJan, setMaxJan]             = useState('')
  const [dataRef, setDataRef]           = useState('')
  const [varMode, setVarMode]           = useState('todas')
  const [variaveis, setVariaveis]       = useState([])
  const [varSelecionadas, setVarSel]    = useState([])
  const [agregacoes, setAgregacoes]     = useState('')
  const [agrOrigem, setAgrOrigem]       = useState('')
  const [agrFunc, setAgrFunc]           = useState('max')
  const [agrNome, setAgrNome]           = useState('')
  const [plugins, setPlugins]           = useState([])
  const [erro, setErro]                 = useState('')

  useEffect(() => {
    apiGet('/api/plugins')
      .then(data => setPlugins(data))
      .catch(() => {})
  }, [])

  async function carregarVariaveis() {
    if (variaveis.length) return
    try {
      const data = await apiGet('/api/variaveis')
      setVariaveis(data)
      setVarSel(data)
    } catch {}
  }

  function toggleVar(v) {
    setVarSel(prev => prev.includes(v) ? prev.filter(x => x !== v) : [...prev, v])
  }

  function adicionarAgregacao() {
    if (!agrOrigem || !agrNome) return
    const linha = `${agrOrigem}:${agrFunc}:${agrNome}`
    setAgregacoes(prev => prev ? prev + '\n' + linha : linha)
    setAgrOrigem(''); setAgrNome('')
  }

  async function executar() {
    setErro('')
    setExecutando(true)
    try {
      const payload = {
        entradas_dir: entradasDir,
        subject_id: subjectId,
        patient_info_file: perfilMode === 'mock' ? mockFile : null,
        cortar_janelas_finais: parseInt(cortar) || 0,
        max_janelas: maxJan || null,
        data_referencia: dataRef || null,
        sem_metadados: varMode === 'sem-meta',
        variaveis_saida: varMode === 'selecionar'
          ? varSelecionadas.join(',') || null
          : null,
        agregacoes,
      }
      const data = await apiPost('/api/transform', payload)
      onResultado(data)
    } catch (err) {
      setErro(err.message)
    } finally {
      setExecutando(false)
    }
  }

  return (
    <aside className={styles.sidebar}>
      <div className={styles.header}>
        <h1 className={styles.title}>Motor de Transformação<br />MIMIC-IV</h1>
        <span className={styles.badge}>Bloco 2</span>
      </div>

      {/* Plugins ativos */}
      {plugins.length > 0 && (
        <div className={styles.section}>
          <div className={styles.label}>Plugins ativos</div>
          <div className={styles.plugins}>
            {plugins.map(p => (
              <span key={p.name} className={styles.pluginTag} title={`Gera: ${p.provides?.join(', ')}`}>
                ⬡ {p.name}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Entrada */}
      <div className={styles.section}>
        <div className={styles.groupLabel}>Entrada</div>
        <div className={styles.field}>
          <label>Pasta de mapas diários</label>
          <input value={entradasDir} onChange={e => setEntradasDir(e.target.value)} />
        </div>
        <div className={styles.field}>
          <label>Paciente específico (opcional)</label>
          <input value={subjectId} onChange={e => setSubjectId(e.target.value)} placeholder="ex: 12925639" />
        </div>
      </div>

      {/* Perfil */}
      <div className={styles.section}>
        <div className={styles.groupLabel}>Perfil &amp; Internação</div>
        <div className={styles.radioGroup}>
          <label><input type="radio" checked={perfilMode === 'mock'} onChange={() => setPerfilMode('mock')} /> Com mock do MEP</label>
          <label><input type="radio" checked={perfilMode === 'sem'} onChange={() => setPerfilMode('sem')} /> Sem perfil</label>
        </div>
        {perfilMode === 'mock' && (
          <div className={styles.field} style={{ marginTop: 8 }}>
            <label>Arquivo de perfil</label>
            <input value={mockFile} onChange={e => setMockFile(e.target.value)} />
          </div>
        )}
      </div>

      {/* Janela */}
      <div className={styles.section}>
        <div className={styles.groupLabel}>Janela de Observação</div>
        <div className={styles.field}>
          <label>Cortar janelas finais</label>
          <input type="number" value={cortar} onChange={e => setCortar(e.target.value)} min="0" />
        </div>
        <div className={styles.field}>
          <label>Máximo de janelas</label>
          <input type="number" value={maxJan} onChange={e => setMaxJan(e.target.value)} placeholder="sem limite" min="1" />
        </div>
        <div className={styles.field}>
          <label>Data de referência (opcional)</label>
          <input value={dataRef} onChange={e => setDataRef(e.target.value)} placeholder="YYYY-MM-DD" />
        </div>
      </div>

      {/* Variáveis de saída */}
      <div className={styles.section}>
        <div className={styles.groupLabel}>Variáveis de Saída</div>
        <div className={styles.radioGroup}>
          <label><input type="radio" checked={varMode === 'todas'} onChange={() => setVarMode('todas')} /> Todas do contrato</label>
          <label><input type="radio" checked={varMode === 'sem-meta'} onChange={() => setVarMode('sem-meta')} /> Sem metadados auxiliares</label>
          <label>
            <input type="radio" checked={varMode === 'selecionar'}
              onChange={() => { setVarMode('selecionar'); carregarVariaveis() }} />
            Selecionar variáveis
          </label>
        </div>
        {varMode === 'selecionar' && (
          <div className={styles.varList}>
            <div className={styles.varActions}>
              <button onClick={() => setVarSel([...variaveis])}>Marcar todas</button>
              <button onClick={() => setVarSel([])}>Desmarcar</button>
            </div>
            <div className={styles.varScroll}>
              {variaveis.map(v => (
                <label key={v} className={styles.varItem}>
                  <input type="checkbox" checked={varSelecionadas.includes(v)} onChange={() => toggleVar(v)} />
                  {v}
                </label>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Agregações */}
      <div className={styles.section}>
        <div className={styles.groupLabel}>Agregações Customizadas</div>
        <div className={styles.agrBuilder}>
          <div className={styles.agrRow}>
            <input value={agrOrigem} onChange={e => setAgrOrigem(e.target.value)} placeholder="Variável origem (ex: ph)" />
            <select value={agrFunc} onChange={e => setAgrFunc(e.target.value)}>
              {['max','min','mean','sum','count'].map(f => <option key={f}>{f}</option>)}
            </select>
          </div>
          <input value={agrNome} onChange={e => setAgrNome(e.target.value)} placeholder="Nome de saída (ex: ph_max)" style={{ marginBottom: 4 }} />
          <button onClick={adicionarAgregacao}>+ Adicionar agregação</button>
        </div>
        <div className={styles.field}>
          <label>Lista (origem:func:nome)</label>
          <textarea value={agregacoes} onChange={e => setAgregacoes(e.target.value)} rows={3} placeholder="creatinina:max:creatinina_max" />
        </div>
      </div>

      {erro && <div className={styles.erro}>{erro}</div>}

      <button className={styles.execBtn} onClick={executar} disabled={executando}>
        {executando
          ? <><span className={styles.spinner} /> Executando...</>
          : '▶ Executar Transformação'}
      </button>

      <p className={styles.hint}>Frontend React → API Flask (5050)<br />→ Motor Python (Bloco 2)</p>
    </aside>
  )
}

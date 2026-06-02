import { useState } from 'react'
import Sidebar from './components/Sidebar'
import Resultado from './pages/Resultado'
import Validacao from './pages/Validacao'
import JsonViewer from './pages/JsonViewer'
import styles from './App.module.css'

export default function App() {
  const [estado, setEstado] = useState(null)
  const [aba, setAba] = useState('resultado')
  const [executando, setExecutando] = useState(false)

  return (
    <div className={styles.shell}>
      <Sidebar
        executando={executando}
        setExecutando={setExecutando}
        onResultado={(data) => { setEstado(data); setAba('resultado') }}
      />
      <div className={styles.main}>
        {/* Topbar */}
        <div className={styles.topbar}>
          <div className={styles.pipeline}>
            <span className={styles.step}>Entradas CSV</span>
            <span className={styles.arrow}>→</span>
            <span className={styles.step}>Adaptador JSON</span>
            <span className={styles.arrow}>→</span>
            <span className={`${styles.step} ${styles.stepActive}`}>Bloco 2</span>
            <span className={styles.arrow}>→</span>
            <span className={styles.step}>Saída</span>
            <span className={styles.arrow}>→</span>
            <span className={styles.step}>Validação</span>
          </div>
          <span className={`${styles.badge} ${executando ? styles.badgeRunning : estado ? styles.badgeOk : styles.badgeIdle}`}>
            {executando ? 'Transformando...' : estado ? `${estado.n_pacientes} paciente(s)` : 'Aguardando execução'}
          </span>
        </div>

        {/* Conteúdo */}
        <div className={styles.content}>
          {!estado && !executando && (
            <div className={styles.empty}>
              <div className={styles.emptyIcon}>⚗️</div>
              <p>Configure os parâmetros e clique em <strong>Executar Transformação</strong></p>
              <p className={styles.emptyHint}>Certifique-se de que a API está rodando: <code>python app/api.py</code></p>
            </div>
          )}

          {estado && (
            <>
              <div className={styles.tabs}>
                {['resultado', 'validacao', 'json'].map(t => (
                  <button
                    key={t}
                    className={`${styles.tab} ${aba === t ? styles.tabActive : ''}`}
                    onClick={() => setAba(t)}
                  >
                    {t === 'resultado' ? '📊 Resultado' : t === 'validacao' ? '✓ Validação' : '{ } JSON'}
                  </button>
                ))}
              </div>

              {aba === 'resultado' && <Resultado estado={estado} />}
              {aba === 'validacao' && <Validacao estado={estado} />}
              {aba === 'json' && <JsonViewer estado={estado} />}
            </>
          )}
        </div>
      </div>
    </div>
  )
}

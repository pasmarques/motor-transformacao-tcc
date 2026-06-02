# Prompt para Claude Design — Figuras de Arquitetura do TCC

---

## CONTEXTO GERAL

Estou desenvolvendo um TCC sobre um pipeline de transformação de dados clínicos do MIMIC-IV.
A solução tem dois blocos:

- **Bloco 1 — Extração e Geração de Janelas**: extrai dados do MIMIC-IV (PostgreSQL),
  fatia a internação em janelas temporais e gera um JSON padronizado por paciente.
- **Bloco 2 — Motor de Transformação (ETL)**: recebe o JSON, aplica regras de agregação
  e cálculo clínico por módulo, e devolve um dataset com features transformadas.

O **protótipo implementado no TCC** cobre o Bloco 2 completo, com interface web, API REST,
painel administrativo, sistema de plugins e deploy via Docker. O Bloco 1 existe na arquitetura
conceitual mas não foi implementado neste TCC.

---

## FIGURA 1 — ARQUITETURA COMPLETA DA SOLUÇÃO (proposta)

### Objetivo
Mostrar a visão completa da solução de ponta a ponta, incluindo Bloco 1, Bloco 2,
interfaces web, processamento assíncrono e integração com sistemas externos.
O que está fora do escopo do protótipo deve ser marcado visualmente como "proposta".

### Elementos obrigatórios

**Fonte de dados:**
- MIMIC-IV (PostgreSQL v2.2)
- Módulo `hosp`: patients, admissions, icustays
- Módulo `icu`: chartevents, inputevents, outputevents, ingredientevents, d_items

**Bloco 1 — Extração e Geração de Janelas (proposta, não implementado):**
- Seleção de coorte (filtro por tempo mínimo de UTI)
- Extração via SQL paramétrico
- Fatiamento em janelas temporais configuráveis (ex: 24h)
- Montagem do JSON por paciente
- Saída: JSON padronizado (contrato entre blocos)

**Contrato JSON** (bloco de ligação entre Bloco 1 e Bloco 2):
- Perfil do paciente (não longitudinal): id, sexo, idade, peso, altura, IMC
- Dados de internação (não longitudinal): admissão, alta, óbito
- Mapas diários por janela (longitudinal): laboratório, sinais vitais, nutrição,
  ventilação, drogas, balanço hídrico, evacuação, hemodiálise
- Mostrar seta alternativa de "upload direto de JSON" que bypassa o Bloco 1

**Camada de processamento assíncrono (proposta — marcada com borda tracejada):**
- Fila de jobs (ex: Celery + Redis)
- Worker assíncrono que executa Bloco 1 e/ou Bloco 2 em background
- API retorna job_id imediatamente; interface consulta status periodicamente

**Bloco 2 — Motor ETL (IMPLEMENTADO — destaque visual):**
- Orquestrador ETL: resolve dependências entre módulos, aplica config de janelas
- Módulos core: Perfil · Internação · Laboratório · Sinais Vitais · Balanço Hídrico ·
  Nutrição · Ventilação Mecânica · Drogas Vasoativas · Evacuação · Hemodiálise · Categorias
- Sistema de plugins: pasta plugins/ com auto-descoberta de módulos externos (.py)
- Regras clínicas externalizadas: regras.json (limiares configuráveis sem alterar código)
- Saída: DataFrame com features transformadas → CSV / JSON

**Camada de interface (IMPLEMENTADO):**
- User Panel (React SPA) — interface da professora: configura parâmetros, executa, visualiza
- Admin Panel (React SPA, protegido por JWT) — upload de plugins, edição de regras, reload
- API REST (Flask + Gunicorn) — endpoints públicos e endpoints admin protegidos

**Integração externa:**
- Interface própria da professora chama diretamente POST /api/transform (sem frontend)
- Outros pesquisadores acessam via User Panel

**Infraestrutura de deploy (IMPLEMENTADO):**
- Docker Compose: 4 containers (motor-api, user-panel, admin-panel, nginx)
- Nginx: HTTPS, rate limiting, proxy reverso

### Estilo visual
- Fluxo horizontal esquerda → direita: Fonte → Bloco 1 → JSON → Bloco 2 → Saída
- Bloco 2 com borda mais grossa e cor de destaque (implementado)
- Processamento assíncrono com borda tracejada (proposta)
- Seta tracejada para upload direto de JSON
- Paleta: fundo branco, azul escuro (#1F3864) para blocos principais,
  cinza (#D9D9D9) para módulos internos, verde (#375623) para o que foi implementado

---

## FIGURA 2 — ARQUITETURA DO PROTÓTIPO IMPLEMENTADO (escopo do TCC)

### Objetivo
Mostrar com precisão técnica o que foi realmente construído e entregue no TCC.
Foco no Bloco 2 completo: desde a entrada dos dados até o deploy em produção.

### Elementos obrigatórios

**1. Camada de Dados de Entrada (duas rotas):**
- Rota A: CSVs de mapas diários (pasta entradas/) → Adaptador JSON (mapas_json.py) → JSON padronizado
- Rota B: JSON direto (upload ou chamada externa) → entra direto no Motor ETL
- Mostrar as duas rotas com setas distintas chegando no Motor

**2. Camada de Apresentação:**
- User Panel (React + Vite): parâmetros de execução, visualização de resultado,
  download CSV/JSON, visualizador de JSON do paciente, relatório de validação
- Admin Panel (React + Vite, protegido por JWT): upload de plugins Python,
  editor de regras clínicas (regras.json), dashboard de status, reload do motor
- Acesso: User Panel em /, Admin Panel em /painel/

**3. Camada de Aplicação — API REST (Flask + Gunicorn):**
- Endpoints públicos: POST /api/transform, GET /api/variaveis, GET /api/plugins, GET /api/regras
- Endpoints admin (JWT): POST /admin/plugins/upload, DELETE /admin/plugins/<nome>,
  POST /admin/reload, PUT /admin/regras, GET /admin/status
- Autenticação: POST /auth/login, POST /auth/refresh, POST /auth/logout
- Instância global do JsonTransformador (recarregada pelo /admin/reload)

**4. Camada de Processamento — Motor ETL (Bloco 2):**
- JsonTransformador: carrega regras.json, descobre plugins, instancia módulos
- Orquestrador ETL: executa módulos em ordem, resolve dependências via requires/provides,
  aplica configuração de janelas (cortar janelas finais, max janelas, data referência)
- Módulos core (11):
  - Perfil: cSexo, cFaixaEtaria, cFaixaIMC
  - Internação: cDiasEmUTI, cDesfechoEmUTI
  - Laboratório: 23 variáveis (ureia, creatinina, pH, sódio, etc.) — limiares via regras.json
  - Sinais Vitais: temperatura, HGT, PAS, PAD, PAM — limiares via regras.json
  - Balanço Hídrico: tendência 72h, sinal do período, proporção dias positivo
  - Nutrição: médias kcal/g por período, jejum, início da nutrição
  - Ventilação Mecânica: proporção de dias, início, desmame, reintubação
  - Drogas Vasoativas: noradrenalina por faixa, vasopressina — limiares via regras.json
  - Evacuação: frequência de diarreia
  - Hemodiálise: proporção de dias
  - Categorias: versões categorizadas (escala 0-4) de todas as variáveis nProp,
    daysinICU_category
- Sistema de plugins: pasta etl_motor/plugins/, plugin_loader.py auto-descobre
  subclasses de BaseModule, instancia e injeta após módulos core
- regras.json: limiares clínicos externalizados (laboratório, sinais vitais, drogas)

**5. Componente de Validação:**
- Comparação com CSV de referência da professora
- Relatório: colunas iguais / divergentes / ausentes / extras
- Saída: métricas numéricas + diagnóstico categorizado

**6. Infraestrutura de Deploy:**
- Docker Compose: motor-api (Flask+Gunicorn, 4 workers), user-panel (React+Nginx),
  admin-panel (React+Nginx), nginx (proxy reverso)
- Nginx: HTTPS com certificado SSL, rate limiting (30r/min API, 5r/min auth),
  roteamento: / → user-panel, /painel/ → admin-panel, /api/* → motor-api
- Volumes persistidos: plugins/, regras.json, entradas/, .admin_hash

### Especificações de cada módulo
Cada módulo deve ter anotação pequena:
- **Requer**: variáveis que precisa de módulos anteriores (ex: Laboratório requer cSexo)
- **Produz**: exemplo de variáveis geradas (ex: nPropDiasUreiaHiper, cFreqASTHiper)

### Estilo visual
- Mesmo padrão visual da Figura 1
- Organização em camadas horizontais (Dados → Apresentação → API → Motor → Saída)
- Módulos como caixas menores dentro do retângulo "Motor ETL"
- Setas numeradas indicando ordem de execução dos módulos
- Cor diferente para plugins (extensível) vs módulos core (fixos)
- Destaque para regras.json como componente externo injetado nos módulos
- Legenda no rodapé: "→ fluxo de dados", "--→ rota alternativa", "[ ] módulo core",
  "[ ] extensível via plugin", "[ ] configurável via regras.json"

---

## INSTRUÇÕES FINAIS PARA O DESIGNER

### Formato e editabilidade
- **OBRIGATÓRIO: gerar em formato PPTX (.pptx)**. Cada figura em um slide separado.
- Todos os elementos devem ser formas nativas do PowerPoint (retângulos, setas, caixas de texto)
  — NUNCA imagens embutidas, NUNCA SVG colado como imagem, NUNCA grupos bloqueados.
- Cada elemento deve ser independente e editável diretamente no PowerPoint ou Google Slides.

### Padrão visual acadêmico
- **Fundo branco** em todos os slides — sem gradientes, sem cores vibrantes de fundo.
- **Paleta sóbria**: azul escuro (#1F3864) para blocos principais, cinza médio (#595959)
  para componentes internos, cinza claro (#D9D9D9) para fundos de módulos, preto para texto.
  Verde escuro (#375623) para componentes implementados, cinza tracejado para propostos.
- **Sem sombras, sem efeitos 3D, sem reflexos** — visual flat e limpo.
- **Tipografia**: Calibri ou Arial, mínimo 10pt para rótulos secundários, 12pt para textos
  principais, 14–16pt negrito para títulos de blocos.
- **Setas simples**, linha fina (1–1.5pt), retas ou com ângulo de 90°.
- **Alinhamento rigoroso** em grade — nenhuma caixa deslocada, nenhum texto cortado.
- **Sem emojis**, sem ícones, sem clip-art — apenas formas geométricas.
- Legenda obrigatória no rodapé explicando os símbolos.
- Prontas para inserção direta em documento ABNT sem retoques.

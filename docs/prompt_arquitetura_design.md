# Prompt para Claude Design — Figuras de Arquitetura do TCC

---

## CONTEXTO GERAL

Estou desenvolvendo um TCC sobre um pipeline de transformação de dados clínicos do MIMIC-IV.
A solução tem dois blocos principais:

- **Bloco 1 — Extração e Geração de Janelas**: extrai dados de uma fonte clínica estruturada,
  fatia a internação em janelas temporais e gera um JSON padronizado por paciente.
- **Bloco 2 — Motor de Transformação (ETL)**: recebe o JSON padronizado, aplica regras de
  agregação e cálculo clínico por módulo, e devolve um dataset com features transformadas.

**Princípio central da proposta: agnóstico de fonte de dados.**
O Motor (Bloco 2) não depende do MIMIC-IV nem de qualquer banco específico.
Ele opera sobre um contrato JSON padronizado que pode ser gerado por qualquer sistema
de extração — MIMIC-IV, outros bancos hospitalares, ou até planilhas manuais.
O protótipo foi implementado com dados do MIMIC-IV apenas como caso de uso de pesquisa,
mas a arquitetura é genérica e reutilizável.

---

## FIGURA 1 — ARQUITETURA FUNCIONAL COMPLETA (proposta genérica)

### Objetivo
Mostrar a visão completa da solução de ponta a ponta como uma proposta genérica,
misturando a arquitetura geral enviada pela professora com a arquitetura MIMIC-IV
desenvolvida pelo aluno. Deve deixar claro:
1. Que a solução é **agnóstica de fonte de dados** — qualquer banco clínico pode alimentar o Bloco 1
2. Que o usuário pode **pular o Bloco 1 completamente** se já tiver os dados no formato JSON
3. Que o MIMIC-IV é apenas o caso de uso implementado no protótipo, não uma dependência arquitetural

### Elementos obrigatórios

**Fontes de dados (lado esquerdo — genérico):**
- Caixa genérica: "Fonte de Dados Clínicos" com exemplos entre parênteses:
  (ex: MIMIC-IV, bancos hospitalares, sistemas EHR)
- Representar que qualquer fonte estruturada pode ser usada

**Bloco 1 — Extração e Geração de Janelas (proposta, não implementado no protótipo):**
- Label: "Bloco 1 — Extração e Janelamento" com marcação visual de "proposta"
- Componentes internos:
  - Seleção de coorte (filtros configuráveis)
  - Extração parametrizada (SQL ou API)
  - Fatiamento em janelas temporais configuráveis
  - Montagem do JSON por paciente
- Saída: JSON padronizado

**Rota alternativa — entrada direta (DESTAQUE OBRIGATÓRIO):**
- Seta tracejada larga e bem visível com label: "Entrada direta (usuário já possui dados extraídos)"
- Essa seta bypassa o Bloco 1 completamente e chega diretamente no Contrato JSON
- Explicação visual clara: o usuário que já extraiu os dados de outra forma
  pode fornecer o JSON diretamente ao Motor, sem precisar do Bloco 1

**Contrato JSON (bloco central de ligação):**
- Representar como um bloco de destaque entre Bloco 1 e Bloco 2
- Label: "Contrato JSON Padronizado"
- Conteúdo resumido:
  - Perfil do paciente (não longitudinal)
  - Dados de internação (não longitudinal)
  - Mapas diários por janela (longitudinal): laboratório, sinais vitais,
    nutrição, ventilação, drogas, balanço hídrico, evacuação, hemodiálise
- Nota: "independente da fonte de dados"

**Camada de processamento assíncrono (proposta — borda tracejada):**
- Label: "Processamento Assíncrono (proposta)"
- Fila de jobs + Worker em background
- API retorna job_id imediatamente
- Interface consulta status periodicamente
- Marcação visual distinta indicando que está fora do escopo do protótipo

**Bloco 2 — Motor ETL (IMPLEMENTADO — destaque visual forte):**
- Label: "Bloco 2 — Motor de Transformação" com badge "Protótipo Implementado"
- Componentes:
  - Orquestrador ETL (resolve dependências entre módulos)
  - Módulos core: Perfil · Internação · Laboratório · Sinais Vitais ·
    Balanço Hídrico · Nutrição · Ventilação · Drogas Vasoativas ·
    Evacuação · Hemodiálise · Categorias
  - Sistema de plugins: módulos externos (.py) carregados automaticamente
  - Regras clínicas configuráveis (regras.json — sem alterar código)
- Saída: Dataset transformado (CSV / JSON)

**Interfaces (IMPLEMENTADO):**
- User Panel (React) — interface do pesquisador/usuário
- Admin Panel (React, JWT) — gestão de plugins e regras
- API REST (Flask + Gunicorn) — ponto de integração com sistemas externos
- Nota: "interface da professora pode chamar diretamente a API"

**Infraestrutura de deploy (IMPLEMENTADO):**
- Docker Compose + Nginx (HTTPS, rate limiting)

### Estilo visual
- Fluxo horizontal esquerda → direita
- Bloco 2 com borda mais grossa e cor verde escuro (implementado)
- Bloco 1 e processamento assíncrono com borda tracejada (proposta)
- Seta de entrada direta em destaque — mais espessa, cor diferente, label bem visível
- Paleta: fundo branco, azul escuro (#1F3864) para blocos principais,
  verde (#375623) para implementado, cinza (#A6A6A6) para proposto

---

## FIGURA 2 — ARQUITETURA TÉCNICA DO PROTÓTIPO IMPLEMENTADO

### Objetivo
Mostrar com precisão técnica o que foi construído e entregue no TCC.
Deve alinhar a arquitetura desenvolvida com o modelo geral da professora,
especificando entradas e saídas de cada bloco e o fluxo de execução interno.
Mostrar os dois blocos (mesmo que Bloco 1 seja representado como "externo/existente")
e a interação entre eles via contrato JSON.

### Elementos obrigatórios

**Bloco 1 — Representação simplificada (externo ao protótipo):**
- Caixa cinza com label: "Bloco 1 — Extração (fora do escopo)"
- Sub-caixas: CSVs de mapas diários (entradas/) + Adaptador JSON (mapas_json.py)
- Saída: JSON padronizado por paciente
- Nota: "no protótipo, o Bloco 1 é simulado via CSVs e adaptador"
- Rota alternativa: seta tracejada "JSON direto (upload ou chamada externa)"

**Contrato JSON (bloco de ligação):**
- Estrutura resumida com os campos principais
- Seta chegando do Bloco 1 e seta alternativa de entrada direta

**Bloco 2 — Motor ETL (detalhado):**

  *Entrada:*
  - JSON padronizado (via Bloco 1 ou direto)

  *JsonTransformador:*
  - Carrega regras.json ao inicializar
  - Descobre plugins automaticamente (plugin_loader.py)
  - Instancia módulos core + plugins
  - Injeta regras nos módulos correspondentes

  *Orquestrador ETL:*
  - Executa módulos em ordem respeitando dependências (requires → provides)
  - Aplica configuração de janelas (cortar finais, máximo, data referência)
  - Acumula features no PatientContext entre módulos

  *Módulos core (mostrar em grid com requer/produz):*
  - **Perfil** | Requer: dados do paciente | Produz: cSexo, cFaixaEtaria, cFaixaIMC
  - **Internação** | Requer: datas de admissão/alta | Produz: cDiasEmUTI, cDesfechoEmUTI
  - **Laboratório** | Requer: cSexo, janelas | Produz: nPropDiasUreiaHiper, cFreqASTHiper, ...
  - **Sinais Vitais** | Requer: janelas | Produz: nPropDiasTempCorpElevada, nPropDiasPAMHipo, ...
  - **Balanço Hídrico** | Requer: eventos BH | Produz: cTendenciaBH72h, cSinalSomaBHPeriodo, ...
  - **Nutrição** | Requer: janelas | Produz: nMediaKcalKgDia, nPropDiasJejumTotal, ...
  - **Ventilação** | Requer: janelas | Produz: nPropDiasVM, cInicioVM, cVMTempoDesmame
  - **Drogas Vasoativas** | Requer: janelas | Produz: nPropDiasSemUsoNora, nPropDiasNoraMax050, ...
  - **Evacuação** | Requer: eventos | Produz: nPropDiasDiarreia, cFreqDiarreia
  - **Hemodiálise** | Requer: janelas | Produz: nPropDiasHemodialise
  - **Categorias** | Requer: todas as nProp | Produz: cPropDias* (escala 0-4), daysinICU_category

  *Sistema de plugins (extensível):*
  - pasta etl_motor/plugins/
  - plugin_loader.py: auto-descobre subclasses de BaseModule
  - Módulos externos seguem mesmo contrato (name, provides, transform)
  - Executados após módulos core

  *regras.json (configurável):*
  - Limiares clínicos externalizados
  - Injetado nos módulos: Laboratório, Sinais Vitais, Drogas Vasoativas
  - Editável sem alterar código

  *Saída:*
  - DataFrame com features transformadas
  - Personalização: seleção de variáveis, agregações customizadas

  *Validação (componente separado):*
  - Comparação com CSV de referência
  - Relatório: colunas iguais / divergentes / ausentes / extras

**Camada de Aplicação — API REST:**
- Endpoints públicos: /api/transform, /api/variaveis, /api/plugins, /api/regras
- Endpoints admin (JWT): /admin/plugins/upload, /admin/reload, /admin/regras
- Autenticação: /auth/login (bcrypt + JWT access 15min + refresh cookie 7d)

**Camada de Apresentação:**
- User Panel (React): parâmetros, execução, tabela de resultado, validação, JSON viewer
- Admin Panel (React + JWT): plugins, regras, dashboard, reload
- Interface externa: professora chama /api/transform diretamente

**Infraestrutura:**
- Docker Compose: motor-api (Gunicorn 4 workers), user-panel, admin-panel, nginx
- Nginx: HTTPS, rate limiting, proxy: / → user-panel, /painel/ → admin-panel, /api/* → motor

### Fluxo de execução (numerado)
1. Usuário configura parâmetros no User Panel ou chama API diretamente
2. API recebe requisição → instancia JsonTransformador com regras e plugins
3. CSVs → Adaptador JSON → JSON padronizado (ou JSON direto)
4. Orquestrador executa módulos em sequência (1→11 + plugins)
5. Cada módulo lê PatientContext, calcula features, adiciona ao contexto
6. Módulo Categorias categoriza todas as variáveis nProp
7. Personalização aplicada (filtro de variáveis + agregações customizadas)
8. Validação contra CSV de referência
9. Resultado retornado via API → exibido no User Panel

### Estilo visual
- Organização em camadas verticais (de cima para baixo) ou horizontal
- Bloco 2 como retângulo grande com módulos em grid interno
- Setas numeradas indicando ordem de execução
- Cor diferente para plugins vs módulos core
- regras.json como componente externo com seta entrando nos 3 módulos relevantes
- Rota alternativa de JSON direto com seta tracejada bem visível
- Legenda: "→ fluxo de dados", "--→ rota alternativa", "[ ] módulo core",
  "[ ] extensível via plugin", "⚙ configurável via regras.json"

---

## INSTRUÇÕES FINAIS PARA O DESIGNER

### Formato e editabilidade
- **OBRIGATÓRIO: gerar em formato PPTX (.pptx)**. Cada figura em um slide separado.
- Todos os elementos devem ser formas nativas do PowerPoint — NUNCA imagens embutidas.
- Cada elemento independente e editável diretamente no PowerPoint ou Google Slides.

### Padrão visual acadêmico
- **Fundo branco** — sem gradientes, sem cores vibrantes de fundo.
- **Paleta sóbria**: azul escuro (#1F3864) para blocos principais, cinza (#595959)
  para componentes internos, cinza claro (#D9D9D9) para fundos de módulos,
  verde escuro (#375623) para implementado, cinza tracejado para proposto.
- **Sem sombras, sem efeitos 3D** — visual flat e limpo.
- **Tipografia**: Calibri ou Arial, mínimo 10pt rótulos, 12pt texto principal, 14–16pt títulos.
- **Setas simples**, linha fina (1–1.5pt), retas ou com ângulo de 90°.
- **Alinhamento rigoroso** em grade — nenhuma caixa deslocada.
- **Sem emojis**, sem ícones decorativos — apenas formas geométricas.
- Legenda obrigatória no rodapé de cada slide.
- Prontas para inserção direta em documento ABNT sem retoques.

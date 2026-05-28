# Prompt para Claude Design — Figuras de Arquitetura do TCC

---

## CONTEXTO GERAL

Estou desenvolvendo um TCC sobre um pipeline de transformação de dados clínicos do MIMIC-IV.
A solução completa tem dois blocos:

- **Bloco 1 — Extração e Geração de Janelas**: extrai dados do banco MIMIC-IV (PostgreSQL),
  fatia a internação em janelas temporais configuráveis e gera um JSON padronizado por paciente.
- **Bloco 2 — Transformação (Motor ETL)**: recebe o JSON do Bloco 1, aplica regras de
  agregação e cálculo clínico por variável, e devolve um dataset com features transformadas.

O **protótipo implementado** cobre apenas o Bloco 2 (motor de transformação). O Bloco 1
existe na arquitetura conceitual mas não foi implementado neste TCC.

O contrato entre os blocos é um **JSON padronizado** com a seguinte estrutura:
- Perfil do paciente: id, sexo, idade, peso, altura, IMC (não longitudinal)
- Internação: data de admissão, alta, óbito (não longitudinal)
- Configuração de janelas: tamanho da janela (horas), dias de internamento, data de referência
- Mapas diários: séries longitudinais de condição clínica, exames laboratoriais, nutrição — uma
  entrada por janela de 24h

O Bloco 2 **pode receber o JSON diretamente** — sem passar pelo Bloco 1 — caso o usuário
já tenha o JSON gerado por outra fonte (ex: upload direto na interface).

---

## FIGURA 1 — FIGURA FUNCIONAL (visão completa da solução)

### Objetivo
Mostrar a solução inteira de ponta a ponta, incluindo Bloco 1 e Bloco 2, mesmo que o
protótipo implemente apenas o Bloco 2. Deve ser uma versão limpa e profissional que mistura
as duas arquiteturas de referência.

### Elementos obrigatórios

**Fonte de dados:**
- MIMIC-IV (PostgreSQL v2.2)
- Dois módulos de tabelas:
  - Módulo `hosp`: patients, admissions, icustays
  - Módulo `icu`: chartevents, inputevents, outputevents, ingredientevents, d_items

**Bloco 1 — Extração e Geração de Janelas:**
- Entrada: MIMIC-IV
- Saída: JSON padronizado (contrato entre blocos)
- Componentes internos:
  - Seleção de coorte (filtro por tempo mínimo de UTI, unidade temporal)
  - Extração via SQL paramétrico
  - Fatiamento em janelas temporais configuráveis (ex: 24h)
  - Montagem do JSON por paciente

**Contrato JSON** (representado como um bloco entre Bloco 1 e Bloco 2):
- Perfil do paciente (não longitudinal)
- Dados de internação (não longitudinal)
- Mapas diários por janela (longitudinal)
- Mostrar que este JSON pode entrar diretamente no Bloco 2 (seta alternativa de "upload direto")

**Bloco 2 — Motor de Transformação (protótipo implementado):**
- Entrada: JSON padronizado
- Saída: Dataset com features transformadas (.csv / .jsonl por paciente)
- Componentes internos (em módulos separados):
  - Módulo Perfil (sexo, idade, IMC, faixa etária)
  - Módulo Internação (dias em UTI, desfecho, início da nutrição/VM)
  - Módulo Laboratório (proporções de dias com valores alterados)
  - Módulo Sinais Vitais (temperatura, PAM, PAS, PAD, HGT)
  - Módulo Balanço Hídrico (tendência, sinal da soma)
  - Módulo Nutrição (calorias, proteínas, jejum)
  - Módulo Ventilação Mecânica (proporção de dias, desmame)
  - Módulo Drogas Vasoativas (noradrenalina, vasopressores)
  - Módulo Evacuação (diarreia, constipação)
  - Módulo Hemodiálise
  - Módulo de Cálculo customizável (importação de .py externo)

**Interface / Camada de apresentação:**
- Frontend Web (React SPA) — configura coorte, janela, regras e dispara execução
- API REST (FastAPI / Flask) — valida, recebe a requisição e responde imediatamente com um `job_id` (não bloqueia)
- Mostrar duas entradas possíveis para o usuário:
  1. Fluxo completo (Bloco 1 → Bloco 2)
  2. Upload direto de JSON → Bloco 2 (bypassa o Bloco 1)

**Camada de processamento assíncrono** (entre a API e os Blocos — parte da proposta, fora do escopo do protótipo):
- Fila de Jobs (ex: Celery + Redis) — a API enfileira o job e retorna imediatamente; o usuário não fica bloqueado esperando
- Worker assíncrono — consome a fila e executa o Bloco 1 e/ou Bloco 2 em background
- A interface consulta o status do job periodicamente até o resultado ficar disponível
- Representar como um componente entre a API e os Blocos, com label "execução assíncrona (proposta)" e marcação visual distinta (ex: borda tracejada ou cor diferente) indicando que está fora do escopo do protótipo implementado

### Estilo visual
- Diagrama horizontal da esquerda para direita: Fonte → Bloco 1 → JSON → Bloco 2 → Saída
- Cada bloco como um retângulo com título em destaque e sub-módulos listados dentro
- Setas com rótulos indicando o tipo de dado trafegado
- Destaque visual (borda diferente, cor ou label) no Bloco 2 indicando "Protótipo implementado"
- Seta tracejada mostrando o caminho alternativo de upload direto do JSON
- Paleta profissional: fundo branco ou cinza muito claro, azul escuro para blocos principais,
  verde ou teal para o JSON/contrato, cinza para componentes internos

---

## FIGURA 2 — FIGURA DA ARQUITETURA (redesenho técnico do Bloco 2)

### Objetivo
Redesenhar a arquitetura técnica que já existe, alinhando-a ao padrão de módulos da solução
completa. Foco no Bloco 2 com entradas, saídas e fluxo interno explícitos. Deve seguir o mesmo
padrão visual da Figura 1 (mesma linguagem gráfica).

### Elementos obrigatórios

**Camadas (de cima para baixo ou da esquerda para direita):**

1. **Camada de Apresentação**
   - Frontend Web (React SPA ou HTML protótipo)
   - Usuário: pesquisador / cientista de dados
   - Ações: selecionar variáveis, definir regras de agregação, configurar janelas,
     fazer upload de JSON ou acionar Bloco 1

2. **Camada de Aplicação**
   - API REST (Flask — protótipo / FastAPI — produção)
   - Endpoints: `/api/transform`, `/api/variaveis`, `/api/paciente_json`
   - Valida configuração, recebe JSON, retorna resultado e relatório de validação

3. **Camada de Processamento — Bloco 2 (Motor ETL)**
   - **Entrada**: JSON padronizado (via API ou upload direto)
   - **Orquestrador**: coordena a execução sequencial dos módulos, resolve dependências
     entre módulos (ex: Perfil antes de Laboratório), aplica configuração de janelas
   - **Módulos** (mostrar como caixas individuais dentro do orquestrador):
     - Perfil · Internação · Laboratório · Sinais Vitais · Balanço Hídrico
     - Nutrição · Ventilação Mecânica · Drogas Vasoativas · Evacuação · Hemodiálise
   - **Personalização**: seleção de variáveis de saída, agregações customizadas,
     importação de módulo externo (.py)
   - **Saída**: DataFrame com features transformadas → CSV / JSON

4. **Entrada de dados (duas rotas):**
   - Rota A: via Bloco 1 (extração do MIMIC-IV) → JSON gerado automaticamente
   - Rota B: upload direto do JSON pelo usuário → entra direto no Motor ETL
   - Mostrar as duas rotas claramente, com setas separadas chegando no Motor

5. **Validação** (componente separado dentro da camada de processamento):
   - Comparação com CSV de referência
   - Relatório: colunas iguais / divergentes / ausentes

### Especificar entradas e saídas de cada módulo
Cada módulo deve ter uma anotação pequena indicando:
- **Requer**: quais variáveis do JSON ele precisa (ex: Laboratório requer `cSexo` do Módulo Perfil)
- **Produz**: quais colunas ele gera no output (ex: `nPropDiasUreiaHiper`, `cFreqASTHiper`)

### Estilo visual
- Mesmo padrão da Figura 1
- Módulos como caixas menores dentro de um retângulo maior (Bloco 2)
- Setas numeradas indicando ordem de execução
- Destacar com uma cor diferente (ex: laranja ou verde) as duas rotas de entrada (A e B)
- Legenda no rodapé: "→ fluxo de dados", "-→ rota alternativa (upload direto)", "[ ] módulo implementado"

---

## INSTRUÇÕES FINAIS PARA O DESIGNER

### Formato e editabilidade
- **OBRIGATÓRIO: gerar em formato PPTX (.pptx)**. Cada figura deve ser um slide separado dentro do mesmo arquivo PPTX.
- Todos os elementos devem ser formas nativas do PowerPoint (caixas de texto, retângulos, setas, conectores) — NUNCA imagens embutidas, NUNCA SVG colado como imagem, NUNCA grupos bloqueados.
- Cada bloco, módulo, seta e rótulo deve ser um objeto independente e editável — o usuário deve conseguir clicar em qualquer elemento e editar texto, cor, tamanho e posição diretamente no PowerPoint ou Google Slides.

### Padrão visual acadêmico
- **Fundo branco** em todos os slides — sem gradientes de fundo, sem cores vibrantes de fundo.
- **Paleta sóbria e consistente**: azul escuro (`#1F3864` ou similar) para blocos principais, cinza médio (`#595959`) para componentes internos, cinza claro (`#D9D9D9`) para fundos de módulos, preto para texto.
- **Sem sombras exageradas**, sem efeitos 3D, sem reflexos — visual flat e limpo.
- **Tipografia**: fonte sem serifa padrão (Calibri ou Arial), tamanho mínimo 10pt para rótulos secundários e 12pt para textos principais. Títulos de blocos em negrito, 14–16pt.
- **Setas simples** com linha fina (1–1.5pt), sem setas decorativas — usar apenas setas retas ou com um ângulo de 90°.
- **Alinhamento rigoroso**: todos os elementos alinhados em grade — nenhuma caixa levemente deslocada, nenhum texto cortado, nenhuma seta que não toca exatamente nas bordas dos blocos.
- **Espaçamento consistente**: mesma margem interna em todas as caixas, mesmo espaço entre blocos.
- **Sem emojis**, sem ícones decorativos, sem clip-art — apenas formas geométricas (retângulos com cantos levemente arredondados são aceitáveis).
- Legenda obrigatória no rodapé de cada slide explicando os símbolos: `→ fluxo de dados`, `--→ rota alternativa`, `[ ] componente implementado`, `[ ] componente proposto`.
- As figuras devem estar prontas para inserção direta em documento Word/ABNT sem necessidade de retoques.

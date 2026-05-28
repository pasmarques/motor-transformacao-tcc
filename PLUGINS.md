# Sistema de Plugins — Motor ETL MIMIC-IV

## Por que isso foi implementado

O motor foi projetado para transformar dados clínicos do MIMIC-IV seguindo um conjunto
fixo de regras definidas pela professora. Porém, à medida que a pesquisa avança, surgem
necessidades de calcular novas variáveis derivadas — escores clínicos, indicadores
compostos, métricas experimentais — sem que isso exija alterar o código do motor central.

A solução foi separar os **módulos core** (estáveis, validados contra a referência SQL)
dos **módulos plugin** (extensíveis, adicionados sem tocar no motor). Assim:

- O motor core permanece estável e auditável
- Novos cálculos são adicionados sem risco de quebrar o que já funciona
- Um erro em um plugin não derruba o motor — ele é ignorado com aviso no log
- A professora ou pesquisadores podem contribuir com módulos sem precisar entender
  a arquitetura interna do motor

---

## Como funciona

Ao iniciar, o `JsonTransformador` chama `descobrir_plugins()`, que escaneia a pasta
`etl_motor/plugins/` em busca de arquivos `.py`. Para cada arquivo encontrado, o loader:

1. Importa o arquivo como módulo Python
2. Inspeciona todas as classes definidas nele
3. Identifica as que herdam de `BaseModule`
4. Instancia e adiciona à lista de módulos do orquestrador

Os plugins são executados **após** todos os módulos core, garantindo que as variáveis
core já estejam disponíveis via `context.features`.

---

## Contrato obrigatório

Todo plugin deve seguir a mesma interface de `BaseModule`:

```python
from etl_motor.base import BaseModule, PatientContext

class MeuModulo(BaseModule):
    name = "nome_unico_do_modulo"       # identificador interno
    provides = ("variavel1", "var2")    # variáveis que este módulo gera

    def transform(self, context: PatientContext) -> dict:
        # context.windows   → DataFrame com as janelas de observação do paciente
        # context.features  → dict com variáveis já calculadas pelos módulos anteriores
        # context.patient   → Series com dados do perfil (sexo, idade, etc.)
        return {
            "variavel1": ...,
            "var2": ...,
        }
```

### Regras importantes

| Regra | Motivo |
|---|---|
| `name` deve ser único | O orquestrador usa o name para identificar o módulo |
| `provides` deve listar todas as chaves retornadas por `transform()` | Necessário para o orquestrador resolver dependências |
| Construtor sem argumentos obrigatórios | O loader instancia com `Classe()` |
| Erros em `transform()` não devem ser silenciados | O orquestrador captura e registra, mas o plugin deve ser robusto |

---

## Como criar um plugin

1. Crie um arquivo `.py` em `etl_motor/plugins/` (ex: `score_sepse.py`)
2. Implemente sua classe herdando de `BaseModule`
3. Reinicie a API (`python app/api.py`)

O motor carrega o plugin automaticamente. As variáveis declaradas em `provides`
aparecem como colunas extras no CSV de saída.

---

## Plugin de exemplo incluído

`etl_motor/plugins/exemplo_escore_carga.py`

Calcula um escore de carga de intervenções intensivas por paciente:

- `nPropDiasCargaAlta` — proporção de dias com 2 ou mais intervenções simultâneas (VM, hemodiálise, noradrenalina)
- `nMaxCargaDia` — máximo de intervenções simultâneas registradas em um único dia

Use este arquivo como ponto de partida para novos módulos.

---

## Regras para plugins (regras.json)

Se o plugin precisar de limiares clínicos configuráveis, declare um `__init__` que
aceite `regras`:

```python
def __init__(self, regras: dict | None = None) -> None:
    self._r = regras or {}
```

E adicione os valores em `regras.json` sob a chave `"plugins"`:

```json
{
  "plugins": {
    "meu_limiar": 10.0
  }
}
```

O loader passa automaticamente `regras["plugins"]` para o construtor do plugin.

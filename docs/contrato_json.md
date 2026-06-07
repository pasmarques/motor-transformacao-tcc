# Contrato JSON do Motor Transformador

Este contrato representa a entrada oficial do Bloco 2. Cada arquivo JSON representa um paciente completo.

## Estrutura principal

```json
{
  "patient_id": 11314855,
  "data_referencia": "2120-12-10T18:14:01",
  "perfil": {
    "gender": "M",
    "anchor_age": 67,
    "pesoadm": 80.0,
    "alturacm": 175.0
  },
  "internacao": {
    "data_admissao_uti": "2120-11-29T18:14:01",
    "data_alta_uti": "2120-12-10T18:14:01",
    "data_obito": null
  },
  "configuracao_processamento": {
    "tamanho_janela_horas": 24,
    "cortar_janelas_finais": 0,
    "max_janelas": null,
    "data_referencia": null
  },
  "mapas_diarios": [
    {
      "janela": 1,
      "inicio": "2120-11-29T18:14:01",
      "fim": "2120-11-30T18:14:01",
      "balanco_hidrico": { "saldo": 450.0 },
      "evacuacao": { "quantidade": 1 },
      "nutricao": {
        "calorias_kcal": 1200.0,
        "proteinas_g": 60.0,
        "calorias_kcal_kg_dia": 15.0,
        "proteinas_g_kg_dia": 0.75
      },
      "drogas_vasoativas": {
        "nora_dose_maxima": 0.0,
        "vasopressina_em_uso": false
      },
      "ventilacao_mecanica": {
        "vm_em_uso": true,
        "desmame_iniciado": false
      },
      "sinais_vitais": {
        "temperatura_maxima": 37.8,
        "pas_media": 118.0,
        "pad_media": 72.0,
        "pam_media": 87.0
      },
      "hgt": { "valor_maximo": 145.0, "valor_minimo": 98.0 },
      "hemodialise": { "em_uso": false },
      "laboratorio": {
        "albumina": 3.2,
        "bilirrubina_total": 0.8,
        "creatinina": 1.1,
        "ureia": 38.0,
        "hemoglobina": 10.5,
        "linfocitos_totais": 1200.0,
        "triglicerides": 180.0,
        "potassio": 4.1,
        "magnesio": 1.9,
        "sodio": 138.0,
        "fosforo": 3.0,
        "ph": 7.38,
        "lactato": 1.4,
        "plaquetas": 210000.0,
        "wbc": 9.5,
        "ast": 32.0,
        "alt": 28.0,
        "fosfatase_alcalina": 85.0
      }
    }
  ]
}
```

## Perfil e internação

`perfil` contém os dados não-longitudinais do paciente necessários para:
- `pesoadm` + `alturacm`: calcular IMC (cFaixaIMC) e normalizar nutrição por kg (nMediaKcalKgDia, nMediaGKgDia)
- `gender`: categorizar sexo (cSexo)
- `anchor_age`: categorizar faixa etária (cFaixaEtaria)

Quando `perfil` é nulo, as variáveis dependentes de peso retornam NaN e não são comparáveis com a base de referência.

`internacao` contém datas de admissão, alta e óbito. Se `data_referencia` estiver
configurada, ela limita o período de observação independentemente da data de alta.

## Adaptador de entradas (fluxo principal)

O contrato é gerado automaticamente por `mapas_json.py` a partir de:

1. `entradas/ICUMapaDiario*.csv` — 30 arquivos, um por variável clínica
2. `ICUpatients21D.csv` — perfil e internação dos pacientes

O adaptador cruza os dois, monta o contrato JSON por paciente e entrega ao
`OrquestradorETL` para transformação.

## Configuração de processamento

| Parâmetro | Tipo | Default | Descrição |
|---|---|---|---|
| `tamanho_janela_horas` | int | 24 | Tamanho de cada janela temporal em horas |
| `cortar_janelas_finais` | int | 0 | Remove N janelas do final para cálculos clínicos |
| `max_janelas` | int\|null | null | Usa apenas as primeiras N janelas |
| `data_referencia` | str\|null | null | Limita o período de observação a uma data |

> `cortar_janelas_finais` é uma decisão de processamento — **não** afeta `nDiasEmUTI`,
> que sempre usa o total de janelas antes do corte.

## Fluxo alternativo (CLI)

Para execução via `main.py --all`, o orquestrador pode receber `ICUNewWindow24.csv`
(janelas consolidadas) diretamente, sem passar pelo adaptador de entradas.
Este modo é mantido para compatibilidade mas não é usado pelo painel React.

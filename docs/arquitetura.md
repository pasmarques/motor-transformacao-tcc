# Arquitetura da Solucao

```mermaid
flowchart LR
    A["MIMIC-IV bruto"] --> B["Bloco 1: Extrator / Padronizador"]
    B --> C["Contrato JSON padronizado"]
    C --> D["Bloco 2: Motor Transformador Modular"]
    D --> E["Tabela final de variaveis"]
    E --> F["Modelo preditivo da pesquisa"]

    B --> B1["Extracao por paciente e periodo"]
    B --> B2["Janela temporal parametrizavel"]
    B --> B3["Limpeza e padronizacao inicial"]
    B --> B4["Geracao de mapas diarios"]

    D --> D1["CLI / Interface simples"]
    D --> D2["Orquestrador"]
    D --> D3["PatientContext"]
    D --> D4["DataCleaner"]
    D --> D5["BaseModule"]

    D2 --> M1["ModuloPerfil"]
    D2 --> M2["ModuloInternacao"]
    D2 --> M3["ModuloBalancoHidrico"]
    D2 --> M4["ModuloEvacuacao"]
    D2 --> M5["ModuloNutricao"]
    D2 --> M6["ModuloLaboratorio"]
    D2 --> M7["ModuloSinaisVitais"]
    D2 --> M8["ModuloVentilacaoMecanica"]
    D2 --> M9["ModuloDrogasVasoativas"]
    D2 --> M10["ModuloHemodialise"]
```

## Escopo do MVP

O MVP implementa o Bloco 2. O Bloco 1 fica descrito na arquitetura completa e
sera responsavel por criar os mapas temporais a partir do MIMIC-IV bruto.

Os modulos do Bloco 2 fazem parte do escopo do MVP. Quando a entrada ainda nao
fornece determinado dominio clinico, o modulo retorna valores neutros de ausencia
de anotacao, mantendo o contrato de saida estavel.

## Interface simples

A interface do MVP deve apenas receber o JSON e os parametros de processamento,
chamar o motor transformador e exibir a saida. As regras clinicas permanecem no
back-end Python.

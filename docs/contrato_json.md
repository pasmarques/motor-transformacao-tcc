# Contrato JSON do Motor Transformador

Este contrato representa a entrada oficial do Bloco 2. Cada arquivo JSON deve
representar um paciente completo.

## Estrutura principal

```json
{
  "patient_id": 11314855,
  "data_referencia": "2120-12-10T18:14:01",
  "perfil": {},
  "internacao": {},
  "configuracao_processamento": {},
  "mapas_diarios": []
}
```

## Dados nao longitudinais

`perfil` contem sexo, idade ou data de nascimento, peso, altura e IMC.

`internacao` contem data de admissao na UTI, data de alta e data de obito.
Alta e obito podem ser nulos. Se `data_referencia` for informada, ela limita
o periodo de observacao. Caso contrario, o motor usa a primeira data disponivel
entre alta e obito.

No adaptador do MVP, quando os mapas diarios nao trazem perfil/internacao, o
JSON pode ser gerado com `perfil` nulo e com `internacao` inferida pelas janelas:
`data_admissao_uti` usa o menor `inicio`, `data_referencia` usa o maior `fim`, e
`data_alta_uti`/`data_obito` ficam nulos. Nesse modo, variaveis de perfil nao
sao comparaveis com a base de amostra.

Opcionalmente, o adaptador aceita uma tabela auxiliar de pacientes para simular
campos que seriam entregues pelo Bloco 1. Essa tabela nao substitui o contrato:
ela apenas preenche `perfil` e `internacao` antes da chamada ao Bloco 2.

## Janelas de observacao

O Bloco 1 deve criar as janelas. O Bloco 2 apenas recebe e respeita essas
janelas.

`configuracao_processamento` aceita:

- `tamanho_janela_horas`: tamanho da janela recebida. No MVP, o padrao e 24.
- `cortar_janelas_finais`: remove N janelas finais.
- `max_janelas`: usa apenas as primeiras N janelas.
- `data_referencia`: limite temporal opcional.

No MVP, como as janelas sao de 24h, cortar uma janela final equivale a remover
aproximadamente um dia. Na arquitetura final, se o Bloco 1 gerar janelas de 12h,
cortar uma janela removera 12h.

## Dados longitudinais

`mapas_diarios` contem os dados organizados por janela. No MVP foram usados:

- `balanco_hidrico.saldo`
- `evacuacao.quantidade`

Novos modulos poderao consumir outros blocos, como nutricao, laboratorio, sinais
vitais, ventilacao mecanica e drogas vasoativas.

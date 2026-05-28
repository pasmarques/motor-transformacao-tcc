from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable
import re
import unicodedata

import numpy as np
import pandas as pd

from etl_motor.config import TransformConfig


METADATA_COLUMNS = (
    "nDiasEmUTI",
    "nJanelasObservadas",
    "tamanhoJanelaHoras",
    "DesfechoEmUTI",
)

VARIAVEIS_SAIDA_PADRAO = (
    "idPaciente",
    "cSexo",
    "cFaixaEtaria",
    "cFaixaIMC",
    "cDiasEmUTI",
    "cDesfechoEmUTI",
    "cInicioNutri",
    "cInicioProteinas",
    "cInicioCalorias",
    "nMediaKcalKgDia",
    "nMediaKcalKgDia_3d",
    "nMediaKcalKgDia_4_7d",
    "nMediaKcalKgDia_7dmais",
    "nMediaGKgDia",
    "nMediaGKgDia_3d",
    "nMediaGKgDia_4_7d",
    "nMediaGKgDia_7dmais",
    "nPropDiasJejumProteina",
    "nQtdeDiasJejumProteina_3d",
    "nQtdeDiasJejumProteina_4_7d",
    "nPropDiasJejumProteina_7dmais",
    "nPropDiasJejumCalorias",
    "nQtdeDiasJejumCalorias_3d",
    "nQtdeDiasJejumCalorias_4_7d",
    "nPropDiasJejumCalorias_7dmais",
    "nPropDiasJejumTotal",
    "nPropDiasTempCorpElevada",
    "cFreqDiarreia",
    "nPropDiasDiarreia",
    "cInicioVM",
    "cVMReintubacao",
    "cVMTempoDesmame",
    "nPropDiasVM",
    "nPropDiasHemodialise",
    "cSinalSomaBHPeriodo",
    "cSinalSomaBH72h",
    "cTendenciaBH72h",
    "cTendenciaBHPeriodo",
    "nPropDiasBHPositivo",
    "nPropDiasHGTHiper",
    "nPropDiasHGTHipo",
    "nPropDiasSemUsoNora",
    "nPropDiasNoraMax025",
    "nPropDiasNoraMax050",
    "nPropDiasNoraMax050Mais",
    "nPropDiasUsoVaso",
    "nPropDiasPASHipo",
    "nPropDiasPASHiper",
    "nPropDiasPADHipo",
    "nPropDiasPADHiper",
    "nPropDiasPAMHipo",
    "nPropDiasPAMHiper",
    "nPropDiasUreiaHiper",
    "nPropDiasCreatininaHiper",
    "nPropDiasLinfoTotaisHipo",
    "nPropDiasHemoglobinaHipo",
    "nPropDiasBilirrubinaHiper",
    "nPropDiasAlbuminaHipo",
    "nPropDiasTrigliceridesHiper",
    "nPropDiasPotassioHiper",
    "nPropDiasPotassioHipo",
    "nPropDiasMagnesioHiper",
    "nPropDiasMagnesioHipo",
    "nPropDiasSodioHiper",
    "nPropDiasSodioHipo",
    "nPropDiasFosforoHipo",
    "cFreqASTHiper",
    "cFreqALTHiper",
    "cFreqFosfatAlcalinaHiper",
    "nPropDiasPHHiper",
    "nPropDiasPHHipo",
    "nPropDiasWBCHipo",
    "nPropDiasWBCHiper",
    "nPropDiasLactatoHiper",
    "nPropDiasPlaquetasHipo",
)

VARIAVEL_PATHS = {
    "saldo_bh": "balanco_hidrico.saldo",
    "balanco_hidrico": "balanco_hidrico.saldo",
    "evacuacao": "evacuacao.quantidade",
    "calorias_kcal": "nutricao.calorias_kcal",
    "proteinas_g": "nutricao.proteinas_g",
    "vm": "ventilacao_mecanica.em_uso",
    "hemodialise": "hemodialise.presente",
    "noradrenalina": "drogas_vasoativas.noradrenalina.dose_maxima",
    "vasopressina": "drogas_vasoativas.vasopressina.em_uso",
    "temperatura": "sinais_vitais.temperatura",
    "hgt": "sinais_vitais.hgt",
    "pas": "sinais_vitais.pas",
    "pad": "sinais_vitais.pad",
    "pam": "sinais_vitais.pam",
    "ph": "laboratorio.ph",
    "ureia": "laboratorio.ureia",
    "creatinina": "laboratorio.creatinina",
    "sodio": "laboratorio.sodio",
    "potassio": "laboratorio.potassio",
    "magnesio": "laboratorio.magnesio",
    "fosforo": "laboratorio.fosforo",
    "albumina": "laboratorio.albumina",
    "linfocitos_totais": "laboratorio.linfocitos_totais",
    "hemoglobina": "laboratorio.hemoglobina",
    "ast": "laboratorio.ast",
    "alt": "laboratorio.alt",
    "bilirrubina": "laboratorio.bilirrubina",
    "triglicerides": "laboratorio.triglicerides",
    "fosfatase_alcalina": "laboratorio.fosfatase_alcalina",
    "wbc": "laboratorio.wbc",
    "plaquetas": "laboratorio.plaquetas",
    "lactato": "laboratorio.lactato",
}


@dataclass(frozen=True)
class AggregationSpec:
    origem: str
    funcao: str
    nome_saida: str


def aplicar_personalizacao(
    resultado: dict[str, Any],
    paciente_json: dict[str, Any],
    config: TransformConfig,
    variaveis_saida: Iterable[str] | None = None,
    agregacoes_customizadas: Iterable[AggregationSpec] | None = None,
) -> dict[str, Any]:
    final = dict(resultado)
    for spec in agregacoes_customizadas or []:
        final[spec.nome_saida] = calcular_agregacao(paciente_json, config, spec)

    if variaveis_saida:
        return filtrar_variaveis(final, variaveis_saida)
    return final


def filtrar_variaveis(
    resultado: dict[str, Any],
    variaveis_saida: Iterable[str],
) -> dict[str, Any]:
    selected = []
    for variable in variaveis_saida:
        variable = variable.strip()
        if variable and variable not in selected:
            selected.append(variable)
    if "idPaciente" not in selected:
        selected.insert(0, "idPaciente")
    return {variable: resultado.get(variable, np.nan) for variable in selected}


def calcular_agregacao(
    paciente_json: dict[str, Any],
    config: TransformConfig,
    spec: AggregationSpec,
) -> float:
    valores = _coletar_valores(paciente_json, config, spec.origem)
    if valores.empty:
        return np.nan

    funcao = _normalizar_funcao(spec.funcao)
    if funcao == "max":
        return float(valores.max())
    if funcao == "min":
        return float(valores.min())
    if funcao == "mean":
        return float(valores.mean())
    if funcao == "sum":
        return float(valores.sum())
    if funcao == "count":
        return float(len(valores))
    raise ValueError(f"Funcao de agregacao invalida: {spec.funcao}")


def parse_agregacao_spec(text: str) -> AggregationSpec:
    parts = [part.strip() for part in re.split(r"[:;]", text, maxsplit=2)]
    if len(parts) < 2:
        raise ValueError(
            "Agregacao deve usar o formato origem:funcao ou origem:funcao:nome_saida."
        )
    origem = parts[0]
    funcao = _normalizar_funcao(parts[1])
    nome_saida = parts[2] if len(parts) == 3 and parts[2] else f"{origem.replace('.', '_')}_{funcao}"
    return AggregationSpec(origem=origem, funcao=funcao, nome_saida=nome_saida)


def parse_variaveis_saida(text: str | None) -> list[str]:
    if not text:
        return []
    return [item.strip() for item in re.split(r"[,\n;]", text) if item.strip()]


def _coletar_valores(
    paciente_json: dict[str, Any],
    config: TransformConfig,
    origem: str,
) -> pd.Series:
    path = VARIAVEL_PATHS.get(origem, origem)
    values: list[Any] = []
    for mapa in _mapas_no_recorte(paciente_json, config):
        value = _get_path(mapa, path)
        values.extend(_flatten(value))
    numeric = pd.to_numeric(pd.Series(values), errors="coerce").dropna()
    return numeric.astype("float64")


def _mapas_no_recorte(
    paciente_json: dict[str, Any],
    config: TransformConfig,
) -> list[dict[str, Any]]:
    mapas = list(paciente_json.get("mapas_diarios") or [])
    mapas.sort(key=lambda item: pd.to_datetime(item.get("inicio"), errors="coerce"))

    reference_time = config.data_referencia_ts
    if reference_time is not None:
        mapas = [
            mapa for mapa in mapas
            if pd.to_datetime(mapa.get("inicio"), errors="coerce") < reference_time
        ]
    if config.max_janelas is not None:
        mapas = mapas[: max(config.max_janelas, 0)]
    if config.cortar_janelas_finais > 0:
        keep = max(len(mapas) - config.cortar_janelas_finais, 0)
        mapas = mapas[:keep]
    return mapas


def _get_path(data: dict[str, Any], path: str) -> Any:
    value: Any = data
    for part in path.split("."):
        if not isinstance(value, dict) or part not in value:
            return None
        value = value[part]
    return value


def _flatten(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        flattened: list[Any] = []
        for item in value:
            flattened.extend(_flatten(item))
        return flattened
    if isinstance(value, tuple):
        return _flatten(list(value))
    if isinstance(value, bool):
        return [int(value)]
    return [value]


def _normalizar_funcao(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value.strip().lower())
    normalized = "".join(char for char in normalized if not unicodedata.combining(char))
    aliases = {
        "max": "max",
        "maximo": "max",
        "min": "min",
        "minimo": "min",
        "media": "mean",
        "mean": "mean",
        "avg": "mean",
        "soma": "sum",
        "sum": "sum",
        "count": "count",
        "contagem": "count",
    }
    if normalized not in aliases:
        raise ValueError(f"Funcao de agregacao invalida: {value}")
    return aliases[normalized]

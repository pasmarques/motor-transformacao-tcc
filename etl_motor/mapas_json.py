from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd

from etl_motor.entrada_maps import _carregar_windows


def converter_entradas_para_jsons(
    base_dir: str | Path,
    entradas_dir: str | Path = "Entradas",
    patient_info_file: str | Path | None = None,
    subject_ids: Iterable[int] | None = None,
) -> list[dict[str, Any]]:
    """Converte os mapas diarios separados em JSONs no contrato do Bloco 2.

    A BASEPACIENTES21D de amostra nao e usada aqui. O arquivo opcional de
    pacientes existe apenas para simular campos que viriam do Bloco 1.
    """
    base = Path(base_dir)
    entradas = _resolve_path(base, entradas_dir)
    windows = _carregar_windows(entradas)

    selected_ids = {int(subject_id) for subject_id in subject_ids or []}
    if selected_ids:
        windows = windows.loc[windows["subject_id"].isin(selected_ids)].copy()

    patient_lookup = _carregar_info_pacientes(base, patient_info_file)
    pacientes_json: list[dict[str, Any]] = []

    for subject_id, group in windows.groupby("subject_id", sort=True):
        patient_id = int(subject_id)
        group = group.sort_values("day").reset_index(drop=True)
        info = patient_lookup.get(patient_id, {})
        pacientes_json.append(_paciente_json(patient_id, group, info))

    return pacientes_json


def salvar_jsons_entradas(
    output_path: str | Path,
    pacientes_json: list[dict[str, Any]],
) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(pacientes_json, ensure_ascii=False, indent=2, allow_nan=False),
        encoding="utf-8",
    )
    return path


def _paciente_json(
    patient_id: int,
    windows: pd.DataFrame,
    info: dict[str, Any],
) -> dict[str, Any]:
    first_start = _datetime_iso(windows["start_time"].iloc[0]) if not windows.empty else None
    last_end = _datetime_iso(windows["end_time"].iloc[-1]) if not windows.empty else None

    perfil = info.get("perfil")
    internacao = dict(info.get("internacao") or {})
    internacao.setdefault("data_admissao_uti", first_start)
    internacao.setdefault("data_alta_uti", None)
    internacao.setdefault("data_obito", None)

    data_referencia = (
        info.get("data_referencia")
        or internacao.get("data_alta_uti")
        or internacao.get("data_obito")
        or last_end
    )

    return {
        "patient_id": patient_id,
        "data_referencia": data_referencia,
        "perfil": perfil,
        "internacao": internacao,
        "configuracao_processamento": {
            "tamanho_janela_horas": 24,
            "cortar_janelas_finais": 0,
            "max_janelas": None,
            "data_referencia": data_referencia,
        },
        "mapas_diarios": [_mapa_diario(row) for _, row in windows.iterrows()],
    }


def _mapa_diario(row: pd.Series) -> dict[str, Any]:
    return {
        "dia": _int_or_none(row.get("day")),
        "inicio": _datetime_iso(row.get("start_time")),
        "fim": _datetime_iso(row.get("end_time")),
        "balanco_hidrico": {
            "saldo": _scalar(row.get("BHDia")),
        },
        "evacuacao": {
            "quantidade": _int_or_zero(row.get("evacuation")),
        },
        "nutricao": {
            "calorias_kcal": _number_or_zero(row.get("calorias_kcal")),
            "proteinas_g": _number_or_zero(row.get("proteinas_g")),
            "calorias_kcal_kg_dia": _number_or_zero(row.get("calorias_kcal_kg_dia")),
            "proteinas_g_kg_dia": _number_or_zero(row.get("proteinas_g_kg_dia")),
        },
        "ventilacao_mecanica": {
            "em_uso": _bool_or_false(row.get("vm_em_uso")),
        },
        "hemodialise": {
            "presente": _bool_or_false(row.get("hemodialise_presente")),
        },
        "drogas_vasoativas": {
            "noradrenalina": {
                "dose_maxima": _number_or_zero(row.get("nora_dose_maxima")),
            },
            "vasopressina": {
                "em_uso": _bool_or_false(row.get("vasopressina_em_uso")),
            },
        },
        "sinais_vitais": {
            "temperatura": _list_values(row.get("temperatura")),
            "hgt": _list_values(row.get("hgt")),
            "pas": _list_values(row.get("pas")),
            "pad": _list_values(row.get("pad")),
            "pam": _list_values(row.get("pam")),
        },
        "laboratorio": {
            "ph": _list_values(row.get("ph")),
            "ureia": _list_values(row.get("ureia")),
            "creatinina": _list_values(row.get("creatinina")),
            "sodio": _list_values(row.get("sodio")),
            "potassio": _list_values(row.get("potassio")),
            "magnesio": _list_values(row.get("magnesio")),
            "fosforo": _list_values(row.get("fosforo")),
            "albumina": _list_values(row.get("albumina")),
            "linfocitos_totais": _list_values(row.get("linfocitos_totais")),
            "hemoglobina": _list_values(row.get("hemoglobina")),
            "ast": _list_values(row.get("ast")),
            "alt": _list_values(row.get("alt")),
            "bilirrubina": _list_values(row.get("bilirrubina")),
            "triglicerides": _list_values(row.get("triglicerides")),
            "fosfatase_alcalina": _list_values(row.get("fosfatase_alcalina")),
            "wbc": _list_values(row.get("wbc")),
            "plaquetas": _list_values(row.get("plaquetas")),
            "lactato": _list_values(row.get("lactato")),
        },
    }


def _carregar_info_pacientes(
    base: Path,
    patient_info_file: str | Path | None,
) -> dict[int, dict[str, Any]]:
    if patient_info_file in (None, ""):
        return {}

    path = _resolve_path(base, patient_info_file)
    patients = pd.read_csv(path)
    return {
        int(row["subject_id"]): _patient_info(row)
        for _, row in patients.iterrows()
        if not _missing(row.get("subject_id"))
    }


def _patient_info(row: pd.Series) -> dict[str, Any]:
    data_alta = _datetime_iso(row.get("outtime"))
    data_obito = _datetime_iso(row.get("deathtime"))
    data_referencia = data_alta or data_obito
    return {
        "data_referencia": data_referencia,
        "perfil": {
            "sexo": _scalar(row.get("gender")),
            "idade": _scalar(row.get("anchor_age")),
            "data_nascimento": None,
            "peso_kg": _scalar(row.get("pesoadm")),
            "altura_cm": _scalar(row.get("alturacm")),
            "imc": None,
        },
        "internacao": {
            "data_admissao_uti": _datetime_iso(row.get("intime")),
            "data_alta_uti": data_alta,
            "data_obito": data_obito,
        },
    }


def _resolve_path(base: Path, path: str | Path) -> Path:
    resolved = Path(path)
    return resolved if resolved.is_absolute() else base / resolved


def _datetime_iso(value: Any) -> str | None:
    if _missing(value):
        return None
    timestamp = pd.to_datetime(str(value).replace(" UTC", ""), errors="coerce")
    if pd.isna(timestamp):
        return None
    return timestamp.isoformat()


def _list_values(value: Any) -> list[Any]:
    if _missing(value):
        return []
    if isinstance(value, list):
        values = value
    elif isinstance(value, tuple):
        values = list(value)
    else:
        values = [value]
    return [_scalar(item) for item in values if not _missing(item)]


def _number_or_zero(value: Any) -> float:
    value = _scalar(value)
    if value is None:
        return 0.0
    numeric = pd.to_numeric(value, errors="coerce")
    return 0.0 if pd.isna(numeric) else float(numeric)


def _int_or_zero(value: Any) -> int:
    value = _scalar(value)
    if value is None:
        return 0
    numeric = pd.to_numeric(value, errors="coerce")
    return 0 if pd.isna(numeric) else int(numeric)


def _int_or_none(value: Any) -> int | None:
    value = _scalar(value)
    if value is None:
        return None
    numeric = pd.to_numeric(value, errors="coerce")
    return None if pd.isna(numeric) else int(numeric)


def _bool_or_false(value: Any) -> bool:
    value = _scalar(value)
    if value is None:
        return False
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "t", "sim", "yes", "y"}
    return bool(value)


def _scalar(value: Any) -> Any:
    if _missing(value):
        return None
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        return float(value)
    if isinstance(value, np.bool_):
        return bool(value)
    return value


def _missing(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, (list, tuple, dict)):
        return False
    try:
        return bool(pd.isna(value))
    except (TypeError, ValueError):
        return False

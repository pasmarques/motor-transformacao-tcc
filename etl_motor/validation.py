from __future__ import annotations

from pathlib import Path
from typing import Iterable

import pandas as pd


NAO_COMPARAVEIS_SEM_PERFIL = {
    "cSexo",
    "cFaixaEtaria",
    "cFaixaIMC",
    "cDesfechoEmUTI",
}

DEPENDENTES_DE_PERFIL = {
    "nMediaKcalKgDia",
    "nMediaKcalKgDia_3d",
    "nMediaKcalKgDia_4_7d",
    "nMediaKcalKgDia_7dmais",
    "nMediaGKgDia",
    "nMediaGKgDia_3d",
    "nMediaGKgDia_4_7d",
    "nMediaGKgDia_7dmais",
    "nPropDiasUreiaHiper",
    "nPropDiasCreatininaHiper",
    "nPropDiasLinfoTotaisHipo",
    "nPropDiasHemoglobinaHipo",
    "nPropDiasTrigliceridesHiper",
    "cFreqASTHiper",
    "cFreqALTHiper",
}

DEPENDENTES_DE_INTERNACAO = {
    "cDiasEmUTI",
    "cInicioNutri",
    "cInicioProteinas",
    "cInicioCalorias",
    "cInicioVM",
    "cVMReintubacao",
    "cVMTempoDesmame",
    "cSinalSomaBHPeriodo",
    "cSinalSomaBH72h",
    "cTendenciaBH72h",
    "cTendenciaBHPeriodo",
}


def comparar_com_referencia(
    df_final: pd.DataFrame,
    reference_path: str | Path,
    ignored_cols: Iterable[str] | None = None,
) -> str:
    expected = pd.read_csv(reference_path)
    ignored = set(ignored_cols or [])
    if "idPaciente" not in expected or "idPaciente" not in df_final:
        return "Comparacao ignorada: coluna idPaciente ausente."

    common_cols = [
        col for col in expected.columns
        if col in df_final.columns and col not in ignored
    ]
    missing_cols = [
        col for col in expected.columns
        if col not in df_final.columns and col not in ignored
    ]
    extra_cols = [col for col in df_final.columns if col not in expected.columns]
    ignored_present = [col for col in expected.columns if col in ignored]

    merged = expected.merge(df_final, on="idPaciente", how="inner", suffixes=("_ref", "_gerado"))
    diff_summary = []
    for col in common_cols:
        if col == "idPaciente":
            continue
        ref = merged[f"{col}_ref"]
        generated = merged[f"{col}_gerado"]

        ref_numeric = pd.to_numeric(ref, errors="coerce")
        generated_numeric = pd.to_numeric(generated, errors="coerce")
        numeric_compare = ref_numeric.notna() | generated_numeric.notna()

        equal = pd.Series(True, index=merged.index)
        if numeric_compare.any():
            equal.loc[numeric_compare] = (
                ref_numeric.loc[numeric_compare].fillna(-999999999).round(1)
                == generated_numeric.loc[numeric_compare].fillna(-999999999).round(1)
            )
        if (~numeric_compare).any():
            equal.loc[~numeric_compare] = (
                ref.loc[~numeric_compare].fillna("").astype(str)
                == generated.loc[~numeric_compare].fillna("").astype(str)
            )

        diff_count = int((~equal).sum())
        if diff_count:
            diff_summary.append((col, diff_count))

    lines = [
        f"Comparacao com referencia: {reference_path}",
        f"Pacientes comparados: {len(merged)}",
        f"Colunas comparadas: {len(common_cols)}",
        f"Colunas esperadas ausentes: {len(missing_cols)}",
        f"Colunas extras geradas: {len(extra_cols)}",
        f"Colunas iguais: {max(len(common_cols) - 1 - len(diff_summary), 0)}",
        f"Colunas com diferenca de valor: {len(diff_summary)}",
    ]
    if ignored_present:
        lines.append("Nao comparaveis neste modo: " + ", ".join(ignored_present))
    if missing_cols:
        lines.append("Ausentes: " + ", ".join(missing_cols[:20]))
    if extra_cols:
        lines.append("Extras: " + ", ".join(extra_cols[:20]))
    if diff_summary:
        top = ", ".join(f"{col} ({count})" for col, count in diff_summary[:20])
        lines.append("Primeiras diferencas: " + top)
        _append_diagnostics(lines, diff_summary, ignored)
    return "\n".join(lines)


def _append_diagnostics(
    lines: list[str],
    diff_summary: list[tuple[str, int]],
    ignored: set[str],
) -> None:
    diff_cols = {col for col, _ in diff_summary}
    perfil = sorted(diff_cols & DEPENDENTES_DE_PERFIL)
    internacao = sorted(diff_cols & DEPENDENTES_DE_INTERNACAO)
    longitudinais = sorted(diff_cols - DEPENDENTES_DE_PERFIL - DEPENDENTES_DE_INTERNACAO)

    if ignored & NAO_COMPARAVEIS_SEM_PERFIL:
        lines.append(
            "Diagnostico: perfil/internacao ausente; variaveis diretas de perfil foram ignoradas."
        )
    if perfil:
        lines.append(
            "Diferencas possivelmente ligadas a perfil/peso/sexo: "
            + ", ".join(perfil[:20])
        )
    if internacao:
        lines.append(
            "Diferencas possivelmente ligadas a recorte/internacao: "
            + ", ".join(internacao[:20])
        )
    if longitudinais:
        lines.append(
            "Diferencas em regras longitudinais a calibrar: "
            + ", ".join(longitudinais[:20])
        )

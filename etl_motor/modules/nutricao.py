from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from etl_motor.base import BaseModule, PatientContext


class ModuloNutricao(BaseModule):
    """Variaveis de calorias, proteinas e jejum."""

    name = "nutricao"
    provides = (
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
    )

    def transform(self, context: PatientContext) -> dict[str, Any]:
        windows = context.windows.copy()
        denominator = max(len(windows), 1)
        weight = pd.to_numeric(context.patient_row.get("pesoadm"), errors="coerce")
        if pd.isna(weight) or weight <= 0:
            weight = np.nan

        kcal = self._numeric_col(windows, "calorias_kcal")
        protein = self._numeric_col(windows, "proteinas_g")
        days = pd.to_numeric(windows.get("day"), errors="coerce") if "day" in windows else pd.Series(dtype=float)

        kcal_kg = self._per_kg_col(windows, "calorias_kcal_kg_dia", kcal, weight)
        protein_kg = self._per_kg_col(windows, "proteinas_g_kg_dia", protein, weight)

        # Alinhado com o SQL da professora: variaveis _4_7d retornam NULL
        # quando daysinICU <= 8. Com cortar_janelas_finais=1, isso equivale
        # a len(windows) <= 7.
        null_4_7d = len(windows) <= 7

        return {
            "cInicioNutri": self._inicio((kcal > 0) | (protein > 0), days),
            "cInicioProteinas": self._inicio(protein > 0, days),
            "cInicioCalorias": self._inicio(kcal > 0, days),
            "nMediaKcalKgDia": self._mean_or_zero(kcal_kg),
            "nMediaKcalKgDia_3d": self._mean_nonzero(kcal_kg, days <= 3, null_if_empty=False),
            "nMediaKcalKgDia_4_7d": np.nan if null_4_7d else self._mean_nonzero(kcal_kg, days.between(4, 7), null_if_empty=False),
            "nMediaKcalKgDia_7dmais": self._mean_nonzero(kcal_kg, days > 7, null_if_empty=len(windows) <= 7),
            "nMediaGKgDia": self._mean_or_zero(protein_kg),
            "nMediaGKgDia_3d": self._mean_nonzero(protein_kg, days <= 3, null_if_empty=False),
            "nMediaGKgDia_4_7d": np.nan if null_4_7d else self._mean_nonzero(protein_kg, days.between(4, 7), null_if_empty=False),
            "nMediaGKgDia_7dmais": self._mean_nonzero(protein_kg, days > 7, null_if_empty=len(windows) <= 7),
            "nPropDiasJejumProteina": float((protein <= 0).sum() / denominator),
            "nQtdeDiasJejumProteina_3d": int(((protein <= 0) & (days <= 3)).sum()),
            "nQtdeDiasJejumProteina_4_7d": np.nan if null_4_7d else self._count_or_nan((protein <= 0) & days.between(4, 7), use_nan=False),
            "nPropDiasJejumProteina_7dmais": self._prop_or_nan((protein <= 0) & (days > 7), max(len(windows) - 7, 1), len(windows) <= 7),
            "nPropDiasJejumCalorias": float((kcal <= 0).sum() / denominator),
            "nQtdeDiasJejumCalorias_3d": int(((kcal <= 0) & (days <= 3)).sum()),
            "nQtdeDiasJejumCalorias_4_7d": np.nan if null_4_7d else self._count_or_nan((kcal <= 0) & days.between(4, 7), use_nan=False),
            "nPropDiasJejumCalorias_7dmais": self._prop_or_nan((kcal <= 0) & (days > 7), max(len(windows) - 7, 1), len(windows) <= 7),
            "nPropDiasJejumTotal": float(((kcal <= 0) & (protein <= 0)).sum() / denominator),
        }

    @staticmethod
    def _numeric_col(windows: pd.DataFrame, column: str) -> pd.Series:
        if column not in windows:
            return pd.Series(0.0, index=windows.index)
        return pd.to_numeric(windows[column], errors="coerce").fillna(0.0)

    @staticmethod
    def _per_kg_col(
        windows: pd.DataFrame,
        column: str,
        fallback: pd.Series,
        weight: float,
    ) -> pd.Series:
        if column in windows:
            values = pd.to_numeric(windows[column], errors="coerce")
            if values.notna().any():
                return values.fillna(0.0)
        if pd.notna(weight) and weight > 0:
            return fallback / weight
        return pd.Series(np.nan, index=fallback.index)

    @staticmethod
    def _inicio(mask: pd.Series, days: pd.Series) -> int:
        if mask.empty or not mask.any():
            return 0
        first_day = days.loc[mask].min()
        if first_day <= 1:
            return 1
        if first_day <= 3:
            return 2
        return 3

    @staticmethod
    def _mean_or_zero(values: pd.Series) -> float:
        mean = values.mean(skipna=True)
        return 0.0 if pd.isna(mean) else float(mean)

    @staticmethod
    def _mean_nonzero(values: pd.Series, mask: pd.Series, null_if_empty: bool) -> float:
        selected = values.loc[mask & values.gt(0)]
        if selected.empty:
            return np.nan if null_if_empty else 0.0
        return float(selected.mean())

    @staticmethod
    def _count_or_nan(mask: pd.Series, use_nan: bool) -> float:
        return np.nan if use_nan else int(mask.sum())

    @staticmethod
    def _prop_or_nan(mask: pd.Series, denominator: int, use_nan: bool) -> float:
        return np.nan if use_nan else float(mask.sum() / denominator)

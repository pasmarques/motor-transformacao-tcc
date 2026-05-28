from __future__ import annotations

from typing import Any

import pandas as pd

from etl_motor.base import BaseModule, PatientContext


class ModuloDrogasVasoativas(BaseModule):
    """Variaveis de noradrenalina e vasopressina."""

    name = "drogas_vasoativas"
    provides = (
        "nPropDiasSemUsoNora",
        "nPropDiasNoraMax025",
        "nPropDiasNoraMax050",
        "nPropDiasNoraMax050Mais",
        "nPropDiasUsoVaso",
    )

    def transform(self, context: PatientContext) -> dict[str, Any]:
        denominator = max(len(context.windows), 1)
        nora = self._numeric_col(context.windows, "nora_dose_maxima")
        vaso = self._bool_col(context.windows, "vasopressina_em_uso")
        nora_use = nora.gt(0)
        return {
            "nPropDiasSemUsoNora": float((~nora_use).sum() / denominator),
            "nPropDiasNoraMax025": float(((nora > 0) & (nora <= 0.25)).sum() / denominator),
            "nPropDiasNoraMax050": float(((nora > 0.25) & (nora <= 0.50)).sum() / denominator),
            "nPropDiasNoraMax050Mais": float((nora > 0.50).sum() / denominator),
            "nPropDiasUsoVaso": float(vaso.sum() / denominator),
        }

    @staticmethod
    def _numeric_col(windows: pd.DataFrame, column: str) -> pd.Series:
        if column not in windows:
            return pd.Series(0.0, index=windows.index)
        return pd.to_numeric(windows[column], errors="coerce").fillna(0.0)

    @staticmethod
    def _bool_col(windows: pd.DataFrame, column: str) -> pd.Series:
        if column not in windows:
            return pd.Series(False, index=windows.index)
        return windows[column].fillna(False).astype(bool)

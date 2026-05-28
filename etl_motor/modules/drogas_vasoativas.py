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

    def __init__(self, regras: dict | None = None) -> None:
        self._r = regras or {}

    def _r_get(self, key: str, default: float) -> float:
        return float(self._r.get(key, default))

    def transform(self, context: PatientContext) -> dict[str, Any]:
        denominator = max(len(context.windows), 1)
        nora = self._numeric_col(context.windows, "nora_dose_maxima")
        vaso = self._bool_col(context.windows, "vasopressina_em_uso")
        nora_use = nora.gt(0)
        f1 = self._r_get("nora_faixa1_upper", 0.25)
        f2 = self._r_get("nora_faixa2_upper", 0.50)
        return {
            "nPropDiasSemUsoNora": float((~nora_use).sum() / denominator),
            "nPropDiasNoraMax025": float(((nora > 0) & (nora <= f1)).sum() / denominator),
            "nPropDiasNoraMax050": float(((nora > f1) & (nora <= f2)).sum() / denominator),
            "nPropDiasNoraMax050Mais": float((nora > f2).sum() / denominator),
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

from __future__ import annotations

from typing import Any

import pandas as pd

from etl_motor.base import BaseModule, PatientContext


class ModuloSinaisVitais(BaseModule):
    """Variaveis de sinais vitais e glicemia capilar por janela."""

    name = "sinais_vitais"
    provides = (
        "nPropDiasTempCorpElevada",
        "nPropDiasHGTHiper",
        "nPropDiasHGTHipo",
        "nPropDiasPASHipo",
        "nPropDiasPASHiper",
        "nPropDiasPADHipo",
        "nPropDiasPADHiper",
        "nPropDiasPAMHipo",
        "nPropDiasPAMHiper",
    )

    def transform(self, context: PatientContext) -> dict[str, Any]:
        denominator = max(len(context.windows), 1)
        return {
            "nPropDiasTempCorpElevada": self._prop_any(context.windows, "temperatura", denominator, lower=None, upper=37.8),
            "nPropDiasHGTHiper": self._prop_any(context.windows, "hgt", denominator, lower=None, upper=180.0),
            "nPropDiasHGTHipo": self._prop_any(context.windows, "hgt", denominator, lower=70.0, upper=None),
            "nPropDiasPASHipo": self._prop_any(context.windows, "pas", denominator, lower=100.0, upper=None),
            "nPropDiasPASHiper": self._prop_any(context.windows, "pas", denominator, lower=None, upper=140.0),
            "nPropDiasPADHipo": self._prop_any(context.windows, "pad", denominator, lower=60.0, upper=None),
            "nPropDiasPADHiper": self._prop_any(context.windows, "pad", denominator, lower=None, upper=90.0),
            "nPropDiasPAMHipo": self._prop_any(context.windows, "pam", denominator, lower=64.0, upper=None),
            "nPropDiasPAMHiper": self._prop_any(context.windows, "pam", denominator, lower=None, upper=64.0),
        }

    @classmethod
    def _prop_any(
        cls,
        windows: pd.DataFrame,
        column: str,
        denominator: int,
        lower: float | None,
        upper: float | None,
    ) -> float:
        if column not in windows:
            return 0.0
        mask = windows[column].map(lambda value: cls._has_value(value, lower=lower, upper=upper))
        return float(mask.sum() / denominator)

    @staticmethod
    def _has_value(value: Any, lower: float | None, upper: float | None) -> bool:
        values = value if isinstance(value, list) else [value]
        numeric = pd.to_numeric(pd.Series(values), errors="coerce").dropna()
        if numeric.empty:
            return False
        if lower is not None:
            return bool(numeric.lt(lower).any())
        if upper is not None:
            return bool(numeric.gt(upper).any())
        return False

from __future__ import annotations

from typing import Any

import pandas as pd

from etl_motor.base import BaseModule, PatientContext


class ModuloInternacao(BaseModule):
    """Variaveis derivadas da permanencia e desfecho em UTI."""

    name = "internacao"
    provides = ("cDiasEmUTI", "cDesfechoEmUTI")

    def transform(self, context: PatientContext) -> dict[str, Any]:
        dias = context.n_observation_days
        return {
            "cDiasEmUTI": self._categoria_dias_uti(dias),
            "cDesfechoEmUTI": self._desfecho(context.patient_row),
        }

    @staticmethod
    def _categoria_dias_uti(dias: float) -> int:
        if pd.isna(dias):
            return 0
        if dias <= 4:
            return 0
        if dias <= 8:
            return 1
        return 2

    @staticmethod
    def _desfecho(patient_row: pd.Series) -> int:
        if pd.notna(patient_row.get("deathtime_clean")):
            return 1
        denouement = pd.to_numeric(patient_row.get("denouement"), errors="coerce")
        return int(denouement) if pd.notna(denouement) and denouement in (0, 1) else 0

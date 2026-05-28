from __future__ import annotations

from typing import Any

import pandas as pd

from etl_motor.base import BaseModule, PatientContext


class ModuloVentilacaoMecanica(BaseModule):
    """Variaveis derivadas do uso de ventilacao mecanica."""

    name = "ventilacao_mecanica"
    provides = ("cInicioVM", "cVMReintubacao", "cVMTempoDesmame", "nPropDiasVM")

    def transform(self, context: PatientContext) -> dict[str, Any]:
        vm = self._bool_col(context.windows, "vm_em_uso")
        days = pd.to_numeric(context.windows.get("day"), errors="coerce") if "day" in context.windows else pd.Series(dtype=float)
        denominator = max(len(context.windows), 1)
        return {
            "cInicioVM": self._inicio(vm, days),
            "cVMReintubacao": self._reintubacao(vm),
            "cVMTempoDesmame": 0 if not vm.any() else 1,
            "nPropDiasVM": float(vm.sum() / denominator),
        }

    @staticmethod
    def _bool_col(windows: pd.DataFrame, column: str) -> pd.Series:
        if column not in windows:
            return pd.Series(False, index=windows.index)
        return windows[column].fillna(False).astype(bool)

    @staticmethod
    def _inicio(mask: pd.Series, days: pd.Series) -> int:
        if mask.empty or not mask.any():
            return 0
        first_day = days.loc[mask].min()
        if first_day <= 1:
            return 1
        if first_day <= 2:
            return 2
        if first_day <= 3:
            return 3
        return 4

    @staticmethod
    def _reintubacao(vm: pd.Series) -> int:
        if vm.empty:
            return 0
        starts = (~vm.shift(fill_value=False)) & vm
        return int(starts.sum() > 1)

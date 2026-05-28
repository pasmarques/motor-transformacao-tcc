"""Plugin de exemplo: Escore de Carga de Intervencoes.

Demonstra como criar um modulo plugin para o motor ETL MIMIC-IV.
Este modulo calcula um escore simples somando a proporcao de dias
em que o paciente usou VM, hemodialise e noradrenalina simultaneamente.

Para usar como base para um plugin real:
1. Copie este arquivo para etl_motor/plugins/seu_modulo.py
2. Renomeie a classe e ajuste name, provides e a logica em transform()
3. Reinicie a API — o motor carrega automaticamente
"""
from __future__ import annotations

from typing import Any

import pandas as pd

from etl_motor.base import BaseModule, PatientContext


class ModuloEscoreCargaIntervencoes(BaseModule):
    """Escore de carga de intervencoes intensivas por janela.

    Conta, para cada janela, quantas das tres intervencoes principais
    estavam ativas (VM, hemodialise, noradrenalina > 0) e calcula
    a proporcao de janelas com carga alta (2 ou 3 intervencoes simultaneas).
    """

    name = "escore_carga_intervencoes"
    provides = (
        "nPropDiasCargaAlta",   # proporcao de dias com >= 2 intervencoes
        "nMaxCargaDia",         # maximo de intervencoes simultaneas em um dia
    )

    def transform(self, context: PatientContext) -> dict[str, Any]:
        windows = context.windows
        denominator = max(len(windows), 1)

        vm = self._col_bool(windows, "vm_em_uso")
        hd = self._col_bool(windows, "hemodialise_presente")
        nora = pd.to_numeric(
            windows["nora_dose_maxima"] if "nora_dose_maxima" in windows else pd.Series(dtype=float),
            errors="coerce",
        ).fillna(0).gt(0)

        # garante que as series tenham o mesmo indice
        carga = vm.astype(int) + hd.astype(int) + nora.reindex(windows.index, fill_value=False).astype(int)

        return {
            "nPropDiasCargaAlta": float((carga >= 2).sum() / denominator),
            "nMaxCargaDia": int(carga.max()) if not carga.empty else 0,
        }

    @staticmethod
    def _col_bool(windows: pd.DataFrame, column: str) -> pd.Series:
        if column not in windows:
            return pd.Series(False, index=windows.index)
        return windows[column].fillna(False).astype(bool)

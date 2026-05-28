from __future__ import annotations

from typing import Any

import pandas as pd

from etl_motor.base import BaseModule, PatientContext


class ModuloHemodialise(BaseModule):
    """Proporcao de janelas com hemodialise."""

    name = "hemodialise"
    provides = ("nPropDiasHemodialise",)

    def transform(self, context: PatientContext) -> dict[str, Any]:
        if "hemodialise_presente" not in context.windows:
            return {"nPropDiasHemodialise": 0.0}
        mask = context.windows["hemodialise_presente"].fillna(False).astype(bool)
        return {"nPropDiasHemodialise": float(mask.sum() / max(len(mask), 1))}

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from etl_motor.base import BaseModule, PatientContext
from etl_motor.cleaning import DataCleaner


class ModuloPerfil(BaseModule):

    name = "perfil"
    provides = ("cSexo", "cFaixaEtaria", "cFaixaIMC")

    def transform(self, context: PatientContext) -> dict[str, Any]:
        row = context.patient_row
        bmi = DataCleaner.calculate_bmi(row.get("pesoadm"), row.get("alturacm"))

        # Quando peso/altura crus nao permitem calculo, usa a faixa ja presente.
        faixa_imc = DataCleaner.categorize_bmi(bmi)
        if pd.isna(faixa_imc) and "IMC_range" in row:
            faixa_imc = pd.to_numeric(row.get("IMC_range"), errors="coerce")

        return {
            "cSexo": DataCleaner.map_sex(row.get("gender")),
            "cFaixaEtaria": DataCleaner.categorize_age(row.get("anchor_age")),
            "cFaixaIMC": int(faixa_imc) if not pd.isna(faixa_imc) else np.nan,
        }

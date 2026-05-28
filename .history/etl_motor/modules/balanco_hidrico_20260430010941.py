from __future__ import annotations

from typing import Any

import pandas as pd

from etl_motor.base import BaseModule, PatientContext
from etl_motor.cleaning import DataCleaner


class ModuloBalancoHidrico(BaseModule):

    name = "balanco_hidrico"
    provides = ("eSinalSomaBHPeriodo",)

    def __init__(self, bh_df: pd.DataFrame) -> None:
        self.bh_df = bh_df.copy()
        self.bh_df["start_time_clean"] = DataCleaner.parse_datetime_series(self.bh_df["start_time"])
        self.bh_df["BHDia_clean"] = DataCleaner.dirty_balance_series_to_float(self.bh_df["BHDia"])

    def transform(self, context: PatientContext) -> dict[str, Any]:
        mask = (
            self.bh_df["subject_id"].eq(context.subject_id)
            & self.bh_df["start_time_clean"].ge(context.start_time)
            & self.bh_df["start_time_clean"].lt(context.cutoff_time)
        )
        values = self.bh_df.loc[mask, "BHDia_clean"].dropna()
        if values.empty:
            return {"eSinalSomaBHPeriodo": 0}

        total = values.sum()
        return {"eSinalSomaBHPeriodo": DataCleaner.signal_from_sum(total)}

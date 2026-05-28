from __future__ import annotations

from typing import Any

import numpy as np

import pandas as pd

from etl_motor.base import BaseModule, PatientContext
from etl_motor.cleaning import DataCleaner


class ModuloBalancoHidrico(BaseModule):
    """Variaveis derivadas do balanco hidrico diario."""

    name = "balanco_hidrico"
    provides = (
        "cSinalSomaBHPeriodo",
        "cSinalSomaBH72h",
        "cTendenciaBH72h",
        "cTendenciaBHPeriodo",
        "nPropDiasBHPositivo",
    )

    TENDENCIA_72H_NEGATIVA = {"00-", "+00", "+0-", "++0", "++-", "+--", "0--"}
    TENDENCIA_72H_POSITIVA = {"+++", "00+", "0++", "--0", "-00", "--+", "-0+", "-++"}
    # "---" foi removido de ESTAVEL: o SQL da professora define estavel como valores
    # IGUAIS E <= 0 (t1==t2==t3 AND t1<=0), o que na pratica cobre apenas "000".
    # Tres dias todos negativos com valores diferentes cai em INDEFINIDA (3).
    TENDENCIA_72H_ESTAVEL = {"000"}

    def __init__(self, bh_df: pd.DataFrame) -> None:
        self.bh_df = bh_df.copy()
        self.bh_df["start_time_clean"] = DataCleaner.parse_datetime_series(self.bh_df["start_time"])
        self.bh_df["BHDia_clean"] = DataCleaner.dirty_balance_series_to_float(self.bh_df["BHDia"])

    def transform(self, context: PatientContext) -> dict[str, Any]:
        cutoff_72h = min(
            context.start_time + pd.Timedelta(hours=72),
            context.cutoff_time,
        )

        return {
            "cSinalSomaBHPeriodo": self._signal_sum_between(
                context=context,
                start_time=context.start_time,
                end_time=context.cutoff_time,
            ),
            "cSinalSomaBH72h": self._signal_sum_between(
                context=context,
                start_time=context.start_time,
                end_time=cutoff_72h,
            ),
            "cTendenciaBH72h": self._trend_first_72h(context),
            "cTendenciaBHPeriodo": self._trend_period(context),
            "nPropDiasBHPositivo": self._prop_positive_between(
                context=context,
                start_time=context.start_time,
                end_time=context.cutoff_time,
            ),
        }

    def _signal_sum_between(
        self,
        context: PatientContext,
        start_time: pd.Timestamp,
        end_time: pd.Timestamp,
    ) -> int:
        """Soma o BH dentro de um intervalo especifico e classifica o sinal."""
        mask = (
            self.bh_df["subject_id"].eq(context.subject_id)
            & self.bh_df["start_time_clean"].ge(start_time)
            & self.bh_df["start_time_clean"].lt(end_time)
        )
        values = self.bh_df.loc[mask, "BHDia_clean"].dropna()
        if values.empty:
            return 0

        total = values.sum()
        return DataCleaner.signal_from_sum(total)

    def _trend_first_72h(self, context: PatientContext) -> int:
        """Classifica a combinacao dos sinais de BH nas 3 primeiras janelas.

        Alinhado com o SQL da professora (ICUFBProporcao):
        - Se qualquer um dos 3 primeiros dias nao tem registro de BH -> retorna 0
          (equivalente a WHEN t1 IS NULL OR t2 IS NULL OR t3 IS NULL THEN 0)
        - "000" (todos zero) -> 0 (Estavel)
        - Combinacoes negativas -> 1; positivas -> 2; demais -> 3 (Indefinida)
        - "---" (todos negativos com valores distintos) -> 3 (Indefinida), NAO estavel
        """
        first_windows = context.windows.sort_values("start_time_clean").head(3)
        if len(first_windows) < 3:
            # Menos de 3 dias -> equivalente a dado ausente -> 0
            return 0

        signs = []
        for _, window in first_windows.iterrows():
            values = self._values_between(
                context=context,
                start_time=window["start_time_clean"],
                end_time=window["end_time_clean"],
            )
            if values.empty:
                # Dia sem registro de BH -> equivalente a NULL no SQL -> retorna 0
                return 0
            signs.append(self._sign_char(float(values.sum())))

        pattern = "".join(signs)
        if pattern in self.TENDENCIA_72H_ESTAVEL:
            return 0
        if pattern in self.TENDENCIA_72H_NEGATIVA:
            return 1
        if pattern in self.TENDENCIA_72H_POSITIVA:
            return 2
        return 3

    def _trend_period(self, context: PatientContext) -> int:
        """Classifica a tendencia do BH no periodo inteiro de observacao."""
        values = self._daily_values_between(
            context=context,
            start_time=context.start_time,
            end_time=context.cutoff_time,
        )
        if len(values) < 3:
            return 0

        if values.lt(0).all():
            return 1
        if values.gt(0).all():
            return 2
        if values.eq(0).all():
            return 3

        trend = self._mann_kendall_direction(values.to_numpy(dtype="float64"))
        if trend < 0:
            return 4
        if trend > 0:
            return 5
        return 6

    def _prop_positive_between(
        self,
        context: PatientContext,
        start_time: pd.Timestamp,
        end_time: pd.Timestamp,
    ) -> float:
        mask = (
            self.bh_df["subject_id"].eq(context.subject_id)
            & self.bh_df["start_time_clean"].ge(start_time)
            & self.bh_df["start_time_clean"].lt(end_time)
        )
        values = self.bh_df.loc[mask, "BHDia_clean"].dropna()
        denominator = max(context.n_observation_windows, 1)
        return float(values.gt(0).sum() / denominator)

    def _values_between(
        self,
        context: PatientContext,
        start_time: pd.Timestamp,
        end_time: pd.Timestamp,
    ) -> pd.Series:
        mask = (
            self.bh_df["subject_id"].eq(context.subject_id)
            & self.bh_df["start_time_clean"].ge(start_time)
            & self.bh_df["start_time_clean"].lt(end_time)
        )
        return self.bh_df.loc[mask, "BHDia_clean"].dropna()

    def _daily_values_between(
        self,
        context: PatientContext,
        start_time: pd.Timestamp,
        end_time: pd.Timestamp,
    ) -> pd.Series:
        values = self.bh_df.loc[
            self.bh_df["subject_id"].eq(context.subject_id)
            & self.bh_df["start_time_clean"].ge(start_time)
            & self.bh_df["start_time_clean"].lt(end_time),
            ["start_time_clean", "BHDia_clean"],
        ].dropna()
        if values.empty:
            return pd.Series(dtype="float64")

        daily_values = (
            values.sort_values("start_time_clean")
            .groupby("start_time_clean", sort=True)["BHDia_clean"]
            .sum()
        )
        return daily_values.astype("float64")

    @staticmethod
    def _sign_char(value: float) -> str:
        if value < 0:
            return "-"
        if value > 0:
            return "+"
        return "0"

    @staticmethod
    def _mann_kendall_direction(values: np.ndarray) -> int:
        statistic = 0
        for index, value in enumerate(values[:-1]):
            statistic += int(np.sign(values[index + 1:] - value).sum())
        if statistic < 0:
            return -1
        if statistic > 0:
            return 1
        return 0

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from etl_motor.base import BaseModule, PatientContext
from etl_motor.cleaning import DataCleaner


class ModuloEvacuacao(BaseModule):
    """Calcula proporcao de dias com diarreia e frequencia por janelas de 24h."""

    name = "evacuacao"
    provides = ("nPropDiasDiarreia", "cFreqDiarreia")
    EVENT_TIME_CANDIDATES = ("charttime", "storetime", "event_time", "start_time")

    def __init__(self, evacuacao_df: pd.DataFrame) -> None:
        self.evacuacao_df = evacuacao_df.copy()
        self.event_time_col = self._detect_event_time_column(self.evacuacao_df)
        if self.event_time_col:
            self.evacuacao_df["event_time_clean"] = DataCleaner.parse_datetime_series(
                self.evacuacao_df[self.event_time_col]
            )

        if "cProp4MaisEvacuacoes" in self.evacuacao_df:
            self.evacuacao_df["prop_4mais_clean"] = DataCleaner.ratio_series_to_unit_interval(
                self.evacuacao_df["cProp4MaisEvacuacoes"]
            )

    def transform(self, context: PatientContext) -> dict[str, Any]:
        if self.event_time_col:
            return self._transform_from_raw_events(context)
        return self._transform_from_aggregated_snapshot(context)

    def _transform_from_raw_events(self, context: PatientContext) -> dict[str, Any]:
        windows = context.windows.copy()
        if windows.empty:
            return {"nPropDiasDiarreia": 0.0, "cFreqDiarreia": 0}

        events = self.evacuacao_df.loc[
            self.evacuacao_df["subject_id"].eq(context.subject_id), "event_time_clean"
        ].dropna()
        events = events[(events >= context.start_time) & (events < context.cutoff_time)]

        counts = self._count_events_by_window(events, windows)
        diarrhea_days = counts >= 4
        prop = float(diarrhea_days.sum() / len(windows)) if len(windows) else 0.0
        freq = self._classify_diarrhea_frequency(diarrhea_days)
        return {"nPropDiasDiarreia": prop, "cFreqDiarreia": freq}

    def _transform_from_aggregated_snapshot(self, context: PatientContext) -> dict[str, Any]:
        row = self.evacuacao_df.loc[self.evacuacao_df["subject_id"].eq(context.subject_id)]
        if row.empty:
            return {"nPropDiasDiarreia": 0.0, "cFreqDiarreia": 0}

        row = row.iloc[0]
        denominator = max(context.n_observation_days, 1)

        # O arquivo atual ja vem agregado por paciente. Usa a proporcao pronta
        # quando ela existe; caso contrario, estima pela contagem categorizada.
        if "prop_4mais_clean" in row.index and not pd.isna(row["prop_4mais_clean"]):
            prop = float(row["prop_4mais_clean"])
        else:
            diarrhea_count = pd.to_numeric(row.get("cPropDiarreiaPeriodo", 0), errors="coerce")
            prop = float(diarrhea_count / denominator) if pd.notna(diarrhea_count) else 0.0
            prop = float(np.clip(prop, 0.0, 1.0))

        freq_raw = pd.to_numeric(row.get("cPropDiarreiaPeriodo", 0), errors="coerce")
        freq = int(np.clip(freq_raw, 0, 3)) if pd.notna(freq_raw) else 0
        return {"nPropDiasDiarreia": prop, "cFreqDiarreia": freq}

    @classmethod
    def _detect_event_time_column(cls, df: pd.DataFrame) -> str | None:
        for col in cls.EVENT_TIME_CANDIDATES:
            if col in df.columns:
                return col
        return None

    @staticmethod
    def _count_events_by_window(events: pd.Series, windows: pd.DataFrame) -> np.ndarray:
        intervals = pd.IntervalIndex.from_arrays(
            windows["start_time_clean"],
            windows["end_time_clean"],
            closed="left",
        )
        positions = intervals.get_indexer(events)
        valid_positions = positions[positions >= 0]
        return np.bincount(valid_positions, minlength=len(windows))

    @staticmethod
    def _classify_diarrhea_frequency(diarrhea_days: np.ndarray) -> int:
        if not diarrhea_days.any():
            return 0

        padded = np.r_[False, diarrhea_days, False]
        starts = np.flatnonzero(~padded[:-1] & padded[1:])
        ends = np.flatnonzero(padded[:-1] & ~padded[1:])
        run_lengths = ends - starts
        long_runs = run_lengths >= 4

        if long_runs.sum() >= 2:
            return 3
        if long_runs.any():
            return 2
        return 1

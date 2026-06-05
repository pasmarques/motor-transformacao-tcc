from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd

from etl_motor.base import BaseModule, PatientContext
from etl_motor.cleaning import DataCleaner
from etl_motor.config import TransformConfig


class OrquestradorETL:
    """Coordena janelas temporais, dependencias e execucao dos modulos."""

    def __init__(
        self,
        patients_df: pd.DataFrame,
        windows_df: pd.DataFrame,
        modules: Iterable[BaseModule],
    ) -> None:
        self.patients_df = patients_df.copy()
        self.windows_df = windows_df.copy()
        self.modules = list(modules)
        self._prepare_core_tables()

    @classmethod
    def from_files(
        cls,
        base_dir: str | Path,
        modules: Iterable[BaseModule],
        patients_file: str = "ICUpatients21D.csv",
        windows_file: str = "ICUNewWindow24.csv",
    ) -> "OrquestradorETL":
        base = Path(base_dir)
        patients_df = pd.read_csv(base / patients_file)
        windows_df = pd.read_csv(base / windows_file)
        return cls(patients_df=patients_df, windows_df=windows_df, modules=modules)

    def transformar_paciente(
        self,
        subject_id: int,
        offset_dias: int | None = 0,
        config: TransformConfig | None = None,
    ) -> dict[str, Any]:
        context = self.criar_contexto(subject_id=subject_id, offset_dias=offset_dias, config=config)

        result: dict[str, Any] = {
            "idPaciente": int(subject_id),
            "nDiasEmUTI": context.dias_internacao,
            "nJanelasObservadas": context.n_observation_windows,
            "tamanhoJanelaHoras": context.window_size_hours,
            "DesfechoEmUTI": self._death_outcome(context.patient_row),
        }

        for module in self.modules:
            module.validate_dependencies(result)
            features = module.transform(context)
            result.update(features)
            context.features.update(features)

        return result

    def transformar_todos(
        self,
        offset_dias: int | None = 0,
        config: TransformConfig | None = None,
    ) -> pd.DataFrame:
        """Transforma todos os pacientes em uma tabela final para modelagem."""
        resultados = [
            self.transformar_paciente(subject_id=int(subject_id), offset_dias=offset_dias, config=config)
            for subject_id in self.patients_df["subject_id"].to_numpy()
        ]
        return pd.DataFrame(resultados)

    def _prepare_core_tables(self) -> None:
        self.patients_df["intime_clean"] = DataCleaner.parse_datetime_series(self.patients_df["intime"])
        self.patients_df["outtime_clean"] = DataCleaner.parse_datetime_series(self.patients_df["outtime"])
        self.patients_df["deathtime_clean"] = DataCleaner.parse_datetime_series(self.patients_df["deathtime"])

        self.windows_df["start_time_clean"] = DataCleaner.parse_datetime_series(self.windows_df["start_time"])
        self.windows_df["end_time_clean"] = DataCleaner.parse_datetime_series(self.windows_df["end_time"])

    def criar_contexto(
        self,
        subject_id: int,
        offset_dias: int | None = 0,
        config: TransformConfig | None = None,
    ) -> PatientContext:
        """Monta o contexto temporal de um paciente para uso dos modulos e debug."""
        config = self._resolve_config(offset_dias=offset_dias, config=config)
        patient_rows = self.patients_df.loc[self.patients_df["subject_id"].eq(subject_id)]
        if patient_rows.empty:
            raise ValueError(f"subject_id nao encontrado: {subject_id}")

        patient_row = patient_rows.iloc[0]
        patient_windows = self.windows_df.loc[self.windows_df["subject_id"].eq(subject_id)].copy()
        patient_windows = patient_windows.sort_values("start_time_clean")

        start_time = patient_row["intime_clean"]
        if pd.isna(start_time) and not patient_windows.empty:
            start_time = patient_windows["start_time_clean"].iloc[0]
        cutoff_time, included_windows, n_total_windows = self._resolve_cutoff(patient_row, patient_windows, config)

        return PatientContext(
            subject_id=subject_id,
            patient_row=patient_row,
            windows=included_windows,
            start_time=start_time,
            cutoff_time=cutoff_time,
            n_observation_windows=len(included_windows),
            n_total_windows=n_total_windows,
            config=config,
        )

    @staticmethod
    def _resolve_cutoff(
        patient_row: pd.Series,
        patient_windows: pd.DataFrame,
        config: TransformConfig,
    ) -> tuple[pd.Timestamp, pd.DataFrame, int]:
        reference_time = config.data_referencia_ts
        if patient_windows.empty:
            cutoff = reference_time if reference_time is not None else patient_row["outtime_clean"]
            return cutoff, patient_windows, 0

        candidate_windows = patient_windows.copy()
        if reference_time is not None:
            candidate_windows = candidate_windows.loc[
                candidate_windows["start_time_clean"].lt(reference_time)
            ].copy()

        if config.max_janelas is not None:
            candidate_windows = candidate_windows.iloc[: max(config.max_janelas, 0)].copy()

        # Total de janelas ANTES do corte final — representa dias reais de internacao
        n_total_windows = len(candidate_windows)

        if config.cortar_janelas_finais > 0:
            keep_windows = max(len(candidate_windows) - config.cortar_janelas_finais, 0)
            candidate_windows = candidate_windows.iloc[:keep_windows].copy()

        included = candidate_windows
        if included.empty:
            cutoff = reference_time if reference_time is not None else patient_windows["start_time_clean"].iloc[0]
        else:
            cutoff = included["end_time_clean"].iloc[-1]
            if reference_time is not None:
                cutoff = min(cutoff, reference_time)
        return cutoff, included, n_total_windows

    @staticmethod
    def _resolve_config(
        offset_dias: int | None,
        config: TransformConfig | None,
    ) -> TransformConfig:
        if config is not None:
            return config
        return TransformConfig.from_legacy_offset(offset_dias or 0)

    @staticmethod
    def _death_outcome(patient_row: pd.Series) -> int:
        deathtime = patient_row.get("deathtime_clean")
        if pd.notna(deathtime):
            return 1
        denouement = pd.to_numeric(patient_row.get("denouement"), errors="coerce")
        return int(denouement) if pd.notna(denouement) and denouement in (0, 1) else 0

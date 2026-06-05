from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from etl_motor.config import TransformConfig


@dataclass
class PatientContext:
    subject_id: int
    patient_row: pd.Series
    windows: pd.DataFrame
    start_time: pd.Timestamp
    cutoff_time: pd.Timestamp
    n_observation_windows: int
    n_total_windows: int
    config: TransformConfig
    features: dict[str, Any] = field(default_factory=dict)

    @property
    def window_size_hours(self) -> float:
        return self.config.tamanho_janela_horas

    @property
    def n_observation_days(self) -> float:
        """Janelas processadas convertidas em dias (afetado por cortar_janelas_finais)."""
        return self.n_observation_windows * (self.window_size_hours / 24.0)

    @property
    def dias_internacao(self) -> float:
        """Dias totais de internacao baseado no total de janelas antes do corte final.

        Representa o tempo real de permanencia na UTI e nao e afetado por
        cortar_janelas_finais, que e uma decisao de processamento, nao um fato clinico.
        """
        return self.n_total_windows * (self.window_size_hours / 24.0)


class BaseModule(ABC):
    name: str = "base"
    provides: tuple[str, ...] = ()
    requires: tuple[str, ...] = ()

    def validate_dependencies(self, features: dict[str, Any]) -> None:
        missing = [f for f in self.requires if f not in features]
        if missing:
            raise ValueError(f"Modulo {self.name} requer variaveis ausentes: {missing}")

    @abstractmethod
    def transform(self, context: PatientContext) -> dict[str, Any]:
        """Executa a transformacao do modulo para um paciente."""

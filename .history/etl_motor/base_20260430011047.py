from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

import pandas as pd


@dataclass
class PatientContext:

    subject_id: int
    patient_row: pd.Series
    windows: pd.DataFrame
    start_time: pd.Timestamp
    cutoff_time: pd.Timestamp
    n_observation_days: int
    features: dict[str, Any] = field(default_factory=dict)


class BaseModule(ABC):
    """Contrato comum para qualquer modulo plug-and-play do motor."""

    name: str = "base"
    provides: tuple[str, ...] = ()
    requires: tuple[str, ...] = ()

    def validate_dependencies(self, features: dict[str, Any]) -> None:
        missing = [field for field in self.requires if field not in features]
        if missing:
            raise ValueError(f"Modulo {self.name} requer variaveis ausentes: {missing}")

    @abstractmethod
    def transform(self, context: PatientContext) -> dict[str, Any]:
        """Executa a transformacao do modulo para um paciente."""

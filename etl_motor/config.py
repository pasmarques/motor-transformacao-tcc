from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd


@dataclass(frozen=True)
class TransformConfig:
    """Configuracao temporal usada pelo bloco transformador."""

    tamanho_janela_horas: float = 24.0
    cortar_janelas_finais: int = 0
    max_janelas: int | None = None
    data_referencia: Any | None = None

    @classmethod
    def from_legacy_offset(cls, offset_dias: int = 0) -> "TransformConfig":
        """
        Converte o parametro antigo em configuracao por janelas.

        offset_dias < 0: remove janelas finais.
        offset_dias > 0: usa apenas as primeiras N janelas.
        offset_dias = 0: usa todas as janelas.
        """
        if offset_dias < 0:
            return cls(cortar_janelas_finais=abs(offset_dias))
        if offset_dias > 0:
            return cls(max_janelas=offset_dias)
        return cls()

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "TransformConfig":
        if not data:
            return cls()
        return cls(
            tamanho_janela_horas=float(data.get("tamanho_janela_horas", 24.0)),
            cortar_janelas_finais=int(data.get("cortar_janelas_finais", 0) or 0),
            max_janelas=cls._optional_int(data.get("max_janelas")),
            data_referencia=data.get("data_referencia"),
        )

    @property
    def data_referencia_ts(self) -> pd.Timestamp | None:
        if self.data_referencia in (None, ""):
            return None
        value = pd.to_datetime(self.data_referencia, errors="coerce")
        return None if pd.isna(value) else value

    @staticmethod
    def _optional_int(value: Any) -> int | None:
        if value in (None, ""):
            return None
        return int(value)

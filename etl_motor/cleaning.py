from __future__ import annotations

import math
import re
from typing import Any

import numpy as np
import pandas as pd


class DataCleaner:
    """Funções utilitárias compartilhadas pelos módulos do motor."""

    _NON_NUMERIC_RE = re.compile(r"[^0-9,\.\-+]")

    @staticmethod
    def parse_datetime_series(series: pd.Series) -> pd.Series:
        """Converte datas do MIMIC para pandas datetime, removendo o sufixo UTC."""
        cleaned = series.astype("string").str.replace(" UTC", "", regex=False)
        return pd.to_datetime(cleaned, errors="coerce")

    @classmethod
    def dirty_balance_to_float(cls, value: Any) -> float:
        """
        Converte strings de balanço hídrico com excesso de pontos em float.

        Exemplo observado: "-10.888.889.346" vira -10.888889346.
        A regra conserva o primeiro ponto como separador decimal e remove os
        pontos seguintes, que aparecem como sujeira na fração do número.
        """
        if pd.isna(value):
            return np.nan

        if isinstance(value, (int, float, np.integer, np.floating)):
            return float(value)

        text = cls._NON_NUMERIC_RE.sub("", str(value).strip())
        if not text:
            return np.nan

        # Formatos com virgula decimal: "1.234,56" ou "1234,56".
        if "," in text:
            text = text.replace(".", "").replace(",", ".")
            return cls._safe_float(text)

        if text.count(".") > 1:
            first_dot = text.find(".")
            text = text[: first_dot + 1] + text[first_dot + 1 :].replace(".", "")

        return cls._safe_float(text)

    @classmethod
    def dirty_balance_series_to_float(cls, series: pd.Series) -> pd.Series:
        """Versão vetorizada para limpar a coluna BHDia."""
        cleaned = series.astype("string").str.strip()
        cleaned = cleaned.str.replace(cls._NON_NUMERIC_RE, "", regex=True)

        comma_mask = cleaned.str.contains(",", regex=False, na=False)
        comma_values = cleaned[comma_mask].str.replace(".", "", regex=False)
        comma_values = comma_values.str.replace(",", ".", regex=False)

        dot_values = cleaned[~comma_mask]
        multi_dot_mask = dot_values.str.count(r"\.").gt(1).fillna(False)

        def keep_first_dot(text: str) -> str:
            first_dot = text.find(".")
            if first_dot == -1:
                return text
            return text[: first_dot + 1] + text[first_dot + 1 :].replace(".", "")

        dot_values.loc[multi_dot_mask] = dot_values.loc[multi_dot_mask].map(keep_first_dot)

        result = pd.Series(index=series.index, dtype="float64")
        result.loc[comma_mask] = pd.to_numeric(comma_values, errors="coerce").astype("float64")
        result.loc[~comma_mask] = pd.to_numeric(dot_values, errors="coerce").astype("float64")
        return result

    @staticmethod
    def ratio_series_to_unit_interval(series: pd.Series) -> pd.Series:
        """
        Normaliza proporções que vieram poluidas do Excel, como 5.833333e+15.

        Aplica somente em colunas que semanticamente ja sao proporcoes.
        """
        values = pd.to_numeric(series, errors="coerce").astype("float64")
        arr = values.to_numpy(copy=True)
        valid = np.isfinite(arr) & (arr > 1)
        powers = np.zeros_like(arr, dtype="float64")
        powers[valid] = np.ceil(np.log10(arr[valid]))
        arr[valid] = arr[valid] / np.power(10.0, powers[valid])
        arr = np.clip(arr, 0.0, 1.0)
        return pd.Series(arr, index=series.index, dtype="float64")

    @staticmethod
    def map_sex(value: Any) -> float:
        """Mapeia sexo para o dominio do PDF: 0 masculino, 1 feminino."""
        if pd.isna(value):
            return np.nan
        if isinstance(value, str):
            normalized = value.strip().upper()
            if normalized == "M":
                return 0
            if normalized == "F":
                return 1
        numeric = pd.to_numeric(value, errors="coerce")
        if pd.isna(numeric):
            return np.nan
        return int(numeric) if numeric in (0, 1) else np.nan

    @staticmethod
    def categorize_age(age: Any) -> float:
        """Enquadra idade nas faixas do PDF."""
        age = pd.to_numeric(age, errors="coerce")
        if pd.isna(age):
            return np.nan
        if 18 <= age < 50:
            return 1
        if age < 60:
            return 2
        if age < 70:
            return 3
        if age < 80:
            return 4
        return 5

    @staticmethod
    def categorize_bmi(bmi: Any) -> float:
        """Enquadra IMC nas faixas do PDF."""
        bmi = pd.to_numeric(bmi, errors="coerce")
        if pd.isna(bmi) or bmi <= 0:
            return np.nan
        if bmi < 18.5:
            return 1
        if bmi < 25.0:
            return 2
        if bmi < 30.0:
            return 3
        if bmi < 35.0:
            return 4
        if bmi < 40.0:
            return 5
        return 6

    @staticmethod
    def calculate_bmi(weight_kg: Any, height_value: Any) -> float:
        """Calcula IMC aceitando altura em cm ou polegadas, conforme observado na base."""
        weight = pd.to_numeric(weight_kg, errors="coerce")
        height = pd.to_numeric(height_value, errors="coerce")
        if pd.isna(weight) or pd.isna(height) or weight <= 0 or height <= 0:
            return np.nan

        # No arquivo atual, valores como 64 e 71 indicam altura em polegadas.
        height_cm = height * 2.54 if height <= 100 else height
        height_m = height_cm / 100.0
        return float(weight / math.pow(height_m, 2))

    @staticmethod
    def signal_from_sum(total: float | int | np.floating) -> int:
        """Converte a soma em categoria 0-3 usada nas variaveis de sinal."""
        if pd.isna(total):
            return 0
        if total < 0:
            return 1
        if total == 0:
            return 2
        return 3

    @staticmethod
    def _safe_float(text: str) -> float:
        try:
            return float(text)
        except (TypeError, ValueError):
            return np.nan

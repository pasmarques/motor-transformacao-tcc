from __future__ import annotations

from typing import Any

import pandas as pd

from etl_motor.base import BaseModule, PatientContext


class ModuloLaboratorio(BaseModule):
    """Variaveis laboratoriais agregadas por janela de observacao."""

    name = "laboratorio"
    requires = ("cSexo",)
    provides = (
        "nPropDiasUreiaHiper",
        "nPropDiasCreatininaHiper",
        "nPropDiasLinfoTotaisHipo",
        "nPropDiasHemoglobinaHipo",
        "nPropDiasBilirrubinaHiper",
        "nPropDiasAlbuminaHipo",
        "nPropDiasTrigliceridesHiper",
        "nPropDiasPotassioHiper",
        "nPropDiasPotassioHipo",
        "nPropDiasMagnesioHiper",
        "nPropDiasMagnesioHipo",
        "nPropDiasSodioHiper",
        "nPropDiasSodioHipo",
        "nPropDiasFosforoHipo",
        "cFreqASTHiper",
        "cFreqALTHiper",
        "cFreqFosfatAlcalinaHiper",
        "nPropDiasPHHiper",
        "nPropDiasPHHipo",
        "nPropDiasWBCHipo",
        "nPropDiasWBCHiper",
        "nPropDiasLactatoHiper",
        "nPropDiasPlaquetasHipo",
    )

    def transform(self, context: PatientContext) -> dict[str, Any]:
        denominator = max(len(context.windows), 1)
        sexo = context.features.get("cSexo")
        masculino = sexo == 0

        ast_limit = 38.0 if masculino else 32.0
        alt_limit = 41.0 if masculino else 31.0

        return {
            "nPropDiasUreiaHiper": self._prop_any(context.windows, "ureia", denominator, upper=50.0 if masculino else 40.0),
            "nPropDiasCreatininaHiper": self._prop_any(context.windows, "creatinina", denominator, upper=1.3 if masculino else 1.1),
            "nPropDiasLinfoTotaisHipo": self._prop_any(context.windows, "linfocitos_totais", denominator, lower=900.0 if masculino else 800.0),
            "nPropDiasHemoglobinaHipo": self._prop_any(context.windows, "hemoglobina", denominator, lower=13.5 if masculino else 12.0),
            "nPropDiasBilirrubinaHiper": self._prop_any(context.windows, "bilirrubina", denominator, upper=1.2),
            "nPropDiasAlbuminaHipo": self._prop_any(context.windows, "albumina", denominator, lower=3.5),
            "nPropDiasTrigliceridesHiper": self._prop_any(context.windows, "triglicerides", denominator, upper=150.0 if masculino else 135.0),
            "nPropDiasPotassioHiper": self._prop_any(context.windows, "potassio", denominator, upper=5.5),
            "nPropDiasPotassioHipo": self._prop_any(context.windows, "potassio", denominator, lower=3.0),
            "nPropDiasMagnesioHiper": self._prop_any(context.windows, "magnesio", denominator, upper=2.5),
            "nPropDiasMagnesioHipo": self._prop_any(context.windows, "magnesio", denominator, lower=1.6),
            "nPropDiasSodioHiper": self._prop_any(context.windows, "sodio", denominator, upper=145.0, inclusive_upper=True),
            "nPropDiasSodioHipo": self._prop_any(context.windows, "sodio", denominator, lower=135.0),
            "nPropDiasFosforoHipo": self._prop_any(context.windows, "fosforo", denominator, lower=2.0),
            "cFreqASTHiper": self._freq_hiper(context.windows, "ast", ast_limit),
            "cFreqALTHiper": self._freq_hiper(context.windows, "alt", alt_limit),
            "cFreqFosfatAlcalinaHiper": self._freq_hiper(context.windows, "fosfatase_alcalina", 120.0),
            "nPropDiasPHHiper": self._prop_any(context.windows, "ph", denominator, upper=7.45),
            "nPropDiasPHHipo": self._prop_any(context.windows, "ph", denominator, lower=7.35),
            "nPropDiasWBCHipo": self._prop_any(context.windows, "wbc", denominator, lower=4.0),
            "nPropDiasWBCHiper": self._prop_any(context.windows, "wbc", denominator, upper=11.0),
            "nPropDiasLactatoHiper": self._prop_any(context.windows, "lactato", denominator, upper=2.5),
            "nPropDiasPlaquetasHipo": self._prop_any(context.windows, "plaquetas", denominator, lower=150.0),
        }

    @classmethod
    def _prop_any(
        cls,
        windows: pd.DataFrame,
        column: str,
        denominator: int,
        lower: float | None = None,
        upper: float | None = None,
        inclusive_upper: bool = False,
    ) -> float:
        if column not in windows:
            return 0.0
        mask = windows[column].map(
            lambda value: cls._has_value(
                value,
                lower=lower,
                upper=upper,
                inclusive_upper=inclusive_upper,
            )
        )
        return float(mask.sum() / denominator)

    @classmethod
    def _freq_hiper(cls, windows: pd.DataFrame, column: str, limit: float) -> int:
        """Classifica a frequencia de valores acima do limite usando escala 0-4.

        Alinhado com ICUTGOTGPFosfataseMaximasProporcao do SQL da professora:
          0 - Nenhuma anotacao encontrada no periodo (dado ausente)
          1 - Anotacoes encontradas, mas nenhuma acima do limite
          2 - Maximo acima do limite e <= 2x o valor de referencia
          3 - Maximo > 2x e <= 5x o valor de referencia
          4 - Maximo > 5x o valor de referencia
        """
        if column not in windows:
            return 0
        max_value = cls._max_value(windows[column])
        # Sem nenhum dado numerico registrado
        if pd.isna(max_value):
            return 0
        # Tem dados, mas todos abaixo ou iguais ao limite
        if max_value <= limit:
            return 1
        ratio = max_value / limit
        if ratio <= 2:
            return 2
        if ratio <= 5:
            return 3
        return 4

    @staticmethod
    def _has_value(
        value: Any,
        lower: float | None,
        upper: float | None,
        inclusive_upper: bool = False,
    ) -> bool:
        values = value if isinstance(value, list) else [value]
        numeric = pd.to_numeric(pd.Series(values), errors="coerce").dropna()
        if numeric.empty:
            return False
        if lower is not None:
            return bool(numeric.lt(lower).any())
        if upper is not None:
            return bool(numeric.ge(upper).any()) if inclusive_upper else bool(numeric.gt(upper).any())
        return False

    @classmethod
    def _max_value(cls, series: pd.Series) -> float:
        values = []
        for value in series:
            items = value if isinstance(value, list) else [value]
            values.extend(items)
        numeric = pd.to_numeric(pd.Series(values), errors="coerce").dropna()
        return float(numeric.max()) if not numeric.empty else float("nan")

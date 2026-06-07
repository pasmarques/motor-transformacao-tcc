from __future__ import annotations

from typing import Any

import numpy as np

from etl_motor.base import BaseModule, PatientContext


def _cat(value):
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return 0
    if value <= 0.0:
        return 0
    if value <= 0.25:
        return 1
    if value <= 0.50:
        return 2
    if value <= 0.75:
        return 3
    return 4


class ModuloCategorias(BaseModule):
    name = "categorias"
    requires = (
        "cDiasEmUTI",
        "nPropDiasJejumProteina",
        "nPropDiasJejumCalorias",
        "nPropDiasJejumTotal",
        "nPropDiasTempCorpElevada",
        "nPropDiasDiarreia",
        "nPropDiasVM",
        "nPropDiasHemodialise",
        "nPropDiasBHPositivo",
        "nPropDiasHGTHiper",
        "nPropDiasHGTHipo",
        "nPropDiasSemUsoNora",
        "nPropDiasNoraMax025",
        "nPropDiasNoraMax050",
        "nPropDiasNoraMax050Mais",
        "nPropDiasUsoVaso",
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
        "nPropDiasPHHiper",
        "nPropDiasPHHipo",
        "nPropDiasPASHipo",
        "nPropDiasPASHiper",
        "nPropDiasPADHipo",
        "nPropDiasPADHiper",
        "nPropDiasPAMHipo",
        "nPropDiasPAMHiper",
        "nPropDiasWBCHipo",
        "nPropDiasWBCHiper",
        "nPropDiasLactatoHiper",
        "nPropDiasPlaquetasHipo",
        "nPropDiasJejumProteina_7dmais",
        "nPropDiasJejumCalorias_7dmais",
    )
    provides = (
        "daysinICU_category",
        "cPropDiasJejumProteina",
        "cPropDiasJejumProteina_7dmais",
        "cPropDiasJejumCalorias",
        "cPropDiasJejumCalorias_7dmais",
        "cPropDJejumTotal",
        "cPropDiasTempCorpElevada",
        "cPropDiasDiarreia",
        "cPropDiasVM",
        "cPropDiasHemodialise",
        "cPropDiasBHPositivo",
        "cPropDiasHGTHiper",
        "cPropDiasHGTHipo",
        "cPropDiasSemUsoNora",
        "cPropDiasNoraMax025",
        "cPropDiasNoraMax050",
        "cPropDiasNoraMax050Mais",
        "cPropDiasUsoVaso",
        "cPropDiasUreiaHiper",
        "cPropDiasCreatininaHiper",
        "cPropDiasLinfoTotaisHipo",
        "cPropDiasHemoglobinaHipo",
        "cPropDiasBilirrubinaHiper",
        "cPropDiasAlbuminaHipo",
        "cPropDiasTrigliceridesHiper",
        "cPropDiasPotassioHiper",
        "cPropDiasPotassioHipo",
        "cPropDiasMagnesioHiper",
        "cPropDiasMagnesioHipo",
        "cPropDiasSodioHiper",
        "cPropDiasSodioHipo",
        "cPropDiasFosforoHipo",
        "cPropDiasPHHiper",
        "cPropDiasPHHipo",
        "cPropDiasPASHipo",
        "cPropDiasPASHiper",
        "cPropDiasPADHipo",
        "cPropDiasPADHiper",
        "cPropDiasPAMHipo",
        "cPropDiasPAMHiper",
        "cPropDiasWBCHipo",
        "cPropDiasWBCHiper",
        "cPropDiasLactatoHiper",
        "cPropDiasPlaquetasHipo",
    )

    def transform(self, context: PatientContext) -> dict[str, Any]:
        f = context.features
        _dias_cat = f.get("cDiasEmUTI", 0)
        _dias_labels = {0: "Short Stay (1-4 days)", 1: "Medium Stay (5-8 days)", 2: "Long Stay (>8 days)"}
        return {
            "daysinICU_category":            _dias_labels.get(_dias_cat, "Unknown"),
            "cPropDiasJejumProteina":        _cat(f.get("nPropDiasJejumProteina")),
            "cPropDiasJejumProteina_7dmais": _cat(f.get("nPropDiasJejumProteina_7dmais")),
            "cPropDiasJejumCalorias":        _cat(f.get("nPropDiasJejumCalorias")),
            "cPropDiasJejumCalorias_7dmais": _cat(f.get("nPropDiasJejumCalorias_7dmais")),
            "cPropDJejumTotal":              _cat(f.get("nPropDiasJejumTotal")),
            "cPropDiasTempCorpElevada":      _cat(f.get("nPropDiasTempCorpElevada")),
            "cPropDiasDiarreia":             _cat(f.get("nPropDiasDiarreia")),
            "cPropDiasVM":                   _cat(f.get("nPropDiasVM")),
            "cPropDiasHemodialise":          _cat(f.get("nPropDiasHemodialise")),
            "cPropDiasBHPositivo":           _cat(f.get("nPropDiasBHPositivo")),
            "cPropDiasHGTHiper":             _cat(f.get("nPropDiasHGTHiper")),
            "cPropDiasHGTHipo":              _cat(f.get("nPropDiasHGTHipo")),
            "cPropDiasSemUsoNora":           4 - _cat(f.get("nPropDiasSemUsoNora")),
            "cPropDiasNoraMax025":           _cat(f.get("nPropDiasNoraMax025")),
            "cPropDiasNoraMax050":           _cat(f.get("nPropDiasNoraMax050")),
            "cPropDiasNoraMax050Mais":       _cat(f.get("nPropDiasNoraMax050Mais")),
            "cPropDiasUsoVaso":              _cat(f.get("nPropDiasUsoVaso")),
            "cPropDiasUreiaHiper":           _cat(f.get("nPropDiasUreiaHiper")),
            "cPropDiasCreatininaHiper":      _cat(f.get("nPropDiasCreatininaHiper")),
            "cPropDiasLinfoTotaisHipo":      _cat(f.get("nPropDiasLinfoTotaisHipo")),
            "cPropDiasHemoglobinaHipo":      _cat(f.get("nPropDiasHemoglobinaHipo")),
            "cPropDiasBilirrubinaHiper":     _cat(f.get("nPropDiasBilirrubinaHiper")),
            "cPropDiasAlbuminaHipo":         _cat(f.get("nPropDiasAlbuminaHipo")),
            "cPropDiasTrigliceridesHiper":   _cat(f.get("nPropDiasTrigliceridesHiper")),
            "cPropDiasPotassioHiper":        _cat(f.get("nPropDiasPotassioHiper")),
            "cPropDiasPotassioHipo":         _cat(f.get("nPropDiasPotassioHipo")),
            "cPropDiasMagnesioHiper":        _cat(f.get("nPropDiasMagnesioHiper")),
            "cPropDiasMagnesioHipo":         _cat(f.get("nPropDiasMagnesioHipo")),
            "cPropDiasSodioHiper":           _cat(f.get("nPropDiasSodioHiper")),
            "cPropDiasSodioHipo":            _cat(f.get("nPropDiasSodioHipo")),
            "cPropDiasFosforoHipo":          _cat(f.get("nPropDiasFosforoHipo")),
            "cPropDiasPHHiper":              _cat(f.get("nPropDiasPHHiper")),
            "cPropDiasPHHipo":              _cat(f.get("nPropDiasPHHipo")),
            "cPropDiasPASHipo":              _cat(f.get("nPropDiasPASHipo")),
            "cPropDiasPASHiper":             _cat(f.get("nPropDiasPASHiper")),
            "cPropDiasPADHipo":              _cat(f.get("nPropDiasPADHipo")),
            "cPropDiasPADHiper":             _cat(f.get("nPropDiasPADHiper")),
            "cPropDiasPAMHipo":              _cat(f.get("nPropDiasPAMHipo")),
            "cPropDiasPAMHiper":             _cat(f.get("nPropDiasPAMHiper")),
            "cPropDiasWBCHipo":              _cat(f.get("nPropDiasWBCHipo")),
            "cPropDiasWBCHiper":             _cat(f.get("nPropDiasWBCHiper")),
            "cPropDiasLactatoHiper":         _cat(f.get("nPropDiasLactatoHiper")),
            "cPropDiasPlaquetasHipo":        _cat(f.get("nPropDiasPlaquetasHipo")),
        }

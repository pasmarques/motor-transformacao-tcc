from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from etl_motor.cleaning import DataCleaner
from etl_motor.config import TransformConfig
from etl_motor.modules import (
    ModuloBalancoHidrico,
    ModuloDrogasVasoativas,
    ModuloEvacuacao,
    ModuloHemodialise,
    ModuloInternacao,
    ModuloLaboratorio,
    ModuloNutricao,
    ModuloPerfil,
    ModuloSinaisVitais,
    ModuloVentilacaoMecanica,
)
from etl_motor.orchestrator import OrquestradorETL
from etl_motor.personalizacao import AggregationSpec, aplicar_personalizacao
from etl_motor.plugin_loader import descobrir_plugins

# Caminho padrao do arquivo de regras (raiz do projeto)
_REGRAS_PATH = Path(__file__).resolve().parents[1] / "regras.json"


def _load_regras(regras_path: Path | None = None) -> dict:
    """Carrega o arquivo regras.json. Retorna dict vazio se nao encontrado."""
    path = regras_path or _REGRAS_PATH
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


class JsonTransformador:
    """Interface oficial do Bloco 2 para transformar um JSON de paciente."""

    def __init__(self, regras_path: Path | None = None, plugins_dir: Path | None = None) -> None:
        regras = _load_regras(regras_path)
        self._regras_lab = regras.get("laboratorio", {})
        self._regras_sv = regras.get("sinais_vitais", {})
        self._regras_dv = regras.get("drogas_vasoativas", {})
        self._regras_plugins = regras.get("plugins", {})
        self._plugins = descobrir_plugins(plugins_dir=plugins_dir, regras=self._regras_plugins)

    def transformar_json(
        self,
        paciente_json: dict[str, Any],
        config: TransformConfig | None = None,
        variaveis_saida: list[str] | None = None,
        agregacoes_customizadas: list[AggregationSpec] | None = None,
    ) -> dict[str, Any]:
        config = self._resolve_config(paciente_json, config)
        subject_id = int(paciente_json["patient_id"])

        patients_df = pd.DataFrame([self._patient_row(paciente_json, config)])
        windows_df = self._windows_df(paciente_json, subject_id)
        bh_df = self._balanco_hidrico_df(paciente_json, subject_id)
        evacuacao_df = self._evacuacao_events_df(paciente_json, subject_id)

        modulos_core = [
            ModuloPerfil(),
            ModuloInternacao(),
            ModuloBalancoHidrico(bh_df),
            ModuloEvacuacao(evacuacao_df),
            ModuloNutricao(),
            ModuloVentilacaoMecanica(),
            ModuloHemodialise(),
            ModuloDrogasVasoativas(self._regras_dv),
            ModuloSinaisVitais(self._regras_sv),
            ModuloLaboratorio(self._regras_lab),
        ]

        orchestrator = OrquestradorETL(
            patients_df=patients_df,
            windows_df=windows_df,
            modules=modulos_core + self._plugins,
        )
        resultado = orchestrator.transformar_paciente(subject_id=subject_id, config=config)
        return aplicar_personalizacao(
            resultado=resultado,
            paciente_json=paciente_json,
            config=config,
            variaveis_saida=variaveis_saida,
            agregacoes_customizadas=agregacoes_customizadas,
        )

    def transformar_varios_json(
        self,
        pacientes_json: list[dict[str, Any]],
        config: TransformConfig | None = None,
        variaveis_saida: list[str] | None = None,
        agregacoes_customizadas: list[AggregationSpec] | None = None,
    ) -> pd.DataFrame:
        """Transforma uma lista de pacientes JSON em tabela final."""
        resultados = [
            self.transformar_json(
                paciente_json,
                config=config,
                variaveis_saida=variaveis_saida,
                agregacoes_customizadas=agregacoes_customizadas,
            )
            for paciente_json in pacientes_json
        ]
        return pd.DataFrame(resultados)

    def gerar_auditoria_json(
        self,
        paciente_json: dict[str, Any],
        config: TransformConfig | None = None,
    ) -> str:
        resultado = self.transformar_json(paciente_json, config)
        return pd.Series(resultado, name="valor").to_string()

    def _resolve_config(
        self,
        paciente_json: dict[str, Any],
        config: TransformConfig | None,
    ) -> TransformConfig:
        if config is not None:
            return config

        config_data = dict(paciente_json.get("configuracao_processamento") or {})
        if "data_referencia" not in config_data and paciente_json.get("data_referencia"):
            config_data["data_referencia"] = paciente_json["data_referencia"]
        return TransformConfig.from_dict(config_data)

    def _patient_row(self, paciente_json: dict[str, Any], config: TransformConfig) -> dict[str, Any]:
        perfil = paciente_json.get("perfil") or {}
        internacao = paciente_json.get("internacao") or {}
        subject_id = int(paciente_json["patient_id"])

        idade = perfil.get("idade")
        if idade in (None, ""):
            idade = self._calculate_age(perfil.get("data_nascimento"), config.data_referencia_ts)

        imc = perfil.get("imc")
        if imc in (None, ""):
            imc = DataCleaner.calculate_bmi(perfil.get("peso_kg"), perfil.get("altura_cm"))

        data_obito = internacao.get("data_obito")
        denouement = 1 if data_obito not in (None, "") else 0

        return {
            "subject_id": subject_id,
            "gender": perfil.get("sexo"),
            "anchor_age": idade,
            "pesoadm": perfil.get("peso_kg"),
            "alturacm": perfil.get("altura_cm"),
            "IMC_range": DataCleaner.categorize_bmi(imc),
            "intime": internacao.get("data_admissao_uti"),
            "outtime": internacao.get("data_alta_uti") or data_obito or config.data_referencia,
            "deathtime": data_obito,
            "denouement": denouement,
        }

    def _windows_df(self, paciente_json: dict[str, Any], subject_id: int) -> pd.DataFrame:
        rows = []
        for mapa in paciente_json.get("mapas_diarios", []):
            start = pd.to_datetime(mapa.get("inicio"), errors="coerce")
            end = pd.to_datetime(mapa.get("fim"), errors="coerce")
            row = {
                "subject_id": subject_id,
                "day": mapa.get("dia") or mapa.get("indice_janela"),
                "start_time": mapa.get("inicio"),
                "end_time": mapa.get("fim"),
                "diff_end_start": self._diff_hours(start, end),
            }
            row.update(self._nutricao_cols(mapa))
            row.update(self._ventilacao_cols(mapa))
            row.update(self._hemodialise_cols(mapa))
            row.update(self._drogas_cols(mapa))
            row.update(self._sinais_cols(mapa))
            row.update(self._laboratorio_cols(mapa))
            rows.append(row)
        return pd.DataFrame(rows)

    def _balanco_hidrico_df(self, paciente_json: dict[str, Any], subject_id: int) -> pd.DataFrame:
        rows = []
        for mapa in paciente_json.get("mapas_diarios", []):
            bh = mapa.get("balanco_hidrico") or {}
            rows.append(
                {
                    "subject_id": subject_id,
                    "day": mapa.get("dia") or mapa.get("indice_janela"),
                    "start_time": mapa.get("inicio"),
                    "BHDia": bh.get("saldo"),
                }
            )
        return pd.DataFrame(rows, columns=["subject_id", "day", "start_time", "BHDia"])

    def _evacuacao_events_df(self, paciente_json: dict[str, Any], subject_id: int) -> pd.DataFrame:
        rows = []
        for mapa in paciente_json.get("mapas_diarios", []):
            quantidade = int((mapa.get("evacuacao") or {}).get("quantidade") or 0)
            start = pd.to_datetime(mapa.get("inicio"), errors="coerce")
            if pd.isna(start):
                continue
            for index in range(quantidade):
                rows.append(
                    {
                        "subject_id": subject_id,
                        "event_time": start + pd.Timedelta(minutes=index),
                    }
                )
        return pd.DataFrame(rows, columns=["subject_id", "event_time"])

    @staticmethod
    def _calculate_age(data_nascimento: Any, data_referencia: pd.Timestamp | None) -> float:
        birth = pd.to_datetime(data_nascimento, errors="coerce")
        if pd.isna(birth) or data_referencia is None:
            return np.nan
        years = data_referencia.year - birth.year
        had_birthday = (data_referencia.month, data_referencia.day) >= (birth.month, birth.day)
        return years if had_birthday else years - 1

    @staticmethod
    def _diff_hours(start: pd.Timestamp, end: pd.Timestamp) -> float:
        if pd.isna(start) or pd.isna(end):
            return np.nan
        return float((end - start) / pd.Timedelta(hours=1))

    @staticmethod
    def _nutricao_cols(mapa: dict[str, Any]) -> dict[str, Any]:
        nutricao = mapa.get("nutricao") or {}
        return {
            "calorias_kcal": nutricao.get("calorias_kcal", 0),
            "proteinas_g": nutricao.get("proteinas_g", 0),
            "calorias_kcal_kg_dia": nutricao.get("calorias_kcal_kg_dia"),
            "proteinas_g_kg_dia": nutricao.get("proteinas_g_kg_dia"),
        }

    @staticmethod
    def _ventilacao_cols(mapa: dict[str, Any]) -> dict[str, Any]:
        vm = mapa.get("ventilacao_mecanica") or {}
        return {"vm_em_uso": bool(vm.get("em_uso", False))}

    @staticmethod
    def _hemodialise_cols(mapa: dict[str, Any]) -> dict[str, Any]:
        hemodialise = mapa.get("hemodialise") or {}
        return {"hemodialise_presente": bool(hemodialise.get("presente", False))}

    @staticmethod
    def _drogas_cols(mapa: dict[str, Any]) -> dict[str, Any]:
        drogas = mapa.get("drogas_vasoativas") or {}
        nora = drogas.get("noradrenalina") or {}
        vaso = drogas.get("vasopressina") or {}
        return {
            "nora_dose_maxima": nora.get("dose_maxima", 0) or 0,
            "vasopressina_em_uso": bool(vaso.get("em_uso", False)),
        }

    @staticmethod
    def _sinais_cols(mapa: dict[str, Any]) -> dict[str, Any]:
        sinais = mapa.get("sinais_vitais") or {}
        return {
            "temperatura": sinais.get("temperatura", []),
            "hgt": sinais.get("hgt", []),
            "pas": sinais.get("pas", []),
            "pad": sinais.get("pad", []),
            "pam": sinais.get("pam", []),
        }

    @staticmethod
    def _laboratorio_cols(mapa: dict[str, Any]) -> dict[str, Any]:
        laboratorio = mapa.get("laboratorio") or {}
        return {
            "ph": laboratorio.get("ph", []),
            "ureia": laboratorio.get("ureia", []),
            "creatinina": laboratorio.get("creatinina", []),
            "sodio": laboratorio.get("sodio", []),
            "potassio": laboratorio.get("potassio", []),
            "magnesio": laboratorio.get("magnesio", []),
            "fosforo": laboratorio.get("fosforo", []),
            "albumina": laboratorio.get("albumina", []),
            "linfocitos_totais": laboratorio.get("linfocitos_totais", []),
            "hemoglobina": laboratorio.get("hemoglobina", []),
            "ast": laboratorio.get("ast", []),
            "alt": laboratorio.get("alt", []),
            "bilirrubina": laboratorio.get("bilirrubina", []),
            "triglicerides": laboratorio.get("triglicerides", []),
            "fosfatase_alcalina": laboratorio.get("fosfatase_alcalina", []),
            "wbc": laboratorio.get("wbc", []),
            "plaquetas": laboratorio.get("plaquetas", []),
            "lactato": laboratorio.get("lactato", []),
        }

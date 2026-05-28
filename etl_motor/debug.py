from __future__ import annotations

from typing import Any

import pandas as pd

from etl_motor.base import PatientContext
from etl_motor.cleaning import DataCleaner
from etl_motor.config import TransformConfig
from etl_motor.orchestrator import OrquestradorETL


class DebugPaciente:
    """Auditoria textual dos recortes usados para calcular um paciente."""

    def __init__(self, orchestrator: OrquestradorETL, max_rows: int = 20) -> None:
        self.orchestrator = orchestrator
        self.max_rows = max_rows

    def gerar_relatorio(
        self,
        subject_id: int,
        offset_dias: int = -1,
        config: TransformConfig | None = None,
    ) -> str:
        context = self.orchestrator.criar_contexto(subject_id, offset_dias, config=config)
        resultado = self.orchestrator.transformar_paciente(subject_id, offset_dias, config=config)

        partes = [
            self._cabecalho(context, offset_dias),
            self._paciente(context),
            self._janelas(context),
            self._balanco_hidrico(context),
            self._evacuacao(context),
            self._resultado(resultado),
        ]
        return "\n\n".join(partes)

    def _cabecalho(self, context: PatientContext, offset_dias: int) -> str:
        cutoff_72h = min(context.start_time + pd.Timedelta(hours=72), context.cutoff_time)
        return "\n".join(
            [
                f"DEBUG PACIENTE {context.subject_id}",
                f"offset_dias: {offset_dias}",
                f"tamanho_janela_horas: {context.window_size_hours}",
                f"inicio_uti: {context.start_time}",
                f"cutoff_global: {context.cutoff_time}",
                f"cutoff_72h_bh: {cutoff_72h}",
                f"janelas_usadas: {context.n_observation_windows}",
                f"dias_equivalentes: {context.n_observation_days}",
            ]
        )

    def _paciente(self, context: PatientContext) -> str:
        cols = [
            "subject_id",
            "gender",
            "anchor_age",
            "pesoadm",
            "alturacm",
            "IMC_range",
            "intime",
            "outtime",
            "deathtime",
            "denouement",
            "daysinICU",
        ]
        available = [col for col in cols if col in context.patient_row.index]
        return "PACIENTE\n" + context.patient_row[available].to_frame("valor").to_string()

    def _janelas(self, context: PatientContext) -> str:
        if context.windows.empty:
            return "JANELAS USADAS\nNenhuma janela encontrada."

        cols = ["day", "start_time_clean", "end_time_clean", "diff_end_start"]
        available = [col for col in cols if col in context.windows.columns]
        windows = context.windows.loc[:, available].head(self.max_rows)
        return "JANELAS USADAS\n" + windows.to_string(index=False)

    def _balanco_hidrico(self, context: PatientContext) -> str:
        module = self._get_module("balanco_hidrico")
        if module is None:
            return "BALANCO HIDRICO\nModulo nao encontrado."

        cutoff_72h = min(context.start_time + pd.Timedelta(hours=72), context.cutoff_time)
        periodo = self._bh_rows(module, context, context.start_time, context.cutoff_time)
        primeiras_72h = self._bh_rows(module, context, context.start_time, cutoff_72h)

        total_periodo = periodo["BHDia_clean"].dropna().sum() if not periodo.empty else pd.NA
        total_72h = primeiras_72h["BHDia_clean"].dropna().sum() if not primeiras_72h.empty else pd.NA

        lines = [
            "BALANCO HIDRICO",
            f"registros_periodo: {len(periodo)}",
            f"soma_periodo: {total_periodo}",
            f"sinal_periodo: {DataCleaner.signal_from_sum(total_periodo)}",
            f"registros_72h: {len(primeiras_72h)}",
            f"soma_72h: {total_72h}",
            f"sinal_72h: {DataCleaner.signal_from_sum(total_72h)}",
            "amostra_periodo:",
            self._format_df(periodo, ["day", "start_time_clean", "BHDia", "BHDia_clean"]),
        ]
        return "\n".join(lines)

    def _evacuacao(self, context: PatientContext) -> str:
        module = self._get_module("evacuacao")
        if module is None:
            return "EVACUACAO\nModulo nao encontrado."

        df = module.evacuacao_df
        row = df.loc[df["subject_id"].eq(context.subject_id)]
        if row.empty:
            return "EVACUACAO\nPaciente sem linha na base de evacuacao."

        cols = [
            "subject_id",
            "evacuation",
            "cPropConstipacaoPeriodo",
            "cPropDiarreiaPeriodo",
            "cProp4MaisEvacuacoes",
            "prop_4mais_clean",
        ]
        return "EVACUACAO\n" + self._format_df(row, cols)

    def _resultado(self, resultado: dict[str, Any]) -> str:
        series = pd.Series(resultado, name="valor")
        return "RESULTADO FINAL\n" + series.to_string()

    def _get_module(self, name: str) -> Any | None:
        matches = [module for module in self.orchestrator.modules if module.name == name]
        return matches[0] if matches else None

    @staticmethod
    def _bh_rows(
        module: Any,
        context: PatientContext,
        start_time: pd.Timestamp,
        end_time: pd.Timestamp,
    ) -> pd.DataFrame:
        mask = (
            module.bh_df["subject_id"].eq(context.subject_id)
            & module.bh_df["start_time_clean"].ge(start_time)
            & module.bh_df["start_time_clean"].lt(end_time)
        )
        return module.bh_df.loc[mask].copy()

    def _format_df(self, df: pd.DataFrame, columns: list[str]) -> str:
        if df.empty:
            return "Nenhum registro."
        available = [col for col in columns if col in df.columns]
        return df.loc[:, available].head(self.max_rows).to_string(index=False)

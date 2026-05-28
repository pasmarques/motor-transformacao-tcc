from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from etl_motor.config import TransformConfig
from etl_motor.json_transformer import JsonTransformador
from etl_motor.mapas_json import converter_entradas_para_jsons
from etl_motor.personalizacao import (
    METADATA_COLUMNS,
    VARIAVEIS_SAIDA_PADRAO,
    parse_agregacao_spec,
)
from etl_motor.validation import NAO_COMPARAVEIS_SEM_PERFIL, comparar_com_referencia


st.set_page_config(page_title="MVP Motor de Transformacao", layout="wide")

st.markdown(
    """
    <style>
    .block-container { padding-top: 1.8rem; }
    .step-row {
        display: grid;
        grid-template-columns: repeat(5, minmax(0, 1fr));
        gap: 8px;
        margin: 14px 0 18px 0;
    }
    .step-box {
        border: 1px solid #d6dde6;
        border-radius: 8px;
        padding: 10px 12px;
        background: #f8fafc;
        min-height: 74px;
    }
    .step-box strong {
        display: block;
        font-size: 0.88rem;
        color: #172033;
        margin-bottom: 4px;
    }
    .step-box span {
        color: #4d5b6c;
        font-size: 0.78rem;
    }
    .ok-note {
        border-left: 4px solid #207f5a;
        padding: 8px 12px;
        background: #f3fbf7;
        color: #23332c;
        margin: 4px 0 18px 0;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("MVP do Motor de Transformacao")
st.markdown(
    """
    <div class="step-row">
      <div class="step-box"><strong>1. Entradas</strong><span>Mapas diarios enviados</span></div>
      <div class="step-box"><strong>2. Adaptador</strong><span>Gera JSON do Bloco 1</span></div>
      <div class="step-box"><strong>3. Bloco 2</strong><span>Aplica modulos e regras</span></div>
      <div class="step-box"><strong>4. Saida</strong><span>CSV final por paciente</span></div>
      <div class="step-box"><strong>5. Validacao</strong><span>Compara com a amostra</span></div>
    </div>
    <div class="ok-note">
      Bloco 1 simulado pelo adaptador de entrada. Bloco 2 funcional neste MVP.
      A BASEPACIENTES21D_ Amostra entra somente na validacao.
    </div>
    """,
    unsafe_allow_html=True,
)


def _parse_agregacoes(text: str):
    return [parse_agregacao_spec(line) for line in text.splitlines() if line.strip()]


def _subject_ids(pacientes_json: list[dict]) -> list[int]:
    return [int(paciente["patient_id"]) for paciente in pacientes_json]


def _total_janelas(pacientes_json: list[dict]) -> int:
    return sum(len(paciente.get("mapas_diarios") or []) for paciente in pacientes_json)


def _report_value(report: str, label: str) -> str:
    match = re.search(rf"{re.escape(label)}:\s*([0-9]+)", report)
    return match.group(1) if match else "-"


def _report_line(report: str, label: str) -> str | None:
    for line in report.splitlines():
        if line.startswith(label + ":"):
            return line.split(":", 1)[1].strip()
    return None


def _run_pipeline(
    entradas_dir: str,
    patient_info_file: str | None,
    subject_id_text: str,
    config: TransformConfig,
    variaveis_saida: list[str] | None,
    agregacoes_text: str,
    sem_metadados: bool,
) -> tuple[list[dict], pd.DataFrame, str | None]:
    subject_ids = [int(subject_id_text)] if subject_id_text.strip() else None
    agregacoes_customizadas = _parse_agregacoes(agregacoes_text)
    pacientes_json = converter_entradas_para_jsons(
        base_dir=PROJECT_ROOT,
        entradas_dir=entradas_dir,
        patient_info_file=patient_info_file,
        subject_ids=subject_ids,
    )
    if not pacientes_json:
        raise ValueError("Nenhum paciente encontrado nos mapas diarios.")

    transformador = JsonTransformador()
    df_final = transformador.transformar_varios_json(
        pacientes_json,
        config=config,
        variaveis_saida=variaveis_saida,
        agregacoes_customizadas=agregacoes_customizadas,
    )
    if sem_metadados:
        df_final = df_final.drop(columns=list(METADATA_COLUMNS), errors="ignore")

    reference_path = PROJECT_ROOT / "BASEPACIENTES21D_ Amostra.csv"
    report = None
    if reference_path.exists():
        ignored_cols = set() if patient_info_file else NAO_COMPARAVEIS_SEM_PERFIL
        report = comparar_com_referencia(df_final, reference_path, ignored_cols=ignored_cols)
    return pacientes_json, df_final, report


with st.sidebar:
    st.header("Configurar")
    perfil_mode = st.radio(
        "Perfil e internacao",
        options=["Mock do Bloco 1", "Sem perfil"],
        index=0,
    )
    st.divider()
    cortar_janelas_finais = st.number_input("Cortar janelas finais", min_value=0, value=1, step=1)
    max_janelas_text = st.text_input("Maximo de janelas", value="")
    data_referencia = st.text_input("Data de referencia", value="")
    sem_metadados = st.checkbox("Ocultar metadados auxiliares", value=True)
    st.divider()
    saida_mode = st.radio(
        "Variaveis finais",
        options=["Todas do PDF", "Selecionar"],
        index=0,
    )
    variaveis_saida = None
    if saida_mode == "Selecionar":
        variaveis_saida = st.multiselect(
            "Colunas exportadas",
            options=list(VARIAVEIS_SAIDA_PADRAO),
            default=["idPaciente", "cSexo", "cFaixaEtaria", "cFaixaIMC", "cDiasEmUTI"],
        )
    agregacoes_text = st.text_area(
        "Agregacoes extras",
        value="",
        placeholder="creatinina:max:creatinina_max\ncreatinina:min:creatinina_min",
        height=96,
    )

max_janelas = int(max_janelas_text) if max_janelas_text.strip() else None
config = TransformConfig(
    tamanho_janela_horas=24,
    cortar_janelas_finais=int(cortar_janelas_finais),
    max_janelas=max_janelas,
    data_referencia=data_referencia or None,
)

st.subheader("1. Entrada do MVP")
input_col, mock_col, run_col = st.columns([1.6, 1.6, 0.8], vertical_alignment="bottom")
with input_col:
    entradas_dir = st.text_input("Pasta Entradas", value=str(PROJECT_ROOT / "Entradas"))
    subject_id_text = st.text_input("Paciente especifico", value="", placeholder="opcional")
with mock_col:
    patient_info_file = None
    if perfil_mode == "Mock do Bloco 1":
        patient_info_file = st.text_input(
            "Mock de perfil/internacao",
            value=str(PROJECT_ROOT / "ICUpatients21D.csv"),
        )
    else:
        st.text_input("Mock de perfil/internacao", value="desativado", disabled=True)
with run_col:
    run_clicked = st.button("Executar MVP", type="primary", use_container_width=True)

if run_clicked:
    try:
        pacientes_json, df_final, report = _run_pipeline(
            entradas_dir=entradas_dir,
            patient_info_file=patient_info_file,
            subject_id_text=subject_id_text,
            config=config,
            variaveis_saida=variaveis_saida,
            agregacoes_text=agregacoes_text,
            sem_metadados=sem_metadados,
        )
    except Exception as exc:  # noqa: BLE001
        st.error(f"Execucao interrompida: {exc}")
        st.stop()

    st.session_state["pacientes_json"] = pacientes_json
    st.session_state["df_final"] = df_final
    st.session_state["validation_report"] = report
    st.session_state["perfil_mode"] = perfil_mode

pacientes_json = st.session_state.get("pacientes_json")
df_final = st.session_state.get("df_final")
report = st.session_state.get("validation_report")

if not pacientes_json or df_final is None:
    st.info("Use o botao Executar MVP para gerar o JSON, transformar e validar.")
    st.stop()

st.subheader("2. JSON gerado para o Bloco 2")
metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)
metric_col1.metric("Pacientes", len(pacientes_json))
metric_col2.metric("Janelas", _total_janelas(pacientes_json))
metric_col3.metric("Colunas finais", len(df_final.columns))
metric_col4.metric("Perfil", "mock" if st.session_state.get("perfil_mode") == "Mock do Bloco 1" else "ausente")

preview_ids = _subject_ids(pacientes_json)
selected_id = st.selectbox("Preview por paciente", options=preview_ids)
selected_json = next(p for p in pacientes_json if int(p["patient_id"]) == int(selected_id))
with st.expander("Ver contrato JSON deste paciente", expanded=False):
    st.json(selected_json)

st.subheader("3. Saida do Bloco 2")
st.dataframe(df_final, use_container_width=True, hide_index=True)
st.download_button(
    "Baixar CSV",
    data=df_final.to_csv(index=False).encode("utf-8"),
    file_name="dataset_transformado_mvp.csv",
    mime="text/csv",
)

st.subheader("4. Validacao")
if report:
    val_col1, val_col2, val_col3, val_col4 = st.columns(4)
    val_col1.metric("Comparados", _report_value(report, "Pacientes comparados"))
    val_col2.metric("Iguais", _report_value(report, "Colunas iguais"))
    val_col3.metric("Diferencas", _report_value(report, "Colunas com diferenca de valor"))
    val_col4.metric("Ausentes", _report_value(report, "Colunas esperadas ausentes"))
    st.warning(
        "Diferencas de valor indicam regras que ainda precisam ser calibradas contra a base legada."
    )
    diagnostic_labels = [
        "Diagnostico",
        "Diferencas possivelmente ligadas a perfil/peso/sexo",
        "Diferencas possivelmente ligadas a recorte/internacao",
        "Diferencas em regras longitudinais a calibrar",
    ]
    for label in diagnostic_labels:
        value = _report_line(report, label)
        if value:
            st.markdown(f"**{label}:** {value}")
    with st.expander("Relatorio completo da validacao", expanded=False):
        st.code(report, language="text")
else:
    st.warning("Arquivo de referencia nao encontrado.")

with st.expander("Entrada JSON manual"):
    example_path = PROJECT_ROOT / "examples" / "paciente_exemplo.json"
    example_json_text = example_path.read_text(encoding="utf-8")
    json_text = st.text_area("JSON", value="", height=220, placeholder=example_json_text)
    if st.button("Transformar JSON manual"):
        try:
            paciente_json = json.loads(json_text or example_json_text)
            transformador = JsonTransformador()
            if isinstance(paciente_json, list):
                manual_df = transformador.transformar_varios_json(paciente_json, config=config)
            else:
                manual_df = pd.DataFrame([transformador.transformar_json(paciente_json, config=config)])
            if sem_metadados:
                manual_df = manual_df.drop(columns=list(METADATA_COLUMNS), errors="ignore")
            st.dataframe(manual_df, use_container_width=True, hide_index=True)
        except Exception as exc:  # noqa: BLE001
            st.error(f"JSON manual invalido: {exc}")

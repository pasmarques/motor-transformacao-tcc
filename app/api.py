"""API Flask minima — camada de aplicacao do prototipo Bloco 2.

Representa a camada API REST da arquitetura completa (FastAPI em producao).
Expoe o motor de transformacao via HTTP para o frontend HTML.

Iniciar: python app/api.py
Porta  : http://localhost:5050
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
from flask import Flask, jsonify, request
from flask_cors import CORS

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

app = Flask(__name__)
CORS(app)


@app.route("/api/variaveis", methods=["GET"])
def variaveis():
    """Retorna a lista de variaveis de saida do contrato."""
    return jsonify(list(VARIAVEIS_SAIDA_PADRAO))


@app.route("/api/transform", methods=["POST"])
def transform():
    """Executa o pipeline completo e retorna resultado + relatorio."""
    body = request.get_json(force=True)

    entradas_dir   = body.get("entradas_dir", str(PROJECT_ROOT / "entradas"))
    patient_info   = body.get("patient_info_file") or None
    subject_id_raw = body.get("subject_id", "")
    cortar         = int(body.get("cortar_janelas_finais", 0))
    max_jan        = body.get("max_janelas") or None
    data_ref       = body.get("data_referencia") or None
    sem_meta       = bool(body.get("sem_metadados", True))
    variaveis_saida = body.get("variaveis_saida") or None
    agregacoes_raw  = body.get("agregacoes", "")

    subject_ids = [int(subject_id_raw)] if str(subject_id_raw).strip() else None
    agregacoes  = [
        parse_agregacao_spec(line)
        for line in agregacoes_raw.splitlines()
        if line.strip()
    ]
    config = TransformConfig(
        tamanho_janela_horas=24,
        cortar_janelas_finais=cortar,
        max_janelas=int(max_jan) if max_jan else None,
        data_referencia=data_ref,
    )

    try:
        pacientes_json = converter_entradas_para_jsons(
            base_dir=PROJECT_ROOT,
            entradas_dir=entradas_dir,
            patient_info_file=patient_info,
            subject_ids=subject_ids,
        )
    except Exception as exc:
        return jsonify({"erro": f"Erro ao carregar entradas: {exc}"}), 400

    if not pacientes_json:
        return jsonify({"erro": "Nenhum paciente encontrado nos mapas diarios."}), 404

    transformador = JsonTransformador()
    df = transformador.transformar_varios_json(
        pacientes_json,
        config=config,
        variaveis_saida=variaveis_saida,
        agregacoes_customizadas=agregacoes,
    )
    if sem_meta:
        df = df.drop(columns=list(METADATA_COLUMNS), errors="ignore")

    # Validacao contra a amostra
    report_text = None
    report_metricas = {}
    ref_path = PROJECT_ROOT / "BASEPACIENTES21D_ Amostra.csv"
    if ref_path.exists():
        ignored = set() if patient_info else NAO_COMPARAVEIS_SEM_PERFIL
        report_text = comparar_com_referencia(df, ref_path, ignored_cols=ignored)
        report_metricas = _parse_report(report_text)

    # Preview do JSON do primeiro paciente
    preview_json = pacientes_json[0] if pacientes_json else {}

    # NaN nao e JSON valido. pandas.to_json converte NaN → null corretamente.
    import json as _json
    tabela_safe = _json.loads(df.to_json(orient="records", default_handler=str))

    return jsonify({
        "n_pacientes":   len(pacientes_json),
        "n_janelas":     sum(len(p.get("mapas_diarios") or []) for p in pacientes_json),
        "n_colunas":     len(df.columns),
        "pacientes_ids": [int(p["patient_id"]) for p in pacientes_json],
        "preview_json":  preview_json,
        "tabela":        tabela_safe,
        "colunas":       list(df.columns),
        "report_texto":  report_text,
        "report_metricas": report_metricas,
        "perfil_ativo":  patient_info is not None,
    })


@app.route("/api/paciente_json", methods=["POST"])
def paciente_json():
    """Retorna o JSON padronizado de um paciente especifico."""
    body    = request.get_json(force=True)
    pid     = int(body.get("subject_id"))
    entradas = body.get("entradas_dir", str(PROJECT_ROOT / "entradas"))
    patient_info = body.get("patient_info_file") or None

    pacientes = converter_entradas_para_jsons(
        base_dir=PROJECT_ROOT,
        entradas_dir=entradas,
        patient_info_file=patient_info,
        subject_ids=[pid],
    )
    if not pacientes:
        return jsonify({"erro": "Paciente nao encontrado."}), 404
    return jsonify(pacientes[0])


def _parse_report(report: str) -> dict:
    metricas = {}
    for line in report.splitlines():
        for key in ["Pacientes comparados", "Colunas comparadas",
                    "Colunas iguais", "Colunas com diferenca de valor",
                    "Colunas esperadas ausentes"]:
            if line.startswith(key + ":"):
                val = line.split(":", 1)[1].strip()
                try:
                    metricas[key] = int(val)
                except ValueError:
                    metricas[key] = val
    # Linhas de diagnostico
    for label in ["Diagnostico", "Diferencas possivelmente ligadas a perfil/peso/sexo",
                  "Diferencas possivelmente ligadas a recorte/internacao",
                  "Diferencas em regras longitudinais a calibrar",
                  "Nao comparaveis neste modo"]:
        for line in report.splitlines():
            if line.startswith(label + ":"):
                metricas[label] = line.split(":", 1)[1].strip()
    return metricas


if __name__ == "__main__":
    print("API Bloco 2 — Motor de Transformacao MIMIC-IV")
    print(f"Raiz do projeto : {PROJECT_ROOT}")
    print("Endereco        : http://localhost:5050")
    app.run(host="0.0.0.0", port=5050, debug=True)

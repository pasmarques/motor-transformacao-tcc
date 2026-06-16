"""API Flask — Motor ETL MIMIC-IV (Bloco 2).

Endpoints publicos de transformacao. Nao requerem autenticacao.
Endpoints admin estao em admin_routes.py (requerem JWT).

Iniciar (dev):    python app/api.py
Iniciar (prod):   gunicorn --workers 4 --bind 0.0.0.0:8000 "app.api:create_app()"
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_jwt_extended import JWTManager

load_dotenv()

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

REGRAS_PATH = PROJECT_ROOT / "regras.json"

# Instancia global do transformador (recarregada pelo /admin/reload)
_transformador: JsonTransformador | None = None


def get_transformador() -> JsonTransformador:
    global _transformador
    if _transformador is None:
        _transformador = JsonTransformador()
    return _transformador


def reload_transformador() -> None:
    global _transformador
    _transformador = JsonTransformador()


def create_app() -> Flask:
    app = Flask(__name__)

    # JWT
    app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY", "dev-secret-troque-em-producao")
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = 900   # 15 minutos
    app.config["JWT_REFRESH_TOKEN_EXPIRES"] = 604800  # 7 dias

    # CORS
    cors_origins = os.getenv("CORS_ORIGINS", "*").split(",")
    CORS(app, origins=cors_origins, supports_credentials=True)

    JWTManager(app)

    # Registra blueprints
    from app.auth import auth_bp
    from app.admin_routes import admin_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)

    # ── Endpoints públicos ─────────────────────────────────

    @app.route("/api/variaveis", methods=["GET"])
    def variaveis():
        return jsonify(list(VARIAVEIS_SAIDA_PADRAO))

    @app.route("/api/regras", methods=["GET"])
    def get_regras():
        if not REGRAS_PATH.exists():
            return jsonify({}), 200
        try:
            return jsonify(json.loads(REGRAS_PATH.read_text(encoding="utf-8")))
        except Exception as exc:
            return jsonify({"erro": str(exc)}), 500

    @app.route("/api/plugins", methods=["GET"])
    def get_plugins():
        t = get_transformador()
        return jsonify([
            {"name": p.name, "provides": list(p.provides)}
            for p in t._plugins
        ])

    @app.route("/api/transform", methods=["POST"])
    def transform():
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
        agregacoes = [
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
            return jsonify({"erro": "Nenhum paciente encontrado."}), 404

        transformador = get_transformador()
        df = transformador.transformar_varios_json(
            pacientes_json,
            config=config,
            variaveis_saida=variaveis_saida,
            agregacoes_customizadas=agregacoes,
        )
        if sem_meta:
            df = df.drop(columns=list(METADATA_COLUMNS), errors="ignore")

        report_text = None
        report_metricas = {}
        ref_path = PROJECT_ROOT / "BASEPACIENTES21D_JUN26_FINAL.csv"
        if ref_path.exists():
            ignored = set() if patient_info else NAO_COMPARAVEIS_SEM_PERFIL
            report_text = comparar_com_referencia(df, ref_path, ignored_cols=ignored)
            report_metricas = _parse_report(report_text)

        preview_json = pacientes_json[0] if pacientes_json else {}
        tabela_safe = json.loads(df.to_json(orient="records", default_handler=str))

        return jsonify({
            "n_pacientes":     len(pacientes_json),
            "n_janelas":       sum(len(p.get("mapas_diarios") or []) for p in pacientes_json),
            "n_colunas":       len(df.columns),
            "pacientes_ids":   [int(p["patient_id"]) for p in pacientes_json],
            "preview_json":    preview_json,
            "tabela":          tabela_safe,
            "colunas":         list(df.columns),
            "report_texto":    report_text,
            "report_metricas": report_metricas,
            "perfil_ativo":    patient_info is not None,
        })

    @app.route("/api/paciente_json", methods=["POST"])
    def paciente_json():
        body = request.get_json(force=True)
        pid  = int(body.get("subject_id"))
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

    return app


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
    for label in ["Diagnostico", "Diferencas possivelmente ligadas a perfil/peso/sexo",
                  "Diferencas possivelmente ligadas a recorte/internacao",
                  "Diferencas em regras longitudinais a calibrar",
                  "Nao comparaveis neste modo"]:
        for line in report.splitlines():
            if line.startswith(label + ":"):
                metricas[label] = line.split(":", 1)[1].strip()
    return metricas


if __name__ == "__main__":
    app = create_app()
    print("API Bloco 2 — Motor de Transformacao MIMIC-IV")
    print(f"Raiz do projeto: {PROJECT_ROOT}")
    print("Endereco: http://localhost:5050")
    app.run(host="0.0.0.0", port=5050, debug=True)

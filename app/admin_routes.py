"""Endpoints admin — requerem JWT valido.

Rotas:
    GET    /admin/plugins              — lista plugins ativos
    POST   /admin/plugins/upload       — faz upload de novo plugin .py
    DELETE /admin/plugins/<nome>       — remove plugin
    POST   /admin/reload               — reinicializa o motor
    PUT    /admin/regras               — atualiza regras.json
    GET    /admin/status               — status do motor
"""
from __future__ import annotations

import importlib
import inspect
import json
import logging
import sys
from pathlib import Path

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required

logger = logging.getLogger(__name__)

admin_bp = Blueprint("admin", __name__)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PLUGINS_DIR  = PROJECT_ROOT / "etl_motor" / "plugins"
REGRAS_PATH  = PROJECT_ROOT / "regras.json"
MAX_PLUGIN_SIZE = 50 * 1024  # 50KB


def _get_reload_fn():
    """Importa reload_transformador do api.py evitando import circular."""
    from app.api import reload_transformador
    return reload_transformador


def _validar_plugin(codigo: str) -> tuple[bool, str]:
    """Valida sintaxe e presença de subclasse de BaseModule."""
    # Validar sintaxe
    try:
        compilado = compile(codigo, "<upload>", "exec")
    except SyntaxError as exc:
        return False, f"Erro de sintaxe: {exc}"

    # Executar em namespace isolado e verificar subclasse de BaseModule
    try:
        from etl_motor.base import BaseModule
        namespace: dict = {}
        exec(compilado, namespace)  # noqa: S102
        subclasses = [
            v for v in namespace.values()
            if isinstance(v, type)
            and issubclass(v, BaseModule)
            and v is not BaseModule
        ]
        if not subclasses:
            return False, "Nenhuma subclasse de BaseModule encontrada no arquivo."
        # Verificar que tem name, provides e transform
        for cls in subclasses:
            if not hasattr(cls, "name") or not hasattr(cls, "provides"):
                return False, f"Classe {cls.__name__} deve ter 'name' e 'provides'."
            if not hasattr(cls, "transform"):
                return False, f"Classe {cls.__name__} deve implementar 'transform()'."
    except Exception as exc:
        return False, f"Erro ao validar plugin: {exc}"

    return True, "OK"


@admin_bp.route("/admin/status", methods=["GET"])
@jwt_required()
def status():
    from app.api import get_transformador
    t = get_transformador()
    return jsonify({
        "motor": "online",
        "plugins": [{"name": p.name, "provides": list(p.provides)} for p in t._plugins],
        "n_plugins": len(t._plugins),
    })


@admin_bp.route("/admin/plugins", methods=["GET"])
@jwt_required()
def listar_plugins():
    from app.api import get_transformador
    t = get_transformador()
    plugins_disco = [f.stem for f in PLUGINS_DIR.glob("*.py") if not f.name.startswith("_")]
    ativos = {p.name: list(p.provides) for p in t._plugins}
    return jsonify({
        "plugins_disco": plugins_disco,
        "plugins_ativos": [
            {"name": p.name, "provides": list(p.provides)}
            for p in t._plugins
        ],
    })


@admin_bp.route("/admin/plugins/upload", methods=["POST"])
@jwt_required()
def upload_plugin():
    body = request.get_json(force=True) or {}
    nome = body.get("nome", "").strip()
    codigo = body.get("codigo", "").strip()

    if not nome:
        return jsonify({"erro": "Campo 'nome' é obrigatório."}), 400
    if not nome.endswith(".py"):
        nome += ".py"
    if not codigo:
        return jsonify({"erro": "Campo 'codigo' é obrigatório."}), 400
    if len(codigo.encode()) > MAX_PLUGIN_SIZE:
        return jsonify({"erro": "Arquivo muito grande (máx 50KB)."}), 400
    if ".." in nome or "/" in nome or "\\" in nome:
        return jsonify({"erro": "Nome de arquivo inválido."}), 400

    valido, mensagem = _validar_plugin(codigo)
    if not valido:
        return jsonify({"erro": mensagem}), 422

    destino = PLUGINS_DIR / nome
    destino.write_text(codigo, encoding="utf-8")

    # Recarrega o motor
    _get_reload_fn()()
    logger.info("Plugin '%s' instalado e motor recarregado.", nome)

    return jsonify({"ok": True, "mensagem": f"Plugin '{nome}' instalado com sucesso."}), 201


@admin_bp.route("/admin/plugins/<nome>", methods=["DELETE"])
@jwt_required()
def remover_plugin(nome: str):
    if not nome.endswith(".py"):
        nome += ".py"
    if ".." in nome or "/" in nome:
        return jsonify({"erro": "Nome inválido."}), 400

    alvo = PLUGINS_DIR / nome
    if not alvo.exists():
        return jsonify({"erro": "Plugin não encontrado."}), 404

    alvo.unlink()
    _get_reload_fn()()
    logger.info("Plugin '%s' removido e motor recarregado.", nome)

    return jsonify({"ok": True, "mensagem": f"Plugin '{nome}' removido com sucesso."})


@admin_bp.route("/admin/reload", methods=["POST"])
@jwt_required()
def reload():
    _get_reload_fn()()
    from app.api import get_transformador
    t = get_transformador()
    return jsonify({
        "ok": True,
        "mensagem": "Motor recarregado com sucesso.",
        "plugins_ativos": [p.name for p in t._plugins],
    })


@admin_bp.route("/admin/regras", methods=["PUT"])
@jwt_required()
def atualizar_regras():
    body = request.get_json(force=True)
    if not isinstance(body, dict):
        return jsonify({"erro": "Payload deve ser um objeto JSON."}), 400
    try:
        REGRAS_PATH.write_text(
            json.dumps(body, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        _get_reload_fn()()
        return jsonify({"ok": True, "mensagem": "regras.json atualizado e motor recarregado."})
    except Exception as exc:
        return jsonify({"erro": str(exc)}), 500

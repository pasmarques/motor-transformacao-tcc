"""Autenticacao JWT — login, refresh e logout.

Rotas:
    POST /auth/login    — recebe senha, retorna access token + seta refresh cookie
    POST /auth/refresh  — usa refresh cookie, retorna novo access token
    POST /auth/logout   — invalida refresh token (blacklist em memoria)
"""
from __future__ import annotations

import os
from datetime import timedelta
from pathlib import Path

import bcrypt
from flask import Blueprint, jsonify, request
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    get_jwt_identity,
    jwt_required,
    set_refresh_cookies,
    unset_refresh_cookies,
)

auth_bp = Blueprint("auth", __name__)

# Blacklist em memoria — em producao real usaria Redis
_blacklist: set[str] = set()

ADMIN_USER = "admin"


def _carregar_hash() -> str:
    """Lê o hash bcrypt do arquivo .admin_hash ou da variável de ambiente.

    Usar arquivo evita que o Docker Compose interpole os $ do hash bcrypt.
    """
    # Tenta primeiro o arquivo (preferido em produção)
    hash_file = Path(__file__).resolve().parents[1] / ".admin_hash"
    if hash_file.exists():
        return hash_file.read_text(encoding="utf-8").strip()
    # Fallback para variável de ambiente (com $$ escapados pelo usuário)
    return os.getenv("ADMIN_PASSWORD_HASH", "")


def _verificar_senha(senha: str) -> bool:
    """Verifica a senha contra o hash bcrypt."""
    hash_val = _carregar_hash()
    if not hash_val:
        return False
    try:
        return bcrypt.checkpw(senha.encode(), hash_val.encode())
    except Exception:
        return False


@auth_bp.route("/auth/login", methods=["POST"])
def login():
    body = request.get_json(force=True) or {}
    senha = body.get("senha", "")

    if not _verificar_senha(senha):
        return jsonify({"erro": "Senha incorreta."}), 401

    access_token = create_access_token(
        identity=ADMIN_USER,
        expires_delta=timedelta(minutes=15),
    )
    refresh_token = create_refresh_token(
        identity=ADMIN_USER,
        expires_delta=timedelta(days=7),
    )

    resp = jsonify({"access_token": access_token, "token_type": "bearer"})
    set_refresh_cookies(resp, refresh_token)
    return resp, 200


@auth_bp.route("/auth/refresh", methods=["POST"])
@jwt_required(refresh=True)
def refresh():
    identity = get_jwt_identity()
    access_token = create_access_token(
        identity=identity,
        expires_delta=timedelta(minutes=15),
    )
    return jsonify({"access_token": access_token, "token_type": "bearer"}), 200


@auth_bp.route("/auth/logout", methods=["POST"])
@jwt_required(refresh=True)
def logout():
    resp = jsonify({"mensagem": "Logout realizado com sucesso."})
    unset_refresh_cookies(resp)
    return resp, 200

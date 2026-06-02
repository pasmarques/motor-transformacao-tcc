"""Gera o hash bcrypt da senha admin e salva em .admin_hash.

Uso:
    python scripts/gerar_hash_senha.py
"""
import getpass
import bcrypt
from pathlib import Path

def main():
    senha = getpass.getpass("Digite a senha do admin: ")
    confirmacao = getpass.getpass("Confirme a senha: ")
    if senha != confirmacao:
        print("As senhas nao conferem.")
        return
    hash_gerado = bcrypt.hashpw(senha.encode(), bcrypt.gensalt(rounds=12)).decode()
    destino = Path(__file__).resolve().parents[1] / ".admin_hash"
    destino.write_text(hash_gerado, encoding="utf-8")
    print(f"Hash salvo em {destino}")

if __name__ == "__main__":
    main()

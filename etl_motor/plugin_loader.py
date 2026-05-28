"""Carregador automatico de modulos plugin do motor ETL MIMIC-IV.

Qualquer arquivo .py colocado em etl_motor/plugins/ que contenha uma classe
que herde de BaseModule sera detectado e carregado automaticamente.
Nenhuma alteracao no codigo do motor e necessaria.

Uso:
    from etl_motor.plugin_loader import descobrir_plugins
    plugins = descobrir_plugins()   # lista de instancias prontas
"""
from __future__ import annotations

import importlib
import importlib.util
import inspect
import logging
import sys
from pathlib import Path

from etl_motor.base import BaseModule

logger = logging.getLogger(__name__)

# Pasta padrao onde os plugins sao procurados
PLUGINS_DIR = Path(__file__).resolve().parent / "plugins"


def descobrir_plugins(
    plugins_dir: Path | None = None,
    regras: dict | None = None,
) -> list[BaseModule]:
    """Escaneia plugins_dir e retorna instancias de todos os BaseModule encontrados.

    Args:
        plugins_dir: Pasta a escanear. Padrao: etl_motor/plugins/
        regras:      Dict de regras clinicas repassado aos plugins que aceitarem.

    Returns:
        Lista de instancias prontas para uso no OrquestradorETL.
    """
    plugins_dir = plugins_dir or PLUGINS_DIR
    if not plugins_dir.exists():
        return []

    instancias: list[BaseModule] = []
    arquivos = sorted(plugins_dir.glob("*.py"))

    for arquivo in arquivos:
        if arquivo.name.startswith("_"):
            continue  # ignora __init__.py e arquivos privados

        modulo_nome = f"etl_motor.plugins.{arquivo.stem}"
        try:
            # importa o arquivo como modulo Python
            if modulo_nome in sys.modules:
                modulo = sys.modules[modulo_nome]
            else:
                spec = importlib.util.spec_from_file_location(modulo_nome, arquivo)
                modulo = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
                sys.modules[modulo_nome] = modulo
                spec.loader.exec_module(modulo)  # type: ignore[union-attr]

            # coleta todas as subclasses de BaseModule definidas nesse arquivo
            for _nome, classe in inspect.getmembers(modulo, inspect.isclass):
                if (
                    issubclass(classe, BaseModule)
                    and classe is not BaseModule
                    and classe.__module__ == modulo_nome
                ):
                    instancia = _instanciar(classe, regras)
                    if instancia is not None:
                        instancias.append(instancia)
                        logger.info("Plugin carregado: %s (%s)", classe.__name__, arquivo.name)

        except Exception as exc:  # noqa: BLE001
            # Plugin com erro nao derruba o motor — apenas registra aviso
            logger.warning("Plugin ignorado (%s): %s", arquivo.name, exc)

    return instancias


def _instanciar(classe: type, regras: dict | None) -> BaseModule | None:
    """Tenta instanciar a classe do plugin com ou sem regras."""
    try:
        # tenta passar regras se o construtor aceitar
        sig = inspect.signature(classe.__init__)
        if "regras" in sig.parameters and regras is not None:
            return classe(regras=regras)
        return classe()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Nao foi possivel instanciar %s: %s", classe.__name__, exc)
        return None

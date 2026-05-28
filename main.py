from __future__ import annotations

import argparse
import json
from pathlib import Path

from etl_motor.config import TransformConfig
from etl_motor.json_transformer import JsonTransformador
from etl_motor.mapas_json import converter_entradas_para_jsons, salvar_jsons_entradas
from etl_motor.personalizacao import (
    METADATA_COLUMNS,
    parse_agregacao_spec,
    parse_variaveis_saida,
)
from etl_motor.validation import NAO_COMPARAVEIS_SEM_PERFIL, comparar_com_referencia


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Motor ETL MIMIC-IV para TCC.")
    parser.add_argument("--all", action="store_true", help="Processa todos os pacientes.")
    parser.add_argument("--debug", action="store_true", help="Mostra auditoria detalhada de um paciente.")
    parser.add_argument("--json-input", default=None, help="Arquivo JSON de um paciente padronizado.")
    parser.add_argument("--entradas-dir", default=None, required=True, help="Pasta com mapas diarios CSV separados por variavel.")
    parser.add_argument("--json-output", default=None, help="Salva o JSON gerado a partir dos mapas diarios.")
    parser.add_argument("--json-only", action="store_true", help="Apenas gera o JSON dos mapas diarios e encerra.")
    parser.add_argument("--preview-json", action="store_true", help="Mostra um preview do JSON gerado.")
    parser.add_argument(
        "--patient-info-file",
        default=None,
        help="Arquivo CSV com perfil dos pacientes (ex: ICUpatients21D.csv).",
    )
    parser.add_argument("--subject-id", type=int, default=None, help="Paciente especifico para processar/debugar.")
    parser.add_argument("--tamanho-janela-horas", type=float, default=24.0, help="Tamanho da janela recebida.")
    parser.add_argument("--cortar-janelas-finais", type=int, default=0, help="Quantidade de janelas finais a remover.")
    parser.add_argument("--max-janelas", type=int, default=None, help="Limita as primeiras N janelas.")
    parser.add_argument("--data-referencia", default=None, help="Limite temporal opcional.")
    parser.add_argument("--output", default="dataset_transformado.csv", help="CSV de saida no modo --all.")
    parser.add_argument("--compare-output", default=None, help="CSV de referencia para comparar a saida gerada.")
    parser.add_argument("--variaveis-saida", default=None, help="Lista separada por virgulas das variaveis finais.")
    parser.add_argument("--variaveis-saida-file", default=None, help="Arquivo com variaveis finais, uma por linha.")
    parser.add_argument(
        "--agregacao",
        action="append",
        default=[],
        help="Agregacao customizada no formato origem:funcao:nome_saida. Pode repetir.",
    )
    parser.add_argument("--sem-metadados", action="store_true", help="Remove colunas auxiliares do motor no CSV.")
    return parser.parse_args()


def config_from_args(args: argparse.Namespace) -> TransformConfig:
    return TransformConfig(
        tamanho_janela_horas=args.tamanho_janela_horas,
        cortar_janelas_finais=args.cortar_janelas_finais,
        max_janelas=args.max_janelas,
        data_referencia=args.data_referencia,
    )


def resolve_path(base_dir: Path, value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else base_dir / path


def personalizacao_from_args(args: argparse.Namespace, base_dir: Path) -> tuple[list[str] | None, list]:
    variaveis = parse_variaveis_saida(args.variaveis_saida)
    if args.variaveis_saida_file:
        text = resolve_path(base_dir, args.variaveis_saida_file).read_text(encoding="utf-8")
        variaveis.extend(parse_variaveis_saida(text))
    agregacoes = [parse_agregacao_spec(spec) for spec in args.agregacao]
    return (variaveis or None), agregacoes


def aplicar_saida_cli(df_final, args):
    if args.sem_metadados:
        return df_final.drop(columns=list(METADATA_COLUMNS), errors="ignore")
    return df_final


if __name__ == "__main__":
    args = parse_args()
    base_dir = Path(__file__).resolve().parent
    config = config_from_args(args)
    variaveis_saida, agregacoes_customizadas = personalizacao_from_args(args, base_dir)

    # --- Rota 1: JSON direto ---
    if args.json_input:
        with open(resolve_path(base_dir, args.json_input), "r", encoding="utf-8") as file:
            payload_json = json.load(file)
        transformador = JsonTransformador()
        if isinstance(payload_json, list):
            if args.preview_json and payload_json:
                print(json.dumps(payload_json[0], indent=2, ensure_ascii=False, allow_nan=False))
            df_final = transformador.transformar_varios_json(
                payload_json,
                config=config,
                variaveis_saida=variaveis_saida,
                agregacoes_customizadas=agregacoes_customizadas,
            )
            df_final = aplicar_saida_cli(df_final, args)
            output_path = resolve_path(base_dir, args.output)
            df_final.to_csv(output_path, index=False)
            print(f"Arquivo gerado: {output_path}")
            print(f"Linhas: {len(df_final)} | Colunas: {len(df_final.columns)}")
            if args.compare_output:
                print(comparar_com_referencia(df_final, resolve_path(base_dir, args.compare_output)))
        else:
            print(transformador.transformar_json(
                payload_json,
                config=config,
                variaveis_saida=variaveis_saida,
                agregacoes_customizadas=agregacoes_customizadas,
            ))
        raise SystemExit(0)

    # --- Rota 2: mapas diários CSV (entradas/) ---
    subject_ids = [args.subject_id] if args.subject_id is not None else None
    pacientes_json = converter_entradas_para_jsons(
        base_dir=base_dir,
        entradas_dir=args.entradas_dir,
        patient_info_file=args.patient_info_file,
        subject_ids=subject_ids,
    )
    if not pacientes_json:
        raise SystemExit("Nenhum paciente encontrado nos mapas diarios.")

    if args.json_output:
        json_output_path = salvar_jsons_entradas(
            resolve_path(base_dir, args.json_output),
            pacientes_json,
        )
        print(f"JSON gerado: {json_output_path}")

    if args.preview_json:
        print(json.dumps(pacientes_json[0], indent=2, ensure_ascii=False, allow_nan=False))

    if args.json_only:
        raise SystemExit(0)

    transformador = JsonTransformador()
    ignored_cols = set() if args.patient_info_file else NAO_COMPARAVEIS_SEM_PERFIL

    if args.all:
        df_final = transformador.transformar_varios_json(
            pacientes_json,
            config=config,
            variaveis_saida=variaveis_saida,
            agregacoes_customizadas=agregacoes_customizadas,
        )
        df_final = aplicar_saida_cli(df_final, args)
        output_path = resolve_path(base_dir, args.output)
        df_final.to_csv(output_path, index=False)
        print(f"Arquivo gerado: {output_path}")
        print(f"Linhas: {len(df_final)} | Colunas: {len(df_final.columns)}")
        if args.compare_output:
            print(comparar_com_referencia(
                df_final,
                resolve_path(base_dir, args.compare_output),
                ignored_cols=ignored_cols,
            ))
    else:
        resultado = transformador.transformar_json(
            pacientes_json[0],
            config=config,
            variaveis_saida=variaveis_saida,
            agregacoes_customizadas=agregacoes_customizadas,
        )
        if args.sem_metadados:
            for column in METADATA_COLUMNS:
                resultado.pop(column, None)
        print(resultado)

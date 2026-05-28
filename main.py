from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from etl_motor.config import TransformConfig
from etl_motor.debug import DebugPaciente
from etl_motor.json_transformer import JsonTransformador
from etl_motor.mapas_json import converter_entradas_para_jsons, salvar_jsons_entradas
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
from etl_motor.personalizacao import (
    METADATA_COLUMNS,
    parse_agregacao_spec,
    parse_variaveis_saida,
)
from etl_motor.validation import NAO_COMPARAVEIS_SEM_PERFIL, comparar_com_referencia


def carregar_orquestrador(base_dir: Path) -> tuple[OrquestradorETL, pd.DataFrame]:
    patients = pd.read_csv(base_dir / "ICUpatients21D.csv")
    windows = pd.read_csv(base_dir / "ICUNewWindow24.csv")
    balanco_hidrico = pd.read_csv(base_dir / "ICUFBDiario - ICUFBDiario.csv")
    evacuacao = pd.read_excel(base_dir / "EvacuacaoProporcao.xlsx")

    modules = [
        ModuloPerfil(),
        ModuloInternacao(),
        ModuloBalancoHidrico(balanco_hidrico),
        ModuloEvacuacao(evacuacao),
        ModuloNutricao(),
        ModuloVentilacaoMecanica(),
        ModuloHemodialise(),
        ModuloDrogasVasoativas(),
        ModuloSinaisVitais(),
        ModuloLaboratorio(),
    ]

    orquestrador = OrquestradorETL(
        patients_df=patients,
        windows_df=windows,
        modules=modules,
    )
    return orquestrador, patients


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Motor ETL MIMIC-IV para TCC.")
    parser.add_argument("--all", action="store_true", help="Processa todos os pacientes.")
    parser.add_argument("--debug", action="store_true", help="Mostra auditoria detalhada de um paciente.")
    parser.add_argument("--json-input", default=None, help="Arquivo JSON de um paciente padronizado.")
    parser.add_argument("--entradas-dir", default=None, help="Pasta com mapas diarios CSV separados por variavel.")
    parser.add_argument("--json-output", default=None, help="Salva o JSON gerado a partir dos mapas diarios.")
    parser.add_argument("--json-only", action="store_true", help="Apenas gera o JSON dos mapas diarios e encerra.")
    parser.add_argument("--preview-json", action="store_true", help="Mostra um preview do JSON gerado.")
    parser.add_argument(
        "--patient-info-file",
        default=None,
        help="Arquivo opcional para enriquecer perfil/internacao como mock explicito do Bloco 1.",
    )
    parser.add_argument("--subject-id", type=int, default=None, help="Paciente especifico para processar/debugar.")
    parser.add_argument(
        "--offset-dias",
        type=int,
        default=0,
        help="Compatibilidade: recorte de janelas. -1 corta uma janela final; 0 usa todas.",
    )
    parser.add_argument("--tamanho-janela-horas", type=float, default=24.0, help="Tamanho da janela recebida.")
    parser.add_argument("--cortar-janelas-finais", type=int, default=None, help="Quantidade de janelas finais a remover.")
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
    if args.cortar_janelas_finais is None and args.max_janelas is None and args.data_referencia is None:
        legacy = TransformConfig.from_legacy_offset(args.offset_dias)
        return TransformConfig(
            tamanho_janela_horas=args.tamanho_janela_horas,
            cortar_janelas_finais=legacy.cortar_janelas_finais,
            max_janelas=legacy.max_janelas,
        )
    return TransformConfig(
        tamanho_janela_horas=args.tamanho_janela_horas,
        cortar_janelas_finais=args.cortar_janelas_finais or 0,
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


def aplicar_saida_cli(df_final: pd.DataFrame, args: argparse.Namespace) -> pd.DataFrame:
    if args.sem_metadados:
        return df_final.drop(columns=list(METADATA_COLUMNS), errors="ignore")
    return df_final


if __name__ == "__main__":
    args = parse_args()
    base_dir = Path(__file__).resolve().parent
    config = config_from_args(args)
    variaveis_saida, agregacoes_customizadas = personalizacao_from_args(args, base_dir)

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
            if args.all or args.output or args.compare_output:
                output_path = resolve_path(base_dir, args.output)
                df_final.to_csv(output_path, index=False)
                print(f"Arquivo gerado: {output_path}")
                print(f"Linhas: {len(df_final)} | Colunas: {len(df_final.columns)}")
                print(df_final.head().to_string(index=False))
                if args.compare_output:
                    print(comparar_com_referencia(df_final, resolve_path(base_dir, args.compare_output)))
            else:
                print(df_final.to_string(index=False))
        elif args.debug:
            print(transformador.gerar_auditoria_json(payload_json, config=config))
        else:
            print(
                transformador.transformar_json(
                    payload_json,
                    config=config,
                    variaveis_saida=variaveis_saida,
                    agregacoes_customizadas=agregacoes_customizadas,
                )
            )
        raise SystemExit(0)

    if args.entradas_dir:
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

        if args.debug:
            print(transformador.gerar_auditoria_json(pacientes_json[0], config=config))
        elif args.all:
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
            print(df_final.head().to_string(index=False))
            if args.compare_output:
                print(
                    comparar_com_referencia(
                        df_final,
                        resolve_path(base_dir, args.compare_output),
                        ignored_cols=ignored_cols,
                    )
                )
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
        raise SystemExit(0)
    else:
        orchestrator, patients = carregar_orquestrador(base_dir)

    subject_id = args.subject_id or int(patients["subject_id"].iloc[0])

    if args.debug:
        print(DebugPaciente(orchestrator).gerar_relatorio(subject_id, args.offset_dias, config=config))
    elif args.all:
        df_final = orchestrator.transformar_todos(config=config)
        df_final = aplicar_saida_cli(df_final, args)
        output_path = resolve_path(base_dir, args.output)
        df_final.to_csv(output_path, index=False)
        print(f"Arquivo gerado: {output_path}")
        print(f"Linhas: {len(df_final)} | Colunas: {len(df_final.columns)}")
        print(df_final.head().to_string(index=False))
        if args.compare_output:
            print(comparar_com_referencia(df_final, resolve_path(base_dir, args.compare_output)))
    else:
        resultado = orchestrator.transformar_paciente(
            subject_id=subject_id,
            config=config,
        )
        print(resultado)

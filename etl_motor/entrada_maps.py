"""Carregamento e combinacao dos mapas diarios da pasta entradas/.

Responsabilidade: ler os ~30 CSVs, fundir por (subject_id, day) e devolver
um unico DataFrame que o modulo mapas_json.py consomira para montar o JSON
padronizado do Bloco 2.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from etl_motor.cleaning import DataCleaner

# ---------------------------------------------------------------------------
# Mapeamento: arquivo → lista de (coluna_csv, coluna_interna)
# Colunas de tempo (start_time, end_time, starttime) sao ignoradas — vem
# do ICUNewWindow24.csv ou sao computadas.
# ---------------------------------------------------------------------------
_ARQUIVOS: list[tuple[str, list[tuple[str, str]]]] = [
    ("ICUMapaDiarioBalancoHidrico", [
        ("BHDia", "BHDia"),
    ]),
    ("ICUMapaDiarioEvacuacao", [
        ("evacuation", "evacuation"),
    ]),
    ("ICUMapaDiarioProteinasCalorias", [
        ("calories_intake",    "calorias_kcal"),
        ("protein_intake",     "proteinas_g"),
        ("calories_intake_KgD", "calorias_kcal_kg_dia"),
        ("protein_intake_KgD",  "proteinas_g_kg_dia"),
    ]),
    ("ICUMapaDiarioVM", [
        ("VM", "vm_em_uso"),
    ]),
    ("ICUMapaDiarioHemodialise", [
        ("hemodialysis", "hemodialise_presente"),
    ]),
    ("ICUMapaDiarioNoraMax", [
        ("MaxNoraDia", "nora_dose_maxima"),
    ]),
    ("ICUMapaDiarioVaso", [
        ("UsoVaso", "vasopressina_em_uso"),
    ]),
    # Sinais vitais (min + max → lista)
    ("ICUMapaDiarioTemperatura", [
        ("temperaturemax", "_temperatura_max"),
        ("temperaturemin", "_temperatura_min"),
    ]),
    ("ICUMapaDiarioHGT", [
        ("nHGTMaxDia", "_hgt_max"),
        ("nHGTMinDia", "_hgt_min"),
    ]),
    ("ICUMapaDiarioPAS", [
        ("nPASMaxDia", "_pas_max"),
        ("nPASMinDia", "_pas_min"),
    ]),
    ("ICUMapaDiarioPAD", [
        ("nPADMaxDia", "_pad_max"),
        ("nPADMinDia", "_pad_min"),
    ]),
    ("ICUMapaDiarioPAM", [
        ("nPAMMaxDia", "_pam_max"),
        ("nPAMMinDia", "_pam_min"),
    ]),
    # Laboratorio (min + max → lista)
    ("ICUMapaDiarioPH", [
        ("nPHMaxDia", "_ph_max"),
        ("nPHMinDia", "_ph_min"),
    ]),
    ("ICUMapaDiarioUreia", [
        ("nUreiaMaxDia", "_ureia_max"),
        ("nUreiaMinDia", "_ureia_min"),
    ]),
    ("ICUMapaDiarioCreatinina", [
        ("nCreatininaMaxDia", "_creatinina_max"),
        ("nCreatininaMinDia", "_creatinina_min"),
    ]),
    ("ICUMapaDiarioSodio", [
        ("nSodioMaxDia", "_sodio_max"),
        ("nSodioMinDia", "_sodio_min"),
    ]),
    ("ICUMapaDiarioPotassio", [
        ("nPotassioMaxDia", "_potassio_max"),
        ("nPotassioMinDia", "_potassio_min"),
    ]),
    ("ICUMapaDiarioMagnesio", [
        ("nMagnesioMaxDia", "_magnesio_max"),
        ("nMagnesioMinDia", "_magnesio_min"),
    ]),
    ("ICUMapaDiarioFosforo", [
        ("nFosforoMaxDia", "_fosforo_max"),
        ("nFosforoMinDia", "_fosforo_min"),
    ]),
    ("ICUMapaDiarioAlbumina", [
        ("nAlbuminaMinDia", "_albumina_min"),
    ]),
    ("ICUMapaDiarioLinfocitosTotais", [
        ("nLinfoTotaisMaxDia", "_linfocitos_totais_max"),
        ("nLinfoTotaisMinDia", "_linfocitos_totais_min"),
    ]),
    ("ICUMapaDiarioHemoglobina", [
        ("nHemoglobinaMaxDia", "_hemoglobina_max"),
        ("nHemoglobinaMinDia", "_hemoglobina_min"),
    ]),
    ("ICUMapaDiarioAspartato", [
        ("nASTMaxDia", "_ast_max"),
    ]),
    ("ICUMapaDiarioAlanina", [
        ("nALTMaxDia", "_alt_max"),
    ]),
    ("ICUMapaDiarioBilirrubinas", [
        ("nBilirrubinaMaxDia", "_bilirrubina_max"),
    ]),
    ("ICUMapaDiarioTriglicerides", [
        ("nTrigliceridesMaxDia", "_triglicerides_max"),
    ]),
    ("ICUMapaDiarioFosfatase", [
        ("nFosfatAlcalinaMaxDia", "_fosfatase_alcalina_max"),
    ]),
    ("ICUMapaDiarioWBC", [
        ("nWBCMaxDia", "_wbc_max"),
        ("nWBCMinDia", "_wbc_min"),
    ]),
    ("ICUMapaDiarioPlaquetas", [
        ("nPlaquetasMaxDia", "_plaquetas_max"),
        ("nPlaquetasMinDia", "_plaquetas_min"),
    ]),
    ("ICUMapaDiarioAcidoLatico", [
        ("nLactatoMaxDia", "_lactato_max"),
        ("nLactatoMinDia", "_lactato_min"),
    ]),
]

# Variaveis que precisam ser compostas a partir de colunas _min/_max
_LIST_VARS: dict[str, tuple[str, ...]] = {
    "temperatura":       ("_temperatura_max", "_temperatura_min"),
    "hgt":               ("_hgt_max",         "_hgt_min"),
    "pas":               ("_pas_max",          "_pas_min"),
    "pad":               ("_pad_max",          "_pad_min"),
    "pam":               ("_pam_max",          "_pam_min"),
    "ph":                ("_ph_max",           "_ph_min"),
    "ureia":             ("_ureia_max",         "_ureia_min"),
    "creatinina":        ("_creatinina_max",    "_creatinina_min"),
    "sodio":             ("_sodio_max",         "_sodio_min"),
    "potassio":          ("_potassio_max",      "_potassio_min"),
    "magnesio":          ("_magnesio_max",      "_magnesio_min"),
    "fosforo":           ("_fosforo_max",       "_fosforo_min"),
    "albumina":          ("_albumina_min",),
    "linfocitos_totais": ("_linfocitos_totais_max", "_linfocitos_totais_min"),
    "hemoglobina":       ("_hemoglobina_max",   "_hemoglobina_min"),
    "ast":               ("_ast_max",),
    "alt":               ("_alt_max",),
    "bilirrubina":       ("_bilirrubina_max",),
    "triglicerides":     ("_triglicerides_max",),
    "fosfatase_alcalina": ("_fosfatase_alcalina_max",),
    "wbc":               ("_wbc_max",           "_wbc_min"),
    "plaquetas":         ("_plaquetas_max",      "_plaquetas_min"),
    "lactato":           ("_lactato_max",        "_lactato_min"),
}

# Colunas de tempo nos CSVs individuais — ignoradas no merge (ja vem da base)
_TIME_COLS = {"start_time", "end_time", "starttime", "diff_end_start"}


def _carregar_windows(entradas_dir: Path) -> pd.DataFrame:
    """Carrega todos os CSVs de entradas_dir e os funde por (subject_id, day).

    Cada mapa diario enviado pela professora ja contem start_time (e alguns
    contem end_time). A base temporal e construida fazendo a uniao de todos
    os pares (subject_id, day) encontrados nos CSVs, preenchendo start_time
    e end_time com o primeiro valor nao-nulo encontrado por par.
    """
    entradas_dir = Path(entradas_dir)

    # --- Passo 1: construir a base temporal a partir da uniao de todos os CSVs ---
    bases: list[pd.DataFrame] = []
    for path in sorted(entradas_dir.glob("*.csv")):
        try:
            header = pd.read_csv(path, nrows=0).columns.tolist()
        except Exception:
            continue

        cols_tempo = [c for c in header if c.lower() in {"start_time", "end_time", "starttime"}]
        cols_ler = ["subject_id", "day"] + cols_tempo
        try:
            tmp = pd.read_csv(path, usecols=cols_ler)
        except Exception:
            continue

        tmp["subject_id"] = pd.to_numeric(tmp["subject_id"], errors="coerce")
        tmp["day"] = pd.to_numeric(tmp["day"], errors="coerce")
        tmp = tmp.dropna(subset=["subject_id", "day"])
        tmp["subject_id"] = tmp["subject_id"].astype(int)
        tmp["day"] = tmp["day"].astype(int)

        # Normalizar nomes de colunas de tempo
        tmp = tmp.rename(columns={"starttime": "start_time"})

        bases.append(tmp[["subject_id", "day"]
                         + [c for c in ["start_time", "end_time"] if c in tmp.columns]])

    if not bases:
        raise FileNotFoundError(f"Nenhum CSV encontrado em {entradas_dir}")

    # Uniao: todos os pares (subject_id, day) de todos os arquivos
    base = pd.concat(bases, ignore_index=True)

    # Para cada par, pegar o primeiro start_time e end_time nao-nulo
    for col in ["start_time", "end_time"]:
        if col not in base.columns:
            base[col] = pd.NaT
    base = (
        base.sort_values(["subject_id", "day"])
        .groupby(["subject_id", "day"], as_index=False)
        .first()
    )

    # Onde end_time ainda e nulo, calcular como start_time + 24 h
    base["start_time"] = pd.to_datetime(
        base["start_time"].astype(str).str.replace(" UTC", "", regex=False),
        errors="coerce",
    )
    base["end_time"] = pd.to_datetime(
        base["end_time"].astype(str).str.replace(" UTC", "", regex=False),
        errors="coerce",
    )
    mask_sem_end = base["end_time"].isna() & base["start_time"].notna()
    base.loc[mask_sem_end, "end_time"] = (
        base.loc[mask_sem_end, "start_time"] + pd.Timedelta(hours=24)
    )

    df = base.copy()

    # --- Passo 2: merge de cada CSV com suas colunas clinicas ---
    for arquivo, mapeamentos in _ARQUIVOS:
        path = entradas_dir / f"{arquivo}.csv"
        if not path.exists():
            continue

        csv_cols_originais = {m[0] for m in mapeamentos}
        try:
            tmp = pd.read_csv(
                path,
                usecols=lambda c: c in csv_cols_originais | {"subject_id", "day"},
            )
        except Exception:
            continue

        tmp["subject_id"] = pd.to_numeric(tmp["subject_id"], errors="coerce").astype("Int64")
        tmp["day"] = pd.to_numeric(tmp["day"], errors="coerce").astype("Int64")
        tmp = tmp.dropna(subset=["subject_id", "day"])
        tmp["subject_id"] = tmp["subject_id"].astype(int)
        tmp["day"] = tmp["day"].astype(int)

        rename_map = {m[0]: m[1] for m in mapeamentos}
        tmp = tmp.rename(columns=rename_map)

        cols_internas = [m[1] for m in mapeamentos]
        colunas_merge = ["subject_id", "day"] + [c for c in cols_internas if c in tmp.columns]
        df = df.merge(tmp[colunas_merge], on=["subject_id", "day"], how="left")

    # --- Passo 3: limpeza do BHDia ---
    if "BHDia" in df.columns:
        df["BHDia"] = DataCleaner.dirty_balance_series_to_float(df["BHDia"])

    # --- Passo 4: combinar _min/_max em listas ---
    for var, componentes in _LIST_VARS.items():
        presentes = [c for c in componentes if c in df.columns]
        if not presentes:
            continue
        df[var] = df[presentes].apply(
            lambda row: [v for v in row.tolist() if pd.notna(v)],
            axis=1,
        )
        df.drop(columns=presentes, inplace=True, errors="ignore")

    return df

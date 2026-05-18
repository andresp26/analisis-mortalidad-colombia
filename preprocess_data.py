"""
Pre-procesa los datos y genera un único archivo Parquet listo para el dashboard.
Ejecutar localmente UNA VEZ antes de desplegar.

Uso:
    python preprocess_data.py

Genera: data/dashboard_ready.parquet
"""

from pathlib import Path
import unicodedata
import warnings

import pandas as pd

warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

MONTH_NAME_MAP = {
    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
    5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
    9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre",
}

AGE_CATEGORY_MAP = {
    0: "Mortalidad neonatal", 1: "Mortalidad neonatal", 2: "Mortalidad neonatal",
    3: "Mortalidad neonatal", 4: "Mortalidad neonatal",
    5: "Mortalidad infantil", 6: "Mortalidad infantil",
    7: "Primera infancia", 8: "Primera infancia",
    9: "Niñez", 10: "Niñez",
    11: "Adolescencia",
    12: "Juventud", 13: "Juventud",
    14: "Adultez temprana", 15: "Adultez temprana", 16: "Adultez temprana",
    17: "Adultez intermedia", 18: "Adultez intermedia", 19: "Adultez intermedia",
    20: "Vejez", 21: "Vejez", 22: "Vejez", 23: "Vejez", 24: "Vejez",
    25: "Longevidad / Centenarios", 26: "Longevidad / Centenarios",
    27: "Longevidad / Centenarios", 28: "Longevidad / Centenarios",
    29: "Edad desconocida",
}


def strip_accents(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", str(value))
    return "".join(char for char in normalized if not unicodedata.combining(char))


def normalize_text(value: str) -> str:
    return " ".join(strip_accents(value).upper().replace("_", " ").split())


def find_column(dataframe, candidates):
    normalized = {normalize_text(column): column for column in dataframe.columns}
    for candidate in candidates:
        key = normalize_text(candidate)
        if key in normalized:
            return normalized[key]
    for column in dataframe.columns:
        normalized_column = normalize_text(column)
        if any(normalize_text(candidate) in normalized_column for candidate in candidates):
            return column
    return None


def clean_string_series(series):
    cleaned = series.astype("string").str.strip()
    return cleaned.replace({"<NA>": pd.NA, "nan": pd.NA, "None": pd.NA, "NONE": pd.NA, "": pd.NA})


def standardize_sex(value) -> str:
    if pd.isna(value):
        return "Sin dato"
    text_value = normalize_text(value)
    if text_value in {"1", "M", "HOMBRE", "MASCULINO", "MALE"}:
        return "Hombre"
    if text_value in {"2", "F", "MUJER", "FEMENINO", "FEMALE"}:
        return "Mujer"
    if text_value in {"3", "I", "INDETERMINADO"}:
        return "Indeterminado"
    return "Sin dato"


def main():
    print("Leyendo archivos fuente...")

    # Read source files
    mort_path = DATA_DIR / "NoFetal2019.parquet"
    if not mort_path.exists():
        mort_path = DATA_DIR / "NoFetal2019.xlsx"
    mortality = pd.read_parquet(mort_path) if mort_path.suffix == ".parquet" else pd.read_excel(mort_path)

    causes_path = DATA_DIR / "CodigosDeMuerte.parquet"
    if not causes_path.exists():
        causes_path = DATA_DIR / "CodigosDeMuerte.xlsx"
    causes = pd.read_parquet(causes_path) if causes_path.suffix == ".parquet" else pd.read_excel(causes_path, skiprows=8)

    divipola_path = DATA_DIR / "Divipola.parquet"
    if not divipola_path.exists():
        divipola_path = DATA_DIR / "Divipola.xlsx"
    divipola = pd.read_parquet(divipola_path) if divipola_path.suffix == ".parquet" else pd.read_excel(divipola_path)

    mortality.columns = [str(c).strip() for c in mortality.columns]

    print(f"  Registros de mortalidad: {len(mortality):,}")

    # --- Join Divipola ---
    if not divipola.empty:
        divipola.columns = [str(c).strip() for c in divipola.columns]
        dept_col = find_column(divipola, ["DEPARTAMENTO"])
        mun_col = find_column(divipola, ["MUNICIPIO"])
        dane_col = find_column(divipola, ["COD_DANE"])
        if dept_col:
            divipola[dept_col] = divipola[dept_col].ffill()
        if dane_col and dept_col and mun_col:
            div_sub = divipola[[dane_col, dept_col, mun_col]].drop_duplicates(subset=[dane_col]).copy()
            div_sub = div_sub.rename(columns={dane_col: "COD_DANE", dept_col: "_dept", mun_col: "_mun"})
            mortality = mortality.merge(div_sub, on="COD_DANE", how="left")
            mortality["department"] = clean_string_series(mortality["_dept"])
            mortality["municipality"] = clean_string_series(mortality["_mun"])
            mortality.drop(columns=["_dept", "_mun"], inplace=True)
        else:
            mortality["department"] = "Sin dato"
            mortality["municipality"] = "Sin dato"
    else:
        mortality["department"] = "Sin dato"
        mortality["municipality"] = "Sin dato"

    # Department code
    dept_code_col = find_column(mortality, ["COD_DEPARTAMENTO"])
    if dept_code_col:
        mortality["dept_code"] = pd.to_numeric(mortality[dept_code_col], errors="coerce")
    else:
        mortality["dept_code"] = pd.NA

    # Month
    mes_col = find_column(mortality, ["MES"])
    if mes_col:
        mortality["month"] = pd.to_numeric(mortality[mes_col], errors="coerce").map(MONTH_NAME_MAP)
    else:
        mortality["month"] = pd.NA

    # Sex
    sex_col = find_column(mortality, ["SEXO", "SEX"])
    mortality["sex"] = mortality[sex_col].map(standardize_sex) if sex_col else "Sin dato"

    # Age
    age_col = find_column(mortality, ["GRUPO_EDAD1", "GRUPO DE EDAD1", "EDAD_GRUPO"])
    if age_col:
        mortality["age_group_code"] = pd.to_numeric(mortality[age_col], errors="coerce")
    else:
        mortality["age_group_code"] = pd.NA
    mortality["age_category"] = mortality["age_group_code"].map(AGE_CATEGORY_MAP).fillna("Edad desconocida")

    # Cause code
    cause_col = find_column(mortality, ["COD_MUERTE", "CAUSA", "COD_CAUSA", "CODIGO_CAUSA", "CIE10"])
    if cause_col:
        mortality["cause_code"] = clean_string_series(mortality[cause_col].astype(str)).str.upper()
    else:
        mortality["cause_code"] = "SIN CODIGO"
    mortality["cause_name"] = pd.NA

    # --- Join causes ---
    if not causes.empty:
        causes.columns = [str(c).strip() for c in causes.columns]
        code_4_col = find_column(causes, [
            "Código de la CIE-10 cuatro caracteres",
            "Codigo de la CIE-10 cuatro caracteres",
            "CIE10 4", "CODIGO 4",
        ])
        name_4_col = find_column(causes, [
            "Descripcion de códigos mortalidad a cuatro caracteres",
            "Descripción de códigos mortalidad a cuatro caracteres",
            "Descripcion de codigos mortalidad a cuatro caracteres",
            "DESC 4", "DESCRIPCION 4",
        ])
        if code_4_col and name_4_col:
            causes_sub = causes[[code_4_col, name_4_col]].dropna(subset=[code_4_col]).copy()
            causes_sub[code_4_col] = causes_sub[code_4_col].astype(str).str.strip().str.upper()
            causes_sub = causes_sub.rename(columns={code_4_col: "cause_code", name_4_col: "cause_name_lookup"})
            causes_sub = causes_sub.drop_duplicates("cause_code")
            mortality = mortality.merge(causes_sub, on="cause_code", how="left")
            mortality["cause_name"] = mortality["cause_name"].fillna(mortality["cause_name_lookup"])
            mortality.drop(columns=["cause_name_lookup"], inplace=True)

        code_3_col = find_column(causes, [
            "Código de la CIE-10 tres caracteres",
            "Codigo de la CIE-10 tres caracteres",
            "CIE10 3", "CODIGO 3",
        ])
        name_3_col = find_column(causes, [
            "Descripción  de códigos mortalidad a tres caracteres",
            "Descripcion  de codigos mortalidad a tres caracteres",
            "Descripción de códigos mortalidad a tres caracteres",
            "DESC 3", "DESCRIPCION 3",
        ])
        if code_3_col and name_3_col:
            causes_3 = causes[[code_3_col, name_3_col]].dropna(subset=[code_3_col]).copy()
            causes_3[code_3_col] = causes_3[code_3_col].astype(str).str.strip().str.upper()
            causes_3 = causes_3.rename(columns={code_3_col: "cause_code_3", name_3_col: "cause_name_3"})
            causes_3 = causes_3.drop_duplicates("cause_code_3")
            mortality["_cc3"] = mortality["cause_code"].str[:3]
            mortality = mortality.merge(causes_3, left_on="_cc3", right_on="cause_code_3", how="left")
            still_missing = mortality["cause_name"].isna()
            mortality.loc[still_missing, "cause_name"] = mortality.loc[still_missing, "cause_name_3"]
            mortality.drop(columns=["_cc3", "cause_code_3", "cause_name_3"], inplace=True, errors="ignore")

    # --- Final cleanup ---
    mortality["department"] = mortality["department"].replace({"NAN": pd.NA, "SIN DATO": "Sin dato"})
    mortality["cause_name"] = mortality["cause_name"].fillna("Causa no identificada")
    mortality["cause_code"] = mortality["cause_code"].fillna("SIN CODIGO")
    mortality["sex"] = mortality["sex"].fillna("Sin dato")
    mortality["month"] = mortality["month"].fillna("Desconocido")

    # Keep only needed columns
    keep_cols = ["department", "dept_code", "municipality", "month", "sex",
                 "age_group_code", "age_category", "cause_code", "cause_name"]
    mortality = mortality[keep_cols].copy()

    # Save
    output_path = DATA_DIR / "dashboard_ready.parquet"
    mortality.to_parquet(output_path, index=False, engine="pyarrow")

    size_mb = output_path.stat().st_size / 1024 / 1024
    print(f"\n  Generado: {output_path.name} ({size_mb:.2f} MB)")
    print(f"  Columnas: {list(mortality.columns)}")
    print(f"  Registros: {len(mortality):,}")
    print("\nListo. Haz commit de data/dashboard_ready.parquet y push.")


if __name__ == "__main__":
    main()

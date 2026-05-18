from __future__ import annotations

from pathlib import Path
import os
import unicodedata
import warnings

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import Dash, Input, Output, dcc, dash_table, html

warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

MORTALITY_FILE = DATA_DIR / "NoFetal2019.parquet"
CAUSES_FILE = DATA_DIR / "CodigosDeMuerte.parquet"
DIVIPOLA_FILE = DATA_DIR / "Divipola.parquet"

# Fallback a Excel si no existen los Parquet
MORTALITY_FILE_XLSX = DATA_DIR / "NoFetal2019.xlsx"
CAUSES_FILE_XLSX = DATA_DIR / "CodigosDeMuerte.xlsx"
DIVIPOLA_FILE_XLSX = DATA_DIR / "Divipola.xlsx"

AGE_CATEGORY_MAP = {
    0: "Mortalidad neonatal",
    1: "Mortalidad neonatal",
    2: "Mortalidad neonatal",
    3: "Mortalidad neonatal",
    4: "Mortalidad neonatal",
    5: "Mortalidad infantil",
    6: "Mortalidad infantil",
    7: "Primera infancia",
    8: "Primera infancia",
    9: "Niñez",
    10: "Niñez",
    11: "Adolescencia",
    12: "Juventud",
    13: "Juventud",
    14: "Adultez temprana",
    15: "Adultez temprana",
    16: "Adultez temprana",
    17: "Adultez intermedia",
    18: "Adultez intermedia",
    19: "Adultez intermedia",
    20: "Vejez",
    21: "Vejez",
    22: "Vejez",
    23: "Vejez",
    24: "Vejez",
    25: "Longevidad / Centenarios",
    26: "Longevidad / Centenarios",
    27: "Longevidad / Centenarios",
    28: "Longevidad / Centenarios",
    29: "Edad desconocida",
}

# Coordenadas indexadas por código DANE de departamento (2 dígitos)
# — más robusto que usar el nombre de texto, que varía entre fuentes.
DEPARTMENT_COORDS_BY_CODE = {
    5:  (6.25,  -75.57),   # Antioquia
    8:  (10.99, -74.80),   # Atlántico
    11: (4.71,  -74.07),   # Bogotá D.C.
    13: (10.40, -75.50),   # Bolívar
    15: (5.54,  -73.36),   # Boyacá
    17: (5.07,  -75.52),   # Caldas
    18: (1.61,  -75.61),   # Caquetá
    19: (2.44,  -76.61),   # Cauca
    20: (10.47, -73.25),   # Cesar
    23: (8.75,  -75.88),   # Córdoba
    25: (4.71,  -74.07),   # Cundinamarca
    27: (5.69,  -76.66),   # Chocó
    41: (2.93,  -75.28),   # Huila
    44: (11.54, -72.90),   # La Guajira
    47: (11.24, -74.19),   # Magdalena
    50: (4.14,  -73.63),   # Meta
    52: (1.21,  -77.27),   # Nariño
    54: (7.89,  -72.50),   # Norte de Santander
    63: (4.54,  -75.67),   # Quindío
    66: (4.81,  -75.69),   # Risaralda
    68: (7.12,  -73.12),   # Santander
    70: (9.30,  -75.39),   # Sucre
    73: (4.44,  -75.24),   # Tolima
    76: (3.45,  -76.53),   # Valle del Cauca
    81: (7.09,  -70.76),   # Arauca
    85: (5.33,  -72.40),   # Casanare
    86: (1.15,  -76.65),   # Putumayo
    88: (12.58, -81.70),   # San Andrés
    91: (-1.48, -71.98),   # Amazonas
    94: (2.67,  -69.76),   # Guainía
    95: (2.57,  -72.64),   # Guaviare
    97: (0.86,  -70.02),   # Vaupés
    99: (4.32,  -69.95),   # Vichada
}

MONTH_ORDER = [
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
]

MONTH_NAME_MAP = {
    1: "Enero",
    2: "Febrero",
    3: "Marzo",
    4: "Abril",
    5: "Mayo",
    6: "Junio",
    7: "Julio",
    8: "Agosto",
    9: "Septiembre",
    10: "Octubre",
    11: "Noviembre",
    12: "Diciembre",
}


app = Dash(__name__, title="Mortalidad Colombia 2019")
server = app.server


def strip_accents(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", str(value))
    return "".join(char for char in normalized if not unicodedata.combining(char))


def normalize_text(value: str) -> str:
    return " ".join(strip_accents(value).upper().replace("_", " ").split())


def find_column(dataframe: pd.DataFrame, candidates: list[str]) -> str | None:
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


def safe_read_excel(path: Path, skiprows: int = 0) -> pd.DataFrame:
    """Read a Parquet file if it exists, otherwise fall back to Excel."""
    if path.exists() and path.suffix == ".parquet":
        return pd.read_parquet(path)
    # Fallback: try the xlsx version
    xlsx_path = path.with_suffix(".xlsx")
    if xlsx_path.exists():
        return pd.read_excel(xlsx_path, skiprows=skiprows)
    # Try the original path as-is (for backwards compat)
    if path.exists():
        return pd.read_excel(path, skiprows=skiprows)
    return pd.DataFrame()


def clean_string_series(series: pd.Series) -> pd.Series:
    cleaned = series.astype("string").str.strip()
    return cleaned.replace({"<NA>": pd.NA, "nan": pd.NA, "None": pd.NA, "NONE": pd.NA, "": pd.NA})


def standardize_sex(value: object) -> str:
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


def assign_age_category(value: object) -> str:
    if pd.isna(value):
        return "Edad desconocida"
    try:
        numeric_value = int(float(value))
    except (TypeError, ValueError):
        return "Edad desconocida"
    return AGE_CATEGORY_MAP.get(numeric_value, "Edad desconocida")


def load_and_prepare_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    mortality = safe_read_excel(MORTALITY_FILE)
    # CodigosDeMuerte: skiprows=8 solo aplica al Excel (el Parquet ya fue convertido sin esas filas)
    causes = safe_read_excel(CAUSES_FILE, skiprows=8)
    divipola = safe_read_excel(DIVIPOLA_FILE)

    if mortality.empty:
        return mortality, causes, divipola

    mortality = mortality.copy()
    mortality.columns = [str(c).strip() for c in mortality.columns]

    # --- Join with Divipola to get department and municipality text names ---
    # NoFetal uses COD_DANE (5-digit) as the municipality key; Divipola has the same field.
    # Divipola uses merged cells so DEPARTAMENTO must be forward-filled.
    if not divipola.empty:
        divipola = divipola.copy()
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
            mortality = mortality.drop(columns=["_dept", "_mun"])
        else:
            mortality["department"] = "Sin dato"
            mortality["municipality"] = "Sin dato"
    else:
        mortality["department"] = "Sin dato"
        mortality["municipality"] = "Sin dato"

    # Preserve numeric department code for coordinate lookup in the map
    dept_code_col = find_column(mortality, ["COD_DEPARTAMENTO"])
    if dept_code_col:
        mortality["dept_code"] = pd.to_numeric(mortality[dept_code_col], errors="coerce")

    # --- Month from integer MES column ---
    mes_col = find_column(mortality, ["MES"])
    if mes_col:
        mortality["month"] = pd.to_numeric(mortality[mes_col], errors="coerce").map(MONTH_NAME_MAP)
    else:
        mortality["month"] = pd.NA

    # --- Sex: 1 = Hombre, 2 = Mujer ---
    sex_col = find_column(mortality, ["SEXO", "SEX"])
    mortality["sex"] = mortality[sex_col].map(standardize_sex) if sex_col else "Sin dato"

    # --- Age group ---
    age_col = find_column(mortality, ["GRUPO_EDAD1", "GRUPO DE EDAD1", "EDAD_GRUPO"])
    if age_col:
        mortality["age_group_code"] = pd.to_numeric(mortality[age_col], errors="coerce")
    else:
        mortality["age_group_code"] = pd.Series([pd.NA] * len(mortality))
    mortality["age_category"] = mortality["age_group_code"].apply(assign_age_category)

    # --- Cause code: COD_MUERTE is the ICD-10 4-char code ---
    cause_col = find_column(mortality, ["COD_MUERTE", "CAUSA", "COD_CAUSA", "CODIGO_CAUSA", "CIE10"])
    if cause_col:
        mortality["cause_code"] = clean_string_series(mortality[cause_col].astype(str)).str.upper()
    else:
        mortality["cause_code"] = "SIN CODIGO"
    mortality["cause_name"] = pd.NA

    # --- Join with CodigosDeMuerte to get cause descriptions ---
    # The file has 4-char ICD-10 codes and their descriptions
    if not causes.empty:
        causes = causes.copy()
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
            mortality = mortality.drop(columns=["cause_name_lookup"])

        # Fallback: try 3-char code for records still without a name
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
            # Match using first 3 chars of cause_code
            mortality["_cause_code_3"] = mortality["cause_code"].str[:3]
            mortality = mortality.merge(causes_3, left_on="_cause_code_3", right_on="cause_code_3", how="left")
            still_missing = mortality["cause_name"].isna() | (mortality["cause_name"] == "Causa no identificada")
            mortality.loc[still_missing, "cause_name"] = mortality.loc[still_missing, "cause_name_3"]
            mortality = mortality.drop(columns=["_cause_code_3", "cause_code_3", "cause_name_3"], errors="ignore")

    # --- Cleanup ---
    mortality["department"] = mortality["department"].replace({"NAN": pd.NA, "SIN DATO": "Sin dato"})
    mortality["department_norm"] = mortality["department"].fillna("Sin dato").map(normalize_text)
    mortality["month"] = pd.Categorical(mortality["month"], categories=MONTH_ORDER, ordered=True)
    mortality["cause_name"] = mortality["cause_name"].fillna("Causa no identificada")
    mortality["cause_code"] = mortality["cause_code"].fillna("SIN CODIGO")
    mortality["sex"] = mortality["sex"].fillna("Sin dato")

    return mortality, causes, divipola


MORTALITY_DF, CAUSES_DF, DIVIPOLA_DF = load_and_prepare_data()

AVAILABLE_DEPARTMENTS = sorted(
    [department for department in MORTALITY_DF.get("department", pd.Series(dtype=str)).dropna().unique().tolist()]
) if not MORTALITY_DF.empty else []


def compute_kpis(dataframe: pd.DataFrame) -> dict:
    """Compute summary KPI values from the mortality dataframe."""
    if dataframe.empty:
        return {
            "total": 0,
            "departments": 0,
            "top_department": "N/A",
            "top_month": "N/A",
            "homicides_x95": 0,
        }
    total = len(dataframe)
    departments = dataframe["department"].dropna().nunique() if "department" in dataframe.columns else 0
    top_department = (
        dataframe["department"].value_counts().idxmax()
        if "department" in dataframe.columns and not dataframe["department"].dropna().empty
        else "N/A"
    )
    top_month = (
        dataframe["month"].value_counts().idxmax()
        if "month" in dataframe.columns and not dataframe["month"].dropna().empty
        else "N/A"
    )
    homicides = 0
    if "cause_code" in dataframe.columns:
        homicides = int(dataframe["cause_code"].astype(str).str.upper().str.startswith("X95").sum())
    return {
        "total": total,
        "departments": departments,
        "top_department": top_department,
        "top_month": top_month,
        "homicides_x95": homicides,
    }


def build_kpi_cards(dataframe: pd.DataFrame) -> html.Div:
    """Build a row of KPI indicator cards."""
    kpis = compute_kpis(dataframe)
    cards = [
        _kpi_card("Total defunciones", f"{kpis['total']:,}", "icon-deaths"),
        _kpi_card("Departamentos", str(kpis["departments"]), "icon-dept"),
        _kpi_card("Depto. más afectado", str(kpis["top_department"]), "icon-top"),
        _kpi_card("Mes más letal", str(kpis["top_month"]), "icon-month"),
        _kpi_card("Homicidios (X95)", f"{kpis['homicides_x95']:,}", "icon-homicide"),
    ]
    return html.Div(className="kpi-row", children=cards, id="kpi-row")


def _kpi_card(label: str, value: str, icon_class: str) -> html.Div:
    return html.Div(
        className="kpi-card",
        children=[
            html.Div(className=f"kpi-icon {icon_class}"),
            html.Div(
                className="kpi-content",
                children=[
                    html.Span(value, className="kpi-value"),
                    html.Span(label, className="kpi-label"),
                ],
            ),
        ],
    )


def build_data_status_banner() -> html.Div | None:
    """Show a warning banner if any data file is missing."""
    missing = []
    if not MORTALITY_FILE.exists() and not MORTALITY_FILE_XLSX.exists():
        missing.append("NoFetal2019")
    if not CAUSES_FILE.exists() and not CAUSES_FILE_XLSX.exists():
        missing.append("CodigosDeMuerte")
    if not DIVIPOLA_FILE.exists() and not DIVIPOLA_FILE_XLSX.exists():
        missing.append("Divipola")
    if not missing:
        return None
    return html.Div(
        className="alert-banner",
        children=[
            html.Span("⚠️ "),
            html.Span(f"Archivos faltantes en data/: {', '.join(missing)}. Colócalos para ver las visualizaciones."),
        ],
    )


def empty_figure(message: str) -> go.Figure:
    figure = go.Figure()
    figure.add_annotation(
        text=message,
        x=0.5,
        y=0.5,
        xref="paper",
        yref="paper",
        showarrow=False,
        font={"size": 16, "color": "#e5e7eb"},
    )
    figure.update_xaxes(visible=False)
    figure.update_yaxes(visible=False)
    figure.update_layout(
        paper_bgcolor="#111827",
        plot_bgcolor="#111827",
        margin={"l": 20, "r": 20, "t": 20, "b": 20},
        height=380,
    )
    return figure


def filter_data(selected_departments: list[str] | None) -> pd.DataFrame:
    if MORTALITY_DF.empty:
        return MORTALITY_DF
    if not selected_departments:
        return MORTALITY_DF
    filtered = MORTALITY_DF[MORTALITY_DF["department"].isin(selected_departments)].copy()
    return filtered if not filtered.empty else MORTALITY_DF


def build_map_figure(dataframe: pd.DataFrame) -> go.Figure:
    if dataframe.empty or "department" not in dataframe.columns:
        return empty_figure("Carga los archivos en la carpeta data/ para ver el mapa")

    group_cols = ["department", "dept_code"] if "dept_code" in dataframe.columns else ["department"]
    department_counts = dataframe.groupby(group_cols).size().reset_index(name="deaths")

    # Assign coordinates using numeric department code (reliable) then fall back to name
    def get_coords(row: pd.Series) -> pd.Series:
        code = int(row["dept_code"]) if "dept_code" in row and pd.notna(row.get("dept_code")) else None
        if code is not None and code in DEPARTMENT_COORDS_BY_CODE:
            return pd.Series(DEPARTMENT_COORDS_BY_CODE[code])
        return pd.Series((None, None))

    department_counts[["lat", "lon"]] = department_counts.apply(get_coords, axis=1)
    department_counts = department_counts.dropna(subset=["lat", "lon"])

    if department_counts.empty:
        return empty_figure("No fue posible ubicar coordenadas para los departamentos")

    # Add percentage column for richer tooltips
    total_deaths = department_counts["deaths"].sum()
    department_counts["pct"] = (department_counts["deaths"] / total_deaths * 100).round(1)

    figure = px.scatter_geo(
        department_counts,
        lat="lat",
        lon="lon",
        size="deaths",
        color="deaths",
        hover_name="department",
        hover_data={"lat": False, "lon": False, "deaths": True, "pct": ":.1f"},
        labels={"deaths": "Muertes", "pct": "% del total"},
        color_continuous_scale="YlOrRd",
        projection="mercator",
        title="Distribución total de muertes por departamento (2019)",
    )
    figure.update_geos(
        visible=False,
        showcountries=True,
        countrycolor="#6b7280",
        showland=True,
        landcolor="#0f172a",
        showocean=True,
        oceancolor="#0b1120",
        fitbounds="locations",
    )
    figure.update_layout(
        paper_bgcolor="#111827",
        plot_bgcolor="#111827",
        font={"color": "#f3f4f6"},
        margin={"l": 0, "r": 0, "t": 50, "b": 0},
        height=430,
        coloraxis_colorbar={"title": "Muertes"},
    )
    return figure


def build_month_figure(dataframe: pd.DataFrame) -> go.Figure:
    if dataframe.empty or "month" not in dataframe.columns:
        return empty_figure("No hay datos para construir la serie mensual")

    monthly = dataframe.dropna(subset=["month"]).groupby("month").size().reset_index(name="deaths")
    if monthly.empty:
        return empty_figure("No hay datos mensuales suficientes")

    figure = px.line(
        monthly,
        x="month",
        y="deaths",
        markers=True,
        title="Total de muertes por mes en Colombia (2019)",
        labels={"month": "Mes", "deaths": "Muertes"},
    )
    figure.update_traces(
        line={"color": "#38bdf8", "width": 3},
        marker={"size": 10},
        hovertemplate="<b>%{x}</b><br>Muertes: %{y:,}<extra></extra>",
    )
    figure.update_layout(
        paper_bgcolor="#111827",
        plot_bgcolor="#111827",
        font={"color": "#f3f4f6"},
        xaxis_title="Mes",
        yaxis_title="Muertes",
        height=380,
        margin={"l": 40, "r": 20, "t": 50, "b": 40},
    )
    figure.update_xaxes(categoryorder="array", categoryarray=MONTH_ORDER)
    return figure


def build_violent_cities_figure(dataframe: pd.DataFrame) -> go.Figure:
    if dataframe.empty or "municipality" not in dataframe.columns:
        return empty_figure("No hay datos para identificar ciudades violentas")

    cause_code_series = (
        dataframe["cause_code"].astype(str).str.upper()
        if "cause_code" in dataframe.columns
        else pd.Series([""] * len(dataframe), index=dataframe.index)
    )
    # Only X95* codes: agresión con disparo de armas de fuego (X950-X954, X959)
    violent_mask = cause_code_series.str.startswith("X95", na=False)
    violent_data = dataframe[violent_mask].copy()

    if violent_data.empty:
        return empty_figure("No se encontraron registros X95 con los filtros actuales")

    top_cities = (
        violent_data.groupby("municipality")
        .size()
        .sort_values(ascending=False)
        .head(5)
        .reset_index(name="homicidios")
    )
    if top_cities.empty:
        return empty_figure("No hay ciudades violentas para graficar")

    # Color gradient: darker red for higher values
    colors = ["#dc2626", "#ef4444", "#f97316", "#fb923c", "#fbbf24"]
    figure = px.bar(
        top_cities,
        x="homicidios",
        y="municipality",
        orientation="h",
        title="Top 5 ciudades más violentas (homicidios X95)",
        text="homicidios",
        color="homicidios",
        color_continuous_scale=["#fbbf24", "#f97316", "#ef4444", "#dc2626", "#991b1b"],
    )
    figure.update_traces(textposition="inside", textfont={"size": 13, "color": "#fff"})
    figure.update_layout(
        paper_bgcolor="#111827",
        plot_bgcolor="#111827",
        font={"color": "#f3f4f6"},
        xaxis_title="Homicidios (X95)",
        yaxis_title="",
        height=380,
        margin={"l": 10, "r": 30, "t": 55, "b": 40},
        coloraxis_showscale=False,
        yaxis={"categoryorder": "total ascending", "tickfont": {"size": 12}},
    )
    return figure


def build_low_mortality_pie(dataframe: pd.DataFrame) -> go.Figure:
    if dataframe.empty or "municipality" not in dataframe.columns:
        return empty_figure("No hay datos para construir el grafico circular")

    city_counts = dataframe.groupby("municipality").size().sort_values(ascending=True).head(10).reset_index(name="deaths")
    if city_counts.empty:
        return empty_figure("No hay ciudades con baja mortalidad para mostrar")

    figure = px.pie(
        city_counts,
        names="municipality",
        values="deaths",
        title="10 ciudades con menor índice de mortalidad",
        hole=0.45,
    )
    figure.update_traces(
        textposition="inside",
        textinfo="percent+label",
        hovertemplate="<b>%{label}</b><br>Defunciones: %{value:,}<br>Proporción: %{percent}<extra></extra>",
    )
    figure.update_layout(
        paper_bgcolor="#111827",
        plot_bgcolor="#111827",
        font={"color": "#f3f4f6"},
        height=380,
        margin={"l": 20, "r": 20, "t": 50, "b": 20},
        legend={"font": {"color": "#f3f4f6"}},
    )
    return figure


def build_top_causes_table(dataframe: pd.DataFrame) -> tuple[list[dict], list[dict]]:
    if dataframe.empty or "cause_code" not in dataframe.columns:
        return [], []

    causes = dataframe.groupby(["cause_code", "cause_name"]).size().sort_values(ascending=False).head(10).reset_index(name="cases")
    if causes.empty:
        return [], []

    rows = causes.to_dict("records")
    columns = [
        {"name": "Codigo", "id": "cause_code"},
        {"name": "Nombre", "id": "cause_name"},
        {"name": "Total", "id": "cases"},
    ]
    return rows, columns


def build_sex_department_figure(dataframe: pd.DataFrame) -> go.Figure:
    if dataframe.empty or "department" not in dataframe.columns or "sex" not in dataframe.columns:
        return empty_figure("No hay datos para comparar sexo por departamento")

    grouped = dataframe.groupby(["department", "sex"]).size().reset_index(name="deaths")
    grouped = grouped[grouped["sex"].isin(["Hombre", "Mujer", "Indeterminado"])]
    if grouped.empty:
        return empty_figure("No hay datos suficientes para la comparacion por sexo")

    # Abbreviate long department names so labels don't overlap
    abbrev = {
        "ARCHIPIELAGO DE SAN ANDRES, PROVIDENCIA Y SANTA CATALINA": "SAN ANDRÉS",
        "ARCHIPIÉLAGO DE SAN ANDRÉS, PROVIDENCIA Y SANTA CATALINA": "SAN ANDRÉS",
        "NORTE DE SANTANDER": "NTE. SANTANDER",
        "VALLE DEL CAUCA": "VALLE DEL CAUCA",
    }
    grouped["dept_label"] = grouped["department"].apply(lambda d: abbrev.get(str(d).upper(), d))

    # Add percentage within each department for richer tooltips
    dept_totals = grouped.groupby("dept_label")["deaths"].transform("sum")
    grouped["pct"] = (grouped["deaths"] / dept_totals * 100).round(1)

    color_map = {"Hombre": "#38bdf8", "Mujer": "#f472b6", "Indeterminado": "#a3e635"}
    figure = px.bar(
        grouped,
        x="dept_label",
        y="deaths",
        color="sex",
        color_discrete_map=color_map,
        title="Comparación del total de muertes por sexo en cada departamento",
        barmode="stack",
        hover_data={"pct": ":.1f"},
        labels={"deaths": "Muertes", "sex": "Sexo", "dept_label": "Departamento", "pct": "% en depto."},
    )
    figure.update_layout(
        paper_bgcolor="#111827",
        plot_bgcolor="#111827",
        font={"color": "#f3f4f6"},
        xaxis_title="Departamento",
        yaxis_title="Muertes",
        height=500,
        margin={"l": 50, "r": 20, "t": 50, "b": 160},
        legend={"orientation": "h", "y": -0.35, "title": "Sexo"},
    )
    figure.update_xaxes(tickangle=-45, tickfont={"size": 10})
    return figure


def build_age_histogram(dataframe: pd.DataFrame) -> go.Figure:
    if dataframe.empty or "age_category" not in dataframe.columns:
        return empty_figure("No hay datos para el histograma de edades")

    age_counts = dataframe.groupby("age_category").size().reset_index(name="deaths")
    order = [
        "Mortalidad neonatal",
        "Mortalidad infantil",
        "Primera infancia",
        "Niñez",
        "Adolescencia",
        "Juventud",
        "Adultez temprana",
        "Adultez intermedia",
        "Vejez",
        "Longevidad / Centenarios",
        "Edad desconocida",
    ]
    age_counts["age_category"] = pd.Categorical(age_counts["age_category"], categories=order, ordered=True)
    age_counts = age_counts.sort_values("age_category")

    figure = px.bar(
        age_counts,
        x="age_category",
        y="deaths",
        title="Distribución de muertes por grupo de edad (GRUPO_EDAD1)",
        text="deaths",
        color="age_category",
        color_discrete_sequence=px.colors.sequential.Tealgrn,
    )
    figure.update_traces(textposition="outside")
    figure.update_layout(
        paper_bgcolor="#111827",
        plot_bgcolor="#111827",
        font={"color": "#f3f4f6"},
        xaxis_title="Grupo de edad",
        yaxis_title="Muertes",
        height=380,
        margin={"l": 40, "r": 20, "t": 50, "b": 80},
        showlegend=False,
    )
    figure.update_xaxes(tickangle=-25)
    return figure


app.layout = html.Div(
    className="page-shell",
    children=[
        # Banner de archivos faltantes (si aplica)
        build_data_status_banner() or html.Div(style={"display": "none"}),
        html.Div(
            className="hero-card",
            children=[
                html.Div(
                    className="hero-copy",
                    children=[
                        html.P("Aplicaciones 1 - Actividad 4 - Plinio Hernandez, Jherson Guzman", className="eyebrow"),
                        html.H1("Mortalidad en Colombia 2019"),
                        html.P(
                            "Explora el comportamiento de la mortalidad por departamento, mes, ciudad, sexo, causa y grupo de edad en una sola vista interactiva.",
                            className="hero-text",
                        ),
                    ],
                ),
                html.Div(
                    className="hero-panel",
                    children=[
                        html.Div("Estado de datos", className="panel-label"),
                        html.Div(
                            "Archivos cargados" if not MORTALITY_DF.empty else "Pendiente: carga los Excel en data/",
                            className="panel-value",
                        ),
                        html.Div(
                            f"Registros disponibles: {len(MORTALITY_DF):,}" if not MORTALITY_DF.empty else "Aun no hay microdatos",
                            className="panel-meta",
                        ),
                    ],
                ),
            ],
        ),
        # KPI indicators
        build_kpi_cards(MORTALITY_DF),
        html.Div(
            className="controls-card",
            children=[
                html.Label("Filtrar por departamento"),
                dcc.Dropdown(
                    id="department-filter",
                    options=[{"label": department, "value": department} for department in AVAILABLE_DEPARTMENTS],
                    value=[],
                    multi=True,
                    placeholder="Selecciona uno o varios departamentos",
                    className="dropdown",
                ),
            ],
        ),
        html.Div(
            className="grid grid-map",
            children=[dcc.Graph(id="map-graph", figure=build_map_figure(MORTALITY_DF), config={"displayModeBar": False})],
        ),
        html.Div(
            className="grid two-col",
            children=[
                dcc.Graph(id="month-graph", figure=build_month_figure(MORTALITY_DF), config={"displayModeBar": False}),
                dcc.Graph(id="violent-cities-graph", figure=build_violent_cities_figure(MORTALITY_DF), config={"displayModeBar": False}),
            ],
        ),
        html.Div(
            className="grid two-col",
            children=[
                dcc.Graph(id="low-mortality-pie", figure=build_low_mortality_pie(MORTALITY_DF), config={"displayModeBar": False}),
                dcc.Graph(id="age-histogram", figure=build_age_histogram(MORTALITY_DF), config={"displayModeBar": False}),
            ],
        ),
        html.Div(
            className="grid row-1-2",
            children=[
                dcc.Graph(
                    id="sex-department-graph",
                    figure=build_sex_department_figure(MORTALITY_DF),
                    config={"displayModeBar": False},
                ),
            ],
        ),
        html.Div(
            className="grid grid-map table-section",
            children=[
                html.Div(
                    className="card table-card",
                    children=[
                        html.H3("Top 10 causas de muerte"),
                        dash_table.DataTable(
                            id="causes-table",
                            columns=[
                                {"name": "Codigo", "id": "cause_code"},
                                {"name": "Nombre", "id": "cause_name"},
                                {"name": "Total", "id": "cases"},
                            ],
                            data=build_top_causes_table(MORTALITY_DF)[0],
                            style_table={"overflowX": "auto"},
                            style_cell={
                                "backgroundColor": "#111827",
                                "color": "#f3f4f6",
                                "border": "1px solid #243244",
                                "padding": "10px",
                                "fontFamily": "sans-serif",
                                "fontSize": "14px",
                                "textAlign": "left",
                                "whiteSpace": "normal",
                                "height": "auto",
                            },
                            style_header={
                                "backgroundColor": "#0f172a",
                                "fontWeight": "700",
                                "color": "#e5e7eb",
                                "border": "1px solid #243244",
                            },
                            page_size=10,
                        ),
                    ],
                ),
            ],
        ),
        dcc.Interval(id="heartbeat", interval=60_000, n_intervals=0),
    ],
)


@app.callback(
    Output("map-graph", "figure"),
    Output("month-graph", "figure"),
    Output("violent-cities-graph", "figure"),
    Output("low-mortality-pie", "figure"),
    Output("age-histogram", "figure"),
    Output("sex-department-graph", "figure"),
    Output("causes-table", "data"),
    Output("causes-table", "columns"),
    Output("kpi-row", "children"),
    Input("department-filter", "value"),
    Input("heartbeat", "n_intervals"),
)
def refresh_dashboard(selected_departments: list[str] | None, _heartbeat: int):
    filtered = filter_data(selected_departments)
    table_rows, table_columns = build_top_causes_table(filtered)
    kpi_children = build_kpi_cards(filtered).children
    return (
        build_map_figure(filtered),
        build_month_figure(filtered),
        build_violent_cities_figure(filtered),
        build_low_mortality_pie(filtered),
        build_age_histogram(filtered),
        build_sex_department_figure(filtered),
        table_rows,
        table_columns,
        kpi_children,
    )


if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=int(os.getenv("PORT", "8050")))

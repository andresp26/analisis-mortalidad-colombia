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

MORTALITY_FILE = DATA_DIR / "NoFetal2019.xlsx"
CAUSES_FILE = DATA_DIR / "CodigosDeMuerte.xlsx"
DIVIPOLA_FILE = DATA_DIR / "Divipola.xlsx"

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
    9: "Ninez",
    10: "Ninez",
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

DEPARTMENT_COORDS = {
    "AMAZONAS": (-1.48, -71.98),
    "ANTIOQUIA": (6.25, -75.57),
    "ARAUCA": (7.09, -70.76),
    "ATLANTICO": (10.99, -74.80),
    "BOLIVAR": (10.40, -75.50),
    "BOYACA": (5.54, -73.36),
    "CALDAS": (5.07, -75.52),
    "CAQUETA": (1.61, -75.61),
    "CASANARE": (5.33, -72.40),
    "CAUCA": (2.44, -76.61),
    "CESAR": (10.47, -73.25),
    "CHOCO": (5.69, -76.66),
    "CORDOBA": (8.75, -75.88),
    "CUNDINAMARCA": (4.71, -74.07),
    "GUAINIA": (2.67, -69.76),
    "GUAJIRA": (11.54, -72.90),
    "GUAVIARE": (2.57, -72.64),
    "HUILA": (2.93, -75.28),
    "MAGDALENA": (11.24, -74.19),
    "META": (4.14, -73.63),
    "NARINO": (1.21, -77.27),
    "NORTE DE SANTANDER": (7.89, -72.50),
    "PUTUMAYO": (1.15, -76.65),
    "QUINDIO": (4.54, -75.67),
    "RISARALDA": (4.81, -75.69),
    "SAN ANDRES": (12.58, -81.70),
    "SANTANDER": (7.12, -73.12),
    "SUCRE": (9.30, -75.39),
    "TOLIMA": (4.44, -75.24),
    "VALLE DEL CAUCA": (3.45, -76.53),
    "VAUPES": (0.86, -70.02),
    "VICHADA": (4.32, -69.95),
    "BOGOTA D.C.": (4.71, -74.07),
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


def safe_read_excel(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_excel(path)


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
    return str(value).strip().title()


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
    causes = safe_read_excel(CAUSES_FILE)
    divipola = safe_read_excel(DIVIPOLA_FILE)

    if mortality.empty:
        return mortality, causes, divipola

    mortality = mortality.copy()
    mortality.columns = [str(column).strip() for column in mortality.columns]

    date_column = find_column(mortality, ["FECHA_DEF", "FECHA_DE_FUNCION", "FECHA DE DEFUNCION", "FECHA"])
    department_column = find_column(mortality, ["NOM_DPTO", "DEPARTAMENTO", "DPTO_RES", "DPTO", "NOM_DEPARTAMENTO"])
    municipality_column = find_column(mortality, ["NOM_MUN", "MUNICIPIO", "MUNICIPIO_RES", "NOM_MUNICIPIO"])
    sex_column = find_column(mortality, ["SEXO", "SEX"])
    age_column = find_column(mortality, ["GRUPO_EDAD1", "GRUPO DE EDAD1", "EDAD_GRUPO"])
    cause_code_column = find_column(mortality, ["CAUSA", "COD_CAUSA", "CODIGO_CAUSA", "CIE10", "COD CAUSA"])
    cause_name_column = find_column(mortality, ["NOMBRE_CAUSA", "CAUSA_NOMBRE", "DESC_CAUSA", "DESCRIPCION_CAUSA"])

    if date_column is not None:
        mortality["date"] = pd.to_datetime(mortality[date_column], errors="coerce")
        mortality["month"] = mortality["date"].dt.month.map(MONTH_NAME_MAP)
    else:
        mortality["date"] = pd.NaT
        mortality["month"] = pd.NA

    mortality["department"] = clean_string_series(mortality[department_column]) if department_column else "Sin dato"
    mortality["municipality"] = clean_string_series(mortality[municipality_column]) if municipality_column else "Sin dato"
    mortality["sex"] = mortality[sex_column].map(standardize_sex) if sex_column else "Sin dato"
    mortality["age_group_code"] = pd.to_numeric(mortality[age_column], errors="coerce") if age_column else pd.Series([pd.NA] * len(mortality))
    mortality["age_category"] = mortality["age_group_code"].apply(assign_age_category)
    mortality["cause_code"] = clean_string_series(mortality[cause_code_column]).str.upper() if cause_code_column else pd.NA
    mortality["cause_name"] = clean_string_series(mortality[cause_name_column]) if cause_name_column else pd.NA

    if not causes.empty:
        causes = causes.copy()
        causes.columns = [str(column).strip() for column in causes.columns]
        code_column = find_column(causes, ["CODIGO", "COD_CAUSA", "CAUSA", "CIE10", "CODIGO_CAUSA"])
        name_column = find_column(causes, ["NOMBRE", "DESCRIPCION", "CAUSA", "NOMBRE_CAUSA", "DESC_CAUSA"])
        if code_column and name_column:
            causes = causes[[code_column, name_column]].dropna().copy()
            causes[code_column] = clean_string_series(causes[code_column]).str.upper()
            causes[name_column] = clean_string_series(causes[name_column])
            causes = causes.rename(columns={code_column: "cause_code", name_column: "cause_name_lookup"})
            mortality = mortality.merge(causes, on="cause_code", how="left")
            mortality["cause_name"] = mortality["cause_name"].fillna(mortality["cause_name_lookup"])
            mortality = mortality.drop(columns=["cause_name_lookup"])

    if not divipola.empty and department_column:
        divipola = divipola.copy()
        divipola.columns = [str(column).strip() for column in divipola.columns]
        div_dept_column = find_column(divipola, ["NOM_DPTO", "DEPARTAMENTO", "NOMBRE_DEPARTAMENTO"])
        if div_dept_column:
            mortality["department"] = mortality["department"].fillna(clean_string_series(mortality[department_column]))

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
    if dataframe.empty or "department_norm" not in dataframe.columns:
        return empty_figure("Carga los archivos en la carpeta data/ para ver el mapa")

    department_counts = dataframe.groupby(["department", "department_norm"]).size().reset_index(name="deaths")
    department_counts[["lat", "lon"]] = department_counts["department_norm"].apply(
        lambda value: pd.Series(DEPARTMENT_COORDS.get(value, (None, None)))
    )
    department_counts = department_counts.dropna(subset=["lat", "lon"])

    if department_counts.empty:
        return empty_figure("No fue posible ubicar coordenadas para los departamentos")

    figure = px.scatter_geo(
        department_counts,
        lat="lat",
        lon="lon",
        size="deaths",
        color="deaths",
        hover_name="department",
        hover_data={"lat": False, "lon": False, "deaths": True},
        color_continuous_scale="YlOrRd",
        projection="mercator",
        title="Total de muertes por department",
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
        coloraxis_colorbar={"title": "Deaths"},
    )
    return figure


def build_month_figure(dataframe: pd.DataFrame) -> go.Figure:
    if dataframe.empty or "month" not in dataframe.columns:
        return empty_figure("No hay datos para construir la serie mensual")

    monthly = dataframe.dropna(subset=["month"]).groupby("month").size().reset_index(name="deaths")
    if monthly.empty:
        return empty_figure("No hay datos mensuales suficientes")

    figure = px.line(monthly, x="month", y="deaths", markers=True, title="Total de muertes por mes")
    figure.update_traces(line={"color": "#38bdf8", "width": 3}, marker={"size": 10})
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
    cause_name_series = (
        dataframe["cause_name"].astype(str).str.lower()
        if "cause_name" in dataframe.columns
        else pd.Series([""] * len(dataframe), index=dataframe.index)
    )
    violent_mask = cause_code_series.str.startswith("X95", na=False) | cause_name_series.str.contains(
        "homicidio|agres|disparo|arma de fuego|no especificad", na=False, regex=True
    )
    violent_data = dataframe[violent_mask].copy()

    if violent_data.empty:
        return empty_figure("No se encontraron registros de homicidios con los filtros actuales")

    top_cities = violent_data.groupby("municipality").size().sort_values(ascending=False).head(5).reset_index(name="deaths")
    if top_cities.empty:
        return empty_figure("No hay ciudades violentas para graficar")

    figure = px.bar(
        top_cities,
        x="deaths",
        y="municipality",
        orientation="h",
        title="Top 5 ciudades mas violentas",
        text="deaths",
    )
    figure.update_traces(marker_color="#f97316", textposition="outside")
    figure.update_layout(
        paper_bgcolor="#111827",
        plot_bgcolor="#111827",
        font={"color": "#f3f4f6"},
        xaxis_title="Casos",
        yaxis_title="Ciudad",
        height=380,
        margin={"l": 20, "r": 20, "t": 50, "b": 40},
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
        title="10 ciudades con menor indice de mortalidad",
        hole=0.45,
    )
    figure.update_traces(textposition="inside", textinfo="percent+label")
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
    if grouped.empty:
        return empty_figure("No hay datos suficientes para la comparacion por sexo")

    figure = px.bar(
        grouped,
        x="department",
        y="deaths",
        color="sex",
        title="Total de muertes por sexo en cada department",
        barmode="stack",
    )
    figure.update_layout(
        paper_bgcolor="#111827",
        plot_bgcolor="#111827",
        font={"color": "#f3f4f6"},
        xaxis_title="Department",
        yaxis_title="Muertes",
        height=430,
        margin={"l": 40, "r": 20, "t": 50, "b": 120},
        legend={"orientation": "h", "y": -0.25},
    )
    figure.update_xaxes(tickangle=-35)
    return figure


def build_age_histogram(dataframe: pd.DataFrame) -> go.Figure:
    if dataframe.empty or "age_category" not in dataframe.columns:
        return empty_figure("No hay datos para el histograma de edades")

    age_counts = dataframe.groupby("age_category").size().reset_index(name="deaths")
    order = [
        "Mortalidad neonatal",
        "Mortalidad infantil",
        "Primera infancia",
        "Ninez",
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
        title="Distribucion de muertes por grupo de edad",
        text="deaths",
    )
    figure.update_traces(marker_color="#22c55e", textposition="outside")
    figure.update_layout(
        paper_bgcolor="#111827",
        plot_bgcolor="#111827",
        font={"color": "#f3f4f6"},
        xaxis_title="Grupo de edad",
        yaxis_title="Muertes",
        height=380,
        margin={"l": 40, "r": 20, "t": 50, "b": 80},
    )
    figure.update_xaxes(tickangle=-25)
    return figure


app.layout = html.Div(
    className="page-shell",
    children=[
        html.Div(
            className="hero-card",
            children=[
                html.Div(
                    className="hero-copy",
                    children=[
                        html.P("Dash | Plotly | Colombia 2019", className="eyebrow"),
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
        html.Div(
            className="controls-card",
            children=[
                html.Label("Filtrar por department"),
                dcc.Dropdown(
                    id="department-filter",
                    options=[{"label": department, "value": department} for department in AVAILABLE_DEPARTMENTS],
                    value=AVAILABLE_DEPARTMENTS[:5] if AVAILABLE_DEPARTMENTS else [],
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
            className="grid two-col table-section",
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
                html.Div(
                    className="card note-card",
                    children=[
                        html.H3("Notas de implementacion"),
                        html.Ul(
                            [
                                html.Li("Coloca NoFetal2019.xlsx, CodigosDeMuerte.xlsx y Divipola.xlsx dentro de data/."),
                                html.Li("La visualizacion geografica usa coordenadas aproximadas por departamento como punto de partida."),
                                html.Li("Cuando cargues los archivos reales, la app se actualiza sin cambiar el codigo base."),
                                html.Li("La publicacion en Railway utiliza Procfile y gunicorn."),
                            ]
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
    Output("causes-table", "data"),
    Output("causes-table", "columns"),
    Input("department-filter", "value"),
    Input("heartbeat", "n_intervals"),
)
def refresh_dashboard(selected_departments: list[str] | None, _heartbeat: int):
    filtered = filter_data(selected_departments)
    table_rows, table_columns = build_top_causes_table(filtered)
    return (
        build_map_figure(filtered),
        build_month_figure(filtered),
        build_violent_cities_figure(filtered),
        build_low_mortality_pie(filtered),
        build_age_histogram(filtered),
        table_rows,
        table_columns,
    )


if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=int(os.getenv("PORT", "8050")))

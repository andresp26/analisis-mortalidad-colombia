from __future__ import annotations

from pathlib import Path
import os
import warnings

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import Dash, Input, Output, dcc, dash_table, html

warnings.filterwarnings("ignore", category=FutureWarning)

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

DASHBOARD_FILE = DATA_DIR / "dashboard_ready.parquet"

# Coordenadas por código DANE de departamento (2 dígitos)
DEPARTMENT_COORDS_BY_CODE = {
    5:  (6.25,  -75.57),   8:  (10.99, -74.80),  11: (4.71,  -74.07),
    13: (10.40, -75.50),  15: (5.54,  -73.36),   17: (5.07,  -75.52),
    18: (1.61,  -75.61),  19: (2.44,  -76.61),   20: (10.47, -73.25),
    23: (8.75,  -75.88),  25: (4.71,  -74.07),   27: (5.69,  -76.66),
    41: (2.93,  -75.28),  44: (11.54, -72.90),   47: (11.24, -74.19),
    50: (4.14,  -73.63),  52: (1.21,  -77.27),   54: (7.89,  -72.50),
    63: (4.54,  -75.67),  66: (4.81,  -75.69),   68: (7.12,  -73.12),
    70: (9.30,  -75.39),  73: (4.44,  -75.24),   76: (3.45,  -76.53),
    81: (7.09,  -70.76),  85: (5.33,  -72.40),   86: (1.15,  -76.65),
    88: (12.58, -81.70),  91: (-1.48, -71.98),   94: (2.67,  -69.76),
    95: (2.57,  -72.64),  97: (0.86,  -70.02),   99: (4.32,  -69.95),
}

MONTH_ORDER = [
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
]

AGE_ORDER = [
    "Mortalidad neonatal", "Mortalidad infantil", "Primera infancia",
    "Niñez", "Adolescencia", "Juventud", "Adultez temprana",
    "Adultez intermedia", "Vejez", "Longevidad / Centenarios", "Edad desconocida",
]

app = Dash(__name__, title="Mortalidad Colombia 2019")
server = app.server


# ─── Data Loading (lightweight: single pre-processed parquet) ───────────────

def load_data() -> pd.DataFrame:
    if not DASHBOARD_FILE.exists():
        return pd.DataFrame()
    df = pd.read_parquet(DASHBOARD_FILE)
    df["month"] = pd.Categorical(df["month"], categories=MONTH_ORDER, ordered=True)
    return df


MORTALITY_DF = load_data()

AVAILABLE_DEPARTMENTS = sorted(
    MORTALITY_DF["department"].dropna().unique().tolist()
) if not MORTALITY_DF.empty else []


# ─── Helper functions ───────────────────────────────────────────────────────

def empty_figure(message: str) -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(text=message, x=0.5, y=0.5, xref="paper", yref="paper",
                       showarrow=False, font={"size": 16, "color": "#e5e7eb"})
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    fig.update_layout(paper_bgcolor="#111827", plot_bgcolor="#111827",
                      margin={"l": 20, "r": 20, "t": 20, "b": 20}, height=380)
    return fig


def filter_data(selected_departments: list[str] | None) -> pd.DataFrame:
    if MORTALITY_DF.empty:
        return MORTALITY_DF
    if not selected_departments:
        return MORTALITY_DF
    filtered = MORTALITY_DF[MORTALITY_DF["department"].isin(selected_departments)]
    return filtered if not filtered.empty else MORTALITY_DF


# ─── KPI Cards ──────────────────────────────────────────────────────────────

def compute_kpis(df: pd.DataFrame) -> dict:
    if df.empty:
        return {"total": 0, "departments": 0, "top_department": "N/A",
                "top_month": "N/A", "homicides_x95": 0}
    return {
        "total": len(df),
        "departments": df["department"].dropna().nunique(),
        "top_department": df["department"].value_counts().idxmax() if not df["department"].dropna().empty else "N/A",
        "top_month": df["month"].value_counts().idxmax() if not df["month"].dropna().empty else "N/A",
        "homicides_x95": int(df["cause_code"].astype(str).str.startswith("X95").sum()),
    }


def build_kpi_cards(df: pd.DataFrame) -> html.Div:
    kpis = compute_kpis(df)
    cards = [
        _kpi_card("Total defunciones", f"{kpis['total']:,}", "icon-deaths"),
        _kpi_card("Departamentos", str(kpis["departments"]), "icon-dept"),
        _kpi_card("Depto. más afectado", str(kpis["top_department"]), "icon-top"),
        _kpi_card("Mes más letal", str(kpis["top_month"]), "icon-month"),
        _kpi_card("Homicidios (X95)", f"{kpis['homicides_x95']:,}", "icon-homicide"),
    ]
    return html.Div(className="kpi-row", children=cards, id="kpi-row")


def _kpi_card(label: str, value: str, icon_class: str) -> html.Div:
    return html.Div(className="kpi-card", children=[
        html.Div(className=f"kpi-icon {icon_class}"),
        html.Div(className="kpi-content", children=[
            html.Span(value, className="kpi-value"),
            html.Span(label, className="kpi-label"),
        ]),
    ])


# ─── Chart builders ─────────────────────────────────────────────────────────

def build_map_figure(df: pd.DataFrame) -> go.Figure:
    if df.empty or "department" not in df.columns:
        return empty_figure("Carga los archivos en data/ para ver el mapa")

    dept_counts = df.groupby(["department", "dept_code"], observed=True).size().reset_index(name="deaths")

    def get_coords(row):
        code = int(row["dept_code"]) if pd.notna(row.get("dept_code")) else None
        if code and code in DEPARTMENT_COORDS_BY_CODE:
            return pd.Series(DEPARTMENT_COORDS_BY_CODE[code])
        return pd.Series((None, None))

    dept_counts[["lat", "lon"]] = dept_counts.apply(get_coords, axis=1)
    dept_counts = dept_counts.dropna(subset=["lat", "lon"])

    if dept_counts.empty:
        return empty_figure("No se encontraron coordenadas")

    total = dept_counts["deaths"].sum()
    dept_counts["pct"] = (dept_counts["deaths"] / total * 100).round(1)

    fig = px.scatter_geo(
        dept_counts, lat="lat", lon="lon", size="deaths", color="deaths",
        hover_name="department",
        hover_data={"lat": False, "lon": False, "deaths": True, "pct": ":.1f"},
        labels={"deaths": "Muertes", "pct": "% del total"},
        color_continuous_scale="YlOrRd", projection="mercator",
        title="Distribución total de muertes por departamento (2019)",
    )
    fig.update_geos(visible=False, showcountries=True, countrycolor="#6b7280",
                    showland=True, landcolor="#0f172a", showocean=True,
                    oceancolor="#0b1120", fitbounds="locations")
    fig.update_layout(paper_bgcolor="#111827", plot_bgcolor="#111827",
                      font={"color": "#f3f4f6"}, margin={"l": 0, "r": 0, "t": 50, "b": 0},
                      height=430, coloraxis_colorbar={"title": "Muertes"})
    return fig


def build_month_figure(df: pd.DataFrame) -> go.Figure:
    if df.empty or "month" not in df.columns:
        return empty_figure("No hay datos mensuales")

    monthly = df.dropna(subset=["month"]).groupby("month", observed=True).size().reset_index(name="deaths")
    if monthly.empty:
        return empty_figure("No hay datos mensuales suficientes")

    fig = px.line(monthly, x="month", y="deaths", markers=True,
                  title="Total de muertes por mes en Colombia (2019)",
                  labels={"month": "Mes", "deaths": "Muertes"})
    fig.update_traces(line={"color": "#38bdf8", "width": 3}, marker={"size": 10},
                      hovertemplate="<b>%{x}</b><br>Muertes: %{y:,}<extra></extra>")
    fig.update_layout(paper_bgcolor="#111827", plot_bgcolor="#111827",
                      font={"color": "#f3f4f6"}, xaxis_title="Mes", yaxis_title="Muertes",
                      height=380, margin={"l": 40, "r": 20, "t": 50, "b": 40})
    fig.update_xaxes(categoryorder="array", categoryarray=MONTH_ORDER)
    return fig


def build_violent_cities_figure(df: pd.DataFrame) -> go.Figure:
    if df.empty or "municipality" not in df.columns:
        return empty_figure("No hay datos de ciudades violentas")

    violent = df[df["cause_code"].astype(str).str.startswith("X95")]
    if violent.empty:
        return empty_figure("No se encontraron registros X95")

    top = violent.groupby("municipality", observed=True).size().sort_values(ascending=False).head(5).reset_index(name="homicidios")

    fig = px.bar(top, x="homicidios", y="municipality", orientation="h",
                 title="Top 5 ciudades más violentas (homicidios X95)",
                 text="homicidios", color="homicidios",
                 color_continuous_scale=["#fbbf24", "#f97316", "#ef4444", "#dc2626", "#991b1b"])
    fig.update_traces(textposition="inside", textfont={"size": 13, "color": "#fff"})
    fig.update_layout(paper_bgcolor="#111827", plot_bgcolor="#111827",
                      font={"color": "#f3f4f6"}, xaxis_title="Homicidios (X95)", yaxis_title="",
                      height=380, margin={"l": 10, "r": 30, "t": 55, "b": 40},
                      coloraxis_showscale=False,
                      yaxis={"categoryorder": "total ascending", "tickfont": {"size": 12}})
    return fig


def build_low_mortality_pie(df: pd.DataFrame) -> go.Figure:
    if df.empty or "municipality" not in df.columns:
        return empty_figure("No hay datos para el gráfico circular")

    city_counts = df.groupby("municipality", observed=True).size().sort_values(ascending=True).head(10).reset_index(name="deaths")

    fig = px.pie(city_counts, names="municipality", values="deaths",
                 title="10 ciudades con menor índice de mortalidad", hole=0.45)
    fig.update_traces(textposition="inside", textinfo="percent+label",
                      hovertemplate="<b>%{label}</b><br>Defunciones: %{value:,}<br>Proporción: %{percent}<extra></extra>")
    fig.update_layout(paper_bgcolor="#111827", plot_bgcolor="#111827",
                      font={"color": "#f3f4f6"}, height=380,
                      margin={"l": 20, "r": 20, "t": 50, "b": 20},
                      legend={"font": {"color": "#f3f4f6"}})
    return fig


def build_top_causes_table(df: pd.DataFrame) -> tuple[list[dict], list[dict]]:
    if df.empty:
        return [], []
    causes = df.groupby(["cause_code", "cause_name"], observed=True).size().sort_values(ascending=False).head(10).reset_index(name="cases")
    rows = causes.to_dict("records")
    columns = [{"name": "Codigo", "id": "cause_code"},
               {"name": "Nombre", "id": "cause_name"},
               {"name": "Total", "id": "cases"}]
    return rows, columns


def build_sex_department_figure(df: pd.DataFrame) -> go.Figure:
    if df.empty or "department" not in df.columns:
        return empty_figure("No hay datos por sexo")

    grouped = df.groupby(["department", "sex"], observed=True).size().reset_index(name="deaths")
    grouped = grouped[grouped["sex"].isin(["Hombre", "Mujer", "Indeterminado"])]
    if grouped.empty:
        return empty_figure("No hay datos suficientes")

    abbrev = {
        "ARCHIPIELAGO DE SAN ANDRES, PROVIDENCIA Y SANTA CATALINA": "SAN ANDRÉS",
        "ARCHIPIÉLAGO DE SAN ANDRÉS, PROVIDENCIA Y SANTA CATALINA": "SAN ANDRÉS",
        "NORTE DE SANTANDER": "NTE. SANTANDER",
    }
    grouped["dept_label"] = grouped["department"].apply(lambda d: abbrev.get(str(d).upper(), d))

    dept_totals = grouped.groupby("dept_label")["deaths"].transform("sum")
    grouped["pct"] = (grouped["deaths"] / dept_totals * 100).round(1)

    color_map = {"Hombre": "#38bdf8", "Mujer": "#f472b6", "Indeterminado": "#a3e635"}
    fig = px.bar(grouped, x="dept_label", y="deaths", color="sex",
                 color_discrete_map=color_map,
                 title="Comparación del total de muertes por sexo en cada departamento",
                 barmode="stack", hover_data={"pct": ":.1f"},
                 labels={"deaths": "Muertes", "sex": "Sexo", "dept_label": "Departamento", "pct": "% en depto."})
    fig.update_layout(paper_bgcolor="#111827", plot_bgcolor="#111827",
                      font={"color": "#f3f4f6"}, xaxis_title="Departamento", yaxis_title="Muertes",
                      height=500, margin={"l": 50, "r": 20, "t": 50, "b": 160},
                      legend={"orientation": "h", "y": -0.35, "title": "Sexo"})
    fig.update_xaxes(tickangle=-45, tickfont={"size": 10})
    return fig


def build_age_histogram(df: pd.DataFrame) -> go.Figure:
    if df.empty or "age_category" not in df.columns:
        return empty_figure("No hay datos de edades")

    age_counts = df.groupby("age_category", observed=True).size().reset_index(name="deaths")
    age_counts["age_category"] = pd.Categorical(age_counts["age_category"], categories=AGE_ORDER, ordered=True)
    age_counts = age_counts.sort_values("age_category")

    fig = px.bar(age_counts, x="age_category", y="deaths",
                 title="Distribución de muertes por grupo de edad (GRUPO_EDAD1)",
                 text="deaths", color="age_category",
                 color_discrete_sequence=px.colors.sequential.Tealgrn)
    fig.update_traces(textposition="outside")
    fig.update_layout(paper_bgcolor="#111827", plot_bgcolor="#111827",
                      font={"color": "#f3f4f6"}, xaxis_title="Grupo de edad", yaxis_title="Muertes",
                      height=380, margin={"l": 40, "r": 20, "t": 50, "b": 80}, showlegend=False)
    fig.update_xaxes(tickangle=-25)
    return fig


# ─── Layout ─────────────────────────────────────────────────────────────────

app.layout = html.Div(
    className="page-shell",
    children=[
        html.Div(
            className="hero-card",
            children=[
                html.Div(className="hero-copy", children=[
                    html.P("Aplicaciones 1 - Actividad 4 - Plinio Hernandez, Jherson Guzman", className="eyebrow"),
                    html.H1("Mortalidad en Colombia 2019"),
                    html.P("Explora el comportamiento de la mortalidad por departamento, mes, ciudad, sexo, causa y grupo de edad en una sola vista interactiva.", className="hero-text"),
                ]),
                html.Div(className="hero-panel", children=[
                    html.Div("Estado de datos", className="panel-label"),
                    html.Div("Archivos cargados" if not MORTALITY_DF.empty else "Pendiente: carga los datos", className="panel-value"),
                    html.Div(f"Registros: {len(MORTALITY_DF):,}" if not MORTALITY_DF.empty else "Sin datos", className="panel-meta"),
                ]),
            ],
        ),
        build_kpi_cards(MORTALITY_DF),
        html.Div(className="controls-card", children=[
            html.Label("Filtrar por departamento"),
            dcc.Dropdown(id="department-filter",
                         options=[{"label": d, "value": d} for d in AVAILABLE_DEPARTMENTS],
                         value=[], multi=True,
                         placeholder="Selecciona uno o varios departamentos", className="dropdown"),
        ]),
        html.Div(className="grid grid-map", children=[
            dcc.Graph(id="map-graph", figure=build_map_figure(MORTALITY_DF), config={"displayModeBar": False})
        ]),
        html.Div(className="grid two-col", children=[
            dcc.Graph(id="month-graph", figure=build_month_figure(MORTALITY_DF), config={"displayModeBar": False}),
            dcc.Graph(id="violent-cities-graph", figure=build_violent_cities_figure(MORTALITY_DF), config={"displayModeBar": False}),
        ]),
        html.Div(className="grid two-col", children=[
            dcc.Graph(id="low-mortality-pie", figure=build_low_mortality_pie(MORTALITY_DF), config={"displayModeBar": False}),
            dcc.Graph(id="age-histogram", figure=build_age_histogram(MORTALITY_DF), config={"displayModeBar": False}),
        ]),
        html.Div(className="grid row-1-2", children=[
            dcc.Graph(id="sex-department-graph", figure=build_sex_department_figure(MORTALITY_DF), config={"displayModeBar": False}),
        ]),
        html.Div(className="grid grid-map table-section", children=[
            html.Div(className="card table-card", children=[
                html.H3("Top 10 causas de muerte"),
                dash_table.DataTable(
                    id="causes-table",
                    columns=[{"name": "Codigo", "id": "cause_code"},
                             {"name": "Nombre", "id": "cause_name"},
                             {"name": "Total", "id": "cases"}],
                    data=build_top_causes_table(MORTALITY_DF)[0],
                    style_table={"overflowX": "auto"},
                    style_cell={"backgroundColor": "#111827", "color": "#f3f4f6",
                                "border": "1px solid #243244", "padding": "10px",
                                "fontFamily": "sans-serif", "fontSize": "14px",
                                "textAlign": "left", "whiteSpace": "normal", "height": "auto"},
                    style_header={"backgroundColor": "#0f172a", "fontWeight": "700",
                                  "color": "#e5e7eb", "border": "1px solid #243244"},
                    page_size=10,
                ),
            ]),
        ]),
        dcc.Interval(id="heartbeat", interval=60_000, n_intervals=0),
    ],
)


# ─── Callback ───────────────────────────────────────────────────────────────

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
    return (
        build_map_figure(filtered),
        build_month_figure(filtered),
        build_violent_cities_figure(filtered),
        build_low_mortality_pie(filtered),
        build_age_histogram(filtered),
        build_sex_department_figure(filtered),
        table_rows,
        table_columns,
        build_kpi_cards(filtered).children,
    )


if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=int(os.getenv("PORT", "8050")))

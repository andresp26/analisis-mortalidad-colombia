# 📊 Mortalidad en Colombia 2019 — Dashboard Interactivo

> Aplicación web dinámica desarrollada en Python con Dash y Plotly para explorar y analizar los datos de mortalidad no fetal en Colombia durante el año 2019, a partir de los microdatos oficiales del DANE.

---

## 🌐 Enlaces

| Recurso | URL |
|---------|-----|
| **Aplicación desplegada** | [analisis-mortalidad-colombia.onrender.com](https://analisis-mortalidad-colombia.onrender.com) |
| **Repositorio GitHub** | [github.com/andresp26/analisis-mortalidad-colombia](https://github.com/andresp26/analisis-mortalidad-colombia) |

---

## 👥 Integrantes

- **Plinio Andrés Hernández**
- **Jherson Guzmán Ramírez**

**Asignatura:** Aplicaciones 1 — Actividad 4  
**Universidad:** Universidad de La Salle

---

## 🎯 Objetivo

Analizar la distribución de la mortalidad en Colombia por departamento, mes, ciudad, sexo, causa de muerte y grupo de edad, proporcionando una herramienta accesible para identificar patrones demográficos y regionales.

---

## 🖥️ Visualizaciones implementadas

| # | Tipo de gráfico | Descripción |
|---|----------------|-------------|
| 1 | **Mapa geográfico** | Distribución total de muertes por departamento en Colombia (2019) |
| 2 | **Gráfico de líneas** | Total de muertes por mes, mostrando variaciones a lo largo del año |
| 3 | **Gráfico de barras** | Top 5 ciudades más violentas (homicidios con código X95 — agresión con armas de fuego) |
| 4 | **Gráfico circular** | 10 ciudades con menor índice de mortalidad |
| 5 | **Tabla** | 10 principales causas de muerte (código CIE-10, nombre y total de casos, orden descendente) |
| 6 | **Barras apiladas** | Comparación del total de muertes por sexo en cada departamento |
| 7 | **Histograma** | Distribución de muertes por grupo de edad según la variable GRUPO_EDAD1 |

### Categorías de edad (GRUPO_EDAD1)

| Categoría | Códigos DANE | Rango de edad |
|-----------|:------------:|---------------|
| Mortalidad neonatal | 0–4 | Menor de 1 mes |
| Mortalidad infantil | 5–6 | 1 a 11 meses |
| Primera infancia | 7–8 | 1 a 4 años |
| Niñez | 9–10 | 5 a 14 años |
| Adolescencia | 11 | 15 a 19 años |
| Juventud | 12–13 | 20 a 29 años |
| Adultez temprana | 14–16 | 30 a 44 años |
| Adultez intermedia | 17–19 | 45 a 59 años |
| Vejez | 20–24 | 60 a 84 años |
| Longevidad / Centenarios | 25–28 | 85 a 100+ años |
| Edad desconocida | 29 | Sin información |

---

## 🏗️ Estructura del proyecto

```
├── app.py                  # Aplicación principal (Dash + Plotly)
├── convert_to_parquet.py   # Script de conversión Excel → Parquet
├── requirements.txt        # Dependencias de Python
├── Procfile                # Comando de arranque (gunicorn)
├── render.yaml             # Configuración de despliegue en Render
├── assets/
│   └── styles.css          # Estilos del dashboard (tema oscuro)
└── data/
    ├── NoFetal2019.parquet       # Microdatos de mortalidad 2019
    ├── CodigosDeMuerte.parquet   # Catálogo CIE-10 de causas de muerte
    └── Divipola.parquet          # División político-administrativa (DANE)
```

---

## ⚙️ Tecnologías utilizadas

| Tecnología | Propósito |
|-----------|-----------|
| **Python 3.11** | Lenguaje principal |
| **Dash** | Framework web para dashboards interactivos |
| **Plotly** | Librería de visualización de datos |
| **Pandas** | Manipulación y análisis de datos |
| **PyArrow / Parquet** | Formato de datos optimizado para carga rápida |
| **Gunicorn** | Servidor WSGI para producción |
| **Render** | Plataforma de despliegue (PaaS) |

---

## 🚀 Instalación local

```bash
# 1. Clonar el repositorio
git clone https://github.com/andresp26/analisis-mortalidad-colombia.git
cd analisis-mortalidad-colombia

# 2. Crear y activar entorno virtual
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux/Mac

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Ejecutar la aplicación
python app.py
```

La aplicación estará disponible en `http://localhost:8050`

---

## ☁️ Despliegue en Render

1. Crear cuenta en [render.com](https://render.com) y conectar con GitHub.
2. Crear un **Web Service** y seleccionar el repositorio.
3. Render detecta automáticamente el archivo `render.yaml` con la configuración:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn app:server`
   - **Instance Type:** Free
4. El despliegue se ejecuta automáticamente con cada push a `master`.

---

## 📁 Fuentes de datos

| Archivo | Descripción | Fuente |
|---------|-------------|--------|
| `NoFetal2019.parquet` | Registros individuales de defunciones no fetales 2019 | DANE — Estadísticas Vitales |
| `CodigosDeMuerte.parquet` | Catálogo de códigos CIE-10 con descripciones | DANE / OMS |
| `Divipola.parquet` | Códigos y nombres de departamentos y municipios | DANE — DIVIPOLA |

---

## 📝 Notas técnicas

- Los datos originales en formato Excel fueron convertidos a **Parquet** para optimizar el tiempo de carga (~10x más rápido).
- El script `convert_to_parquet.py` permite regenerar los archivos Parquet a partir de los Excel originales si es necesario.
- La aplicación incluye un filtro interactivo por departamento que actualiza todas las visualizaciones en tiempo real.
- En el tier gratuito de Render, la instancia se suspende tras 15 minutos de inactividad. La primera visita puede tardar ~30 segundos en despertar.

---

*Desarrollado como parte de la Actividad 4 — Aplicaciones 1, Universidad de La Salle.*

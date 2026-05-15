# Mortalidad Colombia 2019

## Introduccion
Aplicacion web dinamica en Python para explorar la mortalidad en Colombia durante 2019 usando Dash y Plotly.

## Objetivo
Analizar distribuciones de mortalidad por departamento, mes, ciudad, sexo, causa y grupo de edad a partir de los archivos del DANE.

## Estructura del proyecto
- `app.py`: aplicacion principal de Dash.
- `requirements.txt`: dependencias del proyecto.
- `Procfile`: comando de arranque para Railway.
- `data/`: archivos Excel de entrada.
- `assets/`: estilos y recursos visuales.

## Requisitos
- Python 3.10 o superior.
- Dash.
- Plotly.
- Pandas.
- Openpyxl.
- Gunicorn para despliegue.

## Instalacion local
1. Clona el repositorio.
2. Crea y activa un entorno virtual.
3. Instala dependencias con `pip install -r requirements.txt`.
4. Coloca estos archivos en `data/`:
   - `NoFetal2019.xlsx`
   - `CodigosDeMuerte.xlsx`
   - `Divipola.xlsx`
5. Ejecuta `python app.py`.

## Despliegue en Railway
1. Sube el repositorio a GitHub.
2. Crea un proyecto nuevo en Railway desde GitHub.
3. Verifica que Railway detecte `Procfile` y use `gunicorn app:server`.
4. Define las variables o configuraciones necesarias si Railway lo solicita.
5. Publica la aplicacion y copia la URL generada.

## Software
- Python
- Dash
- Plotly
- Pandas
- Gunicorn

## Visualizaciones y hallazgos
Esta seccion se completara cuando se carguen los datos reales y se generen las capturas finales de la aplicacion.

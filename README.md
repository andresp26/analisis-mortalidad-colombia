# Mortalidad Colombia 2019

## Introduccion
Aplicacion web dinamica en Python para explorar la mortalidad en Colombia durante 2019 usando Dash y Plotly.

## Objetivo
Analizar distribuciones de mortalidad por departamento, mes, ciudad, sexo, causa y grupo de edad a partir de los archivos del DANE.

## Integrantes del grupo
- Plinio Andres Hernandez
- Jherson Guzman Ramirez

## Enlaces de entrega
- URL de la aplicacion desplegada: https://analisis-mortalidad-colombia.onrender.com
- URL del repositorio en GitHub: https://github.com/andresp26/analisis-mortalidad-colombia

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

## Despliegue en Render (opcional)
1. Conecta el repositorio en Render.
2. Configura el servicio web con el comando `gunicorn app:server`.
3. Agrega la variable `PORT` si Render la solicita automaticamente.
4. Despliega y copia la URL publica.

## Software
- Python
- Dash
- Plotly
- Pandas
- Gunicorn

## Visualizaciones y hallazgos
Incluye capturas de pantalla y una breve interpretacion por grafico.

1. Mapa de muertes por departamento
   - Hallazgo principal: [PENDIENTE]
   - Evidencia: captura del mapa.
2. Serie mensual de muertes
   - Hallazgo principal: [PENDIENTE]
   - Evidencia: captura del grafico de lineas.
3. Top 5 ciudades mas violentas (homicidios X95)
   - Hallazgo principal: [PENDIENTE]
   - Evidencia: captura del grafico de barras.
4. 10 ciudades con menor indice de mortalidad
   - Hallazgo principal: [PENDIENTE]
   - Evidencia: captura del grafico circular.
5. Top 10 causas de muerte
   - Hallazgo principal: [PENDIENTE]
   - Evidencia: captura de la tabla.
6. Muertes por sexo y departamento (barras apiladas)
   - Hallazgo principal: [PENDIENTE]
   - Evidencia: captura del grafico de barras apiladas.
7. Distribucion por grupo de edad
   - Hallazgo principal: [PENDIENTE]
   - Evidencia: captura del histograma.

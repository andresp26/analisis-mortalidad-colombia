"""
Script de conversión: Excel → Parquet.
Ejecutar una sola vez localmente para generar los archivos .parquet en data/.
Después de ejecutar, hacer commit de los .parquet y push.

Uso:
    python convert_to_parquet.py
"""

from pathlib import Path
import pandas as pd

DATA_DIR = Path(__file__).resolve().parent / "data"

FILES = {
    "NoFetal2019.xlsx": {"skiprows": 0},
    "CodigosDeMuerte.xlsx": {"skiprows": 8},
    "Divipola.xlsx": {"skiprows": 0},
}


def convert():
    for filename, opts in FILES.items():
        xlsx_path = DATA_DIR / filename
        parquet_path = DATA_DIR / filename.replace(".xlsx", ".parquet")

        if not xlsx_path.exists():
            print(f"  SKIP: {filename} no encontrado")
            continue

        print(f"  Leyendo {filename}...")
        df = pd.read_excel(xlsx_path, skiprows=opts.get("skiprows", 0))
        df.to_parquet(parquet_path, index=False, engine="pyarrow")

        xlsx_size = xlsx_path.stat().st_size / 1024 / 1024
        parquet_size = parquet_path.stat().st_size / 1024 / 1024
        print(f"  {filename}: {xlsx_size:.2f} MB → {parquet_path.name}: {parquet_size:.2f} MB")

    print("\nConversión completada. Haz commit de los archivos .parquet.")


if __name__ == "__main__":
    convert()

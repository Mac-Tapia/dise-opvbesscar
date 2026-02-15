"""
Script de inicializacion y utilidades para analisis de generacion solar.

Proporciona funciones helper para:
- Cargar datos de generacion solar
- Consultas rapidas
- Exportar resultados
- Generar reportes
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Dict, Any
import pandas as pd
import json


def cargar_generacion_solar(csv_path: Optional[str] = None) -> pd.DataFrame:
    """Cargar datos de generacion solar desde CSV.
    
    Args:
        csv_path: Ruta al archivo CSV (default: data/oe2/Generacionsolar/...)
    
    Returns:
        DataFrame con los datos
    """
    if csv_path is None:
        csv_path = "data/oe2/Generacionsolar/pv_generation_timeseries.csv"
    
    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(f"Archivo no encontrado: {csv_path}")
    
    df = pd.read_csv(csv_path, index_col='datetime', parse_dates=True)
    
    return df


def energia_total_anual(df: pd.DataFrame) -> float:
    """Obtener energia total anual en kWh."""
    return df['ac_energy_kwh'].sum()


def energia_por_mes(df: pd.DataFrame) -> pd.Series:
    """Obtener energia mensual."""
    return df['ac_energy_kwh'].resample('ME').sum()


def energia_por_dia(df: pd.DataFrame) -> pd.Series:
    """Obtener energia diaria."""
    return df['ac_energy_kwh'].resample('D').sum()


def potencia_promedio(df: pd.DataFrame) -> float:
    """Obtener potencia promedio en kW."""
    return df['ac_power_kw'].mean()


def potencia_maxima(df: pd.DataFrame) -> float:
    """Obtener potencia maxima en kW."""
    return df['ac_power_kw'].max()


def temperatura_promedio(df: pd.DataFrame) -> float:
    """Obtener temperatura promedio en °C."""
    return df['temp_air_c'].mean()


def irradiancia_promedio(df: pd.DataFrame) -> float:
    """Obtener irradiancia promedio en W/m²."""
    return df['ghi_wm2'].mean()


def dia_mas_despejado(df: pd.DataFrame) -> tuple:
    """Encontrar el dia con mas generacion."""
    daily = df['ac_energy_kwh'].resample('D').sum()
    idx = daily.idxmax()
    return idx.date(), daily.max()


def dia_mas_nublado(df: pd.DataFrame) -> tuple:
    """Encontrar el dia con menos generacion."""
    daily = df['ac_energy_kwh'].resample('D').sum()
    idx = daily.idxmin()
    return idx.date(), daily.min()


def dia_templado(df: pd.DataFrame) -> tuple:
    """Encontrar el dia con energia mediana."""
    daily = df['ac_energy_kwh'].resample('D').sum()
    median = daily.median()
    idx = (daily - median).abs().idxmin()
    return idx.date(), daily[idx]


def perfil_horario(df: pd.DataFrame, fecha: pd.Timestamp) -> pd.DataFrame:
    """Obtener perfil horario para una fecha especifica."""
    day_data = df[df.index.date == fecha.date()]
    return day_data[['ac_energy_kwh', 'ac_power_kw', 'temp_air_c', 'ghi_wm2']]


def exportar_resumen_json(df: pd.DataFrame, output_path: Optional[str] = None) -> dict[str, Any]:
    """Exportar resumen a JSON."""
    if output_path is None:
        output_path = "data/oe2/Generacionsolar/resumen_generacion.json"
    
    daily = df['ac_energy_kwh'].resample('D').sum()
    monthly = df['ac_energy_kwh'].resample('ME').sum()
    
    resumen = {
        'anual': {
            'energia_kwh': float(df['ac_energy_kwh'].sum()),
            'energia_mwh': float(df['ac_energy_kwh'].sum() / 1000),
            'potencia_promedio_kw': float(df['ac_power_kw'].mean()),
            'potencia_maxima_kw': float(df['ac_power_kw'].max()),
            'temperatura_promedio_c': float(df['temp_air_c'].mean()),
            'irradiancia_promedio_wm2': float(df['ghi_wm2'].mean()),
        },
        'diario': {
            'promedio_kwh': float(daily.mean()),
            'maximo_kwh': float(daily.max()),
            'minimo_kwh': float(daily.min()),
        },
        'mensual': {
            mes: float(valor) for mes, valor in monthly.items()
        },
    }
    
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(resumen, f, indent=2, ensure_ascii=False, default=str)
    
    return resumen


def mostrar_estadisticas_rapidas(df: pd.DataFrame) -> None:
    """Mostrar estadisticas rapidas en consola."""
    print("""
    ╔============================================================╗
    ║     ESTADISTICAS RAPIDAS - GENERACION SOLAR 2024          ║
    ╚============================================================╝
    
    [GRAPH] ENERGIA:
       Total anual:         {:.0f} kWh ({:.2f} GWh)
       Promedio diario:     {:.0f} kWh/dia
       
    ⚡ POTENCIA:
       Promedio:            {:.1f} kW
       Maxima:              {:.1f} kW
       
    🌡️  TEMPERATURA:
       Promedio:            {:.1f} °C
       
    ☀️  IRRADIANCIA:
       Promedio:            {:.1f} W/m²
    
    ╠============================================================╣
    """.format(
        energia_total_anual(df),
        energia_total_anual(df) / 1e6,
        energia_total_anual(df) / 365,
        potencia_promedio(df),
        potencia_maxima(df),
        temperatura_promedio(df),
        irradiancia_promedio(df),
    ))
    
    fecha_despejado, energia_despejado = dia_mas_despejado(df)
    fecha_nublado, energia_nublado = dia_mas_nublado(df)
    fecha_templado, energia_templado = dia_templado(df)
    
    print(f"""
    🔆 DIAS REPRESENTATIVOS:
    
       Mas despejado:       {fecha_despejado} ({energia_despejado:.0f} kWh)
       Mas nublado:         {fecha_nublado} ({energia_nublado:.0f} kWh)
       Dia templado:        {fecha_templado} ({energia_templado:.0f} kWh)
    
    ╚============================================================╝
    """)


if __name__ == "__main__":
    # Ejemplo de uso
    print("Modulo de utilidades para analisis de generacion solar")
    print("Importa esta modulo en tu codigo para usar las funciones")
    
    try:
        df = cargar_generacion_solar()
        mostrar_estadisticas_rapidas(df)
        exportar_resumen_json(df)
        print("\n[OK] Resumen exportado a: data/oe2/Generacionsolar/resumen_generacion.json")
    except FileNotFoundError as e:
        print(f"\n[!]  {e}")

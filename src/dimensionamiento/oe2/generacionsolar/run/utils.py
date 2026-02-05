"""
Script de inicialización y utilidades para análisis de generación solar.

Proporciona funciones helper para:
- Cargar datos de generación solar
- Consultas rápidas
- Exportar resultados
- Generar reportes
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Dict, Any
import pandas as pd
import json


def cargar_generacion_solar(csv_path: Optional[str] = None) -> pd.DataFrame:
    """Cargar datos de generación solar desde CSV.
    
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
    
    df = pd.read_csv(csv_path)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df.set_index('timestamp', inplace=True)
    
    return df


def energia_total_anual(df: pd.DataFrame) -> float:
    """Obtener energía total anual en kWh."""
    return df['ac_energy_kwh'].sum()


def energia_por_mes(df: pd.DataFrame) -> pd.Series:
    """Obtener energía mensual."""
    return df['ac_energy_kwh'].resample('ME').sum()


def energia_por_dia(df: pd.DataFrame) -> pd.Series:
    """Obtener energía diaria."""
    return df['ac_energy_kwh'].resample('D').sum()


def potencia_promedio(df: pd.DataFrame) -> float:
    """Obtener potencia promedio en kW."""
    return df['ac_power_kw'].mean()


def potencia_maxima(df: pd.DataFrame) -> float:
    """Obtener potencia máxima en kW."""
    return df['ac_power_kw'].max()


def temperatura_promedio(df: pd.DataFrame) -> float:
    """Obtener temperatura promedio en °C."""
    return df['temp_air_c'].mean()


def irradiancia_promedio(df: pd.DataFrame) -> float:
    """Obtener irradiancia promedio en W/m²."""
    return df['ghi_wm2'].mean()


def dia_mas_despejado(df: pd.DataFrame) -> tuple:
    """Encontrar el día con más generación."""
    daily = df['ac_energy_kwh'].resample('D').sum()
    idx = daily.idxmax()
    return idx.date(), daily.max()


def dia_mas_nublado(df: pd.DataFrame) -> tuple:
    """Encontrar el día con menos generación."""
    daily = df['ac_energy_kwh'].resample('D').sum()
    idx = daily.idxmin()
    return idx.date(), daily.min()


def dia_templado(df: pd.DataFrame) -> tuple:
    """Encontrar el día con energía mediana."""
    daily = df['ac_energy_kwh'].resample('D').sum()
    median = daily.median()
    idx = (daily - median).abs().idxmin()
    return idx.date(), daily[idx]


def perfil_horario(df: pd.DataFrame, fecha: pd.Timestamp) -> pd.DataFrame:
    """Obtener perfil horario para una fecha específica."""
    day_data = df[df.index.date == fecha.date()]
    return day_data[['ac_energy_kwh', 'ac_power_kw', 'temp_air_c', 'ghi_wm2']]


def exportar_resumen_json(df: pd.DataFrame, output_path: Optional[str] = None) -> Dict[str, Any]:
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
    """Mostrar estadísticas rápidas en consola."""
    print("""
    ╔════════════════════════════════════════════════════════════╗
    ║     ESTADÍSTICAS RÁPIDAS - GENERACIÓN SOLAR 2024          ║
    ╚════════════════════════════════════════════════════════════╝
    
    📊 ENERGÍA:
       Total anual:         {:.0f} kWh ({:.2f} GWh)
       Promedio diario:     {:.0f} kWh/día
       
    ⚡ POTENCIA:
       Promedio:            {:.1f} kW
       Máxima:              {:.1f} kW
       
    🌡️  TEMPERATURA:
       Promedio:            {:.1f} °C
       
    ☀️  IRRADIANCIA:
       Promedio:            {:.1f} W/m²
    
    ╠════════════════════════════════════════════════════════════╣
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
    🔆 DÍAS REPRESENTATIVOS:
    
       Más despejado:       {fecha_despejado} ({energia_despejado:.0f} kWh)
       Más nublado:         {fecha_nublado} ({energia_nublado:.0f} kWh)
       Día templado:        {fecha_templado} ({energia_templado:.0f} kWh)
    
    ╚════════════════════════════════════════════════════════════╝
    """)


if __name__ == "__main__":
    # Ejemplo de uso
    print("Módulo de utilidades para análisis de generación solar")
    print("Importa esta módulo en tu código para usar las funciones")
    
    try:
        df = cargar_generacion_solar()
        mostrar_estadisticas_rapidas(df)
        exportar_resumen_json(df)
        print("\n✓ Resumen exportado a: data/oe2/Generacionsolar/resumen_generacion.json")
    except FileNotFoundError as e:
        print(f"\n⚠️  {e}")

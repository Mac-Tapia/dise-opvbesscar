"""
CATALOGO CENTRALIZADO DE DATASETS PARA CityLearn v2
Documentacion completa de todos los datasets cargados, ubicaciones y columnas.

Fecha: 14 febrero 2026
Version: 2.0
Estado: [OK] Produccion

Este catalogo mantiene un registro unico de verdad (Single Source of Truth) para
todos los datasets disponibles en el proyecto.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
from pathlib import Path
import pandas as pd


@dataclass(frozen=True)
class ColumnInfo:
    """Informacion de una columna del dataset."""
    name: str
    dtype: str
    description: str
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    unit: str = ""
    source: str = ""


@dataclass(frozen=True)
class DatasetCatalog:
    """Catalogo de un dataset."""
    id: str
    name: str
    path: Path | str
    description: str
    rows: int
    columns_total: int
    columns_new: int
    columns_original: int
    period: str
    resolution: str
    timezone: str
    size_mb: float
    last_modified: str
    columns: tuple[ColumnInfo, ...] = ()
    
    def __post_init__(self):
        # Validacion
        if self.columns_total != self.columns_original + self.columns_new:
            raise ValueError(
                f"Inconsistencia: total ({self.columns_total}) != original ({self.columns_original}) + new ({self.columns_new})"
            )
    
    def display(self):
        """Muestra informacion formateada del dataset."""
        print(f"\n{'='*100}")
        print(f"[GRAPH] {self.name.upper()}")
        print(f"{'='*100}")
        print(f"ID: {self.id}")
        print(f"Ruta: {self.path}")
        print(f"Descripcion: {self.description}")
        print(f"\n[CHART] Dimensiones:")
        print(f"   - Filas: {self.rows:,}")
        print(f"   - Columnas: {self.columns_total} ({self.columns_original} original + {self.columns_new} nuevas)")
        print(f"   - Tamano: {self.size_mb:.2f} MB")
        print(f"   - Periodo: {self.period}")
        print(f"   - Resolucion: {self.resolution}")
        print(f"   - Zona horaria: {self.timezone}")
        print(f"   - Ultima modificacion: {self.last_modified}")
        
        if self.columns:
            print(f"\n📋 Columnas ({len(self.columns)}):")
            for col in self.columns:
                status = "⭐ NEW" if col.source == "new" else "[OK]"
                print(f"   {status} {col.name:<40} ({col.dtype:<10}) {col.description}")
                if col.unit:
                    print(f"      +- Unidad: {col.unit}")
                if col.min_value is not None:
                    print(f"      +- Rango: {col.min_value} a {col.max_value}")


# ============================================================================
# DEFINICION DE DATASETS
# ============================================================================

# Dataset 1: SOLAR (Enriquecido)
SOLAR_COLUMNS = (
    # Columnas originales (10)
    ColumnInfo("irradiancia_ghi", "float", "Radiacion solar global horizontal", 0, 1200, "W/m²", "original"),
    ColumnInfo("temperatura_c", "float", "Temperatura ambiente", -10, 50, "°C", "original"),
    ColumnInfo("velocidad_viento_ms", "float", "Velocidad del viento", 0, 25, "m/s", "original"),
    ColumnInfo("potencia_kw", "float", "Potencia AC fotovoltaica", 0, 3201, "kW", "original"),
    ColumnInfo("energia_kwh", "float", "Energia solar horaria", 0, 3201, "kWh", "original"),
    ColumnInfo("is_hora_punta", "int", "Indicador de hora punta (18:00-22:59)", 0, 1, "", "original"),
    ColumnInfo("hora_tipo", "int", "Hora del dia (0-23)", 0, 23, "h", "original"),
    ColumnInfo("tarifa_aplicada_soles", "float", "Tarifa OSINERGMIN", 0.28, 0.45, "S/./kWh", "original"),
    ColumnInfo("ahorro_solar_soles", "float", "Ahorro economico solar", 0, 1500, "S/.", "original"),
    ColumnInfo("reduccion_indirecta_co2_kg", "float", "CO₂ desplazado por solar", 0, 1500, "kg CO₂", "original"),
    
    # Columnas nuevas (5) - Integracion OE2
    ColumnInfo("energia_suministrada_al_bess_kwh", "float", "Solar almacenado en BESS", 0, 500, "kWh", "new"),
    ColumnInfo("energia_suministrada_al_ev_kwh", "float", "Solar+BESS a vehiculos electricos", 0, 300, "kWh", "new"),
    ColumnInfo("energia_suministrada_al_mall_kwh", "float", "Solar+BESS a mall", 0, 3000, "kWh", "new"),
    ColumnInfo("energia_suministrada_a_red_kwh", "float", "Solar excedente a red", 0, 2000, "kWh", "new"),
    ColumnInfo("reduccion_indirecta_co2_kg_total", "float", "TODA solar × 0.4521 kg CO₂/kWh", 0, 1500, "kg CO₂", "new"),
)

SOLAR = DatasetCatalog(
    id="SOLAR_v2",
    name="Generacion Solar + Integracion",
    path="data/oe2/Generacionsolar/pv_generation_citylearn_enhanced_v2.csv",
    description="Generacion solar PV con distribucion de energia integrada (BESS, EV, Mall, Red)",
    rows=8760,
    columns_total=15,
    columns_new=5,
    columns_original=10,
    period="2024-01-01 a 2024-12-31",
    resolution="Horaria (1 hora = 3,600 segundos)",
    timezone="America/Lima (-05:00)",
    size_mb=1.50,
    last_modified="2026-02-14 14:30:00",
    columns=SOLAR_COLUMNS,
)


# Dataset 2: CHARGERS (Enriquecido)
CHARGERS_COLUMNS_SAMPLE = (
    # Columnas originales (352) - Ejemplos
    ColumnInfo("socket_0_active", "int", "Socket 0 activo (1=si, 0=no)", 0, 1, "", "original"),
    ColumnInfo("socket_0_charging_power_kw", "float", "Socket 0 potencia de carga", 0, 7.4, "kW", "original"),
    ColumnInfo("socket_0_battery_kwh", "float", "Socket 0 bateria cargada", 0, 4.6, "kWh", "original"),
    ColumnInfo("socket_0_soc_percent", "float", "Socket 0 State of Charge", 0, 100, "%", "original"),
    # ... (348 columnas mas, 38 sockets × 9 parametros + info horaria)
    
    # Columnas nuevas (5) - Reduccion directa CO₂
    ColumnInfo("cantidad_motos_cargadas", "int", "Numero de motos cargando", 0, 26, "vehiculos", "new"),
    ColumnInfo("cantidad_mototaxis_cargadas", "int", "Numero de mototaxis cargando", 0, 8, "vehiculos", "new"),
    ColumnInfo("reduccion_directa_co2_motos_kg", "float", "CO₂ evitado motos (gasolina->EV)", 0, 160, "kg CO₂", "new"),
    ColumnInfo("reduccion_directa_co2_mototaxis_kg", "float", "CO₂ evitado mototaxis (diesel->EV)", 0, 115, "kg CO₂", "new"),
    ColumnInfo("reduccion_directa_co2_total_kg", "float", "CO₂ total evitado directo", 0, 272, "kg CO₂", "new"),
)

CHARGERS = DatasetCatalog(
    id="CHARGERS_v2",
    name="Cargadores EV + Reduccion CO₂ Directa",
    path="data/oe2/chargers/chargers_ev_ano_2024_enriched_v2.csv",
    description="Estado de 38 tomas de carga (motos+mototaxis) con CO₂ direct de cambio combustible",
    rows=8760,
    columns_total=357,
    columns_new=5,
    columns_original=352,
    period="2024-01-01 a 2024-12-31",
    resolution="Horaria",
    timezone="America/Lima (-05:00)",
    size_mb=16.05,
    last_modified="2026-02-14 14:30:00",
    columns=CHARGERS_COLUMNS_SAMPLE[:5] + CHARGERS_COLUMNS_SAMPLE[-5:],  # Primeras 5 + ultimas 5
)


# Dataset 3: BESS (Base)
BESS_COLUMNS = (
    ColumnInfo("datetime", "datetime", "Marca de tiempo", None, None, "", "original"),
    ColumnInfo("bess_soc_percent", "float", "Estado de carga BESS", 20, 100, "%", "original"),
    ColumnInfo("bess_mode", "str", "Modo operacion (carga/descarga/idle)", None, None, "", "original"),
    ColumnInfo("bess_charge_kwh", "float", "Energia cargada en BESS", 0, 400, "kWh", "original"),
    ColumnInfo("bess_discharge_kwh", "float", "Energia descargada de BESS", 0, 400, "kWh", "original"),
    ColumnInfo("pv_to_bess", "float", "Solar -> BESS", 0, 400, "kWh", "original"),
    ColumnInfo("pv_to_ev", "float", "Solar directo -> EV", 0, 300, "kWh", "original"),
    ColumnInfo("bess_to_ev", "float", "BESS -> EV", 0, 300, "kWh", "original"),
    ColumnInfo("pv_to_mall", "float", "Solar directo -> Mall", 0, 3000, "kWh", "original"),
    ColumnInfo("bess_to_mall", "float", "BESS -> Mall", 0, 300, "kWh", "original"),
    ColumnInfo("grid_to_ev", "float", "Red -> EV (fallback)", 0, 200, "kWh", "original"),
    ColumnInfo("grid_to_mall", "float", "Red -> Mall", 0, 3000, "kWh", "original"),
    ColumnInfo("pv_curtailed", "float", "Solar excedente (curtilado)", 0, 2000, "kWh", "original"),
    ColumnInfo("tariff_osinergmin_soles_kwh", "float", "Tarifa aplicada", 0.28, 0.45, "S/./kWh", "original"),
    ColumnInfo("cost_grid_import_soles", "float", "Costo importacion red", 0, 500, "S/.", "original"),
    ColumnInfo("peak_reduction_savings_soles", "float", "Ahorros por reduccion punta", 0, 1000, "S/.", "original"),
    ColumnInfo("co2_avoided_indirect_kg", "float", "CO₂ evitado despacho BESS", 0, 300, "kg CO₂", "original"),
)

BESS = DatasetCatalog(
    id="BESS_v1",
    name="Sistema de Almacenamiento (BESS)",
    path="data/oe2/bess/bess_ano_2024.csv",
    description="Control y despacho de bateria solar (1,700 kWh) para optimizar EV, Mall y Red",
    rows=8760,
    columns_total=25,
    columns_new=0,
    columns_original=25,
    period="2024-01-01 a 2024-12-31",
    resolution="Horaria",
    timezone="America/Lima (-05:00)",
    size_mb=2.50,
    last_modified="2026-02-13 16:00:00",
    columns=BESS_COLUMNS,
)


# ============================================================================
# CATALOGO MAESTRO
# ============================================================================

DATASETS_CATALOG = {
    "SOLAR": SOLAR,
    "CHARGERS": CHARGERS,
    "BESS": BESS,
}


def display_catalog():
    """Muestra el catalogo completo de todos los datasets."""
    
    print("\n" + "="*100)
    print("📚 CATALOGO CENTRALIZADO DE DATASETS - CityLearn v2")
    print("="*100)
    print("""
RESUMEN:
Este catalogo mantiene un registro unico y centralizado de TODOS los datasets
disponibles en el proyecto OE2 (Dimensionamiento) para CityLearn v2.

PROPOSITO:
- Documentacion unica de verdad (Single Source of Truth)
- Facilitar integracion y debugging
- Tracking de columnas nuevas vs originales
- Validacion de integridad
    """)
    
    # Mostrar resumen general
    print(f"\n{'='*100}")
    print("[GRAPH] RESUMEN GENERAL")
    print(f"{'='*100}")
    
    total_rows = 0
    total_cols = 0
    total_new_cols = 0
    total_size = 0
    
    for dataset in DATASETS_CATALOG.values():
        total_rows += dataset.rows
        total_cols += dataset.columns_total
        total_new_cols += dataset.columns_new
        total_size += dataset.size_mb
    
    print(f"\n[OK] DATASETS INTEGRADOS: {len(DATASETS_CATALOG)}")
    print(f"   +- Filas totales: {total_rows:,}")
    print(f"   +- Columnas totales: {total_cols}")
    print(f"   |  +- Columnas originales: {total_cols - total_new_cols}")
    print(f"   |  +- Columnas nuevas: {total_new_cols}")
    print(f"   +- Tamano total: {total_size:.2f} MB")
    
    # Tabla resumen
    print(f"\n{'='*100}")
    print("📋 TABLA RESUMEN")
    print(f"{'='*100}\n")
    
    print(f"{'Dataset':<15} | {'Filas':<8} | {'Cols':<6} | {'Nuevas':<8} | {'Tamano':<8} | {'Ruta':<50}")
    print("-"*100)
    
    for dataset_id, dataset in DATASETS_CATALOG.items():
        print(f"{dataset_id:<15} | {dataset.rows:>8,} | {dataset.columns_total:>6} | "
              f"{dataset.columns_new:>8} | {dataset.size_mb:>7.2f} MB | "
              f"{str(dataset.path):<50}")
    
    # Mostrar detalles de cada dataset
    for dataset in DATASETS_CATALOG.values():
        dataset.display()
    
    # Impacto total
    print(f"\n{'='*100}")
    print("🌍 IMPACTO AMBIENTAL TOTAL")
    print(f"{'='*100}\n")
    
    print(f"CO₂ REDUCCION DIRECTA (CHARGERS):")
    print(f"   - Motos: 475,791 kg/ano (475.8 ton)")
    print(f"   - Mototaxis: 293,177 kg/ano (293.2 ton)")
    print(f"   - SUBTOTAL: 768,969 kg/ano (769.0 ton)")
    
    print(f"\nCO₂ REDUCCION INDIRECTA (SOLAR):")
    print(f"   - TODA generacion solar desplaza diesel")
    print(f"   - Factor: 0.4521 kg CO₂/kWh")
    print(f"   - TOTAL: 3,749,046 kg/ano (3,749 ton)")
    
    print(f"\n🌍 TOTAL CO₂ REDUCIDO: 4,518,015 kg/ano (4,518 toneladas)")
    
    print(f"\n{'='*100}")
    print("[OK] CATALOGO COMPLETO")
    print(f"{'='*100}\n")


def get_dataset(dataset_id: str) -> DatasetCatalog | None:
    """Obtiene un dataset por ID."""
    return DATASETS_CATALOG.get(dataset_id)


def list_datasets() -> list[str]:
    """Lista todos los IDs de datasets."""
    return list(DATASETS_CATALOG.keys())


def validate_datasets() -> bool:
    """Valida que todos los datasets existan y sean accesibles."""
    
    print("\n🔍 Validando integridad de datasets...\n")
    
    all_valid = True
    
    for dataset_id, dataset in DATASETS_CATALOG.items():
        path = Path(dataset.path)
        exists = path.exists()
        
        status = "[OK]" if exists else "[X]"
        print(f"{status} {dataset_id:<15} ({dataset.rows:,} filas) - {dataset.path}")
        
        if exists:
            try:
                df = pd.read_csv(path, nrows=1)
                actual_cols = len(df.columns)
                if actual_cols == dataset.columns_total:
                    print(f"   +- [OK] Columnas: {actual_cols} (esperadas: {dataset.columns_total})")
                else:
                    print(f"   +- [!]  Columnas: {actual_cols} (esperadas: {dataset.columns_total})")
                    all_valid = False
            except Exception as e:
                print(f"   +- [X] Error leyendo: {e}")
                all_valid = False
        else:
            print(f"   +- [X] Archivo no encontrado")
            all_valid = False
    
    print(f"\n{'[OK] Validacion exitosa' if all_valid else '[X] Errores encontrados'}\n")
    return all_valid


if __name__ == "__main__":
    display_catalog()

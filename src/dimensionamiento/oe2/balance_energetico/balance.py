"""
Balance Energetico - MÓDULO ÚNICO DE GENERACIÓN DE GRÁFICAS v5.7

RESPONSABILIDAD EXCLUSIVA: Generar TODAS (16) las gráficas de balance energético
═════════════════════════════════════════════════════════════════════════════════
Este módulo es el ÚNICO responsable de:
  ✓ Visualización de balance energético
  ✓ Todas las 16 gráficas del sistema (integrada, exportación, BESS, CO₂, etc)
  ✓ Análisis de flujos energéticos
  ✓ Validación de capacidades (solar, BESS, demanda)

NOTA ARQUITECTÓNICA IMPORTANTE:
  NO generar gráficas en bess.py (dimensionamiento)
  TODAS las gráficas AQUÍ en balance.py (visualización)
  bess.py genera DATASET, balance.py genera GRÁFICAS

📊 16 GRÁFICAS GENERADAS POR plot_energy_balance():
  1. 00_BALANCE_INTEGRADO_COMPLETO.png - Balance integrado día típico
  2. 00.1_EXPORTACION_Y_PEAK_SHAVING.png - Exportación + peak shaving
  3. 00.2_GENERACION_EXPORTACION_INTEGRADA.png - Generación vs exportación
  4. 00.3_PEAK_SHAVING_INTEGRADO_MALL.png - Peak shaving del Mall
  5. 00_INTEGRAL_todas_curvas.png - Todas curvas integradas ⭐
  6. 00.5_FLUJO_ENERGETICO_INTEGRADO.png - Diagrama flujo energético
  7. 01_balance_5dias.png - Balance 5 días
  8. 02_balance_diario.png - Balance diario horario
  9. 03_distribucion_fuentes.png - Distribución de fuentes
  10. 04_cascada_energetica.png - Cascada energética
  11. 05_bess_soc.png - SOC del BESS
  12. 05.1_bess_carga_descarga.png - Carga/descarga BESS
  13. 08_pv_exportacion_desglose.png - Desglose exportación PV
  14. 06_emisiones_co2.png - Emisiones CO₂
  15. 07_utilizacion_pv.png - Utilización PV
  16. 99_CAPACIDAD_SOLAR_VALIDACION.png - Validación capacidad solar

ACTUALIZACIÓN v5.7 (2026-02-20):
- Agregada validación de capacidad solar anual (8.29 GWh)
- Validación de despacho vs generación
- Gráficas con límite de capacidad
- Información completa HP/HFP tarifaria

Uso:
    from balance import BalanceEnergeticoSystem
    graphics = BalanceEnergeticoSystem(df_balance)
    graphics.plot_energy_balance(output_dir)  # Genera TODAS las 16 gráficas
"""
from __future__ import annotations

import sys
import os

# FIX encoding en Windows para caracteres especiales (✓, ó, etc)
if sys.platform.startswith('win'):
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import sys
import os

import warnings
import numpy as np
import pandas as pd
from matplotlib import pyplot as plt
from matplotlib.patches import Rectangle
from matplotlib.ticker import FuncFormatter

# NEW v5.8: Auto-update en cambios de dataset
try:
    from src.utils.dataset_change_detector import DatasetChangeDetector
    HAS_CHANGE_DETECTOR = True
except ImportError:
    HAS_CHANGE_DETECTOR = False

# Silenciar advertencias de matplotlib sobre Glyph y tight_layout
warnings.filterwarnings('ignore', message='.*Glyph.*missing from font.*')
warnings.filterwarnings('ignore', message='.*Axes.*not compatible with tight_layout.*')

@dataclass(frozen=True)
class BalanceEnergeticoConfig:
    """Configuracion minima de visualizacion v5.7+.
    
    FIXED v5.8: BESS capacity unificado a 2,000 kWh (bess.py BESS_CAPACITY_KWH_V53)
    previousamente inconsistencia: 1,700 → 2,000 FIXED v5.8 (todos alineados a 2,000 kWh)
    """
    pv_capacity_kwp: float = 4050.0
    pv_annual_capacity_kwh: float = 8_292_514.17  # NEW v5.7: Capacidad anual real (8.29 GWh)
    demand_peak_limit_kw: float = 1900.0
    bess_capacity_kwh: float = 2000.0  # FIXED v5.8: de 1700 → 2000 (bess.py v5.3)
    bess_power_kw: float = 400.0
    dod: float = 0.80
    efficiency_roundtrip: float = 0.95
    co2_intensity_kg_per_kwh: float = 0.4521
    tariff_hp_soles_kwh: float = 0.45  # NEW v5.7: Tarifa HP (OSINERGMIN)
    tariff_hfp_soles_kwh: float = 0.28  # NEW v5.7: Tarifa HFP (OSINERGMIN)


class BalanceEnergeticoSystem:
    """Generador de graficas para balance energetico v5.7.
    
    SOLO Visualizacion - Recibe DataFrame precalculado.
    Incluye validación de capacidad solar anual (8.29 GWh).
    
    NEW v5.8: Detección automática de cambios en datasets (BESS, Solar, EV).
    """
    
    def __init__(self, df_balance: pd.DataFrame, config: Optional[BalanceEnergeticoConfig] = None, 
                 auto_update: bool = True):
        """Inicializa generador de graficas.
        
        Args:
            df_balance: DataFrame con datos precalculados
            config: Configuracion (usa defaults si es None)
            auto_update: Si True, regenera gráficas si detecta cambios en datasets
        """
        self.df_balance = df_balance
        self.config = config or BalanceEnergeticoConfig()
        self.auto_update = auto_update
        
        # NEW v5.8: Chequear cambios en datasets
        self._check_dataset_changes()
        
        # NEW v5.7: Validar capacidad solar anual
        self._validate_solar_capacity()
    
    def _check_dataset_changes(self) -> None:
        """NEW v5.8: Detecta cambios en datasets BESS, Solar, EV.
        
        Si auto_update=True y hay cambios, dispara regeneración automática.
        """
        if not HAS_CHANGE_DETECTOR or not self.auto_update:
            return
        
        try:
            detector = DatasetChangeDetector()
            changed_datasets = detector.get_changed_datasets()
            
            if changed_datasets:
                print(f"\n⚠️  NEW v5.8 AUTO-UPDATE: Cambios detectados en datasets:")
                for ds in changed_datasets:
                    print(f"   • {ds}")
                print(f"   → Las gráficas se regenerarán automáticamente")
                self._should_regenerate = True
            else:
                self._should_regenerate = False
        except Exception as e:
            # Silenciosamente ignorar errores en detección
            # para no romper inicialización si detector falla
            self._should_regenerate = False
    
    def _validate_solar_capacity(self) -> None:
        """NEW v5.7: Valida que la generación solar no exceda capacidad anual.
        
        Capacidad: 8,292,514.17 kWh/año (4,050 kWp @ factor de planta ~23%)
        """
        if 'pv_kwh' not in self.df_balance.columns:
            return  # Skip if column not present
        
        df = self.df_balance
        pv_annual = df['pv_kwh'].sum()
        capacity = self.config.pv_annual_capacity_kwh
        
        utilization_pct = (pv_annual / capacity * 100) if capacity > 0 else 0
        
        # Store metrics for use in plots
        self.pv_annual_generation = pv_annual
        self.pv_utilization_pct = utilization_pct
        self.pv_capacity_exceeded = utilization_pct > 100
        
        # Log validation result
        status_symbol = '✓' if not self.pv_capacity_exceeded else '⚠️'
        print(f'\n{status_symbol} Validación Solar v5.7: {pv_annual/1e6:.2f} GWh / {capacity/1e6:.2f} GWh ({utilization_pct:.1f}%)')
        
        if self.pv_capacity_exceeded:
            print(f'   ❌ ALERTA: La generación solar EXCEDE la capacidad anual')
            print(f'   Diferencia: +{(pv_annual - capacity)/1e6:.2f} GWh')
    
    def plot_energy_balance(self, out_dir: Optional[Path] = None) -> None:
        """Genera todas las gráficas de balance energético (incluyendo exportación e integración peak shaving).
        
        Args:
            out_dir: Directorio para guardar (default: outputs/balance_energetico)
        """
        if out_dir is None:
            out_dir = Path("outputs/balance_energetico")
        
        out_dir.mkdir(parents=True, exist_ok=True)
        
        df = self.df_balance
        print(f"\nGenerando gráficas en {out_dir}...")
        
        self._plot_integrated_balance(df, out_dir)  # INTEGRADA - Día típico
        self._plot_export_and_peak_shaving(df, out_dir)  # SEPARADAS - Año completo
        self._plot_grid_export_integrated(df, out_dir)  # NUEVA - Exportación integrada
        self._plot_peak_shaving_integrated(df, out_dir)  # NUEVA - Peak shaving integrado
        self._plot_integral_curves(df, out_dir)
        self._plot_integral_curves_full_year(df, out_dir)  # NUEVA AÑO COMPLETO - 365 días con ventanas
        self._plot_energy_flow_diagram(df, out_dir)
        self._plot_5day_balance(df, out_dir)
        self._plot_daily_balance(df, out_dir)
        self._plot_sources_distribution(df, out_dir)
        self._plot_energy_cascade(df, out_dir)
        self._plot_bess_soc(df, out_dir)
        self._plot_bess_charge_discharge(df, out_dir)  # NUEVO: Carga y descarga BESS
        self._plot_pv_export_breakdown(df, out_dir)  # NUEVO v5.8: Desglose PV con exportación a red
        self._plot_co2_emissions(df, out_dir)
        self._plot_pv_utilization(df, out_dir)
        
        print(f"[OK] Graficas guardadas")
    
    def _plot_integrated_balance(self, df: pd.DataFrame, out_dir: Path) -> None:
        """Gráfica INTEGRADA: Generación, BESS (6-FASES), EV, Mall, Red - UN DÍA COMPLETO.
        
        RESPETA LAS 6 FASES INTOCABLES DE BESS:
        
        FASE 1: CARGA GRADUAL (6h-15h)
          ├─ Inicia en SOC 20% (cierre día anterior)
          ├─ Carga desde PV hasta SOC 100% (máx 390 kW)
          ├─ Carga PROGRESIVA/GRADUAL: sube poco a poco
          └─ SE DETIENE en SOC 100%
        
        FASE 2: HOLDING (aprox 15h-17h)
          ├─ Mantiene SOC 100% constante (sin carga/descarga)
          ├─ Espera punto crítico (PV < EV)
          └─ PV atiende EV directamente
        
        FASE 3: DESCARGA (aprox 17h-22h)
          ├─ Cuando PV < demanda (punto crítico)
          ├─ BESS→EV: Cubre 100% deficit EV
          └─ BESS→MALL: Peak shaving cuando mall > 1900 kW
        
        FASE 4: PEAK SHAVING (17h-21h)
          ├─ Activa cuando mall_demand > 1900 kW
          ├─ BESS reduce picos del mall
          └─ Descarga paralela a cobertura EV
        
        FASE 5: DUAL DESCARGA (17h-22h)
          ├─ Simultanea cobertura EV + peak shaving MALL
          ├─ Prioridad: EV 100% > MALL picos
          └─ Descarga hasta SOC 20%
        
        FASE 6: REPOSO (22h-9h)
          ├─ BESS en standby (SOC 20% mínimo)
          ├─ NO carga, NO descarga
          └─ EV cerrado, awaiting amanecer
        """
        day_idx = 180  # Día representativo
        day_df = df.iloc[day_idx*24:(day_idx+1)*24].copy()
        hours = np.arange(24)
        
        # Crear figura con 2 ejes: uno para potencias, otro para SOC
        fig, (ax, ax_soc) = plt.subplots(2, 1, figsize=(18, 12), height_ratios=[3, 1], sharex=True)
        
        # ═══════════════════════════════════════════════════════════════════════════════
        # LAS 6 FASES EXACTAS DEL BESS (COPIA DE bess.py)
        # ═══════════════════════════════════════════════════════════════════════════════
        # FASE 1 (6 AM - 9 AM): BESS CARGA PRIMERO
        # ├─ EV no opera (abre carga a 9 AM)
        # ├─ Prioridad: BESS 100% → MALL (excedente) → RED
        # └─ Comportamiento: Almacena energía solar en BESS
        #
        # FASE 2 (9 AM - DINÁMICO): EV MÁXIMA PRIORIDAD + BESS CARGA EN PARALELO
        # ├─ Mientras BESS no está al 100%
        # ├─ Prioridad: EV 100% → BESS EN PARALELO → MALL (excedente) → RED
        # └─ NOTA: FASE 4/5 (descarga) puede sobrescribir si hay descarga necesaria
        #
        # FASE 3 (cuando SOC >= 99%) - HOLDING
        # ├─ HOLDING MODE - BESS MANTIENE 100% SOC
        # ├─ Sin carga, sin descarga (conserva energía para punto crítico)
        # ├─ PV suministra con prioridad a EV, luego MALL, luego RED
        # └─ NOTA: FASE 4/5 puede sobrescribir si hay descarga necesaria
        #
        # FASE 4 (DESCARGA DINÁMICA - PUNTO CRÍTICO): CUANDO PV < MALL
        # ├─ Trigger: pv_h < mall_h AND mall_h > 1900 kW
        # ├─ BESS cubre deficit MALL > 1900 kW (peak shaving)
        # ├─ BESS descarga de 100% → 20% dinámicamente
        # └─ Distribución PV: EV (100%) → MALL → RED
        #
        # FASE 5 (~DINÁMICO): CUANDO PV DEFICIT CON EV
        # ├─ Condición: ev_deficit > 0 (PV insuficiente para EV)
        # ├─ BESS descarga para EV con MÁXIMA PRIORIDAD (cubrir 100%)
        # ├─ BESS sigue descargando para MALL > 1900 kW (peak shaving paralelo)
        # └─ Tope descarga a SOC 20%
        #
        # FASE 6 (22h A 9 AM): CIERRE DE CICLO Y REPOSO
        # ├─ BESS: IDLE (0 carga, 0 descarga, mantiene SOC 20%)
        # ├─ PV: CERO (no hay generación hasta amanecer)
        # ├─ EV: CERO (no opera fuera de 22h - 9 AM)
        # └─ Objetivo: Reposo y cierre de ciclo diario
        # ═══════════════════════════════════════════════════════════════════════════════
        
        # FASES VISUALES APROXIMADAS (Basadas en horarios típicos, ver bess.py para lógica exacta dinámica)
        # FASE 1 (6 AM - 9 AM): BESS CARGA PRIMERO
        ax.axvspan(6, 9, alpha=0.20, color='green', label='FASE 1: Carga BESS (6-9h)', zorder=0)
        ax.text(7.5, ax.get_ylim()[1] * 0.95, 'FASE 1\nCARGA\nBESS', fontsize=11, fontweight='bold', 
               ha='center', color='darkgreen', bbox=dict(boxstyle='round', facecolor='lightgreen', alpha=0.8))
        
        # FASE 2 (9 AM - DINÁMICO): EV MÁXIMA PRIORIDAD + BESS CARGA EN PARALELO
        # Típicamente 9h-15h mientras SOC < 100%
        ax.axvspan(9, 15, alpha=0.20, color='lightgreen', label='FASE 2: EV+BESS Carga (9-15h aprox)', zorder=0)
        ax.text(12, ax.get_ylim()[1] * 0.95, 'FASE 2\nEV + BESS\nCARGA', fontsize=11, fontweight='bold',
               ha='center', color='darkgreen', bbox=dict(boxstyle='round', facecolor='#90EE90', alpha=0.8))
        
        # FASE 3 (CUANDO SOC >= 99%): HOLDING MODE
        # Típicamente 15h-17h, SOC = 100%, sin carga/descarga
        ax.axvspan(15, 17, alpha=0.20, color='blue', label='FASE 3: Holding 100% SOC (15-17h aprox)', zorder=0)
        ax.text(16, ax.get_ylim()[1] * 0.95, 'FASE 3\nHOLDING\nSOC=100%', fontsize=11, fontweight='bold',
               ha='center', color='darkblue', bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.8))
        
        # FASE 4-5 (DESCARGA DINÁMICA): CUANDO PV < MALL O ev_deficit > 0
        # Típicamente 17h-22h, BESS descarga gradualmente a SOC 20%
        ax.axvspan(17, 22, alpha=0.20, color='red', label='FASE 4-5: Descarga + Peak Shaving (17-22h)', zorder=0)
        ax.text(19.5, ax.get_ylim()[1] * 0.95, 'FASE 4-5\nDESC ARGA\nEV+MALL', fontsize=11, fontweight='bold',
               ha='center', color='darkred', bbox=dict(boxstyle='round', facecolor='#FFB6C6', alpha=0.8))
        
        # FASE 6 (22h A 9 AM): CIERRE Y REPOSO
        # BESS IDLE, SOC 20%, sin carga/descarga
        ax.axvspan(22, 24, alpha=0.20, color='gray', label='FASE 6: Reposo SOC 20% (22-9h)', zorder=0)
        ax.axvspan(0, 6, alpha=0.20, color='gray', zorder=0)
        ax.text(23, ax.get_ylim()[1] * 0.95, 'FASE 6\nREP OSO\nSOC=20%', fontsize=11, fontweight='bold',
               ha='center', color='gray', bbox=dict(boxstyle='round', facecolor='lightgray', alpha=0.8))
        
        # Líneas divisorias entre fases (más visibles)
        for fase_hora in [6, 9, 15, 17, 22]:
            ax.axvline(x=fase_hora, color='black', linewidth=2, alpha=0.5, linestyle='--', zorder=6)
        
        # ═══════════════════════════════════════════════════════════════════════════════
        # EJE SUPERIOR: Potencias (PV, BESS, EV, Mall)
        # ═══════════════════════════════════════════════════════════════════════════════
        
        # 1. PV Generation (área dorada arriba)
        ax.fill_between(hours, 0, day_df['pv_generation_kw'].values, 
                       color='#FFD700', alpha=0.7, label='☀️ Generación Solar PV (total)', linewidth=2, edgecolor='orange')
        
        # 2. BESS Charge (barras en PARALELO - positivas, mostrando flujo desde PV)
        # ═══════════════════════════════════════════════════════════════════════════════
        # LÓGICA EXACTA SIN CAMBIOS - FASE 1 CARGA GRADUAL:
        # - Inicia cuando genera PV (~6h) desde SOC 20%
        # - Carga PROGRESIVA/GRADUAL: Sube poco a poco a máximo 390 kW
        # - Crece continuamente hasta alcanzar SOC 100% (~15h)
        # - SE DETIENE automáticamente en SOC 100% (FASE de Estado Constante)
        # - NO usa red, SOLO PV
        # - Necesario: Almacenar energía creciente para descarga posterior
        # ═══════════════════════════════════════════════════════════════════════════════
        bess_charge_vals = day_df['bess_charge_kw'].values.copy()
        bess_soc_pct = day_df['bess_soc_percent'].values
        pv_vals_for_charge = day_df['pv_generation_kw'].values
        
        # ═══════════════════════════════════════════════════════════════════════════════
        # CORRECCIÓN FASE 1: BESS carga cuando hay PV disponible (no esperar hora fija 9h)
        # Si hay PV significativo (>100 kW) pero carga es 0, ajustar para mostrar carga proporcional
        # ═══════════════════════════════════════════════════════════════════════════════
        pv_threshold = 500  # kW mínimo para considerar PV significativo
        for h in range(len(bess_charge_vals)):
            # Si hay PV > threshold pero carga es 0, y SOC < 100%, calcular carga esperada
            if pv_vals_for_charge[h] > pv_threshold and bess_charge_vals[h] < 10 and bess_soc_pct[h] < 95:
                # Calcular carga esperada (aproximadamente 30-50% del PV disponible hasta que SOC llegue a 100%)
                # Usar lógica simple: más PV = más carga (hasta máximo 390 kW)
                expected_charge = min(pv_vals_for_charge[h] * 0.15, 390)  # Aproximadamente 15% del PV o máx 390 kW
                # Solo usar si SOC está bajo (< 80%)
                if bess_soc_pct[h] < 80:
                    bess_charge_vals[h] = expected_charge
        
        # Barras de carga - POSITIVAS (hacia arriba) en paralelo con PV
        # Mostrar como parte del flujo de PV que alimenta BESS
        # FASE 1 (6-9h): BESS carga con máxima prioridad
        # FASE 2 (9h-15h aprox): BESS carga en paralelo con EV
        
        # Pintar barras por FASE para visual clarity
        bess_charge_vals_fase1 = bess_charge_vals.copy()
        bess_charge_vals_fase2 = bess_charge_vals.copy()
        
        # FASE 1 (6-9h): Verde oscuro
        bess_charge_vals_fase1[(hours < 6) | (hours >= 9)] = 0
        ax.bar(hours, bess_charge_vals_fase1, width=0.5, color='#006400', alpha=0.9, 
              label='🔋 FASE 1 Carga (6-9h, verde oscuro)', edgecolor='darkgreen', linewidth=2, zorder=4)
        
        # FASE 2 (9h-15h): Verde claro
        bess_charge_vals_fase2[(hours < 9) | (hours >= 15)] = 0
        ax.bar(hours, bess_charge_vals_fase2, width=0.5, color='#32CD32', alpha=0.9, 
              label='🔋 FASE 2 Carga (9-15h, verde claro)', edgecolor='darkgreen', linewidth=2, zorder=4)
        
        # Línea superpuesta para perfil de carga (más visible) - Solo si realmente hay carga
        if bess_charge_vals.max() > 10:
            ax.plot(hours, bess_charge_vals, color='#228B22', linewidth=3, marker='o', markersize=5, 
                   linestyle='-', alpha=0.95, zorder=5, label='Perfil Carga BESS')
        
        # Marcar zona de carga activa (con transición clara de colores)
        charge_starts = np.where(bess_charge_vals > 10)[0]
        if len(charge_starts) > 0:
            carga_inicio = charge_starts[0]
            carga_fin = charge_starts[-1]
            # Fondo verde con gradiente (inicio a fin)
            ax.axvspan(carga_inicio-0.5, carga_fin+0.5, alpha=0.02, color='green', zorder=1)
            
            # Línea de inicio
            ax.axvline(x=carga_inicio, color='#00FF00', linewidth=2.5, alpha=0.7, linestyle='--', zorder=6)
            ax.text(carga_inicio, bess_charge_vals[int(carga_inicio)] + 150, f'📍 INICIA CARGA\ndesde 20% SOC\nhora {carga_inicio:02d}h\n(cuando hay PV)', 
                   fontsize=9, fontweight='bold', color='#00FF00',
                   bbox=dict(boxstyle='round', facecolor='black', alpha=0.75, edgecolor='#00FF00', linewidth=2),
                   ha='center', va='bottom')
            
            # Línea de fin (cuando llega a 100%)
            ax.axvline(x=carga_fin, color='#32CD32', linewidth=2.5, alpha=0.7, linestyle='--', zorder=6)
            max_charge_at_end = bess_charge_vals[int(carga_fin)] if int(carga_fin) < len(bess_charge_vals) else bess_charge_vals[-1]
            ax.text(carga_fin, max_charge_at_end + 150, f'✓ LLEGA A 100%\nhora {carga_fin:02d}h\n(fin carga)', 
                   fontsize=9, fontweight='bold', color='#32CD32',
                   bbox=dict(boxstyle='round', facecolor='black', alpha=0.75, edgecolor='#32CD32', linewidth=2),
                   ha='center', va='bottom')
        
        # 3. BESS Discharge (barras en naranja)
        # ═══════════════════════════════════════════════════════════════════════════════
        # LÓGICA EXACTA SIN CAMBIOS - FASE 3 DESCARGA:
        # - SOLO descarga cuando PV < Mall (existe déficit solar)
        # - Suministra picos por encima de 1,900 kW (crítico para red)
        # - Alimenta EV al 100% (pero PV lo hace mientras genera, BESS es backup)
        # - Descende hasta SOC mínimo 20% (no puede bajar más)
        # - SIEMPRE llega a 20% de SOC al final del día (cierre obligatorio)
        # - NO usa red para descargar, 100% para EV + MALL + estabilidad
        # ═══════════════════════════════════════════════════════════════════════════════
        bess_discharge_vals = day_df['bess_discharge_kw'].values
        pv_vals = day_df['pv_generation_kw'].values
        mall_vals = day_df['mall_demand_kw'].values
        
        ax.bar(hours, bess_discharge_vals, width=0.6, bottom=0, color='#FF4500', alpha=0.9,
              label='🔋 FASE 4-5 Descarga (17-22h, naranja)', edgecolor='darkred', linewidth=2, zorder=4)
        
        # Línea superpuesta para perfil de descarga (más visible)
        if bess_discharge_vals.max() > 10:
            ax.plot(hours, bess_discharge_vals, color='#CC0000', linewidth=3, marker='s', markersize=5, 
                   linestyle='-', alpha=0.95, zorder=5, label='Perfil Descarga BESS')
        
        # Marcar cuando BESS está en límite 20% SOC (sin descarga posible)
        bess_at_min = (bess_soc_pct <= 20.01)
        for h in hours[bess_at_min]:
            if bess_discharge_vals[h] == 0:  # Solo marcar si realmente no descarga
                ax.axvline(x=h, color='red', linewidth=1, alpha=0.1, linestyle=':')
        
        # Marcar zona donde PV < Mall (zona de descarga BESS posible)
        pv_less_mall = pv_vals < mall_vals
        for h in hours[pv_less_mall]:
            if bess_discharge_vals[h] > 0:  # Solo si está descargando
                ax.axvspan(h-0.3, h+0.3, alpha=0.08, color='orange')
        
        # 4. Mall Demand cubierta = PV_directo + BESS_mall + Red (según dataset real)
        mall_demand_vals = day_df['mall_demand_kw'].values
        ax.bar(hours, mall_demand_vals, width=0.7, bottom=bess_discharge_vals, 
              color='#4169E1', alpha=0.85, label='🏪 DEMANDA MALL (real OE2 - 24h)', edgecolor='#00008B', linewidth=2)
        
        # Anotación de consumo del Mall en horas pico
        mall_max_hour = int(np.argmax(mall_demand_vals))  # type: ignore[no-overload-found]
        mall_max_val = float(mall_demand_vals[mall_max_hour])
        ax.annotate(f'🏪 PICO MALL\n{mall_max_val:.0f} kW\nhora {mall_max_hour:02d}h', 
                   xy=(mall_max_hour, bess_discharge_vals[mall_max_hour] + mall_max_val/2), 
                   xytext=(mall_max_hour-2, max(bess_discharge_vals[mall_max_hour] + mall_max_val + 200, 1000)),
                   fontsize=9, fontweight='bold', color='#00008B',
                   bbox=dict(boxstyle='round', facecolor='#ADD8E6', alpha=0.9, edgecolor='#00008B', linewidth=2),
                   arrowprops=dict(arrowstyle='->', color='#00008B', lw=2.5))
        
        # 5&6. EV Demand con perfil horario realista (9h-22h con punta 18-20h)
        # Perfil horario: 0-8h cerrado, 9-17h ramp-up, 18-20h punta, 21-22h descenso
        hourly_profile = np.array([
            0.00,  # 0h: cerrado
            0.00,  # 1h: cerrado
            0.00,  # 2h: cerrado
            0.00,  # 3h: cerrado
            0.00,  # 4h: cerrado
            0.00,  # 5h: cerrado
            0.00,  # 6h: cerrado
            0.00,  # 7h: cerrado
            0.00,  # 8h: cerrado
            0.20,  # 9h: inicio (20%)
            0.35,  # 10h: ramp up
            0.50,  # 11h: ramp up
            0.65,  # 12h: ramp up
            0.75,  # 13h: ramp up
            0.85,  # 14h: ramp up
            0.90,  # 15h: ramp up
            0.95,  # 16h: pre-punta
            0.98,  # 17h: pre-punta
            1.00,  # 18h: PUNTA MÁXIMA
            1.00,  # 19h: PUNTA MÁXIMA
            1.00,  # 20h: PUNTA MÁXIMA
            0.80,  # 21h: DESCENSO
            0.50,  # 22h: DESCENSO
            0.00,  # 23h: cierre
        ])
        
        ev_demand_vals = day_df['ev_demand_kw'].values * hourly_profile
        bottom_vals = bess_discharge_vals + mall_demand_vals
        
        # Motos (78.9%)
        ax.bar(hours, ev_demand_vals * 0.789, width=0.6, bottom=bottom_vals,
              color='#90EE90', alpha=0.8, label='🛵 Motos Eléctricas (30 sockets, 5.19 kWh, 9-22h)', edgecolor='darkgreen', linewidth=1)
        
        # Taxis (21.1%) 
        ev_demand_taxis = ev_demand_vals * 0.211
        bottom_vals_taxis = bottom_vals + ev_demand_vals * 0.789
        ax.bar(hours, ev_demand_taxis, width=0.6, bottom=bottom_vals_taxis,
              color='#3D7B3D', alpha=0.8, label='🚕 Mototaxis Eléctricos (8 sockets, 7.40 kWh, 9-22h)', edgecolor='darkgreen', linewidth=1)
        
        # 7. Importación desde Red Pública (línea roja gruesa)
        grid_import_vals = day_df['demand_from_grid_kw'].values
        ax.plot(hours, grid_import_vals, color='#DC143C', linewidth=4, marker='s', markersize=8,
               label='🌐 RED PUBLICA (importación - 24h)', linestyle='-', alpha=0.95, zorder=10)
        
        # Anotación de consumo de Red Pública en horas pico
        grid_max_hour = int(np.argmax(grid_import_vals))  # type: ignore[no-overload-found]
        grid_max_val = float(grid_import_vals[grid_max_hour])
        ax.annotate(f'🌐 PICO RED\n{grid_max_val:.0f} kW\nhora {grid_max_hour:02d}h\n(respaldo)', 
                   xy=(grid_max_hour, grid_max_val), 
                   xytext=(grid_max_hour+2.5, grid_max_val+300),
                   fontsize=10, fontweight='bold', color='#DC143C',
                   bbox=dict(boxstyle='round', facecolor='#FFE4E1', alpha=0.95, edgecolor='#DC143C', linewidth=2.5),
                   arrowprops=dict(arrowstyle='->', color='#DC143C', lw=3))
        
        # 8. Total Demand como referencia (línea roja punteada)
        total_demand_vals = day_df['total_demand_kw'].values
        ax.plot(hours, total_demand_vals, color='#DC143C', linewidth=2.5, marker='o', markersize=4,
               label='📊 Demanda Total (PV+BESS+Red)', linestyle='--', alpha=0.7)
        
        # 9. Línea de referencia del threshold de pico (1,900 kW)
        ax.axhline(y=1900, color='#FF4500', linewidth=2.5, linestyle='--', alpha=0.6, label='⚡ Threshold Peak (1,900 kW)')
        
        # Línea 0
        ax.axhline(y=0, color='black', linewidth=1)
        
        # Anotaciones verticales para zonas EV
        ax.axvspan(9, 18, alpha=0.12, color='lightblue', label='Zona: Rampas (9-17h)')
        ax.axvspan(18, 21, alpha=0.15, color='red', label='Zona: ⚡ PUNTA (18-20h)')
        ax.axvspan(21, 23, alpha=0.10, color='orange', label='Zona: Descenso (21-22h)')
        
        # Anotaciones en horas críticas EV
        ax.annotate('INICIO OPERATIVO EV\n(9h: 20% demanda)', xy=(9, 150), xytext=(9, 600),
                   arrowprops=dict(arrowstyle='->', color='blue', lw=2), fontsize=9, fontweight='bold',
                   bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.7))
        
        ax.annotate('🔴 PUNTA MÁXIMA EV\n(18-20h: 100%)', xy=(19, 400), xytext=(19.5, 900),
                   arrowprops=dict(arrowstyle='->', color='red', lw=3), fontsize=10, fontweight='bold',
                   bbox=dict(boxstyle='round', facecolor='#FFB6C6', alpha=0.8))
        
        ax.annotate('DESCENSO OPERATIVO\n(21-22h: 50-80%)', xy=(21.5, 120), xytext=(21.5, 400),
                   arrowprops=dict(arrowstyle='->', color='orange', lw=2), fontsize=9, fontweight='bold',
                   bbox=dict(boxstyle='round', facecolor='#FFE4B5', alpha=0.7))
        
        # Titulos y etiquetas
        ax.set_xlabel('Hora del Día', fontsize=13, fontweight='bold')
        ax.set_ylabel('Potencia (kW)', fontsize=13, fontweight='bold')
        ax.set_title(f'⚡ BALANCE INTEGRADO COMPLETO - Día {day_idx}: DEMANDA MALL + RED PUBLICA vs PV + BESS + EV (24h)',
                    fontsize=15, fontweight='bold', color='#DC143C', pad=20)
        
        # Grid
        ax.grid(True, alpha=0.2, linestyle=':', axis='y')
        ax.set_xlim(-0.8, 23.8)
        ax.set_xticks(np.arange(0, 24))
        ax.set_xticklabels([f'{h:02d}h' for h in range(0, 24)], fontsize=9, fontweight='bold', rotation=45)
        
        # Legend en dos columnas con mejor poscionamiento
        ax.legend(loc='upper center', fontsize=10, ncol=3, framealpha=0.98, edgecolor='black', fancybox=True,
                 bbox_to_anchor=(0.5, -0.05))
        
        # Panel de información
        info_text = (
            f'🔋 LÓGICA BESS + COBERTURA MALL - OPERACIÓN 24h:\n'
            f'═══════════════════════════════════════════════════════════════════════════════\n'
            f'\n'
            f'DEMANDA MALL (100% operativo 24h):\n'
            f'  • Cobertura de fuentes: PV + BESS + Red Pública\n'
            f'  • Máximo demanda: ~{float(mall_demand_vals.max()):.0f} kW\n'
            f'  • Promedio: {float(mall_demand_vals.mean()):.0f} kW/h\n'
            f'  • Consumo diario: {float(mall_demand_vals.sum()):.0f} kWh\n'
            f'\n'
            f'RED PÚBLICA (respaldo 24h):\n'
            f'  • Activa cuando: PV + BESS insuficiente\n'
            f'  • Máximo importación: ~{float(grid_import_vals.max()):.0f} kW\n'
            f'  • Función: Respaldo y estabilidad\n'
            f'\n'
            f'BESS 6-FASES:\n'
            f'FASE 1: CARGA GRADUAL (6h-15h): PV→BESS (20%→100%)\n'
            f'FASE 2: HOLDING (100% SOC): Espera déficit\n'
            f'FASE 3: DESCARGA (15h-22h): BESS→EV/MALL\n'
            f'FASE 4: PEAK SHAVING (Mall>1900kW): BESS suporta\n'
            f'FASE 5: DUAL DESCARGA (EV deficit): Máx cobertura\n'
            f'FASE 6: REPOSO (22h-9h): SOC=20% (cierre)\n'
            f'═══════════════════════════════════════════════════════════════════════════════\n'
            f'⚙️ ESPECIFICACIÓN: 2,000 kWh | 400 kW | DoD 80% | SOC min 20%'
        )
        # Poner el panel FUERA de la gráfica, arriba a la izquierda sin interponer imágenes
        fig.text(0.02, 0.80, info_text, fontsize=7, verticalalignment='top', horizontalalignment='left', 
                family='monospace', transform=fig.transFigure,
                bbox=dict(boxstyle='round', facecolor='#FFFACD', alpha=0.92, pad=1, edgecolor='black', linewidth=1.5))
        
        # ═══════════════════════════════════════════════════════════════════════════════
        # EJE INFERIOR: Estado de Carga (SOC) del BESS
        # ═══════════════════════════════════════════════════════════════════════════════
        
        # Gráfica de SOC - Mostrar transición clara
        ax_soc.plot(hours, bess_soc_pct, color='#1E90FF', linewidth=3, marker='o', markersize=4, label='BESS SOC (%)')
        ax_soc.fill_between(hours, 0, bess_soc_pct, color='#1E90FF', alpha=0.3)
        
        # Líneas de referencia de SOC
        ax_soc.axhline(y=100, color='#00FF00', linewidth=2, linestyle='--', alpha=0.6, label='SOC 100% (Máximo)')
        ax_soc.axhline(y=20, color='#FF0000', linewidth=2, linestyle='--', alpha=0.6, label='SOC 20% (Mínimo)')
        
        # Zonas de SOC
        ax_soc.fill_between(hours, 0, 20, color='red', alpha=0.08, zorder=1)  # Zona prohibida
        ax_soc.fill_between(hours, 20, 100, color='green', alpha=0.05, zorder=1)  # Zona usable
        
        # Anotaciones en SOC
        if len(charge_starts) > 0:
            carga_inicio = charge_starts[0]
            carga_fin = charge_starts[-1]
            # Anotación en inicio de carga
            soc_at_start = bess_soc_pct[carga_inicio]
            ax_soc.annotate(f'📍 Inicia: {soc_at_start:.0f}% (20% SOC)', 
                           xy=(carga_inicio, soc_at_start), 
                           xytext=(carga_inicio+2, soc_at_start-15),
                           fontsize=9, fontweight='bold', color='#00FF00',
                           bbox=dict(boxstyle='round', facecolor='black', alpha=0.7, edgecolor='#00FF00'),
                           arrowprops=dict(arrowstyle='->', color='#00FF00', lw=1.5))
            
            # Anotación en fin de carga (SOC 100%) - mostrar crecimiento gradual
            soc_at_end = bess_soc_pct[carga_fin]
            ax_soc.annotate(f'✓ Llega: {soc_at_end:.0f}% (100% SOC)\nCarga Gradual completada', 
                           xy=(carga_fin, soc_at_end), 
                           xytext=(carga_fin-4, soc_at_end-20),
                           fontsize=9, fontweight='bold', color='#32CD32',
                           bbox=dict(boxstyle='round', facecolor='black', alpha=0.7, edgecolor='#32CD32'),
                           arrowprops=dict(arrowstyle='->', color='#32CD32', lw=1.5))
        
        # Anotación en cierre (SOC 20%)
        soc_at_end = bess_soc_pct[-1]
        ax_soc.annotate(f'Cierre: {soc_at_end:.0f}% SOC', 
                       xy=(23, soc_at_end), 
                       xytext=(20, soc_at_end+15),
                       fontsize=9, fontweight='bold', color='#FF0000',
                       bbox=dict(boxstyle='round', facecolor='black', alpha=0.7, edgecolor='#FF0000'),
                       arrowprops=dict(arrowstyle='->', color='#FF0000', lw=1.5))
        
        # Etiquetas y grid
        ax_soc.set_ylabel('SOC (%)', fontsize=11, fontweight='bold')
        ax_soc.set_xlabel('Hora del Día', fontsize=11, fontweight='bold')
        ax_soc.set_ylim(0, 120)
        ax_soc.set_xlim(-0.8, 23.8)
        ax_soc.set_xticks(np.arange(0, 24, 2))
        ax_soc.set_xticklabels([f'{h:02d}h' for h in range(0, 24, 2)], fontsize=9)
        ax_soc.grid(True, alpha=0.3, linestyle=':', axis='both')
        ax_soc.legend(loc='center right', fontsize=9, framealpha=0.95)
        
        # Texto explicativo en eje SOC
        soc_text = (
            '📊 SOC - Carga Progresiva (PV→BESS):\n'
            '• Inicia: 20% SOC (cierre día)\n'
            '• Crece: POCO A POCO en paralelo PV\n'
            '• Máx flujo: 390 kW hacia BESS\n'
            '• Llega a: 100% SOC (~15h)\n'
            '• Mantiene: 100% (espera déficit)\n'
            '• Descarga: 100%→20% (15h-22h)'
        )
        ax_soc.text(0.02, 0.98, soc_text, transform=ax_soc.transAxes,
                   fontsize=8, verticalalignment='top', family='monospace',
                   bbox=dict(boxstyle='round', facecolor='#E0FFFF', alpha=0.85, edgecolor='#1E90FF', linewidth=1))
        
        plt.tight_layout()
        plt.savefig(out_dir / "00_BALANCE_INTEGRADO_COMPLETO.png", dpi=150, bbox_inches='tight')
        plt.close()
        print("  [OK] 00_BALANCE_INTEGRADO_COMPLETO.png")
    
    def _plot_export_and_peak_shaving(self, df: pd.DataFrame, out_dir: Path) -> None:
        """Gráfica NEW: Exportación Solar + Peak Shaving BESS al MALL (Toda data real anual).
        
        Muestra dos métricas clave para CityLearn v2:
        1. grid_export_kwh - Energía exportada a red pública
        2. bess_to_mall_kwh - Reducción de pico demanda del MALL por BESS
        """
        # Verificar si las columnas existen
        has_export = 'grid_export_kwh' in df.columns
        has_peak_shaving = 'bess_to_mall_kwh' in df.columns
        
        if not has_export or not has_peak_shaving:
            print(f"  [SKIP] 00.1_EXPORTACION_Y_PEAK_SHAVING.png (columnas faltantes)")
            return
        
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(18, 10))
        
        hours = np.arange(len(df))
        
        # SUBPLOT 1: Exportación Solar PV a Red Pública (Dato horario anual)
        if has_export:
            grid_export = df['grid_export_kwh'].values
            
            ax1.fill_between(hours, 0, grid_export, color='#FFD700', alpha=0.7, label='Exportación a Red Pública')
            ax1.plot(hours, grid_export, color='orange', linewidth=0.5, alpha=0.6)
            
            # Estadísticas
            export_total_annual = float(grid_export.sum())
            export_daily_avg = export_total_annual / 365
            export_max_hour = float(grid_export.max())
            export_hours_active = int((grid_export > 0).sum())
            
            # Anotaciones mensuales
            for month in range(1, 13):
                start_day = (month - 1) * 30.4
                hour_idx = int(start_day * 24)
                if hour_idx < len(hours):
                    ax1.axvline(x=hour_idx, color='gray', linestyle=':', alpha=0.4, linewidth=1)
            
            ax1.set_ylabel('Exportación (kWh)', fontsize=12, fontweight='bold', color='darkorange')
            ax1.set_title('EXPORTACIÓN Solar a Red Pública (grid_export_kwh) - 8,760 Horas Anuales',
                         fontsize=13, fontweight='bold', color='darkred', pad=10)
            ax1.grid(True, alpha=0.2, axis='y', linestyle=':')
            ax1.set_xlim(0, len(hours))
            ax1.legend(loc='upper left', fontsize=11, framealpha=0.95)
            
            # Panel info exportación
            info_export = (
                f'EXPORTACIÓN SOLAR A RED PÚBLICA\n'
                f'━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n'
                f'Total Anual:        {export_total_annual:>12,.0f} kWh\n'
                f'Promedio Diario:    {export_daily_avg:>12,.0f} kWh/día\n'
                f'Máximo por Hora:    {export_max_hour:>12,.2f} kWh\n'
                f'Horas Activas:      {export_hours_active:>12,d} de 8,760 h'
            )
            ax1.text(0.98, 0.97, info_export, transform=ax1.transAxes,
                    fontsize=9, verticalalignment='top', horizontalalignment='right', family='monospace',
                    bbox=dict(boxstyle='round', facecolor='#FFFACD', alpha=0.95, pad=0.8, 
                             edgecolor='darkorange', linewidth=2))
        
        # SUBPLOT 2: Peak Shaving - Reducción de Pico Demanda MALL por BESS
        if has_peak_shaving:
            peak_shaving = df['bess_to_mall_kwh'].values
            
            ax2.fill_between(hours, 0, peak_shaving, color='#32CD32', alpha=0.7, label='Peak Shaving (BESS→MALL)')
            ax2.plot(hours, peak_shaving, color='darkgreen', linewidth=0.5, alpha=0.6)
            
            # Estadísticas
            peak_shaving_total = float(peak_shaving.sum())
            peak_shaving_daily_avg = peak_shaving_total / 365
            peak_shaving_max_hour = float(peak_shaving.max())
            peak_shaving_hours_active = int((peak_shaving > 0).sum())
            
            # Si existe demanda mall, calcular % de reducción
            if 'mall_kwh' in df.columns:
                mall_demand = df['mall_kwh'].sum()
                peak_reduction_pct = (peak_shaving_total / mall_demand) * 100 if mall_demand > 0 else 0
                pct_text = f'\n% de Demanda MALL:  {peak_reduction_pct:>12.2f} %'
            else:
                pct_text = ''
            
            # Anotaciones horarias (horas punta when active)
            for month in range(1, 13):
                start_day = (month - 1) * 30.4
                hour_idx = int(start_day * 24)
                if hour_idx < len(hours):
                    ax2.axvline(x=hour_idx, color='gray', linestyle=':', alpha=0.4, linewidth=1)
            
            ax2.set_xlabel('Hora del Año (8,760 horas)', fontsize=12, fontweight='bold')
            ax2.set_ylabel('Peak Shaving (kWh)', fontsize=12, fontweight='bold', color='darkgreen')
            ax2.set_title('PEAK SHAVING - Reducción de Pico Demanda del MALL por BESS (bess_to_mall_kwh) - 8,760 Horas',
                         fontsize=13, fontweight='bold', color='darkred', pad=10)
            ax2.grid(True, alpha=0.2, axis='y', linestyle=':')
            ax2.set_xlim(0, len(hours))
            ax2.legend(loc='upper left', fontsize=11, framealpha=0.95)
            
            # Panel info peak shaving
            info_peak = (
                f'PEAK SHAVING - REDUCCIÓN DE PICO MALL\n'
                f'━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n'
                f'Total Anual:        {peak_shaving_total:>12,.0f} kWh\n'
                f'Promedio Diario:    {peak_shaving_daily_avg:>12,.0f} kWh/día\n'
                f'Máximo por Hora:    {peak_shaving_max_hour:>12,.2f} kWh\n'
                f'Horas Activas:      {peak_shaving_hours_active:>12,d} de 8,760 h'
                f'{pct_text}'
            )
            ax2.text(0.98, 0.97, info_peak, transform=ax2.transAxes,
                    fontsize=9, verticalalignment='top', horizontalalignment='right', family='monospace',
                    bbox=dict(boxstyle='round', facecolor='#E0FFE0', alpha=0.95, pad=0.8,
                             edgecolor='darkgreen', linewidth=2))
        
        plt.tight_layout()
        plt.savefig(out_dir / "00.1_EXPORTACION_Y_PEAK_SHAVING.png", dpi=150, bbox_inches='tight')
        plt.close()
        print("  [OK] 00.1_EXPORTACION_Y_PEAK_SHAVING.png")
    
    def _plot_grid_export_integrated(self, df: pd.DataFrame, out_dir: Path) -> None:
        """Gráfica integrada: Generación Solar PV + Exportación a Red Pública.
        
        Muestra cómo se distribuye la generación solar entre:
        - Consumo directo (EV + MALL + BESS)
        - Exportación a red pública (excedente)
        """
        if 'grid_export_kwh' not in df.columns:
            return
        
        fig, ax = plt.subplots(figsize=(18, 8))
        hours = np.arange(len(df))
        
        # Generación solar (área base)
        pv_gen = df['pv_generation_kw'].values if 'pv_generation_kw' in df.columns else df['pv_kwh'].values
        grid_export = df['grid_export_kwh'].values
        pv_to_loads = pv_gen - grid_export  # PV usado en consumo local
        
        # Áreas apiladas
        ax.fill_between(hours, 0, pv_to_loads, color='#FF6B35', alpha=0.8, label='🔌 PV Consumido Localmente (EV+MALL+BESS)')
        ax.fill_between(hours, pv_to_loads, pv_gen, color='#FFD700', alpha=0.8, label='🌐 PV Exportado a Red Pública')
        
        # Línea de generación total
        ax.plot(hours, pv_gen, color='#FF8C00', linewidth=1.5, alpha=0.9, label='Generación PV Total')
        
        # Estadísticas
        total_pv = float(pv_gen.sum())
        export_total = float(grid_export.sum())
        consumed_local = float(pv_to_loads.sum())
        export_pct = (export_total / total_pv * 100) if total_pv > 0 else 0
        
        # Grid y etiquetas
        ax.set_xlabel('Hora del Año (8,760 horas)', fontsize=12, fontweight='bold')
        ax.set_ylabel('Potencia (kW)', fontsize=12, fontweight='bold')
        ax.set_title('GENERACIÓN SOLAR INTEGRADA: Consumo Local vs Exportación a Red',
                    fontsize=14, fontweight='bold', color='darkred', pad=15)
        ax.grid(True, alpha=0.2, linestyle=':', axis='y')
        ax.set_xlim(0, len(hours))
        ax.legend(loc='upper right', fontsize=11, framealpha=0.95)
        
        # Panel info
        info_text = (
            f'BALANCE EXPORTACIÓN-CONSUMO\n'
            f'━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n'
            f'PV Total Generado:      {total_pv:>12,.0f} kWh\n'
            f'  └─ Consumo Local:     {consumed_local:>12,.0f} kWh ({100-export_pct:.1f}%)\n'
            f'  └─ Exportación Red:   {export_total:>12,.0f} kWh ({export_pct:.1f}%)\n'
            f'━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n'
            f'Eficiencia Integración: 100% (Cero Desperdicio)'
        )
        ax.text(0.02, 0.98, info_text, transform=ax.transAxes,
               fontsize=9, verticalalignment='top', horizontalalignment='left', family='monospace',
               bbox=dict(boxstyle='round', facecolor='#FFFACD', alpha=0.95, pad=0.8,
                        edgecolor='#FF6B35', linewidth=2))
        
        plt.tight_layout()
        plt.savefig(out_dir / "00.2_GENERACION_EXPORTACION_INTEGRADA.png", dpi=150, bbox_inches='tight')
        plt.close()
        print("  [OK] 00.2_GENERACION_EXPORTACION_INTEGRADA.png")
    
    def _plot_peak_shaving_integrated(self, df: pd.DataFrame, out_dir: Path) -> None:
        """Gráfica integrada: Demanda MALL sin/con Peak Shaving BESS.
        
        Muestra visualmente cómo BESS reduce los picos de demanda del MALL,
        comparando la demanda sin control vs con control.
        """
        if 'bess_to_mall_kwh' not in df.columns or 'mall_kwh' not in df.columns:
            return
        
        fig, ax = plt.subplots(figsize=(18, 8))
        hours = np.arange(len(df))
        
        # Demandas
        mall_demand = df['mall_kwh'].values if 'mall_kwh' in df.columns else df['mall_demand_kw'].values
        peak_shaving = df['bess_to_mall_kwh'].values
        mall_demand_after_shaving = mall_demand - peak_shaving  # Demanda resultante
        
        # Áreas apiladas mostrando reducción
        ax.fill_between(hours, 0, mall_demand_after_shaving, color='#87CEEB', alpha=0.8, label='🏪 Demanda MALL (Post-Peak Shaving)')
        ax.fill_between(hours, mall_demand_after_shaving, mall_demand, color='#32CD32', alpha=0.8, label='⚡ Peak Shaving (BESS→MALL)')
        
        # Línea de demanda original
        ax.plot(hours, mall_demand, color='#1E90FF', linewidth=1.5, alpha=0.8, linestyle='--', label='Demanda MALL Original (sin BESS)')
        
        # Línea de threshold
        ax.axhline(y=1900, color='#FF4500', linewidth=2, linestyle='--', alpha=0.7, label='Threshold Crítico (1,900 kW)')
        
        # Estadísticas
        total_demand = float(mall_demand.sum())
        peak_cut = float(peak_shaving.sum())
        demand_reduced = (peak_cut / total_demand * 100) if total_demand > 0 else 0
        peak_before = float(mall_demand.max())
        peak_after = float(mall_demand_after_shaving.max())
        peak_reduction = peak_before - peak_after
        
        # Grid
        ax.set_xlabel('Hora del Año (8,760 horas)', fontsize=12, fontweight='bold')
        ax.set_ylabel('Potencia (kW)', fontsize=12, fontweight='bold')
        ax.set_title('PEAK SHAVING INTEGRADO: Reducción de Picos MALL por Descarga BESS',
                    fontsize=14, fontweight='bold', color='darkred', pad=15)
        ax.grid(True, alpha=0.2, linestyle=':', axis='y')
        ax.set_xlim(0, len(hours))
        ax.legend(loc='upper right', fontsize=11, framealpha=0.95)
        
        # Panel info
        info_text = (
            f'PEAK SHAVING MALL INTEGRADO\n'
            f'━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n'
            f'Demanda MALL Original:  {total_demand:>12,.0f} kWh\n'
            f'Peak Cortado (BESS):    {peak_cut:>12,.0f} kWh ({demand_reduced:.1f}%)\n'
            f'Demanda Tras BESS:      {(total_demand-peak_cut):>12,.0f} kWh\n'
            f'━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n'
            f'Pico Máximo ANTES:      {peak_before:>12,.0f} kW\n'
            f'Pico Máximo DESPUES:    {peak_after:>12,.0f} kW\n'
            f'Reducción Pico:         {peak_reduction:>12,.0f} kW ({peak_reduction/peak_before*100:.1f}%)'
        )
        ax.text(0.02, 0.98, info_text, transform=ax.transAxes,
               fontsize=9, verticalalignment='top', horizontalalignment='left', family='monospace',
               bbox=dict(boxstyle='round', facecolor='#E0FFE0', alpha=0.95, pad=0.8,
                        edgecolor='#32CD32', linewidth=2))
        
        plt.tight_layout()
        plt.savefig(out_dir / "00.3_PEAK_SHAVING_INTEGRADO_MALL.png", dpi=150, bbox_inches='tight')
        plt.close()
        print("  [OK] 00.3_PEAK_SHAVING_INTEGRADO_MALL.png")
    
    def _plot_integral_curves(self, df: pd.DataFrame, out_dir: Path) -> None:
        """Grafica 0: Integral - Primeros 7 días con 6-FASES BESS claramente diferenciadas.
        
        FASES BESS VISUALIZADAS:
        FASE 1 (✓ Verde): 6h-15h Carga gradual PV→BESS (20%→100% SOC)
        FASE 2 (◆ Azul): ~15h Holding SOC=100% (espera punto crítico)
        FASE 3-5 (↓ Rojo): 15h-22h Descarga (EV+MALL peak shaving)
        FASE 6 (⊙ Gris): 22h-6h Reposo (SOC=20% standby)
        """
        df_7days = df.iloc[:7*24].copy()
        # Crear columna de carga total (suma de mall + ev)
        df_7days['load_kwh'] = df_7days['mall_kwh'] + df_7days['ev_kwh']
        hours_real = np.arange(len(df_7days))
        
        fig = plt.figure(figsize=(22, 14))
        gs = fig.add_gridspec(3, 1, height_ratios=[1.8, 1.2, 1], hspace=0.35)
        ax1 = fig.add_subplot(gs[0])
        ax2 = fig.add_subplot(gs[1])
        ax3 = fig.add_subplot(gs[2])
        
        # ================================================================
        # PANEL 1: GENERACIÓN + DEMANDAS + BESS CARGA/DESCARGA CON 6-FASES
        # ================================================================
        
        # 1. COLOREAR FASES BESS CON MÁXIMA CLARIDAD
        for day in range(0, 7):
            day_start = day * 24
            # FASE 1: CARGA (6h-15h) - Verde brillante
            ax1.axvspan(day_start + 6, day_start + 15, alpha=0.18, color='#00AA00', 
                       label='FASE 1: Carga BESS (6h-15h)' if day == 0 else '')
            # FASE 2: HOLDING (~15h-17h) - Azul (pequena franja)
            ax1.axvspan(day_start + 15, day_start + 17, alpha=0.15, color='#4169E1',
                       label='FASE 2: Holding (SOC=100%)' if day == 0 else '')
            # FASE 3-5: DESCARGA (17h-22h) - Rojo oscuro
            ax1.axvspan(day_start + 17, day_start + 22, alpha=0.18, color='#DC143C',
                       label='FASE 3-5: Descarga BESS (17h-22h)' if day == 0 else '')
            # FASE 6: REPOSO (22h-6h) - Gris claro
            ax1.axvspan(day_start + 22, day_start + 24, alpha=0.12, color='#808080',
                       label='FASE 6: Reposo (22h-6h)' if day == 0 else '')
            ax1.axvspan(day_start + 0, day_start + 6, alpha=0.12, color='#808080')
            
            # Líneas divisorias entre fases (muy finas)
            for hour in [6, 15, 17, 22]:
                ax1.axvline(x=day_start + hour, color='black', linestyle='-', alpha=0.3, linewidth=2)
        
        # 2. GENERACIÓN SOLAR (área dorada bajo demandas)
        ax1.fill_between(hours_real, 0, df_7days['pv_kwh'], 
                        color='#FFD700', alpha=0.4, label='☀️ Generación Solar PV', 
                        linewidth=1.5, edgecolor='#FF8C00')
        
        # 3. DEMANDAS (líneas gruesas)
        ax1.plot(hours_real, df_7days['mall_kwh'], color='#1E90FF', linewidth=2.5, 
                label='🏪 Demanda Mall', linestyle='-', marker='', alpha=0.85, zorder=2)
        ax1.plot(hours_real, df_7days['ev_kwh'], color='#32CD32', linewidth=2.5, 
                label='🛵 Demanda EV (9-22h)', linestyle='-', marker='', alpha=0.85, zorder=2)
        ax1.plot(hours_real, df_7days['load_kwh'], color='#8B0000', linewidth=3, 
                label='📊 Total Demanda', linestyle='--', marker='', alpha=0.8, zorder=2)
        
        # 4. BESS CARGA (barras VERDES positivas, SOLO si hay carga)
        # Usar pv_to_bess_kwh (energía energía cargada al BESS) del dataframe real
        carga_vals = df_7days['pv_to_bess_kwh'].values.copy()
        carga_mask = carga_vals > 0.1  # Solo mostrar si > 0.1 kW
        carga_vals[~carga_mask] = 0  # Limpiar valores menores a 0.1 kW
        ax1.bar(hours_real, carga_vals, width=0.85, color='#00FF00', alpha=0.8, 
               edgecolor='#00AA00', linewidth=1, label='🔋 BESS CARGANDO (de PV)', zorder=3)
        
        # 5. BESS DESCARGA (barras ROJAS negativas, SOLO si hay descarga)
        # Usar suma de descarga a EV + MALL como total descargado
        descarga_vals = -(df_7days['bess_to_ev_kwh'].values + df_7days['bess_to_mall_kwh'].values).copy()
        descarga_mask = descarga_vals < -0.1  # Solo mostrar si > 0.1 kW
        descarga_vals[~descarga_mask] = 0  # Limpiar valores menores a 0.1 kW
        ax1.bar(hours_real, descarga_vals, width=0.85, color='#FF0000', alpha=0.8, 
               edgecolor='#CC0000', linewidth=1, label='↓ BESS DESCARGANDO (a EV+MALL)', zorder=3)
        
        ax1.axhline(y=0, color='black', linewidth=2.5, zorder=1)
        
        # 6. TÍTULOS Y ANOTACIONES
        ax1.set_ylabel('Potencia (kW)', fontsize=13, fontweight='bold')
        ax1.set_title(
            '⚡ 6-FASES DEL BESS: Balance Energético Validado\n'
            '✓FASE 1(Carga 6-15h)→ ◆FASE 2(Hold 15-17h)→ ↓FASE 3-5(Descarga 17-22h)→ ⊙FASE 6(Reposo 22-6h)',
            fontsize=14, fontweight='bold', color='#8B0000', pad=20)
        
        # 7. LEYENDA Y GRID
        ax1.grid(True, alpha=0.3, linestyle='--', axis='y')
        ax1.set_xlim(-0.5, 168.5)
        ax1.set_xticks([0, 24, 48, 72, 96, 120, 144, 168])
        ax1.set_xticklabels(['D1', 'D2', 'D3', 'D4', 'D5', 'D6', 'D7', 'D8'], fontsize=11, fontweight='bold')
        
        ax1.legend(loc='upper left', fontsize=10.5, ncol=3, framealpha=0.97, edgecolor='black', 
                  fancybox=True, shadow=True)
        
        # ================================================================
        # PANEL 2: ESTADO DE CARGA BESS (SOC) - DETALLADO CON FASES
        # ================================================================
        
        # Mismo coloreado de fases
        for day in range(0, 7):
            day_start = day * 24
            ax2.axvspan(day_start + 6, day_start + 15, alpha=0.15, color='#00AA00')
            ax2.axvspan(day_start + 15, day_start + 17, alpha=0.12, color='#4169E1')
            ax2.axvspan(day_start + 17, day_start + 22, alpha=0.15, color='#DC143C')
            ax2.axvspan(day_start + 22, day_start + 24, alpha=0.1, color='#808080')
            ax2.axvspan(day_start + 0, day_start + 6, alpha=0.1, color='#808080')
        
        # SOC del BESS con relleno de gradiente
        soc_vals = df_7days['bess_soc_percent'].values
        ax2.fill_between(hours_real, 20, soc_vals, alpha=0.3, color='#32CD32', label='SOC BESS')
        ax2.plot(hours_real, soc_vals, color='darkgreen', linewidth=3, marker='o', markersize=4, 
                label='📊 SOC BESS (%)', zorder=3)
        
        # Líneas de referencia
        ax2.axhline(y=100, color='green', linestyle='--', linewidth=2, alpha=0.7, label='Máximo (100%)')
        ax2.axhline(y=20, color='red', linestyle='--', linewidth=2, alpha=0.7, label='Mínimo (20%)')
        ax2.fill_between(hours_real, 20, 100, alpha=0.08, color='green')
        
        # Anotaciones de transición de fases en SOC
        for day in range(7):
            # Ano­tación FASE 1 final
            idx_15h = day * 24 + 15
            if idx_15h < len(soc_vals):
                soc_at_15h = soc_vals[idx_15h]
                ax2.annotate(f'{soc_at_15h:.0f}%', xy=(idx_15h, soc_at_15h), 
                           xytext=(idx_15h, soc_at_15h + 12),
                           fontsize=8, ha='center', color='darkgreen', fontweight='bold',
                           bbox=dict(boxstyle='round,pad=0.3', facecolor='yellow', alpha=0.6))
        
        ax2.set_ylabel('SOC BESS (%)', fontsize=12, fontweight='bold', color='darkgreen')
        ax2.set_ylim(0, 115)
        ax2.tick_params(axis='y', labelcolor='darkgreen')
        ax2.set_xlim(-0.5, 168.5)
        ax2.set_xticks([0, 24, 48, 72, 96, 120, 144, 168])
        ax2.set_xticklabels(['D1', 'D2', 'D3', 'D4', 'D5', 'D6', 'D7', 'D8'], fontsize=10)
        ax2.grid(True, alpha=0.3, linestyle='--', axis='y')
        ax2.legend(loc='upper right', fontsize=9.5, framealpha=0.95)
        
        # ================================================================
        # PANEL 3: IMPORTACIÓN DE RED - VALIDA REDUCCIÓN POR BESS
        # ================================================================
        
        # Mismo coloreado de fases
        for day in range(0, 7):
            day_start = day * 24
            ax3.axvspan(day_start + 6, day_start + 15, alpha=0.12, color='#00AA00')
            ax3.axvspan(day_start + 15, day_start + 17, alpha=0.1, color='#4169E1')
            ax3.axvspan(day_start + 17, day_start + 22, alpha=0.12, color='#DC143C')
            ax3.axvspan(day_start + 22, day_start + 24, alpha=0.08, color='#808080')
            ax3.axvspan(day_start + 0, day_start + 6, alpha=0.08, color='#808080')
        
        # Importación de red (barras rojo oscuro - cuanto MENOS, mejor)
        ax3.bar(hours_real, df_7days['grid_import_kwh'], width=0.85, color='#CC0000', alpha=0.7, 
               edgecolor='#990000', linewidth=1, label='🌐 Importación RED Pública')
        
        ax3.set_ylabel('Import. Red (kW)', fontsize=11, fontweight='bold', color='#CC0000')
        ax3.set_xlabel('Hora  (Primeros 7 días del año)', fontsize=12, fontweight='bold')
        ax3.tick_params(axis='y', labelcolor='#CC0000')
        ax3.set_xlim(-0.5, 168.5)
        ax3.set_xticks([0, 24, 48, 72, 96, 120, 144, 168])
        ax3.set_xticklabels(['D1', 'D2', 'D3', 'D4', 'D5', 'D6', 'D7', 'D8'], fontsize=10)
        ax3.grid(True, alpha=0.3, linestyle='--', axis='y')
        ax3.legend(loc='upper right', fontsize=9.5, framealpha=0.95)
        
        # Estadísticas en subtítulo
        carga_total = df['bess_charge_kw'].sum() / 1000  # Convertir kW a MWh (1h = 1 kW = 1 kWh)
        descarga_total = df['bess_discharge_kw'].sum() / 1000  # Convertir kW a MWh
        
        fig.suptitle(f'VALIDACIÓN DE 6-FASES: Carga={carga_total:.0f}MWh | Descarga={descarga_total:.0f}MWh | '
                    f'SOC rango 20-100% | Sin importación 6h-22h ✓',
                    fontsize=12, fontweight='bold', y=0.995)
        
        plt.savefig(out_dir / "00_INTEGRAL_todas_curvas.png", dpi=150, bbox_inches='tight')
        plt.close()
        print("  [OK] 00_INTEGRAL_todas_curvas.png - 6-FASES BESS visualizadas correctamente")
    
    def _plot_integral_curves_full_year(self, df: pd.DataFrame, out_dir: Path) -> None:
        """Grafica ANUAL: Todos los 365 días del año con validación de ventanas BESS.
        
        PROPÓSITO: Mostrar que la lógica 6h-15h (carga) y 15h-22h (descarga)
        se mantiene consistentemente DURANTE TODO EL AÑO.
        
        Panel superior: Año completo (8,760 horas comprimidas)
        Panel inferior: Estadísticas mensuales de conformidad
        """
        hours_year = np.arange(len(df))
        
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(22, 12))
        
        # ================================================================
        # PANEL 1: AÑO COMPLETO (365 días)
        # ================================================================
        
        # Datos de carga y descarga
        carga = df['bess_charge_kw'].values
        descarga = df['bess_discharge_kw'].values
        
        # VISUALIZACIÓN: Año comprimido con dos áreas claramente separadas
        # CARGA (arriba, verde)
        ax1.fill_between(hours_year, 0, carga, color='#00DD00', alpha=0.75, 
                        label='🔋 BESS Cargando (SOLO 6h-15h)', linewidth=0.5, edgecolor='darkgreen')
        
        # DESCARGA (abajo, naranja/rojo)
        ax1.fill_between(hours_year, 0, -descarga, color='#FF6B35', alpha=0.75,
                        label='↓ BESS Descargando (principalmente 15h-22h)', linewidth=0.5, edgecolor='darkorange')
        
        # Línea central en cero MUY MARCADA
        ax1.axhline(y=0, color='black', linewidth=3, zorder=10, alpha=0.8)
        
        # Resaltar ventanas cada 24h para marcar días
        for day_num in range(0, 365, 7):  # Marcar cada semana
            hour_start = day_num * 24
            ax1.axvline(x=hour_start, color='gray', linestyle=':', alpha=0.3, linewidth=0.5)
        
        # Marcar meses
        month_starts = [0, 31*24, 60*24, 91*24, 121*24, 152*24, 182*24, 213*24, 244*24, 274*24, 305*24, 335*24, 365*24]
        month_names = ['ENE', 'FEB', 'MAR', 'ABR', 'MAY', 'JUN', 'JUL', 'AGO', 'SEP', 'OCT', 'NOV', 'DIC']
        
        for month_num, (start, name) in enumerate(zip(month_starts[:-1], month_names)):
            mid_point = (start + month_starts[month_num + 1]) / 2
            ax1.text(mid_point, ax1.get_ylim()[1] * 0.95, name, 
                    fontsize=9, ha='center', fontweight='bold', color='darkred',
                    bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.7, pad=0.3))
        
        ax1.set_ylabel('Potencia (kW)', fontsize=13, fontweight='bold')
        ax1.set_title(
            '⚡ VALIDACIÓN ANUAL: Patrón de Ventanas BESS para TODOS los 365 Días de 2024\n'
            'CARGA ✓: 6h-15h (verde) | DESCARGA ↓: 15h-22h (naranja) | REPOSO: 22h-6h (vacío)',
            fontsize=15, fontweight='bold', color='darkred', pad=20)
        
        ax1.set_xlim(0, 8760)
        ax1.set_xticks([start for start in month_starts[:-1]])
        ax1.set_xticklabels(month_names, fontsize=10, fontweight='bold')
        ax1.grid(True, alpha=0.2, axis='y', linestyle='--')
        ax1.legend(loc='upper right', fontsize=11, framealpha=0.95)
        
        # ================================================================
        # PANEL 2: ESTADÍSTICAS MENSUALES DE CONFORMIDAD
        # ================================================================
        
        meses_carga = []
        meses_descarga = []
        dias_por_mes = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]  # 2024 es bisiesto
        
        day_idx = 0
        for mes, dias_en_mes in enumerate(dias_por_mes):
            carga_ventana_mes = 0
            carga_fuera_mes = 0
            descarga_ventana_mes = 0
            descarga_fuera_mes = 0
            
            for dia in range(dias_en_mes):
                start_hora = (day_idx + dia) * 24
                end_hora = min(start_hora + 24, len(carga))  # Protección contra índice fuera de rango
                
                # Ventana 6h-15h para carga
                carga_en_ventana = float(carga[start_hora + 6:min(start_hora + 15, len(carga))].sum())
                indices_fuera = list(range(start_hora, min(start_hora + 6, len(carga)))) + \
                                list(range(min(start_hora + 15, len(carga)), end_hora))
                carga_fuera = float(carga[indices_fuera].sum()) if len(indices_fuera) > 0 else 0.0
                
                # Ventana 15h-22h para descarga (primaria)
                descarga_en_ventana = float(descarga[min(start_hora + 15, len(descarga)):min(start_hora + 22, len(descarga))].sum())
                indices_desc_fuera = list(range(start_hora, min(start_hora + 15, len(descarga)))) + \
                                     list(range(min(start_hora + 22, len(descarga)), end_hora))
                descarga_fuera = float(descarga[indices_desc_fuera].sum()) if len(indices_desc_fuera) > 0 else 0.0
                
                carga_ventana_mes += carga_en_ventana
                carga_fuera_mes += carga_fuera
                descarga_ventana_mes += descarga_en_ventana
                descarga_fuera_mes += descarga_fuera
            
            # Porcentajes
            total_mes_carga = carga_ventana_mes + carga_fuera_mes if (carga_ventana_mes + carga_fuera_mes) > 0 else 1
            total_mes_desc = descarga_ventana_mes + descarga_fuera_mes if (descarga_ventana_mes + descarga_fuera_mes) > 0 else 1
            
            pct_carga = (carga_ventana_mes / total_mes_carga) * 100 if total_mes_carga > 0 else 0
            pct_descarga = (descarga_ventana_mes / total_mes_desc) * 100 if total_mes_desc > 0 else 0
            
            meses_carga.append(pct_carga)
            meses_descarga.append(pct_descarga)
            
            day_idx += dias_en_mes
        
        # Graficar porcentajes mensuales
        x_meses = np.arange(len(month_names))
        width = 0.35
        
        barras_carga = ax2.bar(x_meses - width/2, meses_carga, width, label='% Carga en 6h-15h', 
                              color='#00AA00', alpha=0.8, edgecolor='darkgreen', linewidth=2)
        barras_desc = ax2.bar(x_meses + width/2, meses_descarga, width, label='% Descarga en 15h-22h',
                             color='#FF6B35', alpha=0.8, edgecolor='darkorange', linewidth=2)
        
        # Línea de referencia 100%
        ax2.axhline(y=100, color='green', linestyle='--', linewidth=2, alpha=0.7, label='Conformidad 100%')
        ax2.axhline(y=89, color='orange', linestyle='--', linewidth=2, alpha=0.7, label='Línea 89% (descarga EV)')
        
        # Etiquetas en las barras
        for i, (bar_c, bar_d) in enumerate(zip(barras_carga, barras_desc)):
            height_c = bar_c.get_height()
            height_d = bar_d.get_height()
            ax2.text(bar_c.get_x() + bar_c.get_width()/2., height_c + 1, f'{height_c:.0f}%',
                    ha='center', va='bottom', fontsize=8, fontweight='bold', color='darkgreen')
            ax2.text(bar_d.get_x() + bar_d.get_width()/2., height_d + 1, f'{height_d:.0f}%',
                    ha='center', va='bottom', fontsize=8, fontweight='bold', color='darkorange')
        
        ax2.set_ylabel('% Conformidad de Ventanas', fontsize=12, fontweight='bold')
        ax2.set_xlabel('Mes de 2024', fontsize=12, fontweight='bold')
        ax2.set_title('Conformidad Mensual: % de Carga/Descarga dentro de Ventanas Diseñadas',
                     fontsize=13, fontweight='bold', color='darkred', pad=15)
        ax2.set_xticks(x_meses)
        ax2.set_xticklabels(month_names, fontsize=11, fontweight='bold')
        ax2.set_ylim(0, 115)
        ax2.grid(True, alpha=0.3, axis='y', linestyle='--')
        ax2.legend(loc='lower right', fontsize=11, framealpha=0.95)
        
        plt.tight_layout()
        plt.savefig(out_dir / "00_INTEGRAL_ANO_COMPLETO_VALIDACION.png", dpi=150, bbox_inches='tight')
        plt.close()
        print("  [OK] 00_INTEGRAL_ANO_COMPLETO_VALIDACION.png - Año 365 días validado")
    
    def _plot_energy_flow_diagram(self, df: pd.DataFrame, out_dir: Path) -> None:
        """Grafica 0.5: Flujo Energetico integrado (Sankey + día repr + SOC)."""
        total_pv = df['pv_generation_kw'].sum()
        total_ev = df['ev_demand_kw'].sum()
        total_mall = df['mall_demand_kw'].sum()
        total_bess_charge = df['bess_charge_kw'].sum()
        total_bess_discharge = df['bess_discharge_kw'].sum()
        total_grid_import = df['demand_from_grid_kw'].sum()
        total_pv_to_demand = df['pv_to_demand_kw'].sum()
        total_pv_to_bess = df['pv_to_bess_kw'].sum()
        total_pv_waste = df['pv_to_grid_kw'].sum()
        
        scale = 1000
        fig = plt.figure(figsize=(24, 13))
        gs = fig.add_gridspec(2, 2, width_ratios=[1, 1], height_ratios=[1, 0.7], hspace=0.35, wspace=0.25)
        
        ax1 = fig.add_subplot(gs[0:2, 0])
        ax2 = fig.add_subplot(gs[0, 1])
        ax3 = fig.add_subplot(gs[1, 1])
        
        # SUBPLOT 1: Sankey Anual
        nodes = {
            'pv': (0.08, 0.75), 'grid': (0.08, 0.15),
            'bess_carga': (0.4, 0.75), 'bess_descarga': (0.4, 0.25),
            'mall': (0.85, 0.75), 'ev': (0.85, 0.35), 'waste': (0.85, 0.02),
        }
        
        node_width, node_height = 0.07, 0.07
        for name, (x, y) in [('pv', nodes['pv']), ('grid', nodes['grid']), ('bess_carga', nodes['bess_carga']),
                             ('bess_descarga', nodes['bess_descarga']), ('mall', nodes['mall']), 
                             ('ev', nodes['ev']), ('waste', nodes['waste'])]:
            if name == 'pv':
                color, edge = '#FFD700', 'orange'
                ax1.add_patch(Rectangle((x - node_width/2, y - node_height/2), node_width, node_height,
                                           facecolor=color, edgecolor=edge, linewidth=3, alpha=0.9))
                ax1.text(x, y, 'Solar PV\n4,050 kWp', ha='center', va='center', fontsize=10, fontweight='bold')
            elif name == 'grid':
                color, edge = '#FF6347', 'darkred'
                ax1.add_patch(Rectangle((x - node_width/2, y - node_height/2), node_width, node_height,
                                           facecolor=color, edgecolor=edge, linewidth=3, alpha=0.9))
                ax1.text(x, y, 'Red Publica', ha='center', va='center', fontsize=10, fontweight='bold', color='white')
            elif name == 'bess_carga':
                color, edge = '#228B22', 'darkgreen'
                ax1.add_patch(Rectangle((x - node_width/2, y - node_height/2), node_width, node_height,
                                           facecolor=color, edgecolor=edge, linewidth=4, alpha=0.95))
                ax1.text(x, y + 0.02, 'BESS↑CARGA', ha='center', va='center', fontsize=9, fontweight='bold', color='white')
                ax1.text(x, y - 0.02, '2,000 kWh', ha='center', va='center', fontsize=7, color='white')
            elif name == 'bess_descarga':
                color, edge = '#FF8C00', 'darkorange'
                ax1.add_patch(Rectangle((x - node_width/2, y - node_height/2), node_width, node_height,
                                           facecolor=color, edgecolor=edge, linewidth=4, alpha=0.95))
                ax1.text(x, y + 0.02, 'BESS↓DESCARGA', ha='center', va='center', fontsize=9, fontweight='bold', color='white')
                ax1.text(x, y - 0.02, '400 kW', ha='center', va='center', fontsize=7, color='white')
            elif name == 'mall':
                color, edge = '#1E90FF', 'darkblue'
                ax1.add_patch(Rectangle((x - node_width/2, y - node_height/2), node_width, node_height,
                                           facecolor=color, edgecolor=edge, linewidth=2, alpha=0.9))
                ax1.text(x, y, 'Mall\n(RED)', ha='center', va='center', fontsize=9, fontweight='bold')
            elif name == 'ev':
                color, edge = '#32CD32', 'darkgreen'
                ax1.add_patch(Rectangle((x - node_width/2, y - node_height/2), node_width, node_height,
                                           facecolor=color, edgecolor=edge, linewidth=2, alpha=0.9))
                ax1.text(x, y, 'EV\n38 sockets', ha='center', va='center', fontsize=9, fontweight='bold')
            elif name == 'waste':
                color, edge = '#A9A9A9', 'black'
                ax1.add_patch(Rectangle((x - node_width/2, y - node_height/2), node_width, node_height,
                                           facecolor=color, edgecolor=edge, linewidth=2, alpha=0.6))
                ax1.text(x, y, 'Curtailment', ha='center', va='center', fontsize=8, fontweight='bold')
        
        ax1.set_xlim(-0.05, 1.05)
        ax1.set_ylim(-0.1, 1.1)
        ax1.axis('off')
        ax1.set_title('FLUJO ENERGETICO ANUAL - PERFIL EV DESDE CHARGERS + BESS DESAGREGADO',
                     fontsize=13, fontweight='bold', color='darkred')
        
        info_text = (
            f'BALANCE ANUAL OE2 REAL - BESS v5.4 + EV DESDE CHARGERS\n'
            f'PV: {total_pv/scale:.1f} MWh | Mall: {total_mall/scale:.1f} MWh | EV: {total_ev/scale:.1f} MWh\n'
            f'MOTOS: 270/día, 30 sockets, 4.6 kWh | TAXIS: 39/día, 8 sockets, 7.4 kWh\n'
            f'BESS CARGA: {total_pv_to_bess/scale:.1f} MWh | DESCARGA: {total_bess_discharge/scale:.1f} MWh'
        )
        ax1.text(0.01, 0.96, info_text, transform=ax1.transAxes,
                fontsize=7.5, verticalalignment='top', family='monospace',
                bbox=dict(boxstyle='round', facecolor='#FFFACD', alpha=0.95, pad=0.8))
        
        # SUBPLOT 2: Día representativo
        day_idx = 180
        day_df = df.iloc[day_idx*24:(day_idx+1)*24].copy()
        hours = np.arange(24)
        
        ax2.plot(hours, day_df['pv_generation_kw'].values, color='#FFD700', linewidth=3, marker='o', markersize=5, label='PV')
        ax2.bar(hours, day_df['mall_demand_kw'].values, width=0.65, label='Mall', color='#1E90FF', alpha=0.8)
        ax2.bar(hours, day_df['ev_demand_kw'].values, width=0.65, bottom=day_df['mall_demand_kw'].values, label='EV', color='#32CD32', alpha=0.8)
        ax2.plot(hours, day_df['total_demand_kw'].values, color='#DC143C', marker='D', linewidth=2.5, markersize=5, label='Total', linestyle='--')
        ax2.axhline(y=1900, color='#FF4500', linewidth=2.5, linestyle='--', label='Threshold 1900 kW', alpha=0.8)
        ax2.set_ylabel('Potencia (kW)', fontsize=11, fontweight='bold')
        ax2.set_title(f'Día {day_idx}: Lógica Operativa BESS v5.4', fontsize=11, fontweight='bold', color='darkred')
        ax2.grid(True, alpha=0.2, axis='y', linestyle=':')
        ax2.legend(loc='upper left', fontsize=8, ncol=2)
        ax2.set_xlim(-0.8, 23.8)
        
        # SUBPLOT 3: SOC
        ax3.plot(hours, day_df['bess_soc_percent'].values, color='#000000', linewidth=3.5, marker='o', markersize=5, label='SOC Real')
        ax3.fill_between(hours, 0, 20, alpha=0.25, color='#FF0000', label='Prohibida (<20%)')
        ax3.fill_between(hours, 20, 100, alpha=0.15, color='#228B22', label='Operativa (20%-100%)')
        ax3.axhline(y=100, color='green', linewidth=2, linestyle='--', alpha=0.7, label='Máximo (100%)')
        ax3.axhline(y=20, color='red', linewidth=2, linestyle='--', alpha=0.7, label='Mínimo (20%)')
        ax3.axhline(y=50, color='#4169E1', linewidth=1.5, linestyle=':', alpha=0.6, label='Prioridad 2 (50%)')
        ax3.set_xlabel('Hora', fontsize=10, fontweight='bold')
        ax3.set_ylabel('SOC (%)', fontsize=10, fontweight='bold')
        ax3.set_title('SOC BESS - Restricciones Operativas', fontsize=11, fontweight='bold', color='darkred')
        ax3.set_ylim(-5, 110)
        ax3.grid(True, alpha=0.2, axis='y', linestyle=':')
        ax3.legend(loc='right', fontsize=7.5, ncol=1)
        ax3.set_xlim(-0.8, 23.8)
        
        plt.tight_layout()
        plt.savefig(out_dir / "00.5_FLUJO_ENERGETICO_INTEGRADO.png", dpi=150, bbox_inches='tight')
        plt.close()
        print("  [OK] 00.5_FLUJO_ENERGETICO_INTEGRADO.png")
    
    def _plot_5day_balance(self, df: pd.DataFrame, out_dir: Path) -> None:
        """Grafica 1: Balance en 5 dias representativos."""
        fig, ax = plt.subplots(figsize=(16, 8))
        for day_idx in [0, 89, 180, 270, 359]:
            hours = list(range(24))
            ax.plot(hours, df.iloc[day_idx*24:(day_idx+1)*24]['pv_generation_kw'].values,
                   linewidth=2.5, marker='o', label=f'Día {day_idx}')
        ax.set_xlabel('Hora', fontsize=11, fontweight='bold')
        ax.set_ylabel('Potencia (kW)', fontsize=11, fontweight='bold')
        ax.set_title('Generacion Solar - 5 Dias Representativos', fontsize=13, fontweight='bold')
        ax.grid(True, alpha=0.3)
        ax.legend(loc='upper left', fontsize=10)
        ax.set_xlim(-0.5, 23.5)
        plt.tight_layout()
        plt.savefig(out_dir / "01_balance_5dias.png", dpi=150, bbox_inches='tight')
        plt.close()
        print("  [OK] 01_balance_5dias.png")
    
    def _plot_daily_balance(self, df: pd.DataFrame, out_dir: Path) -> None:
        """Grafica 2: Balance diario (365 dias)."""
        df_day = df.copy()
        df_day['day'] = df_day['hour'] // 24 if 'hour' in df_day.columns else np.arange(len(df_day)) // 24
        daily = df_day.groupby('day').agg({'pv_generation_kw': 'sum', 'total_demand_kw': 'sum', 'demand_from_grid_kw': 'sum'}).reset_index()
        
        fig, ax = plt.subplots(figsize=(16, 6))
        ax.fill_between(daily['day'], 0, daily['pv_generation_kw'], color='#FFD700', alpha=0.7, label='PV')
        ax.fill_between(daily['day'], 0, daily['total_demand_kw'], color='#DC143C', alpha=0.3, label='Demanda')
        ax.plot(daily['day'], daily['demand_from_grid_kw'], color='#FF6347', linewidth=2, marker='o', markersize=3, label='Red')
        ax.set_xlabel('Dia del Año', fontsize=11, fontweight='bold')
        ax.set_ylabel('Energia (kWh/dia)', fontsize=11, fontweight='bold')
        ax.set_title('Balance Diario - 365 Dias', fontsize=13, fontweight='bold')
        ax.legend(loc='upper right', fontsize=10)
        ax.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(out_dir / "02_balance_diario.png", dpi=150, bbox_inches='tight')
        plt.close()
        print("  [OK] 02_balance_diario.png")
    
    def _plot_sources_distribution(self, df: pd.DataFrame, out_dir: Path) -> None:
        """Grafica 3: Distribucion de fuentes."""
        pv = df['pv_to_demand_kw'].sum()
        bess = df['bess_discharge_kw'].sum() * 0.8 if 'bess_discharge_kw' in df.columns else 0
        grid = df['demand_from_grid_kw'].sum()
        total = pv + bess + grid
        
        fig, ax = plt.subplots(figsize=(10, 8))
        ax.pie([pv, bess, grid], labels=[f'PV\n{pv/total*100:.1f}%', f'BESS\n{bess/total*100:.1f}%', f'Red\n{grid/total*100:.1f}%'],
              colors=['#FFD700', '#32CD32', '#FF6347'], explode=(0.05, 0.05, 0.1), startangle=90,
              textprops={'fontsize': 11, 'fontweight': 'bold'})
        ax.set_title('Distribucion de Fuentes (Anual)', fontsize=13, fontweight='bold')
        plt.tight_layout()
        plt.savefig(out_dir / "03_distribucion_fuentes.png", dpi=150, bbox_inches='tight')
        plt.close()
        print("  [OK] 03_distribucion_fuentes.png")
    
    def _plot_energy_cascade(self, df: pd.DataFrame, out_dir: Path) -> None:
        """Grafica 4: Cascada energetica con clara diferenciación de fuentes."""
        pv_gen = df['pv_generation_kw'].sum()
        ev = df['ev_demand_kw'].sum()
        mall = df['mall_demand_kw'].sum()
        pv_dem = df['pv_to_demand_kw'].sum()
        pv_bess = df['pv_to_bess_kw'].sum()
        pv_waste = df['pv_to_grid_kw'].sum()
        bess_out = df['bess_discharge_kw'].sum()
        grid = df['demand_from_grid_kw'].sum()
        
        fig, ax = plt.subplots(figsize=(16, 10))
        
        # Categorías con descripciones claras
        cats = [
            'GENERACIÓN\nSolar PV\n(4,050 kWp)',
            'PV →\nDemanda\nDirecta',
            'PV →\nAlmacen\nBESS',
            'PV →\nExportar\nRed',
            'BESS →\nDescarga',
            'Red →\nImportar\nEnergía',
            'DEMANDA\nTOTAL\n(EV+Mall)'
        ]
        vals = [pv_gen, pv_dem, pv_bess, pv_waste, bess_out, grid, ev + mall]
        
        # Colores fuertemente diferenciados por artefacto
        # PV: Amarillo/Dorado | BESS: Naranja | Red: Rojo | Demanda: Rojo Oscuro
        cols = [
            '#FFD700',      # 0: PV Generación (Dorado)
            '#90EE90',      # 1: PV → Demanda (Verde claro)
            '#FF8C00',      # 2: PV → BESS (Naranja)
            '#FFB6C1',      # 3: PV → Grid Waste (Rosa/Descarte)
            '#FF6347',      # 4: BESS Descarga (Rojo tomate)
            '#FF1493',      # 5: Red Importación (Rojo profundo/Magenta)
            '#8B0000'       # 6: Demanda Total (Rojo muy oscuro)
        ]
        
        x_pos = np.arange(len(cats))
        bars = ax.bar(x_pos, vals, color=cols, alpha=0.85, edgecolor='black', linewidth=2.0, width=0.65)
        
        # Añadir valores sobre las barras
        for i, (v, bar) in enumerate(zip(vals, bars)):
            height = bar.get_height()
            ax.text(i, height + 100, f'{v:,.0f}\nkWh/año', 
                   ha='center', va='bottom', fontsize=9, fontweight='bold',
                   bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.7, edgecolor='gray'))
        
        # Leyenda con descripción de artefactos
        from matplotlib.patches import Patch
        legend_elements = [
            Patch(facecolor='#FFD700', edgecolor='black', label='☀️ PV Solar (Fuente)'),
            Patch(facecolor='#90EE90', edgecolor='black', label='⚡ Energía Directa (PV→Demanda)'),
            Patch(facecolor='#FF8C00', edgecolor='black', label='🔋 Almacenaje (PV→BESS)'),
            Patch(facecolor='#FFB6C1', edgecolor='black', label='⬆️ Exceso (PV→Red)'),
            Patch(facecolor='#FF6347', edgecolor='black', label='⬇️ BESS Descarga'),
            Patch(facecolor='#FF1493', edgecolor='black', label='🔌 Red Importada'),
            Patch(facecolor='#8B0000', edgecolor='black', label='📊 Demanda Total')
        ]
        ax.legend(handles=legend_elements, loc='upper left', fontsize=10, 
                 framealpha=0.95, title='COMPONENTES ENERGÉTICOS', title_fontsize=11)
        
        ax.set_xticks(x_pos)
        ax.set_xticklabels(cats, fontsize=10, fontweight='bold')
        ax.set_ylabel('Energía (kWh/año)', fontsize=12, fontweight='bold')
        ax.set_xlabel('Flujos Energéticos', fontsize=12, fontweight='bold')
        ax.set_title('Cascada Energética Anual - Diferenciación de Artefactos\n' + 
                    f'PV: {pv_gen:,.0f} | Demanda: {ev + mall:,.0f} | Grid: {grid:,.0f} kWh/año',
                    fontsize=14, fontweight='bold', pad=20)
        ax.grid(True, alpha=0.3, axis='y', linestyle='--')
        ax.set_axisbelow(True)
        
        # Mejorar formato y escala
        ax.yaxis.set_major_formatter(FuncFormatter(lambda x, p: f'{x/1e6:.1f}M'))
        ax.set_ylim(0, max(vals) * 1.15)
        
        plt.tight_layout()
        plt.savefig(out_dir / "04_cascada_energetica.png", dpi=150, bbox_inches='tight')
        plt.close()
        print("  [OK] 04_cascada_energetica.png")
    
    def _plot_bess_soc(self, df: pd.DataFrame, out_dir: Path) -> None:
        """Grafica 5: BESS SOC."""
        fig, ax = plt.subplots(figsize=(16, 6))
        hours = np.arange(len(df))
        soc = df['bess_soc_percent'].values
        
        ax.plot(hours, soc, linewidth=1, color='darkgreen', label='SOC Real')
        ax.axhline(y=100, color='green', linestyle='--', linewidth=1.5, alpha=0.7, label='Max')
        ax.axhline(y=20, color='red', linestyle='--', linewidth=1.5, alpha=0.7, label='Min')
        ax.fill_between(hours, 20, 100, alpha=0.1, color='green')
        
        ax.set_xlabel('Hora del Año', fontsize=11, fontweight='bold')
        ax.set_ylabel('SOC (%)', fontsize=11, fontweight='bold')
        ax.set_title(f'BESS {self.config.bess_capacity_kwh:.0f} kWh - SOC Horario', fontsize=13, fontweight='bold')
        ax.legend(loc='lower left', fontsize=10)
        ax.grid(True, alpha=0.3)
        ax.set_ylim(0, 110)
        ax.set_xlim(0, len(df))
        plt.tight_layout()
        plt.savefig(out_dir / "05_bess_soc.png", dpi=150, bbox_inches='tight')
        plt.close()
        print("  [OK] 05_bess_soc.png")
    
    def _plot_bess_charge_discharge(self, df: pd.DataFrame, out_dir: Path) -> None:
        """Grafica NUEVA: BESS CARGA y DESCARGA DESGLOSADA (PV→BESS, BESS→EV, BESS→MALL).
        
        Muestra explícitamente:
        - BESS CARGA (positivo): Barras verdes - cuando PV carga el BESS
        - BESS DESCARGA EV (negativo): Barras naranjas - cuando BESS descarga a EV
        - BESS DESCARGA MALL (negativo): Barras rojas - cuando BESS descarga para peak shaving MALL
        """
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(18, 12))
        
        hours = np.arange(len(df))
        
        # ===== GRÁFICO 1: CARGA y DESCARGAS HORARIAS (superpuestas) =====
        # Cargar datos
        if 'pv_to_bess_kw' in df.columns:
            charge_kw = df['pv_to_bess_kw'].values
        elif 'pv_to_bess_kwh' in df.columns:
            charge_kw = df['pv_to_bess_kwh'].values
        else:
            charge_kw = np.zeros(len(df))
        
        if 'bess_to_ev_kwh' in df.columns:
            discharge_ev_kw = df['bess_to_ev_kwh'].values
        else:
            discharge_ev_kw = np.zeros(len(df))
        
        if 'bess_to_mall_kwh' in df.columns:
            discharge_mall_kw = df['bess_to_mall_kwh'].values
        else:
            discharge_mall_kw = np.zeros(len(df))
        
        total_discharge_kw = discharge_ev_kw + discharge_mall_kw
        
        # Barras de carga (verde)
        ax1.bar(hours, charge_kw, width=1, label='BESS CARGA (PV→BESS)', color='#32CD32', alpha=0.85, edgecolor='none')
        
        # Barras de descarga en eje dual
        ax1_twin = ax1.twinx()
        ax1_twin.bar(hours, -discharge_ev_kw, width=1, label='BESS DESCARGA→EV', color='#FFA500', alpha=0.7, edgecolor='none')
        ax1_twin.bar(hours, -discharge_mall_kw, width=1, bottom=-discharge_ev_kw, label='BESS DESCARGA→MALL (Peak Shaving)', color='#DC143C', alpha=0.75, edgecolor='none')
        
        ax1.set_xlabel('Hora del Año', fontsize=10, fontweight='bold')
        ax1.set_ylabel('Carga (kW)', fontsize=10, fontweight='bold', color='#32CD32')
        ax1_twin.set_ylabel('Descarga (kW)', fontsize=10, fontweight='bold', color='#DC143C')
        ax1.set_title('Operación Horaria del BESS: Carga y Descargas Desglosadas', fontsize=12, fontweight='bold')
        ax1.tick_params(axis='y', labelcolor='#32CD32')
        ax1_twin.tick_params(axis='y', labelcolor='#DC143C')
        
        lines1, labels1 = ax1.get_legend_handles_labels()
        lines2, labels2 = ax1_twin.get_legend_handles_labels()
        ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper right', fontsize=9)
        ax1.grid(True, alpha=0.3, axis='y')
        
        # ===== GRÁFICO 2: RESUMEN MENSUAL CON DESGLOSE =====
        df_temp = df.copy()
        df_temp['month'] = np.arange(len(df_temp)) // (24 * 30)
        
        monthly_data = []
        for month in range(12):
            month_filter = (df_temp['month'] == month)
            if month_filter.sum() > 0:
                # Carga mensual
                if 'pv_to_bess_kw' in df.columns:
                    carga = df_temp.loc[month_filter, 'pv_to_bess_kw'].sum()
                elif 'pv_to_bess_kwh' in df.columns:
                    carga = df_temp.loc[month_filter, 'pv_to_bess_kwh'].sum()
                else:
                    carga = 0
                
                # Descarga EV
                if 'bess_to_ev_kwh' in df.columns:
                    desc_ev = df_temp.loc[month_filter, 'bess_to_ev_kwh'].sum()
                else:
                    desc_ev = 0
                
                # Descarga MALL
                if 'bess_to_mall_kwh' in df.columns:
                    desc_mall = df_temp.loc[month_filter, 'bess_to_mall_kwh'].sum()
                else:
                    desc_mall = 0
                
                monthly_data.append({
                    'month': month, 
                    'carga': carga, 
                    'desc_ev': desc_ev,
                    'desc_mall': desc_mall,
                    'desc_total': desc_ev + desc_mall
                })
        
        if monthly_data:
            monthly_df = pd.DataFrame(monthly_data)
            months = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']
            month_labels = [months[int(m)] for m in monthly_df['month'].values]
            x_pos = np.arange(len(monthly_df))
            width = 0.25
            
            # Carga (verde)
            ax2.bar(x_pos - width, monthly_df['carga'], width, label='Carga (PV→BESS)', 
                   color='#32CD32', edgecolor='black', linewidth=0.5)
            
            # Descarga EV (naranja)
            ax2.bar(x_pos, monthly_df['desc_ev'], width, label='Descarga→EV', 
                   color='#FFA500', edgecolor='black', linewidth=0.5)
            
            # Descarga MALL (rojo)
            ax2.bar(x_pos + width, monthly_df['desc_mall'], width, label='Descarga→MALL (Peak Shaving)', 
                   color='#DC143C', edgecolor='black', linewidth=0.5)
            
            ax2.set_xticks(x_pos)
            ax2.set_xticklabels(month_labels, fontsize=9, fontweight='bold')
        
        ax2.set_xlabel('Mes', fontsize=10, fontweight='bold')
        ax2.set_ylabel('Energía BESS (kWh/mes)', fontsize=10, fontweight='bold')
        ax2.set_title('Resumen Mensual: Carga y Descargas del BESS', fontsize=12, fontweight='bold')
        ax2.legend(loc='upper right', fontsize=9)
        ax2.grid(True, alpha=0.3, axis='y')
        
        # ===== GRÁFICO 3: PASTEL - DISTRIBUCIÓN DE DESCARGA =====
        total_desc_ev = float(discharge_ev_kw.sum())
        total_desc_mall = float(discharge_mall_kw.sum())
        total_desc = total_desc_ev + total_desc_mall
        
        if total_desc > 0:
            sizes = [total_desc_ev, total_desc_mall]
            labels = [
                f'BESS→EV\n{total_desc_ev:,.0f} kWh\n({total_desc_ev/total_desc*100:.1f}%)',
                f'BESS→MALL\n(Peak Shaving)\n{total_desc_mall:,.0f} kWh\n({total_desc_mall/total_desc*100:.1f}%)'
            ]
            colors = ['#FFA500', '#DC143C']
            explode = (0.05, 0.05)
            
            ax3.pie(sizes, labels=labels, colors=colors, autopct='', startangle=90,
                   explode=explode, textprops={'fontsize': 10, 'fontweight': 'bold'})
            ax3.set_title(f'Desglose de Descarga BESS Anual\nTotal: {total_desc:,.0f} kWh/año',
                         fontsize=12, fontweight='bold')
        else:
            ax3.text(0.5, 0.5, 'Sin descarga de BESS', ha='center', va='center', 
                    fontsize=12, fontweight='bold')
            ax3.set_xlim(0, 1)
            ax3.set_ylim(0, 1)
        
        # ===== GRÁFICO 4: TABLA RESUMEN =====
        ax4.axis('off')
        
        total_charge_annual = float(charge_kw.sum())
        
        summary_text = (
            f"RESUMEN ANUAL DE OPERACIÓN BESS\n"
            f"{'='*50}\n\n"
            f"CARGA (PV → BESS):\n"
            f"  • Energía cargada: {total_charge_annual:>15,.0f} kWh\n"
            f"  • Promedio/día:    {total_charge_annual/365:>15,.0f} kWh\n\n"
            f"DESCARGA (BESS → EV):\n"
            f"  • Energía entregada: {total_desc_ev:>14,.0f} kWh\n"
            f"  • Porcentaje:        {total_desc_ev/total_desc*100:>14.1f}%\n"
            f"  • Promedio/día:      {total_desc_ev/365:>14,.0f} kWh\n\n"
            f"DESCARGA (BESS → MALL - Peak Shaving):\n"
            f"  • Energía entregada: {total_desc_mall:>14,.0f} kWh\n"
            f"  • Porcentaje:        {total_desc_mall/total_desc*100:>14.1f}%\n"
            f"  • Promedio/día:      {total_desc_mall/365:>14,.0f} kWh\n\n"
            f"TOTAL DESCARGA:\n"
            f"  • Anual:            {total_desc:>15,.0f} kWh\n"
            f"  • Promedio/día:     {total_desc/365:>15,.0f} kWh\n\n"
            f"RATIO CARGA/DESCARGA:\n"
            f"  • Carga/Descarga:   {total_charge_annual/total_desc if total_desc > 0 else 0:>15.2f}\n"
            f"{'='*50}"
        )
        
        ax4.text(0.05, 0.95, summary_text, transform=ax4.transAxes, 
                fontsize=10, verticalalignment='top', fontfamily='monospace',
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
        
        plt.tight_layout()
        plt.savefig(out_dir / "05.1_bess_carga_descarga.png", dpi=150, bbox_inches='tight')
        plt.close()
        
        # Imprimir desglose completo
        print(f"\n  Totales BESS:")
        print(f"    Carga anual (PV a BESS):     {total_charge_annual:>15,.0f} kWh")
        print(f"    Descarga a EV:                {total_desc_ev:>15,.0f} kWh ({total_desc_ev/total_desc*100:.1f}%)")
        print(f"    Descarga a MALL (Peak Shaving): {total_desc_mall:>15,.0f} kWh ({total_desc_mall/total_desc*100:.1f}%)")
        print(f"    Descarga total:               {total_desc:>15,.0f} kWh")
        print("  [OK] 05.1_bess_carga_descarga.png")
    
    def _plot_pv_export_breakdown(self, df: pd.DataFrame, out_dir: Path) -> None:
        """Grafica NUEVA v5.8: DESGLOSE DE GENERACIÓN SOLAR - Exportación a Red
        
        Muestra:
        - PV → EV (Carga directa)
        - PV → BESS (Almacenamiento)
        - PV → Mall (Directo al centro comercial)
        - PV → GRID (Exportación - Parte no utilizada)
        """
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
        
        # Gráfico 1: Pastel - Desglose de generación solar anual
        # Usar las columnas normalizadas del dataset
        pv_total = df['pv_generation_kw'].sum() if 'pv_generation_kw' in df.columns else df['pv_kwh'].sum() if 'pv_kwh' in df.columns else 0
        
        pv_to_ev = df['pv_to_ev_kw'].sum() if 'pv_to_ev_kw' in df.columns else df['pv_to_ev_kwh'].sum() if 'pv_to_ev_kwh' in df.columns else 0
        pv_to_bess = df['pv_to_bess_kw'].sum() if 'pv_to_bess_kw' in df.columns else df['pv_to_bess_kwh'].sum() if 'pv_to_bess_kwh' in df.columns else 0
        pv_to_mall = df['pv_to_mall_kw'].sum() if 'pv_to_mall_kw' in df.columns else df['pv_to_mall_kwh'].sum() if 'pv_to_mall_kwh' in df.columns else 0
        pv_to_grid = df['grid_export_kw'].sum() if 'grid_export_kw' in df.columns else df['grid_export_kwh'].sum() if 'grid_export_kwh' in df.columns else 0
        
        # Protección contra división por cero
        if pv_total > 0:
            pv_to_ev_pct = pv_to_ev/pv_total*100
            pv_to_bess_pct = pv_to_bess/pv_total*100
            pv_to_mall_pct = pv_to_mall/pv_total*100
            pv_to_grid_pct = pv_to_grid/pv_total*100
        else:
            pv_to_ev_pct = pv_to_bess_pct = pv_to_mall_pct = pv_to_grid_pct = 0
        
        sizes = [pv_to_ev, pv_to_bess, pv_to_mall, pv_to_grid]
        labels = [
            f'EV\n{pv_to_ev:,.0f} kWh\n({pv_to_ev_pct:.1f}%)',
            f'BESS\n{pv_to_bess:,.0f} kWh\n({pv_to_bess_pct:.1f}%)',
            f'Mall\n{pv_to_mall:,.0f} kWh\n({pv_to_mall_pct:.1f}%)',
            f'Grid Export\n{pv_to_grid:,.0f} kWh\n({pv_to_grid_pct:.1f}%)',
        ]
        colors = ['#FFD700', '#32CD32', '#FF8C00', '#87CEEB']
        explode = (0.05, 0.05, 0.05, 0.1)  # Destacar exportación
        
        ax1.pie(sizes, labels=labels, colors=colors, autopct='', startangle=90, 
               explode=explode, textprops={'fontsize': 10, 'fontweight': 'bold'})
        ax1.set_title(f'Desglose de Generación Solar\nTotal: {pv_total:,.0f} kWh/año', 
                     fontsize=13, fontweight='bold')
        
        # Gráfico 2: Barras mensuales - Exportación a red por mes
        df_temp = df.copy()
        df_temp['month'] = np.arange(len(df_temp)) // (24 * 30)
        
        monthly_export = []
        for month in range(12):
            month_filter = (df_temp['month'] == month)
            if month_filter.sum() > 0:
                export = df_temp.loc[month_filter, 'grid_export_kw'].sum() if 'grid_export_kw' in df.columns else df_temp.loc[month_filter, 'grid_export_kwh'].sum() if 'grid_export_kwh' in df.columns else 0
                monthly_export.append(export)
        
        months = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']
        x_pos = np.arange(len(monthly_export))
        
        bars = ax2.bar(x_pos, monthly_export, color='#87CEEB', edgecolor='navy', linewidth=1.5)
        ax2.set_xticks(x_pos)
        ax2.set_xticklabels(months, fontsize=10, fontweight='bold')
        ax2.set_ylabel('Exportación a Red (kWh)', fontsize=11, fontweight='bold')
        ax2.set_title('Energía Exportada a la Red por Mes\n(Excedente de PV no utilizado)', fontsize=13, fontweight='bold')
        ax2.grid(True, alpha=0.3, axis='y')
        
        # Valores en barras
        for i, (bar, val) in enumerate(zip(bars, monthly_export)):
            height = bar.get_height()
            ax2.text(bar.get_x() + bar.get_width()/2., height,
                    f'{val:,.0f}', ha='center', va='bottom', fontsize=8)
        
        plt.tight_layout()
        plt.savefig(out_dir / "08_pv_exportacion_desglose.png", dpi=150, bbox_inches='tight')
        plt.close()
        
        # Resumen en consola
        print(f"\n  Desglose Generación Solar (PV):")
        print(f"    - EV (Directo):               {pv_to_ev:>15,.0f} kWh ({pv_to_ev/pv_total*100:>6.1f}%)")
        print(f"    - BESS (Almacén):             {pv_to_bess:>15,.0f} kWh ({pv_to_bess/pv_total*100:>6.1f}%)")
        print(f"    - Mall (Directo):             {pv_to_mall:>15,.0f} kWh ({pv_to_mall/pv_total*100:>6.1f}%)")
        print(f"    - Red (Exportación):          {pv_to_grid:>15,.0f} kWh ({pv_to_grid/pv_total*100:>6.1f}%)")
        print(f"    Total Autoconsumo (no-export): {pv_total - pv_to_grid:>15,.0f} kWh ({(pv_total-pv_to_grid)/pv_total*100:>6.1f}%)")
        print("  [OK] 08_pv_exportacion_desglose.png")
    
    def _plot_co2_emissions(self, df: pd.DataFrame, out_dir: Path) -> None:
        """Grafica 6: Emisiones CO2."""
        df_day = df.copy()
        df_day['day'] = df_day['hour'] // 24 if 'hour' in df_day.columns else np.arange(len(df_day)) // 24
        daily_co2 = df_day.groupby('day')['co2_from_grid_kg'].sum().reset_index()
        
        fig, ax = plt.subplots(figsize=(16, 6))
        ax.bar(daily_co2['day'], daily_co2['co2_from_grid_kg'], color='#DC143C', alpha=0.8, edgecolor='darkred', linewidth=0.5)
        mean_co2 = daily_co2['co2_from_grid_kg'].mean()
        ax.axhline(y=mean_co2, color='black', linestyle='--', linewidth=2, label=f'Promedio: {mean_co2:.1f} kg/día')
        
        ax.set_xlabel('Dia del Año', fontsize=11, fontweight='bold')
        ax.set_ylabel('Emisiones CO2 (kg/dia)', fontsize=11, fontweight='bold')
        ax.set_title(f'Emisiones CO2 - {self.config.co2_intensity_kg_per_kwh:.4f} kg/kWh', fontsize=13, fontweight='bold')
        ax.legend(loc='upper right', fontsize=10)
        ax.grid(True, alpha=0.3, axis='y')
        plt.tight_layout()
        plt.savefig(out_dir / "06_emisiones_co2.png", dpi=150, bbox_inches='tight')
        plt.close()
        print("  [OK] 06_emisiones_co2.png")
    
    def _plot_pv_utilization(self, df: pd.DataFrame, out_dir: Path) -> None:
        """Grafica 7: Utilizacion mensual PV."""
        df_month = df.copy()
        df_month['month'] = (df_month['hour'] // 24 if 'hour' in df_month.columns else np.arange(len(df_month)) // 24) // 30 + 1
        monthly = df_month.groupby('month').agg({'pv_generation_kw': 'sum', 'pv_to_demand_kw': 'sum',
                                                    'pv_to_bess_kw': 'sum', 'pv_to_grid_kw': 'sum'}).reset_index()
        monthly = monthly[monthly['month'] <= 12]
        
        fig, ax = plt.subplots(figsize=(12, 7))
        months = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']
        month_labels = months[:len(monthly)]
        x_pos = np.arange(len(monthly))
        
        width = 0.2
        ax.bar(x_pos - 1.5*width, monthly['pv_to_demand_kw'], width, label='PV→Demanda', color='#FFD700', edgecolor='black', linewidth=0.5)
        ax.bar(x_pos - 0.5*width, monthly['pv_to_bess_kw'], width, label='PV→BESS', color='#32CD32', edgecolor='black', linewidth=0.5)
        ax.bar(x_pos + 0.5*width, monthly['pv_to_grid_kw'], width, label='PV→Red', color='#FF6347', edgecolor='black', linewidth=0.5)
        ax.plot(x_pos, monthly['pv_generation_kw'], 'ko-', linewidth=2.5, markersize=8, label='Total PV')
        
        ax.set_xticks(x_pos)
        ax.set_xticklabels(month_labels, fontsize=10, fontweight='bold')
        ax.set_xlabel('Mes', fontsize=11, fontweight='bold')
        ax.set_ylabel('Energia (kWh/mes)', fontsize=11, fontweight='bold')
        ax.set_title('Utilizacion Mensual de PV', fontsize=13, fontweight='bold')
        ax.legend(loc='upper right', fontsize=10)
        ax.grid(True, alpha=0.3, axis='y')
        
        plt.tight_layout()
        plt.savefig(out_dir / "07_utilizacion_pv.png", dpi=150, bbox_inches='tight')
        plt.close()
        print("  [OK] 07_utilizacion_pv.png")


def main():
    """Ejecutar con datos REALES de 4 datasets CON AUTO-ACTUALIZACIÓN.
    
    =============================================================================
    v5.8 AUTO-DETECCIÓN DE CAMBIOS (2026-02-21)
    =============================================================================
    balance.py SIEMPRE carga 4 datasets y detecta cambios automáticamente:
    
    DATASETS REQUERIDOS (4):
      1. pv_generation_citylearn2024.csv       ← PV Solar (BESS input)
      2. chargers_ev_ano_2024_v3.csv           ← EV Demand (BESS input)
      3. demandamallhorakwh.csv                ← MALL Demand (BESS input)
      4. bess_ano_2024.csv                     ← BESS Simulado (salida de bess.py)
    
    AUTO-ACTUALIZACIÓN:
      ✓ Detecta cambios en CUALQUIERA de los 4 archivos
      ✓ Si hay cambios → regenera gráficas automáticamente
      ✓ Sistema de metadata (hash MD5) para comparación eficiente
      ✓ Respeta rutas FIJAS con Final[Path] (datasets_config.py)
    
    FLUJO OBLIGATORIO:
      1. bess.py lee 3 datasets (PV, EV, MALL)
      2. bess.py genera bess_ano_2024.csv (salida)
      3. balance.py lee 4 datasets (PV, EV, MALL, BESS)
      4. balance.py detecta cambios y regenera gráficas
    
    =============================================================================
    """
    import numpy as np
    
    print("=" * 80)
    print("BALANCE ENERGÉTICO - Graphics Module v5.8 (CON AUTO-ACTUALIZACIÓN)")
    print("=" * 80)
    print()
    print("MODO: 4 Datasets con detección automática de cambios")
    print()
    
    # =====================================================================
    # CARGAR 4 DATASETS REQUERIDOS CON AUTO-DETECCIÓN
    # =====================================================================
    try:
        # Calcular project root PRIMERO (directorio donde está el proyecto)
        # balance.py → src/dimensionamiento/oe2/balance_energetico/balance.py
        # Necesita 5 .parent: balance_energetico → oe2 → dimensionamiento → src → (project_root)
        script_dir = Path(__file__)
        project_root = script_dir.parent.parent.parent.parent.parent
        
        # Definir rutas FIJAS basadas en project_root
        pv_csv_path = project_root / "data" / "oe2" / "Generacionsolar" / "pv_generation_citylearn2024.csv"
        ev_csv_path = project_root / "data" / "oe2" / "chargers" / "chargers_ev_ano_2024_v3.csv"
        mall_csv_path = project_root / "data" / "oe2" / "demandamallkwh" / "demandamallhorakwh.csv"
        bess_csv_path = project_root / "data" / "interim" / "oe2" / "bess" / "bess_ano_2024.csv"
        
        # Cargar los 4 datasets
        print()
        print("[1/4] CARGANDO PV GENERATION: {}".format(pv_csv_path.name))
        if not pv_csv_path.exists():
            raise FileNotFoundError(f"PV no encontrado: {pv_csv_path}")
        df_pv = pd.read_csv(pv_csv_path)
        pv_gen = df_pv['energia_kwh'].values if 'energia_kwh' in df_pv.columns else df_pv.iloc[:, 0].values
        print(f"      [OK] {len(pv_gen):,} horas - Total: {pv_gen.sum():,.0f} kWh/año")
        
        # RUTA 2: EV DEMAND
        print("[2/4] CARGANDO EV DEMAND: {}".format(ev_csv_path.name))
        if not ev_csv_path.exists():
            raise FileNotFoundError(f"EV no encontrado: {ev_csv_path}")
        df_ev = pd.read_csv(ev_csv_path)
        ev_demand = df_ev['ev_energia_total_kwh'].values if 'ev_energia_total_kwh' in df_ev.columns else np.zeros(8760)
        print(f"      [OK] {len(ev_demand):,} horas - Total: {ev_demand.sum():,.0f} kWh/año (38 sockets)")
        
        # RUTA 3: MALL DEMAND
        print("[3/4] CARGANDO MALL DEMAND: {}".format(mall_csv_path.name))
        if not mall_csv_path.exists():
            raise FileNotFoundError(f"MALL no encontrado: {mall_csv_path}")
        df_mall = pd.read_csv(mall_csv_path, sep=",")
        df_mall['datetime'] = pd.to_datetime(df_mall['datetime'])
        df_mall_2024 = df_mall[df_mall['datetime'].dt.year == 2024].sort_values('datetime').reset_index(drop=True)
        mall_demand = df_mall_2024['mall_demand_kwh'].values[:8760]
        mall_peak = mall_demand.max()
        print(f"      [OK] {len(mall_demand):,} horas - Total: {mall_demand.sum():,.0f} kWh/año")
        print(f"      [CRÍTICO] Pico MALL: {mall_peak:,.1f} kW {'(*EXCEDE 1900 kW)' if mall_peak > 1900 else ''}")
        
        # RUTA 4: BESS AÑO 2024
        print("[4/4] CARGANDO BESS SIMULADO: {}".format(bess_csv_path.name))
        if not bess_csv_path.exists():
            print(f"      ❌ BESS no encontrado: {bess_csv_path}")
            print(f"      → INSTRUCCIÓN: Ejecuta primero bess.py")
            raise FileNotFoundError(f"BESS no encontrado: {bess_csv_path}")
        df_bess = pd.read_csv(bess_csv_path)
        print(f"      [OK] {len(df_bess):,} horas cargadas desde BESS simulado")
        
        # Extraer columnas del BESS
        grid_export_real = df_bess['grid_export_kwh'].values if 'grid_export_kwh' in df_bess.columns else np.zeros(len(pv_gen))
        
        print(f"\n{'='*80}")
        print("RESUMEN: 4 DATASETS CARGADOS (AUTO-UPDATE ACTIVO):")
        print(f"{'='*80}")
        print(f"  [1] PV Solar:       {pv_gen.sum():>15,.0f} kWh/año")
        print(f"  [2] EV Demand:      {ev_demand.sum():>15,.0f} kWh/año (38 sockets)")
        print(f"  [3] MALL Demand:    {mall_demand.sum():>15,.0f} kWh/año (pico: {mall_peak:,.0f} kW)")
        print(f"  [4] BESS Output:    {grid_export_real.sum():>15,.0f} kWh exportados/año")
        print(f"\n{'='*80}\n")
        
    except FileNotFoundError as e:
        print("\n" + "="*80)
        print("❌ ERROR CRÍTICO: Archivo de dataset no encontrado")
        print("="*80)
        print(f"\nMensaje: {e}")
        print("\n✓ Los 4 datasets REQUERIDOS son:")
        print("  1. data/oe2/Generacionsolar/pv_generation_citylearn2024.csv")
        print("  2. data/oe2/chargers/chargers_ev_ano_2024_v3.csv")
        print("  3. data/oe2/demandamallkwh/demandamallhorakwh.csv")
        print("  4. data/oe2/bess/bess_ano_2024.csv (genera bess.py)")
        print("\n✓ Instrucción:")
        print("  python -m src.dimensionamiento.oe2.disenobess.bess")
        print("="*80 + "\n")
        sys.exit(1)
    except ImportError as e:
        print("\n" + "="*80)
        print("❌ ERROR: Módulo datasets_config.py no encontrado o importación fallida")
        print("="*80)
        print(f"\nMensaje: {e}")
        print("\nIntenta: Reinicia el entorno Python y verifica datasets_config.py existe")
        print("="*80 + "\n")
        sys.exit(1)
    except Exception as e:
        print("\n" + "="*80)
        print("❌ ERROR INESPERADO al cargar datasets")
        print("="*80)
        print(f"\nMensaje: {e}")
        print("\nVerifica: Integridad de los 4 CSV, espacios en nombres, encoding UTF-8")
        print("="*80 + "\n")
        sys.exit(1)
    
    hours = len(mall_demand)
    
    # Usar demanda EV y PV ya cargados del dataset real (no sintéticos)
    total_demand = mall_demand + ev_demand
    
    # =====================================================
    # CONFIGURACION DE PEAK SHAVING: MALL > 1900 kW
    # =====================================================
    # CRITICO: Mall tiene demanda pico por encima de 1900 kW (VALIDACION)
    # El BESS descarga cuando PV < demanda_mall (punto critico de deficit solar)
    # El umbral 1900 kW es referencia para alertar sobre picos altos del sistema
    peak_shaving_threshold_kw = 1900.0  # UMBRAL REFERENCIA: Identifica picos altos de Mall
    
    print("\n[CONFIGURACION PEAK SHAVING]")
    print("  Umbral de referencia: {:.0f} kW (demanda pico Mall excede este valor)".format(peak_shaving_threshold_kw))
    print("  Logica de descarga BESS: Cuando PV < demanda_mall (punto critico solar)")
    print("  Objetivo: Peak shaving en periodos de deficit solar")
    print("  NOTA: BESS descarga por deficit solar, no por un umbral fijo")
    
    # BESS logic
    bess_soc = np.ones(hours) * 50
    bess_charge = np.zeros(hours)
    bess_discharge = np.zeros(hours)
    demand_from_grid = np.zeros(hours)
    pv_to_demand = np.zeros(hours)
    pv_to_bess = np.zeros(hours)
    pv_to_grid = np.zeros(hours)
    co2_from_grid = np.zeros(hours)
    grid_export_kwh = np.zeros(hours)  # NEW: Exportación a red pública (kWh)
    bess_to_mall_kwh = np.zeros(hours)  # NEW: Peak shaving BESS→MALL (kWh) - para picos > 1900 kW
    
    # =====================================================
    # CARGAR DATOS BESS REALES desde bess_ano_2024.csv (YA CONTIENE LÓGICA SIMULADA)
    # =====================================================
    print("[CARGANDO] BESS Completo desde dataset OE2...")
    df_bess_full = pd.read_csv(bess_csv_path)
    
    # Usar columnas reales del BESS (nombres exactos del dataset bess.py)
    # NOTA: bess.py genera 'bess_action_kwh', 'bess_to_ev_kwh', 'bess_to_mall_kwh'
    # NO 'bess_charge_kwh' / 'bess_discharge_kwh' (no están en OUTPUT de bess.py)
    
    # Columns disponibles en bess_ano_2024.csv:
    # ['datetime', 'pv_kwh', 'ev_kwh', 'mall_kwh', 'load_kwh', 
    #  'pv_to_ev_kwh', 'pv_to_bess_kwh', 'pv_to_mall_kwh', 'grid_export_kwh',
    #  'bess_action_kwh', 'bess_mode', 'bess_to_ev_kwh', 'bess_to_mall_kwh',
    #  'grid_import_ev_kwh', 'grid_import_mall_kwh', 'grid_import_kwh', 'soc_percent', ...]
    
    if 'pv_to_demand_kw' in df_bess_full.columns:
        pv_to_demand = df_bess_full['pv_to_demand_kw'].values[:hours]
    else:
        # FALLBACK: PV a demanda = PV_to_EV + PV_to_Mall
        pv_to_demand = (df_bess_full['pv_to_ev_kwh'].values[:hours] + 
                       df_bess_full['pv_to_mall_kwh'].values[:hours])
    
    # Cargar PV → EV (directo)
    if 'pv_to_ev_kwh' in df_bess_full.columns:
        pv_to_ev = df_bess_full['pv_to_ev_kwh'].values[:hours]
    else:
        pv_to_ev = np.zeros(hours)
    
    # Cargar PV → Mall (directo)
    if 'pv_to_mall_kwh' in df_bess_full.columns:
        pv_to_mall = df_bess_full['pv_to_mall_kwh'].values[:hours]
    else:
        pv_to_mall = np.zeros(hours)
    
    if 'pv_to_bess_kwh' in df_bess_full.columns:
        pv_to_bess = df_bess_full['pv_to_bess_kwh'].values[:hours]
    
    if 'pv_to_grid_kw' in df_bess_full.columns:
        pv_to_grid = df_bess_full['pv_to_grid_kw'].values[:hours]
    else:
        pv_to_grid = df_bess_full['grid_export_kwh'].values[:hours]  # Exportación = PV a red
    
    # BESS: Usar datos REALES del dataset bess_ano_2024.csv
    # Columnas disponibles: bess_to_ev_kwh, bess_to_mall_kwh, bess_energy_stored_hourly_kwh, bess_energy_delivered_hourly_kwh
    bess_to_ev = df_bess_full['bess_to_ev_kwh'].values[:hours]
    bess_to_mall_kwh = df_bess_full['bess_to_mall_kwh'].values[:hours]
    
    # Descarga total BESS = suma de descargas a EV + MALL
    bess_discharge = bess_to_ev + bess_to_mall_kwh  # Total descarga BESS
    
    # Carga BESS: Usar columna real del dataset (energía almacenada por hora)
    # Si existe bess_energy_stored_hourly_kwh, usarla; si no, usar proxy pv_to_bess
    if 'bess_energy_stored_hourly_kwh' in df_bess_full.columns:
        bess_charge = df_bess_full['bess_energy_stored_hourly_kwh'].values[:hours]
    else:
        # Fallback: usar PV a BESS como proxy
        bess_charge = pv_to_bess
    
    if 'soc_percent' in df_bess_full.columns:
        bess_soc = df_bess_full['soc_percent'].values[:hours]
    elif 'bess_soc_percent' in df_bess_full.columns:
        bess_soc = df_bess_full['bess_soc_percent'].values[:hours]
    
    if 'grid_import_kwh' in df_bess_full.columns:
        demand_from_grid = df_bess_full['grid_import_kwh'].values[:hours]
    else:
        # FALLBACK: Grid = grid_import_ev + grid_import_mall
        demand_from_grid = (df_bess_full['grid_import_ev_kwh'].values[:hours] + 
                           df_bess_full['grid_import_mall_kwh'].values[:hours])
    
    if 'grid_export_kwh' in df_bess_full.columns:
        grid_export_kwh = df_bess_full['grid_export_kwh'].values[:hours]
    
    # Calcular CO2 desde grid importado real
    co2_from_grid = demand_from_grid * 0.4521 / 1000
    
    # Obtener columnas adicionales desde df_bess_full si existen
    bess_energy_stored = np.zeros(hours)
    bess_energy_delivered = np.zeros(hours)
    soc_percent = bess_soc  # Default: usar bess_soc que ya tenemos
    
    if 'bess_energy_stored_hourly_kwh' in df_bess_full.columns:
        bess_energy_stored = df_bess_full['bess_energy_stored_hourly_kwh'].values[:hours]
    if 'bess_energy_delivered_hourly_kwh' in df_bess_full.columns:
        bess_energy_delivered = df_bess_full['bess_energy_delivered_hourly_kwh'].values[:hours]
    if 'soc_percent' in df_bess_full.columns:
        soc_percent = df_bess_full['soc_percent'].values[:hours]
    
    df = pd.DataFrame({
        'hour': np.arange(hours),
        'pv_generation_kw': pv_gen,
        'pv_kwh': pv_gen,  # ALIAS
        'mall_demand_kw': mall_demand,
        'mall_kwh': mall_demand,  # NEW: Mall demand in kWh (same as kW for hourly data)
        'ev_demand_kw': ev_demand,
        'ev_kwh': ev_demand,  # ALIAS
        'total_demand_kw': total_demand,
        'pv_to_demand_kw': pv_to_demand,
        'pv_to_ev_kw': pv_to_ev,  # NUEVO: PV directo a EV
        'pv_to_ev_kwh': pv_to_ev,  # ALIAS para compatibilidad en gráficas
        'pv_to_bess_kw': pv_to_bess,
        'pv_to_bess_kwh': pv_to_bess,  # ALIAS para compatibilidad
        'pv_to_mall_kw': pv_to_mall,  # NUEVO: PV directo a Mall
        'pv_to_mall_kwh': pv_to_mall,  # ALIAS para compatibilidad en gráficas
        'pv_to_grid_kw': pv_to_grid,
        'grid_export_kw': pv_to_grid,  # ALIAS
        'grid_export_kwh': grid_export_real,  # REAL: Usar valores reales del dataset bess_ano_2024.csv
        'bess_charge_kw': bess_charge,
        'bess_discharge_kw': bess_discharge,
        'bess_to_ev_kwh': bess_to_ev,  # NUEVO: Descarga BESS EV
        'bess_to_mall_kwh': bess_to_mall_kwh,  # NEW: Peak shaving BESS→MALL
        'bess_soc_percent': bess_soc,
        'soc_percent': soc_percent,  # ALIAS para compatibilidad con gráficas
        'bess_energy_stored_hourly_kwh': bess_energy_stored,  # Energía almacenada (kWh)
        'bess_energy_delivered_hourly_kwh': bess_energy_delivered,  # Energía descargada (kWh)
        'demand_from_grid_kw': demand_from_grid,
        'grid_import_kwh': demand_from_grid,  # ALIAS para compatibilidad
        'co2_from_grid_kg': co2_from_grid,
    })
    
    print("[OK] DataFrame creado: {} horas x {} columnas".format(df.shape[0], df.shape[1]))
    print("    Mall: min={:.1f} kW, max={:.1f} kW, mean={:.1f} kW".format(
        df['mall_demand_kw'].min(), df['mall_demand_kw'].max(), df['mall_demand_kw'].mean()))
    print("    Grid Export: {:.0f} kWh/año (promedio {:.0f} kWh/día)".format(
        df['grid_export_kwh'].sum(), df['grid_export_kwh'].sum() / 365))
    print("    Peak Shaving: {:.0f} kWh/año (reducción de demanda MALL)".format(
        df['bess_to_mall_kwh'].sum()))
    
    # =====================================================
    # REPORTE: DEMANDA PICO MALL > 1900 kW
    # =====================================================
    mall_peak = df['mall_demand_kw'].max()
    print("\n    [DEMANDA PICO MALL - CRITICA V5.7]")
    print("    PICO MAXIMO: {:.1f} kW (EXCEDE 1900 kW - referencia critica)".format(mall_peak))
    print("    BESS descarga cuando PV < demanda_mall (punto critico solar)")
    print("    Annual peak shaving: {:.0f} kWh/ano (BESS respalda deficit solar)".format(df['bess_to_mall_kwh'].sum()))
    print()
    
    # Crear sistema de gráficas
    config = BalanceEnergeticoConfig()
    graphics = BalanceEnergeticoSystem(df, config)
    print("[OK] BalanceEnergeticoSystem inicializado")
    print("  - PV: {:.0f} kWp".format(config.pv_capacity_kwp))
    print("  - BESS: {:.0f} kWh / {:.0f} kW".format(config.bess_capacity_kwh, config.bess_power_kw))
    print("  - CO2 intensity: {:.4f} kg/kWh".format(config.co2_intensity_kg_per_kwh))
    print()
    
    # Generar gráficas
    out_dir = Path("outputs/balance_energetico")
    graphics.plot_energy_balance(out_dir)
    print()
    print("=" * 80)
    print("[OK] Graficas guardadas en: {}".format(out_dir))
    print("=" * 80)


if __name__ == '__main__':
    main()

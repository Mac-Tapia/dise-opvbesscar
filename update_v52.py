#!/usr/bin/env python
"""Script para actualizar archivos a valores v5.2."""

import re
from pathlib import Path

def update_file(filepath: Path, replacements: list) -> int:
    """Actualizar un archivo con reemplazos."""
    if not filepath.exists():
        print(f'[SKIP FILE] {filepath} not found')
        return 0
        
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    count = 0
    for old, new in replacements:
        if old in content:
            content = content.replace(old, new)
            count += 1
    
    if count > 0:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f'[OK] {filepath.name}: {count} replacements')
    else:
        print(f'[SKIP] {filepath.name}: no matches')
    
    return count

def main():
    """Actualizar todos los archivos con valores v5.2."""
    
    # Reemplazos comunes
    common_replacements = [
        # Sockets
        ('128 sockets', '38 sockets'),
        ('128 socket', '38 socket'),
        ('128 SOCKETS', '38 SOCKETS'),
        ('128 SOCKET', '38 SOCKET'),
        ('128 columnas', '38 columnas'),
        ('128 columns', '38 columns'),
        ('112 motos', '30 motos'),
        ('16 mototaxis', '8 mototaxis'),
        ('112 moto', '30 moto'),
        ('16 mototaxi', '8 mototaxi'),
        # Chargers
        ('32 chargers', '19 chargers'),
        ('32 charger', '19 charger'),
        ('32 cargadores', '19 cargadores'),
        ('32 units', '19 units'),
        ('32 físicos', '19 físicos'),
        ('4 sockets per charger', '2 sockets per charger'),
        ('4 sockets/cargador', '2 sockets/cargador'),
        ('× 4 sockets', 'x 2 sockets'),
        ('x 4 sockets', 'x 2 sockets'),
        ('* 4 sockets', '* 2 sockets'),
        ('× 4 tomas', 'x 2 tomas'),
        ('x 4 tomas', 'x 2 tomas'),
        ('32 × 4 = 128', '19 × 2 = 38'),
        ('32 x 4 = 128', '19 x 2 = 38'),
        # Ranges
        ('range(128)', 'range(38)'),
        ('range(112)', 'range(30)'),
        ('range(16)', 'range(8)'),
        # Specific values
        ('8760 hours × 128', '8760 hours x 38'),
        ('8,760 hours × 128', '8,760 hours x 38'),
        ('8760 × 128', '8760 x 38'),
        ('8,760 × 128', '8,760 x 38'),
        ('socket_127', 'socket_037'),
        ('charger_mall_128', 'charger_mall_38'),
        ('(8760, 128)', '(8760, 38)'),
        # Distribution
        ('112 + 16', '30 + 8'),
        ('(112 motos + 16 mototaxis)', '(30 motos + 8 mototaxis v5.2)'),
        ('112 motos + 16 mototaxis', '30 motos + 8 mototaxis'),
        ('28 motos + 4 mototaxis', '30 motos + 8 mototaxis'),
        # Power
        ('2.5 kWh', '4.6 kWh'),  # moto battery
        ('4.5 kWh', '7.4 kWh'),  # mototaxi battery
        ('2.0 kW', '7.4 kW'),    # moto power
        ('3.0 kW', '7.4 kW'),    # mototaxi power
        # Dataset specific
        ('charger_simulation_128', 'charger_simulation_038'),
        ('charger_simulation_001.csv through charger_simulation_128.csv', 
         'charger_simulation_001.csv through charger_simulation_038.csv'),
        ('total_sockets = 128', 'total_sockets = 38'),
        ('slice(229, 357)', 'slice(229, 267)'),  # 229 + 38 = 267
        # Documentation
        ('50.0% de 128 sockets', '50.0% de 38 sockets'),
        ('% de 128 sockets', '% de 38 sockets'),
        ('109 / 128 sockets', '35 / 38 sockets'),
        ('no 23', 'v5.2 actualizado'),
        # Additional patterns
        ('128 tomas', '38 tomas'),
        ('32 cargadores × 4 tomas', '19 cargadores x 2 tomas'),
        ('32 chargers × 4 sockets', '19 chargers x 2 sockets'),
        ('32 chargers x 4 sockets', '19 chargers x 2 sockets'),
        ('= 128 tomas', '= 38 tomas'),
        ('n_chargers: int = 32', 'n_chargers: int = 19'),
        ('32 chargers físicos', '19 chargers físicos'),
        ('(32 chargers × 4 sockets)', '(19 chargers x 2 sockets)'),
        ('(32 chargers x 4 sockets)', '(19 chargers x 2 sockets)'),
        ('128 simultáneos', '38 simultáneos'),
        ('32 CARGADORES', '19 CARGADORES'),
        ('Todos los 32 cargadores', 'Todos los 19 cargadores'),
        ('28 motos + 4 taxis', '30 motos + 8 mototaxis'),
        ('(28 motos + 4 mototaxis)', '(30 motos + 8 mototaxis)'),
        ('112 que esperas', '30 que esperas'),
        ('16 que esperas', '8 que esperas'),
        # Action/Observation dimensions (128 chargers -> 38 sockets)
        ('129-dim', '39-dim'),       # 1 BESS + 38 sockets = 39
        ('129 acciones', '39 acciones'),
        ('(129,)', '(39,)'),
        ('action[1:129]', 'action[1:39]'),
        ('1 BESS + 128 chargers', '1 BESS + 38 sockets'),
        ('1 BESS + 128 cargadores', '1 BESS + 38 tomas'),
        ('394-dim', '124-dim'),     # adjusted observation
        ('(394,)', '(124,)'),
        ('128 charger', '38 socket'),
        ('128 cargador', '38 toma'),
        # Specific patterns
        ('0-128 sockets', '0-38 sockets'),
        ('128 chargers × 3', '38 sockets × 3'),
        ('128 chargers x 3', '38 sockets x 3'),
        ('128 chargers', '38 sockets'),
        ('128 cargadores', '38 tomas'),
        # File references
        ('charger_simulation_XXX.csv', 'charger_simulation_0XX.csv'),
        ('128 charger_simulation_XXX', '38 charger_simulation_0XX'),
        ('128 charger_simulation', '38 charger_simulation'),
        ('128 files', '38 files'),
        ('128 archivos', '38 archivos'),
        # Additional patterns
        ('sockets_per_charger  # 128', 'sockets_per_charger  # 38'),
        ('Dataset validated (128 chargers', 'Dataset validated (38 sockets v5.2'),
        ('Dataset validated: 128 chargers', 'Dataset validated: 38 sockets v5.2'),
        ('Dataset validation (128 chargers)', 'Dataset validation (38 sockets v5.2)'),
        ('128 chargers controllable', '38 sockets controllable'),
    ]
    
    files_to_update = [
        'train_a2c_multiobjetivo.py',
        'train_ppo_multiobjetivo.py',
        'generar_chargers_ev_dataset_v3.py',
        'generar_chargers_ev_dataset_v2.py',
        'scripts/verify_environment_timesteps.py',
        'VALIDACION_DATASET_BUILDER.md',
        'src/citylearnv2/progress/metrics_extractor.py',
        'src/citylearnv2/progress/fixed_schedule.py',
        'src/dimensionamiento/oe2/disenocargadoresev/run/run_chargers_real.py',
        'src/dimensionamiento/oe2/disenocargadoresev/run/run_chargers_real_fixed.py',
        'src/dimensionamiento/oe2/disenobess/generate_bess_dataset_2024.py',
        'src/dimensionamiento/oe2/disenobess/bess.py',
        'src/citylearnv2/dataset_builder/dataset_builder.py',
        # Documentation
        'docs/VALIDACION_CO2_CALCULOS_2026-02-04.md',
        'docs/VALIDACION_ARQUITECTURA_PROFESIONAL_2026-02-07.md',
        'docs/SINCRONIZACION_METRICAS_CITYLEARN_V2_2026-02-07.md',
        'docs/REWARD_WEIGHTS_AND_METRICS_CITYLEARN_V2_2026-02-07.md',
        'docs/RESUMEN_VALIDACION_CO2_2026-02-04.md',
        'docs/RESUMEN_EJECUTIVO_VALIDACION_2026-02-07.md',
        'docs/QUICK_REFERENCE.md',
        'docs/LOGGING_STRUCTURE_COMPLETE_2026-02-07.md',
        'docs/EV_UTILIZATION_BONUS_INTEGRATION.md',
        'docs/ESCENARIOS_PREDEFINIDOS_VALIDACION.md',
        'docs/CO2_VALUES_CODE_LOCATIONS.md',
        'docs/ADVANTAGE_FUNCTION_INTEGRATION_PPO_A2C.md',
        'docs/A2C_VELOCIDAD_CORRECTA_2026-02-07.md',
        'src/citylearnv2/rewards/rewards.py',
        # Additional found files
        'generar_chargers_ev_dataset.py',
        'src/agents/rbc.py',
        'RESUMEN_VERIFICACION_IQUITOS_EV_MALL.md',
        'scripts/run_oe3_build_dataset.py',
        'RESUMEN_VALIDACION_BESS_v3.py',
        'RESUMEN_FINAL_DATASET_EV_V3.md',
        'DATASET_EV_COMPLETADO.md',
        'DATASET_EV_V3_SIMULACION_ESTOCASTICA.md',
        'RESUMEN_FINAL_AUDITORIA_dataset_builder.md',
        'RESUMEN_FINAL_CONSOLIDADO_AUDITORIA.md',
        # Balance and core code
        'src/dimensionamiento/oe2/balance_energetico/balance.py',
        'data/oe2/Generacionsolar/README.md',
        'data/oe2/bess/generate_charger_hourly.py',
        'cleanup_simple.py',
        'AUDITORIA_ARCHIVOS_IQUITOS_EV_MALL.md',
        'README.md',
        'REPORTE_SESION_TRABAJO_2026-02-09.md',
        # Docs
        'docs/A2C_PARAMETROS_IMPLEMENTACION_2026-02-07.md',
        'docs/audit_archive/README.md',
        'docs/audit_archive/auditoria_fase3/VERIFICACION_SAC_COMPLETA_2026_02_01.md',
        'docs/audit_archive/auditoria_fase3/VERIFICACION_FINAL_COMPLETITUD_20260201.md',
        'docs/audit_archive/auditoria_fase3/VERIFICACION_CONTROL_AGENTE_128_CHARGERS_BESS_FINAL.md',
        'docs/audit_archive/auditoria_fase3/RESUMEN_VISUAL_FINAL_AUDITORIA.md',
        'docs/audit_archive/auditoria_fase3/RESUMEN_FINAL_AUDITORIA_PPO_A2C.md',
        'docs/audit_archive/auditoria_fase3/RESUMEN_EJECUTIVO_SAC.md',
        'docs/audit_archive/auditoria_fase3/RESUMEN_EJECUTIVO_AUDITORIA_FASE3.md',
        # Round 4
        'docs/A2C_CONFIGURACION_REAL_2026-02-07.md',
        'docs/A2C_TECHNICAL_DATA_VERIFICATION_STATUS.md',
        'docs/DYNAMIC_EV_MODEL.md',
        'docs/ESCENARIOS_PREDEFINIDOS_RESUMEN.txt',
        'docs/guides/A2C_PRODUCTION_PIPELINE.md',
        'docs/CALCULO_CARGA_VEHICULOS_CO2_ACUMULADO_ANUAL_2026-02-07.md',
        'docs/guides/SAC_PRODUCTION_PIPELINE.md',
        'docs/audit_archive/auditoria_fase3/RESUMEN_DEFINITIVO_AUDITORIA_COMPLETADA.md',
        'docs/audit_archive/auditoria_fase3/RESUMEN_COMPLETO_LIMPIEZA_2026_02_01.md',
        'docs/audit_archive/auditoria_fase3/QUICK_REFERENCE_SAC_VERIFIED.md',
        'docs/audit_archive/auditoria_fase3/QUICK_REFERENCE_AUDITORIA_FINAL.md',
        'docs/audit_archive/auditoria_fase3/RESPUESTA_AGENTE_CONTROL_129.md',
        # Round 5
        'src/dimensionamiento/oe2/balance_energetico/README.md',
        'src/dimensionamiento/oe2/balance_energetico/run_analysis.py',
        'src/citylearnv2/progress/build_citylearnv2_with_integration.py',
        'src/citylearnv2/metric/schema_validator.py',
        'show_bess_summary.py',
        # Round 6 - Reference docs
        'docs/_reference/VALIDACION_SINCRONIZACION_COMPLETA_2026_02_02.md',
        'docs/_reference/MAPEO_TU_PEDIDO_vs_IMPLEMENTACION_2026_02_02.md',
        'docs/_reference/DIAGNOSTICO_TRAINING_2026_02_02.md',
        'docs/_reference/ARQUITECTURA_VALIDACION_COMPLETA_2026_02_02.md',
        'docs/_reference/CO2_3SOURCES_BREAKDOWN_2026_02_02.md',
        'docs/_reference/AGENTES_3VECTORES_LISTOS_2026_02_02.md',
        'docs/_reference/00_SIGUIENTE_PASO_ENTRENAMIENTO_2026_02_02.md',
        'docs/VALIDACION_BESS_DATASET_PPO_TRAINING.md',
        'docs/README.md',
        'DATASET_EV_V3_SIMULACION_ESTOCASTICA.md',
        'RESUMEN_FINAL_DATASET_EV_V3.md',
        # Round 7
        'docs/PRODUCTION_READINESS_SESSION3.md',
    ]
    
    total = 0
    for file in files_to_update:
        filepath = Path(file)
        total += update_file(filepath, common_replacements)
    
    print(f'\n[TOTAL] {total} replacements across all files')

if __name__ == '__main__':
    main()

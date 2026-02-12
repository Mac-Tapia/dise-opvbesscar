#!/usr/bin/env python
"""Script para actualizar archivos de CÓDIGO con valores v5.2."""

from pathlib import Path
import re

def update_file_regex(filepath: Path, patterns: list) -> int:
    """Actualizar archivo con regex patterns."""
    if not filepath.exists():
        print(f'[SKIP FILE] {filepath}')
        return 0
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    count = 0
    for pattern, replacement in patterns:
        matches = len(re.findall(pattern, content))
        if matches > 0:
            content = re.sub(pattern, replacement, content)
            count += matches
    
    if count > 0:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f'[OK] {filepath.name}: {count} replacements')
    
    return count

def main():
    """Actualizar archivos de código con valores v5.2."""
    
    # Patterns específicos para código (NO tocar net_arch=[128, 128] de redes neuronales)
    code_patterns = [
        # Rangos de índices
        (r'socket_idx >= 112', 'socket_idx >= 30'),
        (r'socket_idx - 112', 'socket_idx - 30'),
        (r'range\(112,\s*128\)', 'range(30, 38)'),
        (r'sockets\[:112\]', 'sockets[:30]'),
        (r'sockets\[112:\]', 'sockets[30:]'),
        (r'charger_demand\[:112\]', 'charger_demand[:30]'),
        (r'charger_demand\[112:\]', 'charger_demand[30:]'),
        (r'charger_setpoints\[:112\]', 'charger_setpoints[:30]'),
        (r'charger_setpoints\[112:\]', 'charger_setpoints[30:]'),
        (r'socket_cols\[:112\]', 'socket_cols[:30]'),
        (r'socket_cols\[112:\]', 'socket_cols[30:]'),
        
        # Validaciones de shape
        (r'shape\[1\] == 128', 'shape[1] == 38'),
        (r'\.shape\[1\] == 128', '.shape[1] == 38'),
        (r'esperado 8,760 × 128', 'esperado 8,760 x 38'),
        (r'esperado 8,760 x 128', 'esperado 8,760 x 38'),
        (r'expected 8760×128', 'expected 8760x38'),
        
        # Full arrays
        (r'np\.full\(128,', 'np.full(38,'),
        (r'np\.ones\(128\)', 'np.ones(38)'),
        (r'np\.zeros\(128\)', 'np.zeros(38)'),
        
        # Totales y contadores
        (r'NUM_CHARGERS = 128', 'NUM_CHARGERS = 38'),
        (r'total_sockets == 128', 'total_sockets == 38'),
        (r'chargers == 32', 'chargers == 19'),
        (r'len\(chargers\) == 32', 'len(chargers) == 19'),
        (r'len\(chargers_to_update\) != 128', 'len(chargers_to_update) != 38'),
        (r'128 simulation files', '38 simulation files'),
        
        # Documentación en código
        (r'sockets 0-111 \(112', 'sockets 0-29 (30'),
        (r'sockets 112-127 \(16', 'sockets 30-37 (8'),
        (r'Motos: sockets 0-111', 'Motos: sockets 0-29'),
        (r'Mototaxis: sockets 112-127', 'Mototaxis: sockets 30-37'),
        (r'112 sockets motos', '30 sockets motos'),
        (r'16 sockets mototaxis', '8 sockets mototaxis'),
        
        # División 128 paths
        (r'/ 128\.0', '/ 38.0'),
        (r'/128\.0', '/38.0'),
        (r'/ 128\)', '/ 38)'),
        (r'/128\)', '/38)'),
        (r'Promedio por socket: \{total_ev_demand_kwh/128', 'Promedio por socket: {total_ev_demand_kwh/38'),
        
        # Mensajes y logging
        (r'128 charger_simulation', '38 charger_simulation'),
        (r'to 128\.csv', 'to 038.csv'),
        (r'128 CSV', '38 CSV'),
        (r'128/128', '38/38'),
        (r'128 \(charger_simulation', '38 (charger_simulation'),
        
        # Power calculations (cuidado con net_arch)
        (r'2\.0 \* 112 \* 2\.0', '2.0 * 30 * 7.4'),  # motos power
        (r'112 sockets', '30 sockets'),
        (r'16 sockets', '8 sockets'),
        
        # Específicos del archivo generar_chargers_ev_dataset
        (r'112 \+ \(\(charger_id', '30 + ((charger_id'),
        (r'- 28\) \* 4', '- 15) * 2'),  # mototaxi offset
        (r'28 cargadores de motos', '15 cargadores de motos'),
        (r'28 cargadores MOTOS', '15 cargadores MOTOS'),
        (r'4 cargadores de mototaxis', '4 cargadores de mototaxis'),  # mantener 4
        (r'índices 0-27', 'índices 0-14'),
        (r'índices 28-31', 'índices 15-18'),
        (r'charger_id - 28', 'charger_id - 15'),
        
        # Documentación texto
        (r'MOTOS \(112\)', 'MOTOS (30)'),
        (r'MOTOTAXIS \(16\)', 'MOTOTAXIS (8)'),
        (r'motos_demand = float\(np\.sum\(charger_demand\[:112\]', 'motos_demand = float(np.sum(charger_demand[:30]'),
        (r'mototaxis_demand = float\(np\.sum\(charger_demand\[112:\]', 'mototaxis_demand = float(np.sum(charger_demand[30:]'),
    ]
    
    files_to_update = [
        'generar_chargers_ev_dataset.py',
        'generar_chargers_ev_dataset_v3.py',
        'resumen_datasets_ev.py',
        'resumen_datasets_ev_completo.py',
        'train_sac_multiobjetivo.py',
        'RESUMEN_VALIDACION_BESS_v3.py',
        'run_bess_sizing_simple.py',
        'scripts/verify_logging_completeness.py',
        'scripts/verify_architecture_episodes.py',
        'scripts/verify_a2c_real_data.py',
        'scripts/verify_5_datasets.py',
        'scripts/run_oe3_build_dataset.py',
        'src/citylearnv2/dataset_builder/dataset_builder.py',
        'src/dimensionamiento/oe2/disenobess/bess.py',
    ]
    
    total = 0
    for file in files_to_update:
        filepath = Path(file)
        total += update_file_regex(filepath, code_patterns)
    
    print(f'\n[TOTAL] {total} code replacements')

if __name__ == '__main__':
    main()

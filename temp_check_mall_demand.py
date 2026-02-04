import pandas as pd
import os

print('='*80)
print('[OE2 MALL DEMAND - 15 MIN vs HOURLY] Comparación de resoluciones')
print('='*80)

# 1. Cargar datos horarios (8,760 filas)
print('\n[1] Datos HORARIOS (anual):')
hourly_path = 'data/interim/oe2/demandamallkwh/demanda_mall_horaria_anual.csv'
if os.path.exists(hourly_path):
    try:
        df_hourly = pd.read_csv(hourly_path)
        print(f'   ✓ Cargado: {hourly_path}')
        print(f'   Filas: {len(df_hourly):,}')
        print(f'   Columnas: {list(df_hourly.columns)}')

        # Buscar columna de demanda
        demand_cols = [c for c in df_hourly.columns if 'kwh' in c.lower() or 'kw' in c.lower()]
        if demand_cols:
            col = demand_cols[0]
            total_hourly = df_hourly[col].sum()
            print(f'   Demanda total: {total_hourly:,.0f} kWh/año')
            print(f'   Primeras 5 valores: {df_hourly[col].head().values}')
    except Exception as e:
        print(f'   ✗ Error: {e}')
else:
    print(f'   ✗ No existe: {hourly_path}')

# 2. Cargar datos 15-minuto (si existen)
print('\n[2] Datos 15-MINUTO (si existen):')
paths_15min = [
    'data/interim/oe2/demandamallkwh/demandamallkwh.csv',
    'data/interim/oe2/demandamall/demanda_mall_kwh.csv',
    'data/interim/oe2/demandamallkwh/demanda_mall_kwh.csv',
]

for path_15 in paths_15min:
    if os.path.exists(path_15):
        print(f'\n   Encontrado: {path_15}')
        try:
            # Intentar con diferentes separadores
            for sep in [',', ';']:
                try:
                    df_15 = pd.read_csv(path_15, sep=sep)
                    if len(df_15) > 100:  # Válido si tiene muchas filas
                        print(f'   ✓ Cargado con separador: {repr(sep)}')
                        print(f'   Filas: {len(df_15):,}')
                        print(f'   Columnas: {list(df_15.columns)[:3]}')

                        # Detectar resolución
                        if len(df_15) == 52560:
                            print(f'   ⏱ Resolución: 15-MINUTO (365×24×4 = 52,560 filas)')
                        elif len(df_15) == 8760:
                            print(f'   ⏱ Resolución: HORARIO (365×24 = 8,760 filas)')
                        else:
                            print(f'   ⏱ Resolución desconocida ({len(df_15):,} filas)')

                        # Calcular total anual
                        demand_cols = [c for c in df_15.columns if 'kwh' in c.lower() or 'kw' in c.lower() or 'demanda' in c.lower() or len(df_15.columns) <= 2]
                        if demand_cols:
                            col = demand_cols[0] if demand_cols else df_15.columns[-1]
                            try:
                                df_15[col] = pd.to_numeric(df_15[col], errors='coerce')
                                total_15 = df_15[col].sum()
                                print(f'   Demanda total: {total_15:,.0f} kWh/año')
                                print(f'   Primeras 5 valores ({col}): {df_15[col].head().values}')
                            except:
                                pass
                        break
                except Exception as e_sep:
                    pass
        except Exception as e:
            print(f'   ✗ Error al procesar: {type(e).__name__}')
    else:
        print(f'   ✗ No existe: {path_15}')

print('\n' + '='*80)
print('[CONCLUSIÓN] Si existen ambos, comparar totales:')
print('  • Si totales ≈ iguales → mismos datos, diferente resolución')
print('  • Si totales muy diferentes → datos independientes (15min es subset/muestra)')
print('='*80)

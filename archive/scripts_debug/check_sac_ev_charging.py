import pandas as pd

df = pd.read_csv('outputs/sac_training/timeseries_sac.csv')

print(f"""
EV CHARGING STATISTICS (SAC):
  Min: {df['ev_charging_kw'].min()}
  Max: {df['ev_charging_kw'].max()}
  Mean: {df['ev_charging_kw'].mean():.4f}
  Sum: {df['ev_charging_kw'].sum():.0f}
  Non-zero rows: {(df['ev_charging_kw'] > 0).sum()} of {len(df)}
  Unique values: {df['ev_charging_kw'].nunique()}
""")

# Check grid import and solar too
print(f"""
GRID IMPORT STATISTICS:
  Min: {df['grid_import_kw'].min():.0f}
  Max: {df['grid_import_kw'].max():.0f}
  Mean: {df['grid_import_kw'].mean():.0f}
  Sum: {df['grid_import_kw'].sum():.0f}

SOLAR GENERATION STATISTICS:
  Min: {df['solar_kw'].min():.0f}
  Max: {df['solar_kw'].max():.0f}
  Mean: {df['solar_kw'].mean():.0f}
  Sum: {df['solar_kw'].sum():.0f}

BESS POWER STATISTICS:
  Min: {df['bess_power_kw'].min():.0f}
  Max: {df['bess_power_kw'].max():.0f}
  Mean: {df['bess_power_kw'].mean():.0f}
  Sum: {df['bess_power_kw'].sum():.0f}
""")

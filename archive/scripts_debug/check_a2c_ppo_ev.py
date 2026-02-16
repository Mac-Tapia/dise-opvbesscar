import pandas as pd

for agent in ['A2C', 'PPO']:
    try:
        df = pd.read_csv(f'outputs/{agent.lower()}_training/timeseries_{agent.lower()}.csv')
        print(f'\n{agent} CHARGING/BESS:')
        if 'ev_charging_kw' in df.columns:
            print(f'  ev_charging_kw: min={df["ev_charging_kw"].min():.0f}, max={df["ev_charging_kw"].max():.0f}, mean={df["ev_charging_kw"].mean():.0f}')
        else:
            print(f'  ev_charging_kw: NOT FOUND')
        if 'bess_power_kw' in df.columns:
            print(f'  bess_power_kw: min={df["bess_power_kw"].min():.0f}, max={df["bess_power_kw"].max():.0f}, mean={df["bess_power_kw"].mean():.0f}')
        else:
            print(f'  bess_power_kw: NOT FOUND')
        print(f'  Columns: {list(df.columns)}')
    except Exception as e:
        print(f'\n{agent}: ERROR - {e}')

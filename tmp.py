import pandas as pd
from pathlib import Path
path=Path('analyses/oe3/co2_control_vs_uncontrolled.csv')
df=pd.read_csv(path)
print(df.columns.tolist())
print(df.iloc[0].to_dict())


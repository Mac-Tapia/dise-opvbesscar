import pandas as pd
from pathlib import Path
path=Path('analyses/oe3/co2_comparison_table.csv')
df=pd.read_csv(path)
print(df.columns.tolist())
print(df.to_string(index=False))


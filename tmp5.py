import pandas as pd
from pathlib import Path
path=Path('analyses/oe3/co2_comparison_table.csv')
df=pd.read_csv(path)
print(df.head())
print(df[df['label'].str.contains('control', case=False, na=False)])


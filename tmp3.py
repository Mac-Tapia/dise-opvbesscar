import pandas as pd
from pathlib import Path
path=Path('analyses/oe3/co2_breakdown.csv')
df=pd.read_csv(path)
print(df.to_string(index=False))


import pandas as pd

df = pd.read_csv('data/oe2/bess/bess_ano_2024.csv')
print("Columnas del CSV:")
for i, col in enumerate(df.columns, 1):
    print(f"{i:2d}. {col}")

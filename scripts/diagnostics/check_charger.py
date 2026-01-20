import pandas as pd

# Check what the charger CSV looks like
df = pd.read_csv('data/processed/citylearn/iquitos_ev_mall/MOTO_CH_001.csv')
print("Columns:", df.columns.tolist())
print("Shape:", df.shape)
print("\nFirst 5 rows:")
print(df.head(5))
print("\nLast 5 rows:")
print(df.tail(5))

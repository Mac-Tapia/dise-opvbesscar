import pandas as pd
import os

# Check one charger CSV to see what's there
charger_file = 'data/processed/citylearn/iquitos_ev_mall/MOTO_CH_001.csv'
df = pd.read_csv(charger_file)

print("Charger CSV Info:")
print(f"Columns: {df.columns.tolist()}")
print(f"Shape: {df.shape}")

# Check if it has unique values per column
for col in df.columns:
    unique_vals = df[col].unique()[:5]
    print(f"{col}: {unique_vals}")

# Check template to see what columns it should have
template_dir = 'data/raw/citylearn_templates/citylearn_challenge_2022_phase_all_plus_evs'
template_chargers = []
for f in os.listdir(template_dir):
    if 'ELEC' in f and f.endswith('.csv'):
        template_chargers.append(f)
        break

if template_chargers:
    template_file = os.path.join(template_dir, template_chargers[0])
    print(f"\n\nTemplate charger file: {template_chargers[0]}")
    try:
        df_template = pd.read_csv(template_file)
        print(f"Template columns: {df_template.columns.tolist()}")
        print(f"Template shape: {df_template.shape}")
        print("\nTemplate first 3 rows:")
        print(df_template.head(3))
    except Exception as e:
        print(f"Could not read template: {e}")

"""Analyze real chargers data to extract motos and mototaxis specifications."""
import pandas as pd
import numpy as np

# Read the chargers file
print("Reading chargers CSV (large file, may take a moment)...")
df = pd.read_csv('data/oe2/chargers/chargers_ev_ano_2024_v3.csv')

# Find all socket columns
socket_cols = [col for col in df.columns if 'socket_' in col and 'vehicle_type' in col]
print(f"\n✓ Total sockets found: {len(socket_cols)}")

# Count vehicle types per socket
socket_vehicle_types = {}
for col in socket_cols:
    socket_num = int(col.split('_')[1])
    # Get the most common vehicle type in this socket
    vtype_vals = df[col].dropna()
    if len(vtype_vals) > 0:
        most_common = vtype_vals.value_counts().index[0]
        socket_vehicle_types[socket_num] = most_common

print(f"\n✓ Vehicle type per socket:")
motos_count = 0
taxis_count = 0
for socket_num in sorted(socket_vehicle_types.keys()):
    vtype = socket_vehicle_types[socket_num]
    print(f"  Socket {socket_num:02d}: {vtype}")
    if 'moto' in vtype.lower() and 'taxi' not in vtype.lower():
        motos_count += 1
    elif 'taxi' in vtype.lower():
        taxis_count += 1

print(f"\n📊 SUMMARY:")
print(f"  Motos sockets: {motos_count}")
print(f"  Taxi sockets: {taxis_count}")
print(f"  Total sockets: {motos_count + taxis_count}")

# Get battery size and daily vehicle counts
print(f"\n✓ Battery sizes and vehicle counts:")
for vtype_name, vtype_key in [('MOTO', 'MOTO'), ('MOTOTAXI', 'MOTOTAXI')]:
    batt_sizes = []
    daily_vehicle_totals = []
    
    # Get sockets for this vehicle type
    sockets_for_type = [s for s, t in socket_vehicle_types.items() if vtype_key in t]
    socket_count = len(sockets_for_type)
    
    # Get unique dates to calculate daily totals
    df['date'] = pd.to_datetime(df['datetime']).dt.date
    unique_dates = df['date'].unique()
    
    for socket_num in sockets_for_type:
        batt_col = f'socket_{socket_num:03d}_battery_kwh'
        vcount_col = f'socket_{socket_num:03d}_vehicle_count'
        
        if batt_col in df.columns:
            batt = df[batt_col].dropna()
            if len(batt) > 0:
                batt_sizes.append(batt.iloc[0])
        
        if vcount_col in df.columns:
            # Sum vehicle count per day and get mean across days
            daily_totals = df.groupby('date')[vcount_col].sum()
            if len(daily_totals) > 0:
                daily_vehicle_totals.append(daily_totals.mean())
    
    if batt_sizes:
        avg_batt = np.mean(batt_sizes)
        avg_vehicles_per_day = np.mean(daily_vehicle_totals) if daily_vehicle_totals else 0
        print(f"  {vtype_name}:")
        print(f"    Avg battery: {avg_batt:.2f} kWh/vehicle")
        print(f"    Avg total per day: {avg_vehicles_per_day:.0f} vehicles/day (all {socket_count} sockets)")
        print(f"    Per socket/day: {avg_vehicles_per_day/socket_count:.2f} vehicles/socket/day")
        print(f"    Socket count: {socket_count}")

# Get daily demand
print(f"\n✓ Daily EV demand analysis:")
power_cols = [col for col in df.columns if 'charging_power_kw' in col]
if power_cols:
    total_power_per_hour = df[[col for col in power_cols if col in df.columns]].sum(axis=1)
    print(f"  Min demand: {total_power_per_hour.min():.1f} kW")
    print(f"  Max demand: {total_power_per_hour.max():.1f} kW")
    print(f"  Mean demand: {total_power_per_hour.mean():.1f} kW")

print("\nAnalysis complete!")

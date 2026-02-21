#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Diagnóstico detallado Día 7, Hora 11 (índice 155)"""
import pandas as pd

bess_data = pd.read_csv('data/interim/oe2/bess/bess_ano_2024.csv')

# Hora 11 del Día 7 = global index 155
# (Día 7 comienza en index 144, +11 horas = 155)

print("=" * 100)
print("HORA 11 DEL DÍA 7 (Index Global 155) - DIAGNÓSTICO DETALLADO")
print("=" * 100)

row = bess_data.iloc[155]
print(f"\nTODAS LAS COLUMNAS:")
for col in bess_data.columns:
    val = row[col]
    print(f"  {col:35s}: {val}")

print("\n" + "=" * 100)
print("VALIDACIÓN: ¿HAY CARGA Y DESCARGA SIMULTÁNEA?")
print("=" * 100)

pv_to_bess = row['pv_to_bess_kwh']
bess_to_ev = row['bess_to_ev_kwh']
bess_to_mall = row['bess_to_mall_kwh']

print(f"\nCARGA:       pv_to_bess_kwh = {pv_to_bess:7.2f} kWh")
print(f"DESCARGA EV: bess_to_ev_kwh  = {bess_to_ev:7.2f} kWh")
print(f"DESCARGA ML: bess_to_mall_kwh= {bess_to_mall:7.2f} kWh")

total_discharge = bess_to_ev + bess_to_mall
print(f"\nDESCAR TOTAL:                   {total_discharge:7.2f} kWh")

if pv_to_bess > 0.1 and (bess_to_ev > 0.1 or bess_to_mall > 0.1):
    print(f"\n❌ PROBLEMA: CARGA Y DESCARGA SIMULTÁNEA")
    print(f"   Debería ser mutuamente excluyente en la misma hora")
else:
    print(f"\n✓ OK: No hay carga y descarga simultánea")

print(f"\nTIMESTAMP: {row['datetime']}")
print(f"HORA LOCAL: {pd.to_datetime(row['datetime']).hour}:00")
print(f"TARIFA PERIOD: {row['tariff_period']}")
print(f"MODE: {row['bess_mode']}")
print(f"ACTION: {row['bess_action_kwh']} kWh")

# Verifica si es HP o HFP
if row['tariff_period'] == 'HP':
    print(f"\n>> PERÍODO HORA PUNTA (HP): Debería DESCARGAR, NO CARGAR")
else:
    print(f"\n>> PERÍODO FUERA PUNTA (HFP): Debería CARGAR O IDLE, puede descargar a EV primero")

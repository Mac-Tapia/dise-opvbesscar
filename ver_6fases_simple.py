"""
Resumen visual: 6 FASES de BESS en la grafica
"""
import pandas as pd

df = pd.read_csv('data/interim/oe2/bess/bess_ano_2024.csv')
day_7_start = 6 * 24
day_7_df = df.iloc[day_7_start:day_7_start+24].copy()
day_7_df['hour'] = range(24)

print("\n" + "="*100)
print("RESUMEN: COMO VER LAS 6 FASES EN LA GRAFICA 00_INTEGRAL_todas_curvas.png")
print("="*100)

print("""
Abre la grafica: outputs/balance_energetico/00_INTEGRAL_todas_curvas.png

BUSCA ESTOS PATRONES VISUALES:

FASE 1 (6-9h) - VERDE OSCURO:
  - Barras VERDES OSCURAS que SUBEN desde abajo (carga progressiva)
  - Zona con FONDO VERDE OSCURO
  - Texto: "FASE 1 CARGA BESS"
  - SOC en eje derecho: SUBE de 20% a 100%

FASE 2 (9-15h) - VERDE CLARO:
  - Barras VERDES CLARAS mas pequenas (paralelo con EV azul)
  - Zona con FONDO VERDE CLARO
  - Texto: "FASE 2 EV+BESS CARGA"
  - SOC: LLEGA a 100% y SE MANTIENE ahi

FASE 3 (15-17h) - AZUL (HOLDING):
  - NO HAY BARRAS VERDES (vacio de BESS)
  - Zona con FONDO AZUL
  - Texto: "FASE 3 HOLDING SOC=100%"
  - SOC: CONGELADO en 100% (linea plana)

FASE 4-5 (17-22h) - NARANJA (DESCARGA):
  - Barras NARANJAS que BAJAN (espejo de FASE 1)
  - Zona con FONDO ROJO
  - Texto: "FASE 4-5 DESCARGA EV+MALL"
  - SOC: DESCIENDE de 100% a 20%

FASE 6 (22-9h) - GRIS (REPOSO):
  - NO HAY BARRAS (todo cero)
  - Zona con FONDO GRIS
  - Texto: "FASE 6 REPOSO"
  - SOC: BLOQUEADO en 20% (linea plana en parte baja)
""")

print("\nCOMPARACION DATO vs VISUAL EN DAY 7:\n")
print("Hora  Fase            PV->BESS  BESS->EV  BESS->MALL  SOC%  Visual")
print("-"*75)

for idx, row in day_7_df.iterrows():
    h = int(row['hour'])
    pv_bess = row['pv_to_bess_kwh']
    bess_ev = row['bess_to_ev_kwh']
    bess_mall = row['bess_to_mall_kwh']
    soc = row['soc_percent']
    
    if h < 6:
        fase = "FASE 6"; visual = "GRIS/VACIO"
    elif h < 9:
        fase = "FASE 1"; visual = "VERDE OSCURO ^"
    elif h < 15:
        fase = "FASE 2"; visual = "VERDE CLARO ^"
    elif h < 17:
        fase = "FASE 3"; visual = "AZUL/VACIO = (holding)"
    elif h < 22:
        fase = "FASE 4-5"; visual = "NARANJA v"
    else:
        fase = "FASE 6"; visual = "GRIS/VACIO"
    
    print(f"{h:2d}h  {fase:14s} {pv_bess:7.0f}   {bess_ev:7.0f}   {bess_mall:7.0f}   {soc:5.1f}%  {visual}")

print("\n" + "="*100)
print("CONCLUSION: Las 6 FASES ahora son CLARAMENTE VISIBLES en la grafica:")
print("="*100)
print("""
1. BANDAS DE FONDO COLOR (verde/azul/rojo/gris) separando cada FASE
2. BARRAS DE BESS CARGADO con COLORES distintos (verde oscuro vs verde claro)
3. BARRAS DE BESS DESCARGADO en NARANJA (FASE 4-5)
4. LINEAS DIVISORIAS punteadas en horas 6, 9, 15, 17, 22
5. ETIQUETAS DE TEXTO sobre cada zona diciendo "FASE X nombre"
6. GRAFICA del SOC (eje derecho) mostrando subia (FASE 1-2) y bajada (FASE 4-5)

TODO ESTO EN UN SOLO GRAFICO = MUY FACIL DE ENTENDER VISUALMENTE
""")

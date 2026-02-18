"""
Gráfica simple: Curva SOC BESS anual (datos reales del CSV)
"""
import pandas as pd
import numpy as np
from pathlib import Path
import matplotlib.pyplot as plt

# Cargar BESS
df = pd.read_csv("data/oe2/bess/bess_ano_2024.csv")

# Crear figura
fig, ax = plt.subplots(figsize=(16, 6))

# Graficar SOC
hours = np.arange(len(df))
ax.plot(hours, df['soc_percent'], linewidth=1.5, color='darkgreen', label='SOC BESS')

# Líneas de referencia
ax.axhline(y=100, color='green', linestyle='--', linewidth=1.5, alpha=0.7, label='100% (Máximo)')
ax.axhline(y=20, color='red', linestyle='--', linewidth=1.5, alpha=0.7, label='20% (Mínimo)')
ax.fill_between(hours, 20, 100, alpha=0.1, color='green', label='Rango Operacional')

# Formato
ax.set_xlabel('Hora del Año (0-8760)', fontsize=12, fontweight='bold')
ax.set_ylabel('SOC (%)', fontsize=12, fontweight='bold')
ax.set_title('Estado de Carga BESS - Año Completo 2024', fontsize=14, fontweight='bold')
ax.grid(True, alpha=0.3)
ax.legend(loc='lower left', fontsize=11)
ax.set_ylim(0, 110)

plt.tight_layout()
plt.savefig('reports/balance_energetico/curva_soc_bess_anual.png', dpi=150, bbox_inches='tight')
print("✅ Gráfica guardada: reports/balance_energetico/curva_soc_bess_anual.png")
plt.close()

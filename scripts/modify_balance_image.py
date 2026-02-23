#!/usr/bin/env python3
"""
Script para modificar 00_BALANCE_INTEGRADO_COMPLETO.png
Mueve la leyenda/texto del primer panel a la esquina superior derecha con fondo amarillo
"""
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
import numpy as np

# Ruta de la imagen
image_path = Path("outputs/balance_energetico/00_BALANCE_INTEGRADO_COMPLETO.png")

if not image_path.exists():
    print(f"❌ No se encontró la imagen en {image_path}")
    exit(1)

# Abrir imagen
img = Image.open(image_path)
width, height = img.size
print(f"📐 Tamaño de imagen original: {width} x {height} px")

# Crear objeto de dibujo
draw = ImageDraw.Draw(img, 'RGBA')

# Intentar usar una fuente del sistema, si no está disponible usar por defecto
try:
    # Intentar con tamaño grande
    font_big = ImageFont.truetype("arial.ttf", 20)
    font_medium = ImageFont.truetype("arial.ttf", 16)
    font_small = ImageFont.truetype("arial.ttf", 12)
except:
    try:
        font_big = ImageFont.truetype("C:\\Windows\\Fonts\\arial.ttf", 20)
        font_medium = ImageFont.truetype("C:\\Windows\\Fonts\\arial.ttf", 16)
        font_small = ImageFont.truetype("C:\\Windows\\Fonts\\arial.ttf", 12)
    except:
        font_big = ImageFont.load_default()
        font_medium = ImageFont.load_default()
        font_small = ImageFont.load_default()
        print("⚠️ Usando fuente por defecto (no está arial disponible)")

# Texto de la leyenda (tomado del primer panel de balance integrado)
legend_text = """
⚡ BALANCE INTEGRADO - DÍA REPRESENTATIVO
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
☀️  Generación Solar (PV): 4,050 kWp
🔋 BESS: 2,000 kWh / 400 kW (95% eficiencia)
🏪 Demanda MALL: 12,380 MWh/año (24h operativo)
🛵 Demanda EV: 408 MWh/año (9h-22h)
🌐 Red Pública: Respaldo (importación necesaria)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
6 FASES de Operación BESS:
  FASE 1: Carga Prioritaria (6-9h, verde oscuro)
  FASE 2: Carga + EV (9-15h, verde claro)
  FASE 3: Holding SOC=100% (15-17h, azul)
  FASE 4-5: Descarga + Peak Shaving (17-22h, naranja)
  FASE 6: Reposo SOC=20% (22-6h, gris)
"""

# Parámetros de la caja amarilla en esquina superior derecha
padding = 20
box_width = 520
box_height = 380
x_position = width - box_width - padding
y_position = padding

# Color amarillo (RGB)
yellow_color = (255, 255, 0, 180)  # RGBA con transparencia
text_color = (0, 0, 0, 255)  # Negro

# Dibujar rectángulo relleno amarillo (transparente)
draw.rectangle(
    [x_position, y_position, x_position + box_width, y_position + box_height],
    fill=yellow_color,
    outline=(255, 200, 0, 255),  # Borde naranja más oscuro
    width=3
)

# Dibujar texto línea por línea
lines = legend_text.strip().split('\n')
text_y = y_position + 15
line_height = 22

for line in lines:
    if line.startswith('━'):
        # Línea divisoria (saltar)
        text_y += 10
    elif line.startswith('⚡') or line.startswith('6'):
        # Títulos (fuente más grande, bold)
        draw.text((x_position + 10, text_y), line, fill=text_color, font=font_medium)
        text_y += line_height + 3
    elif line.strip().startswith('FASE'):
        # Fases (fuente pequeña, indentado)
        draw.text((x_position + 15, text_y), line.strip(), fill=text_color, font=font_small)
        text_y += line_height - 4
    else:
        # Contenido normal
        if line.strip():
            draw.text((x_position + 10, text_y), line, fill=text_color, font=font_small)
        text_y += line_height - 2

# Validar que no se salga del canvas
if text_y > height:
    print(f"⚠️ Advertencia: El texto puede no caber completamente ({text_y} > {height})")

# Guardar imagen modificada
output_path = Path("outputs/balance_energetico/00_BALANCE_INTEGRADO_COMPLETO_ACTUALIZADO.png")
output_path.parent.mkdir(parents=True, exist_ok=True)

img.save(output_path)
print(f"✅ Imagen modificada guardada en: {output_path}")
print(f"📊 Leyenda agregada a esquina superior derecha con fondo amarillo")
print(f"📐 Posición: x={x_position}, y={y_position}")
print(f"📦 Tamaño caja: {box_width} x {box_height} px")

from pathlib import Path

# Buscar todos los .png en el árbol
png_files = list(Path('.').rglob('*.png'))
print(f'Total PNG encontrados: {len(png_files)}')

# Mostrar ubicaciones únicas
locations = {}
for p in png_files:
    parent = str(p.parent)
    if parent not in locations:
        locations[parent] = []
    locations[parent].append(p.name)

print('\nUbicaciones con PNG:')
for loc in sorted(locations.keys()):
    files = locations[loc]
    print(f'  {loc}/ ({len(files)} archivos)')
    if 'integral' in files[0].lower() if files else False:
        for f in files[:16]:
            print(f'    ✓ {f}')

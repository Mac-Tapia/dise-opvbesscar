# CHECKLIST DE PUBLICACION - RAMA `smartcharger`

## Estado actual

- [x] Rama activa: `smartcharger`
- [x] README principal actualizado con la metodologia de investigacion del proyecto
- [x] Metodologia corregida a un solo diseno para todo el proyecto
- [x] DOCX vigente generado y guardado en `outputs/docx/`
- [x] Figuras vigentes disponibles en `outputs/docx/graficas/`
- [x] Reportes canonicos OE3 disponibles en `reports/oe3/`
- [x] Cambios publicados en GitHub en `origin/smartcharger`

## Documento Word vigente

| Archivo | Ruta |
|---|---|
| Informe tesis OE3 v12 | `outputs/docx/INFORME_OE3_SELECCION_AGENTE_RL_v12.docx` |

Este DOCX fue regenerado con:

```bash
python scripts/reporting/generar_informe_tesis_oe3.py
```

El documento incluye la metodologia corregida:

- Enfoque: cuantitativo
- Tipo: aplicada
- Nivel: explicativo-causal
- Diseno unico: cuasi-experimental por simulacion para todo el proyecto
- OE1, OE2 y OE3 como etapas del mismo diseno metodologico

## Archivos que deben quedar versionados

| Categoria | Ruta |
|---|---|
| README principal | `README.md` |
| Metodologia completa | `reports/metodologia/METODOLOGIA_INVESTIGACION_OE3.md` |
| Informe Word | `outputs/docx/INFORME_OE3_SELECCION_AGENTE_RL_v12.docx` |
| Figuras del informe | `outputs/docx/graficas/` |
| Estadistica OE3 | `outputs/estadistica_oe3/` |
| Comparativa canonica OE3 | `reports/oe3/AGENTES_RL_COMPARATIVA_CANONICA.md` |
| JSON canonico OE3 | `reports/oe3/agents_comparison_canonical.json` |
| CSV canonico OE3 | `reports/oe3/agents_comparison_canonical.csv` |

## Verificaciones realizadas

```bash
python -m py_compile scripts/reporting/generar_informe_tesis_oe3.py
python scripts/reporting/generar_informe_tesis_oe3.py
```

Ademas, se verifico que el DOCX contiene:

- `Diseno de investigacion del proyecto`
- `Diseno unico`
- `Cuasi-experimental por simulacion`
- `OE1, OE2 y OE3 son etapas del mismo diseno`
- `Infraestructura de carga inteligente`

## Nota

No crear una rama `tesis` para esta actualizacion. La instruccion vigente es trabajar
solo en la rama `smartcharger`.

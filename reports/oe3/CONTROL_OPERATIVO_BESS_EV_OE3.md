# OE3 — Control operativo BESS/EV/pico por hora del día

**Fecha:** 2026-05-31
**Episodios analizados:** A2C ep19 (mayor CO₂ evitado) | PPO ep49 (menor F2) | SAC ep33 (mejor SAC)

---

## A2C ep19

| Hora | Mall | HP | SOC medio | Grid (kWh) | Solar (kWh) | EV (kWh) | Patrón |
|---:|:---:|:---:|---:|---:|---:|---:|---|
| h00 | — | — | 0.93 | 2,081 | 111 | 76.7 | carga EV intensa |
| h01 | — | — | 0.87 | 2,114 | 0 | 81.9 | carga EV intensa |
| h02 | — | — | 0.83 | 2,114 | 0 | 86.4 | carga EV intensa |
| h03 | — | — | 0.77 | 2,074 | 0 | 82.4 | carga EV intensa |
| h04 | — | — | 0.72 | 1,912 | 0 | 49.1 | — |
| h05 | — | — | 0.68 | 1,148 | 0 | 17.4 | — |
| h06 | — | — | 0.67 | 620 | 0 | 4.1 | — |
| h07 | — | — | 0.54 | 291 | 0 | 0.0 | — |
| h08 | — | — | 0.43 | 320 | 0 | 0.0 | — |
| h09 | ABIERTO | — | 0.35 | 372 | 0 | 0.0 | — |
| h10 | ABIERTO | — | 0.30 | 431 | 0 | 0.0 | — |
| h11 | ABIERTO | — | 0.28 | 465 | 0 | 0.0 | BESS bajo |
| h12 | ABIERTO | — | 0.27 | 468 | 0 | 0.0 | BESS bajo |
| h13 | ABIERTO | — | 0.28 | 489 | 93 | 0.0 | BESS bajo |
| h14 | ABIERTO | — | 0.39 | 285 | 641 | 0.0 | — |
| h15 | ABIERTO | — | 0.52 | 143 | 1,255 | 2.0 | solar → BESS |
| h16 | ABIERTO | — | 0.67 | 121 | 1,760 | 12.5 | solar → BESS |
| h17 | ABIERTO | — | 0.80 | 212 | 2,110 | 24.5 | solar → BESS |
| h18 | ABIERTO | HP | 0.88 | 287 | 2,278 | 32.5 | ✓ pico controlado |
| h19 | ABIERTO | HP | 0.94 | 298 | 2,230 | 40.5 | ✓ pico controlado |
| h20 | ABIERTO | HP | 0.96 | 410 | 2,016 | 48.1 | ✓ pico controlado |
| h21 | ABIERTO | HP | 0.97 | 693 | 1,663 | 55.8 | ✓ pico controlado |
| h22 | — | HP | 0.97 | 1,177 | 1,177 | 63.5 | ⚠ pico alto |
| h23 | — | — | 0.96 | 1,682 | 610 | 70.3 | BESS lleno (solar) |

## PPO ep49

| Hora | Mall | HP | SOC medio | Grid (kWh) | Solar (kWh) | EV (kWh) | Patrón |
|---:|:---:|:---:|---:|---:|---:|---:|---|
| h00 | — | — | 0.19 | 660 | 0 | 3.9 | BESS bajo |
| h01 | — | — | 0.19 | 531 | 0 | 0.0 | BESS bajo |
| h02 | — | — | 0.19 | 483 | 0 | 0.0 | BESS bajo |
| h03 | — | — | 0.19 | 470 | 0 | 0.0 | BESS bajo |
| h04 | — | — | 0.19 | 460 | 0 | 0.0 | BESS bajo |
| h05 | — | — | 0.19 | 453 | 0 | 0.0 | BESS bajo |
| h06 | — | — | 0.19 | 434 | 0 | 0.0 | BESS bajo |
| h07 | — | — | 0.19 | 431 | 94 | 0.0 | BESS bajo |
| h08 | — | — | 0.34 | 349 | 642 | 0.0 | — |
| h09 | ABIERTO | — | 0.52 | 172 | 1,257 | 1.8 | solar → BESS |
| h10 | ABIERTO | — | 0.70 | 151 | 1,761 | 12.6 | solar → BESS |
| h11 | ABIERTO | — | 0.87 | 217 | 2,110 | 24.0 | BESS lleno (solar) |
| h12 | ABIERTO | — | 0.97 | 272 | 2,277 | 32.6 | BESS lleno (solar) |
| h13 | ABIERTO | — | 0.99 | 282 | 2,227 | 40.6 | BESS lleno (solar) |
| h14 | ABIERTO | — | 0.99 | 397 | 2,017 | 48.1 | BESS lleno (solar) |
| h15 | ABIERTO | — | 0.99 | 698 | 1,662 | 55.8 | BESS lleno (solar) |
| h16 | ABIERTO | — | 0.99 | 1,185 | 1,177 | 63.3 | BESS lleno (solar) |
| h17 | ABIERTO | — | 0.98 | 1,721 | 608 | 69.7 | BESS lleno (solar) |
| h18 | ABIERTO | HP | 0.90 | 1,831 | 110 | 75.9 | ⚠ pico alto |
| h19 | ABIERTO | HP | 0.76 | 1,908 | 0 | 81.4 | ⚠ pico alto |
| h20 | ABIERTO | HP | 0.57 | 1,888 | 0 | 86.1 | ⚠ pico alto |
| h21 | ABIERTO | HP | 0.37 | 1,918 | 0 | 82.9 | ⚠ pico alto |
| h22 | — | HP | 0.21 | 2,015 | 0 | 48.7 | ⚠ pico alto |
| h23 | — | — | 0.20 | 1,242 | 0 | 17.0 | BESS bajo |

## SAC ep33

| Hora | Mall | HP | SOC medio | Grid (kWh) | Solar (kWh) | EV (kWh) | Patrón |
|---:|:---:|:---:|---:|---:|---:|---:|---|
| h00 | — | — | 0.29 | 222 | 642 | 0.0 | BESS bajo |
| h01 | — | — | 0.42 | 118 | 1,255 | 1.8 | solar → BESS |
| h02 | — | — | 0.55 | 108 | 1,760 | 12.1 | solar → BESS |
| h03 | — | — | 0.67 | 192 | 2,110 | 23.0 | solar → BESS |
| h04 | — | — | 0.77 | 319 | 2,278 | 31.3 | solar → BESS |
| h05 | — | — | 0.88 | 351 | 2,230 | 38.7 | BESS lleno (solar) |
| h06 | — | — | 0.95 | 437 | 2,016 | 46.6 | BESS lleno (solar) |
| h07 | — | — | 0.98 | 712 | 1,663 | 54.8 | BESS lleno (solar) |
| h08 | — | — | 0.99 | 1,191 | 1,177 | 62.4 | BESS lleno (solar) |
| h09 | ABIERTO | — | 0.99 | 1,734 | 610 | 67.2 | BESS lleno (solar) |
| h10 | ABIERTO | — | 0.91 | 1,915 | 111 | 73.0 | carga EV intensa |
| h11 | ABIERTO | — | 0.85 | 2,192 | 0 | 79.2 | carga EV intensa |
| h12 | ABIERTO | — | 0.80 | 2,181 | 0 | 84.4 | carga EV intensa |
| h13 | ABIERTO | — | 0.75 | 2,146 | 0 | 80.5 | carga EV intensa |
| h14 | ABIERTO | — | 0.70 | 1,952 | 0 | 47.8 | — |
| h15 | ABIERTO | — | 0.53 | 935 | 0 | 16.8 | — |
| h16 | ABIERTO | — | 0.42 | 449 | 0 | 3.7 | — |
| h17 | ABIERTO | — | 0.33 | 401 | 0 | 0.0 | — |
| h18 | ABIERTO | HP | 0.26 | 420 | 0 | 0.0 | ✓ pico controlado |
| h19 | ABIERTO | HP | 0.22 | 451 | 0 | 0.0 | ✓ pico controlado |
| h20 | ABIERTO | HP | 0.20 | 456 | 0 | 0.0 | ✓ pico controlado |
| h21 | ABIERTO | HP | 0.20 | 454 | 0 | 0.0 | ✓ pico controlado |
| h22 | — | HP | 0.20 | 435 | 0 | 0.0 | ✓ pico controlado |
| h23 | — | — | 0.21 | 451 | 94 | 0.0 | BESS bajo |

---

## Resumen comparativo — Peak Shaving HP (h18–h22)

| Hora | A2C grid (kWh) | PPO grid (kWh) | SAC grid (kWh) | A2C SOC | PPO SOC | SAC SOC |
|---:|---:|---:|---:|---:|---:|---:|
| h18 | 287 | 1,831 | 420 | 0.88 | 0.90 | 0.26 |
| h19 | 298 | 1,908 | 451 | 0.94 | 0.76 | 0.22 |
| h20 | 410 | 1,888 | 456 | 0.96 | 0.57 | 0.20 |
| h21 | 693 | 1,918 | 454 | 0.97 | 0.37 | 0.20 |
| h22 | 1,177 | 2,015 | 435 | 0.97 | 0.21 | 0.20 |

**Grid import promedio HP:**  A2C = 573 kWh/h | PPO = 1,912 kWh/h | SAC = 443 kWh/h

A2C reduce el pico HP en **1,339 kWh/h** vs PPO (70% menos).

---

## Estrategias aprendidas

### A2C — 'Carga solar tarde, EV noche, BESS lleno al HP'
- BESS cargado (SOC 0.88–0.97) al entrar a HP por recarga solar vespertina
- EV carga en h00–h06 usando BESS descargado de la noche anterior
- EV pausa en h07–h13 para no competir con demanda apertura mall
- Grid HP: **287–693 kWh/h** — pico absorbido por BESS+solar

### PPO — 'BESS vacío noche, carga solar mañana, EV en HP'
- BESS depleto de noche (SOC 0.19), se llena con solar en h07–h11
- EV carga concentrada en HP (h18–h21: 82–86 kWh/h)
- Grid HP: **1,909–2,011 kWh/h** — EV+mall crean pico alto

### SAC — 'BESS temprano, EV mediodía, corte en HP'
- BESS recarga en madrugada, se vacía en mediodía
- EV carga en h10–h13, se detiene desde h16
- Grid HP: **420–456 kWh/h** — bajo solo porque no carga EVs
- No es control óptimo: evasión del pico a costa de no cargar mototaxis

---

*Generado: 2026-05-31 | Script: scripts/analysis/control_operativo_bess_ev_oe3.py*
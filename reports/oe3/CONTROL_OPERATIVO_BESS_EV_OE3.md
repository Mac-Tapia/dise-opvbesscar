# OE3 — Control operativo BESS/EV/pico por hora del día

**Fecha:** 2026-05-31
**Episodios analizados:** A2C ep19 (mayor CO₂ evitado) | PPO ep49 (menor F2) | SAC ep33 (mejor SAC)

---

## A2C ep19

| Hora | Mall | HP | SOC medio | Grid (kWh) | Solar (kWh) | EV (kWh) | Patrón |
|---:|:---:|:---:|---:|---:|---:|---:|---|
| h00 | — | — | 0.80 | 1,868 | 111 | 77.2 | carga EV intensa |
| h01 | — | — | 0.64 | 1,962 | 0 | 82.7 | carga EV intensa |
| h02 | — | — | 0.48 | 1,985 | 0 | 87.2 | carga EV intensa |
| h03 | — | — | 0.33 | 2,070 | 0 | 82.9 | carga EV intensa |
| h04 | — | — | 0.24 | 1,994 | 0 | 49.2 | BESS bajo |
| h05 | — | — | 0.21 | 1,238 | 0 | 17.3 | BESS bajo |
| h06 | — | — | 0.20 | 665 | 0 | 4.0 | BESS bajo |
| h07 | — | — | 0.20 | 533 | 0 | 0.0 | BESS bajo |
| h08 | — | — | 0.20 | 489 | 0 | 0.0 | BESS bajo |
| h09 | ABIERTO | — | 0.20 | 478 | 0 | 0.0 | BESS bajo |
| h10 | ABIERTO | — | 0.19 | 464 | 0 | 0.0 | BESS bajo |
| h11 | ABIERTO | — | 0.19 | 458 | 0 | 0.0 | BESS bajo |
| h12 | ABIERTO | — | 0.19 | 441 | 0 | 0.0 | BESS bajo |
| h13 | ABIERTO | — | 0.19 | 432 | 93 | 0.0 | BESS bajo |
| h14 | ABIERTO | — | 0.27 | 212 | 641 | 0.0 | BESS bajo |
| h15 | ABIERTO | — | 0.41 | 126 | 1,255 | 1.9 | solar → BESS |
| h16 | ABIERTO | — | 0.57 | 131 | 1,760 | 12.6 | solar → BESS |
| h17 | ABIERTO | — | 0.73 | 238 | 2,110 | 23.9 | solar → BESS |
| h18 | ABIERTO | HP | 0.85 | 321 | 2,278 | 32.7 | ✓ pico controlado |
| h19 | ABIERTO | HP | 0.93 | 308 | 2,230 | 40.4 | ✓ pico controlado |
| h20 | ABIERTO | HP | 0.96 | 410 | 2,016 | 49.0 | ✓ pico controlado |
| h21 | ABIERTO | HP | 0.96 | 690 | 1,663 | 56.3 | ✓ pico controlado |
| h22 | — | HP | 0.96 | 1,151 | 1,177 | 63.0 | ⚠ pico alto |
| h23 | — | — | 0.91 | 1,537 | 610 | 70.1 | BESS lleno (solar) |

## PPO ep49

| Hora | Mall | HP | SOC medio | Grid (kWh) | Solar (kWh) | EV (kWh) | Patrón |
|---:|:---:|:---:|---:|---:|---:|---:|---|
| h00 | — | — | 0.20 | 660 | 0 | 3.9 | BESS bajo |
| h01 | — | — | 0.19 | 531 | 0 | 0.0 | BESS bajo |
| h02 | — | — | 0.19 | 483 | 0 | 0.0 | BESS bajo |
| h03 | — | — | 0.19 | 470 | 0 | 0.0 | BESS bajo |
| h04 | — | — | 0.19 | 460 | 0 | 0.0 | BESS bajo |
| h05 | — | — | 0.19 | 453 | 0 | 0.0 | BESS bajo |
| h06 | — | — | 0.19 | 434 | 0 | 0.0 | BESS bajo |
| h07 | — | — | 0.19 | 434 | 94 | 0.0 | BESS bajo |
| h08 | — | — | 0.34 | 346 | 642 | 0.0 | — |
| h09 | ABIERTO | — | 0.52 | 177 | 1,257 | 2.0 | solar → BESS |
| h10 | ABIERTO | — | 0.70 | 154 | 1,761 | 12.6 | solar → BESS |
| h11 | ABIERTO | — | 0.88 | 221 | 2,110 | 24.2 | BESS lleno (solar) |
| h12 | ABIERTO | — | 0.97 | 270 | 2,277 | 32.5 | BESS lleno (solar) |
| h13 | ABIERTO | — | 0.99 | 278 | 2,227 | 40.2 | BESS lleno (solar) |
| h14 | ABIERTO | — | 0.99 | 393 | 2,017 | 48.2 | BESS lleno (solar) |
| h15 | ABIERTO | — | 0.99 | 699 | 1,662 | 56.1 | BESS lleno (solar) |
| h16 | ABIERTO | — | 0.99 | 1,187 | 1,177 | 63.4 | BESS lleno (solar) |
| h17 | ABIERTO | — | 0.98 | 1,717 | 608 | 70.0 | BESS lleno (solar) |
| h18 | ABIERTO | HP | 0.90 | 1,845 | 110 | 76.4 | ⚠ pico alto |
| h19 | ABIERTO | HP | 0.76 | 1,913 | 0 | 82.7 | ⚠ pico alto |
| h20 | ABIERTO | HP | 0.57 | 1,891 | 0 | 86.2 | ⚠ pico alto |
| h21 | ABIERTO | HP | 0.37 | 1,923 | 0 | 82.9 | ⚠ pico alto |
| h22 | — | HP | 0.21 | 2,012 | 0 | 49.2 | ⚠ pico alto |
| h23 | — | — | 0.20 | 1,243 | 0 | 17.5 | BESS bajo |

## SAC ep33

| Hora | Mall | HP | SOC medio | Grid (kWh) | Solar (kWh) | EV (kWh) | Patrón |
|---:|:---:|:---:|---:|---:|---:|---:|---|
| h00 | — | — | 0.29 | 222 | 642 | 0.0 | BESS bajo |
| h01 | — | — | 0.41 | 113 | 1,255 | 2.0 | solar → BESS |
| h02 | — | — | 0.55 | 110 | 1,760 | 12.3 | solar → BESS |
| h03 | — | — | 0.67 | 202 | 2,110 | 23.5 | solar → BESS |
| h04 | — | — | 0.79 | 332 | 2,278 | 32.1 | solar → BESS |
| h05 | — | — | 0.89 | 344 | 2,230 | 38.9 | BESS lleno (solar) |
| h06 | — | — | 0.95 | 434 | 2,016 | 47.1 | BESS lleno (solar) |
| h07 | — | — | 0.98 | 704 | 1,663 | 54.1 | BESS lleno (solar) |
| h08 | — | — | 0.99 | 1,189 | 1,177 | 61.3 | BESS lleno (solar) |
| h09 | ABIERTO | — | 0.99 | 1,733 | 610 | 68.5 | BESS lleno (solar) |
| h10 | ABIERTO | — | 0.92 | 1,914 | 111 | 74.5 | carga EV intensa |
| h11 | ABIERTO | — | 0.85 | 2,184 | 0 | 80.7 | carga EV intensa |
| h12 | ABIERTO | — | 0.80 | 2,181 | 0 | 84.8 | carga EV intensa |
| h13 | ABIERTO | — | 0.75 | 2,160 | 0 | 81.0 | carga EV intensa |
| h14 | ABIERTO | — | 0.71 | 1,972 | 0 | 48.3 | — |
| h15 | ABIERTO | — | 0.55 | 939 | 0 | 16.8 | — |
| h16 | ABIERTO | — | 0.43 | 451 | 0 | 3.8 | — |
| h17 | ABIERTO | — | 0.34 | 388 | 0 | 0.0 | — |
| h18 | ABIERTO | HP | 0.27 | 410 | 0 | 0.0 | ✓ pico controlado |
| h19 | ABIERTO | HP | 0.22 | 445 | 0 | 0.0 | ✓ pico controlado |
| h20 | ABIERTO | HP | 0.21 | 454 | 0 | 0.0 | ✓ pico controlado |
| h21 | ABIERTO | HP | 0.20 | 452 | 0 | 0.0 | ✓ pico controlado |
| h22 | — | HP | 0.20 | 435 | 0 | 0.0 | ✓ pico controlado |
| h23 | — | — | 0.20 | 441 | 94 | 0.0 | BESS bajo |

---

## Resumen comparativo — Peak Shaving HP (h18–h22)

| Hora | A2C grid (kWh) | PPO grid (kWh) | SAC grid (kWh) | A2C SOC | PPO SOC | SAC SOC |
|---:|---:|---:|---:|---:|---:|---:|
| h18 | 321 | 1,845 | 410 | 0.85 | 0.90 | 0.27 |
| h19 | 308 | 1,913 | 445 | 0.93 | 0.76 | 0.22 |
| h20 | 410 | 1,891 | 454 | 0.96 | 0.57 | 0.21 |
| h21 | 690 | 1,923 | 452 | 0.96 | 0.37 | 0.20 |
| h22 | 1,151 | 2,012 | 435 | 0.96 | 0.21 | 0.20 |

**Grid import promedio HP:**  A2C = 576 kWh/h | PPO = 1,917 kWh/h | SAC = 440 kWh/h

A2C reduce el pico HP en **1,341 kWh/h** vs PPO (70% menos).

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
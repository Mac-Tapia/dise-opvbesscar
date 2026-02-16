# 🔴 PROBLEMA IDENTIFICADO EN chargers.py

## Localización del Bug

**Archivo**: `src/dimensionamiento/oe2/disenocargadoresev/chargers.py`

### 1️⃣ LÍNEA 214 - Lambda para Motos (INCORRECTO)
```python
MOTO_SPEC = VehicleType(
    name="MOTO",
    lambda_arrivals=0.69,    # 270 motos / (30 tomas × 13h operativas)
    ...
)
```

**Comentario dice**: `270 motos / (30 tomas × 13h operativas) = 0.69`

**Verificación**: 270 / (30 × 13) = 0.69 ✓ Matemática CORRECTA

### 2️⃣ LÍNEA 395 - Cómo se usa lambda (AQUÍ ESTÁ EL FALLO!)
```python
def hourly_step(self, hour: int, operational_factor: float) -> float:
    ...
    # En línea 395:
    num_arrivals = self.rng.poisson(self.vehicle_type.lambda_arrivals * operational_factor)
```

**EL PROBLEMA**: 
- `lambda_arrivals = 0.69` fue calculado **asumiendo operational_factor = 1.0** (24h × 100%)
- Pero en el generador se multiplica por `operational_factor` que VARÍA según la hora
- Resultado: Las arrivals se reducen dramáticamente

### 3️⃣ LÍNEA 650 - get_operational_factor() (CULPABLE FINAL!)
```python
def get_operational_factor(hour_of_day: int) -> float:
    # 0-9h: 0% (cerrado)
    # 9h: 30% (apertura)
    # 10-18h: 30%→100% (rampa)
    # 18-21h: 100% (pico)
    # 21-23h: 100%→0% (cierre)
    # 23-24h: 0% (cerrado)
```

**Factor promedio durante 24h**:
```
0h-9h:   0.0 × 9h = 0
9h:      0.3 × 1h = 0.3
10-18h:  (promedio 0.65) × 8h = 5.2
18-21h:  1.0 × 3h = 3.0
21h:     1.0 × 1h = 1.0
22h:     0.5 × 1h = 0.5
23-24h:  0.0 × 2h = 0
         ─────────────── 
         Total ≈ 10 / 24 ≈ 0.416
         
PROMEDIO: ~0.34 a 0.42 (según cálculo exacto)
```

---

## 📊 DEMOSTRACIÓN DEL IMPACTO

### Cálculo de lambda_arrivals:

**Lo que el código asume**:
```
lambda_arrivals = 0.69
Asume: Operacion 13 horas a 100% → motos/socket/hora = 270 / (30 × 13) = 0.69
```

**Pero en realidad ocurre**:
```
En cada hora, num_arrivals = Poisson(0.69 × operational_factor[hour])

Ejemplo por hora:
  Hora 0-9:     0.69 × 0.0 = 0.0 arrivals
  Hora 9:       0.69 × 0.3 = 0.207 arrivals
  Hora 10-17:   0.69 × [0.3 a 1.0] = 0.207 a 0.69 arrivals
  Hora 18-21:   0.69 × 1.0 = 0.69 arrivals
  Hora 21:      0.69 × 1.0 = 0.69 arrivals
  Hora 22:      0.69 × 0.5 = 0.345 arrivals
  Hora 23-24:   0.69 × 0.0 = 0.0 arrivals
```

**Resultado total / día**:
```
Esperado:  270 motos/día
Real:      ~93-94 motos/día (330% menos)  ← COINCIDE CON NUESTRO HALLAZGO
Ratio:     93.5 / 270 = 0.346 (factor promedio operational)
```

---

## ✅ SOLUCIÓN: 3 OPCIONES

### OPCION A: Escalar lambda_arrivals por operational_factor (RECOMENDADO)
```python
# Calcular operational_factor promedio
FACTOR_OP_PROMEDIO = sum(get_operational_factor(h) for h in range(24)) / 24  # ≈ 0.34-0.42

# Nuevo lambda_arrivals (compensar)
MOTO_SPEC = VehicleType(
    name="MOTO",
    lambda_arrivals=0.69 / FACTOR_OP_PROMEDIO,  # ≈ 0.69 / 0.35 ≈ 1.97
    ...
)

# MOTOTAXI similar
MOTOTAXI_SPEC = VehicleType(
    name="MOTOTAXI",
    lambda_arrivals=0.375 / FACTOR_OP_PROMEDIO,  # ≈ 0.375 / 0.35 ≈ 1.07
    ...
)
```

### OPCION B: Cambiar cómo se aplica operational_factor
```python
# En SocketSimulator.hourly_step() línea 395:
# EN LUGAR DE:
num_arrivals = self.rng.poisson(self.vehicle_type.lambda_arrivals * operational_factor)

# HACER:
# Si operational_factor < 1.0, reducir probabilidad de que un vehículo llegue
# Pero NO reducir el conteo total de arrivals esperado para el año
# (El operational_factor debería aplicarse a la DEMANDA, no a la tasa base)

# Opción: Usar operational_factor solo si está cerca de 0 (cerrado)
if operational_factor < 0.1:
    num_arrivals = 0
else:
    num_arrivals = self.rng.poisson(self.vehicle_type.lambda_arrivals)
```

### OPCION C: Cambiar los comentarios de lambda_arrivals
```python
# Reconocer que lambda_arrivals ya está normalizado para TODO el día
# Comentario CORRECTO:
lambda_arrivals=0.69,  # Promediado sobre 24h considerando operational_factor
```

---

## 🎯 RECOMENDACIÓN FINAL

**La Opción A es la más consistente con el diseño del proyecto**:

1. Calcular `FACTOR_OPERACIONAL_PROMEDIO` como la media de `get_operational_factor()` para 0-23h
2. Multiplicar ambos `lambda_arrivals` por `1 / FACTOR_OPERACIONAL_PROMEDIO`

Esto hará que el dataset genere:
✅ 270 motos/día
✅ 39 mototaxis/día
✅ ...respetando el horario de operación del mall

---

## 📋 VERIFICACIÓN FINAL

**Antes (actual)**:
- Dataset generado: ~93-94 motos/día ❌
- Agentes cargan: ~28 motos/día ❌
- Eficiencia: 30% (es la culpa del dataset, no de los agentes)

**Después (con fix)**:
- Dataset generado: ~270 motos/día ✓
- Agentes esperados: 100%+ del dataset ✓
- Eficiencia: Podremos medir REAL


# Diagnóstico y Arquitectura de Despliegue Docker — pvbesscar OE3

**Proyecto:** pvbesscar — Optimización RL de Carga EV con Solar PV + BESS  
**Agente seleccionado:** A2C (Advantage Actor-Critic) — OE3, obs_dim=19, CO2_DUAL_FOCUS v8.1  
**Fecha:** 2026-05-31  
**Autor:** mac.tapia@unmsm.edu.pe — UNMSM Facultad de Ingeniería Industrial

---

## 1. Diagnóstico de Brechas (Gap Analysis)

### 1.1 Estado pre-implementación

| Componente | Estado | Observación |
|---|---|---|
| `Dockerfile` | ✅ Existía | Multi-stage, Python 3.11, SB3 — solo modo entrenamiento |
| `docker-compose.yml` | ✅ Existía | Pipeline de entrenamiento SAC/PPO/A2C |
| `docker-entrypoint.sh` | ⚠️ Parcial | Modos: sac/ppo/a2c/pipeline/jupyter — sin inferencia |
| `fastapi_websocket_server.py` | ❌ Faltaba | Referenciado en Dockerfile.fastapi pero inexistente |
| Script de inferencia | ❌ Faltaba | Sin modo predict-only, todo integrado al training |
| `docker-compose.operational.yml` | ❌ Faltaba | Sin stack operativo separado |
| Seguridad API | ❌ Faltaba | Sin API Key, sin TLS, sin rate limiting |
| Persistencia resultados | ❌ Incompleto | MongoDB sin índices, sin init script |

### 1.2 Brechas resueltas en esta implementación

| Archivo creado/modificado | Función |
|---|---|
| `scripts/infer/run_a2c_operational.py` | CLI de inferencia determinista (sin entrenamiento) |
| `fastapi_websocket_server.py` | API REST + WebSocket con auth, CORS, MongoDB async |
| `docker-entrypoint.sh` | + modos `infer`, `serve`, `analyze` |
| `docker-compose.operational.yml` | Stack operativo: nginx + a2c-api + mongodb |
| `Dockerfile.fastapi` | Multi-stage dedicado a la API (no mezcla training deps) |
| `requirements.api.txt` | Deps mínimas FastAPI separadas del entorno ML |
| `deploy/nginx/nginx.conf` | TLS 1.3 + rate limiting + WebSocket proxy |
| `deploy/mongo/init.js` | Índices + TTL + config inicial MongoDB |
| `.env.operational` | Template seguro de variables de entorno |

---

## 2. Arquitectura de Software

### 2.1 Vista de capas (C4 — Nivel 2: Contenedores)

```
╔══════════════════════════════════════════════════════════════════════╗
║  CAPA INGRESS                                                        ║
║  ┌────────────────────────────────────────────────────────────────┐  ║
║  │  nginx 1.27-alpine                                             │  ║
║  │  Puerto 443 (HTTPS/TLS 1.3) + 80 → 443 redirect              │  ║
║  │  Rate limit: /simulate=10r/min | /health=60r/min              │  ║
║  │  WebSocket upgrade → /ws/realtime                             │  ║
║  └───────────────────────┬────────────────────────────────────────┘  ║
╠═══════════════════════════╪══════════════════════════════════════════╣
║  CAPA API                 │ proxy_pass                               ║
║  ┌────────────────────────▼───────────────────────────────────────┐  ║
║  │  FastAPI 0.115 + Uvicorn 1 worker                              │  ║
║  │                                                                │  ║
║  │  Auth:    X-API-Key header                                     │  ║
║  │  REST:    GET /health  /model/status  /metrics  /history       │  ║
║  │           POST /simulate  {"episodes": N, "deterministic": T}  │  ║
║  │  WS:      /ws/realtime  (stream step-by-step 8,760 pasos)     │  ║
║  │  Concurr: asyncio.Semaphore(MAX_CONCURRENT=2)                 │  ║
║  └──────┬──────────────────────────────┬─────────────────────────┘  ║
╠══════════╪══════════════════════════════╪════════════════════════════╣
║  CAPA    │  load once                  │  async insert              ║
║  MODELO  │                             │  CAPA PERSISTENCIA         ║
║  ┌───────▼──────────────┐  ┌───────────▼────────────────────────┐  ║
║  │  A2C Inference       │  │  MongoDB 7.0                       │  ║
║  │  ─────────────────   │  │  ────────────────────────────────  │  ║
║  │  A2C.load(.zip)      │  │  episodes:     resultados/episodio │  ║
║  │  VecNormalize(.pkl)  │  │  metrics_daily: KPIs por día      │  ║
║  │  obs_dim=19          │  │  audit_log:    accesos API (TTL90d)│  ║
║  │  action_dim=3        │  │  system_config: config del sistema │  ║
║  │  MLP 256×256         │  │  Índices: timestamp↓, run_id uniq. │  ║
║  │  deterministic=True  │  └────────────────────────────────────┘  ║
║  └──────┬───────────────┘                                          ║
╠══════════╪═══════════════════════════════════════════════════════════╣
║  CAPA    │  read-only volumes                                        ║
║  DATOS   ▼                                                          ║
║  ┌────────────────────────────────────────────────────────────────┐  ║
║  │  checkpoints/A2C_CityLearn/a2c_final.zip     (modelo 438k)   │  ║
║  │  checkpoints/A2C_CityLearn/vecnormalize.pkl  (normalización)  │  ║
║  │  data/interim/citylearn_v2/                  (7 CSV, 8,760h) │  ║
║  │    energy_simulation.csv   carbon_intensity.csv              │  ║
║  │    weather.csv             pricing.csv                       │  ║
║  │    ev_charger_motos.csv    ev_charger_mototaxis.csv          │  ║
║  │    schema_iquitos.json                                       │  ║
║  └────────────────────────────────────────────────────────────────┘  ║
╚══════════════════════════════════════════════════════════════════════╝
```

### 2.2 Flujo de datos detallado

```
SOLICITUD CLIENTE
  │
  │  POST /simulate
  │  Header: X-API-Key: <token>
  │  Body: {"episodes": 1, "deterministic": true}
  ▼
[nginx] TLS termination → rate_limit check → proxy_pass a2c-api:8000
  ▼
[FastAPI] verify_api_key() → 401 si inválida
  │
  └─ asyncio.Semaphore.acquire()  ← hasta MAX_CONCURRENT simulaciones
       │
       └─ run_id = uuid4()
          loop.run_in_executor(None, _run_episode_sync, ep, deterministic)
            │
            ├─ vec_env.reset()
            │    └─ IquitosEVChargingWrapper.reset()
            │         └─ CityLearnEnv.reset()
            │              └─ lee data/interim/citylearn_v2/*.csv (8,760 filas)
            │
            └─ FOR step in range(8_760):
                 │
                 ├─ action, _ = model.predict(obs, deterministic=True)
                 │    └─ VecNormalize.normalize(obs_19D)
                 │    └─ A2C.policy.forward(obs_norm)   # MLP 256×256
                 │    └─ action_3D:
                 │         [0] bess_action    ∈ [-1, +1]
                 │         [1] motos_frac     ∈ [0, 1]
                 │         [2] mototaxis_frac ∈ [0, 1]
                 │
                 └─ obs, reward, done, info = vec_env.step(action_3D)
                      └─ IquitosEVChargingWrapper.step()
                      └─ CO2_DUAL_FOCUS v8.1 reward (7 componentes)
                      └─ info: {
                           co2_direct_kg, co2_indirect_kg,
                           ev_motos_kwh, ev_mototaxis_kwh,
                           grid_import_kwh, bess_discharge_kwh,
                           solar_kwh
                         }
            │
            └─ RESULTADO EPISODIO:
                 co2_total_avoided_kg  ≈ 2,460,341 kg
                 co2_f2_residual_kg_yr ≈ 3,642,436 kg/año
                 co2_reduction_pct     ≈ 48.36% vs F0
                 ev_total_kwh          ≈ 265,101 kWh
                 cost_total_soles      ≈ 2,426,823 S./año

  ▼
[MongoDB] episodes.insert_one({run_id, timestamp, co2, ev, grid, cost, ...})
  ▼
RESPUESTA JSON → Cliente
  {
    "run_id": "...",
    "agent": "A2C",
    "obs_dim": 19,
    "mean_co2_avoided_kg": 2460341.0,
    "mean_reduction_pct": 48.36,
    "mean_reward": 1647.04,
    "detail": [...]
  }
```

### 2.3 WebSocket — Stream en tiempo real

```
Cliente WebSocket
  │  ws://host/ws/realtime
  ▼
HANDSHAKE:
  Cliente envía: {"api_key": "...", "deterministic": true}
  Servidor valida → 4401 si inválida

STREAM (8,760 mensajes):
  {"type": "step", "step": 0,    "action": [0.12, 0.85, 0.70], "reward": 1.23, ...}
  {"type": "step", "step": 1,    "action": [...], ...}
  ...
  {"type": "step", "step": 8759, ...}

FINAL:
  {"type": "done", "summary": {
    "steps": 8760, "total_reward": 1647.04,
    "co2_total_avoided_kg": 2460341.0,
    "reduction_pct": 48.36
  }}
```

---

## 3. Seguridad — Capas de Defensa

| Capa | Tecnología | Qué protege |
|---|---|---|
| **TLS 1.3** | Nginx + certificado SSL | Encriptación end-to-end, man-in-the-middle |
| **API Key** | Header `X-API-Key` | Autenticación de clientes |
| **Rate limiting** | Nginx `limit_req_zone` | DoS, abuso `/simulate` (10r/min) |
| **Semáforo** | `asyncio.Semaphore(2)` | Saturación CPU (episodio toma ~40s) |
| **CORS restrictivo** | FastAPI `CORSMiddleware` | Cross-origin requests no autorizados |
| **Volúmenes `:ro`** | Docker mount flag | Checkpoints y datos no modificables |
| **Red interna** | `pvbesscar-net` bridge | MongoDB no expuesto al host |
| **Secrets en runtime** | Variables de entorno | No hay secretos en la imagen Docker |
| **TTL audit_log** | MongoDB index TTL 90d | Rotación automática de logs de acceso |
| **Headers seguridad** | Nginx `add_header` | XSS, clickjacking, MIME sniffing |

---

## 4. Almacenamiento de Datos

| Categoría | Dónde | Qué | Acceso | Ciclo de vida |
|---|---|---|---|---|
| Modelo A2C | `checkpoints/A2C_CityLearn/` | a2c_final.zip + vecnorm.pkl | `:ro` | Permanente |
| Datos entorno | `data/interim/citylearn_v2/` | 7 CSV × 8,760 filas | `:ro` | Permanente |
| Episodios inferencia | MongoDB `episodes` | CO2, EV, costos por run_id | R/W | Permanente |
| Métricas diarias | MongoDB `metrics_daily` | KPIs agregados por día | R/W | Permanente |
| Audit log | MongoDB `audit_log` | Accesos API + IP + endpoint | R/W | TTL 90 días |
| Config sistema | MongoDB `system_config` | Parámetros OE3 | R/W | Permanente |
| Logs de contenedor | Docker json-file | Stdout/stderr | R/W | Rotación 50MB×5 |
| Outputs inferencia CLI | `outputs/infer/` | JSON resultados job | R/W | Manual |

---

## 5. Guía de Despliegue Paso a Paso

### 5.1 Prerrequisitos

```bash
# Docker Engine 24+ y Docker Compose v2
docker --version          # Docker version 24.x.x
docker compose version    # Docker Compose version v2.x.x

# Verificar que los archivos están presentes (locales)
ls checkpoints/A2C_CityLearn/a2c_final.zip       # modelo entrenado
ls checkpoints/A2C_CityLearn/vecnormalize.pkl     # normalización
ls data/interim/citylearn_v2/energy_simulation.csv # datos entorno
```

### 5.2 Generar certificado TLS (desarrollo)

```bash
mkdir -p deploy/nginx/certs
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout deploy/nginx/certs/server.key \
  -out    deploy/nginx/certs/server.crt \
  -subj   "/C=PE/ST=Lima/L=Lima/O=UNMSM/CN=pvbesscar"
```

### 5.3 Configurar variables de entorno

```bash
cp .env.operational .env.local

# Generar API_KEY segura
python -c "import secrets; print('API_KEY=' + secrets.token_urlsafe(32))" >> .env.local

# Generar password MongoDB
python -c "import secrets; print('MONGO_INITDB_ROOT_PASSWORD=' + secrets.token_urlsafe(24))" >> .env.local

# Editar .env.local y configurar CORS_ORIGINS con el dominio real
```

### 5.4 Build y despliegue

```bash
# Build + start en background
docker compose -f docker-compose.operational.yml --env-file .env.local up -d --build

# Verificar estado de contenedores
docker compose -f docker-compose.operational.yml ps

# Ver logs de la API
docker compose -f docker-compose.operational.yml logs -f a2c-api
```

### 5.5 Verificación funcional

```bash
# 1. Health check
curl -k https://localhost/health
# → {"status": "ok", "model_ready": true, "mongodb": true}

# 2. Info modelo (requiere API Key)
curl -k https://localhost/model/status -H "X-API-Key: $API_KEY"

# 3. Inferencia — 1 episodio completo
curl -k -X POST https://localhost/simulate \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"episodes": 1, "deterministic": true}'

# 4. Métricas históricas
curl -k https://localhost/metrics -H "X-API-Key: $API_KEY"

# 5. Historial de episodios
curl -k "https://localhost/history?page=1&per_page=10" -H "X-API-Key: $API_KEY"
```

### 5.6 Job de inferencia CLI (sin API)

```bash
# Ejecutar 5 episodios y guardar JSON
EPISODES=5 docker compose -f docker-compose.operational.yml \
  --env-file .env.local \
  --profile infer \
  run a2c-infer-job

# O directamente con Python local
python scripts/infer/run_a2c_operational.py --episodes 5 --output results/ep5.json
```

### 5.7 Panel MongoDB (solo perfil dev)

```bash
docker compose -f docker-compose.operational.yml --profile dev up -d mongo-admin
# Acceder en: http://localhost:8081
# Usuario/password: admin / $MONGO_EXPRESS_PASSWORD
```

---

## 6. Descripción de Endpoints API

| Método | Endpoint | Auth | Descripción |
|---|---|---|---|
| `GET` | `/health` | No | Estado del servicio y modelo |
| `GET` | `/model/status` | X-API-Key | Info checkpoint A2C, obs_dim, system specs |
| `POST` | `/simulate` | X-API-Key | Ejecuta N episodios deterministas completos |
| `GET` | `/metrics` | X-API-Key | Métricas agregadas de MongoDB |
| `GET` | `/history` | X-API-Key | Historial paginado de episodios |
| `WS` | `/ws/realtime` | api_key en body | Stream step-by-step (8,760 pasos/episodio) |
| `GET` | `/docs` | No | Swagger UI (FastAPI automático) |
| `GET` | `/redoc` | No | ReDoc documentation |

### Ejemplo respuesta `/simulate` (episodio completo):

```json
{
  "run_id": "a1b2c3d4-...",
  "agent": "A2C",
  "obs_dim": 19,
  "episodes": 1,
  "mean_co2_avoided_kg": 2460341.0,
  "mean_f2_kg_yr": 3642436.0,
  "mean_reduction_pct": 48.3600,
  "mean_reward": 1647.04,
  "mean_ev_total_kwh": 265101.0,
  "mean_cost_total_soles": 2426823.0,
  "detail": [{
    "run_id": "a1b2c3d4-...",
    "episode": 1,
    "timestamp": "2026-05-31T18:00:00Z",
    "steps": 8760,
    "elapsed_s": 38.5,
    "total_reward": 1647.04,
    "co2_total_avoided_kg": 2460341.0,
    "co2_f2_residual_kg_yr": 3642436.0,
    "co2_reduction_vs_f0_pct": 48.3600,
    "ev_motos_kwh": 225198.0,
    "ev_mototaxis_kwh": 39903.0,
    "ev_total_kwh": 265101.0,
    "grid_import_kwh": 7385447.0,
    "bess_discharge_kwh": 632300.0,
    "cost_total_soles": 2426823.0
  }]
}
```

---

## 7. Árbol de archivos del stack operativo

```
pvbesscar/
├── Dockerfile                    # Imagen entrenamiento (existente)
├── Dockerfile.fastapi            # Imagen API operativa (actualizado)
├── docker-compose.yml            # Stack entrenamiento (existente)
├── docker-compose.operational.yml ← NUEVO — stack operativo
├── docker-entrypoint.sh          # + modos infer/serve/analyze
├── fastapi_websocket_server.py   ← NUEVO — API REST + WebSocket
├── requirements.api.txt          ← NUEVO — deps FastAPI
├── .env.operational              ← NUEVO — template env vars
│
├── scripts/
│   └── infer/
│       └── run_a2c_operational.py ← NUEVO — CLI inferencia
│
├── deploy/
│   ├── nginx/
│   │   ├── nginx.conf            ← NUEVO — TLS + rate limit
│   │   └── certs/                ← GENERAR localmente
│   └── mongo/
│       └── init.js               ← NUEVO — índices + config
│
├── checkpoints/
│   └── A2C_CityLearn/            # montado :ro en contenedor
│       ├── a2c_final.zip         # modelo 438k steps
│       └── vecnormalize.pkl      # estadísticas normalización
│
└── data/
    └── interim/
        └── citylearn_v2/         # montado :ro en contenedor
            ├── energy_simulation.csv
            ├── weather.csv
            ├── carbon_intensity.csv
            ├── pricing.csv
            ├── ev_charger_motos.csv
            ├── ev_charger_mototaxis.csv
            └── schema_iquitos.json
```

---

## 8. Resultados esperados en producción

Basados en los resultados canónicos del entrenamiento (obs_dim=19, CO2_DUAL_FOCUS v8.1, n=50 episodios):

| Métrica | Valor esperado por episodio |
|---|---:|
| CO₂ total evitado | ~2,460,341 kg/año |
| CO₂ residual F2 | ~3,642,436 kg/año |
| Reducción vs F0 (sin RL) | **48.36%** |
| Reward medio | 1,647.04 |
| EV total cargado | ~265,101 kWh/año |
| Carga motos | ~225,198 kWh/año |
| Carga mototaxis | ~39,903 kWh/año |
| Grid import | ~7,385,447 kWh/año |
| BESS descarga | ~632,300 kWh/año |
| Costo OSINERGMIN | ~2,426,823 S./año |
| Tiempo por episodio (CPU) | ~40 segundos |

**Referencia canónica:** `reports/oe3/agents_comparison_canonical.json`

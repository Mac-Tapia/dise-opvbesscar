// deploy/mongo/init.js
// Inicialización MongoDB para pvbesscar operacional
// Ejecutado automáticamente en primer inicio del contenedor

db = db.getSiblingDB("pvbesscar");

// Colección de episodios — índices para queries frecuentes
db.episodes.createIndex({ run_id: 1 },    { unique: true, sparse: true });
db.episodes.createIndex({ timestamp: -1 });
db.episodes.createIndex({ agent: 1, timestamp: -1 });

// Colección de métricas agregadas por día
db.metrics_daily.createIndex({ date: 1 },   { unique: true });
db.metrics_daily.createIndex({ agent: 1 });

// Colección de audit log (accesos API)
db.audit_log.createIndex({ timestamp: -1 });
db.audit_log.createIndex({ endpoint: 1, timestamp: -1 });

// TTL index: borrar audit_log después de 90 días
db.audit_log.createIndex({ timestamp: 1 }, { expireAfterSeconds: 7776000 });

// Documento de configuración del sistema
db.system_config.insertOne({
    _id:            "pvbesscar_config",
    agent:          "A2C",
    obs_dim:        19,
    reward_version: "CO2_DUAL_FOCUS v8.1",
    f0_reference:   7053999,
    co2_factor:     0.4521,
    location:       "Iquitos, Peru",
    system: {
        solar_kwp_dc:    4162,
        solar_kwh_year:  5819332,
        bess_kwh:        2000,
        bess_kw:         400,
        sockets:         38,
        daily_motos:     270,
        daily_mototaxis: 39,
    },
    created_at: new Date(),
});

print("pvbesscar MongoDB inicializado correctamente.");

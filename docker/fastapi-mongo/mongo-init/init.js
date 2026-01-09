// MongoDB initialization script
db = db.getSiblingDB('iquitos_ev_db');

// Create collections with validation
db.createCollection('charging_sessions', {
    validator: {
        $jsonSchema: {
            bsonType: 'object',
            required: ['charger_id', 'vehicle_type', 'playa', 'energy_kwh', 'timestamp'],
            properties: {
                charger_id: {
                    bsonType: 'int',
                    minimum: 1,
                    maximum: 128,
                    description: 'Charger ID (1-128)'
                },
                vehicle_type: {
                    enum: ['moto', 'mototaxi'],
                    description: 'Type of electric vehicle'
                },
                playa: {
                    enum: ['Playa_Motos', 'Playa_Mototaxis'],
                    description: 'Parking area'
                },
                energy_kwh: {
                    bsonType: 'double',
                    minimum: 0,
                    description: 'Energy consumed in kWh'
                },
                duration_minutes: {
                    bsonType: 'int',
                    minimum: 0,
                    description: 'Charging duration in minutes'
                },
                co2_kg: {
                    bsonType: 'double',
                    description: 'CO2 emissions in kg'
                },
                timestamp: {
                    bsonType: 'date',
                    description: 'Session timestamp'
                }
            }
        }
    }
});

db.createCollection('simulations');
db.createCollection('agent_metrics');

// Create indexes
db.charging_sessions.createIndex({ timestamp: -1 });
db.charging_sessions.createIndex({ playa: 1, vehicle_type: 1 });
db.charging_sessions.createIndex({ charger_id: 1 });

db.simulations.createIndex({ agent: 1, timestamp: -1 });
db.agent_metrics.createIndex({ agent_name: 1, episode: 1 });

// Insert sample infrastructure data
db.infrastructure.insertOne({
    _id: 'iquitos_ev_mall',
    location: {
        city: 'Iquitos',
        country: 'Peru',
        lat: -3.75,
        lon: -73.25,
        timezone: 'America/Lima'
    },
    playas: {
        Playa_Motos: {
            chargers: 112,
            charger_power_kw: 2,
            pv_kwp: 3641.8,
            bess_kwh: 1750
        },
        Playa_Mototaxis: {
            chargers: 16,
            charger_power_kw: 3,
            pv_kwp: 520.2,
            bess_kwh: 250
        }
    },
    carbon_intensity_kg_kwh: 0.4521,
    created_at: new Date()
});

print('Database initialized: iquitos_ev_db');

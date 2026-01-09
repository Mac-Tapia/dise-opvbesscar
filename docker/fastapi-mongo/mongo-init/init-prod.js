// Production MongoDB initialization with authentication
// This script runs when MongoDB container starts for the first time

// Switch to admin database
db = db.getSiblingDB('admin');

// Create application user
db.createUser({
    user: 'apiuser',
    pwd: process.env.MONGO_PASSWORD || 'change_this_password',
    roles: [
        { role: 'readWrite', db: 'iquitos_ev_db' }
    ]
});

print('Created API user: apiuser');

// Switch to application database
db = db.getSiblingDB('iquitos_ev_db');

// Create collections with validation schemas
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

db.createCollection('simulations', {
    validator: {
        $jsonSchema: {
            bsonType: 'object',
            required: ['agent', 'episodes', 'total_reward', 'timestamp'],
            properties: {
                agent: {
                    enum: ['SAC', 'PPO', 'A2C', 'Uncontrolled'],
                    description: 'RL agent name'
                },
                episodes: {
                    bsonType: 'int',
                    minimum: 1
                },
                total_reward: {
                    bsonType: 'double'
                },
                co2_emissions_kg: {
                    bsonType: 'double',
                    minimum: 0
                },
                solar_utilization_pct: {
                    bsonType: 'double',
                    minimum: 0,
                    maximum: 100
                }
            }
        }
    }
});

db.createCollection('agent_metrics');

// Create indexes for performance
db.charging_sessions.createIndex({ timestamp: -1 });
db.charging_sessions.createIndex({ playa: 1, vehicle_type: 1 });
db.charging_sessions.createIndex({ charger_id: 1 });
db.charging_sessions.createIndex({ 'timestamp': 1 }, { expireAfterSeconds: 31536000 }); // TTL: 1 year

db.simulations.createIndex({ agent: 1, timestamp: -1 });
db.simulations.createIndex({ timestamp: -1 });

db.agent_metrics.createIndex({ agent_name: 1, episode: 1 });
db.agent_metrics.createIndex({ timestamp: -1 });

print('Created indexes');

// Insert infrastructure configuration
db.infrastructure.insertOne({
    _id: 'iquitos_ev_mall',
    version: '1.0.0',
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
            total_power_kw: 224,
            pv_kwp: 3641.8,
            bess_kwh: 1750,
            vehicle_type: 'moto',
            vehicles_served: 900
        },
        Playa_Mototaxis: {
            chargers: 16,
            charger_power_kw: 3,
            total_power_kw: 48,
            pv_kwp: 520.2,
            bess_kwh: 250,
            vehicle_type: 'mototaxi',
            vehicles_served: 130
        }
    },
    totals: {
        chargers: 128,
        power_kw: 272,
        pv_kwp: 4162,
        bess_kwh: 2000,
        vehicles: 1030
    },
    carbon_intensity_kg_kwh: 0.4521,
    tariff_usd_kwh: 0.20,
    multi_objective_weights: {
        co2: 0.50,
        cost: 0.15,
        solar: 0.20,
        ev: 0.10,
        grid: 0.05
    },
    created_at: new Date(),
    updated_at: new Date()
});

print('Inserted infrastructure configuration');

// Create views for analytics
db.createView('daily_stats', 'charging_sessions', [
    {
        $group: {
            _id: {
                date: { $dateToString: { format: '%Y-%m-%d', date: '$timestamp' } },
                playa: '$playa'
            },
            sessions: { $sum: 1 },
            total_energy_kwh: { $sum: '$energy_kwh' },
            total_co2_kg: { $sum: '$co2_kg' },
            avg_duration_min: { $avg: '$duration_minutes' }
        }
    },
    { $sort: { '_id.date': -1 } }
]);

db.createView('agent_performance', 'simulations', [
    {
        $group: {
            _id: '$agent',
            runs: { $sum: 1 },
            avg_reward: { $avg: '$total_reward' },
            avg_co2_kg: { $avg: '$co2_emissions_kg' },
            avg_solar_pct: { $avg: '$solar_utilization_pct' },
            best_reward: { $max: '$total_reward' },
            lowest_co2: { $min: '$co2_emissions_kg' }
        }
    },
    { $sort: { avg_co2_kg: 1 } }
]);

print('Created analytics views');
print('=== Database initialization completed ===');

"""API Tests for Iquitos EV Infrastructure."""

import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_root():
    """Test root endpoint returns OK."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "Iquitos EV Infrastructure API"


@pytest.mark.anyio
async def test_health():
    """Test health endpoint."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")
    
    assert response.status_code in [200, 503]  # 503 if no MongoDB
    data = response.json()
    assert "status" in data
    assert "database" in data


@pytest.mark.anyio
async def test_infrastructure():
    """Test infrastructure endpoint returns correct data."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/infrastructure")
    
    assert response.status_code == 200
    data = response.json()
    
    # Verify location
    assert data["location"]["city"] == "Iquitos"
    assert data["location"]["country"] == "Peru"
    assert data["location"]["lat"] == -3.75
    assert data["location"]["lon"] == -73.25
    
    # Verify playas
    assert "Playa_Motos" in data["playas"]
    assert "Playa_Mototaxis" in data["playas"]
    
    # Verify totals
    assert data["totals"]["chargers"] == 128
    assert data["totals"]["power_kw"] == 272
    assert data["totals"]["pv_kwp"] == 4162
    assert data["totals"]["bess_kwh"] == 2000
    
    # Verify carbon intensity
    assert data["carbon_intensity_kg_kwh"] == 0.4521


@pytest.mark.anyio
async def test_create_session_validation():
    """Test charging session validation."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Invalid charger_id (> 128)
        response = await client.post("/api/v1/sessions", json={
            "charger_id": 200,
            "vehicle_type": "moto",
            "playa": "Playa_Motos",
            "energy_kwh": 2.5,
            "duration_minutes": 30
        })
        assert response.status_code == 422
        
        # Invalid vehicle_type
        response = await client.post("/api/v1/sessions", json={
            "charger_id": 1,
            "vehicle_type": "car",
            "playa": "Playa_Motos",
            "energy_kwh": 2.5,
            "duration_minutes": 30
        })
        assert response.status_code == 422
        
        # Invalid playa
        response = await client.post("/api/v1/sessions", json={
            "charger_id": 1,
            "vehicle_type": "moto",
            "playa": "Invalid_Playa",
            "energy_kwh": 2.5,
            "duration_minutes": 30
        })
        assert response.status_code == 422


@pytest.mark.anyio
async def test_simulation_validation():
    """Test simulation result validation."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Valid simulation data (will fail without MongoDB but validates schema)
        valid_data = {
            "agent": "SAC",
            "episodes": 10,
            "total_reward": -1234.56,
            "co2_emissions_kg": 500.0,
            "solar_utilization_pct": 75.5
        }
        
        response = await client.post("/api/v1/simulations", json=valid_data)
        # Will be 500 without MongoDB, but validates the endpoint exists
        assert response.status_code in [200, 201, 500]

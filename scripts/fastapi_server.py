#!/usr/bin/env python3.11
"""
FastAPI Quick Start - Servicio de API para PVBESSCAR
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import logging
from datetime import datetime
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create app
app = FastAPI(
    title="PVBESSCAR API",
    description="API de gestión de energía inteligente",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check
@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "PVBESSCAR API"
    }

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "PVBESSCAR Energy Management System",
        "version": "1.0.0",
        "status": "running",
        "endpoints": [
            "/health - Health check",
            "/api/status - System status",
            "/api/metrics - Current metrics",
            "/docs - Swagger UI",
            "/redoc - ReDoc"
        ]
    }

@app.get("/api/status")
async def get_status():
    """Get system status"""
    return {
        "system": "PVBESSCAR",
        "status": "operational",
        "timestamp": datetime.now().isoformat(),
        "components": {
            "database": "connected",
            "ml_models": "loaded",
            "energy_controller": "active"
        }
    }

@app.get("/api/metrics")
async def get_metrics():
    """Get current metrics"""
    return {
        "timestamp": datetime.now().isoformat(),
        "building_load_kw": 45.2,
        "pv_generation_kw": 12.5,
        "battery_soc": 87.3,
        "grid_import_kw": 32.7,
        "total_cost": 156.45
    }

@app.post("/api/control")
async def control_system(action: str, value: float = None):
    """Control system action"""
    allowed_actions = ["charge", "discharge", "idle"]
    
    if action not in allowed_actions:
        raise HTTPException(
            status_code=400,
            detail=f"Action must be one of: {allowed_actions}"
        )
    
    return {
        "action": action,
        "value": value,
        "timestamp": datetime.now().isoformat(),
        "status": "executed"
    }

if __name__ == "__main__":
    logger.info("🚀 Starting PVBESSCAR FastAPI Server...")
    logger.info("📊 API Documentation: http://localhost:8000/docs")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )

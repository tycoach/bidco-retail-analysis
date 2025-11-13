"""
FastAPI Application - Bidco Retail Analysis
============================================
REST API exposing data quality, promotions, pricing, and KPIs.
"""

import sys
from pathlib import Path

# Add src to path for imports
project_root = Path(__file__).parent.parent.parent
if str(project_root / "src") not in sys.path:
    sys.path.insert(0, str(project_root / "src"))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from schema import ErrorResponse
from utils.helpers import get_timestamp
from api.dependencies import load_data

# Import all routers
from api.endpoints import health, quality, promotions, pricing, kpis, dashboard





# Initialize FastAPI app
app = FastAPI(
    title="Bidco Retail Analysis API",
    description="REST API for retail data quality and performance analytics",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  #
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(health.router)
app.include_router(quality.router)
app.include_router(promotions.router)
app.include_router(pricing.router)
app.include_router(kpis.router)
app.include_router(dashboard.router)

# Load data on startup
load_data()

# Error handlers
@app.exception_handler(404)
async def not_found_handler(request, exc):
    return JSONResponse(
        status_code=404,
        content=ErrorResponse(
            error="Not Found",
            detail=str(exc.detail) if hasattr(exc, 'detail') else "Resource not found",
            timestamp=get_timestamp()
        ).dict()
    )

@app.exception_handler(500)
async def internal_error_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="Internal Server Error",
            detail=str(exc),
            timestamp=get_timestamp()
        ).dict()
    )

if __name__ == "__main__":
    import uvicorn
    
   
    print("BIDCO RETAIL ANALYSIS API")
 
    print()
    print("Starting API server...")
    print("Documentation: http://localhost:8000/docs")
    print("Health check: http://localhost:8000/health")
    print()
    
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)
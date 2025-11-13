"""
KPI Endpoints
"""
from fastapi import APIRouter, HTTPException, Depends
import polars as pl

from schema import MetricsResponse
from analytics.aggregations import KPIAggregator
from utils import get_timestamp
from api.dependencies import get_df

router = APIRouter(prefix="/api/kpis", tags=["kpis"])

@router.get("/market")
async def get_market_overview(df: pl.DataFrame = Depends(get_df)):
    """Get overall market metrics"""
    try:
        aggregator = KPIAggregator(df)
        market = aggregator.get_market_overview()
        
        return MetricsResponse(
            success=True,
            data=market,
            timestamp=get_timestamp()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{supplier_name}")
async def get_supplier_kpis(supplier_name: str = "BIDCO", df: pl.DataFrame = Depends(get_df)):
    """
    Get KPIs for a specific supplier.
    """
    try:
        aggregator = KPIAggregator(df)
        metrics = aggregator.get_supplier_metrics(supplier_name)
        
        return MetricsResponse(
            success=True,
            data=metrics,
            timestamp=get_timestamp()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{supplier_name}/summary")
async def get_executive_summary(supplier_name: str = "BIDCO", df: pl.DataFrame = Depends(get_df)):
    """
    Get executive summary for a supplier.
    """
    try:
        aggregator = KPIAggregator(df)
        summary = aggregator.generate_executive_summary(supplier_name)
        
        return MetricsResponse(
            success=True,
            data=summary,
            timestamp=get_timestamp()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
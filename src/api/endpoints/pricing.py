"""
Pricing Endpoints
"""
from fastapi import APIRouter, HTTPException, Depends
import polars as pl

from schema import MetricsResponse
from analytics.pricing import PriceIndexCalculator
from utils import get_timestamp
from api.dependencies import get_df

router = APIRouter(prefix="/api/pricing", tags=["pricing"])

@router.get("/{supplier_name}")
async def get_price_positioning(supplier_name: str = "BIDCO", df: pl.DataFrame = Depends(get_df)):
    """
    Get price positioning for a supplier.
    """
    try:
        calculator = PriceIndexCalculator(df)
        summary = calculator.get_price_summary(supplier_name)
        
        return MetricsResponse(
            success=True,
            data={
                "supplier": summary.supplier,
                "analysis_date": str(summary.analysis_date),
                "portfolio": {
                    "total_skus": summary.total_skus,
                    "premium_skus": summary.premium_skus,
                    "at_market_skus": summary.at_market_skus,
                    "discount_skus": summary.discount_skus
                },
                "price_indices": {
                    "average": summary.avg_price_index,
                    "median": summary.median_price_index
                },
                "category_indices": summary.category_indices,
                "store_indices": dict(list(summary.store_level_indices.items())[:10]),
                "recommendations": summary.price_opportunities
            },
            timestamp=get_timestamp()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
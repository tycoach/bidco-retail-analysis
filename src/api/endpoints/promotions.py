"""
Promotions Endpoints for Bidco Retail Analysis API.
"""
from fastapi import APIRouter, HTTPException, Depends
import polars as pl

from schema import MetricsResponse
from analytics.promotions import PromoDetector
from utils import get_timestamp
from api.dependencies import get_df
from schema import PromoPerformanceSummary

router = APIRouter(prefix="/api/promos", tags=["promotions"])

@router.get("/{supplier_name}")
async def get_promo_performance(supplier_name: str = "BIDCO", df: pl.DataFrame = Depends(get_df)):
    """
    Get promotional performance for a supplier.
    """
    try:
        detector = PromoDetector(df)
        summary = detector.get_supplier_summary(supplier_name)
        
        return MetricsResponse(
            success=True,
            data={
                "supplier": summary.supplier,
                "analysis_date": str(summary.analysis_date),  # NEW
                "methodology": summary.methodology,  # NEW
                
                # These fields might be None now (optional in new schema)
                "category": summary.category if summary.category else "All Categories",
                "sub_department": summary.sub_department if summary.sub_department else "All Sub-Departments",
                
                "portfolio": {
                    "total_skus": summary.total_skus,  # CHANGED: was total_skus_analyzed
                    "skus_on_promo": summary.skus_on_promo,
                    "promo_sku_pct": summary.promo_sku_pct
                },
                "performance": {
                    "avg_uplift_pct": summary.avg_uplift_pct,
                    "median_uplift_pct": summary.median_uplift_pct,
                    "avg_discount_pct": summary.avg_discount_pct,
                    "avg_promo_coverage_pct": summary.avg_promo_coverage_pct
                },
                
               
                "top_performers": summary.top_performing_skus[:10] if summary.top_performing_skus else [],
                
                "insights": summary.insights
            },
            metadata={  
                "endpoint": "/api/promos",
                "methodology_note": "Cross-sectional comparison: promo stores vs baseline stores"
            },
            timestamp=get_timestamp()
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
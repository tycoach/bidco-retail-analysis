"""
Dashboard Endpoint (Combined Analytics)
"""
from fastapi import APIRouter, HTTPException, Depends
import polars as pl

from schema import MetricsResponse
from quality import generate_quality_report
from analytics.promotions import PromoDetector
from analytics.pricing import PriceIndexCalculator
from analytics.aggregations import KPIAggregator
from utils import get_timestamp
from api.dependencies import get_df

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

@router.get("/{supplier_name}")
async def get_dashboard(supplier_name: str = "BIDCO", df: pl.DataFrame = Depends(get_df)):
    """
    Get complete dashboard data for a supplier.
    """
    try:
        # Quality
        quality_report = generate_quality_report(df)
        supplier_quality = [
            s for s in quality_report.supplier_scores 
            if supplier_name.lower() in s.entity_name.lower()
        ]
        
        # Promos
        promo_detector = PromoDetector(df)
        promo_summary = promo_detector.get_supplier_summary(supplier_name)
        
        # Pricing
        price_calculator = PriceIndexCalculator(df)
        price_summary = price_calculator.get_price_summary(supplier_name)
        
        # KPIs
        kpi_aggregator = KPIAggregator(df)
        kpi_summary = kpi_aggregator.generate_executive_summary(supplier_name)
        
        return MetricsResponse(
            success=True,
            data={
                "supplier": supplier_name,
                "quality": {
                    "overall_score": supplier_quality[0].overall_score if supplier_quality else None,
                    "grade": supplier_quality[0].grade if supplier_quality else None,
                    "is_trusted": supplier_quality[0].is_trusted if supplier_quality else None
                },
                "promos": {
                    "skus_on_promo": promo_summary.skus_on_promo,
                    "total_skus": promo_summary.total_skus,
                    "avg_uplift_pct": promo_summary.avg_uplift_pct
                },
                "pricing": {
                    "avg_index": price_summary.avg_price_index,
                    "positioning": "premium" if price_summary.avg_price_index > 1.1 
                                   else "discount" if price_summary.avg_price_index < 0.9 
                                   else "at_market"
                },
                "kpis": kpi_summary["key_metrics"]
            },
            metadata={
                "endpoint": "/api/dashboard",
                "components": ["quality", "promos", "pricing", "kpis"]
            },
            timestamp=get_timestamp()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
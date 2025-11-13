"""
Data Quality Endpoints
"""
from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Optional
import polars as pl

from schema import MetricsResponse
from quality import generate_quality_report
from utils import get_timestamp
from api.dependencies import get_df

router = APIRouter(prefix="/api/quality", tags=["quality"])

@router.get("/report")
async def get_quality_report(df: pl.DataFrame = Depends(get_df)):
    """
    Get complete data quality report.
    """
    try:
        report = generate_quality_report(df)
        
        return MetricsResponse(
            success=True,
            data={
                "report_date": str(report.report_date),
                "total_records": report.total_records,
                "total_stores": report.total_stores,
                "total_suppliers": report.total_suppliers,
                "overall_metrics": {
                    "completeness": report.overall_completeness,
                    "validity": report.overall_validity,
                    "consistency": report.overall_consistency
                },
                "store_summary": {
                    "trusted": report.trusted_stores,
                    "untrusted": report.untrusted_stores
                },
                "supplier_summary": {
                    "trusted": report.trusted_suppliers,
                    "untrusted": report.untrusted_suppliers
                },
                "critical_issues": [
                    {
                        "type": issue.issue_type,
                        "severity": issue.severity,
                        "field": issue.field_name,
                        "description": issue.description,
                        "count": issue.count,
                        "percentage": issue.percentage
                    }
                    for issue in report.critical_issues
                ]
            },
            metadata={
                "endpoint": "/api/quality/report",
                "data_source": "Test_Data.xlsx"
            },
            timestamp=get_timestamp()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stores")
async def get_store_scores(
    min_score: Optional[float] = Query(None, description="Minimum quality score filter"),
    trusted_only: bool = Query(False, description="Return only trusted stores"),
    df: pl.DataFrame = Depends(get_df)
):
    """
    Get quality scores for all stores.
    """
    try:
        report = generate_quality_report(df)
        
        stores = []
        for score in report.store_scores:
            if trusted_only and not score.is_trusted:
                continue
            if min_score is not None and score.overall_score < min_score:
                continue
                
            stores.append({
                "store_name": score.entity_name,
                "overall_score": score.overall_score,
                "grade": score.grade,
                "is_trusted": score.is_trusted,
                "completeness_score": score.completeness_score,
                "validity_score": score.validity_score,
                "consistency_score": score.consistency_score,
                "total_records": score.total_records
            })
        
        return MetricsResponse(
            success=True,
            data={
                "stores": stores,
                "count": len(stores)
            },
            metadata={
                "endpoint": "/api/quality/stores",
                "filters": {
                    "min_score": min_score,
                    "trusted_only": trusted_only
                }
            },
            timestamp=get_timestamp()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/suppliers/{supplier_name}")
async def get_supplier_score(supplier_name: str, df: pl.DataFrame = Depends(get_df)):
    """
    Get quality score for a specific supplier.
    """
    try:
        report = generate_quality_report(df)
        
        # Find supplier (case-insensitive)
        supplier_scores = [
            s for s in report.supplier_scores 
            if supplier_name.lower() in s.entity_name.lower()
        ]
        
        if not supplier_scores:
            raise HTTPException(
                status_code=404, 
                detail=f"Supplier '{supplier_name}' not found"
            )
        
        score = supplier_scores[0]
        
        return MetricsResponse(
            success=True,
            data={
                "supplier_name": score.entity_name,
                "overall_score": score.overall_score,
                "grade": score.grade,
                "is_trusted": score.is_trusted,
                "completeness_score": score.completeness_score,
                "validity_score": score.validity_score,
                "consistency_score": score.consistency_score,
                "total_records": score.total_records,
                "issues": [
                    {
                        "type": issue.issue_type,
                        "severity": issue.severity,
                        "field": issue.field_name,
                        "description": issue.description
                    }
                    for issue in score.issues
                ]
            },
            timestamp=get_timestamp()
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
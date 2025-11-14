"""
Pydantic Schemas for Bidco Retail Analysis
"""

from datetime import date
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator, computed_field, ConfigDict
from enum import Enum



# RAW DATA SCHEMAS


class RawTransactionRecord(BaseModel):
    """Schema for a single transaction from the raw Excel file"""
    
    store_name: str = Field(..., alias="Store Name")
    item_code: int = Field(..., alias="Item_Code")
    item_barcode: Optional[str] = Field(None, alias="Item Barcode")
    description: str = Field(..., alias="Description")
    category: str = Field(..., alias="Category")
    department: str = Field(..., alias="Department")
    sub_department: str = Field(..., alias="Sub-Department")
    section: str = Field(..., alias="Section")
    quantity: float = Field(..., alias="Quantity")
    total_sales: float = Field(..., alias="Total Sales")
    rrp: Optional[float] = Field(None, alias="RRP")
    supplier: Optional[str] = Field(None, alias="Supplier")
    date_of_sale: date = Field(..., alias="Date Of Sale")
    
    model_config = ConfigDict(
        populate_by_name=True,
        str_strip_whitespace=True
    )


# ENRICHED DATA SCHEMAS


class EnrichedTransactionRecord(BaseModel):
    """Transaction with derived fields added"""
    
    # Original fields
    store_name: str
    item_code: int
    item_barcode: Optional[str]
    description: str
    category: str
    department: str
    sub_department: str
    section: str
    quantity: float
    total_sales: float
    rrp: Optional[float]
    supplier: Optional[str]
    date_of_sale: date
    
    # Derived fields
    realized_unit_price: Optional[float] = Field(
        None,
        description="Actual price per unit (Total Sales / Quantity)"
    )
    
    discount_pct: Optional[float] = Field(
        None,
        description="Discount percentage vs RRP"
    )
    
    is_valid_transaction: bool = Field(
        True,
        description="Whether transaction passes basic validity checks"
    )
    
    validation_flags: List[str] = Field(
        default_factory=list,
        description="List of validation issues found"
    )
    
    is_bidco: bool = Field(
        False,
        description="Whether this is a Bidco product"
    )
    
    competitive_set_key: Optional[str] = Field(
        None,
        description="Key for grouping competitive products"
    )
    
    @computed_field
    @property
    def is_negative(self) -> bool:
        """Check if quantity or sales are negative"""
        return self.quantity < 0 or self.total_sales < 0
    
    @computed_field
    @property
    def is_zero(self) -> bool:
        """Check if quantity or sales are zero"""
        return self.quantity == 0 or self.total_sales == 0



# DATA QUALITY SCHEMAS


class DataQualityIssue(BaseModel):
    """A single data quality issue"""
    
    issue_type: str = Field(..., description="Type of issue (null, negative, outlier)")
    severity: str = Field(..., description="critical, warning, or info")
    field_name: str = Field(..., description="Column where issue was found")
    description: str = Field(..., description="Human-readable description")
    count: int = Field(..., description="Number of records affected")
    percentage: float = Field(..., description="Percentage of total records")


class DataQualityScore(BaseModel):
    """Quality score for a store or supplier"""
    
    entity_name: str = Field(..., description="Store or supplier name")
    entity_type: str = Field(..., description="'store' or 'supplier'")
    
    # Component scores (0-1 scale)
    completeness_score: float = Field(..., ge=0, le=1)
    validity_score: float = Field(..., ge=0, le=1)
    consistency_score: float = Field(..., ge=0, le=1)
    
    # Overall score (weighted average)
    overall_score: float = Field(..., ge=0, le=1)
    
    # Supporting metrics
    total_records: int
    issues: List[DataQualityIssue] = Field(default_factory=list)
    is_trusted: bool = Field(..., description="Whether score meets minimum threshold")
    
    @computed_field
    @property
    def grade(self) -> str:
        """Letter grade for the quality score"""
        if self.overall_score >= 0.9:
            return "A"
        elif self.overall_score >= 0.8:
            return "B"
        elif self.overall_score >= 0.7:
            return "C"
        elif self.overall_score >= 0.6:
            return "D"
        else:
            return "F"


class DataQualityReport(BaseModel):
    """Complete data quality report"""
    
    report_date: date
    total_records: int
    total_stores: int
    total_suppliers: int
    
    # Aggregate statistics
    overall_completeness: float
    overall_validity: float
    overall_consistency: float
    
    # Entity-level scores
    store_scores: List[DataQualityScore]
    supplier_scores: List[DataQualityScore]
    
    # Top issues
    critical_issues: List[DataQualityIssue]
    
    # Summary
    trusted_stores: int
    untrusted_stores: int
    trusted_suppliers: int
    untrusted_suppliers: int



# PROMOTION SCHEMAS F CROSS-SECTIONAL APPROACH


class PromoStatus(str, Enum):
    """Promotion status for a SKU"""
    ON_PROMO = "on_promo"
    BASELINE = "baseline"
    INSUFFICIENT_DATA = "insufficient_data"
    INVALID = "invalid"


class PromoDetectionResult(BaseModel):
    """
    Promo detection for a single SKU.
    Compares stores WITH promo to stores WITHOUT promo for same SKU.
    """
    
    item_code: int
    description: str
    supplier: str
    store_name: Optional[str] = Field(
        None, 
        description="Specific store (None for aggregated cross-store view)"
    )
    sub_department: str
    section: str
    
    # Promo detection (cross-sectional)
    promo_status: PromoStatus
    promo_stores: int = Field(..., description="Number of stores running promo")
    baseline_stores: int = Field(..., description="Number of stores at baseline price")
    total_stores: int = Field(..., description="Total stores carrying SKU")
    
    # Volume metrics
    promo_units: Optional[float] = Field(None, description="Total units sold in promo stores")
    baseline_units: Optional[float] = Field(None, description="Total units sold in baseline stores")
    
    # Performance (cross-sectional uplift)
    promo_uplift_pct: Optional[float] = Field(
        None,
        description="Uplift % (promo stores vs baseline stores, not same store over time)"
    )
    
    # Pricing
    avg_promo_price: Optional[float] = Field(None, description="Average price in promo stores")
    avg_baseline_price: Optional[float] = Field(None, description="Average price in baseline stores")
    avg_discount_pct: Optional[float] = Field(None, description="Average discount depth in promo stores")
    median_rrp: Optional[float] = Field(None, description="Median RRP")
    
    # Coverage
    promo_coverage_pct: float = Field(..., description="% of stores running promo for this SKU")
    
    # DEPRECATED (time-series fields - kept for backward compatibility)
    analysis_start_date: Optional[date] = None
    analysis_end_date: Optional[date] = None
    promo_days: Optional[int] = Field(None, description="DEPRECATED: Use promo_stores instead")
    baseline_days: Optional[int] = Field(None, description="DEPRECATED: Use baseline_stores instead")


class PromoPerformanceSummary(BaseModel):
    """
    Aggregated promo performance across multiple SKUs.
    """
    
    supplier: str
    analysis_date: date
    category: Optional[str] = None
    sub_department: Optional[str] = None
    
    total_skus: int = Field(..., alias="total_skus_analyzed")
    skus_on_promo: int
    promo_sku_pct: float
    
    # Aggregated metrics (cross-sectional)
    avg_uplift_pct: Optional[float] = Field(
        None,
        description="Average uplift across all promo SKUs (cross-sectional)"
    )
    median_uplift_pct: Optional[float] = None
    avg_discount_pct: Optional[float] = None
    avg_promo_coverage_pct: Optional[float] = Field(
        None,
        description="Average % of stores running promos"
    )
    
    # Top performers
    top_performing_skus: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Top SKUs by uplift (simplified dict format)"
    )
    
    # Insights
    insights: List[str] = Field(default_factory=list)
    
    # Methodology flag
    methodology: str = Field(
        default="cross_sectional",
        description="Analysis methodology: 'cross_sectional' or 'time_series'"
    )
    
    model_config = ConfigDict(populate_by_name=True)



# PRICING INDEX SCHEMAS


class PricePosition(str, Enum):
    """Price positioning relative to competitors"""
    PREMIUM = "premium"
    AT_MARKET = "at_market"
    DISCOUNT = "discount"
    INSUFFICIENT_DATA = "insufficient_data"


class PriceIndexResult(BaseModel):
    """Price index for a SKU in a competitive set"""
    
    item_code: int
    description: str
    supplier: str
    store_name: Optional[str] = None  # None for aggregated view
    sub_department: str
    section: str
    
    # Bidco pricing
    bidco_avg_price: float
    bidco_avg_rrp: Optional[float] = None
    
    # Competitor pricing
    competitor_avg_price: Optional[float] = None
    competitor_count: int = Field(..., description="Number of competitors in set")
    
    # Price index (Bidco / Competitor average)
    price_index: Optional[float] = Field(
        None,
        description="Price index: <0.9 discount, 0.9-1.1 at market, >1.1 premium"
    )
    
    price_position: PricePosition
    
    # Price variance
    price_vs_rrp_pct: Optional[float] = Field(
        None,
        description="How much below/above RRP Bidco is selling"
    )
    
    # Supporting data
    bidco_transaction_count: int
    competitor_transaction_count: int


class PriceIndexSummary(BaseModel):
    """Summary of price positioning across portfolio"""
    
    supplier: str
    analysis_date: date
    
    # Portfolio breakdown
    total_skus: int
    premium_skus: int
    at_market_skus: int
    discount_skus: int
    
    # Averages
    avg_price_index: float
    median_price_index: float
    
    # By store (if applicable)
    store_level_indices: Dict[str, float] = Field(default_factory=dict)
    
    # By category
    category_indices: Dict[str, float] = Field(default_factory=dict)
    
    # Recommendations
    price_opportunities: List[str] = Field(
        default_factory=list,
        description="Areas where pricing could be optimized"
    )



# API RESPONSE SCHEMAS


class HealthCheckResponse(BaseModel):
    """API health check response"""
    status: str
    version: str
    timestamp: str


class ErrorResponse(BaseModel):
    """Standard error response"""
    error: str
    detail: Optional[str] = None
    timestamp: str


class MetricsResponse(BaseModel):
    """Generic metrics response wrapper"""
    success: bool
    data: Dict[str, Any]
    metadata: Dict[str, Any] = Field(default_factory=dict)
    timestamp: str



# VALIDATION HELPERS


def validate_transaction_record(record: Dict[str, Any]) -> tuple[bool, List[str]]:
    """
    Validate a transaction record and return validation status + issues.
    """
    issues = []
    
    # Check for negative values
    if record.get("quantity", 0) < 0:
        issues.append("negative_quantity")
    if record.get("total_sales", 0) < 0:
        issues.append("negative_sales")
    
    # Check for zeros
    if record.get("quantity", 0) == 0:
        issues.append("zero_quantity")
    if record.get("total_sales", 0) == 0:
        issues.append("zero_sales")
    
    # Check for required fields
    required = ["store_name", "item_code", "description", "quantity", "total_sales", "date_of_sale"]
    for field in required:
        if not record.get(field):
            issues.append(f"missing_{field}")
    
    is_valid = len(issues) == 0
    return is_valid, issues


# if __name__ == "__main__":
#     """Test schemas with sample data"""
    
#     print("=" * 80)
#     print("SCHEMA VALIDATION TESTS (UPDATED FOR CROSS-SECTIONAL)")
#     print("=" * 80)
#     print()
    
#     # Test raw transaction
#     raw_data = {
#         "Store Name": "KIAMBU RD",
#         "Item_Code": 280236,
#         "Item Barcode": "6374692674377",
#         "Description": "HC-TOPEX LEMON 250ML",
#         "Category": "HOMECARE",
#         "Department": "HOME CARE",
#         "Sub-Department": "BLEACH",
#         "Section": "BLEACH 250ML",
#         "Quantity": 1.0,
#         "Total Sales": 103.45,
#         "RRP": 91.41,
#         "Supplier": "SUPERSLEEK LIMITED",
#         "Date Of Sale": date(2025, 9, 23)
#     }
    
#     try:
#         record = RawTransactionRecord(**raw_data)
#         print(" RawTransactionRecord validation passed")
#         print(f"   Store: {record.store_name}")
#         print(f"   Product: {record.description}")
#         print(f"   Sales: {record.total_sales}")
#     except Exception as e:
#         print(f" RawTransactionRecord validation failed: {e}")
    
#     print()
    
#     # Test quality score
#     quality_score = DataQualityScore(
#         entity_name="KIAMBU RD",
#         entity_type="store",
#         completeness_score=0.99,
#         validity_score=0.98,
#         consistency_score=0.95,
#         overall_score=0.97,
#         total_records=1134,
#         is_trusted=True
#     )
    
#     print(f" DataQualityScore created: {quality_score.entity_name}")
#     print(f"   Grade: {quality_score.grade}")
#     print(f"   Trusted: {quality_score.is_trusted}")
#     print()
    
#     # Test promo result (CROSS-SECTIONAL)
#     promo = PromoDetectionResult(
#         item_code=280236,
#         description="Bidco Chipsy Cooking Fat",
#         supplier="BIDCO AFRICA LIMITED",
#         store_name=None,  # Aggregated view
#         sub_department="COOKING FATS",
#         section="COOKING FAT 2.5KG",
#         promo_status=PromoStatus.ON_PROMO,
#         promo_stores=2,
#         baseline_stores=2,
#         total_stores=4,
#         promo_units=22.0,
#         baseline_units=7.0,
#         promo_uplift_pct=214.3,
#         avg_promo_price=450.0,
#         avg_baseline_price=500.0,
#         avg_discount_pct=15.5,
#         median_rrp=525.0,
#         promo_coverage_pct=50.0
#     )
    
#     print(f" PromoDetectionResult (CROSS-SECTIONAL) created: {promo.description}")
#     print(f"   Status: {promo.promo_status.value}")
#     print(f"   Uplift: {promo.promo_uplift_pct}% (promo stores vs baseline stores)")
#     print(f"   Promo stores: {promo.promo_stores}, Baseline stores: {promo.baseline_stores}")
#     print(f"   Coverage: {promo.promo_coverage_pct}%")
#     print()
    
#     # Test promo summary
#     promo_summary = PromoPerformanceSummary(
#         supplier="BIDCO",
#         analysis_date=date(2025, 11, 14),
#         total_skus_analyzed=105,
#         skus_on_promo=71,
#         promo_sku_pct=67.6,
#         avg_uplift_pct=7.56,
#         median_uplift_pct=5.2,
#         avg_discount_pct=15.3,
#         avg_promo_coverage_pct=42.5,
#         methodology="cross_sectional"
#     )
    
#     print(f" PromoPerformanceSummary created: {promo_summary.supplier}")
#     print(f"   SKUs on promo: {promo_summary.skus_on_promo}/{promo_summary.total_skus}")
#     print(f"   Avg uplift: {promo_summary.avg_uplift_pct}%")
#     print(f"   Methodology: {promo_summary.methodology}")
#     print()
    
#     # Test price index
#     price_idx = PriceIndexResult(
#         item_code=280236,
#         description="HC-TOPEX LEMON 250ML",
#         supplier="BIDCO",
#         store_name="KIAMBU RD",
#         sub_department="BLEACH",
#         section="BLEACH 250ML",
#         bidco_avg_price=95.50,
#         competitor_avg_price=105.00,
#         competitor_count=3,
#         price_index=0.91,
#         price_position=PricePosition.DISCOUNT,
#         bidco_transaction_count=15,
#         competitor_transaction_count=45
#     )
    
#     print(f" PriceIndexResult created: {price_idx.description}")
#     print(f"   Position: {price_idx.price_position.value}")
#     print(f"   Index: {price_idx.price_index}")
#     print()
    
#     print("=" * 80)
#     print("All schema tests passed")
#     print("=" * 80)
"""Configuration module for Bidco retail analysis.
Defines Pydantic models for structured configuration management.
Includes settings for promotion detection, data quality scoring,
competitive price indexing, and general analysis parameters.
Each configuration section is encapsulated in its own class,
with sensible defaults and validation.
"""

from pathlib import Path
from typing import List
from pydantic import BaseModel, Field


# Project paths
PROJECT_ROOT = Path.cwd().parent
DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
# PROCESSED_DATA_DIR = DATA_DIR / "processed"
# EXPORTS_DIR = DATA_DIR / "exports"


class PromoConfig(BaseModel):
    """Configuration for promotion detection logic"""
    
    # Discount threshold: realized price must be this % below RRP
    discount_threshold_pct: float = Field(
        default=10.0,
        description="Minimum discount % to be considered a promotion"
    )
    
    # Minimum days a SKU must be on promo to be counted
    min_promo_days: int = Field(
        default=2,
        description="Minimum consecutive days at discount to qualify as promo"
    )
    
    # Maximum discount(> = data error)
    max_realistic_discount_pct: float = Field(
        default=70.0,
        description="Discounts beyond this are flagged as suspicious"
    )
    
    # Minimum baseline days needed to calculate uplift
    min_baseline_days: int = Field(
        default=2,
        description="Need at least this many non-promo days for baseline"
    )


class DataQualityConfig(BaseModel):
    """Configuration for data quality scoring"""
    
    # Completeness thresholds
    max_acceptable_null_pct: float = Field(
        default=5.0,
        description="Maximum % of nulls before penalizing quality score"
    )
    
    # Validity thresholds
    max_acceptable_negative_pct: float = Field(
        default=1.0,
        description="Maximum % of negative values before penalty"
    )
    
    max_acceptable_zero_pct: float = Field(
        default=2.0,
        description="Maximum % of zero values before penalty"
    )
    
    # Outlier detection
    outlier_sigma: float = Field(
        default=3.0,
        description="Standard deviations for outlier detection"
    )
    
    price_outlier_quantile: float = Field(
        default=0.99,
        description="Quantile threshold for price outliers"
    )
    
    # Minimum trust score to be considered "reliable"
    min_trust_score: float = Field(
        default=0.75,
        description="Stores/suppliers below this are flagged as unreliable"
    )
    
    # Quality score weights (must sum to 1.0)
    completeness_weight: float = 0.30
    validity_weight: float = 0.40
    consistency_weight: float = 0.30


class PriceIndexConfig(BaseModel):
    """Configuration for competitive price indexing"""
    
    # Price index = Bidco Price / Competitor Avg Price
    # Interpretation thresholds
    premium_threshold: float = Field(
        default=1.10,
        description="Index > this = Bidco is premium priced"
    )
    
    discount_threshold: float = Field(
        default=0.90,
        description="Index < this = Bidco is discount priced"
    )
    
    # Minimum competitors needed for meaningful comparison
    min_competitors_for_index: int = Field(
        default=2,
        description="Need at least this many competitors in section"
    )
    
    # Minimum transactions for reliable price
    min_transactions_for_price: int = Field(
        default=5,
        description="SKU needs this many transactions for reliable avg price"
    )


class AnalysisConfig(BaseModel):
    """General analysis configuration"""
    
    # Target client
    target_supplier: str = Field(
        default="BIDCO",
        description="The supplier under analysis"
    )
    
    # Competitive set definition
    competitive_grouping: List[str] = Field(
        default=["Sub-Department", "Section"],
        description="Columns that define competitive sets"
    )
    
    # Store grouping for analysis
    store_grouping_cols: List[str] = Field(
        default=["Store Name"],
        description="Columns that define store-level groups"
    )
    
    # Critical columns that must not be null
    required_columns: List[str] = Field(
        default=[
            "Store Name",
            "Item_Code", 
            "Description",
            "Category",
            "Department",
            "Sub-Department",
            "Quantity",
            "Total Sales",
            "Supplier",
            "Date Of Sale"
        ],
        description="Columns that cannot be null for valid analysis"
    )
    
    # Columns where nulls can be imputed
    imputable_columns: List[str] = Field(
        default=["RRP", "Item Barcode"],
        description="Columns to fill missing values"
    )


class OutputConfig(BaseModel):
    """Configuration for outputs and reporting"""
    
    # Number of top items to show in reports
    top_n_items: int = Field(
        default=10,
        description="Show top N items in various rankings"
    )
    
    # Decimal places for percentages
    pct_decimal_places: int = 2
    
    # Decimal places for currency
    currency_decimal_places: int = 2
    
    # Decimal places for indices
    index_decimal_places: int = 3


# Create singleton instances
PROMO_CONFIG = PromoConfig()
QUALITY_CONFIG = DataQualityConfig()
PRICE_INDEX_CONFIG = PriceIndexConfig()
ANALYSIS_CONFIG = AnalysisConfig()
OUTPUT_CONFIG = OutputConfig()


# Validation: Ensure quality weights sum to 1.0
_total_weight = (
    QUALITY_CONFIG.completeness_weight + 
    QUALITY_CONFIG.validity_weight + 
    QUALITY_CONFIG.consistency_weight
)
assert abs(_total_weight - 1.0) < 0.001, f"Quality weights must sum to 1.0, got {_total_weight}"


def get_config_summary() -> dict:
    """Get a summary of all configuration settings"""
    return {
        "promo": PROMO_CONFIG.model_dump(),
        "quality": QUALITY_CONFIG.model_dump(),
        "price_index": PRICE_INDEX_CONFIG.model_dump(),
        "analysis": ANALYSIS_CONFIG.model_dump(),
        "output": OUTPUT_CONFIG.model_dump(),
    }


# if __name__ == "__main__":
#     """Print configuration for validation"""
#     import json
    
    
#     print("BIDCO RETAIL ANALYSIS - CONFIGURATION")
    
#     config = get_config_summary()
    
#     print("PROMO DETECTION")
#     print(f"  Discount threshold: {PROMO_CONFIG.discount_threshold_pct}%")
#     print(f"  Min promo days: {PROMO_CONFIG.min_promo_days}")
#     print(f"  Max realistic discount: {PROMO_CONFIG.max_realistic_discount_pct}%")
#     print(f"  Min baseline days: {PROMO_CONFIG.min_baseline_days}")
#     print()
    
#     print("DATA QUALITY")
#     print(f"  Max null %: {QUALITY_CONFIG.max_acceptable_null_pct}%")
#     print(f"  Max negative %: {QUALITY_CONFIG.max_acceptable_negative_pct}%")
#     print(f"  Max zero %: {QUALITY_CONFIG.max_acceptable_zero_pct}%")
#     print(f"  Outlier sigma: {QUALITY_CONFIG.outlier_sigma}")
#     print(f"  Min trust score: {QUALITY_CONFIG.min_trust_score}")
#     print(f"  Weights: {QUALITY_CONFIG.completeness_weight:.0%} completeness, "
#           f"{QUALITY_CONFIG.validity_weight:.0%} validity, "
#           f"{QUALITY_CONFIG.consistency_weight:.0%} consistency")
#     print()
    
#     print("PRICE INDEX")
#     print(f"  Premium threshold: {PRICE_INDEX_CONFIG.premium_threshold}x")
#     print(f"  Discount threshold: {PRICE_INDEX_CONFIG.discount_threshold}x")
#     print(f"  Min competitors: {PRICE_INDEX_CONFIG.min_competitors_for_index}")
#     print(f"  Min transactions: {PRICE_INDEX_CONFIG.min_transactions_for_price}")
#     print()
    
#     print("ANALYSIS")
#     print(f"  Target supplier: {ANALYSIS_CONFIG.target_supplier}")
#     print(f"  Competitive grouping: {', '.join(ANALYSIS_CONFIG.competitive_grouping)}")
#     print(f"  Required columns: {len(ANALYSIS_CONFIG.required_columns)} fields")
#     print()
    
#     print("Configuration valid and loaded")
#     print()
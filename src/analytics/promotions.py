"""
Promotion Detection Engine
"""

import sys
from pathlib import Path

# Add src to path for imports
if __name__ == "__main__":
    project_root = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(project_root / "src"))

import polars as pl
from typing import List, Dict, Optional, Tuple
from datetime import date

from config import PROMO_CONFIG, ANALYSIS_CONFIG
from schema import (
    PromoDetectionResult,
    PromoPerformanceSummary,
    PromoStatus
)
from utils import (
    calculate_realized_price,
    calculate_discount_pct,
    flag_bidco_products,
    calculate_uplift_pct,
    filter_valid_transactions
)


class PromoDetector:
    """
    Detects promotional periods and calculates performance metrics.
    """
    
    def __init__(self, df: pl.DataFrame):
        """
        Initialize with transaction data.
    
        """
        self.df = df
        self._prepare_data()
    
    def _prepare_data(self):
        """Prepare data with necessary derived fields"""
        # Add realized price and discount %
        self.df = calculate_realized_price(self.df)
        self.df = calculate_discount_pct(self.df)
        
        # Flag Bidco products
        self.df = flag_bidco_products(self.df)
        
        # Filter to valid transactions only
        self.df = filter_valid_transactions(self.df, allow_negatives=False, allow_zeros=False)
        
        # Add day-level key for grouping
        self.df = self.df.with_columns([
            pl.concat_str([
                pl.col("Store Name"),
                pl.col("Item_Code").cast(pl.Utf8),
                pl.col("Date Of Sale").cast(pl.Utf8)
            ], separator="|").alias("day_key")
        ])
    
    def detect_promos(self) -> pl.DataFrame:
        """
        Detect promotional periods for each SKU in each store.
        """
        # Group by store, SKU, and date to get daily metrics
        daily_data = self.df.group_by(["Store Name", "Item_Code", "Date Of Sale"]).agg([
            pl.col("Description").first(),
            pl.col("Supplier").first(),
            pl.col("Sub-Department").first(),
            pl.col("Section").first(),
            pl.col("Quantity").sum().alias("daily_quantity"),
            pl.col("Total Sales").sum().alias("daily_sales"),
            pl.col("RRP").median().alias("median_rrp"),
            pl.col("discount_pct").mean().alias("avg_discount_pct"),
            pl.col("is_bidco").first()
        ]).with_columns([
            # Calculate daily realized price
            (pl.col("daily_sales") / pl.col("daily_quantity")).alias("daily_realized_price")
        ])
        
        # Flag promo days: discount >= threshold
        daily_data = daily_data.with_columns([
            pl.when(pl.col("avg_discount_pct") >= PROMO_CONFIG.discount_threshold_pct)
            .then(pl.lit(True))
            .otherwise(pl.lit(False))
            .alias("is_promo_day")
        ])
        
        # Count promo days per SKU per store
        sku_store_summary = daily_data.group_by(["Store Name", "Item_Code"]).agg([
            pl.col("Description").first(),
            pl.col("Supplier").first(),
            pl.col("Sub-Department").first(),
            pl.col("Section").first(),
            pl.col("is_bidco").first(),
            pl.col("Date Of Sale").min().alias("first_date"),
            pl.col("Date Of Sale").max().alias("last_date"),
            pl.col("is_promo_day").sum().alias("promo_days"),
            pl.col("is_promo_day").len().alias("total_days"),
            
            # Promo metrics
            pl.when(pl.col("is_promo_day"))
            .then(pl.col("daily_quantity"))
            .otherwise(None)
            .sum()
            .alias("promo_quantity"),
            
            pl.when(pl.col("is_promo_day"))
            .then(pl.col("daily_sales"))
            .otherwise(None)
            .sum()
            .alias("promo_sales"),
            
            pl.when(pl.col("is_promo_day"))
            .then(pl.col("daily_realized_price"))
            .otherwise(None)
            .mean()
            .alias("avg_promo_price"),
            
            pl.when(pl.col("is_promo_day"))
            .then(pl.col("avg_discount_pct"))
            .otherwise(None)
            .mean()
            .alias("avg_promo_discount"),
            
            # Baseline metrics (non-promo days)
            pl.when(~pl.col("is_promo_day"))
            .then(pl.col("daily_quantity"))
            .otherwise(None)
            .sum()
            .alias("baseline_quantity"),
            
            pl.when(~pl.col("is_promo_day"))
            .then(pl.col("daily_sales"))
            .otherwise(None)
            .sum()
            .alias("baseline_sales"),
            
            pl.when(~pl.col("is_promo_day"))
            .then(pl.col("daily_realized_price"))
            .otherwise(None)
            .mean()
            .alias("avg_baseline_price"),
            
            pl.col("median_rrp").median().alias("avg_rrp")
        ])
        
        # Calculate baseline days
        sku_store_summary = sku_store_summary.with_columns([
            (pl.col("total_days") - pl.col("promo_days")).alias("baseline_days")
        ])
        
        # Determine promo status
        sku_store_summary = sku_store_summary.with_columns([
            pl.when(
                (pl.col("promo_days") >= PROMO_CONFIG.min_promo_days) &
                (pl.col("baseline_days") >= PROMO_CONFIG.min_baseline_days)
            )
            .then(pl.lit("on_promo"))
            .when(pl.col("baseline_days") >= PROMO_CONFIG.min_baseline_days)
            .then(pl.lit("baseline"))
            .otherwise(pl.lit("insufficient_data"))
            .alias("promo_status")
        ])
        
        # Calculate uplift
        sku_store_summary = sku_store_summary.with_columns([
            # Uplift % = ((promo - baseline) / baseline) * 100
            pl.when((pl.col("baseline_quantity") > 0) & (pl.col("promo_quantity").is_not_null()))
            .then(
                ((pl.col("promo_quantity") - pl.col("baseline_quantity")) / pl.col("baseline_quantity")) * 100
            )
            .otherwise(None)
            .alias("uplift_pct")
        ])
        
        return sku_store_summary
    
    def calculate_promo_coverage(self, promo_data: pl.DataFrame) -> pl.DataFrame:
        """
        Calculate what % of stores are running each promo.
        """
        # Count stores per SKU
        sku_coverage = promo_data.group_by("Item_Code").agg([
            pl.col("Description").first(),
            pl.col("Supplier").first(),
            pl.col("Sub-Department").first(),
            pl.col("Section").first(),
            pl.col("is_bidco").first(),
            
            # Total stores carrying this SKU
            pl.col("Store Name").n_unique().alias("total_stores_with_sku"),
            
            # Stores with promo
            pl.when(pl.col("promo_status") == "on_promo")
            .then(pl.col("Store Name"))
            .otherwise(None)
            .n_unique()
            .alias("stores_with_promo"),
            
            # Average metrics across stores
            pl.col("uplift_pct").mean().alias("avg_uplift_pct"),
            pl.col("avg_promo_discount").mean().alias("avg_discount_pct"),
            pl.col("promo_quantity").sum().alias("total_promo_units"),
            pl.col("baseline_quantity").sum().alias("total_baseline_units")
        ])
        
        # Calculate coverage %
        sku_coverage = sku_coverage.with_columns([
            (pl.col("stores_with_promo") / pl.col("total_stores_with_sku") * 100).alias("promo_coverage_pct")
        ])
        
        return sku_coverage
    
    def get_promo_results(self) -> List[PromoDetectionResult]:
        """
        Get detailed promo detection results.
        """
        promo_data = self.detect_promos()
        
        results = []
        for row in promo_data.iter_rows(named=True):
            result = PromoDetectionResult(
                item_code=row["Item_Code"],
                description=row["Description"],
                supplier=row["Supplier"],
                store_name=row["Store Name"],
                sub_department=row["Sub-Department"],
                section=row["Section"],
                analysis_start_date=row["first_date"],
                analysis_end_date=row["last_date"],
                promo_days=row["promo_days"],
                baseline_days=row["baseline_days"],
                promo_status=PromoStatus(row["promo_status"]),
                avg_promo_price=row["avg_promo_price"],
                avg_baseline_price=row["avg_baseline_price"],
                avg_rrp=row["avg_rrp"],
                avg_discount_pct=row["avg_promo_discount"],
                promo_units=row["promo_quantity"],
                baseline_units=row["baseline_quantity"],
                promo_uplift_pct=row["uplift_pct"]
            )
            results.append(result)
        
        return results
    
    def get_supplier_summary(self, supplier: str = "BIDCO") -> PromoPerformanceSummary:
        """
        Get aggregated promo performance for a supplier.
        """
        promo_data = self.detect_promos()
        coverage_data = self.calculate_promo_coverage(promo_data)
        
        # Filter to supplier
        supplier_data = promo_data.filter(
            pl.col("Supplier").str.to_lowercase().str.contains(supplier.lower())
        )
        
        if len(supplier_data) == 0:
            raise ValueError(f"No data found for supplier: {supplier}")
        
        # Get category (assume single category for simplicity)
        category = supplier_data["Sub-Department"].mode()[0] if len(supplier_data) > 0 else "Unknown"
        sub_dept = supplier_data["Sub-Department"].unique().to_list()[0] if len(supplier_data) > 0 else "Unknown"
        
        # Calculate aggregate metrics
        total_skus = supplier_data["Item_Code"].n_unique()
        skus_on_promo = supplier_data.filter(pl.col("promo_status") == "on_promo")["Item_Code"].n_unique()
        
        # Get valid uplift values only
        valid_uplifts = supplier_data.filter(
            (pl.col("uplift_pct").is_not_null()) & 
            (pl.col("promo_status") == "on_promo")
        )
        
        avg_uplift = valid_uplifts["uplift_pct"].mean() if len(valid_uplifts) > 0 else None
        median_uplift = valid_uplifts["uplift_pct"].median() if len(valid_uplifts) > 0 else None
        
        avg_discount = supplier_data.filter(
            pl.col("avg_promo_discount").is_not_null()
        )["avg_promo_discount"].mean() if len(supplier_data) > 0 else None
        
        # Get top performers
        top_performers = []
        if len(valid_uplifts) > 0:
            top_skus = valid_uplifts.sort("uplift_pct", descending=True).head(5)
            
            for row in top_skus.iter_rows(named=True):
                result = PromoDetectionResult(
                    item_code=row["Item_Code"],
                    description=row["Description"],
                    supplier=row["Supplier"],
                    store_name=row["Store Name"],
                    sub_department=row["Sub-Department"],
                    section=row["Section"],
                    analysis_start_date=row["first_date"],
                    analysis_end_date=row["last_date"],
                    promo_days=row["promo_days"],
                    baseline_days=row["baseline_days"],
                    promo_status=PromoStatus(row["promo_status"]),
                    avg_promo_price=row["avg_promo_price"],
                    avg_baseline_price=row["avg_baseline_price"],
                    avg_rrp=row["avg_rrp"],
                    avg_discount_pct=row["avg_promo_discount"],
                    promo_units=row["promo_quantity"],
                    baseline_units=row["baseline_quantity"],
                    promo_uplift_pct=row["uplift_pct"]
                )
                top_performers.append(result)
        
        # Generate insights
        insights = self._generate_insights(
            supplier_data, 
            skus_on_promo, 
            total_skus, 
            avg_uplift,
            avg_discount
        )
        
        # Get coverage from coverage_data
        supplier_coverage = coverage_data.filter(
            pl.col("Supplier").str.to_lowercase().str.contains(supplier.lower())
        )
        avg_coverage = supplier_coverage["promo_coverage_pct"].mean() if len(supplier_coverage) > 0 else None
        
        return PromoPerformanceSummary(
            supplier=supplier,
            category=category,
            sub_department=sub_dept,
            total_skus_analyzed=total_skus,
            skus_on_promo=skus_on_promo,
            promo_sku_pct=(skus_on_promo / total_skus * 100) if total_skus > 0 else 0,
            avg_uplift_pct=avg_uplift,
            median_uplift_pct=median_uplift,
            avg_discount_pct=avg_discount,
            avg_promo_coverage_pct=avg_coverage,
            top_performing_skus=top_performers,
            insights=insights
        )
    
    def _generate_insights(
        self,
        supplier_data: pl.DataFrame,
        skus_on_promo: int,
        total_skus: int,
        avg_uplift: Optional[float],
        avg_discount: Optional[float]
    ) -> List[str]:
        """Generate actionable insights from promo data"""
        insights = []
        
        #  Promo coverage
        promo_pct = (skus_on_promo / total_skus * 100) if total_skus > 0 else 0
        if promo_pct < 30:
            insights.append(
                f"Only {promo_pct:.1f}% of SKUs are on promotion. Consider expanding promo coverage."
            )
        elif promo_pct > 70:
            insights.append(
                f"High promo activity ({promo_pct:.1f}% of SKUs). Evaluate ROI of promotional spend."
            )
        
        #  Uplift performance
        if avg_uplift is not None:
            if avg_uplift > 50:
                insights.append(
                    f"Strong promo performance with {avg_uplift:.1f}% average uplift. Promos are driving significant incremental volume."
                )
            elif avg_uplift > 20:
                insights.append(
                    f"Moderate promo uplift ({avg_uplift:.1f}%). Consider testing deeper discounts or better placement."
                )
            elif avg_uplift > 0:
                insights.append(
                    f"Low promo uplift ({avg_uplift:.1f}%). Promotions may not be cost-effective at current discount levels."
                )
            else:
                insights.append(
                    f"Negative uplift ({avg_uplift:.1f}%). Promos are cannibalizing baseline sales."
                )
        
        # Discount depth
        if avg_discount is not None:
            if avg_discount > 20:
                insights.append(
                    f"Deep discounts ({avg_discount:.1f}% average). Ensure margin remains positive."
                )
            elif avg_discount < 10:
                insights.append(
                    f"Shallow discounts ({avg_discount:.1f}% average). May not be noticeable to consumers."
                )
        
        return insights


def analyze_bidco_promos(df: pl.DataFrame) -> PromoPerformanceSummary:
    """
    Convenience function to analyze Bidco promotions.
    
    """
    detector = PromoDetector(df)
    return detector.get_supplier_summary("BIDCO")

####---UNCOMMENT TO TEST PROMO DETECTION ENGINE---####

# if __name__ == "__main__":
#     """Test promo detection"""
    
#     print("=" * 80)
#     print("PROMO DETECTION ENGINE TEST")
#     print("=" * 80)
#     print()
    
#     # Load data
#     data_path = Path(__file__).parent.parent.parent / "data" / "raw" / "Test_Data.xlsx"
#     print(f"Loading data from {data_path}...")
#     df = pl.read_excel(data_path)
#     print(f" Loaded {len(df):,} records")
#     print()
    
#     # Run promo detection
#     print("Running promo detection...")
#     detector = PromoDetector(df)
#     print(" Promo detector initialized")
#     print()
    
#     # Get Bidco summary
#     print("=" * 80)
#     print("BIDCO PROMO PERFORMANCE")
#     print("=" * 80)
#     bidco_summary = detector.get_supplier_summary("BIDCO")
    
#     print(f"Supplier: {bidco_summary.supplier}")
#     print(f"Sub-Department: {bidco_summary.sub_department}")
#     print()
    
#     print("PORTFOLIO OVERVIEW:")
#     print(f"  Total SKUs Analyzed: {bidco_summary.total_skus_analyzed}")
#     print(f"  SKUs on Promo: {bidco_summary.skus_on_promo} ({bidco_summary.promo_sku_pct:.1f}%)")
#     print()
    
#     print("PERFORMANCE METRICS:")
#     if bidco_summary.avg_uplift_pct is not None:
#         print(f"  Average Uplift: {bidco_summary.avg_uplift_pct:.1f}%")
#     if bidco_summary.median_uplift_pct is not None:
#         print(f"  Median Uplift: {bidco_summary.median_uplift_pct:.1f}%")
#     if bidco_summary.avg_discount_pct is not None:
#         print(f"  Average Discount: {bidco_summary.avg_discount_pct:.1f}%")
#     if bidco_summary.avg_promo_coverage_pct is not None:
#         print(f"  Average Coverage: {bidco_summary.avg_promo_coverage_pct:.1f}% of stores")
#     print()
    
#     if bidco_summary.top_performing_skus:
#         print("TOP PERFORMING SKUS:")
#         for i, sku in enumerate(bidco_summary.top_performing_skus[:5], 1):
#             print(f"{i}. {sku.description[:40]:40s} | "
#                   f"Uplift: {sku.promo_uplift_pct:6.1f}% | "
#                   f"Store: {sku.store_name}")
#         print()
    
#     if bidco_summary.insights:
#         print("KEY INSIGHTS:")
#         for i, insight in enumerate(bidco_summary.insights, 1):
#             print(f"{i}. {insight}")
#         print()
    
#     print("=" * 80)
#     print(" Promo analysis complete!")
#     print("=" * 80)
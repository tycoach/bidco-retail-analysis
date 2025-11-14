"""
Promotional Analysis Module - Cross-Sectional Approach
"""

import sys
from pathlib import Path

# Add src to path for imports
if __name__ == "__main__":
    project_root = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(project_root / "src"))

import polars as pl
from typing import List, Dict, Optional
from datetime import date

from config import PROMO_CONFIG, ANALYSIS_CONFIG
from schema import (
    PromoDetectionResult,
    PromoPerformanceSummary
)
from utils import (
    calculate_realized_price,
    flag_bidco_products,
    filter_valid_transactions
)


class PromoDetector:
    """
    Detects promotions using cross-sectional comparison.
    
    """
    
    def __init__(self, df: pl.DataFrame):
        """Initialize with transaction data."""
        self.df = df
        self._prepare_data()
    
    def _prepare_data(self):
        """Prepare data with necessary derived fields"""
        # Add realized price
        self.df = calculate_realized_price(self.df)
        
        # Flag Bidco products
        self.df = flag_bidco_products(self.df)
        
        # Filter to valid transactions (positive quantities only)
        self.df = filter_valid_transactions(
            self.df, 
            allow_negatives=False, 
            allow_zeros=False
        )
        
        # Calculate discount percentage
        self.df = self.df.with_columns([
            pl.when(pl.col("RRP").is_not_null() & (pl.col("RRP") > 0))
            .then(
                ((pl.col("RRP") - pl.col("realized_unit_price")) / pl.col("RRP") * 100)
            )
            .otherwise(None)
            .alias("discount_pct")
        ])
        
        # Flag promo observations (discount >= threshold)
        self.df = self.df.with_columns([
            pl.when(
                pl.col("discount_pct").is_not_null() & 
                (pl.col("discount_pct") >= PROMO_CONFIG.discount_threshold_pct)
            )
            .then(pl.lit(True))
            .otherwise(pl.lit(False))
            .alias("is_promo")
        ])
    
    def detect_promos_cross_sectional(
        self,
        supplier: Optional[str] = None,
        min_stores: int = 2
    ) -> pl.DataFrame:
        """
        Detect promotions using cross-sectional approach.
        
        """
        df = self.df
        
        # Filter to supplier if specified
        if supplier:
            df = df.filter(
                pl.col("Supplier").str.to_lowercase().str.contains(supplier.lower())
            )
        
        # Aggregate by SKU and Store, then classify as promo or baseline
        store_sku_summary = df.group_by(["Item_Code", "Description", "Supplier", "Store Name"]).agg([
            pl.col("Quantity").sum().alias("total_units"),
            pl.col("Total Sales").sum().alias("total_sales"),
            pl.col("realized_unit_price").mean().alias("avg_price"),
            pl.col("RRP").median().alias("median_rrp"),
            pl.col("discount_pct").mean().alias("avg_discount_pct"),
            pl.col("is_promo").max().alias("store_has_promo"),  # If any promo, flag store
            pl.len().alias("transaction_count")
        ])
        
        # Now aggregate across stores to compare promo stores vs baseline stores
        sku_analysis = store_sku_summary.group_by(["Item_Code", "Description", "Supplier"]).agg([
            # Promo stores metrics
            pl.when(pl.col("store_has_promo"))
            .then(pl.col("total_units"))
            .otherwise(None)
            .sum()
            .alias("promo_units"),
            
            pl.when(pl.col("store_has_promo"))
            .then(pl.col("Store Name"))
            .otherwise(None)
            .n_unique()
            .alias("promo_stores"),
            
            pl.when(pl.col("store_has_promo"))
            .then(pl.col("avg_price"))
            .otherwise(None)
            .mean()
            .alias("avg_promo_price"),
            
            pl.when(pl.col("store_has_promo"))
            .then(pl.col("avg_discount_pct"))
            .otherwise(None)
            .mean()
            .alias("avg_promo_discount"),
            
            # Baseline stores metrics
            pl.when(~pl.col("store_has_promo"))
            .then(pl.col("total_units"))
            .otherwise(None)
            .sum()
            .alias("baseline_units"),
            
            pl.when(~pl.col("store_has_promo"))
            .then(pl.col("Store Name"))
            .otherwise(None)
            .n_unique()
            .alias("baseline_stores"),
            
            pl.when(~pl.col("store_has_promo"))
            .then(pl.col("avg_price"))
            .otherwise(None)
            .mean()
            .alias("avg_baseline_price"),
            
            # Overall metrics
            pl.col("Store Name").n_unique().alias("total_stores"),
            pl.col("median_rrp").median().alias("median_rrp")
        ])
        
        # Calculate uplift and coverage
        sku_analysis = sku_analysis.with_columns([
            # Promo uplift % (cross-sectional)
            pl.when(
                (pl.col("baseline_units") > 0) & 
                (pl.col("promo_units") > 0) &
                (pl.col("baseline_stores") >= 1) &
                (pl.col("promo_stores") >= 1)
            )
            .then(
                # Average units per store for fair comparison
                ((pl.col("promo_units") / pl.col("promo_stores")) - 
                 (pl.col("baseline_units") / pl.col("baseline_stores"))) /
                (pl.col("baseline_units") / pl.col("baseline_stores")) * 100
            )
            .otherwise(None)
            .alias("promo_uplift_pct"),
            
            # Promo coverage %
            pl.when(pl.col("total_stores") > 0)
            .then(
                (pl.col("promo_stores") / pl.col("total_stores") * 100)
            )
            .otherwise(0.0)
            .alias("promo_coverage_pct"),
            
            # Status classification
            pl.when(
                (pl.col("promo_stores") >= 1) & 
                (pl.col("baseline_stores") >= 1)
            )
            .then(pl.lit("on_promo"))
            .when(pl.col("baseline_stores") >= min_stores)
            .then(pl.lit("baseline"))
            .otherwise(pl.lit("insufficient_data"))
            .alias("promo_status")
        ])
        
        return sku_analysis
    
    def get_promo_results(
        self,
        supplier: Optional[str] = None,
        min_uplift: Optional[float] = None
    ) -> List[PromoDetectionResult]:
        """
        Get promotional detection results as Pydantic objects.
        """
        promo_data = self.detect_promos_cross_sectional(supplier)
        
        # Filter to SKUs with valid promo status
        promo_data = promo_data.filter(pl.col("promo_status") == "on_promo")
        
        # Optional: filter by minimum uplift
        if min_uplift is not None:
            promo_data = promo_data.filter(
                pl.col("promo_uplift_pct").is_not_null() &
                (pl.col("promo_uplift_pct") >= min_uplift)
            )
        
        results = []
        for row in promo_data.iter_rows(named=True):
            result = PromoDetectionResult(
                item_code=row["Item_Code"],
                description=row["Description"],
                supplier=row["Supplier"],
                promo_status="on_promo",
                promo_stores=row["promo_stores"],
                baseline_stores=row["baseline_stores"],
                total_stores=row["total_stores"],
                promo_units=row["promo_units"],
                baseline_units=row["baseline_units"],
                promo_uplift_pct=row["promo_uplift_pct"],
                avg_promo_price=row["avg_promo_price"],
                avg_baseline_price=row["avg_baseline_price"],
                avg_discount_pct=row["avg_promo_discount"],
                promo_coverage_pct=row["promo_coverage_pct"],
                median_rrp=row["median_rrp"]
            )
            results.append(result)
        
        return results
    
    def get_supplier_summary(
        self,
        supplier: str = "BIDCO"
    ) -> PromoPerformanceSummary:
        """
        Get promotional performance summary for a supplier.
        """
        # Get all promo results
        promo_data = self.detect_promos_cross_sectional(supplier)
        
        # Get overall portfolio stats
        total_skus = len(promo_data)
        on_promo = promo_data.filter(pl.col("promo_status") == "on_promo")
        skus_on_promo = len(on_promo)
        
        # Calculate average metrics (only for SKUs on promo)
        if len(on_promo) > 0:
            avg_uplift = on_promo["promo_uplift_pct"].mean()
            median_uplift = on_promo["promo_uplift_pct"].median()
            avg_discount = on_promo["avg_promo_discount"].mean()
            avg_coverage = on_promo["promo_coverage_pct"].mean()
            
            # Get top performers (by uplift, with minimum volume)
            top_performers = on_promo.filter(
                pl.col("promo_units") >= 50  # Minimum 50 units for significance
            ).sort("promo_uplift_pct", descending=True).head(10)
            
            top_skus = []
            for row in top_performers.iter_rows(named=True):
                top_skus.append({
                    "item_code": row["Item_Code"],
                    "description": row["Description"],
                    "uplift_pct": row["promo_uplift_pct"],
                    "promo_units": row["promo_units"],
                    "discount_pct": row["avg_promo_discount"],
                    "coverage_pct": row["promo_coverage_pct"]
                })
        else:
            avg_uplift = None
            median_uplift = None
            avg_discount = None
            avg_coverage = None
            top_skus = []
        
        # Generate insights
        insights = self._generate_insights(
            total_skus,
            skus_on_promo,
            avg_uplift,
            avg_discount,
            avg_coverage
        )
        
        return PromoPerformanceSummary(
            supplier=supplier,
            analysis_date=date.today(),
            total_skus=total_skus,
            skus_on_promo=skus_on_promo,
            promo_sku_pct=(skus_on_promo / total_skus * 100) if total_skus > 0 else 0.0,
            avg_uplift_pct=avg_uplift,
            median_uplift_pct=median_uplift,
            avg_discount_pct=avg_discount,
            avg_promo_coverage_pct=avg_coverage,
            top_performing_skus=top_skus,
            insights=insights,
            methodology="cross_sectional"
        )
    
    def _generate_insights(
        self,
        total_skus: int,
        skus_on_promo: int,
        avg_uplift: Optional[float],
        avg_discount: Optional[float],
        avg_coverage: Optional[float]
    ) -> List[str]:
        """Generate business insights from promo analysis"""
        insights = []
        
        if total_skus == 0:
            insights.append("No SKUs found for analysis.")
            return insights
        
        promo_pct = (skus_on_promo / total_skus) * 100
        
        # Promo coverage insight
        if promo_pct < 10:
            insights.append(
                f"Only {promo_pct:.1f}% of SKUs are on promotion. "
                "Consider expanding promo coverage."
            )
        elif promo_pct > 50:
            insights.append(
                f"{promo_pct:.1f}% of SKUs are on promotion. "
                "High promotional intensity."
            )
        
        # Uplift insight
        if avg_uplift is not None:
            if avg_uplift < 5:
                insights.append(
                    f"Low average uplift ({avg_uplift:.1f}%). "
                    "Promotions may not be deep enough to drive volume."
                )
            elif avg_uplift > 20:
                insights.append(
                    f"Strong average uplift ({avg_uplift:.1f}%). "
                    "Promotions are effectively driving incremental volume."
                )
            else:
                insights.append(
                    f"Moderate average uplift ({avg_uplift:.1f}%). "
                    "Promotions are having a positive impact."
                )
        
        # Discount depth insight
        if avg_discount is not None:
            if avg_discount < 15:
                insights.append(
                    f"Shallow discount depth ({avg_discount:.1f}%). "
                    "Consider deeper discounts to maximize impact."
                )
            elif avg_discount > 30:
                insights.append(
                    f"Deep discount depth ({avg_discount:.1f}%). "
                    "Review margin impact of heavy discounting."
                )
        
        # Store coverage insight
        if avg_coverage is not None:
            if avg_coverage < 30:
                insights.append(
                    f"Limited store coverage ({avg_coverage:.1f}%). "
                    "Promotions are regional rather than national."
                )
            elif avg_coverage > 70:
                insights.append(
                    f"High store coverage ({avg_coverage:.1f}%). "
                    "Promotions are widely distributed."
                )
        
        return insights


def analyze_bidco_promos(df: pl.DataFrame) -> PromoPerformanceSummary:
    """
    Convenience function to analyze Bidco promotional performance.
    
    """
    detector = PromoDetector(df)
    return detector.get_supplier_summary("BIDCO")

##--UNCOMMENT TO TEST PROMOTIONAL ANALYSIS --##

# if __name__ == "__main__":
#     """Test promotional analysis with cross-sectional approach"""
    
#     print("=" * 80)
#     print("PROMOTIONAL ANALYSIS TEST - CROSS-SECTIONAL APPROACH")
#     print("=" * 80)
#     print()
    
#     print("METHODOLOGY:")
#     print("  Comparing stores WITH promos vs stores WITHOUT promos for same SKUs")
#     print("  (Cross-sectional comparison, not time-series)")
#     print()
    
#     # Load data
#     data_path = Path(__file__).parent.parent.parent / "data" / "raw" / "Test_Data.xlsx"
#     print(f"Loading data from {data_path}...")
#     df = pl.read_excel(data_path)
#     print(f"Loaded {len(df):,} records")
#     print()
    
#     # Analyze promotions
#     print("Detecting promotions...")
#     detector = PromoDetector(df)
#     summary = detector.get_supplier_summary("BIDCO")
#     print("Promotional analysis complete")
#     print()
    
#     # Display results
#     print("=" * 80)
#     print("BIDCO PROMOTIONAL PERFORMANCE")
#     print("=" * 80)
#     print(f"Analysis Date: {summary.analysis_date}")
#     print(f"Methodology: {summary.methodology.upper()}")
#     print()
    
#     print("PORTFOLIO OVERVIEW:")
#     print(f"  Total SKUs: {summary.total_skus}")
#     print(f"  SKUs on Promo: {summary.skus_on_promo} ({summary.promo_sku_pct:.1f}%)")
#     print()
    
#     if summary.skus_on_promo > 0:
#         print("PERFORMANCE METRICS:")
#         if summary.avg_uplift_pct is not None:
#             print(f"  Average Uplift: {summary.avg_uplift_pct:.1f}%")
#             print(f"  Median Uplift: {summary.median_uplift_pct:.1f}%")
#         if summary.avg_discount_pct is not None:
#             print(f"  Average Discount: {summary.avg_discount_pct:.1f}%")
#         if summary.avg_promo_coverage_pct is not None:
#             print(f"  Average Coverage: {summary.avg_promo_coverage_pct:.1f}% of stores")
#         print()
        
#         if summary.top_performing_skus:
#             print("TOP PERFORMING SKUs:")
#             for i, sku in enumerate(summary.top_performing_skus[:5], 1):
#                 print(f"{i}. {sku['description'][:50]:50s}")
#                 print(f"   Uplift: {sku['uplift_pct']:>6.1f}% | "
#                       f"Units: {sku['promo_units']:>6.0f} | "
#                       f"Discount: {sku['discount_pct']:>5.1f}% | "
#                       f"Coverage: {sku['coverage_pct']:>5.1f}%")
#             print()
    
#     if summary.insights:
#         print("KEY INSIGHTS:")
#         for i, insight in enumerate(summary.insights, 1):
#             print(f"{i}. {insight}")
#         print()
    
#     print("=" * 80)
#     print("Promotional analysis complete!")
#     print("=" * 80)
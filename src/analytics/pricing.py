"""
Price Index Calculator
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

from config import PRICE_INDEX_CONFIG, ANALYSIS_CONFIG
from schema import (
    PriceIndexResult,
    PriceIndexSummary,
    PricePosition
)
from utils import (
    calculate_realized_price,
    flag_bidco_products,
    create_competitive_set_key,
    filter_valid_transactions
)


class PriceIndexCalculator:
    """
    Calculates price indices for a target supplier against competitors.
    """
    
    def __init__(self, df: pl.DataFrame):
        """
        Initialize with transaction data.
        """
        self.df = df
        self._prepare_data()
    
    def _prepare_data(self):
        """Prepare data with necessary derived fields"""
        # Add realized price
        self.df = calculate_realized_price(self.df)
        
        # Flag Bidco products
        self.df = flag_bidco_products(self.df)
        
        # Create competitive set key
        self.df = create_competitive_set_key(
            self.df,
            grouping_cols=ANALYSIS_CONFIG.competitive_grouping
        )
        
        # Filter to valid transactions
        self.df = filter_valid_transactions(self.df, allow_negatives=False, allow_zeros=False)
    
    def calculate_price_index(
        self,
        target_supplier: str = "BIDCO",
        by_store: bool = True
    ) -> pl.DataFrame:
        """
        Calculate price index for target supplier vs competitors.
        """
        # Group columns
        if by_store:
            group_cols = ["Store Name", "competitive_set_key", "Item_Code"]
        else:
            group_cols = ["competitive_set_key", "Item_Code"]
        
        # Calculate average prices per SKU per competitive set (and store if applicable)
        price_summary = self.df.group_by(group_cols).agg([
            pl.col("Description").first(),
            pl.col("Supplier").first(),
            pl.col("Sub-Department").first(),
            pl.col("Section").first(),
            pl.col("is_bidco").first(),
            pl.col("realized_unit_price").mean().alias("avg_realized_price"),
            pl.col("RRP").median().alias("median_rrp"),
            pl.len().alias("transaction_count")
        ])
        
        # Filter to SKUs with minimum transactions
        price_summary = price_summary.filter(
            pl.col("transaction_count") >= PRICE_INDEX_CONFIG.min_transactions_for_price
        )
        
        # Calculate competitive set averages (excluding target supplier)
        comp_set_cols = ["competitive_set_key"]
        if by_store:
            comp_set_cols.append("Store Name")
        
        # Get competitor prices (not Bidco)
        competitor_prices = price_summary.filter(~pl.col("is_bidco")).group_by(comp_set_cols).agg([
            pl.col("avg_realized_price").mean().alias("competitor_avg_price"),
            pl.len().alias("competitor_count"),
            pl.col("transaction_count").sum().alias("competitor_transactions")
        ])
        
        # Filter to competitive sets with minimum competitors
        competitor_prices = competitor_prices.filter(
            pl.col("competitor_count") >= PRICE_INDEX_CONFIG.min_competitors_for_index
        )
        
        # Get target supplier prices
        target_prices = price_summary.filter(
            pl.col("Supplier").str.to_lowercase().str.contains(target_supplier.lower())
        )
        
        # Join target with competitors
        price_index = target_prices.join(
            competitor_prices,
            on=comp_set_cols,
            how="left"
        )
        
        # Calculate price index
        price_index = price_index.with_columns([
            # Price index = Bidco / Competitor average
            (pl.col("avg_realized_price") / pl.col("competitor_avg_price")).alias("price_index"),
            
            # Price vs RRP
            pl.when(pl.col("median_rrp").is_not_null())
            .then(
                ((pl.col("avg_realized_price") - pl.col("median_rrp")) / pl.col("median_rrp") * 100)
            )
            .otherwise(None)
            .alias("price_vs_rrp_pct")
        ])
        
        # Determine price position
        price_index = price_index.with_columns([
            pl.when(pl.col("price_index").is_null())
            .then(pl.lit("insufficient_data"))
            .when(pl.col("price_index") > PRICE_INDEX_CONFIG.premium_threshold)
            .then(pl.lit("premium"))
            .when(pl.col("price_index") < PRICE_INDEX_CONFIG.discount_threshold)
            .then(pl.lit("discount"))
            .otherwise(pl.lit("at_market"))
            .alias("price_position")
        ])
        
        return price_index
    
    def get_price_index_results(
        self,
        target_supplier: str = "BIDCO",
        by_store: bool = True
    ) -> List[PriceIndexResult]:
        """
        Get price index results as Pydantic objects.
        """
        price_data = self.calculate_price_index(target_supplier, by_store)
        
        results = []
        for row in price_data.iter_rows(named=True):
            result = PriceIndexResult(
                item_code=row["Item_Code"],
                description=row["Description"],
                supplier=row["Supplier"],
                store_name=row.get("Store Name") if by_store else None,
                sub_department=row["Sub-Department"],
                section=row["Section"],
                bidco_avg_price=row["avg_realized_price"],
                bidco_avg_rrp=row["median_rrp"],
                competitor_avg_price=row["competitor_avg_price"],
                competitor_count=row["competitor_count"],
                price_index=row["price_index"],
                price_position=PricePosition(row["price_position"]),
                price_vs_rrp_pct=row["price_vs_rrp_pct"],
                bidco_transaction_count=row["transaction_count"],
                competitor_transaction_count=row["competitor_transactions"]
            )
            results.append(result)
        
        return results
    
    def get_price_summary(
        self,
        target_supplier: str = "BIDCO"
    ) -> PriceIndexSummary:
        """
        Get aggregated price index summary.
        """
        # Get store-level indices
        store_level = self.calculate_price_index(target_supplier, by_store=True)
        
        # Get portfolio-level indices
        portfolio_level = self.calculate_price_index(target_supplier, by_store=False)
        
        # Calculate summary statistics
        valid_indices = portfolio_level.filter(pl.col("price_index").is_not_null())
        
        total_skus = len(valid_indices)
        premium_skus = len(valid_indices.filter(pl.col("price_position") == "premium"))
        at_market_skus = len(valid_indices.filter(pl.col("price_position") == "at_market"))
        discount_skus = len(valid_indices.filter(pl.col("price_position") == "discount"))
        
        avg_index = valid_indices["price_index"].mean() if len(valid_indices) > 0 else 0.0
        median_index = valid_indices["price_index"].median() if len(valid_indices) > 0 else 0.0
        
        # Store-level indices
        store_indices = {}
        if len(store_level) > 0:
            store_summary = store_level.group_by("Store Name").agg([
                pl.col("price_index").mean().alias("avg_store_index")
            ])
            
            for row in store_summary.iter_rows(named=True):
                if row["avg_store_index"] is not None:
                    store_indices[row["Store Name"]] = row["avg_store_index"]
        
        # Category-level indices
        category_indices = {}
        if len(portfolio_level) > 0:
            category_summary = portfolio_level.group_by("Sub-Department").agg([
                pl.col("price_index").mean().alias("avg_category_index")
            ])
            
            for row in category_summary.iter_rows(named=True):
                if row["avg_category_index"] is not None:
                    category_indices[row["Sub-Department"]] = row["avg_category_index"]
        
        # Generate recommendations
        recommendations = self._generate_recommendations(
            avg_index,
            premium_skus,
            at_market_skus,
            discount_skus,
            total_skus,
            category_indices
        )
        
        return PriceIndexSummary(
            supplier=target_supplier,
            analysis_date=date.today(),
            total_skus=total_skus,
            premium_skus=premium_skus,
            at_market_skus=at_market_skus,
            discount_skus=discount_skus,
            avg_price_index=avg_index,
            median_price_index=median_index,
            store_level_indices=store_indices,
            category_indices=category_indices,
            price_opportunities=recommendations
        )
    
    def _generate_recommendations(
        self,
        avg_index: float,
        premium_count: int,
        at_market_count: int,
        discount_count: int,
        total_count: int,
        category_indices: Dict[str, float]
    ) -> List[str]:
        """Generate pricing recommendations"""
        recommendations = []
        
        if total_count == 0:
            recommendations.append("Insufficient data for competitive comparison.")
            return recommendations
        
        # Overall positioning
        if avg_index > 1.15:
            recommendations.append(
                f"Overall premium pricing (index: {avg_index:.2f}). "
                "Consider selective price reductions on high-volume SKUs."
            )
        elif avg_index < 0.85:
            recommendations.append(
                f"Overall discount positioning (index: {avg_index:.2f}). "
                "Opportunity to increase prices without losing competitiveness."
            )
        else:
            recommendations.append(
                f"Competitive pricing (index: {avg_index:.2f}). Well-positioned vs market."
            )
        
        # Portfolio mix
        premium_pct = (premium_count / total_count) * 100
        discount_pct = (discount_count / total_count) * 100
        
        if premium_pct > 50:
            recommendations.append(
                f"{premium_pct:.0f}% of SKUs are premium-priced. "
                "Review if premium positioning is supported by brand perception."
            )
        
        if discount_pct > 50:
            recommendations.append(
                f"{discount_pct:.0f}% of SKUs are discount-priced. "
                "Potential margin opportunity through selective price increases."
            )
        
        # Category-specific
        if category_indices:
            max_category = max(category_indices.items(), key=lambda x: x[1])
            min_category = min(category_indices.items(), key=lambda x: x[1])
            
            if max_category[1] > 1.2:
                recommendations.append(
                    f"{max_category[0]} is significantly premium (index: {max_category[1]:.2f}). "
                    "Consider price testing to optimize volume."
                )
            
            if min_category[1] < 0.8:
                recommendations.append(
                    f"{min_category[0]} is deeply discounted (index: {min_category[1]:.2f}). "
                    "Opportunity for price increase."
                )
        
        return recommendations


def analyze_bidco_pricing(df: pl.DataFrame) -> PriceIndexSummary:
    """
    Analyze Bidco's pricing position and return summary.
    """
    calculator = PriceIndexCalculator(df)
    return calculator.get_price_summary("BIDCO")

####--UNCOMMENT TO TEST --####

# if __name__ == "__main__":
#     """Test price index calculation"""
    
#     print("=" * 80)
#     print("PRICE INDEX CALCULATOR TEST")
#     print("=" * 80)
#     print()
    
#     # Load data
#     data_path = Path(__file__).parent.parent.parent / "data" / "raw" / "Test_Data.xlsx"
#     print(f"Loading data from {data_path}...")
#     df = pl.read_excel(data_path)
#     print(f"Loaded {len(df):,} records")
#     print()
    
#     # Calculate price indices
#     print("Calculating price indices...")
#     calculator = PriceIndexCalculator(df)
#     summary = calculator.get_price_summary("BIDCO")
#     print("Price analysis complete")
#     print()
    
#     # Display results
#     print("=" * 80)
#     print("BIDCO PRICE POSITIONING")
#     print("=" * 80)
#     print(f"Analysis Date: {summary.analysis_date}")
#     print()
    
#     print("PORTFOLIO OVERVIEW:")
#     print(f"  Total SKUs: {summary.total_skus}")
#     print(f"  Premium Positioned: {summary.premium_skus} ({summary.premium_skus/summary.total_skus*100:.1f}%)")
#     print(f"  At Market: {summary.at_market_skus} ({summary.at_market_skus/summary.total_skus*100:.1f}%)")
#     print(f"  Discount Positioned: {summary.discount_skus} ({summary.discount_skus/summary.total_skus*100:.1f}%)")
#     print()
    
#     print("PRICE INDICES:")
#     print(f"  Average Index: {summary.avg_price_index:.3f}")
#     print(f"  Median Index: {summary.median_price_index:.3f}")
#     print(f"  Interpretation: <0.9 discount, 0.9-1.1 at market, >1.1 premium")
#     print()
    
#     if summary.category_indices:
#         print("CATEGORY-LEVEL POSITIONING:")
#         for category, index in sorted(summary.category_indices.items(), key=lambda x: x[1], reverse=True):
#             position = "PREMIUM" if index > 1.1 else "DISCOUNT" if index < 0.9 else "AT MARKET"
#             print(f"  {category:30s}: {index:.3f} ({position})")
#         print()
    
#     if summary.store_level_indices:
#         print(f"STORE-LEVEL VARIANCE (showing top 10):")
#         sorted_stores = sorted(summary.store_level_indices.items(), key=lambda x: x[1], reverse=True)
#         for store, index in sorted_stores[:10]:
#             position = "PREMIUM" if index > 1.1 else "DISCOUNT" if index < 0.9 else "AT MARKET"
#             print(f"  {store:30s}: {index:.3f} ({position})")
#         print()
    
#     if summary.price_opportunities:
#         print("PRICING RECOMMENDATIONS:")
#         for i, rec in enumerate(summary.price_opportunities, 1):
#             print(f"{i}. {rec}")
#         print()
    
#     print("=" * 80)
#     print(" Price index analysis complete!")
#     print("=" * 80)
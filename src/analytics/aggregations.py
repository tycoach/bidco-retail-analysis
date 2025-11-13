"""
KPI Aggregations

"""

import sys
from pathlib import Path

# Add src to path for imports
if __name__ == "__main__":
    project_root = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(project_root / "src"))

import polars as pl
from typing import Dict, List, Optional
from datetime import date

from utils import (
    calculate_realized_price,
    flag_bidco_products,
    filter_valid_transactions,
    format_currency,
    format_percentage,
    format_number
)


class KPIAggregator:
    """
    Aggregates transaction data into business KPIs.
    """
    
    def __init__(self, df: pl.DataFrame):
        """
        Initialize with transaction data.
        """
        self.df = df
        self._prepare_data()
    
    def _prepare_data(self):
        """Prepare data with necessary derived fields"""
        self.df = calculate_realized_price(self.df)
        self.df = flag_bidco_products(self.df)
        self.df = filter_valid_transactions(self.df, allow_negatives=False, allow_zeros=False)
    
    def get_market_overview(self) -> Dict:
        """Get high-level market metrics"""
        return {
            "total_sales": self.df["Total Sales"].sum(),
            "total_units": self.df["Quantity"].sum(),
            "total_transactions": len(self.df),
            "unique_stores": self.df["Store Name"].n_unique(),
            "unique_suppliers": self.df["Supplier"].n_unique(),
            "unique_skus": self.df["Item_Code"].n_unique(),
            "avg_transaction_value": self.df["Total Sales"].mean(),
            "avg_unit_price": self.df["realized_unit_price"].mean(),
            "date_range": {
                "start": str(self.df["Date Of Sale"].min()),
                "end": str(self.df["Date Of Sale"].max())
            }
        }
    
    def get_supplier_metrics(self, supplier: str = "BIDCO") -> Dict:
        """Get metrics for a specific supplier"""
        supplier_df = self.df.filter(
            pl.col("Supplier").str.to_lowercase().str.contains(supplier.lower())
        )
        
        total_market_sales = self.df["Total Sales"].sum()
        supplier_sales = supplier_df["Total Sales"].sum()
        
        return {
            "supplier": supplier,
            "total_sales": supplier_sales,
            "total_units": supplier_df["Quantity"].sum(),
            "total_transactions": len(supplier_df),
            "market_share_pct": (supplier_sales / total_market_sales * 100) if total_market_sales > 0 else 0,
            "unique_skus": supplier_df["Item_Code"].n_unique(),
            "stores_present": supplier_df["Store Name"].n_unique(),
            "avg_unit_price": supplier_df["realized_unit_price"].mean(),
            "categories": supplier_df["Category"].unique().to_list()
        }
    
    def get_category_breakdown(self, supplier: Optional[str] = None) -> List[Dict]:
        """Get sales by category"""
        df = self.df
        
        if supplier:
            df = df.filter(
                pl.col("Supplier").str.to_lowercase().str.contains(supplier.lower())
            )
        
        category_summary = df.group_by("Category").agg([
            pl.col("Total Sales").sum().alias("sales"),
            pl.col("Quantity").sum().alias("units"),
            pl.len().alias("transactions"),
            pl.col("Item_Code").n_unique().alias("unique_skus")
        ]).sort("sales", descending=True)
        
        total_sales = df["Total Sales"].sum()
        
        results = []
        for row in category_summary.iter_rows(named=True):
            results.append({
                "category": row["Category"],
                "sales": row["sales"],
                "units": row["units"],
                "transactions": row["transactions"],
                "unique_skus": row["unique_skus"],
                "sales_share_pct": (row["sales"] / total_sales * 100) if total_sales > 0 else 0
            })
        
        return results
    
    def get_store_rankings(
        self,
        supplier: Optional[str] = None,
        top_n: int = 10
    ) -> List[Dict]:
        """Get top stores by sales"""
        df = self.df
        
        if supplier:
            df = df.filter(
                pl.col("Supplier").str.to_lowercase().str.contains(supplier.lower())
            )
        
        store_summary = df.group_by("Store Name").agg([
            pl.col("Total Sales").sum().alias("sales"),
            pl.col("Quantity").sum().alias("units"),
            pl.len().alias("transactions"),
            pl.col("Item_Code").n_unique().alias("unique_skus")
        ]).sort("sales", descending=True).head(top_n)
        
        results = []
        for row in store_summary.iter_rows(named=True):
            results.append({
                "store": row["Store Name"],
                "sales": row["sales"],
                "units": row["units"],
                "transactions": row["transactions"],
                "unique_skus": row["unique_skus"],
                "avg_transaction_value": row["sales"] / row["transactions"] if row["transactions"] > 0 else 0
            })
        
        return results
    
    def get_top_skus(
        self,
        supplier: Optional[str] = None,
        by: str = "sales",
        top_n: int = 10
    ) -> List[Dict]:
        """
        Get top SKUs.
        """
        df = self.df
        
        if supplier:
            df = df.filter(
                pl.col("Supplier").str.to_lowercase().str.contains(supplier.lower())
            )
        
        sku_summary = df.group_by(["Item_Code", "Description", "Supplier"]).agg([
            pl.col("Total Sales").sum().alias("sales"),
            pl.col("Quantity").sum().alias("units"),
            pl.len().alias("transactions"),
            pl.col("Store Name").n_unique().alias("stores_present")
        ])
        
        sort_col = "sales" if by == "sales" else "units"
        sku_summary = sku_summary.sort(sort_col, descending=True).head(top_n)
        
        results = []
        for row in sku_summary.iter_rows(named=True):
            results.append({
                "item_code": row["Item_Code"],
                "description": row["Description"],
                "supplier": row["Supplier"],
                "sales": row["sales"],
                "units": row["units"],
                "transactions": row["transactions"],
                "stores_present": row["stores_present"]
            })
        
        return results
    
    def get_daily_trends(self, supplier: Optional[str] = None) -> List[Dict]:
        """Get daily sales trends"""
        df = self.df
        
        if supplier:
            df = df.filter(
                pl.col("Supplier").str.to_lowercase().str.contains(supplier.lower())
            )
        
        daily_summary = df.group_by("Date Of Sale").agg([
            pl.col("Total Sales").sum().alias("sales"),
            pl.col("Quantity").sum().alias("units"),
            pl.len().alias("transactions")
        ]).sort("Date Of Sale")
        
        results = []
        for row in daily_summary.iter_rows(named=True):
            results.append({
                "date": str(row["Date Of Sale"]),
                "sales": row["sales"],
                "units": row["units"],
                "transactions": row["transactions"]
            })
        
        return results
    
    def generate_executive_summary(self, supplier: str = "BIDCO") -> Dict:
        """
        Generate executive summary with all key metrics.
        """
        market = self.get_market_overview()
        supplier_metrics = self.get_supplier_metrics(supplier)
        categories = self.get_category_breakdown(supplier)
        top_stores = self.get_store_rankings(supplier, top_n=5)
        top_products = self.get_top_skus(supplier, top_n=5)
        
        return {
            "summary_date": str(date.today()),
            "supplier": supplier,
            "market_overview": market,
            "supplier_performance": supplier_metrics,
            "category_breakdown": categories,
            "top_stores": top_stores,
            "top_products": top_products,
            "key_metrics": {
                "market_share": format_percentage(supplier_metrics["market_share_pct"]),
                "total_sales": format_currency(supplier_metrics["total_sales"]),
                "total_units": format_number(supplier_metrics["total_units"]),
                "avg_unit_price": format_currency(supplier_metrics["avg_unit_price"]),
                "store_coverage": f"{supplier_metrics['stores_present']} of {market['unique_stores']} stores"
            }
        }


def generate_bidco_summary(df: pl.DataFrame) -> Dict:
    """
    Convenience function to generate Bidco executive summary.
    """
    aggregator = KPIAggregator(df)
    return aggregator.generate_executive_summary("BIDCO")


# if __name__ == "__main__":
#     """Test KPI aggregation"""
    
#     print("=" * 80)
#     print("KPI AGGREGATION TEST")
#     print("=" * 80)
#     print()
    
#     # Load data
#     data_path = Path(__file__).parent.parent.parent / "data" / "raw" / "Test_Data.xlsx"
#     print(f"Loading data from {data_path}...")
#     df = pl.read_excel(data_path)
#     print(f"Loaded {len(df):,} records")
#     print()
    
#     # Generate summary
#     print("Generating executive summary...")
#     aggregator = KPIAggregator(df)
#     summary = aggregator.generate_executive_summary("BIDCO")
#     print(" Summary generated")
#     print()
    
#     # Display results
#     print("=" * 80)
#     print(f"EXECUTIVE SUMMARY - {summary['supplier']}")
#     print(f"Date: {summary['summary_date']}")
#     print("=" * 80)
#     print()
    
#     print("KEY METRICS:")
#     for metric, value in summary["key_metrics"].items():
#         print(f"  {metric.replace('_', ' ').title():20s}: {value}")
#     print()
    
#     print("MARKET CONTEXT:")
#     market = summary["market_overview"]
#     print(f"  Total Market Size: {format_currency(market['total_sales'])}")
#     print(f"  Total Stores: {market['unique_stores']}")
#     print(f"  Total Suppliers: {market['unique_suppliers']}")
#     print(f"  Date Range: {market['date_range']['start']} to {market['date_range']['end']}")
#     print()
    
#     print("CATEGORY PERFORMANCE:")
#     for cat in summary["category_breakdown"]:
#         print(f"  {cat['category']:15s}: {format_currency(cat['sales']):>15s} "
#               f"({cat['sales_share_pct']:5.1f}% of {summary['supplier']} sales)")
#     print()
    
#     print("TOP 5 STORES:")
#     for i, store in enumerate(summary["top_stores"], 1):
#         print(f"{i}. {store['store']:20s}: {format_currency(store['sales']):>15s} "
#               f"({store['transactions']:>4,} txns)")
#     print()
    
#     print("TOP 5 PRODUCTS:")
#     for i, product in enumerate(summary["top_products"], 1):
#         print(f"{i}. {product['description'][:40]:40s}: {format_currency(product['sales']):>15s}")
#     print()
    
#     print("=" * 80)
#     print(" KPI aggregation complete!")
#     print("=" * 80)
"""
Utility Functions 
"""

import polars as pl
from typing import Optional, List, Tuple
from datetime import datetime
from pathlib import Path


def calculate_realized_price(df: pl.DataFrame) -> pl.DataFrame:
    """
    Calculate realized unit price from total sales and quantity.
    """
    return df.with_columns([
        pl.when(pl.col("Quantity") != 0)
        .then(pl.col("Total Sales") / pl.col("Quantity"))
        .otherwise(None)
        .alias("realized_unit_price")
    ])


def calculate_discount_pct(df: pl.DataFrame) -> pl.DataFrame:
    """
    Calculate discount percentage vs RRP.
    """
    df = calculate_realized_price(df)
    
    return df.with_columns([
        pl.when((pl.col("RRP").is_not_null()) & (pl.col("RRP") != 0))
        .then(
            ((pl.col("RRP") - pl.col("realized_unit_price")) / pl.col("RRP")) * 100
        )
        .otherwise(None)
        .alias("discount_pct")
    ])


def flag_bidco_products(df: pl.DataFrame, supplier_col: str = "Supplier") -> pl.DataFrame:
    """
    Add a boolean column indicating if product is from Bidco.
    """
    return df.with_columns([
        pl.col(supplier_col).str.to_lowercase().str.contains("bidco").alias("is_bidco")
    ])


def create_competitive_set_key(
    df: pl.DataFrame,
    grouping_cols: List[str] = ["Sub-Department", "Section"]
) -> pl.DataFrame:
    """
    Create a composite key for competitive set grouping.
    """
    # Concatenate the grouping columns with a separator
    key_expr = pl.concat_str(
        [pl.col(col) for col in grouping_cols],
        separator="|"
    ).alias("competitive_set_key")
    
    return df.with_columns([key_expr])


def filter_valid_transactions(
    df: pl.DataFrame,
    allow_negatives: bool = False,
    allow_zeros: bool = False
) -> pl.DataFrame:
    """
    Filter to valid transactions only.
    """
    filters = []
    
    if not allow_negatives:
        filters.extend([
            pl.col("Quantity") >= 0,
            pl.col("Total Sales") >= 0
        ])
    
    if not allow_zeros:
        filters.extend([
            pl.col("Quantity") != 0,
            pl.col("Total Sales") != 0
        ])
    
    if filters:
        combined_filter = filters[0]
        for f in filters[1:]:
            combined_filter = combined_filter & f
        return df.filter(combined_filter)
    
    return df


def get_date_range(df: pl.DataFrame, date_col: str = "Date Of Sale") -> Tuple[str, str]:
    """
    Get the min and max dates from a dataframe.
    """
    date_range = df.select([
        pl.col(date_col).min().alias("start_date"),
        pl.col(date_col).max().alias("end_date")
    ]).row(0)
    
    return str(date_range[0]), str(date_range[1])


def calculate_statistics(
    df: pl.DataFrame,
    value_col: str,
    group_by_cols: Optional[List[str]] = None
) -> pl.DataFrame:
    """
    Calculate common statistics for a value column.
    """
    stats_exprs = [
        pl.col(value_col).count().alias("count"),
        pl.col(value_col).sum().alias("sum"),
        pl.col(value_col).mean().alias("mean"),
        pl.col(value_col).median().alias("median"),
        pl.col(value_col).std().alias("std"),
        pl.col(value_col).min().alias("min"),
        pl.col(value_col).max().alias("max"),
        pl.col(value_col).quantile(0.25).alias("p25"),
        pl.col(value_col).quantile(0.75).alias("p75"),
    ]
    
    if group_by_cols:
        return df.group_by(group_by_cols).agg(stats_exprs)
    else:
        return df.select(stats_exprs)


def detect_outliers(
    df: pl.DataFrame,
    value_col: str,
    method: str = "iqr",
    threshold: float = 3.0
) -> pl.DataFrame:
    """
    Detect outliers using IQR or Z-score method.
    """
    if method == "iqr":
        q1 = df[value_col].quantile(0.25)
        q3 = df[value_col].quantile(0.75)
        iqr = q3 - q1
        lower_bound = q1 - (threshold * iqr)
        upper_bound = q3 + (threshold * iqr)
        
        return df.with_columns([
            ((pl.col(value_col) < lower_bound) | (pl.col(value_col) > upper_bound))
            .alias("is_outlier")
        ])
    
    elif method == "zscore":
        mean = df[value_col].mean()
        std = df[value_col].std()
        
        return df.with_columns([
            (((pl.col(value_col) - mean) / std).abs() > threshold)
            .alias("is_outlier")
        ])
    
    else:
        raise ValueError(f"Unknown method: {method}. Use 'iqr' or 'zscore'")


def format_percentage(value: Optional[float], decimal_places: int = 2) -> str:
    """Format a value as a percentage string"""
    if value is None:
        return "N/A"
    return f"{value:.{decimal_places}f}%"


def format_currency(value: Optional[float], currency: str = "KES", decimal_places: int = 2) -> str:
    """Format a value as currency"""
    if value is None:
        return "N/A"
    return f"{currency} {value:,.{decimal_places}f}"


def format_number(value: Optional[float], decimal_places: int = 2) -> str:
    """Format a number with commas and decimals"""
    if value is None:
        return "N/A"
    return f"{value:,.{decimal_places}f}"


def get_timestamp() -> str:
    """Get current timestamp as ISO string"""
    return datetime.now().isoformat()


def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """Safely divide two numbers, returning default if denominator is zero"""
    if denominator == 0:
        return default
    return numerator / denominator


def calculate_uplift_pct(promo_value: float, baseline_value: float) -> Optional[float]:
    """
    Calculate percentage uplift from baseline.
    """
    if baseline_value == 0:
        return None
    return ((promo_value - baseline_value) / baseline_value) * 100


def ensure_directories_exist(paths: List[Path]) -> None:
    """Ensure all directories in the list exist"""
    for path in paths:
        path.mkdir(parents=True, exist_ok=True)


def get_top_n(
    df: pl.DataFrame,
    sort_col: str,
    n: int = 10,
    ascending: bool = False
) -> pl.DataFrame:
    """Get top N rows sorted by a column"""
    return df.sort(sort_col, descending=not ascending).head(n)


def null_count_summary(df: pl.DataFrame) -> pl.DataFrame:
    """
    Get a summary of null counts for all columns.
    """
    total_rows = len(df)
    
    null_counts = []
    for col in df.columns:
        null_count = df[col].null_count()
        null_pct = (null_count / total_rows) * 100
        null_counts.append({
            "column_name": col,
            "null_count": null_count,
            "null_pct": null_pct
        })
    
    return pl.DataFrame(null_counts).sort("null_count", descending=True)


def value_count_summary(df: pl.DataFrame, col: str, top_n: int = 20) -> pl.DataFrame:
    """
    Get value counts for a column.
    """
    total_rows = len(df)
    counts = (
        df.group_by(col)
        .agg([
            pl.len().alias("count")
        ])
        .with_columns([
            (pl.col("count") / total_rows * 100).alias("pct")
        ])
        .sort("count", descending=True)
        .head(top_n)
    ) 
    return counts

###-----Uncomment to Test utility Functions----##

# if __name__ == "__main__":
#     """Test utility functions"""    
#     # Create sample data
#     sample_data = pl.DataFrame({
#         "Store Name": ["Store A", "Store A", "Store B", "Store B"],
#         "Supplier": ["BIDCO", "BIDCO", "Competitor X", "Competitor Y"],
#         "Sub-Department": ["Cooking Oil", "Cooking Oil", "Cooking Oil", "Detergents"],
#         "Section": ["Premium Oil", "Premium Oil", "Premium Oil", "Powder"],
#         "Quantity": [10.0, 5.0, 8.0, 0.0],
#         "Total Sales": [500.0, 250.0, 400.0, 0.0],
#         "RRP": [55.0, 55.0, 52.0, 100.0],
#         "Date Of Sale": ["2025-09-22", "2025-09-23", "2025-09-22", "2025-09-23"]
#     })
    
#     print("Sample data:")
#     print(sample_data)
    
    
#     # Test realized price calculation
#     df_with_price = calculate_realized_price(sample_data)
#     print(" Realized price calculated:")
#     print(df_with_price.select(["Quantity", "Total Sales", "realized_unit_price"]))
#     print()
    
#     # Test discount calculation
#     df_with_discount = calculate_discount_pct(sample_data)
#     print(" Discount % calculated:")
#     print(df_with_discount.select(["RRP", "realized_unit_price", "discount_pct"]))
#     print()
    
#     # Test Bidco flagging
#     df_with_bidco = flag_bidco_products(sample_data)
#     print(" Bidco products flagged:")
#     print(df_with_bidco.select(["Supplier", "is_bidco"]))
#     print()
    
#     # Test competitive set key
#     df_with_key = create_competitive_set_key(sample_data)
#     print(" Competitive set key created:")
#     print(df_with_key.select(["Sub-Department", "Section", "competitive_set_key"]))
#     print()
    
#     # Test valid transactions filter
#     df_valid = filter_valid_transactions(sample_data, allow_zeros=False)
#     print(f" Valid transactions filtered: {len(df_valid)} of {len(sample_data)} rows")
#     print()
    
#     # Test formatting
#     print(" Formatting functions:")
#     print(f"  Percentage: {format_percentage(12.54)}")
#     print(f"  Currency: {format_currency(1234.56)}")
#     print(f"  Number: {format_number(98765.4321)}")
#     print()
    
#     # Test uplift calculation
#     uplift = calculate_uplift_pct(150, 100)
#     print(f" Uplift calculation: {uplift}%")
#     print()
    

#     print("All utility tests passed ----")
  
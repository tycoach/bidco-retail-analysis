"""
API Dependencies
================
Dependency injection for FastAPI routes.
"""
import polars as pl
from pathlib import Path

# Global data store
_df = None

def load_data():
    """Load data from Excel file"""
    global _df
    if _df is None:
        # Calculate data path from this file's location
        # api/dependencies.py -> src/api -> src -> project_root -> data/raw
        project_root = Path(__file__).resolve().parent.parent.parent
        data_path = project_root / "data" / "raw" / "Test_Data.xlsx"
        
        try:
            print(f"Loading data from {data_path}...")
            _df = pl.read_excel(data_path)
            print(f"Loaded {len(_df):,} records")
        except Exception as e:
            print(f"Failed to load data: {e}")
            print(f" Please ensure Test_Data.xlsx is at: {data_path}")
            _df = pl.DataFrame()
    return _df
  

def get_df() -> pl.DataFrame:
    """
    Dependency that provides the dataframe to route handlers.
    
    Usage in routes:
        @router.get("/endpoint")
        async def my_endpoint(df = Depends(get_df)):
            # Use df here
    """
    if _df is None:
        load_data()
    return _df
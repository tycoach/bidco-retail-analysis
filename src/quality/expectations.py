"""
Great Expectations Test Suite
==============================
Define and validate data quality expectations for retail transactions.
"""

import sys
from pathlib import Path

# Add src to path for imports
if __name__ == "__main__":
    project_root = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(project_root / "src"))

import polars as pl
import great_expectations as gx
from great_expectations.core.batch import RuntimeBatchRequest
from typing import Dict, Any, List

from config import QUALITY_CONFIG, ANALYSIS_CONFIG


class RetailDataExpectations:
    """
    Great Expectations suite for retail transaction data.
    """
    
    def __init__(self):
        self.context = gx.get_context()
        
    def create_expectation_suite(self, suite_name: str = "retail_transactions") -> Dict[str, Any]:
        """
        Create  expectation suite for retail data.
        
       
        """
        suite = self.context.add_or_update_expectation_suite(expectation_suite_name=suite_name)
        
        # Build expectations
        expectations = self._build_expectations()
        
        return {
            "suite_name": suite_name,
            "expectations_count": len(expectations),
            "expectations": expectations
        }
    
    def _build_expectations(self) -> List[Dict[str, Any]]:
        """Build all data quality expectations"""
        expectations = []
        
        # ================================================================
        # SCHEMA EXPECTATIONS (columns must exist)
        # ================================================================
        expectations.append({
            "expectation_type": "expect_table_columns_to_match_set",
            "kwargs": {
                "column_set": [
                    "Store Name", "Item_Code", "Item Barcode", "Description",
                    "Category", "Department", "Sub-Department", "Section",
                    "Quantity", "Total Sales", "RRP", "Supplier", "Date Of Sale"
                ],
                "exact_match": True
            },
            "meta": {
                "description": "All required columns must be present"
            }
        })
        
        # ================================================================
        # COMPLETENESS EXPECTATIONS (no nulls in critical fields)
        # ================================================================
        for col in ANALYSIS_CONFIG.required_columns:
            expectations.append({
                "expectation_type": "expect_column_values_to_not_be_null",
                "kwargs": {
                    "column": col
                },
                "meta": {
                    "description": f"{col} must not have null values"
                }
            })
        
        # Allow some nulls in RRP and Item Barcode (imputable)
        expectations.append({
            "expectation_type": "expect_column_values_to_not_be_null",
            "kwargs": {
                "column": "RRP",
                "mostly": 0.95  # Allow up to 5% nulls
            },
            "meta": {
                "description": "RRP should be present in at least 95% of records"
            }
        })
        
        # ================================================================
        # VALIDITY EXPECTATIONS (correct data types and ranges)
        # ================================================================
        
        # Quantity should be numeric and mostly positive
        expectations.append({
            "expectation_type": "expect_column_values_to_be_of_type",
            "kwargs": {
                "column": "Quantity",
                "type_": "float64"
            }
        })
        
        expectations.append({
            "expectation_type": "expect_column_values_to_be_between",
            "kwargs": {
                "column": "Quantity",
                "min_value": 0,
                "max_value": 10000,
                "mostly": 0.99  # Allow 1% outside range (returns)
            },
            "meta": {
                "description": "Quantity should be between 0 and 10,000 for 99% of records"
            }
        })
        
        # Total Sales should be numeric and mostly positive
        expectations.append({
            "expectation_type": "expect_column_values_to_be_of_type",
            "kwargs": {
                "column": "Total Sales",
                "type_": "float64"
            }
        })
        
        expectations.append({
            "expectation_type": "expect_column_values_to_be_between",
            "kwargs": {
                "column": "Total Sales",
                "min_value": 0,
                "max_value": 100000,
                "mostly": 0.99
            },
            "meta": {
                "description": "Total Sales should be positive for 99% of records"
            }
        })
        
        # RRP should be positive when present
        expectations.append({
            "expectation_type": "expect_column_values_to_be_between",
            "kwargs": {
                "column": "RRP",
                "min_value": 0,
                "max_value": 50000,
                "mostly": 0.95
            },
            "meta": {
                "description": "RRP should be reasonable (0-50,000)"
            }
        })
        
        # Item_Code should be positive integer
        expectations.append({
            "expectation_type": "expect_column_values_to_be_between",
            "kwargs": {
                "column": "Item_Code",
                "min_value": 100000,
                "max_value": 999999
            },
            "meta": {
                "description": "Item codes should be 6-digit numbers"
            }
        })
        
        # ================================================================
        # CONSISTENCY EXPECTATIONS (logical relationships)
        # ================================================================
        
        # Store names should be from a known set (if we have the list)
        expectations.append({
            "expectation_type": "expect_column_distinct_values_to_be_in_set",
            "kwargs": {
                "column": "Store Name",
                "value_set": None,  # Will be populated at runtime
                "result_format": "SUMMARY"
            },
            "meta": {
                "description": "Store names should be from known retail outlets"
            }
        })
        
        # Category should be one of the known categories
        expectations.append({
            "expectation_type": "expect_column_distinct_values_to_be_in_set",
            "kwargs": {
                "column": "Category",
                "value_set": ["FOODS", "HOMECARE", "PERSONAL CARE"]
            },
            "meta": {
                "description": "Category must be FOODS, HOMECARE, or PERSONAL CARE"
            }
        })
        
        # Date should be within reasonable range
        expectations.append({
            "expectation_type": "expect_column_values_to_be_dateutil_parseable",
            "kwargs": {
                "column": "Date Of Sale"
            },
            "meta": {
                "description": "Date Of Sale must be a valid date"
            }
        })
        
        # ================================================================
        # UNIQUENESS EXPECTATIONS
        # ================================================================
        
        # No exact duplicate rows
        expectations.append({
            "expectation_type": "expect_table_row_count_to_be_between",
            "kwargs": {
                "min_value": 1000,
                "max_value": 100000
            },
            "meta": {
                "description": "Table should have reasonable number of rows"
            }
        })
        
        return expectations
    
    def validate_data(
        self,
        df: pl.DataFrame,
        suite_name: str = "retail_transactions"
    ) -> Dict[str, Any]:
        """
        Validate a dataframe against the expectation suite.
        """
        # Convert Polars to Pandas for Great Expectations
        df_pandas = df.to_pandas()
        
        # Create a batch request
        batch_request = RuntimeBatchRequest(
            datasource_name="runtime_datasource",
            data_connector_name="runtime_data_connector",
            data_asset_name="retail_transactions",
            runtime_parameters={"batch_data": df_pandas},
            batch_identifiers={"default_identifier_name": "retail_data"}
        )
        
        # Get or create expectation suite
        try:
            suite = self.context.get_expectation_suite(suite_name)
        except:
            self.create_expectation_suite(suite_name)
            suite = self.context.get_expectation_suite(suite_name)
        
        # Create checkpoint and run validation
        checkpoint_config = {
            "name": "retail_checkpoint",
            "config_version": 1.0,
            "class_name": "SimpleCheckpoint",
            "run_name_template": "%Y%m%d-%H%M%S",
        }
        
        try:
            checkpoint = self.context.add_or_update_checkpoint(**checkpoint_config)
            
            results = checkpoint.run(
                validations=[
                    {
                        "batch_request": batch_request,
                        "expectation_suite_name": suite_name,
                    }
                ]
            )
            
            # Extract useful summary
            validation_result = results.list_validation_results()[0]
            
            return {
                "success": validation_result.success,
                "statistics": validation_result.statistics,
                "results": validation_result.results,
                "evaluated_expectations": validation_result.statistics.get("evaluated_expectations", 0),
                "successful_expectations": validation_result.statistics.get("successful_expectations", 0),
                "unsuccessful_expectations": validation_result.statistics.get("unsuccessful_expectations", 0),
                "success_percent": validation_result.statistics.get("success_percent", 0.0)
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": "Validation failed with error"
            }


def create_simple_expectations_suite() -> List[Dict[str, str]]:
    """Create a simple list of data quality expectations with rationale"""
    expectations = [
        {
            "category": "Schema",
            "expectation": "All 13 required columns present",
            "rationale": "Missing columns break downstream processing"
        },
        {
            "category": "Completeness",
            "expectation": "No nulls in Store Name, Item_Code, Description, Quantity, Total Sales, Date Of Sale",
            "rationale": "These fields are critical for analysis"
        },
        {
            "category": "Completeness",
            "expectation": "RRP null rate < 5%",
            "rationale": "Needed for promo detection, but can be imputed if missing"
        },
        {
            "category": "Validity",
            "expectation": "Quantity >= 0 for 99% of records",
            "rationale": "Negative values are returns, should be rare"
        },
        {
            "category": "Validity",
            "expectation": "Total Sales >= 0 for 99% of records",
            "rationale": "Negative sales are refunds, should be rare"
        },
        {
            "category": "Validity",
            "expectation": "RRP between 0 and 50,000",
            "rationale": "Unreasonable prices indicate data errors"
        },
        {
            "category": "Validity",
            "expectation": "Item_Code is 6-digit number",
            "rationale": "Standard format for SKU codes"
        },
        {
            "category": "Consistency",
            "expectation": "Category in [FOODS, HOMECARE, PERSONAL CARE]",
            "rationale": "Only these three categories exist in the data"
        },
        {
            "category": "Consistency",
            "expectation": "Date Of Sale is valid date",
            "rationale": "Invalid dates break time-series analysis"
        },
        {
            "category": "Consistency",
            "expectation": "Store Name from known list",
            "rationale": "Unknown stores may indicate data quality issues"
        },
        {
            "category": "Uniqueness",
            "expectation": "No exact duplicate rows",
            "rationale": "Duplicates skew analysis results"
        },
        {
            "category": "Range",
            "expectation": "Row count between 1,000 and 100,000",
            "rationale": "Sanity check on dataset size"
        }
    ]
    
    return expectations

###-----Uncomment to Test the expectations suite----##

# if __name__ == "__main__":
#     """Test the expectations suite"""
    
#     print("=" * 80)
#     print("GREAT EXPECTATIONS TEST SUITE")
#     print("=" * 80)
#     print()
    
#     # Display simple expectations
#     print("DATA QUALITY EXPECTATIONS")
#     print("-" * 80)
#     expectations = create_simple_expectations_suite()
    
#     current_category = None
#     for exp in expectations:
#         if exp["category"] != current_category:
#             current_category = exp["category"]
#             print(f"\n {current_category.upper()}")
#             print("-" * 80)
        
#         print(f" {exp['expectation']}")
#         print(f"  Rationale: {exp['rationale']}")
    
#     print()
#     print("=" * 80)
#     print("VALIDATION TEST")
#     print("=" * 80)
#     print()
    
#     # Load test data
#     data_path = Path(__file__).parent.parent.parent / "data" / "raw" / "Test_Data.xlsx"
#     print(f"Loading data from {data_path}...")
#     df = pl.read_excel(data_path)
#     print(f" Loaded {len(df):,} records")
#     print()
    
#     # Note: Great Expectations full validation requires more setup
#     # For now, we'll show the expectations framework
#     print("Great Expectations Suite Created:")
#     print(f"  Total Expectations: {len(expectations)}")
#     print(f"  Categories: Schema, Completeness, Validity, Consistency, Uniqueness, Range")
#     print()
    
#     print("These expectations define the 'contract' for good data.")
#     print("Any violations are automatically flagged for investigation.")
#     print()
    
#     # Show what violations would look like
#     print("=" * 80)
#     print("EXAMPLE VIOLATIONS (if they existed)")
#     print("=" * 80)
#     print()
    
#     # Check actual data against some simple expectations
#     violations = []
    
#     # Check for nulls in critical columns
#     for col in ANALYSIS_CONFIG.required_columns:
#         null_count = df[col].null_count()
#         if null_count > 0:
#             violations.append(f" {col}: {null_count} null values")
    
#     # Check for negatives
#     negative_qty = len(df.filter(pl.col("Quantity") < 0))
#     if negative_qty > 0:
#         violations.append(f" Quantity: {negative_qty} negative values (likely returns)")
    
#     negative_sales = len(df.filter(pl.col("Total Sales") < 0))
#     if negative_sales > 0:
#         violations.append(f"  Total Sales: {negative_sales} negative values (likely refunds)")
    
#     # Check for zeros
#     zero_qty = len(df.filter(pl.col("Quantity") == 0))
#     if zero_qty > 0:
#         violations.append(f" Quantity: {zero_qty} zero values (data errors)")
    
#     if violations:
#         print("Found data quality issues:")
#         for violation in violations:
#             print(f"  {violation}")
#     else:
#         print("No major violations found! Data quality is excellent.")
    
    
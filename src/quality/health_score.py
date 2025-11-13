"""
Data Quality Health Score Module
Calculates quality scores for stores and suppliers based on:
Completeness (missing values)
Validity (negatives, zeros, outliers)
Consistency (price logic, patterns)
"""
import sys
from pathlib import Path

# Add src to path so imports work when running this file directly
if __name__ == "__main__":
    # project_root = Path(__file__).parent.parent.parent
    project_root = Path.cwd().parent
    sys.path.insert(0, str(project_root / "src"))

import polars as pl
from typing import List, Dict, Tuple
from datetime import date

from config import QUALITY_CONFIG, ANALYSIS_CONFIG
from schema import (
    DataQualityIssue,
    DataQualityScore,
    DataQualityReport
)
from utils import (
    null_count_summary
)


class DataQualityAnalyzer:
    """Analyzes data quality and generates trust scores"""
    
    def __init__(self, df: pl.DataFrame):
        self.df = df
        self.total_records = len(df)
        self.issues: List[DataQualityIssue] = []
        
    def analyze(self) -> DataQualityReport:
        """
        Run complete data quality analysis.
        """
        # Calculate aggregate metrics
        overall_completeness = self._calculate_overall_completeness()
        overall_validity = self._calculate_overall_validity()
        overall_consistency = self._calculate_overall_consistency()
        
        # Score individual stores and suppliers
        store_scores = self._score_entities("Store Name", "store")
        supplier_scores = self._score_entities("Supplier", "supplier")
        
        # Identify critical issues
        critical_issues = [issue for issue in self.issues if issue.severity == "critical"]
        
        # Count trusted vs untrusted entities
        trusted_stores = sum(1 for s in store_scores if s.is_trusted)
        untrusted_stores = len(store_scores) - trusted_stores
        trusted_suppliers = sum(1 for s in supplier_scores if s.is_trusted)
        untrusted_suppliers = len(supplier_scores) - trusted_suppliers
        
        return DataQualityReport(
            report_date=date.today(),
            total_records=self.total_records,
            total_stores=self.df["Store Name"].n_unique(),
            total_suppliers=self.df["Supplier"].n_unique(),
            overall_completeness=overall_completeness,
            overall_validity=overall_validity,
            overall_consistency=overall_consistency,
            store_scores=store_scores,
            supplier_scores=supplier_scores,
            critical_issues=critical_issues,
            trusted_stores=trusted_stores,
            untrusted_stores=untrusted_stores,
            trusted_suppliers=trusted_suppliers,
            untrusted_suppliers=untrusted_suppliers
        )
    
    def _calculate_overall_completeness(self) -> float:
        """Calculate completeness score (0-1) for the entire dataset"""
        null_summary = null_count_summary(self.df)
        
        # Focus on critical columns
        critical_nulls = null_summary.filter(
            pl.col("column_name").is_in(ANALYSIS_CONFIG.required_columns)
        )
        
        if len(critical_nulls) == 0:
            return 1.0
        
        # Average null percentage across critical columns
        avg_null_pct = critical_nulls["null_pct"].mean()
        
        # Record issues for columns with high null rates
        for row in critical_nulls.iter_rows(named=True):
            if row["null_pct"] > QUALITY_CONFIG.max_acceptable_null_pct:
                self.issues.append(DataQualityIssue(
                    issue_type="missing_values",
                    severity="critical" if row["null_pct"] > 10 else "warning",
                    field_name=row["column_name"],
                    description=f"High null rate in critical field: {row['null_pct']:.2f}%",
                    count=row["null_count"],
                    percentage=row["null_pct"]
                ))
        
        # Convert to 0-1 score (less nulls = higher score)
        score = max(0, 1 - (avg_null_pct / 100))
        return score
    
    def _calculate_overall_validity(self) -> float:
        """Calculate validity score (0-1) based on data value checks"""
        validity_checks = []
        
        # Check for negative values
        negative_qty = self.df.filter(pl.col("Quantity") < 0)
        negative_sales = self.df.filter(pl.col("Total Sales") < 0)

        negative_count = len(negative_qty) + len(negative_sales)
        negative_pct = (negative_count / self.total_records) * 100
        
        if negative_pct > QUALITY_CONFIG.max_acceptable_negative_pct:
            self.issues.append(DataQualityIssue(
                issue_type="negative_values",
                severity="critical" if negative_pct > 5 else "warning",
                field_name="Quantity, Total Sales",
                description=f"Found {negative_count} negative values",
                count=negative_count,
                percentage=negative_pct
            ))
        
        negative_score = max(0, 1 - (negative_pct / QUALITY_CONFIG.max_acceptable_negative_pct))
        validity_checks.append(negative_score)
        
        # Check for zero values
        zero_qty = self.df.filter(pl.col("Quantity") == 0)
        zero_sales = self.df.filter(pl.col("Total Sales") == 0)
        
        zero_count = len(zero_qty) + len(zero_sales)
        zero_pct = (zero_count / self.total_records) * 100
        
        if zero_pct > QUALITY_CONFIG.max_acceptable_zero_pct:
            self.issues.append(DataQualityIssue(
                issue_type="zero_values",
                severity="warning",
                field_name="Quantity, Total Sales",
                description=f"Found {zero_count} zero values",
                count=zero_count,
                percentage=zero_pct
            ))
        
        zero_score = max(0, 1 - (zero_pct / QUALITY_CONFIG.max_acceptable_zero_pct))
        validity_checks.append(zero_score)
        
        # Check for price outliers
        df_with_price = self.df.with_columns([
            (pl.col("Total Sales") / pl.col("Quantity")).alias("realized_unit_price")
        ]).filter((pl.col("Quantity") > 0) & (pl.col("Total Sales") > 0))
        
        if len(df_with_price) > 0:
            price_threshold = df_with_price["realized_unit_price"].quantile(
                QUALITY_CONFIG.price_outlier_quantile
            )
            outliers = df_with_price.filter(pl.col("realized_unit_price") > price_threshold)
            outlier_pct = (len(outliers) / len(df_with_price)) * 100
            
            if outlier_pct > 2:  # More than 2% outliers
                self.issues.append(DataQualityIssue(
                    issue_type="price_outliers",
                    severity="info",
                    field_name="realized_unit_price",
                    description=f"Found {len(outliers)} price outliers above {price_threshold:.2f}",
                    count=len(outliers),
                    percentage=outlier_pct
                ))
            
            outlier_score = max(0, 1 - (outlier_pct / 10))  # Penalty if >10% outliers
            validity_checks.append(outlier_score)
        
        # Return average of all validity checks
        return sum(validity_checks) / len(validity_checks) if validity_checks else 1.0
    
    def _calculate_overall_consistency(self) -> float:
        """Calculate consistency score based on logical relationships"""
        consistency_checks = []
        
        # Check: Realized price should be <= RRP in most cases
        df_with_price = self.df.with_columns([
            (pl.col("Total Sales") / pl.col("Quantity")).alias("realized_unit_price")
        ]).filter(
            (pl.col("Quantity") > 0) & 
            (pl.col("Total Sales") > 0) &
            (pl.col("RRP").is_not_null())
        )
        
        if len(df_with_price) > 0:
            # Count where realized price > RRP by more than 20% 
            above_rrp = df_with_price.filter(pl.col("realized_unit_price") > pl.col("RRP") * 1.2)
            above_rrp_pct = (len(above_rrp) / len(df_with_price)) * 100
            
            if above_rrp_pct > 20:  # More than 20% significantly above RRP is suspicious
                self.issues.append(DataQualityIssue(
                    issue_type="price_consistency",
                    severity="warning",
                    field_name="realized_unit_price vs RRP",
                    description=f"{len(above_rrp)} transactions priced >20% above RRP",
                    count=len(above_rrp),
                    percentage=above_rrp_pct
                ))
            
            # More lenient scoring - allow up to 30% of transactions above RRP
            price_consistency = max(0, 1 - (above_rrp_pct / 30))
            consistency_checks.append(price_consistency)
        
        # Check: Barcode should not be "0" or empty
        invalid_barcodes = self.df.filter(
            (pl.col("Item Barcode").is_null()) | 
            (pl.col("Item Barcode") == "0") |
            (pl.col("Item Barcode") == "")
        )
        invalid_barcode_pct = (len(invalid_barcodes) / self.total_records) * 100
        
        if invalid_barcode_pct > 5:
            self.issues.append(DataQualityIssue(
                issue_type="invalid_barcodes",
                severity="info",
                field_name="Item Barcode",
                description=f"{len(invalid_barcodes)} records with invalid barcodes",
                count=len(invalid_barcodes),
                percentage=invalid_barcode_pct
            ))
        
        barcode_consistency = max(0, 1 - (invalid_barcode_pct / 20))
        consistency_checks.append(barcode_consistency)
        
        # Return average of all consistency checks
        return sum(consistency_checks) / len(consistency_checks) if consistency_checks else 1.0
    
    def _score_entities(
        self,
        entity_col: str,
        entity_type: str
    ) -> List[DataQualityScore]:
        """
        Score individual stores or suppliers.

        """
        entities = self.df[entity_col].unique().to_list()
        scores = []
        
        for entity in entities:
            if entity is None:
                continue
                
            entity_df = self.df.filter(pl.col(entity_col) == entity)
            entity_records = len(entity_df)
            
            # Completeness score
            completeness = self._score_completeness(entity_df)
            
            # Validity score
            validity = self._score_validity(entity_df)
            
            # Consistency score
            consistency = self._score_consistency(entity_df)
            
            # Calculate weighted overall score
            overall = (
                completeness * QUALITY_CONFIG.completeness_weight +
                validity * QUALITY_CONFIG.validity_weight +
                consistency * QUALITY_CONFIG.consistency_weight
            )
            
            # Determine if trusted
            is_trusted = overall >= QUALITY_CONFIG.min_trust_score
            
            # Collect entity-specific issues
            entity_issues = []
            
            # Check for high null rates
            null_summary = null_count_summary(entity_df)
            high_nulls = null_summary.filter(pl.col("null_pct") > 5)
            for row in high_nulls.iter_rows(named=True):
                entity_issues.append(DataQualityIssue(
                    issue_type="missing_values",
                    severity="warning",
                    field_name=row["column_name"],
                    description=f"High null rate: {row['null_pct']:.2f}%",
                    count=row["null_count"],
                    percentage=row["null_pct"]
                ))
            
            scores.append(DataQualityScore(
                entity_name=entity,
                entity_type=entity_type,
                completeness_score=completeness,
                validity_score=validity,
                consistency_score=consistency,
                overall_score=overall,
                total_records=entity_records,
                issues=entity_issues,
                is_trusted=is_trusted
            ))
        
        # Sort by overall score descending
        return sorted(scores, key=lambda x: x.overall_score, reverse=True)
    
    def _score_completeness(self, df: pl.DataFrame) -> float:
        """Score completeness for a subset of data"""
        null_summary = null_count_summary(df)
        critical_nulls = null_summary.filter(
            pl.col("column_name").is_in(ANALYSIS_CONFIG.required_columns)
        )
        
        if len(critical_nulls) == 0:
            return 1.0
        
        avg_null_pct = critical_nulls["null_pct"].mean()
        return max(0, 1 - (avg_null_pct / 100))
    
    def _score_validity(self, df: pl.DataFrame) -> float:
        """Score validity for a subset of data"""
        total = len(df)
        if total == 0:
            return 1.0
        
        # Negative values
        negatives = df.filter((pl.col("Quantity") < 0) | (pl.col("Total Sales") < 0))
        negative_pct = (len(negatives) / total) * 100
        
        # Zero values
        zeros = df.filter((pl.col("Quantity") == 0) | (pl.col("Total Sales") == 0))
        zero_pct = (len(zeros) / total) * 100
        
        # Combined validity score
        negative_score = max(0, 1 - (negative_pct / QUALITY_CONFIG.max_acceptable_negative_pct))
        zero_score = max(0, 1 - (zero_pct / QUALITY_CONFIG.max_acceptable_zero_pct))
        
        return (negative_score + zero_score) / 2
    
    def _score_consistency(self, df: pl.DataFrame) -> float:
        """Score consistency for a subset of data"""
        df_with_price = df.with_columns([
            (pl.col("Total Sales") / pl.col("Quantity")).alias("realized_unit_price")
        ]).filter(
            (pl.col("Quantity") > 0) & 
            (pl.col("Total Sales") > 0) &
            (pl.col("RRP").is_not_null())
        )
        
        if len(df_with_price) == 0:
            return 1.0
        
        # Price consistency - allow 20% markup before penalizing
        above_rrp = df_with_price.filter(pl.col("realized_unit_price") > pl.col("RRP") * 1.2)
        above_rrp_pct = (len(above_rrp) / len(df_with_price)) * 100
        
        # More lenient - allow up to 30% above RRP
        return max(0, 1 - (above_rrp_pct / 30))


def generate_quality_report(df: pl.DataFrame) -> DataQualityReport:
    """
    function to generate a quality report.
    """
    analyzer = DataQualityAnalyzer(df)
    return analyzer.analyze()


# if __name__ == "__main__":
#     """Test the quality module"""
#     import sys
#     from pathlib import Path
    
#     # Add project root to path
#     project_root = Path(__file__).parent.parent.parent
#     sys.path.insert(0, str(project_root))
    
 
#     print("DATA QUALITY MODULE TEST")
 
#     # Load test data
#     data_path = project_root / "data" / "raw" / "Test_Data.xlsx"
#     print(f"Loading data from {data_path}...")
#     df = pl.read_excel(data_path)
#     print(f" Loaded {len(df):,} records")
#     print()
    
#     # Generate quality report
#     print("Running quality analysis...")
#     report = generate_quality_report(df)
#     print(" Analysis complete")
#     print()
    
#     # Display results
   
#     print("OVERALL QUALITY METRICS")

#     print(f"Total Records: {report.total_records:,}")
#     print(f"Total Stores: {report.total_stores}")
#     print(f"Total Suppliers: {report.total_suppliers}")
#     print()
#     print(f"Completeness Score: {report.overall_completeness:.2%}")
#     print(f"Validity Score: {report.overall_validity:.2%}")
#     print(f"Consistency Score: {report.overall_consistency:.2%}")
#     print()
    

#     print("STORE QUALITY SCORES")

#     print(f"Trusted Stores: {report.trusted_stores} of {report.total_stores}")
#     print(f"Untrusted Stores: {report.untrusted_stores}")
#     print()
#     print("Top 10 Stores by Quality:")
#     for i, score in enumerate(report.store_scores[:10], 1):
#         trust_icon = "✅" if score.is_trusted else "⚠️"
#         print(f"{i:2d}. {trust_icon} {score.entity_name:20s} | "
#               f"Score: {score.overall_score:.2%} | Grade: {score.grade} | "
#               f"Records: {score.total_records:,}")
#     print()
    
#     if report.untrusted_stores > 0:
#         print("Untrusted Stores (need investigation):")
#         untrusted = [s for s in report.store_scores if not s.is_trusted]
#         for score in untrusted[:5]:
#             print(f"    {score.entity_name}: {score.overall_score:.2%} "
#                   f"(C:{score.completeness_score:.2f}, "
#                   f"V:{score.validity_score:.2f}, "
#                   f"Cs:{score.consistency_score:.2f})")
#         print()
    
#     print("=" * 80)
#     print("SUPPLIER QUALITY SCORES")
#     print("=" * 80)
#     print(f"Trusted Suppliers: {report.trusted_suppliers} of {report.total_suppliers}")
#     print(f"Untrusted Suppliers: {report.untrusted_suppliers}")
#     print()
    
#     # Find Bidco
#     bidco_scores = [s for s in report.supplier_scores if "bidco" in s.entity_name.lower()]
#     if bidco_scores:
#         bidco = bidco_scores[0]
#         print("BIDCO Quality Score:")
#         print(f"  Overall: {bidco.overall_score:.2%} (Grade: {bidco.grade})")
#         print(f"  Completeness: {bidco.completeness_score:.2%}")
#         print(f"  Validity: {bidco.validity_score:.2%}")
#         print(f"  Consistency: {bidco.consistency_score:.2%}")
#         print(f"  Trusted: {'Yes' if bidco.is_trusted else '⚠️ No'}")
#         print(f"  Records: {bidco.total_records:,}")
#     print()
    

#     print("CRITICAL ISSUES")
 
#     if report.critical_issues:
#         for issue in report.critical_issues:
#             print(f" {issue.issue_type.upper()}")
#             print(f"   Field: {issue.field_name}")
#             print(f"   {issue.description}")
#             print(f"   Affected: {issue.count:,} records ({issue.percentage:.2f}%)")
#             print()
#     else:
#         print("No critical issues found!")
#     print()
    
#     print("=" * 80)
#     print(" Quality analysis complete!")
#     print("=" * 80)
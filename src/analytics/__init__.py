"""
Analytics package for Bidco Retail Analysis
"""

from .promotions import PromoDetector, analyze_bidco_promos
from .pricing import PriceIndexCalculator, analyze_bidco_pricing
from .aggregations import KPIAggregator, generate_bidco_summary

__all__ = [
    "PromoDetector",
    "analyze_bidco_promos",
    "PriceIndexCalculator",
    "analyze_bidco_pricing",
    "KPIAggregator",
    "generate_bidco_summary",
]
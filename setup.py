"""
Setup configuration for Bidco Retail Analysis
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read requirements
project_root = Path(__file__).parent
#readme = (project_root / "README.md").read_text() if (project_root / "README.md").exists() else ""

setup(
    name="bidco-retail-analysis",
    version="0.1.0",
    description="Retail data analysis platform for FMCG manufacturers",
    #long_description=readme,
    long_description_content_type="text/markdown",
    author="",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    python_requires=">=3.11",
    install_requires=[
        "polars>=0.20.0",
        "fastexcel>=0.7.0",
        "pydantic>=2.0.0",
        "plotly>=5.0.0",
        "duckdb>=0.9.0",
        "fastapi>=0.100.0",
        "uvicorn>=0.23.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "ruff>=0.1.0",
            "ipython>=8.0.0",
        ]
    },
    entry_points={
        "console_scripts": [
            "bidco-quality=quality.health_score:main",
        ]
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
)
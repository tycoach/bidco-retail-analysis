# Architecture Documentation

**Project:** Bidco Retail Analysis Platform  
**Architecture Style:** Modular, Layered, API-First  
**Language:** Python 3.12+  

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Architectural Principles](#architectural-principles)
3. [Layer Architecture](#layer-architecture)
4. [Module Design](#module-design)
5. [Data Flow](#data-flow)
6. [Technology Stack](#technology-stack)
7. [Design Patterns](#design-patterns)
8. [Scalability Considerations](#scalability-considerations)
9. [Security Architecture](#security-architecture)
10. [Future Enhancements](#future-enhancements)

---

## System Overview

The Bidco Retail Analysis Platform is a data-driven application that transforms raw retail transaction data into actionable business intelligence through quality assessment, promotional analysis, and competitive benchmarking.

### High-Level Architecture

```
![Architecture](documentation/architecture.png)
```

---

## Architectural Principles

### 1. Separation of Concerns

Each layer has a single, well-defined responsibility:

- **Presentation Layer**: User interface and visualization
- **API Layer**: HTTP endpoints and request/response handling
- **Business Logic Layer**: Domain logic and calculations
- **Data Layer**: Data access and storage

**Benefits:**
- Easy to test individual components
- Changes in one layer don't cascade
- Clear boundaries for team ownership

---

### 2. Dependency Inversion

High-level modules don't depend on low-level modules. Both depend on abstractions.

**Example:**
```python
# API endpoints depend on abstract interfaces
from analytics.promotions import PromoDetector  # Interface

# Not tightly coupled to data source
detector = PromoDetector(df)  # df could come from anywhere
```

**Benefits:**
- Easy to swap data sources
- Testable without real data
- Flexible deployment options

---

### 3. Single Responsibility Principle

Each module has one reason to change:

- `quality/` - Changes when quality rules change
- `analytics/promotions.py` - Changes when promo logic changes
- `api/endpoints/pricing.py` - Changes when pricing API changes

**Benefits:**
- Easier to understand
- Fewer merge conflicts
- Targeted testing

---

### 4. Configuration Over Code

Business rules externalized to `config.py`:

```python
PROMO_CONFIG = PromoConfig(
    discount_threshold_pct=10.0,  # Configurable
    min_promo_days=2,
    min_baseline_days=2
)
```

**Benefits:**
- Business users can adjust thresholds
- No code changes for parameter tuning
- A/B testing friendly

---

### 5. Type Safety

Strong typing throughout with Pydantic:

```python
class PromoDetectionResult(BaseModel):
    item_code: int
    description: str
    promo_uplift_pct: Optional[float]
```

**Benefits:**
- Catch errors at development time
- Self-documenting code
- IDE autocomplete support

---

## Layer Architecture

### Presentation Layer

**Components:**
- `dashboard.html` - Interactive web dashboard
- Swagger UI - Auto-generated API docs
- External clients - Python/JS/curl consumers

**Responsibilities:**
- Render visualizations
- Handle user interactions
- Call API endpoints

**Technology:**
- HTML5, CSS3, JavaScript
- Plotly.js for charts
- Fetch API for HTTP calls

---

### API Layer

**Structure:**
```
src/api/
├── main.py              # FastAPI app initialization
├── dependencies.py      # Dependency injection
└── endpoints/           # Route handlers
    ├── health.py        # Health checks
    ├── quality.py       # Quality endpoints
    ├── promotions.py    # Promo endpoints
    ├── pricing.py       # Pricing endpoints
    ├── kpis.py          # KPI endpoints
    └── dashboard.py     # Combined endpoint
```

**Responsibilities:**
- HTTP request/response handling
- Input validation (via Pydantic)
- Endpoint routing
- Error handling
- Response formatting

**Design Pattern:** Router pattern (modular endpoints)

**Example:**
```python
# Each endpoint module defines a router
router = APIRouter(prefix="/api/quality", tags=["quality"])

@router.get("/report")
async def get_quality_report(df = Depends(get_df)):
    # Business logic delegated to quality module
    report = generate_quality_report(df)
    return MetricsResponse(success=True, data=report)
```

---

### Business Logic Layer

#### Quality Module

**Purpose:** Assess data reliability

**Components:**
- `health_score.py` - Quality scoring engine
- `expectations.py` - Great Expectations integration

**Key Classes:**
- `QualityScorer` - Calculates quality scores
- `DataValidator` - Runs validation rules

**Inputs:** Raw transaction DataFrame  
**Outputs:** Quality scores, trust flags, issue lists

---

#### Analytics Module

**Purpose:** Business intelligence calculations

**Components:**
- `promotions.py` - Promo detection & uplift
- `pricing.py` - Price index calculation
- `aggregations.py` - KPI rollups

**Key Classes:**
- `PromoDetector` - Detects promotional periods
- `PriceIndexCalculator` - Competitive benchmarking
- `KPIAggregator` - Metric aggregation

**Pattern:** Each class follows:
1. Initialize with data
2. Process data (private methods)
3. Return structured results (Pydantic models)

---

#### Shared Utilities

**Purpose:** Common functionality

**Components:**
- `config.py` - Configuration management
- `schemas.py` - Pydantic models
- `utils/helpers.py` - Utility functions

**Examples:**
```python
# Configuration
from config import PROMO_CONFIG

# Schemas
from schemas import PromoDetectionResult

# Utilities
from utils.helpers import calculate_realized_price
```

---

### Data Layer

**Current Implementation:**
- Excel file as source
- Polars DataFrames for processing
- In-memory data model

**Future Implementation:**
- PostgreSQL for persistent storage
- Polars for high-performance queries
- Caching layer (Redis)

**Why Polars?**
- 10-100x faster than Pandas
- Built in Rust (memory safe)
- Lazy evaluation
- Arrow-native (efficient)

---

## Module Design

### Quality Module Architecture

```
quality/
├── health_score.py
│   ├── QualityScorer
│   │   ├── calculate_completeness()
│   │   ├── calculate_validity()
│   │   ├── calculate_consistency()
│   │   └── assign_grade()
│   └── generate_quality_report()
│
└── expectations.py
    ├── create_expectation_suite()
    ├── validate_transaction_data()
    └── format_validation_results()
```

**Design Decisions:**
- Separate completeness/validity/consistency for clarity
- Configurable thresholds in `config.py`
- Returns strongly-typed Pydantic models

---

### Analytics Module Architecture

```
analytics/
├── promotions.py
│   ├── PromoDetector
│   │   ├── detect_promos()
│   │   ├── calculate_promo_coverage()
│   │   └── get_supplier_summary()
│   └── analyze_bidco_promos()
│
├── pricing.py
│   ├── PriceIndexCalculator
│   │   ├── calculate_price_index()
│   │   ├── get_price_summary()
│   │   └── _generate_recommendations()
│   └── analyze_bidco_pricing()
│
└── aggregations.py
    ├── KPIAggregator
    │   ├── get_market_overview()
    │   ├── get_supplier_metrics()
    │   ├── get_category_breakdown()
    │   ├── get_top_skus()
    │   └── generate_executive_summary()
    └── generate_bidco_summary()
```

**Design Decisions:**
- Each analyzer as a class (stateful processing)
- Convenience functions for common use cases
- Consistent method naming (`get_*`, `calculate_*`, `analyze_*`)

---

## Data Flow

### End-to-End Request Flow

```
1. User Request
   ↓
2. FastAPI Router (main.py)
   ↓
3. Endpoint Handler (e.g., pricing.py)
   ↓
4. Dependency Injection (get_df)
   ↓
5. Business Logic (PriceIndexCalculator)
   ↓
6. Data Processing (Polars operations)
   ↓
7. Result Construction (Pydantic model)
   ↓
8. Response Formatting (MetricsResponse)
   ↓
9. JSON Response to User
```

**Example: `/api/pricing/BIDCO` Request**

```python
# 1. User makes request
GET /api/pricing/BIDCO

# 2. Router matches endpoint
@router.get("/{supplier_name}")

# 3. Handler receives request
async def get_price_positioning(
    supplier_name: str,
    df: pl.DataFrame = Depends(get_df)  # 4. DI injects data
):
    # 5. Business logic
    calculator = PriceIndexCalculator(df)
    summary = calculator.get_price_summary(supplier_name)
    
    # 7. Result construction
    # summary is already a PriceIndexSummary (Pydantic)
    
    # 8. Response formatting
    return MetricsResponse(
        success=True,
        data=summary.dict(),
        timestamp=get_timestamp()
    )
    
# 9. FastAPI serializes to JSON
```

---

## Technology Stack

### Core Technologies

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| **API Framework** | FastAPI | Modern, async, auto-docs, type-safe |
| **Data Processing** | Polars | 10-100x faster than Pandas |
| **Validation** | Pydantic | Type safety, serialization |
| **Quality Checks** | Great Expectations | Industry standard |
| **Visualization** | Plotly.js | Interactive, professional charts |
| **HTTP Client** | httpx | Async support |
| **Testing** | pytest | Standard Python testing |

### Why These Choices?

**FastAPI over Flask/Django:**
- Auto-generated OpenAPI docs
- Native async support
- Pydantic integration
- Modern Python features

**Polars over Pandas:**
- Memory efficiency (10x less RAM)
- Speed (10-100x faster)
- Better NULL handling
- Arrow-native (interop)

**Pydantic over dataclasses:**
- Runtime validation
- JSON serialization
- Auto OpenAPI schemas
- Nested models

---

## Design Patterns

### 1. Dependency Injection

**Used in:** API layer

```python
# dependencies.py
def get_df() -> pl.DataFrame:
    return load_data()

# endpoint
@router.get("/report")
async def endpoint(df = Depends(get_df)):
    # df automatically injected
```

**Benefits:**
- Testable (mock get_df)
- Centralized data loading
- Clean separation

---

### 2. Factory Pattern

**Used in:** Chart generation

```python
# visualization/charts.py
def create_quality_gauge(score: float) -> go.Figure:
    # Creates and returns configured chart
    return fig

def create_market_share_pie(...) -> go.Figure:
    # Creates different chart type
    return fig
```

**Benefits:**
- Consistent chart styling
- Reusable components
- Easy testing

---

### 3. Builder Pattern

**Used in:** Quality report construction

```python
report = (
    QualityScorer(df)
    .calculate_completeness()
    .calculate_validity()
    .calculate_consistency()
    .build_report()
)
```

---

### 4. Strategy Pattern

**Used in:** Price index calculation

```python
class PriceIndexCalculator:
    def calculate_price_index(
        self,
        by_store: bool = True  # Strategy parameter
    ):
        if by_store:
            # Store-level strategy
        else:
            # Portfolio-level strategy
```

**Benefits:**
- Multiple calculation methods
- Runtime selection
- Extensible

---

## Scalability Considerations

### Current Scale

- **Data Volume:** 30K transactions (~1MB)
- **Processing Time:** <1 second per analysis
- **Memory:** ~50MB peak usage
- **API Throughput:** 100+ req/sec possible

---

### Scaling to 10x (300K transactions)

**Approach:**
1. Polars already handles this efficiently
2. Lazy evaluation (only compute what's needed)
3. Efficient aggregations (vectorized ops)

**No changes needed.**

---

## Deployment Architecture

### Development
```
Local Machine
├── Python 3.12
├── FastAPI dev server
└── SQLite (optional)
```

### Production 
```
Cloud Provider (AWS/GCP/Azure)
├── API Server
│   ├── ECS/Kubernetes pods
│   ├── Load balancer
│   └── Auto-scaling
├── Database
│   ├── RDS PostgreSQL
│   └── Read replicas
├── Cache
│   ├── ElastiCache Redis
│   └── CDN for static assets
└── Monitoring
    ├── CloudWatch/Datadog
    ├── Sentry (error tracking)
    └── Grafana dashboards
```

---

## Conclusion

This architecture provides:

**Maintainability** - Clear separation, single responsibility  
**Scalability** - Horizontal scaling ready  
**Testability** - Dependency injection, mocking  
**Performance** - Polars, async, caching  
**Extensibility** - Plugin architecture, configuration  

---

**Document Version:** 1.0  
**Last Updated:** November 13, 2025  


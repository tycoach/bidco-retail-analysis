# API Documentation

**Bidco Retail Analysis Platform**  
**Version:** 0.1.0  
**Base URL:** `http://localhost:8000`  
**Documentation UI:** `http://localhost:8000/docs`  

---

## Table of Contents

1. [Overview](#overview)
2. [Authentication](#authentication)
3. [Response Format](#response-format)
4. [Error Handling](#error-handling)
5. [Health Endpoints](#health-endpoints)
6. [Data Quality Endpoints](#data-quality-endpoints)
7. [Promotions Endpoints](#promotions-endpoints)
8. [Pricing Endpoints](#pricing-endpoints)
9. [KPI Endpoints](#kpi-endpoints)
10. [Dashboard Endpoint](#dashboard-endpoint)
11. [Rate Limiting](#rate-limiting)
12. [Examples](#examples)

---

## Overview

The Bidco Retail Analysis API provides programmatic access to:
- Data quality assessments
- Promotional performance analysis
- Competitive price positioning
- Key performance indicators

All endpoints return JSON responses with consistent structure and type-safe schemas.

### Base URL
```
http://localhost:8000
```

### Interactive Documentation
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

---

## Authentication

**Current Version:** No authentication required (development mode)

**Production Considerations:**
- Implement API key authentication
- Use OAuth 2.0 for user-based access
- Rate limiting per client

---

## Response Format

All successful responses follow this structure:

```json
{
  "success": true,
  "data": { 
    // Endpoint-specific data 
  },
  "metadata": {
    "endpoint": "/api/...",
    "timestamp": "2025-11-13T10:30:00"
  },
  "timestamp": "2025-11-13T10:30:00"
}
```

### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `success` | boolean | `true` for successful responses, `false` for errors |
| `data` | object | Endpoint-specific response data |
| `metadata` | object | Optional metadata (filters, source info) |
| `timestamp` | string | ISO-8601 timestamp of response generation |

---

## Error Handling

### Error Response Format

```json
{
  "error": "Error Type",
  "detail": "Detailed error message",
  "timestamp": "2025-11-13T10:30:00"
}
```

### HTTP Status Codes

| Code | Meaning | Use Case |
|------|---------|----------|
| 200 | OK | Successful request |
| 400 | Bad Request | Invalid parameters |
| 404 | Not Found | Resource doesn't exist |
| 422 | Validation Error | Invalid input data |
| 500 | Internal Server Error | Server-side error |

### Common Errors

**404 - Supplier Not Found**
```json
{
  "error": "Not Found",
  "detail": "Supplier 'XYZ' not found",
  "timestamp": "2025-11-13T10:30:00"
}
```

**422 - Validation Error**
```json
{
  "error": "Validation Error",
  "detail": "min_score must be between 0 and 1",
  "timestamp": "2025-11-13T10:30:00"
}
```

---

## Health Endpoints

### GET /

Root health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "version": "0.1.0",
  "timestamp": "2025-11-13T10:30:00"
}
```

**Example:**
```bash
curl http://localhost:8000/
```

---

### GET /health

Detailed health status.

**Response:**
```json
{
  "status": "healthy",
  "version": "0.1.0",
  "timestamp": "2025-11-13T10:30:00"
}
```

**Example:**
```bash
curl http://localhost:8000/health
```

---

## Data Quality Endpoints

### GET /api/quality/report

Get complete data quality report for all stores and suppliers.

**Response Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `report_date` | string | Date of analysis |
| `total_records` | integer | Total transaction count |
| `total_stores` | integer | Number of stores analyzed |
| `total_suppliers` | integer | Number of suppliers analyzed |
| `overall_metrics` | object | Completeness, validity, consistency scores |
| `store_summary` | object | Trusted/untrusted store counts |
| `supplier_summary` | object | Trusted/untrusted supplier counts |
| `critical_issues` | array | List of quality issues found |

**Example Request:**
```bash
curl http://localhost:8000/api/quality/report
```

**Example Response:**
```json
{
  "success": true,
  "data": {
    "report_date": "2025-11-13",
    "total_records": 30691,
    "total_stores": 35,
    "total_suppliers": 190,
    "overall_metrics": {
      "completeness": 1.0,
      "validity": 0.944,
      "consistency": 0.989
    },
    "store_summary": {
      "trusted": 32,
      "untrusted": 3
    },
    "supplier_summary": {
      "trusted": 145,
      "untrusted": 45
    },
    "critical_issues": [
      {
        "type": "validity",
        "severity": "high",
        "field_name": "Total Sales",
        "description": "Extreme price outliers detected",
        "count": 15,
        "percentage": 0.05
      }
    ]
  },
  "metadata": {
    "endpoint": "/api/quality/report",
    "data_source": "Test_Data.xlsx"
  },
  "timestamp": "2025-11-13T10:30:00"
}
```

---

### GET /api/quality/stores

Get quality scores for all stores with optional filtering.

**Query Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `min_score` | float | No | None | Minimum quality score (0.0-1.0) |
| `trusted_only` | boolean | No | false | Return only trusted stores |

**Response Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `stores` | array | List of store quality scores |
| `count` | integer | Number of stores returned |

**Store Object:**

| Field | Type | Description |
|-------|------|-------------|
| `store_name` | string | Store name |
| `overall_score` | float | Overall quality score (0.0-1.0) |
| `grade` | string | Quality grade (A-F) |
| `is_trusted` | boolean | Trust classification |
| `completeness_score` | float | Completeness score |
| `validity_score` | float | Validity score |
| `consistency_score` | float | Consistency score |
| `total_records` | integer | Transaction count |

**Example Request:**
```bash
# All stores
curl http://localhost:8000/api/quality/stores

# Trusted stores only with minimum 80% score
curl "http://localhost:8000/api/quality/stores?min_score=0.8&trusted_only=true"
```

**Example Response:**
```json
{
  "success": true,
  "data": {
    "stores": [
      {
        "store_name": "RONGAI MAIN",
        "overall_score": 0.92,
        "grade": "A",
        "is_trusted": true,
        "completeness_score": 1.0,
        "validity_score": 0.95,
        "consistency_score": 0.91,
        "total_records": 1245
      }
    ],
    "count": 32
  },
  "metadata": {
    "endpoint": "/api/quality/stores",
    "filters": {
      "min_score": 0.8,
      "trusted_only": true
    }
  },
  "timestamp": "2025-11-13T10:30:00"
}
```

---

### GET /api/quality/suppliers/{supplier_name}

Get quality score for a specific supplier.

**Path Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `supplier_name` | string | Yes | Supplier name (case-insensitive) |

**Response Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `supplier_name` | string | Full supplier name |
| `overall_score` | float | Overall quality score |
| `grade` | string | Quality grade (A-F) |
| `is_trusted` | boolean | Trust classification |
| `completeness_score` | float | Completeness score |
| `validity_score` | float | Validity score |
| `consistency_score` | float | Consistency score |
| `total_records` | integer | Transaction count |
| `issues` | array | List of quality issues |

**Example Request:**
```bash
curl http://localhost:8000/api/quality/suppliers/BIDCO
```

**Example Response:**
```json
{
  "success": true,
  "data": {
    "supplier_name": "BIDCO AFRICA LIMITED",
    "overall_score": 0.7876,
    "grade": "C",
    "is_trusted": true,
    "completeness_score": 1.0,
    "validity_score": 0.944,
    "consistency_score": 0.989,
    "total_records": 1000,
    "issues": [
      {
        "type": "validity",
        "severity": "low",
        "field_name": "RRP",
        "description": "Some RRP values below realized price"
      }
    ]
  },
  "timestamp": "2025-11-13T10:30:00"
}
```

---

## Promotions Endpoints

### GET /api/promos/{supplier_name}

Get promotional performance analysis for a supplier.

**Methodology Note:** Uses cross-sectional comparison, comparing stores running promotions 
vs stores not running promotions for the same SKUs during the same period. This approach 
is appropriate for snapshot data and measures promotional effectiveness across locations.

**Path Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `supplier_name` | string | No | BIDCO | Supplier name |

**Response Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `supplier` | string | Supplier name |
| `analysis_date` | string | Date of analysis (NEW) |
| `methodology` | string | Analysis approach: "cross_sectional"  |
| `category` | string | Primary category (may be "All Categories") |
| `sub_department` | string | Primary sub-department (may be "All Sub-Departments") |

**Portfolio Object:**

| Field | Type | Description |
|-------|------|-------------|
| `total_skus` | integer | Total SKUs analyzed |
| `skus_on_promo` | integer | SKUs with active promos |
| `promo_sku_pct` | float | Percentage of SKUs on promo |

**Performance Object:**

| Field | Type | Description |
|-------|------|-------------|
| `avg_uplift_pct` | float | Average uplift percentage |
| `median_uplift_pct` | float | Median uplift percentage |
| `avg_discount_pct` | float | Average discount depth |
| `avg_promo_coverage_pct` | float | Average coverage across stores |

**Top Performer Object:**

| Field | Type | Description |
|-------|------|-------------|
| `item_code` | integer | SKU code |
| `description` | string | Product description |
| `uplift_pct` | float | Uplift percentage (cross-sectional) |
| `promo_units` | float | Units sold in promo stores |
| `discount_pct` | float | Discount percentage |
| `coverage_pct` | float | Store coverage percentage |

**Example Request:**
```bash
curl http://localhost:8000/api/promos/BIDCO
```

**Example Response:**
```json
{
  "success": true,
  "data": {
    "supplier": "BIDCO",
    "analysis_date": "2025-11-14",
    "methodology": "cross_sectional",
    "category": "All Categories",
    "sub_department": "All Sub-Departments",
    "portfolio": {
      "total_skus": 105,
      "skus_on_promo": 71,
      "promo_sku_pct": 67.6
    },
    "performance": {
      "avg_uplift_pct": 7.56,
      "median_uplift_pct": 5.2,
      "avg_discount_pct": 15.3,
      "avg_promo_coverage_pct": 42.5
    },
    "top_performers": [
      {
        "item_code": 12345,
        "description": "Chipsy Cooking Fat 2.5KG",
        "uplift_pct": 233.0,
        "promo_units": 150,
        "discount_pct": 18.5,
        "coverage_pct": 60.0
      }
    ],
    "insights": [
      "67.6% of SKUs are on promotion.",
      "Strong average uplift (7.56%). Promotions effectively drive incremental volume."
    ]
  },
  "metadata": {
    "endpoint": "/api/promos",
    "methodology_note": "Cross-sectional comparison: promo stores vs baseline stores"
  },
  "timestamp": "2025-11-14T10:30:00"
}
```

---

## Pricing Endpoints

### GET /api/pricing/{supplier_name}

Get competitive price positioning for a supplier.

**Path Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `supplier_name` | string | No | BIDCO | Supplier name |

**Response Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `supplier` | string | Supplier name |
| `analysis_date` | string | Analysis date |
| `portfolio` | object | Portfolio breakdown |
| `price_indices` | object | Price index metrics |
| `category_indices` | object | Category-level indices |
| `store_indices` | object | Store-level indices (top 10) |
| `recommendations` | array | Pricing recommendations |

**Portfolio Object:**

| Field | Type | Description |
|-------|------|-------------|
| `total_skus` | integer | Total SKUs analyzed |
| `premium_skus` | integer | Premium-positioned SKUs |
| `at_market_skus` | integer | At-market SKUs |
| `discount_skus` | integer | Discount-positioned SKUs |

**Price Indices Object:**

| Field | Type | Description |
|-------|------|-------------|
| `average` | float | Average price index |
| `median` | float | Median price index |

**Example Request:**
```bash
curl http://localhost:8000/api/pricing/BIDCO
```

**Example Response:**
```json
{
  "success": true,
  "data": {
    "supplier": "BIDCO",
    "analysis_date": "2025-11-13",
    "portfolio": {
      "total_skus": 41,
      "premium_skus": 13,
      "at_market_skus": 2,
      "discount_skus": 26
    },
    "price_indices": {
      "average": 0.825,
      "median": 0.648
    },
    "category_indices": {
      "PUFFED SNACKS": 1.664,
      "COOKING FATS": 1.386,
      "NOODLES": 1.243,
      "NON CARBONATED DRINKS": 0.925,
      "COOKING OIL": 0.772,
      "DETERGENT POWDER": 0.532
    },
    "store_indices": {
      "RONGAI MAIN": 0.891,
      "MFANGANO": 0.823,
      "KIAMBU RD": 0.799
    },
    "recommendations": [
      "Overall discount positioning (index: 0.82). Opportunity to increase prices without losing competitiveness.",
      "63% of SKUs are discount-priced. Potential margin opportunity through selective price increases."
    ]
  },
  "timestamp": "2025-11-13T10:30:00"
}
```

---

## KPI Endpoints

### GET /api/kpis/market

Get overall market metrics.

**Response Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `total_sales` | float | Total market sales value |
| `total_units` | integer | Total units sold |
| `total_transactions` | integer | Total transaction count |
| `unique_stores` | integer | Number of stores |
| `unique_suppliers` | integer | Number of suppliers |
| `unique_skus` | integer | Number of SKUs |
| `avg_transaction_value` | float | Average transaction value |
| `avg_unit_price` | float | Average unit price |
| `date_range` | object | Analysis period |

**Example Request:**
```bash
curl http://localhost:8000/api/kpis/market
```

---

### GET /api/kpis/{supplier_name}

Get KPIs for a specific supplier.

**Path Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `supplier_name` | string | No | BIDCO | Supplier name |

**Response Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `supplier` | string | Supplier name |
| `total_sales` | float | Total sales value |
| `total_units` | integer | Total units sold |
| `total_transactions` | integer | Transaction count |
| `market_share_pct` | float | Market share percentage |
| `unique_skus` | integer | Number of SKUs |
| `stores_present` | integer | Store count |
| `avg_unit_price` | float | Average unit price |
| `categories` | array | List of categories |

**Example Request:**
```bash
curl http://localhost:8000/api/kpis/BIDCO
```

**Example Response:**
```json
{
  "success": true,
  "data": {
    "supplier": "BIDCO",
    "total_sales": 1100192.69,
    "total_units": 4154,
    "total_transactions": 1000,
    "market_share_pct": 7.84,
    "unique_skus": 105,
    "stores_present": 35,
    "avg_unit_price": 321.28,
    "categories": ["FOODS", "HOMECARE", "PERSONAL CARE"]
  },
  "timestamp": "2025-11-13T10:30:00"
}
```

---

### GET /api/kpis/{supplier_name}/summary

Get executive summary with all KPIs.

**Response includes:**
- Market overview
- Supplier performance
- Category breakdown
- Top stores (top 5)
- Top products (top 5)
- Key metrics (formatted)

**Example Request:**
```bash
curl http://localhost:8000/api/kpis/BIDCO/summary
```

---

## Dashboard Endpoint

### GET /api/dashboard/{supplier_name}

Get combined metrics from all modules in a single call.

**Path Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `supplier_name` | string | No | BIDCO | Supplier name |

**Response combines:**
- Quality score
- Promotional performance
- Price positioning
- Key KPIs

**Example Request:**
```bash
curl http://localhost:8000/api/dashboard/BIDCO
```

**Example Response:**
```json
{
  "success": true,
  "data": {
    "supplier": "BIDCO",
    "quality": {
      "overall_score": 0.7876,
      "grade": "C",
      "is_trusted": true
    },
    "promos": {
      "skus_on_promo": 0,
      "total_skus": 105,
      "avg_uplift_pct": null
    },
    "pricing": {
      "avg_index": 0.825,
      "positioning": "discount"
    },
    "kpis": {
      "market_share": "7.84%",
      "total_sales": "KES 1,100,192.69",
      "total_units": "4,154.00",
      "avg_unit_price": "KES 321.28",
      "store_coverage": "35 of 35 stores"
    }
  },
  "metadata": {
    "endpoint": "/api/dashboard",
    "components": ["quality", "promos", "pricing", "kpis"]
  },
  "timestamp": "2025-11-13T10:30:00"
}
```

---

## Rate Limiting

**Current:** No rate limiting (development mode)

**Production Recommendations:**
- 100 requests per hour per client
- 1000 requests per day per client
- Burst allowance: 10 requests per minute

---

## Examples

### Python
```python
import requests

# Get Bidco dashboard
response = requests.get("http://localhost:8000/api/dashboard/BIDCO")
data = response.json()

print(f"Market Share: {data['data']['kpis']['market_share']}")
print(f"Quality Grade: {data['data']['quality']['grade']}")
```

### JavaScript
```javascript
fetch('http://localhost:8000/api/dashboard/BIDCO')
  .then(res => res.json())
  .then(data => {
    console.log('Market Share:', data.data.kpis.market_share);
    console.log('Quality Grade:', data.data.quality.grade);
  });
```

### curl
```bash
# Pretty-print with jq
curl http://localhost:8000/api/dashboard/BIDCO | jq .

# Extract specific field
curl http://localhost:8000/api/kpis/BIDCO | jq '.data.market_share_pct'

# Filter stores by quality
curl "http://localhost:8000/api/quality/stores?min_score=0.8" | jq '.data.stores[].store_name'
```

---

## Support

For issues or questions:
- Interactive Docs: `http://localhost:8000/docs`


---

**Version:** 0.1.0  
**Last Updated:** November 13, 2025

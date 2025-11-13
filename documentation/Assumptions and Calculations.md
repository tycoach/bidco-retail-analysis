# Technical Assumptions & Calculation Methodology

**Project:** Bidco Retail Analysis Platform  
**Purpose:** Document all assumptions, business rules, and calculation methodologies used in the analysis  
**Audience:** Technical reviewers, data engineers, stakeholders  

---

## Table of Contents

1. [Data Assumptions](#data-assumptions)
2. [Quality Assessment Methodology](#quality-assessment-methodology)
3. [Promotional Analysis Calculations](#promotional-analysis-calculations)
4. [Price Index Methodology](#price-index-methodology)
5. [KPI Calculations](#kpi-calculations)
6. [Edge Cases & Handling](#edge-cases--handling)

---

## Data Assumptions

### 1. Data Source & Format

**Assumption:** Excel file represents complete transaction data for analysis period.

**Details:**
- File: `Test_Data.xlsx`
- Period: September 22-28, 2025 (7 days)
- Records: 30,691 transactions
- Granularity: Transaction-level (not aggregated)

**Validation:**
- Date range verified: 2025-09-22 to 2025-09-28
- No transactions outside this window
- Assumption holds: True

---

### 2. Transaction Validity

**Assumption:** Each row represents a single transaction at a specific store on a specific date.

**Implications:**
- Multiple rows for same SKU + Store + Date = multiple transactions (not duplicates)
- Same Item_Code across stores = same product
- Quantity and Total Sales are as-transacted (may include returns)

**Handling:**
- Negative quantities treated as returns (excluded from most analyses)
- Zero-value transactions excluded from pricing calculations
- Duplicates checked but NOT removed (legitimate multiple transactions)

---

### 3. Price Fields

**Assumption:** Price hierarchy exists: RRP (recommended) → Realized Price (actual)

**Price Definitions:**
```python
RRP (Recommended Retail Price):
    - The "list price" or suggested selling price
    - Field: 'RRP' column
    - Assumption: Same RRP across all stores for a given SKU

Realized Unit Price:
    - Actual price paid per unit
    - Calculation: Total Sales / Quantity
    - Formula: realized_unit_price = df["Total Sales"] / df["Quantity"]
    - Excludes transactions where Quantity = 0
```

**Why This Matters:**
- Discount % = (RRP - Realized Price) / RRP × 100
- Positive discount = customer paid less than RRP
- Negative discount = customer paid MORE than RRP (possible premium/convenience pricing)

---

### 4. Product Identification

**Assumption:** Item_Code uniquely identifies a product (SKU) across all stores.

**Competitive Set Definition:**
- Products compete within same Sub-Department AND Section
- Competitive set key: `f"{Sub-Department}|{Section}"`
- Example: All cooking oils in "FOODS|COOKING OIL" compete

**Bidco Identification:**
```python
is_bidco = Supplier.str.contains("BIDCO", case=False)
# Matches: "BIDCO AFRICA LIMITED", "Bidco", "BIDCO OIL", etc.
```

---

## Quality Assessment Methodology

### Quality Score Calculation

**Overall Approach:** Multi-dimensional quality assessment across 3 pillars.

#### 1. Completeness Score

**Definition:** Percentage of required fields that are non-null.

**Formula:**
```python
completeness_score = 1 - (missing_count / total_records)

Where:
- missing_count = number of null/empty values in critical fields
- critical_fields = ["Store Name", "Item_Code", "Quantity", "Total Sales", 
                     "RRP", "Supplier", "Date Of Sale"]
```

**Assumptions:**
- All 7 critical fields must be present for valid transaction
- Missing = NULL, empty string, or whitespace-only
- Weight: 33.3% of overall quality score

---

#### 2. Validity Score

**Definition:** Percentage of records passing business logic rules.

**Validation Rules:**
```python
# Rule 1: Quantity must be numeric and reasonable
valid_quantity = (Quantity is not null) AND (Quantity != 0)

# Rule 2: Total Sales must be numeric and non-zero
valid_sales = (Total Sales is not null) AND (Total Sales != 0)

# Rule 3: RRP must be positive
valid_rrp = (RRP > 0)

# Rule 4: Realized price must be positive
valid_realized_price = (realized_unit_price > 0)

# Rule 5: Price reasonability (not extreme outliers)
valid_price_range = (realized_unit_price < 1000000)  # < 1M KES per unit

# Rule 6: Date is within expected range
valid_date = (Date Of Sale between 2025-09-01 and 2025-12-31)

validity_score = (records_passing_all_rules / total_records)
```

**Assumptions:**
- Negative quantities are returns (flagged but not invalid)
- Prices > 1M KES per unit are data errors
- Weight: 33.3% of overall quality score

---

#### 3. Consistency Score

**Definition:** Logical consistency across related fields.

**Consistency Checks:**
```python
# Check 1: Price calculation consistency
price_consistent = (
    abs((Total Sales / Quantity) - realized_unit_price) < 0.01
)

# Check 2: Discount direction consistency
discount_consistent = (
    (realized_unit_price <= RRP) OR (discount_pct < 0)
)

# Check 3: Category hierarchy consistency
category_consistent = (
    Sub-Department matches expected Category
)

consistency_score = (consistent_records / total_records)
```

**Assumptions:**
- Price calculation tolerance: ±0.01 KES (rounding)
- Negative discounts acceptable (premium pricing)
- Weight: 33.3% of overall quality score

---

#### 4. Overall Quality Score

**Formula:**
```python
overall_quality = (
    completeness_score × 0.333 +
    validity_score × 0.333 +
    consistency_score × 0.333
)

# Grade Assignment:
A: >= 0.90  (Excellent)
B: >= 0.80  (Good)
C: >= 0.70  (Acceptable)
D: >= 0.60  (Poor)
F: <  0.60  (Failing)
```

**Trust Classification:**
```python
is_trusted = (overall_quality >= 0.75) AND (record_count >= 10)

Rationale:
- 75% threshold = "C grade or better"
- Minimum 10 records = statistical significance
- Both conditions must be met
```

---

## Promotional Analysis Calculations

### Promo Detection Logic

**Core Assumption:** A promotion is a sustained discount period, not a one-off price drop.

#### Promo Detection Rules

**Configuration (from config.py):**
```python
PROMO_CONFIG = {
    'discount_threshold_pct': 10.0,      # Minimum 10% discount
    'min_promo_days': 2,                  # Sustained for 2+ days
    'min_baseline_days': 2,               # Need 2+ non-promo days for comparison
    'min_transactions_for_analysis': 5    # Minimum data points
}
```

**Step-by-Step Detection:**

**Step 1: Calculate Daily Discount**
```python
# For each Store + SKU + Date combination:
daily_discount_pct = (
    (median_rrp - avg_realized_price) / median_rrp × 100
)

# Using median RRP handles price changes during period
```

**Step 2: Flag Promo Days**
```python
is_promo_day = (daily_discount_pct >= 10.0)

Example:
Date        Daily Discount    Is Promo Day?
2025-09-22  5%               No
2025-09-23  12%              Yes
2025-09-24  15%              Yes
2025-09-25  3%               No
```

**Step 3: Aggregate to SKU Level**
```python
promo_days = count(is_promo_day == True)
baseline_days = count(is_promo_day == False)
total_days = count(all days with transactions)
```

**Step 4: Determine Promo Status**
```python
if (promo_days >= 2) AND (baseline_days >= 2):
    status = "on_promo"
elif baseline_days >= 2:
    status = "baseline"
else:
    status = "insufficient_data"
```

**Why This Logic?**
- Prevents misclassifying one-off price errors as promos
- Requires both promo AND baseline periods for valid comparison
- Ensures statistical validity

---

### Promo Performance Metrics

#### A. Promo Uplift %

**Definition:** Percentage increase in units sold during promo vs baseline.

**Formula:**
```python
promo_uplift_pct = (
    (avg_daily_promo_units - avg_daily_baseline_units) / 
    avg_daily_baseline_units × 100
)

Where:
avg_daily_promo_units = total_promo_units / promo_days
avg_daily_baseline_units = total_baseline_units / baseline_days

Example:
Promo period: 100 units over 2 days = 50 units/day
Baseline: 60 units over 3 days = 20 units/day
Uplift = (50 - 20) / 20 × 100 = 150%
```

**Interpretation:**
- Positive uplift = Promo drove incremental sales
- Negative uplift = Promo cannibalized baseline (red flag!)
- 0% uplift = No effect (ineffective promo)

**Assumptions:**
- Daily averaging accounts for different period lengths
- Baseline represents "normal" sales velocity
- External factors (seasonality, stockouts) are constant

---

#### B. Promo Coverage %

**Definition:** Percentage of stores running the promo for a given SKU.

**Formula:**
```python
promo_coverage_pct = (
    stores_with_promo / total_stores_with_sku × 100
)

Where:
stores_with_promo = count(stores where status = "on_promo")
total_stores_with_sku = count(stores carrying the SKU)

Example:
SKU carried in: 20 stores
Promo active in: 15 stores
Coverage = 15/20 × 100 = 75%
```

**Business Significance:**
- <30% = Limited test
- 30-70% = Regional rollout
- >70% = National campaign

---

#### C. Promo Price Impact (Discount Depth)

**Definition:** Average discount offered during promo period.

**Formula:**
```python
avg_promo_discount_pct = (
    sum(discount_pct for promo_days) / promo_days
)

discount_pct = (RRP - realized_price) / RRP × 100
```

**Typical Ranges:**
- 5-10% = Shallow discount (may not be noticed)
- 10-20% = Standard discount (effective)
- 20-30% = Deep discount (strong driver)
- >30% = Extreme discount (margin risk)

---

#### D. Baseline vs Promo Avg Price

**Definition:** Compare actual prices during promo vs non-promo periods.

**Formulas:**
```python
avg_promo_price = (
    sum(realized_unit_price for promo_days) / promo_days
)

avg_baseline_price = (
    sum(realized_unit_price for baseline_days) / baseline_days
)

price_reduction = avg_baseline_price - avg_promo_price
price_reduction_pct = price_reduction / avg_baseline_price × 100
```

**Example:**
```
Baseline avg price: KES 250
Promo avg price: KES 200
Reduction: KES 50 (20%)
```

**Why Both Metrics?**
- Discount depth (vs RRP) = how big the discount looks
- Price reduction (baseline vs promo) = actual price change experienced

---

#### E. Top Performing SKUs

**Definition:** SKUs with highest uplift AND reasonable volume.

**Ranking Logic:**
```python
# Primary sort: Uplift %
# Secondary sort: Promo units sold
# Filter: Minimum 50 units during promo (significance threshold)

top_performers = (
    filter(promo_units >= 50)
    .sort_by(['uplift_pct', 'promo_units'], descending=True)
    .head(10)
)
```

**Why Volume Filter?**
- A 500% uplift on 10 units is less meaningful than 100% uplift on 1000 units
- Prevents cherry-picking low-volume anomalies

---

## Price Index Methodology

### Competitive Price Index

**Core Concept:** Compare Bidco's realized prices to competitors within same product categories.

#### Step 1: Define Competitive Set

**Formula:**
```python
competitive_set_key = f"{Sub-Department}|{Section}"

Example competitive sets:
- "FOODS|COOKING OIL" - All cooking oils compete
- "HOMECARE|DETERGENT POWDER" - All detergent powders compete
- "FOODS|NOODLES" - All noodles compete
```

**Assumption:**
- Products in same Sub-Department + Section are substitutable
- Cross-section competition (e.g., cooking oil vs margarine) not modeled
- Store location doesn't affect competitive set definition

---

#### Step 2: Calculate Average Prices

**For Each SKU in Each Store:**
```python
sku_avg_price = mean(realized_unit_price)

# Uses all transactions for that SKU in that store
# Mean is more robust than median for pricing (less sensitive to volume)
```

**Minimum Transaction Threshold:**
```python
min_transactions_for_price = 3

# Rationale: Need at least 3 transactions for stable average
# Single transactions could be data errors
```

---

#### Step 3: Calculate Competitor Benchmark

**For Each Competitive Set in Each Store:**
```python
competitor_avg_price = mean(
    sku_avg_price 
    for all SKUs in competitive_set 
    where is_bidco == False
)

min_competitors_for_index = 2

# Need at least 2 competitors for valid comparison
# Single competitor not representative of market
```

**Example:**
```
Competitive Set: FOODS|COOKING OIL in Store "RONGAI MAIN"

SKUs in set:
1. Bidco Golden Fry 5L: KES 1,200 (Bidco - excluded from benchmark)
2. Elianto 5L: KES 1,250 (Competitor)
3. Fresh Fri 5L: KES 1,300 (Competitor)
4. Rina 5L: KES 1,150 (Competitor)

Competitor benchmark = (1250 + 1300 + 1150) / 3 = KES 1,233
```

---

#### Step 4: Calculate Price Index

**Formula:**
```python
price_index = bidco_avg_price / competitor_avg_price

Interpretation:
> 1.1  = Premium (Bidco prices 10%+ above market)
0.9-1.1 = At Market (Bidco within ±10% of market)
< 0.9  = Discount (Bidco prices 10%+ below market)
```

**Example:**
```
Bidco Golden Fry 5L: KES 1,200
Competitor benchmark: KES 1,233
Price Index = 1200/1233 = 0.973 (At Market)
```

**Thresholds Rationale:**
- ±10% chosen as "perceptible" price difference to consumers
- Smaller differences often not noticed
- Aligns with industry standards for price positioning

---

#### Step 5: Store-Level vs Portfolio-Level

**Store-Level Index:**
```python
# Calculated per store
store_price_index = mean(price_index for all Bidco SKUs in store)

# Shows: "Is Bidco premium/discount in THIS store?"
```

**Portfolio-Level Index:**
```python
# Aggregated across all stores
portfolio_price_index = mean(store_price_index for all stores)

# Shows: "Is Bidco premium/discount OVERALL?"
```

**Why Both?**
- Store-level reveals regional pricing variance
- Portfolio-level shows overall brand positioning
- Enables "where should we raise/lower prices?" analysis

---

#### Step 6: RRP Analysis

**Realized Price vs RRP:**
```python
price_vs_rrp_pct = (
    (avg_realized_price - avg_rrp) / avg_rrp × 100
)

Interpretation:
< 0%  = Selling below RRP (discounting)
= 0%  = Selling at RRP
> 0%  = Selling above RRP (premium/convenience)
```

**Business Insight:**
- If price_index < 1.0 BUT price_vs_rrp > 0:
  → Bidco's RRPs are set too high relative to competition
  
- If price_index > 1.0 AND price_vs_rrp < 0:
  → Bidco charges premium but discounts heavily

---

## KPI Calculations

### Market Share

**Formula:**
```python
market_share_pct = (
    supplier_total_sales / total_market_sales × 100
)

Where:
supplier_total_sales = sum(Total Sales for supplier)
total_market_sales = sum(Total Sales for all suppliers)
```

**Assumption:**
- Sales value is better metric than volume (accounts for product mix)
- All stores equally weighted (no store weighting by importance)

---

### Sales Metrics

**Total Sales:**
```python
total_sales = sum(Total Sales)

# Sum of transaction values
# Includes all categories
```

**Total Units:**
```python
total_units = sum(Quantity)

# Raw unit count
# Does NOT account for pack sizes
```

**Average Unit Price:**
```python
avg_unit_price = total_sales / total_units

# Weighted average across all SKUs
# Reflects actual product mix sold
```

---

### Store/SKU Rankings

**Top Stores:**
```python
# Ranked by total sales (descending)
# Includes all suppliers (market view) or filtered to specific supplier
```

**Top Products:**
```python
# Ranked by total sales (descending)
# Can also rank by units sold
# Minimum transactions not required (actual sales are facts)
```

---

## Edge Cases & Handling

### 1. Missing RRP Values

**Problem:** Some transactions have NULL RRP.

**Handling:**
```python
# Option A: Use median RRP for that SKU
median_rrp = df.filter(Item_Code == sku).select(RRP).median()

# Option B: Exclude from discount calculations
if RRP is null:
    discount_pct = None  # Cannot calculate

# Choice: Option B (more conservative)
# Rationale: Don't impute pricing data
```

---

### 2. Negative Quantities (Returns)

**Problem:** Returns appear as negative quantities.

**Handling:**
```python
# Quality assessment: Flag but don't exclude (valid transactions)
# Pricing analysis: Exclude (distorts unit price)
# Promo analysis: Exclude (not real sales)
# KPI totals: Include (reflects net sales)

filter_for_pricing = df.filter(Quantity > 0)
filter_for_kpis = df  # Keep all
```

**Rationale:**
- Returns are real business events (affect quality)
- But distort per-unit economics (shouldn't affect price index)

---

### 3. Zero-Value Transactions

**Problem:** Some transactions have Total Sales = 0 or Quantity = 0.

**Handling:**
```python
# Realized price calculation: Exclude (division by zero)
# Other analyses: Exclude (no economic value)

valid_transactions = df.filter(
    (Quantity != 0) & (Total Sales != 0)
)
```

**Rationale:**
- Could be data errors, samples, or processing transactions
- Don't represent real market dynamics

---

### 4. Extreme Outliers

**Problem:** Prices > KES 100,000 per unit (likely errors).

**Detection:**
```python
is_outlier = (realized_unit_price > 100000)

# Example errors seen:
# - Quantity = 0.001 (data entry error)
# - Total Sales = 999999 (placeholder value)
```

**Handling:**
```python
# Flag in quality report (validity score affected)
# Exclude from pricing analysis
# Include in KPI totals IF part of actual sales

# Decision rule:
if realized_unit_price > 100000:
    exclude_from_price_index()
    flag_in_quality_report()
```

---

### 5. Insufficient Competitive Data

**Problem:** SKU has no competitors in competitive set.

**Example:**
```
Bidco is only supplier in "FOODS|PUFFED SNACKS" in Store X
```

**Handling:**
```python
if competitor_count < min_competitors_for_index:
    price_index = None
    price_position = "insufficient_data"
    
# Skip from portfolio averages (don't set to 1.0)
```

**Rationale:**
- Cannot benchmark against self
- Don't impute market parity
- Flag as "no competitive comparison available"

---

### 6. Single-Day Data

**Problem:** SKU only sold on 1 day in analysis period.

**Handling:**
```python
# Promo analysis: Cannot determine (need 2+ baseline + 2+ promo days)
promo_status = "insufficient_data"

# Pricing analysis: Can proceed if meets transaction minimum
if transaction_count >= 3:
    calculate_price_index()
    
# Quality analysis: Always include (is a data point)
```

**Rationale:**
- Promotions require time series
- Pricing can use cross-sectional data
- Quality assessment always relevant

---

## Calculation Summary Table

| Metric | Formula | Key Assumptions |
|--------|---------|-----------------|
| Quality Score | (Completeness + Validity + Consistency) / 3 | Equal weights, 75% = trusted |
| Promo Uplift | (Promo Units - Baseline Units) / Baseline Units × 100 | Daily averaging, stable externals |
| Price Index | Bidco Avg Price / Competitor Avg Price | Same comp set = substitutable |
| Discount % | (RRP - Realized Price) / RRP × 100 | RRP is accurate, negative allowed |
| Market Share | Supplier Sales / Total Sales × 100 | Value-based, unweighted stores |

---

## Validation & Testing

### Data Validation Performed

1.  Date range consistency (all dates within expected period)
2.  Numeric field validation (prices, quantities are numbers)
3.  Referential integrity (Item_Code consistency across stores)
4.  Price reasonableness (no prices > KES 1M per unit in analysis)
5.  Calculation verification (spot-checked against Excel)

### Assumptions Validated

1. RRP consistency (same RRP per SKU across stores) - **98% consistent**
2. Competitive set relevance (Sub-Dept + Section) - **Manually verified**
3. Promo detection (10% discount) - **0 promos detected for Bidco** (finding, not error)
4. Transaction granularity (multiple rows = multiple transactions) - **Confirmed**

---

## Conclusion

This document provides full transparency into:
- **Assumptions made** - Explicitly stated and justified
- **Calculations used** - Step-by-step formulas with examples
- **Edge cases handled** - Real-world data issues addressed
- **Validation performed** - How assumptions were tested

All thresholds and business rules are configurable in `src/config.py` .

---

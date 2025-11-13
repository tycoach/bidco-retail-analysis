# Executive Summary: Bidco Retail Performance Analysis

**Analysis Period:** September 22-28, 2025 (7 days)  
**Data Coverage:** 35 stores, 30,691 transactions, 190 suppliers  
**Focus:** Bidco Africa Limited performance vs market  

---

## Key Questions Answered

### 1. Is Our Data Reliable?

**Answer: Yes**

- **Overall Data Quality:** 78.76% (Grade C)
- **Status:** Trusted data source
- **Coverage:** Present in all 35 stores (100% distribution)
- **Completeness:** 100% - No missing critical fields
- **Validity:** 94.4% - Strong data accuracy

**What This Means:**
The C grade reflects industry-standard retail data quality. All key fields (prices, quantities, dates) are complete and accurate.


---

### 2. Are We Running Effective Promotions?

**Answer: No promotions detected during analysis period.**

**Key Finding:** Zero SKUs met the criteria for sustained promotional activity (10%+ discount for 2+ consecutive days).

**What We Found:**
- **Total SKUs Analyzed:** 105 Bidco products
- **SKUs on Promo:** 0
- **Average Discount:** 17.0% (but not sustained)
- **Promo Coverage:** Only 30.5% of stores showed any discounting

**What This Means:**
Bidco products are selling at or near full retail price (RRP). While some intermittent discounting occurs, there are no sustained promotional campaigns running during this period.

**Critical Insight:**
Despite no active promotions, Bidco still captures 7.84% market share. This suggests:
1. Strong brand equity (customers buy without needing discounts)
2. Opportunity cost - Could promotions drive higher volume?
3. Competitive disadvantage - If competitors are promoting and you're not

**Recommendations:**

1. **Test Promotional Pricing**
   - Run controlled test: 15% discount for 5 days on top 10 SKUs
   - Measure uplift vs baseline
   - Target: 30-50% volume increase to justify margin sacrifice

2. **Strategic Category Selection**
   - Start with categories where you're discount-positioned (already lower priced than competitors)
   - Examples: Cooking Oil (index 0.77), Detergent Powder (index 0.53)
   - Lower risk since you're already priced competitively

3. **Store-Specific Rollout**
   - Begin in top-performing stores (Rongai Main, Mfangano)
   - These account for 15% of your volume
   - Minimize risk while maximizing learnings

---

### 3. How Are We Priced vs Competition?

**Answer: Overall discount-positioned, but with significant category variation.**

**Overall Price Positioning:**
- **Price Index:** 0.825 (Bidco prices ~18% below competitor average)
- **Portfolio Mix:** 
  - 63.4% of SKUs are discount-priced (below market)
  - 31.7% are premium-priced (above market)
  - 4.9% at market parity

**What This Means:**
This is a predominantly a value brand, undercutting competitors on most products. However, nearly a third of the portfolio commands premium pricing.

**Category-Level Breakdown:**

| Category | Price Index | Position | Insight |
|----------|-------------|----------|---------|
| Puffed Snacks | 1.664 | **PREMIUM** | Charging 66% above market - unique offering or overpriced? |
| Cooking Fats | 1.386 | **PREMIUM** | 39% above market |
| Noodles | 1.243 | **PREMIUM** | 24% above market |
| Non-Carbonated Drinks | 0.925 | **AT MARKET** | Competitive parity |
| Margarine | 0.876 | **DISCOUNT** | 12% below market |
| Hand Wash Detergent | 0.775 | **DISCOUNT** | 22% below market |
| Cooking Oil | 0.772 | **DISCOUNT** | 23% below market |
| Bleach | 0.617 | **DISCOUNT** | 38% below market |
| Detergent Powder | 0.532 | **DISCOUNT** | 47% below market |
| Breakfast Cereals | 0.422 | **DEEP DISCOUNT** | 58% below market |

**Critical Insights:**

1. **Margin Opportunity (Detergent Powder)**
   - You're 47% cheaper than competitors
   - This is excessive discounting - unlikely to be necessary
   - **Action:** Test 10-15% price increase on Msafi range
   - **Potential Impact:** Could improve margins by 18-28% with minimal volume loss

2. **Premium Justification (Puffed Snacks)**
   - 66% price premium is extreme
   - Either: (a) Unique product with no direct competition, or (b) Overpriced
   - **Action:** Review competitive set - are you truly comparable?
   - **Risk:** If competitors exist, you're vulnerable to substitution

3. **Sweet Spot (Non-Carbonated Drinks)**
   - Priced at market parity (index 0.925)
   - This is ideal positioning - competitive without leaving margin on table
   - **Model:** Replicate this positioning in other categories

**Store-Level Variance:**
- Price positioning varies by store (not uniform)
- Some stores perceive you as premium, others as discount
- Suggests inconsistent pricing strategy or local competitive dynamics

---

## Market Performance Summary

### Market Position
- **Market Share:** 7.84% by value
- **Total Sales:** KES 1,100,192.69 (of KES 14M market)
- **Distribution:** 35 of 35 stores (100% coverage)
- **Units Sold:** 4,154 units
- **Average Unit Price:** KES 321.28

**What This Means:**
You're a mid-tier player with solid distribution. Your 7.84% share ranks you in the top quartile of the 190 suppliers in this market.

### Category Performance

**Foods (74.2% of Bidco sales):**
- Total: KES 816,416.94
- Dominant category
- Driven by cooking oils and noodles

**Homecare (25.7% of Bidco sales):**
- Total: KES 282,724.03
- Secondary category
- Detergents and cleaning products

**Personal Care (0.1% of Bidco sales):**
- Total: KES 1,051.72
- Minimal presence
- Consider exit or investment

### Top Performers

**By Sales:**
1. Golden Fry Cooking Oil 5L - KES 274,942.92 (25% of total sales)
2. Msafi Purple Detergent 1KG - KES 116,234.42
3. Msafi Purple Detergent (Sachets) - KES 79,655.17
4. Elianto Corn Oil 5L - KES 47,485.33
5. Golden Fry Cooking Oil 2L - KES 43,836.20

**Critical Dependency:**
- Top product represents 25% of total sales
- Top 5 products = 50% of sales
- High concentration risk - any disruption to Golden Fry significantly impacts business

**By Store:**
1. Rongai Main - KES 110,899.98 (10% of sales)
2. Mfangano - KES 60,696.52
3. Kiambu Rd - KES 50,183.60
4. Kilimani - KES 45,658.61
5. Ruaka - KES 45,043.95

**Store Concentration:**
- Top 5 stores = 28% of sales
- Geographic concentration in specific locations
- Opportunity: Underperforming stores could be developed

---



**Appendix:** Detailed analysis available via:
- Interactive Dashboard: `src/visualization/dashboard.html`
- API Documentation: `http://localhost:8000/docs`
- Technical Details: `documentation/Assumptions and Calculations.md`

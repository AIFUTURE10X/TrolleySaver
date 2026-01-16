# Australian Supermarket Price Comparison App - Research Findings

**Date:** 2025-01-14

## Executive Summary

Building an Australian supermarket price comparison app is **technically challenging but feasible** using existing open-source tools and reverse-engineered APIs. Direct scraping is heavily blocked, but alternative approaches exist.

---

## 1. Direct Scraping Test Results (Firecrawl Viability)

### Test Results

| Store | URL | Result | Notes |
|-------|-----|--------|-------|
| **Woolworths** | /shop/browse/specials | **403 Forbidden** | Blocked at request level |
| **Coles** | /on-special | **Blocked (Incapsula)** | WAF/Security service intercepts |
| **ALDI** | /en/special-buys/ | **SPA - No Data** | JavaScript renders content, needs API |

### Conclusion on Firecrawl

Firecrawl alone **will not work** for these sites because:
1. Woolworths and Coles use aggressive anti-bot protection
2. ALDI uses a Nuxt.js SPA where product data loads via API after page render
3. All three would require bypassing security measures (legally risky)

---

## 2. Alternative Data Sources (The Better Path)

### A. Open Source Projects (Best Options)

#### 1. Australian Grocery Price Database
- **URL:** https://github.com/tjhowse/aus_grocery_price_database
- **Status:** Active, 28 stars
- **Tech:** Go-based scraper -> InfluxDB -> Grafana
- **Coverage:** Woolworths & Coles
- **Data:** SKU, product name, department, price, barcode (Woolworths only)
- **Pros:** Working solution, time-series data, open source
- **Cons:** No ALDI, needs self-hosting, "dirty" product names

#### 2. Australian Supermarket OpenAPI Specs
- **URL:** https://github.com/drkno/au-supermarket-apis
- **Status:** 29 stars, minimal updates
- **Coverage:** Coles & Woolworths API specs (YAML/OpenAPI format)
- **Method:** Reverse-engineered from mobile apps
- **Pros:** Documents actual internal APIs
- **Cons:** May break without notice, no ALDI

#### 3. Coles & Woolworths MCP Server
- **URL:** https://www.pulsemcp.com/servers/coles-woolworths
- **Status:** Released August 2025, 16 GitHub stars
- **Function:** Real-time product info and price fetching
- **Tech:** Model Context Protocol server
- **Pros:** Recent, actively used, comparison-ready
- **Cons:** Depends on API stability

### B. Catalogue Aggregators

#### Lasoo
- **URL:** https://www.lasoo.com.au
- **Coverage:** 80+ retailers including Woolworths, Coles, ALDI
- **Features:** Weekly specials, catalogue browsing, price alerts
- **API:** No public API available
- **Scraping:** Also blocked (429 rate limit on testing)

### C. Datasets (Static/Historical)

#### Kaggle Australian Grocery Dataset
- **URL:** https://www.kaggle.com/datasets/thedevastator/grocery-product-prices-for-australian-states
- **Data:** Products, prices, descriptions by state
- **Limitation:** From 2022, not real-time

---

## 3. Regulatory Developments (Future Opportunity)

### ACCC Supermarket Inquiry (2025)

The ACCC has recommended that **Woolworths and Coles be required to publish live prices via API**.

> "Woolworths and Coles should be forced to provide their current prices to third parties using application programming interfaces (APIs) that would facilitate live price comparisons."

**Source:** [Information Age - Supermarkets should publish live prices: ACCC](https://ia.acs.org.au/article/2025/supermarkets-should-publish-live-prices--accc.html)

**Implication:** If implemented, this would make the app significantly easier to build with official, legal data access.

---

## 4. Recommended Architecture

### Phase 1: MVP Using Existing Tools

```
┌─────────────────────────────────────────────────────────────┐
│                    Data Collection Layer                     │
├─────────────────────────────────────────────────────────────┤
│  aus_grocery_price_database    │  Woolworths + Coles data   │
│  (Fork & extend)               │  Already working           │
├─────────────────────────────────────────────────────────────┤
│  au-supermarket-apis           │  API documentation         │
│  (Reference for custom calls)  │  For building extensions   │
├─────────────────────────────────────────────────────────────┤
│  Manual ALDI entry             │  Weekly catalogue review   │
│  (Until API found)             │  ~50-100 key products      │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Storage Layer                             │
├─────────────────────────────────────────────────────────────┤
│  PostgreSQL / InfluxDB                                       │
│  - Products table (normalized names, categories)             │
│  - Prices table (store, price, date, unit_price)             │
│  - Product_matches (cross-store matching)                    │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    API / Backend                             │
├─────────────────────────────────────────────────────────────┤
│  Python FastAPI / Node.js Express                            │
│  - GET /products?search=milk                                 │
│  - GET /compare?product_id=123                               │
│  - GET /specials?store=woolworths                            │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Frontend                                  │
├─────────────────────────────────────────────────────────────┤
│  React Native / Flutter                                      │
│  - Search products                                           │
│  - Compare prices across stores                              │
│  - View current specials                                     │
│  - Shopping list with best prices                            │
└─────────────────────────────────────────────────────────────┘
```

### Phase 2: Enhanced Features

1. **Product Matching ML** - Use fuzzy matching / embeddings to match products across stores
2. **Price Alerts** - Notify when tracked products go on special
3. **Shopping List Optimizer** - Which store has best total basket price
4. **Historical Trends** - Price history charts

---

## 5. Technical Challenges & Solutions

| Challenge | Solution |
|-----------|----------|
| Product name variations | Fuzzy matching (fuzzywuzzy) + manual curation for top products |
| Unit price normalization | Parse "per 100g", "per kg", "each" and normalize |
| API instability | Cache data, graceful degradation, multiple sources |
| ALDI coverage | Manual catalogue entry + potential PDF parsing |
| Legal concerns | Use existing open-source tools, avoid TOS violations |

---

## 6. Effort Estimate

| Component | Complexity |
|-----------|-----------|
| Fork/setup aus_grocery_price_database | Low - 1-2 days |
| Build REST API layer | Medium - 3-5 days |
| Product matching system | Medium-High - 5-7 days |
| Mobile app (basic) | Medium - 5-7 days |
| ALDI data collection | Manual ongoing |
| **Total MVP** | **~3-4 weeks for working prototype** |

---

## 7. Key Resources

### GitHub Repositories
- https://github.com/tjhowse/aus_grocery_price_database
- https://github.com/drkno/au-supermarket-apis

### APIs & Tools
- https://www.pulsemcp.com/servers/coles-woolworths
- https://apiportal.woolworths.com.au/ (official B2B - may require partnership)

### Data & Statistics
- https://www.kaggle.com/datasets/thedevastator/grocery-product-prices-for-australian-states
- https://www.statista.com/statistics/1479659/australia-average-grocery-basket-prices-by-supermarket-chain/

### News & Regulation
- https://ia.acs.org.au/article/2025/supermarkets-should-publish-live-prices--accc.html

---

## 8. Recommendation

**Start with the aus_grocery_price_database** as your foundation:

1. Fork the repository
2. Set up local InfluxDB + Grafana
3. Let it collect price data for 1-2 weeks
4. Build a simple API on top
5. Create basic mobile/web frontend
6. Add ALDI manually for key products
7. Iterate based on user feedback

This approach leverages working code, avoids legal issues, and can be enhanced incrementally.

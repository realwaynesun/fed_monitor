# Wayne's Macro Dashboard Trading Guide

> A beginner's guide to using macroeconomic data for trading decisions

## Table of Contents

1. [Dashboard Overview](#1-dashboard-overview)
2. [Core Concept: The Fed's Interest Rate Corridor](#2-core-concept-the-feds-interest-rate-corridor)
3. [Key Indicators Explained](#3-key-indicators-explained)
4. [Understanding the Alert System](#4-understanding-the-alert-system)
5. [Identifying Trading Signals](#5-identifying-trading-signals)
6. [Practical Examples](#6-practical-examples)
7. [FAQ](#7-faq)

---

## 1. Dashboard Overview

### 1.1 Access

URL: https://realwaynesun.github.io/fed_monitor/

### 1.2 Interface Layout

```
┌─────────────────────────────────────────────────┐
│  Header + FED/BOJ Toggle Buttons                │
├─────────────────────────────────────────────────┤
│  Key Metrics Panel (8 core data points)         │
├─────────────────────────────────────────────────┤
│  Alerts Panel (Critical / Warning / Info)       │
├─────────────────────────────────────────────────┤
│  Charts Section (16 charts)                     │
├─────────────────────────────────────────────────┤
│  Data Tables (detailed values + changes)        │
└─────────────────────────────────────────────────┘
```

### 1.3 Data Update Schedule

- **Daily updates**: 7:00 UTC
- **Data source**: Federal Reserve Economic Data (FRED)
- **Lag**: T+1 (most indicators)

---

## 2. Core Concept: The Fed's Interest Rate Corridor

### 2.1 What is the Interest Rate Corridor?

The Federal Reserve controls short-term money markets through a series of administered rates:

```
        Discount Window Rate ←── Ceiling (penalty rate)
            │
        SRF Rate (Standing Repo Facility)
            │
        IORB (Interest on Reserve Balances) ←── Target range upper bound
            │
        EFFR (Effective Fed Funds Rate) ←── Actual market rate
            │
        ON RRP (Overnight Reverse Repo) ←── Target range lower bound
            │
```

### 2.2 Why Does This Matter?

| Condition | Meaning | Market Impact |
|-----------|---------|---------------|
| EFFR near IORB | Funding conditions tightening | Potential liquidity stress |
| EFFR near ON RRP | Funding conditions loose | Ample liquidity |
| EFFR outside corridor | Abnormal signal | Requires Fed intervention |

---

## 3. Key Indicators Explained

### 3.1 Top Key Metrics Panel

| Indicator | Meaning | Normal Range | Watch For |
|-----------|---------|--------------|-----------|
| **EFFR** | Effective Fed Funds Rate | Within target range | Deviation from midpoint |
| **IORB** | Interest on Reserve Balances | Target upper bound | Fed's set ceiling |
| **SOFR** | Secured Overnight Financing Rate | Slightly below EFFR | Repo market conditions |
| **EFFR-IORB** | Spread | -1 to -5 bps | Funding tightness |
| **SOFR-EFFR** | Spread | -5 to +5 bps | Secured vs unsecured |
| **Fed Assets** | Federal Reserve Balance Sheet | Trend | QT progress |
| **RRP Usage** | Reverse Repo Facility Usage | Trend | Liquidity reservoir |
| **Reserves** | Bank Reserve Balances | >$3T | System liquidity |

### 3.2 EFFR-IORB Spread (Most Important!)

This is the **primary indicator** for monitoring funding conditions:

| Value | Status | Trading Implication |
|-------|--------|---------------------|
| **-1 to -3 bps** | ✅ Normal | Markets stable |
| **-3 to -5 bps** | ✅ Slightly loose | Ample liquidity |
| **0 to +2 bps** | ⚠️ Tightening | Monitor trend |
| **> +5 bps** | 🚨 Tight | Potential volatility |

### 3.3 Liquidity Indicators

#### Reserves

```
Abundant: > $3.5 trillion → Ample liquidity
Adequate: $3.0-3.5 trillion → Normal functioning
Scarce: < $3.0 trillion → Requires attention
```

#### RRP Usage

```
High RRP: > $1 trillion → Excess cash parked at Fed (liquidity glut)
Low RRP: < $200 billion → Cash flowing to markets (potential tightness)
```

#### Net Liquidity

```
Net Liquidity = Fed Assets - TGA - RRP
```

This is a proxy for actual market liquidity:
- **Rising**: Bullish for risk assets
- **Falling**: Bearish for risk assets

### 3.4 Stress Indicators

| Indicator | Meaning | Warning Level |
|-----------|---------|---------------|
| **VIX** | Market fear index | > 25 elevated, > 35 panic |
| **NFCI** | Financial Conditions Index | > 0 tightening, < 0 loosening |
| **HY OAS** | High Yield spread | > 500 bps elevated |
| **IG OAS** | Investment Grade spread | > 150 bps elevated |

---

## 4. Understanding the Alert System

### 4.1 Alert Levels

| Level | Color | Meaning | Action |
|-------|-------|---------|--------|
| **Critical** | 🔴 Red | Severe anomaly | Immediate attention, may impact trading |
| **Warning** | 🟡 Yellow | Noteworthy | Monitor trends |
| **Info** | 🔵 Blue | Informational | Awareness only |

### 4.2 Common Alert Interpretations

#### Rate-Related Alerts

```
⚠️ "EFFR-IORB spread elevated (5-day MA > 0)"
Meaning: Persistent funding tightness
Action: Watch short-end rate volatility, be cautious with leverage

⚠️ "SOFR-EFFR spread > 10 bps"
Meaning: Divergence between repo and fed funds markets
Action: Monitor repo market stress
```

#### Liquidity-Related Alerts

```
🚨 "Reserves/Bank Assets ratio < 12%"
Meaning: Insufficient bank reserves, potential liquidity stress
Action: Reduce risk exposure

⚠️ "RRP usage declined > $100B in 5 days"
Meaning: Large outflows from RRP, potentially into Treasury market
Action: Monitor Treasury supply/demand dynamics
```

#### Stress-Related Alerts

```
🚨 "VIX > 35"
Meaning: Market in panic mode
Action: Avoid chasing, wait for volatility to subside

⚠️ "HY OAS > 500 bps"
Meaning: Credit market stress rising
Action: Reduce high-risk bond holdings
```

---

## 5. Identifying Trading Signals

### 5.1 Liquidity Cycles

#### Liquidity Expansion (Bullish for Risk Assets)

Characteristics:
- [ ] Net Liquidity rising
- [ ] RRP usage declining (cash flowing out)
- [ ] Reserves stable or rising
- [ ] VIX low (< 18)

Trading Strategy:
- Increase exposure to equities, crypto, and risk assets
- Consider using leverage
- Focus on growth stocks

#### Liquidity Contraction (Bearish for Risk Assets)

Characteristics:
- [ ] Net Liquidity falling
- [ ] Reserves declining
- [ ] EFFR-IORB spread narrowing or turning positive
- [ ] VIX rising

Trading Strategy:
- Reduce risk exposure
- Increase cash or short-term Treasuries
- Focus on defensive sectors

### 5.2 Key Turning Point Signals

#### 🚨 Liquidity Stress Signals

Be highly vigilant when these conditions appear simultaneously:

1. EFFR-IORB > 0 (funding tight)
2. Reserves declining rapidly
3. VIX rising
4. Credit spreads widening

**Historical Example**: September 2019 repo market crisis

#### ✅ Liquidity Improvement Signals

1. Fed announces QT slowdown or begins QE
2. RRP usage declining from highs
3. EFFR-IORB returning to normal range
4. VIX falling from elevated levels

### 5.3 Seasonal Factors

| Timing | Potential Impact | Reason |
|--------|------------------|--------|
| Month-end | Tighter liquidity | Bank balance sheet adjustments |
| Quarter-end | Even tighter | Regulatory reporting requirements |
| Tax dates (Apr, Jun, Sep, Dec) | TGA rises, liquidity tightens | Tax payments flow to Treasury |
| Heavy Treasury issuance | Liquidity tightens | Market must absorb supply |

---

## 6. Practical Examples

### Example 1: Using Net Liquidity to Gauge Market Direction

**Context**: Early 2023, markets recovering from 2022 bear market

**Observations**:
- Net Liquidity rebounding from lows
- RRP usage declining from $2.5T peak
- Reserves stable above $3T

**Trade**:
- Increased equity allocation
- Result: S&P 500 rallied over 20% from lows

### Example 2: Identifying Liquidity Stress

**Context**: Month-end with unusual market volatility

**Dashboard showed**:
- EFFR-IORB rose from -2 bps to +3 bps
- Warning alert triggered
- Short-term Treasury yields spiked

**Trade**:
- Reduced leverage
- Increased cash holdings
- Result: Avoided short-term drawdown

### Example 3: BOJ Monitoring

**After switching to BOJ view**:
- 10-year JGB yield approaching 1.5%
- USD/JPY breaking above 150

**Trading implications**:
- Yen carry trade risk increasing
- Watch for BOJ intervention
- Spillover effects on global liquidity

---

## 7. FAQ

### Q1: How often is the data updated?

A: Daily around 15:00 Beijing time (07:00 UTC). Most FRED data is released T+1.

### Q2: Is EFFR-IORB showing -1 normal?

A: Completely normal. This means EFFR is 1 basis point below IORB, which is normal market pricing.

### Q3: How do I determine if we're in a liquidity stress period?

A: Check this combination of indicators:
1. Is EFFR-IORB > 0?
2. Are reserves < $3T?
3. Is VIX > 20?
4. Are there Critical alerts?

If multiple conditions are met, be cautious.

### Q4: What's the point of BOJ data?

A: The Bank of Japan is the world's second-largest central bank. Its policy changes affect:
- Yen exchange rate (impacts carry trades)
- Global bond markets (Japanese investors are major US Treasury buyers)
- Global liquidity (yen is a major funding currency)

### Q5: Why monitor VIX?

A: VIX is the market's fear barometer:
- < 15: Extremely calm (possibly too complacent)
- 15-20: Normal volatility
- 20-25: Elevated volatility
- 25-35: Market stress
- \> 35: Panic mode

### Q6: How can I set up my own alerts?

A: The dashboard doesn't provide push notifications. Recommendations:
1. Check daily at a set time (e.g., before market open)
2. Focus on Critical and Warning alerts
3. Combine with other tools (e.g., TradingView alerts)

---

## Appendix: Quick Reference Tables

### Interest Rate Indicators

| Code | Name | Normal | Warning |
|------|------|--------|---------|
| effr | Effective Fed Funds Rate | Within target | Outside range |
| iorb | Interest on Reserve Balances | Target upper bound | - |
| sofr | Secured Overnight Financing Rate | ≈ EFFR | Large deviation from EFFR |
| spread_effr_iorb | EFFR-IORB Spread | -1 to -5 bps | > 0 bps |

### Liquidity Indicators

| Code | Name | Normal | Warning |
|------|------|--------|---------|
| reserves_mil | Bank Reserves | > $3T | < $3T |
| rrp_usage_bil | RRP Usage | Trend | Sharp changes |
| walcl_mil | Fed Total Assets | Trend | Sharp changes |

### Stress Indicators

| Code | Name | Normal | Warning |
|------|------|--------|---------|
| vix | Volatility Index | < 20 | > 25 |
| nfci | Financial Conditions Index | < 0 | > 0 |
| hy_oas | High Yield OAS | < 400 bps | > 500 bps |

---

## Disclaimer

This guide is for educational purposes only and does not constitute investment advice. Macroeconomic data analysis is one factor among many in trading decisions. Please combine with other analytical methods and consider your personal risk tolerance when making investment decisions. Past performance does not guarantee future results.

---

*Last updated: January 2026*

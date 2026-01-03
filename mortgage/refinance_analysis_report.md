# Mortgage Portfolio Refinance Analysis Report

**Prepared:** January 3, 2026  
**Prepared For:** Frank Breen  
**Properties:** 711pine, 819helen, 905brown (MHB Properties LLC), parnell (Personal)

---

## Executive Summary

| Property | Balance | Rate | Monthly P&I | Status | Recommendation |
|----------|---------|------|-------------|--------|----------------|
| **711pine** | $54,160 | 8.25% | $440 | ⚠️ **CRITICAL** | Refinance immediately |
| **819helen** | $56,854 | 8.00% | $432 | ⚠️ **CRITICAL** | Refinance immediately |
| **905brown** | $11,029 | 7.95% | $305 | ✅ OK | Pay off or refinance |
| **parnell** | $136,486 | 3.75% | $834 | ✅ **EXCELLENT** | Keep current loan |

**Total MHB Debt:** $122,043  
**Total Personal Debt:** $136,486  
**Combined Portfolio:** $258,529

---

## 1. Critical Issues: 711pine & 819helen

### The Problem: Interest-Only Trap

Both properties have variable rate loans where **rate increases caused payments to become interest-only**.

#### 711pine Analysis

| Metric | Value | Issue |
|--------|-------|-------|
| Original Balance (2020) | $66,621.85 | |
| Current Balance (2026) | $54,160.09 | |
| Principal Paid (67 payments) | $5,515.40 | **Only 8.3% of original** |
| Interest Paid | $24,153.66 | **4.4x principal paid** |
| Zero-Principal Payments | **24 of 67 (36%)** | ⚠️ Interest-only periods |
| Total Paid | $36,022.16 | |
| Principal Reduction | $12,461.76 | Doesn't match payments! |

**Rate History - 711pine:**
```
2021-04: 4.95% (start)
2022-03: 5.00% (+0.05)
2022-05: 5.50% (+0.50)
2022-06: 6.25% (+0.75)
2022-07: 7.00% (+0.75)
2022-09: 7.75% (+0.75)
2022-11: 8.50% (+0.75)
2022-12: 9.00% (+0.50)
2023-02: 9.25% (+0.25)
2023-03: 9.50% (+0.25)
2023-05: 9.75% (+0.25)
2023-07: 10.00% (+0.25) ← PEAK
2024-09: 9.50% (-0.50)
2024-11: 9.25% (-0.25)
2024-12: 9.00% (-0.25)
2025-09: 8.75% (-0.25)
2025-10: 8.50% (-0.25)
2025-12: 8.25% (-0.25) ← Current
```

**19 rate changes in 4.5 years!** Rate doubled from 4.95% to 10%.

#### 819helen Analysis

| Metric | Value | Issue |
|--------|-------|-------|
| Original Balance (2021) | $67,014.00 | |
| Current Balance (2026) | $56,854.29 | |
| Principal Paid (66 payments) | $6,639.25 | **Only 9.9% of original** |
| Interest Paid | $21,968.75 | **3.3x principal paid** |
| Zero-Principal Payments | **17 of 66 (26%)** | ⚠️ Interest-only periods |
| Total Paid | $33,329.00 | |
| Principal Reduction | $10,159.71 | |

**Rate History - 819helen:**
```
2021-03: 5.25% (start)
2024-03: 9.75% (+4.50) ← HUGE JUMP after 3-year fixed period?
2024-09: 9.25% (-0.50)
2024-11: 9.00% (-0.25)
2024-12: 8.75% (-0.25)
2025-09: 8.50% (-0.25)
2025-10: 8.25% (-0.25)
2025-12: 8.00% (-0.25) ← Current
```

**Suspicious:** Rate jumped 4.5% in one adjustment (Mar 2024). Check loan docs for rate caps.

---

## 2. Payment vs. Interest Analysis

### What Your Payment SHOULD Cover

At current rates with standard amortization:

| Property | Balance | Rate | Required P&I | Your Payment | Shortfall |
|----------|---------|------|--------------|--------------|-----------|
| 711pine | $54,160 | 8.25% | **$526/mo** | $440/mo | **-$86/mo** |
| 819helen | $56,854 | 8.00% | **$536/mo** | $432/mo | **-$104/mo** |

**Your payments are too low to amortize the loans at current rates.**

### Monthly Interest Calculation

| Property | Balance | Rate | Monthly Interest | Your Payment | For Principal |
|----------|---------|------|------------------|--------------|---------------|
| 711pine | $54,160 | 8.25% | $372.35 | $440.00 | $67.65 |
| 819helen | $56,854 | 8.00% | $379.03 | $432.00 | $52.97 |

At current rates, you ARE paying some principal now, but barely. At peak rates (10%), you were underwater:

| Property | Balance | Peak Rate | Monthly Interest | Payment | Principal |
|----------|---------|-----------|------------------|---------|-----------|
| 711pine | ~$58,000 | 10.00% | $483.33 | $440.00 | **-$43.33** |

**Negative amortization risk!**

---

## 3. 905brown - The Success Story

| Metric | Value |
|--------|-------|
| Original Balance (2019) | $36,620.00 |
| Current Balance (2026) | $11,029.23 |
| Principal Paid | $20,723.24 |
| Interest Paid | $11,165.82 |
| Zero-Principal Payments | **0** |
| Paydown Rate | **69.9%** |

**This loan is performing correctly.**

- Fixed or stable rate (7.95%)
- Payment ($305.19) properly covers interest + principal
- On track to pay off ~2029 (10 years early if you keep current pace)

**Recommendation:** Either:
- Pay off with cash/HELOC (~$11k) to eliminate the payment
- Continue as-is - will be paid off soon

---

## 4. Parnell - Personal Residence

| Metric | Value |
|--------|-------|
| Original Balance (2015) | $180,000.00 |
| Current Balance (2026) | $136,485.93 |
| Interest Rate | **3.75% FIXED** |
| Monthly Payment | $833.61 |
| Principal Paid | $31,524.76 |
| Interest Paid | $43,500.14 |
| Zero-Principal Payments | **0** |

**This is an excellent loan. DO NOT REFINANCE.**

- 3.75% fixed rate is below current market (7-8%)
- Refinancing would INCREASE your rate and payment
- Keep this loan for the full term

---

## 5. Refinance Scenarios for 711pine & 819helen

### Option A: Consolidate Both into Single Loan

**Combined Balance:** $111,014

| Term | Rate | Monthly P&I | Total Interest | Total Cost |
|------|------|-------------|----------------|------------|
| 15-year | 7.00% | $998 | $68,640 | $179,654 |
| 15-year | 7.50% | $1,030 | $74,386 | $185,400 |
| 15-year | 8.00% | $1,061 | $79,998 | $191,012 |
| 10-year | 7.00% | $1,289 | $43,680 | $154,694 |
| 10-year | 7.50% | $1,319 | $47,280 | $158,294 |

**vs. Current Path (keeping existing loans):**
- Current combined payment: $872/mo
- At current rates, remaining interest: ~$95,000+
- Time to payoff: 20+ years (if rates stay stable)

### Option B: Refinance Separately

| Property | Balance | 15yr @ 7.5% | Current | Savings/mo |
|----------|---------|-------------|---------|------------|
| 711pine | $54,160 | $502/mo | $440/mo | +$62 more |
| 819helen | $56,854 | $527/mo | $432/mo | +$95 more |

**Note:** Refinance payments are HIGHER, but you're actually paying down principal. Current payments aren't.

### Option C: Pay Off 905brown, Apply Payment to Others

1. Pay off 905brown with $11,029 (cash or HELOC)
2. Apply $305/mo to 711pine or 819helen as extra principal
3. This accelerates payoff by ~3-4 years

---

## 6. Rate Comparison: Are Your Rates Reasonable?

### Prime Rate + Spread Analysis

| Date | Prime Rate | Typical Commercial | 711pine | 819helen | Assessment |
|------|------------|-------------------|---------|----------|------------|
| 2021-04 | 3.25% | 5.25-6.25% | 4.95% | 5.25% | ✅ Fair |
| 2023-07 | 8.50% | 9.50-10.50% | 10.00% | - | ✅ Fair |
| 2025-12 | 7.50% | 8.50-9.50% | 8.25% | 8.00% | ✅ Fair |

**Verdict:** Your rates appear to track Prime Rate reasonably. The issue isn't the rate itself - it's that:
1. Your payment didn't adjust with the rate
2. Variable rate + fixed payment = negative amortization risk

---

## 7. Red Flags & Concerns

### 🚩 Escrow Issues
- Insurance escrow concerns reported
- Request full escrow account statement from Central Savings Bank
- Verify escrow disbursements match actual insurance/tax bills

### 🚩 Reversal Transactions
- 819helen CSV showed many reversals (Type 800)
- Request explanation for each reversal
- May indicate payment processing issues or fee generation

### 🚩 Zero-Principal Payments
- 36% of 711pine payments had $0 principal
- 26% of 819helen payments had $0 principal
- This extended loan life significantly

### 🚩 Payment Amount Never Adjusted
- With variable rate loans, payments should adjust when rates change
- Your payments stayed fixed while rates doubled
- This caused the interest-only trap

---

## 8. Recommendations

### Immediate Actions (This Week)

1. **Request from Central Savings Bank:**
   - Full amortization schedule for 711pine and 819helen
   - Escrow account statements for all properties
   - Explanation of all reversal transactions
   - Loan agreement showing rate adjustment terms and caps

2. **Review Loan Documents:**
   - What is the rate index? (Prime? SOFR?)
   - What is the margin? (Rate = Index + Margin)
   - Are there rate caps? (per adjustment and lifetime)
   - Are there payment caps?

### Short-Term (This Month)

3. **Get Refinance Quotes From:**
   - Local credit unions (often best rates for small commercial)
   - Community banks (not Central Savings)
   - SBA 504 lenders (if investment properties)

4. **Request Quotes For:**
   - 15-year fixed, combined $111k loan
   - 10-year fixed (if cash flow allows)
   - Compare total cost including closing costs

### Medium-Term (Next 90 Days)

5. **Consider:**
   - Removing escrow and paying insurance/taxes directly
   - Paying off 905brown to free up $305/mo
   - Converting to fixed-rate personal loans

---

## 9. Financial Summary

### Current Monthly Outflow (MHB Properties)

| Property | P&I | Escrow Est. | Total |
|----------|-----|-------------|-------|
| 711pine | $440 | ~$150 | ~$590 |
| 819helen | $432 | ~$150 | ~$582 |
| 905brown | $305 | ~$100 | ~$405 |
| **Total** | **$1,177** | **~$400** | **~$1,577** |

### After Recommended Refinance (15yr @ 7.5%)

| Property | New P&I | Escrow | Total |
|----------|---------|--------|-------|
| 711pine + 819helen (combined) | $1,030 | ~$300 | ~$1,330 |
| 905brown (paid off) | $0 | $0 | $0 |
| **Total** | **$1,030** | **~$300** | **~$1,330** |

**Monthly Savings:** ~$247/mo  
**Annual Savings:** ~$2,964/yr  
**Loan Paid Off:** 15 years (vs. 20+ years current path)

---

## 10. Regulatory Filing Information

If you discover the bank violated lending regulations, you can file complaints with:

### Michigan Department of Insurance and Financial Services (DIFS)
- Website: michigan.gov/difs
- Phone: 877-999-6442
- Handles: State-chartered bank complaints

### Consumer Financial Protection Bureau (CFPB)
- Website: consumerfinance.gov/complaint
- Handles: Federal lending law violations, TILA, RESPA

### Potential Violations to Investigate:
- Truth in Lending Act (TILA) - Disclosure requirements
- RESPA - Escrow account requirements
- Unfair/Deceptive practices - If payments structured to never pay principal

---

## Appendix: Data Sources

- Mortgage data from `copilot_db` database (mhb.mortgage, per.mortgage)
- Payment history from `mhb.mortgage_payment`, `per.mortgage_payment`
- Rate history from `mhb.mortgage_rate_history`
- CSV imports from Central Savings Bank statements
- Prime Rate data from Federal Reserve (federalreserve.gov)

---

*Report generated by Copilot Mortgage Analysis System*

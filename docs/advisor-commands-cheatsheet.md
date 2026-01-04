# AI Financial Advisor - Quick Reference Cheatsheet

## Command Overview

| Command | Purpose | Example |
|---------|---------|---------|
| `copilot advisor ask` | Ask natural language questions | `copilot advisor ask "What should I pay first?"` |
| `copilot advisor report` | Generate financial reports | `copilot advisor report --type tax` |
| `copilot advisor plan` | Create payment plans | `copilot advisor plan --months 12 --budget 5000` |
| `copilot advisor alert` | Show urgent alerts | `copilot advisor alert` |

## Quick Start

### Setup (One Time)

```bash
# 1. Install dependencies
pip install openai>=1.0.0

# 2. Get API key from https://platform.openai.com/api-keys

# 3. Add to .env file
echo "OPENAI_API_KEY=sk-your-key-here" >> .env

# 4. Test it works
copilot advisor alert
```

### Daily Usage

```bash
# Morning check
copilot advisor alert

# Ask a question
copilot advisor ask "What's my most urgent financial task today?"
```

## Common Questions to Ask

### Priority & Planning

```bash
copilot advisor ask "What should I pay first?"
copilot advisor ask "Which bills are most urgent?"
copilot advisor ask "How should I prioritize my limited budget?"
copilot advisor ask "What are my top 3 financial priorities?"
```

### Foreclosure Risk

```bash
copilot advisor ask "How much do I need to avoid foreclosure?"
copilot advisor ask "Am I at risk of losing any properties?"
copilot advisor ask "Which properties are in the most danger?"
copilot advisor ask "What happens if I don't pay the 2022 taxes?"
```

### Property Analysis

```bash
copilot advisor ask "Which property has the worst tax situation?"
copilot advisor ask "Which property costs me the most in taxes?"
copilot advisor ask "How much do I owe on 905brown?"
copilot advisor ask "Compare tax burden across all properties"
```

### Financial Overview

```bash
copilot advisor ask "What's my total outstanding debt?"
copilot advisor ask "How much have I paid in taxes this year?"
copilot advisor ask "What's my overall financial health?"
copilot advisor ask "What are my biggest financial risks?"
```

### Strategic Questions

```bash
copilot advisor ask "Should I focus on one property or spread payments?"
copilot advisor ask "Is it worth getting a loan to pay off taxes?"
copilot advisor ask "Can I afford to buy another property?"
copilot advisor ask "Should I sell a property to cover tax debt?"
copilot advisor ask "How much should I budget for taxes next year?"
```

### PRE Exemption

```bash
copilot advisor ask "What's the PRE exemption status for my properties?"
copilot advisor ask "How much would I save with PRE exemption?"
copilot advisor ask "Why are taxes higher on 905brown than parnell?"
```

## Report Types

### Summary (Default)
**Best for:** Quick overview of financial health

```bash
copilot advisor report
copilot advisor report --type summary
```

**Contains:**
- Overall financial position
- Critical risks
- Key metrics
- Top 3 actions

---

### Tax Report
**Best for:** Detailed tax analysis

```bash
copilot advisor report --type tax
```

**Contains:**
- Tax situation by property
- Foreclosure risk assessment
- Payment priorities
- Recent payment history
- Detailed action plan

---

### Weekly Report
**Best for:** Weekly review meetings

```bash
copilot advisor report --type weekly
```

**Contains:**
- This week's status
- Immediate action items
- Upcoming deadlines
- Quick wins

---

### Monthly Report
**Best for:** Strategic planning

```bash
copilot advisor report --type monthly
```

**Contains:**
- Monthly trends
- Strategic recommendations
- Long-term planning
- Month-over-month comparison

---

### Cash Flow Report
**Best for:** Budget planning

```bash
copilot advisor report --type cashflow
```

**Contains:**
- Income vs expenses
- Tax obligations
- Budget recommendations
- Cash flow projections

## Payment Plan Examples

### Basic Plans

```bash
# Default 12-month plan
copilot advisor plan

# Aggressive 6-month plan
copilot advisor plan --months 6

# Conservative 24-month plan
copilot advisor plan --months 24
```

### Budget-Constrained Plans

```bash
# $3,000 monthly budget
copilot advisor plan --budget 3000

# $5,000 monthly budget over 12 months
copilot advisor plan --months 12 --budget 5000

# Minimal budget - see what's possible
copilot advisor plan --budget 1500
```

### Property-Specific Plans

```bash
# Focus on one property
copilot advisor plan --property 905brown

# Combined: one property, 8 months, $2500/month
copilot advisor plan -p 711pine -m 8 -b 2500
```

## Alert Command

### What You'll See

```bash
copilot advisor alert
```

**Output includes:**
- 🔴 **CRITICAL**: Foreclosure risks (3+ years delinquent)
- 🟡 **WARNING**: Bills approaching foreclosure
- 🟢 **OK**: Properties in good standing
- 💡 **AI Insights**: Top 3 action items

**Run frequency:**
- Daily: If high risk
- Weekly: If managing actively
- Monthly: If situation is stable

## Tips for Better Results

### 1. Be Specific
❌ "What should I do?"
✅ "What should I pay first to avoid foreclosure with a $5,000 budget?"

### 2. Include Context
❌ "Is this bad?"
✅ "I have $27,000 outstanding in taxes across 4 properties. Is this a crisis?"

### 3. Use Property Names
❌ "How much do I owe?"
✅ "How much do I owe on 905brown and 711pine combined?"

### 4. Ask Follow-ups
```bash
copilot advisor ask "What should I pay first?"
# Review answer, then ask:
copilot advisor ask "What if I can only afford half of that?"
```

### 5. Combine with Data Commands
```bash
# First, get the data
copilot tax foreclosure
copilot tax priority --limit 10

# Then, ask for interpretation
copilot advisor ask "Based on my foreclosure risk, what's the smartest payment strategy?"
```

## Common Workflows

### Weekly Review
```bash
copilot advisor alert
copilot advisor report --type weekly
# Act on recommendations
```

### Monthly Planning
```bash
copilot advisor report --type monthly
copilot advisor plan --budget <your-budget>
# Implement plan
```

### Before Major Financial Decision
```bash
copilot advisor report --type summary
copilot advisor ask "Can I afford [specific decision]?"
# Review and decide
```

### Foreclosure Emergency
```bash
copilot tax foreclosure
copilot advisor ask "I have $X available immediately. What should I pay to minimize foreclosure risk?"
copilot advisor plan --months 3 --budget <available>
# Execute plan immediately
```

## Troubleshooting Quick Fixes

| Problem | Quick Fix |
|---------|-----------|
| "API key not set" | Add `OPENAI_API_KEY=...` to `.env` file |
| "OpenAI library not installed" | Run `pip install openai` |
| "Rate limit exceeded" | Wait 5 minutes, then try again |
| Generic/unhelpful answers | Be more specific in your question |
| Inaccurate data | Check database is current with `copilot tax foreclosure` |

## Cost Reference

**Typical costs per query:**
- Simple question: $0.01-0.03
- Report: $0.03-0.06
- Payment plan: $0.02-0.04
- Alert: $0.02-0.05

**Monthly estimate (moderate use):**
- ~$2-5 for regular use
- ~$10-20 for heavy use

**Cost saving tips:**
- Use GPT-3.5 instead of GPT-4 (edit `advisor_cmd.py`)
- Batch multiple questions together
- Use `copilot tax` commands for simple lookups
- Save report outputs to review later

## Property Quick Reference

Your properties in the system:

| Property | Type | PRE Status | Typical Tax | Notes |
|----------|------|------------|-------------|-------|
| **905brown** | Rental | 0% | ~$3,700/yr | MHB Properties LLC |
| **711pine** | Rental | 0% | ~$5,000/yr | MHB Properties LLC |
| **819helen** | Rental | 0% | ~$4,500/yr | MHB Properties LLC |
| **parnell** | Personal | 100% | ~$700/yr | Primary residence, lower taxes |

**Michigan Foreclosure Rule:**
- 3+ years delinquent = foreclosure risk
- Priority: Pay oldest bills first
- Personal residence (PRE) has some protections

## One-Line Command Examples

```bash
# Daily
copilot advisor alert

# Weekly
copilot advisor report -t weekly

# Before paying bills
copilot advisor ask "What should I pay first?"

# Planning
copilot advisor plan -m 12 -b 4000

# Emergency
copilot advisor ask "How much do I need to avoid foreclosure RIGHT NOW?"

# Strategic
copilot advisor ask "What's my 12-month tax strategy?"

# Property-specific
copilot advisor ask "What's the situation with 905brown?"

# Budget planning
copilot advisor ask "How much should I budget monthly for all properties?"

# Comparison
copilot advisor ask "Which property is the biggest financial burden?"

# Verification
copilot advisor ask "If I pay $X today, which bills should I pay?"
```

## When to Use Each Command

### Use `advisor ask` when:
- You have a specific question
- You need personalized advice
- You want interpretation of data
- You're exploring options

### Use `advisor report` when:
- You need comprehensive overview
- You're doing weekly/monthly review
- You want formatted documentation
- You need to share with others

### Use `advisor plan` when:
- You have budget to allocate
- You need payment schedule
- You want to become current
- You're planning ahead

### Use `advisor alert` when:
- You want quick status check
- You're doing daily review
- You need to spot problems fast
- You want AI priorities

## Integration with Other Copilot Commands

```bash
# Data commands (no AI cost)
copilot tax foreclosure          # See foreclosure risks
copilot tax priority             # See payment priorities
copilot tax trends 905brown      # See historical trends

# AI interpretation (uses API)
copilot advisor ask "Interpret the foreclosure report"
copilot advisor ask "Explain these payment priorities"
copilot advisor ask "What do the trends tell me?"
```

## Keyboard Shortcuts & Aliases (Optional)

Add to your `.bashrc` or `.zshrc`:

```bash
# Quick aliases
alias ca='copilot advisor'
alias caa='copilot advisor ask'
alias car='copilot advisor report'
alias cap='copilot advisor plan'
alias caal='copilot advisor alert'

# Now use:
caa "What should I pay first?"
car -t weekly
cap -m 6 -b 5000
caal
```

## Emergency Response Checklist

If you discover foreclosure risk:

1. ✅ Run `copilot tax foreclosure` to see exact amounts
2. ✅ Run `copilot advisor ask "How much to avoid foreclosure?"`
3. ✅ Assess available funds
4. ✅ Run `copilot advisor plan --months 3 --budget <available>`
5. ✅ Execute payment plan immediately
6. ✅ Verify with `copilot tax foreclosure` after payment
7. ✅ Set up monthly review to prevent recurrence

---

**Need more details?** See full guide: `docs/advisor-guide.md`

**Issues?** Check troubleshooting section in full guide

**Questions?** Ask the advisor: `copilot advisor ask "How do I use the advisor effectively?"`

---

*Quick Reference v1.0 - Last updated: 2026-01-04*

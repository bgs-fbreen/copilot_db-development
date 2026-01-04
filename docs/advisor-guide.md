# AI Financial Advisor - Comprehensive Guide

## Overview

The Copilot AI Financial Advisor is an intelligent assistant that helps you manage your rental property finances using advanced AI technology. It analyzes your property tax data, provides personalized recommendations, and helps you make informed financial decisions.

### What It Can Do

- **Answer Financial Questions**: Ask natural language questions about your finances and get intelligent, context-aware answers
- **Generate Reports**: Create comprehensive financial reports with AI-powered insights
- **Create Payment Plans**: Generate customized tax payment plans based on your budget
- **Proactive Alerts**: Get warnings about foreclosure risks and other urgent financial matters

### How It Works

The advisor combines two powerful technologies:

1. **Database Context**: Queries your Copilot database to gather real-time financial data (tax bills, payments, property information)
2. **OpenAI GPT-4**: Uses advanced AI to analyze the data and provide intelligent recommendations

This combination ensures that all advice is based on your actual financial situation, not generic suggestions.

## Setup Instructions

### 1. Install Dependencies

First, ensure you have the OpenAI library installed:

```bash
pip install openai>=1.0.0
```

Or install all requirements:

```bash
pip install -r requirements.txt
```

### 2. Get an OpenAI API Key

1. Visit [OpenAI's website](https://platform.openai.com/api-keys)
2. Create an account or sign in
3. Navigate to API Keys section
4. Click "Create new secret key"
5. Copy the key (you won't be able to see it again!)

**Pricing**: OpenAI charges per API usage. GPT-4 costs approximately:
- Input: $0.03 per 1K tokens (~750 words)
- Output: $0.06 per 1K tokens (~750 words)

Typical advisor queries cost $0.01-0.05 each.

### 3. Configure Your API Key

Add your API key to your `.env` file:

```bash
# Copy the example file if you haven't already
cp .env.example .env

# Edit .env and add your key
nano .env
```

Add this line:

```
OPENAI_API_KEY=sk-your-actual-api-key-here
```

**Security Note**: Never commit your `.env` file to version control! It's already in `.gitignore`.

### 4. Verify Setup

Test the advisor is working:

```bash
copilot advisor alert
```

If you see alerts, you're all set! If you get an error about the API key, double-check your `.env` file.

## Commands

### `copilot advisor ask` - Natural Language Questions

Ask the AI advisor any question about your finances.

#### Usage

```bash
copilot advisor ask <question>
```

#### Examples

**Priority Questions:**
```bash
copilot advisor ask "What should I pay first?"
copilot advisor ask "Which bills are most urgent?"
copilot advisor ask "How should I prioritize my tax payments?"
```

**Foreclosure Risk:**
```bash
copilot advisor ask "How much do I need to avoid foreclosure?"
copilot advisor ask "Am I at risk of losing any properties?"
copilot advisor ask "Which properties are in danger?"
```

**Property-Specific:**
```bash
copilot advisor ask "Which property has the worst tax situation?"
copilot advisor ask "How much do I owe on 905brown?"
copilot advisor ask "What's the PRE exemption status for my properties?"
```

**Financial Overview:**
```bash
copilot advisor ask "What's my total outstanding debt?"
copilot advisor ask "How much have I paid in taxes this year?"
copilot advisor ask "What are my biggest financial risks?"
```

**Strategic Planning:**
```bash
copilot advisor ask "Should I focus on one property or spread payments?"
copilot advisor ask "Is it worth getting a loan to pay off taxes?"
copilot advisor ask "What happens if I can't pay everything?"
```

#### Output Format

The advisor responds with formatted markdown including:
- Clear headers and sections
- Bullet points for action items
- Specific dollar amounts
- Risk assessments with 🔴🟡🟢 indicators
- Direct recommendations

### `copilot advisor report` - AI-Generated Reports

Generate comprehensive financial reports with AI analysis.

#### Usage

```bash
copilot advisor report [--type TYPE]
```

#### Report Types

**Summary Report (Default)**
```bash
copilot advisor report
copilot advisor report --type summary
```

Provides:
- Overall financial health assessment
- Critical risks and warnings
- Key financial metrics
- Top 3 recommended actions

**Tax Report**
```bash
copilot advisor report --type tax
```

Provides:
- Complete tax situation by property
- Foreclosure risk analysis
- Payment priority recommendations
- Recent payment history
- Detailed action plan

**Weekly Report**
```bash
copilot advisor report --type weekly
```

Provides:
- This week's financial status
- Immediate action items
- Upcoming deadlines
- Quick wins and priorities

**Monthly Report**
```bash
copilot advisor report --type monthly
```

Provides:
- Monthly financial trends
- Strategic recommendations
- Long-term planning suggestions
- Comparison to previous months (if data available)

**Cash Flow Report**
```bash
copilot advisor report --type cashflow
```

Provides:
- Income vs expenses analysis
- Tax obligations as primary expense
- Budget recommendations
- Cash flow projections

*Note: Full cash flow analysis requires additional income/expense tracking tables.*

### `copilot advisor plan` - Payment Plan Generator

Generate a customized payment plan to become current on taxes.

#### Usage

```bash
copilot advisor plan [OPTIONS]
```

#### Options

- `--months, -m`: Number of months for the payment plan (default: 12)
- `--budget, -b`: Monthly budget available for tax payments (dollars)
- `--property, -p`: Focus on specific property code

#### Examples

**Basic 12-Month Plan:**
```bash
copilot advisor plan
```

**6-Month Aggressive Plan:**
```bash
copilot advisor plan --months 6
```

**Budget-Constrained Plan:**
```bash
copilot advisor plan --budget 3000
```

**Property-Specific Plan:**
```bash
copilot advisor plan --property 905brown --months 8
```

**Combined Options:**
```bash
copilot advisor plan -m 12 -b 5000 -p 711pine
```

#### Output Includes

- Priority-ordered payment schedule
- Month-by-month breakdown
- Total amount needed
- Foreclosure risk assessment
- Recommendations if budget is insufficient
- Timeline to become current

### `copilot advisor alert` - Proactive Alerts

Show urgent financial alerts and warnings.

#### Usage

```bash
copilot advisor alert
```

No options needed - it automatically checks your entire financial situation.

#### What It Shows

**Critical Alerts (🔴):**
- Properties at foreclosure risk (3+ years delinquent)
- Bills requiring immediate payment
- Total amount needed to avoid foreclosure

**Warnings (🟡):**
- Bills approaching foreclosure threshold
- Large outstanding balances
- Properties with unusual payment patterns

**Status (🟢):**
- Properties in good standing
- Recent successful payments
- Positive financial indicators

**AI Insights:**
- Top 3 immediate action items
- Specific recommendations with dollar amounts
- Strategic suggestions for risk mitigation

## Privacy and Security

### Data Privacy

- **All data stays local**: The advisor queries your local Copilot database
- **Only summaries sent to OpenAI**: Property codes, amounts, and dates - no personal identifying information
- **No data stored by OpenAI**: Queries are processed and discarded (check OpenAI's data retention policy)

### API Key Security

- **Never commit your API key**: Always use `.env` file (already in `.gitignore`)
- **Rotate keys regularly**: Generate new keys periodically in OpenAI dashboard
- **Monitor usage**: Check OpenAI dashboard for unexpected API usage
- **Use separate keys**: Consider separate keys for development vs production

### Best Practices

1. **Review recommendations**: The AI is smart but not infallible - always verify critical decisions
2. **Verify dollar amounts**: Cross-check against your database with `copilot tax foreclosure` or `copilot tax priority`
3. **Keep data current**: The advisor is only as good as your database data
4. **Don't share sensitive output**: Advisor responses may contain financial details

## Customization Options

### Adjusting AI Behavior

The AI's personality and focus can be customized by modifying the system prompt in `advisor_cmd.py`:

```python
def create_system_prompt(context_type='general'):
    base_prompt = """You are a financial advisor for a small landlord...
    
    # Customize this prompt to change AI behavior:
    # - Add specific rules or preferences
    # - Change tone (formal, casual, technical)
    # - Focus on specific concerns
    # - Add domain-specific knowledge
```

### Changing AI Model

To use a different OpenAI model (e.g., GPT-3.5 for cost savings):

```python
# In advisor_cmd.py, update the model parameter:
response = client.chat.completions.create(
    model="gpt-3.5-turbo",  # Changed from "gpt-4"
    messages=messages,
    temperature=0.7,
    max_tokens=1500
)
```

**Model Comparison:**
- **GPT-4**: Most intelligent, best for complex analysis (~10x more expensive)
- **GPT-3.5-turbo**: Fast and cost-effective, good for simple questions
- **GPT-4-turbo**: Balanced option (not yet fully released)

### Adding Custom Context

To include additional database context:

1. Add queries to helper functions (`get_financial_context`, etc.)
2. Update context summary in `query_openai` function
3. Test that the AI properly uses the new information

Example:
```python
def get_financial_context():
    # ... existing code ...
    
    # Add rental income context
    income_query = """
        SELECT property_code, SUM(amount) as monthly_income
        FROM rental_income
        WHERE date >= CURRENT_DATE - INTERVAL '3 months'
        GROUP BY property_code
    """
    context['rental_income'] = execute_query(income_query)
    
    return context
```

## Troubleshooting

### "Error: OPENAI_API_KEY not set"

**Cause**: API key not found in environment.

**Solutions:**
1. Check `.env` file exists and contains `OPENAI_API_KEY=...`
2. Make sure `.env` is in the project root directory
3. Restart your terminal/shell after editing `.env`
4. Verify the key doesn't have extra spaces or quotes

### "Error: OpenAI library not installed"

**Cause**: Missing OpenAI package.

**Solution:**
```bash
pip install openai>=1.0.0
```

### "Rate limit exceeded"

**Cause**: Too many API requests in short time.

**Solutions:**
1. Wait a few minutes before trying again
2. Upgrade your OpenAI plan for higher limits
3. Reduce frequency of advisor queries

### "Authentication failed"

**Cause**: Invalid API key.

**Solutions:**
1. Generate a new API key in OpenAI dashboard
2. Update `.env` with new key
3. Check for typos in API key

### "Response timeout"

**Cause**: API request took too long.

**Solutions:**
1. Check your internet connection
2. Try again (temporary OpenAI issue)
3. Simplify your question (complex queries take longer)

### Inaccurate Recommendations

**Cause**: Outdated or incomplete database data.

**Solutions:**
1. Ensure tax bills are up to date
2. Record all payments in the database
3. Verify property information is current
4. Check that views (`v_property_tax_foreclosure_risk`, etc.) are working

### AI Gives Generic Advice

**Cause**: Missing database context.

**Solutions:**
1. Check that queries in helper functions return data
2. Verify database views exist and contain data
3. Add more specific context to your questions
4. Use property names in questions ("905brown" vs "my property")

## Advanced Usage

### Combining with Other Commands

Get comprehensive information by combining advisor with other copilot commands:

```bash
# 1. Check foreclosure risk
copilot tax foreclosure

# 2. Get AI recommendations
copilot advisor ask "Based on the foreclosure risk, what's my best strategy?"

# 3. Generate payment plan
copilot advisor plan --budget 5000

# 4. View priority list
copilot tax priority --limit 10
```

### Scripting and Automation

You can use the advisor in scripts:

```bash
#!/bin/bash
# weekly-check.sh - Run weekly financial review

echo "=== Weekly Financial Check ==="
copilot advisor alert
copilot advisor report --type weekly

# Email results (requires mail setup)
copilot advisor report --type weekly | mail -s "Weekly Financial Report" you@example.com
```

### Batch Questions

Ask multiple questions efficiently:

```bash
# Save questions to file
cat > questions.txt << EOF
What should I pay first?
How much to avoid foreclosure?
What's my biggest risk?
EOF

# Ask each question
while read question; do
    echo "Q: $question"
    copilot advisor ask "$question"
    echo "---"
done < questions.txt
```

## Cost Management

### Estimating Costs

Typical costs per command:
- `advisor ask`: $0.01-0.03 (simple questions)
- `advisor report`: $0.03-0.06 (comprehensive reports)
- `advisor plan`: $0.02-0.04 (payment plans)
- `advisor alert`: $0.02-0.05 (includes AI insights)

Monthly usage estimate (moderate use):
- 20 questions: ~$0.40
- 4 weekly reports: ~$0.16
- 2 payment plans: ~$0.08
- Daily alerts: ~$1.50

**Total: ~$2-5/month** for regular use

### Reducing Costs

1. **Use GPT-3.5**: Change model to save ~90% (with some quality trade-off)
2. **Batch questions**: Ask multiple things in one query
3. **Use non-AI commands**: Use `copilot tax foreclosure` for simple lookups
4. **Cache results**: Save report outputs to reference later
5. **Disable AI insights in alerts**: Comment out the OpenAI call in `show_alerts()`

## Examples and Use Cases

### Use Case 1: Monthly Financial Review

```bash
# Generate comprehensive monthly report
copilot advisor report --type monthly

# Check for any new alerts
copilot advisor alert

# Create next month's payment plan
copilot advisor plan --budget 4000
```

### Use Case 2: Foreclosure Emergency

```bash
# Identify immediate risk
copilot tax foreclosure

# Get AI strategy
copilot advisor ask "I have $10,000 available. How should I spend it to minimize foreclosure risk?"

# Create aggressive payment plan
copilot advisor plan --months 3 --budget 3333
```

### Use Case 3: Property Purchase Decision

```bash
# Assess current situation
copilot advisor report --type summary

# Ask strategic question
copilot advisor ask "Given my current tax situation, can I afford to buy another rental property?"
```

### Use Case 4: Year-End Tax Planning

```bash
# Get detailed tax report
copilot advisor report --type tax

# Ask about deductions
copilot advisor ask "What tax deductions should I be tracking for my rental properties?"

# Plan for next year
copilot advisor ask "How much should I budget monthly for property taxes next year?"
```

## Feedback and Improvements

The AI advisor learns from the prompts and context you provide. To improve results:

1. **Be specific in questions**: Include property names, dollar amounts, timeframes
2. **Provide context**: Mention constraints, goals, or concerns
3. **Iterate**: If an answer isn't helpful, rephrase and ask again
4. **Verify**: Always cross-check important recommendations with actual data

## Support

For issues or questions:
1. Check this guide first
2. Review troubleshooting section
3. Verify database data is current
4. Check OpenAI API status page
5. Contact support or file an issue in the repository

---

*Last updated: 2026-01-04*

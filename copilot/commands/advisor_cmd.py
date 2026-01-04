"""
AI Financial Advisor for Copilot

Provides AI-powered financial advice using OpenAI GPT-4:
- Natural language Q&A about finances
- Comprehensive financial reports
- Payment plan generation
- Proactive alerts and warnings
"""

import click
import os
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from copilot.db import execute_query
from decimal import Decimal
from datetime import datetime

console = Console()

# Configuration constants
PLACEHOLDER_API_KEY = 'your-api-key-here'
DEFAULT_MODEL = os.getenv('OPENAI_MODEL', 'gpt-4')
DEFAULT_TEMPERATURE = float(os.getenv('OPENAI_TEMPERATURE', '0.7'))
DEFAULT_MAX_TOKENS = int(os.getenv('OPENAI_MAX_TOKENS', '1500'))

# ============================================================================
# HELPER FUNCTIONS - UTILITIES
# ============================================================================

def decimal_to_float(value):
    """Convert Decimal to float for JSON serialization, handling None"""
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    return value

# ============================================================================
# HELPER FUNCTIONS - DATABASE CONTEXT GATHERING
# ============================================================================

def get_financial_context():
    """Gather current financial state from database"""
    context = {
        'tax_outstanding': {},
        'foreclosure_risk': {},
        'total_outstanding': Decimal('0.00'),
        'total_at_risk': Decimal('0.00')
    }
    
    # Get tax outstanding by property
    tax_query = """
        SELECT 
            property_code,
            SUM(balance_due) as total_balance
        FROM acc.property_tax_bill
        WHERE balance_due > 0
        GROUP BY property_code
        ORDER BY property_code
    """
    
    tax_results = execute_query(tax_query)
    for row in tax_results:
        context['tax_outstanding'][row['property_code']] = decimal_to_float(row['total_balance'])
        context['total_outstanding'] += row['total_balance']
    
    # Get foreclosure risk bills (3+ years delinquent)
    foreclosure_query = """
        SELECT 
            property_code,
            tax_year,
            tax_season,
            balance_due,
            years_delinquent
        FROM acc.v_property_tax_foreclosure_risk
        WHERE years_delinquent >= 3
        ORDER BY years_delinquent DESC, tax_year
    """
    
    foreclosure_results = execute_query(foreclosure_query)
    for row in foreclosure_results:
        prop = row['property_code']
        if prop not in context['foreclosure_risk']:
            context['foreclosure_risk'][prop] = {
                'bills': [],
                'total': Decimal('0.00')
            }
        context['foreclosure_risk'][prop]['bills'].append({
            'year': row['tax_year'],
            'season': row['tax_season'],
            'amount': decimal_to_float(row['balance_due']),
            'years_delinquent': int(row['years_delinquent'])
        })
        context['foreclosure_risk'][prop]['total'] += row['balance_due']
        context['total_at_risk'] += row['balance_due']
    
    # Convert remaining Decimals to float for JSON serialization
    context['total_outstanding'] = decimal_to_float(context['total_outstanding'])
    context['total_at_risk'] = decimal_to_float(context['total_at_risk'])
    for prop in context['foreclosure_risk']:
        context['foreclosure_risk'][prop]['total'] = decimal_to_float(context['foreclosure_risk'][prop]['total'])
    
    return context

def get_tax_context():
    """Get detailed tax context"""
    context = {
        'all_bills': [],
        'foreclosure_bills': [],
        'recent_payments': []
    }
    
    # Get all outstanding bills
    bills_query = """
        SELECT 
            property_code,
            tax_year,
            tax_season,
            total_due,
            total_paid,
            balance_due,
            due_date,
            assessed_value,
            taxable_value,
            pre_pct
        FROM acc.property_tax_bill
        WHERE balance_due > 0
        ORDER BY tax_year, property_code, tax_season
    """
    
    bills_results = execute_query(bills_query)
    for row in bills_results:
        context['all_bills'].append({
            'property': row['property_code'],
            'year': row['tax_year'],
            'season': row['tax_season'],
            'total_due': decimal_to_float(row['total_due']),
            'paid': decimal_to_float(row['total_paid']) if row['total_paid'] else 0.0,
            'balance': decimal_to_float(row['balance_due']),
            'due_date': row['due_date'].strftime('%Y-%m-%d') if row['due_date'] else None,
            'assessed_value': decimal_to_float(row['assessed_value']) if row['assessed_value'] else None,
            'pre_pct': decimal_to_float(row['pre_pct']) if row['pre_pct'] else 0.0
        })
    
    # Get foreclosure risk bills
    foreclosure_query = """
        SELECT 
            property_code,
            tax_year,
            tax_season,
            balance_due,
            years_delinquent,
            risk_level
        FROM acc.v_property_tax_foreclosure_risk
        ORDER BY years_delinquent DESC, tax_year
    """
    
    foreclosure_results = execute_query(foreclosure_query)
    for row in foreclosure_results:
        context['foreclosure_bills'].append({
            'property': row['property_code'],
            'year': row['tax_year'],
            'season': row['tax_season'],
            'balance': decimal_to_float(row['balance_due']),
            'years_delinquent': int(row['years_delinquent']),
            'risk': row['risk_level']
        })
    
    # Get recent payment history (last 6 months)
    payments_query = """
        SELECT 
            b.property_code,
            b.tax_year,
            b.tax_season,
            p.payment_date,
            p.amount,
            p.payment_method
        FROM acc.property_tax_payment p
        JOIN acc.property_tax_bill b ON p.tax_bill_id = b.id
        WHERE p.payment_date >= CURRENT_DATE - INTERVAL '6 months'
        ORDER BY p.payment_date DESC
        LIMIT 20
    """
    
    payments_results = execute_query(payments_query)
    for row in payments_results:
        context['recent_payments'].append({
            'property': row['property_code'],
            'year': row['tax_year'],
            'season': row['tax_season'],
            'date': row['payment_date'].strftime('%Y-%m-%d'),
            'amount': decimal_to_float(row['amount']),
            'method': row['payment_method']
        })
    
    return context

def get_cashflow_context():
    """Get cash flow context (if available in database)"""
    # This is a placeholder - would need actual income/expense tables
    # For now, we'll return an empty structure
    context = {
        'monthly_income': {},
        'monthly_expenses': {},
        'note': 'Cash flow data would require additional tables in the database'
    }
    
    return context

def get_openai_client():
    """Get OpenAI client with API key validation"""
    try:
        from openai import OpenAI
    except ImportError:
        console.print("[red]Error: OpenAI library not installed. Install with: pip install 'openai>=1.0.0'[/red]")
        return None
    
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key or api_key == PLACEHOLDER_API_KEY:
        console.print("[red]Error: OPENAI_API_KEY not set in environment[/red]")
        console.print("[yellow]Set your API key in .env file or environment variable[/yellow]")
        console.print("[dim]Get your API key from: https://platform.openai.com/api-keys[/dim]")
        return None
    
    return OpenAI(api_key=api_key)

def create_system_prompt(context_type='general'):
    """Create system prompt for the AI advisor"""
    base_prompt = """You are a financial advisor for a small landlord managing rental properties.

Properties:
- 905brown, 711pine, 819helen: Rental properties (MHB Properties LLC, 0% PRE)
- parnell: Personal residence (100% PRE, lower taxes)

Critical rules:
- Michigan forecloses at 3+ years delinquent - THIS IS URGENT
- Always prioritize paying oldest tax bills first
- Give specific dollar amounts and action items
- Be direct about risks and consequences
- Format responses with clear sections and bullet points
- Use markdown formatting for clarity"""
    
    return base_prompt

def query_openai(client, prompt, context_data, model=None):
    """Query OpenAI with context and return response"""
    if model is None:
        model = DEFAULT_MODEL
    
    try:
        # Build context summary
        context_summary = f"""
Current Financial Context:
- Total outstanding taxes: ${context_data.get('total_outstanding', 0):,.2f}
- Amount at foreclosure risk: ${context_data.get('total_at_risk', 0):,.2f}

Tax Outstanding by Property:
"""
        for prop, amount in context_data.get('tax_outstanding', {}).items():
            context_summary += f"- {prop}: ${amount:,.2f}\n"
        
        if context_data.get('foreclosure_risk'):
            context_summary += "\nFORECLOSURE RISK (3+ years delinquent):\n"
            for prop, data in context_data['foreclosure_risk'].items():
                context_summary += f"- {prop}: ${data['total']:,.2f} ({len(data['bills'])} bills)\n"
                for bill in data['bills']:
                    context_summary += f"  - {bill['year']} {bill['season']}: ${bill['amount']:,.2f} ({bill['years_delinquent']} years overdue)\n"
        
        # Create messages
        messages = [
            {"role": "system", "content": create_system_prompt()},
            {"role": "user", "content": f"{context_summary}\n\nUser Question: {prompt}"}
        ]
        
        # Call OpenAI
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=DEFAULT_TEMPERATURE,
            max_tokens=DEFAULT_MAX_TOKENS
        )
        
        return response.choices[0].message.content
    
    except ImportError:
        console.print("[red]Error: OpenAI library not available[/red]")
        return None
    except Exception as e:
        # Try to provide more specific error messages for common OpenAI errors
        error_msg = str(e).lower()
        if 'rate limit' in error_msg or 'quota' in error_msg:
            console.print("[red]Error: OpenAI rate limit exceeded or quota reached[/red]")
            console.print("[yellow]Please wait a few minutes or upgrade your OpenAI plan[/yellow]")
        elif 'authentication' in error_msg or 'api key' in error_msg:
            console.print("[red]Error: OpenAI API key authentication failed[/red]")
            console.print("[yellow]Check that your API key is valid and hasn't expired[/yellow]")
        elif 'timeout' in error_msg:
            console.print("[red]Error: OpenAI request timed out[/red]")
            console.print("[yellow]Check your internet connection and try again[/yellow]")
        else:
            console.print(f"[red]Error querying OpenAI: {str(e)}[/red]")
        return None

# ============================================================================
# MAIN COMMAND GROUP
# ============================================================================

@click.group()
def advisor():
    """AI-powered financial advisor"""
    pass

# ============================================================================
# ASK COMMAND - Natural Language Q&A
# ============================================================================

@advisor.command('ask')
@click.argument('question', nargs=-1, required=True)
def ask_advisor(question):
    """Ask the AI advisor a financial question
    
    Examples:
        copilot advisor ask "What should I pay first?"
        copilot advisor ask "How much do I need to avoid foreclosure?"
        copilot advisor ask "Which property has the worst tax situation?"
    """
    # Join question parts
    question_text = ' '.join(question)
    
    if not question_text:
        console.print("[red]Please provide a question[/red]")
        return
    
    # Get OpenAI client
    client = get_openai_client()
    if not client:
        return
    
    # Gather context
    console.print("[dim]Gathering financial context...[/dim]")
    context = get_financial_context()
    
    # Query OpenAI
    console.print("[dim]Consulting AI advisor...[/dim]")
    response = query_openai(client, question_text, context)
    
    if not response:
        console.print("[red]Failed to get response from AI advisor[/red]")
        return
    
    # Display response
    console.print()
    console.print(Panel.fit(
        "💡 Financial Advisor",
        style="bold cyan"
    ))
    console.print()
    
    # Render as markdown
    md = Markdown(response)
    console.print(md)
    console.print()

# ============================================================================
# REPORT COMMAND - AI-Generated Reports
# ============================================================================

@advisor.command('report')
@click.option('--type', '-t', 'report_type', 
              type=click.Choice(['weekly', 'monthly', 'tax', 'cashflow', 'summary']),
              default='summary',
              help='Type of report to generate')
def generate_report(report_type):
    """Generate an AI-powered financial report
    
    Report Types:
        summary  - Overall financial health summary (default)
        weekly   - Weekly status with action items
        monthly  - Monthly trends and recommendations
        tax      - Detailed tax situation analysis
        cashflow - Income vs expenses analysis
    """
    # Get OpenAI client
    client = get_openai_client()
    if not client:
        return
    
    # Gather appropriate context
    console.print(f"[dim]Generating {report_type} report...[/dim]")
    
    if report_type == 'tax':
        context = get_tax_context()
        context.update(get_financial_context())
        prompt = "Generate a comprehensive property tax analysis report. Include: 1) Current tax situation by property, 2) Foreclosure risk assessment, 3) Payment priorities, 4) Recent payment activity, 5) Recommended action plan."
    elif report_type == 'cashflow':
        context = get_cashflow_context()
        context.update(get_financial_context())
        prompt = "Generate a cash flow analysis report. Note: Detailed income/expense data is not yet available in the system. Focus on tax obligations as the primary expense category."
    elif report_type == 'weekly':
        context = get_financial_context()
        prompt = "Generate a weekly financial status report with immediate action items for this week. Focus on urgent matters and deadlines."
    elif report_type == 'monthly':
        context = get_financial_context()
        prompt = "Generate a monthly financial summary with trends and strategic recommendations for the upcoming month."
    else:  # summary
        context = get_financial_context()
        prompt = "Generate a comprehensive financial health summary covering: 1) Overall financial position, 2) Critical risks and warnings, 3) Key metrics, 4) Top 3 recommended actions."
    
    # Query OpenAI
    console.print("[dim]Consulting AI advisor...[/dim]")
    response = query_openai(client, prompt, context)
    
    if not response:
        console.print("[red]Failed to generate report[/red]")
        return
    
    # Display response
    console.print()
    console.print(Panel.fit(
        f"📊 {report_type.upper()} FINANCIAL REPORT",
        style="bold cyan"
    ))
    console.print()
    
    # Render as markdown
    md = Markdown(response)
    console.print(md)
    console.print()

# ============================================================================
# PLAN COMMAND - Payment Plan Generator
# ============================================================================

@advisor.command('plan')
@click.option('--months', '-m', default=12, help='Months to pay off')
@click.option('--budget', '-b', type=float, help='Monthly budget for taxes')
@click.option('--property', '-p', 'property_code', help='Specific property')
def payment_plan(months, budget, property_code):
    """Generate a tax payment plan
    
    Examples:
        copilot advisor plan --months 6 --budget 5000
        copilot advisor plan -m 12 -p 905brown
        copilot advisor plan --budget 3000
    """
    # Get OpenAI client
    client = get_openai_client()
    if not client:
        return
    
    # Gather context
    console.print("[dim]Analyzing tax situation...[/dim]")
    context = get_tax_context()
    context.update(get_financial_context())
    
    # Build prompt
    prompt = f"Generate a {months}-month payment plan to become current on property taxes."
    
    if property_code:
        prompt += f" Focus on property: {property_code}."
    
    if budget:
        prompt += f" Monthly budget available: ${budget:,.2f}."
    
    prompt += """
    
    The plan should include:
    1. Priority order (pay foreclosure-risk bills first)
    2. Month-by-month payment schedule
    3. Total amount needed
    4. Monthly payment amounts
    5. When you'll be current
    6. Risk assessment if budget is insufficient
    """
    
    # Query OpenAI
    console.print("[dim]Creating payment plan...[/dim]")
    response = query_openai(client, prompt, context)
    
    if not response:
        console.print("[red]Failed to generate payment plan[/red]")
        return
    
    # Display response
    console.print()
    console.print(Panel.fit(
        "📅 TAX PAYMENT PLAN",
        style="bold cyan"
    ))
    console.print()
    
    # Render as markdown
    md = Markdown(response)
    console.print(md)
    console.print()

# ============================================================================
# ALERT COMMAND - Proactive Alerts
# ============================================================================

@advisor.command('alert')
def show_alerts():
    """Show urgent financial alerts and warnings
    
    Displays proactive alerts about:
    - Foreclosure risks
    - Approaching deadlines
    - Unusual financial patterns
    - Recommended immediate actions
    """
    # Gather context
    console.print("[dim]Checking for alerts...[/dim]")
    context = get_financial_context()
    
    # Display header
    console.print()
    console.print(Panel.fit(
        "🚨 Financial Alerts",
        style="bold red"
    ))
    console.print()
    
    # Critical alerts - Foreclosure risk
    if context['total_at_risk'] > 0:
        console.print(f"[bold red]🔴 CRITICAL: {len([b for prop in context['foreclosure_risk'].values() for b in prop['bills']])} tax bills at foreclosure risk (${context['total_at_risk']:,.2f})[/bold red]")
        for prop, data in context['foreclosure_risk'].items():
            console.print(f"   - {prop}: {len(data['bills'])} bills, ${data['total']:,.2f}")
        console.print()
    
    # Warning - Non-foreclosure outstanding
    non_foreclosure = context['total_outstanding'] - context['total_at_risk']
    if non_foreclosure > 0:
        console.print(f"[bold yellow]🟡 WARNING: ${non_foreclosure:,.2f} in other outstanding taxes[/bold yellow]")
        console.print(f"   - These will become foreclosure risks if not paid")
        console.print()
    
    # Check for properties with manageable situations
    safe_properties = []
    for prop, amount in context['tax_outstanding'].items():
        if prop not in context['foreclosure_risk'] and amount < 1000:
            safe_properties.append(prop)
    
    if safe_properties:
        console.print(f"[bold green]🟢 OK: Properties with low balances: {', '.join(safe_properties)}[/bold green]")
        console.print()
    
    # Get AI-powered insights if OpenAI is available
    client = get_openai_client()
    if client:
        console.print("[dim]Getting AI-powered insights...[/dim]")
        prompt = "Based on the current financial situation, provide a brief alert summary with top 3 immediate action items. Be concise and specific about dollar amounts and deadlines."
        response = query_openai(client, prompt, context)
        
        if response:
            console.print()
            console.print("[bold]💡 AI Recommendations:[/bold]")
            console.print()
            md = Markdown(response)
            console.print(md)
    
    console.print()

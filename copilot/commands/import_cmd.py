"""
Bank import command - Import bank transactions from CSV files
"""
import click
import csv
import hashlib
import os
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.prompt import Confirm
from copilot.db import execute_query, get_connection

console = Console()


def clear_screen():
    """Clear the terminal screen"""
    os.system('clear' if os.name != 'nt' else 'cls')


def compute_file_hash(file_path):
    """Compute SHA256 hash of file content"""
    sha256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b''):
            sha256.update(chunk)
    return sha256.hexdigest()


def parse_amount(amount_str):
    """Parse amount string, handling negative values and currency symbols"""
    if not amount_str:
        return 0.0
    
    # Remove currency symbols and spaces
    amount_str = amount_str.replace('$', '').replace(',', '').strip()
    
    # Handle parentheses for negative amounts
    if amount_str.startswith('(') and amount_str.endswith(')'):
        amount_str = '-' + amount_str[1:-1]
    
    try:
        return float(amount_str)
    except ValueError:
        return 0.0


def parse_date(date_str):
    """Parse date string in various common formats"""
    if not date_str:
        return None
    
    date_formats = [
        '%Y-%m-%d',      # 2024-01-15
        '%m/%d/%Y',      # 01/15/2024
        '%m/%d/%y',      # 01/15/24
        '%d/%m/%Y',      # 15/01/2024
        '%Y/%m/%d',      # 2024/01/15
        '%b %d, %Y',     # Jan 15, 2024
        '%B %d, %Y',     # January 15, 2024
    ]
    
    for fmt in date_formats:
        try:
            return datetime.strptime(date_str.strip(), fmt).date()
        except ValueError:
            continue
    
    console.print(f"[yellow]Warning: Could not parse date '{date_str}'[/yellow]")
    return None


def detect_csv_format(file_path):
    """Detect CSV format and column mappings"""
    with open(file_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames
        
        if not headers:
            return None
        
        # Normalize headers to lowercase for matching
        headers_lower = [h.lower() if h else '' for h in headers]
        
        # Try to detect column mappings
        mapping = {
            'date': None,
            'post_date': None,
            'payee': None,
            'memo': None,
            'amount': None,
            'debit': None,
            'credit': None,
        }
        
        # Common patterns for each field
        date_patterns = ['date', 'transaction date', 'trans date', 'posting date']
        post_date_patterns = ['post date', 'posting date', 'effective date']
        payee_patterns = ['payee', 'description', 'merchant', 'name', 'details']
        memo_patterns = ['memo', 'note', 'description', 'details', 'comment']
        amount_patterns = ['amount', 'transaction amount', 'value']
        debit_patterns = ['debit amount', 'debit', 'withdrawal', 'withdrawals', 'debit_amount', 'payments', 'debits']
        credit_patterns = ['credit amount', 'credit', 'deposit', 'deposits', 'credit_amount', 'credits']
        
        # Match headers to patterns
        # Check debit/credit patterns BEFORE amount patterns to avoid confusion
        for i, header in enumerate(headers_lower):
            if any(pattern in header for pattern in date_patterns) and not mapping['date']:
                mapping['date'] = headers[i]
            elif any(pattern in header for pattern in post_date_patterns) and not mapping['post_date']:
                mapping['post_date'] = headers[i]
            elif any(pattern in header for pattern in payee_patterns) and not mapping['payee']:
                mapping['payee'] = headers[i]
            elif any(pattern in header for pattern in memo_patterns) and not mapping['memo']:
                mapping['memo'] = headers[i]
            elif any(pattern in header for pattern in debit_patterns):
                mapping['debit'] = headers[i]
            elif any(pattern in header for pattern in credit_patterns):
                mapping['credit'] = headers[i]
            elif any(pattern in header for pattern in amount_patterns) and not mapping['amount']:
                mapping['amount'] = headers[i]
        
        # If no payee found but memo exists, use memo as payee
        if not mapping['payee'] and mapping['memo']:
            mapping['payee'] = mapping['memo']
        
        return mapping


def extract_entity(account_code):
    """Extract entity from account code (e.g., 'bgs:checking' -> 'bgs')"""
    if ':' in account_code:
        return account_code.split(':')[0]
    return account_code


def is_duplicate_transaction(account_code, trans_date, amount, description):
    """Check if transaction already exists (fuzzy match on date, amount, description)"""
    result = execute_query("""
        SELECT COUNT(*) as count
        FROM acc.bank_staging
        WHERE source_account_code = %s
          AND normalized_date = %s
          AND amount = %s
          AND LOWER(description) = LOWER(%s)
    """, (account_code, trans_date, amount, description or ''))
    
    return result[0]['count'] > 0


@click.group(name='import')
def import_cmd():
    """Import bank transactions from files"""
    pass


@import_cmd.command('csv')
@click.argument('file', type=click.Path(exists=True))
@click.option('--account', '-a', required=True, help='Bank account code')
@click.option('--dry-run', is_flag=True, help='Preview import without saving')
def import_csv(file, account, dry_run):
    """Import transactions from CSV file.
    
    Usage: copilot import csv <file> --account <account_code> [--dry-run]
    
    Examples:
        copilot import csv ~/Downloads/statement.csv --account bgs:account --dry-run
        copilot import csv ~/Downloads/statement.csv --account bgs:account
    """
    
    clear_screen()
    console.print("\n[bold cyan]═══════════════════════════════════════[/bold cyan]")
    console.print("[bold cyan]   Bank Transaction Import[/bold cyan]")
    console.print("[bold cyan]═══════════════════════════════════════[/bold cyan]\n")
    
    # Verify account exists
    accounts = execute_query("""
        SELECT code, name FROM acc.bank_account WHERE code = %s
    """, (account,))
    
    if not accounts:
        console.print(f"[red]Error: Account '{account}' not found[/red]\n")
        console.print("[bold]Available accounts:[/bold]")
        all_accounts = execute_query("SELECT code, name FROM acc.bank_account ORDER BY code")
        
        # Find max code length for alignment
        max_code_len = max(len(acc['code']) for acc in all_accounts) if all_accounts else 0
        
        for acc in all_accounts:
            console.print(f"  [cyan]{acc['code']:<{max_code_len}}[/cyan]  {acc['name']}")
        
        console.print("\n[bold]Example usage:[/bold]")
        if all_accounts:
            example_account = all_accounts[0]['code']
            console.print(f"  copilot import csv ~/Downloads/statement.csv --account {example_account} --dry-run")
            console.print(f"  copilot import csv ~/Downloads/statement.csv --account {example_account}")
        return
    
    console.print(f"[bold]Account:[/bold] {accounts[0]['name']} ({account})")
    console.print(f"[bold]File:[/bold] {os.path.basename(file)}\n")
    
    # Check if file was already imported
    file_hash = compute_file_hash(file)
    existing_import = execute_query("""
        SELECT * FROM acc.import_log
        WHERE account_code = %s AND file_hash = %s
    """, (account, file_hash))
    
    if existing_import:
        console.print("[yellow]Warning: This file has already been imported![/yellow]")
        console.print(f"Previous import: {existing_import[0]['import_date']}")
        console.print(f"Records imported: {existing_import[0]['records_imported']}")
        
        if not Confirm.ask("\nDo you want to import anyway?", default=False):
            console.print("[yellow]Import cancelled[/yellow]")
            return
    
    # Detect CSV format
    mapping = detect_csv_format(file)
    if not mapping or not mapping['date']:
        console.print("[red]Error: Could not detect CSV format[/red]")
        console.print("Required columns: date and either amount OR (debit and credit)")
        return
    
    console.print("[green]✓ CSV format detected[/green]")
    console.print(f"  Date column: {mapping['date']}")
    if mapping['payee']:
        console.print(f"  Payee column: {mapping['payee']}")
    if mapping['amount']:
        console.print(f"  Amount column: {mapping['amount']}")
    elif mapping['debit'] and mapping['credit']:
        console.print(f"  Debit column: {mapping['debit']}")
        console.print(f"  Credit column: {mapping['credit']}")
    console.print()
    
    # Parse transactions
    transactions = []
    with open(file, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            trans_date = parse_date(row.get(mapping['date'], ''))
            if not trans_date:
                continue
            
            # Calculate amount
            if mapping['amount']:
                amount = parse_amount(row.get(mapping['amount'], '0'))
            elif mapping['debit'] and mapping['credit']:
                debit = parse_amount(row.get(mapping['debit'], '0'))
                credit = parse_amount(row.get(mapping['credit'], '0'))
                # Credits are positive, debits are negative
                amount = credit - debit
            else:
                continue
            
            # Skip zero amounts
            if amount == 0:
                continue
            
            payee = row.get(mapping['payee'], '') if mapping['payee'] else ''
            memo = row.get(mapping['memo'], '') if mapping['memo'] else ''
            post_date = parse_date(row.get(mapping['post_date'], '')) if mapping['post_date'] else None
            
            transactions.append({
                'trans_date': trans_date,
                'post_date': post_date or trans_date,
                'payee': payee,
                'memo': memo,
                'amount': amount
            })
    
    if not transactions:
        console.print("[yellow]No valid transactions found in file[/yellow]")
        return
    
    # Extract entity from account code
    entity = extract_entity(account)
    console.print(f"[bold]Entity:[/bold] {entity}\n")
    
    # Show preview
    console.print(f"[bold]Found {len(transactions)} transactions[/bold]\n")
    
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Date", style="cyan")
    table.add_column("Description", style="white")
    table.add_column("Amount", justify="right", style="green")
    table.add_column("Status", style="yellow")
    
    imported_count = 0
    skipped_count = 0
    date_range_start = None
    date_range_end = None
    
    for trans in transactions[:10]:  # Preview first 10
        is_dup = is_duplicate_transaction(account, trans['trans_date'], trans['amount'], trans['payee'])
        status = "[red]Duplicate[/red]" if is_dup else "[green]New[/green]"
        
        if not is_dup:
            imported_count += 1
        else:
            skipped_count += 1
        
        amount_str = f"${trans['amount']:,.2f}" if trans['amount'] >= 0 else f"-${abs(trans['amount']):,.2f}"
        table.add_row(
            trans['trans_date'].strftime('%Y-%m-%d'),
            trans['payee'][:40],
            amount_str,
            status
        )
    
    if len(transactions) > 10:
        table.add_row("[dim]...", "[dim]...", "[dim]...", f"[dim]{len(transactions) - 10} more...")
    
    console.print(table)
    console.print()
    
    # Count actual new vs duplicates
    imported_count = 0
    skipped_count = 0
    for trans in transactions:
        if is_duplicate_transaction(account, trans['trans_date'], trans['amount'], trans['payee']):
            skipped_count += 1
        else:
            imported_count += 1
            if not date_range_start or trans['trans_date'] < date_range_start:
                date_range_start = trans['trans_date']
            if not date_range_end or trans['trans_date'] > date_range_end:
                date_range_end = trans['trans_date']
    
    console.print(f"[bold]Summary:[/bold]")
    console.print(f"  New transactions: [green]{imported_count}[/green]")
    console.print(f"  Duplicates (skipped): [yellow]{skipped_count}[/yellow]\n")
    
    if dry_run:
        # Calculate detailed statistics for dry-run
        new_transactions = [t for t in transactions if not is_duplicate_transaction(account, t['trans_date'], t['amount'], t['payee'])]
        
        if new_transactions:
            # Date range
            dates = [t['trans_date'] for t in new_transactions]
            earliest_date = min(dates)
            latest_date = max(dates)
            span_days = (latest_date - earliest_date).days
            
            # Separate debits and credits
            debits = [t['amount'] for t in new_transactions if t['amount'] < 0]
            credits = [t['amount'] for t in new_transactions if t['amount'] > 0]
            
            # Calculate net flow
            net_flow = sum(t['amount'] for t in new_transactions)
            
            console.print("[bold cyan]═══════════════════════════════════════[/bold cyan]")
            console.print("[bold cyan]   Detailed Statistics[/bold cyan]")
            console.print("[bold cyan]═══════════════════════════════════════[/bold cyan]\n")
            
            # Date Range
            console.print("[bold]Date Range:[/bold]")
            console.print(f"  From: {earliest_date.strftime('%Y-%m-%d')}")
            console.print(f"  To:   {latest_date.strftime('%Y-%m-%d')}")
            console.print(f"  Span: {span_days} days\n")
            
            # Transaction Counts
            console.print("[bold]Transaction Counts:[/bold]")
            console.print(f"  Total:   {len(new_transactions)}")
            console.print(f"  Debits:  {len(debits)}")
            console.print(f"  Credits: {len(credits)}\n")
            
            # Debits (Outflows)
            if debits:
                console.print("[bold]Debits (Outflows):[/bold]")
                console.print(f"  Total:    [red]-${abs(sum(debits)):,.2f}[/red]")
                console.print(f"  Largest:  [red]-${abs(min(debits)):,.2f}[/red]")
                console.print(f"  Smallest: [red]-${abs(max(debits)):,.2f}[/red]")
                console.print(f"  Average:  [red]-${abs(sum(debits) / len(debits)):,.2f}[/red]\n")
            
            # Credits (Inflows)
            if credits:
                console.print("[bold]Credits (Inflows):[/bold]")
                console.print(f"  Total:    [green]${sum(credits):,.2f}[/green]")
                console.print(f"  Largest:  [green]${max(credits):,.2f}[/green]")
                console.print(f"  Smallest: [green]${min(credits):,.2f}[/green]")
                console.print(f"  Average:  [green]${sum(credits) / len(credits):,.2f}[/green]\n")
            
            # Net Flow
            net_color = "green" if net_flow >= 0 else "red"
            net_prefix = "+" if net_flow >= 0 else "-"
            console.print("[bold]Net Flow:[/bold]")
            console.print(f"  [{net_color}]{net_prefix}${abs(net_flow):,.2f}[/{net_color}]\n")
        
        console.print("[yellow]Dry run - no changes made[/yellow]")
        return
    
    if imported_count == 0:
        console.print("[yellow]No new transactions to import[/yellow]")
        return
    
    # Confirm import
    if not Confirm.ask(f"Import {imported_count} transactions?", default=True):
        console.print("[yellow]Import cancelled[/yellow]")
        return
    
    # Import transactions
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # Extract entity once
            entity = extract_entity(account)
            
            for trans in transactions:
                if is_duplicate_transaction(account, trans['trans_date'], trans['amount'], trans['payee']):
                    continue
                
                cur.execute("""
                    INSERT INTO acc.bank_staging
                        (source_account_code, normalized_date, post_date, description, memo, 
                         amount, entity, source)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (account, trans['trans_date'], trans['post_date'], 
                      trans['payee'], trans['memo'], trans['amount'], entity, 'csv_import'))
            
            # Log the import
            cur.execute("""
                INSERT INTO acc.import_log
                    (account_code, file_name, file_hash, records_imported, 
                     records_skipped, date_range_start, date_range_end)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (account, os.path.basename(file), file_hash, imported_count,
                  skipped_count, date_range_start, date_range_end))
            
            conn.commit()
            console.print(f"\n[bold green]✓ Successfully imported {imported_count} transactions![/bold green]\n")
    except Exception as e:
        conn.rollback()
        console.print(f"[red]Error importing transactions: {e}[/red]")
    finally:
        conn.close()


@import_cmd.command('list')
@click.option('--account', '-a', help='Filter by account code')
def import_list(account):
    """List import history"""
    
    clear_screen()
    console.print("\n[bold cyan]═══════════════════════════════════════[/bold cyan]")
    console.print("[bold cyan]   Import History[/bold cyan]")
    console.print("[bold cyan]═══════════════════════════════════════[/bold cyan]\n")
    
    if account:
        query = """
            SELECT 
                il.id,
                il.account_code,
                ba.name as account_name,
                il.import_date,
                il.file_name,
                il.records_imported,
                il.records_skipped,
                il.date_range_start,
                il.date_range_end
            FROM acc.import_log il
            JOIN acc.bank_account ba ON ba.code = il.account_code
            WHERE il.account_code = %s
            ORDER BY il.import_date DESC
            LIMIT 50
        """
        imports = execute_query(query, (account,))
    else:
        query = """
            SELECT 
                il.id,
                il.account_code,
                ba.name as account_name,
                il.import_date,
                il.file_name,
                il.records_imported,
                il.records_skipped,
                il.date_range_start,
                il.date_range_end
            FROM acc.import_log il
            JOIN acc.bank_account ba ON ba.code = il.account_code
            ORDER BY il.import_date DESC
            LIMIT 50
        """
        imports = execute_query(query)
    
    if not imports:
        console.print("[yellow]No imports found[/yellow]")
        return
    
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("ID", style="cyan", justify="right")
    table.add_column("Account", style="white")
    table.add_column("Date", style="cyan")
    table.add_column("File", style="white")
    table.add_column("Imported", justify="right", style="green")
    table.add_column("Skipped", justify="right", style="yellow")
    table.add_column("Date Range", style="white")
    
    for imp in imports:
        date_range = ""
        if imp['date_range_start'] and imp['date_range_end']:
            date_range = f"{imp['date_range_start']} to {imp['date_range_end']}"
        
        table.add_row(
            str(imp['id']),
            f"{imp['account_code']} ({imp['account_name']})",
            imp['import_date'].strftime('%Y-%m-%d %H:%M'),
            imp['file_name'],
            str(imp['records_imported']),
            str(imp['records_skipped']),
            date_range
        )
    
    console.print(table)
    console.print()


@import_cmd.command('status')
@click.option('--account', '-a', help='Filter by account code')
def import_status(account):
    """Show matched and unmatched transaction counts"""
    
    clear_screen()
    console.print("\n[bold cyan]═══════════════════════════════════════[/bold cyan]")
    console.print("[bold cyan]   Bank Staging Status[/bold cyan]")
    console.print("[bold cyan]═══════════════════════════════════════[/bold cyan]\n")
    
    # Get summary counts by match status
    if account:
        summary_query = """
            SELECT 
                CASE 
                    WHEN match_method = 'pattern' THEN 'Pattern Matched'
                    WHEN match_method = 'manual' THEN 'Manually Assigned'
                    WHEN gl_account_code = 'TODO' THEN 'Unmatched (TODO)'
                    ELSE 'Other'
                END as status,
                COUNT(*) as count,
                SUM(amount) as total_amount
            FROM acc.bank_staging
            WHERE source_account_code = %s
            GROUP BY 1
            ORDER BY 
                CASE 
                    WHEN gl_account_code = 'TODO' THEN 1
                    WHEN match_method = 'pattern' THEN 2
                    WHEN match_method = 'manual' THEN 3
                    ELSE 4
                END
        """
        summary = execute_query(summary_query, (account,))
    else:
        summary_query = """
            SELECT 
                CASE 
                    WHEN match_method = 'pattern' THEN 'Pattern Matched'
                    WHEN match_method = 'manual' THEN 'Manually Assigned'
                    WHEN gl_account_code = 'TODO' THEN 'Unmatched (TODO)'
                    ELSE 'Other'
                END as status,
                COUNT(*) as count,
                SUM(amount) as total_amount
            FROM acc.bank_staging
            GROUP BY 1
            ORDER BY 
                CASE 
                    WHEN gl_account_code = 'TODO' THEN 1
                    WHEN match_method = 'pattern' THEN 2
                    WHEN match_method = 'manual' THEN 3
                    ELSE 4
                END
        """
        summary = execute_query(summary_query)
    
    if not summary:
        console.print("[yellow]No transactions found in staging[/yellow]")
        return
    
    # Display summary table
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Status", style="white")
    table.add_column("Count", justify="right", style="cyan")
    table.add_column("Total Amount", justify="right", style="green")
    
    total_count = 0
    total_amount = 0.0
    
    for row in summary:
        status_style = "red" if row['status'] == 'Unmatched (TODO)' else "white"
        amount_str = f"${row['total_amount']:,.2f}" if row['total_amount'] >= 0 else f"-${abs(row['total_amount']):,.2f}"
        table.add_row(
            f"[{status_style}]{row['status']}[/{status_style}]",
            str(row['count']),
            amount_str
        )
        total_count += row['count']
        total_amount += row['total_amount'] or 0.0
    
    console.print(table)
    console.print()
    
    # Show overall totals
    total_amount_str = f"${total_amount:,.2f}" if total_amount >= 0 else f"-${abs(total_amount):,.2f}"
    console.print(f"[bold]Total Transactions:[/bold] {total_count}")
    console.print(f"[bold]Total Amount:[/bold] {total_amount_str}\n")
    
    # Show unmatched transactions if any
    if account:
        unmatched_query = """
            SELECT 
                id,
                source_account_code,
                normalized_date,
                description,
                amount,
                memo
            FROM acc.bank_staging
            WHERE source_account_code = %s
              AND gl_account_code = 'TODO'
            ORDER BY normalized_date DESC
            LIMIT 20
        """
        unmatched = execute_query(unmatched_query, (account,))
    else:
        unmatched_query = """
            SELECT 
                id,
                source_account_code,
                normalized_date,
                description,
                amount,
                memo
            FROM acc.bank_staging
            WHERE gl_account_code = 'TODO'
            ORDER BY normalized_date DESC
            LIMIT 20
        """
        unmatched = execute_query(unmatched_query)
    
    if unmatched:
        console.print(f"[bold yellow]Unmatched Transactions (showing up to 20):[/bold yellow]\n")
        
        detail_table = Table(show_header=True, header_style="bold magenta")
        detail_table.add_column("ID", style="cyan", justify="right")
        detail_table.add_column("Account", style="white")
        detail_table.add_column("Date", style="white")
        detail_table.add_column("Description", style="white")
        detail_table.add_column("Amount", justify="right", style="green")
        
        for trans in unmatched:
            amount_str = f"${trans['amount']:,.2f}" if trans['amount'] >= 0 else f"-${abs(trans['amount']):,.2f}"
            detail_table.add_row(
                str(trans['id']),
                trans['source_account_code'],
                trans['normalized_date'].strftime('%Y-%m-%d'),
                (trans['description'] or '')[:40],
                amount_str
            )
        
        console.print(detail_table)
        console.print()

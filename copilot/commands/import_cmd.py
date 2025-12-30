"""
Bank import command - Import bank transactions from CSV files
"""
import click
import csv
import glob
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


def is_check_transaction(memo, column_name):
    """
    Determine if a transaction is a check based on memo content.
    
    Args:
        memo: The transaction memo/description
        column_name: The name of the column that contained the potential check number
        
    Returns:
        True if this appears to be a check transaction
    """
    if not memo:
        # If column was explicitly named as check number, trust it
        if column_name:
            col_lower = column_name.lower()
            return any(p in col_lower for p in ['check number', 'check_number', 'check #', 'check no', 'chk'])
        return False
    
    memo_upper = memo.upper()
    
    # Explicit check indicators
    if 'SUBSTITUTE CHECK' in memo_upper:
        return True
    
    # "CHECK" as a word but not "CHECKING"
    if 'CHECKING' in memo_upper:
        return False
        
    # Check for "CHECK" as a standalone word
    if ' CHECK ' in f' {memo_upper} ':
        return True
    if memo_upper.endswith(' CHECK'):
        return True
    if memo_upper.startswith('CHECK '):
        return True
        
    return False


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
            'check_number': None,
        }
        
        # Common patterns for each field
        date_patterns = ['date', 'transaction date', 'trans date', 'posting date']
        post_date_patterns = ['post date', 'posting date', 'effective date']
        payee_patterns = ['payee', 'description', 'merchant', 'name', 'details']
        memo_patterns = ['memo', 'note', 'description', 'details', 'comment']
        amount_patterns = ['amount', 'transaction amount', 'value']
        debit_patterns = ['debit amount', 'debit_amount', 'debit', 'withdrawal', 'payments']
        credit_patterns = ['credit amount', 'credit_amount', 'credit', 'deposit', 'deposits']
        check_patterns = ['check number', 'check_number', 'check #', 'check no', 'check', 'chk', 'chk #', 'chk no', 'reference', 'ref']
        
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
            elif any(pattern in header for pattern in debit_patterns) and not mapping['debit']:
                mapping['debit'] = headers[i]
            elif any(pattern in header for pattern in credit_patterns) and not mapping['credit']:
                mapping['credit'] = headers[i]
            elif any(pattern in header for pattern in amount_patterns) and not mapping['amount']:
                mapping['amount'] = headers[i]
            elif any(pattern in header for pattern in check_patterns) and not mapping['check_number']:
                mapping['check_number'] = headers[i]
        
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


def show_import_help():
    """Show comprehensive import help with accounts and CSV files"""
    console.print("\n[bold cyan]═══════════════════════════════════════════════════════════════[/bold cyan]")
    console.print("[bold cyan]   Bank Transaction Import[/bold cyan]")
    console.print("[bold cyan]═══════════════════════════════════════════════════════════════[/bold cyan]\n")
    
    # Syntax
    console.print("[bold]SYNTAX:[/bold]")
    console.print("  copilot import csv <file> --account <code> --dry-run\n")
    
    # Available accounts
    console.print("[bold]AVAILABLE ACCOUNTS:[/bold]")
    try:
        accounts = execute_query("""
            SELECT code, name, institution 
            FROM acc.bank_account 
            WHERE status = 'active'
            ORDER BY code
        """)
        
        if accounts:
            # Find max code length for alignment
            max_code_len = max(len(acc['code']) for acc in accounts)
            
            for acc in accounts:
                institution_str = f" ({acc['institution']})" if acc.get('institution') else ""
                console.print(f"  [cyan]{acc['code']:<{max_code_len}}[/cyan]  {acc['name']}{institution_str}")
        else:
            console.print("  [yellow]No active accounts found[/yellow]")
    except Exception as e:
        console.print(f"  [yellow]Could not fetch accounts: {e}[/yellow]")
    
    console.print()
    
    # CSV files in current directory
    console.print("[bold]CSV FILES IN CURRENT DIRECTORY:[/bold]")
    csv_files = sorted(glob.glob("*.csv"))
    if csv_files:
        for csv_file in csv_files:
            try:
                file_size = os.path.getsize(csv_file)
                size_kb = file_size / 1024
                console.print(f"  [green]{csv_file}[/green] ({size_kb:.1f} KB)")
            except OSError:
                # File might have been deleted between glob and getsize
                console.print(f"  [green]{csv_file}[/green]")
    else:
        console.print("  [yellow]No CSV files found in current directory[/yellow]")
    
    console.print()
    
    # Workflow
    console.print("[bold]WORKFLOW:[/bold]")
    console.print("  1. Check available accounts above")
    console.print("  2. Preview import: copilot import csv <file> --account <code> --dry-run")
    console.print("  3. Review the transaction preview")
    console.print("  4. Run without --dry-run to import: copilot import csv <file> --account <code>")
    console.print("  5. Run allocation wizard: copilot allocate wizard --period <year>\n")


@click.group(name='import', invoke_without_command=True)
@click.pass_context
def import_cmd(ctx):
    """Import bank transactions from files"""
    if ctx.invoked_subcommand is None:
        # Show comprehensive help when no subcommand given
        show_import_help()


@import_cmd.command('csv')
@click.argument('file', type=click.Path(exists=True))
@click.option('--account', '-a', required=True, help='Account code (e.g., bgs:checking)')
@click.option('--dry-run', is_flag=True, help='Preview without importing')
def import_csv(file, account, dry_run):
    """Import transactions from CSV file.
    
    SYNTAX:
      copilot import csv <file> --account <code> --dry-run
      copilot import csv <file> --account <code>
    
    WORKFLOW:
      1. Check available accounts: copilot import
      2. Preview import: copilot import csv statement.csv --account bgs:checking --dry-run
      3. Review the transaction preview
      4. Import: copilot import csv statement.csv --account bgs:checking
      5. Run allocation wizard: copilot allocate wizard --period <year>
    """
    
    clear_screen()
    console.print("\n[bold cyan]═══════════════════════════════════════[/bold cyan]")
    console.print("[bold cyan]   Bank Transaction Import[/bold cyan]")
    console.print("[bold cyan]═══════════════════════════════════════[/bold cyan]\n")
    
    # Verify account exists
    accounts = execute_query("""
        SELECT code, name, institution FROM acc.bank_account WHERE code = %s
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
    
    # Capture institution from account for later use
    institution = accounts[0].get('institution')
    
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
        console.print(f"  Description column: {mapping['payee']}")
    if mapping['amount']:
        console.print(f"  Amount column: {mapping['amount']}")
    elif mapping['debit'] and mapping['credit']:
        console.print(f"  Debit column: {mapping['debit']}")
        console.print(f"  Credit column: {mapping['credit']}")
    if mapping['check_number']:
        console.print(f"  [cyan]Check Number:[/cyan] {mapping['check_number']}")
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
            
            # Smart check number detection
            raw_check_num = row.get(mapping['check_number'], '').strip() if mapping['check_number'] else None
            
            # Determine if this is actually a check transaction
            check_number = None
            if raw_check_num and raw_check_num != '0':
                # Check if memo indicates this is a check transaction
                if is_check_transaction(memo, mapping.get('check_number')):
                    check_number = raw_check_num
                # If column was explicitly named as check number, trust it
                elif mapping.get('check_number') and any(
                    pattern in mapping['check_number'].lower() 
                    for pattern in ['check number', 'check_number', 'check #', 'check no', 'chk']
                ):
                    check_number = raw_check_num
            
            transactions.append({
                'trans_date': trans_date,
                'post_date': post_date or trans_date,
                'payee': payee,
                'memo': memo,
                'amount': amount,
                'check_number': check_number
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
    table.add_column("Check #", style="cyan")
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
            trans['check_number'] or '-',
            status
        )
    
    if len(transactions) > 10:
        table.add_row("[dim]...", "[dim]...", "[dim]...", "[dim]...", f"[dim]{len(transactions) - 10} more...")
    
    console.print(table)
    console.print()
    
    # Count actual new vs duplicates and calculate statistics
    imported_count = 0
    skipped_count = 0
    new_transactions = []
    for trans in transactions:
        if is_duplicate_transaction(account, trans['trans_date'], trans['amount'], trans['payee']):
            skipped_count += 1
        else:
            imported_count += 1
            new_transactions.append(trans)
            if not date_range_start or trans['trans_date'] < date_range_start:
                date_range_start = trans['trans_date']
            if not date_range_end or trans['trans_date'] > date_range_end:
                date_range_end = trans['trans_date']
    
    # Calculate detailed statistics for new transactions
    if new_transactions:
        amounts = [t['amount'] for t in new_transactions]
        debits = [a for a in amounts if a < 0]
        credits = [a for a in amounts if a > 0]
        
        # Calculate date span using already-calculated date_range_start and date_range_end
        date_span_days = (date_range_end - date_range_start).days if date_range_start and date_range_end else 0
        
        total_count = len(new_transactions)
        debit_count = len(debits)
        credit_count = len(credits)
        
        debit_total = abs(sum(debits)) if debits else 0
        debit_largest = abs(min(debits)) if debits else 0
        debit_smallest = abs(max(debits)) if debits else 0
        debit_average = debit_total / debit_count if debit_count > 0 else 0
        
        credit_total = sum(credits) if credits else 0
        credit_largest = max(credits) if credits else 0
        credit_smallest = min(credits) if credits else 0
        credit_average = credit_total / credit_count if credit_count > 0 else 0
        
        net_flow = sum(amounts)
    else:
        # Default values if no new transactions
        date_span_days = 0
        total_count = 0
        debit_count = 0
        credit_count = 0
        debit_total = 0
        debit_largest = 0
        debit_smallest = 0
        debit_average = 0
        credit_total = 0
        credit_largest = 0
        credit_smallest = 0
        credit_average = 0
        net_flow = 0
    
    console.print(f"[bold]Summary:[/bold]")
    console.print(f"  New transactions: [green]{imported_count}[/green]")
    console.print(f"  Duplicates (skipped): [yellow]{skipped_count}[/yellow]\n")
    
    if dry_run:
        # Display detailed statistics for dry-run (already calculated above)
        if new_transactions:
            console.print("[bold cyan]═══════════════════════════════════════[/bold cyan]")
            console.print("[bold cyan]   Detailed Statistics[/bold cyan]")
            console.print("[bold cyan]═══════════════════════════════════════[/bold cyan]\n")
            
            # Date Range
            console.print("[bold]Date Range:[/bold]")
            console.print(f"  From: {date_range_start.strftime('%Y-%m-%d')}")
            console.print(f"  To:   {date_range_end.strftime('%Y-%m-%d')}")
            console.print(f"  Span: {date_span_days} days\n")
            
            # Transaction Counts
            console.print("[bold]Transaction Counts:[/bold]")
            console.print(f"  Total:   {total_count}")
            console.print(f"  Debits:  {debit_count}")
            console.print(f"  Credits: {credit_count}\n")
            
            # Debits (Outflows)
            if debit_count > 0:
                console.print("[bold]Debits (Outflows):[/bold]")
                console.print(f"  Total:    [red]-${debit_total:,.2f}[/red]")
                console.print(f"  Largest:  [red]-${debit_largest:,.2f}[/red]")
                console.print(f"  Smallest: [red]-${debit_smallest:,.2f}[/red]")
                console.print(f"  Average:  [red]-${debit_average:,.2f}[/red]\n")
            
            # Credits (Inflows)
            if credit_count > 0:
                console.print("[bold]Credits (Inflows):[/bold]")
                console.print(f"  Total:    [green]${credit_total:,.2f}[/green]")
                console.print(f"  Largest:  [green]${credit_largest:,.2f}[/green]")
                console.print(f"  Smallest: [green]${credit_smallest:,.2f}[/green]")
                console.print(f"  Average:  [green]${credit_average:,.2f}[/green]\n")
            
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
                         amount, entity, source, check_number, source_institution)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (account, trans['trans_date'], trans['post_date'], 
                      trans['payee'], trans['memo'], trans['amount'], entity, 'csv_import',
                      trans['check_number'], institution))
            
            # Log the import
            cur.execute("""
                INSERT INTO acc.import_log
                    (account_code, file_name, file_hash, records_imported, records_skipped,
                     date_range_start, date_range_end, date_span_days,
                     total_count, debit_count, credit_count,
                     debit_total, debit_largest, debit_smallest, debit_average,
                     credit_total, credit_largest, credit_smallest, credit_average,
                     net_flow)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (account, os.path.basename(file), file_hash, imported_count, skipped_count,
                  date_range_start, date_range_end, date_span_days,
                  total_count, debit_count, credit_count,
                  debit_total, debit_largest, debit_smallest, debit_average,
                  credit_total, credit_largest, credit_smallest, credit_average,
                  net_flow))
            
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

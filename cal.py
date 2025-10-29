import typer
from rich.console import Console, Group
from rich.table import Table
import pathlib
import sqlite3
import configparser
from datetime import datetime
from typing import Union

from rich.panel import Panel
from rich.progress_bar import ProgressBar
from datetime import date, timedelta


# --- Imports for single-character input ---
import platform
if platform.system() == "Windows":
    import msvcrt


# --- Configuration ---
APP_DIR = pathlib.Path(__file__).parent
CONFIG_FILE = APP_DIR / "config.ini"
DATABASE_FILE = APP_DIR / "database.db"

# --- Typer App Initialization ---
app = typer.Typer()
log_app = typer.Typer()
app.add_typer(log_app, name="log")

console = Console()

# --- Helper Functions ---

def _get_char():
    """Gets a single character from stdin, cross-platform."""
    if platform.system() == "Windows":
        # Returns a byte string, so decode it
        return msvcrt.getch().decode('utf-8', errors='ignore')
    else:
        import sys
        import tty
        import termios
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(sys.stdin.fileno())
            ch = sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        return ch

def get_config():
    """Reads and returns the configuration."""
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE)
    return config

def check_initialized():
    """Check if the app has been initialized."""
    if not CONFIG_FILE.exists() or not DATABASE_FILE.exists():
        console.print("[bold red]Error: Application not initialized.[/bold red]")
        console.print("Please run [cyan]cal init[/cyan] first.")
        raise typer.Exit()


# --- Database Functions ---
def get_db_connection():
    """Establishes a connection to the SQLite database."""
    conn = sqlite3.connect(DATABASE_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def create_db_tables():
    """Creates the necessary database tables if they don't exist."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS food_entries (
            id INTEGER PRIMARY KEY,
            timestamp TEXT NOT NULL,
            calories INTEGER NOT NULL,
            description TEXT
        );
        CREATE TABLE IF NOT EXISTS weight_entries (
            id INTEGER PRIMARY KEY,
            timestamp TEXT NOT NULL,
            weight REAL NOT NULL
        );
        CREATE TABLE IF NOT EXISTS waist_entries (
            id INTEGER PRIMARY KEY,
            timestamp TEXT NOT NULL,
            waist_length REAL NOT NULL
        );
    """)
    conn.commit()
    conn.close()


# --- Internal Database Logic ---
def _add_food_entry(timestamp: str, calories: int, description: Union[str, None]):
    """Adds a food entry to the database with a specific timestamp."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO food_entries (timestamp, calories, description) VALUES (?, ?, ?)",
        (timestamp, calories, description)
    )
    conn.commit()
    conn.close()

def _add_weight_entry(timestamp: str, weight: float):
    """Adds a weight entry to the database with a specific timestamp."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO weight_entries (timestamp, weight) VALUES (?, ?)",
        (timestamp, weight)
    )
    conn.commit()
    conn.close()

def _add_waist_entry(timestamp: str, waist_length: float):
    """Adds a waist entry to the database with a specific timestamp."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO waist_entries (timestamp, waist_length) VALUES (?, ?)",
        (timestamp, waist_length)
    )
    conn.commit()
    conn.close()


def _delete_entry(entry_type: str, entry_id: int):
    """Deletes an entry from the database."""
    table_name = "food_entries" if entry_type == "food" else "weight_entries"
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(f"DELETE FROM {table_name} WHERE id = ?", (entry_id,))
    conn.commit()
    conn.close()


def _edit_food_entry(entry_id: int, calories: int, description: Union[str, None], timestamp: Union[str, None] = None):
    """Updates a food entry in the database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    if timestamp:
        cursor.execute(
            "UPDATE food_entries SET calories = ?, description = ?, timestamp = ? WHERE id = ?",
            (calories, description, timestamp, entry_id)
        )
    else:
        cursor.execute(
            "UPDATE food_entries SET calories = ?, description = ? WHERE id = ?",
            (calories, description, entry_id)
        )
    conn.commit()
    conn.close()


def _edit_weight_entry(entry_id: int, weight: float):
    """Updates a weight entry in the database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE weight_entries SET weight = ? WHERE id = ?",
        (weight, entry_id)
    )
    conn.commit()
    conn.close()


# --- CLI Commands ---

@app.command()
def init():
    """Initializes the calorie tracking application."""
    if CONFIG_FILE.exists() or DATABASE_FILE.exists():
        console.print("[yellow]Application has already been initialized.[/yellow]")
        raise typer.Exit()

    # Create config file
    config = configparser.ConfigParser()
    tdee = typer.prompt("What is your Total Daily Energy Expenditure (TDEE) in calories?")
    config["USER"] = {"TDEE": tdee}
    with open(CONFIG_FILE, "w") as configfile:
        config.write(configfile)

    # Create database and tables
    create_db_tables()

    console.print(f"[green]Initialization complete![/green]")
    console.print(f"Config file created at: {CONFIG_FILE}")
    console.print(f"Database created at: {DATABASE_FILE}")


def _parse_time(time_str: str) -> Union[datetime.time, None]:
    """Parses a time string in HH:MM or H:MM format."""
    try:
        # Handles HH:MM, H:MM, HH:MM:SS, etc.
        return datetime.strptime(time_str, "%H:%M").time()
    except ValueError:
        return None

@log_app.command("food")
def log_food(
    calories: int = typer.Argument(..., help="The number of calories to log."),
    description: str = typer.Option(None, "--desc", "-d", help="An optional description of the food."),
    time_str: str = typer.Option(None, "--time", "-t", help="Time of the meal in HH:MM format. Defaults to now.")
):
    """Logs a food entry for a specific time."""
    check_initialized()
    
    now = datetime.now()
    meal_time = now.time()

    if time_str:
        parsed_time = _parse_time(time_str)
        if parsed_time:
            meal_time = parsed_time
        else:
            console.print(f"[bold red]Invalid time format: '{time_str}'. Please use HH:MM.[/bold red]")
            raise typer.Exit()

    timestamp = datetime.combine(now.date(), meal_time).isoformat()
    _add_food_entry(timestamp, calories, description)
    console.print(f"[green]Logged {calories} calories at {meal_time.strftime('%H:%M')}.[/green]")

@log_app.command("weight")
def log_weight(
    weight: float = typer.Argument(..., help="Your current weight.")
):
    """Logs a weight entry for the current time."""
    check_initialized()
    timestamp = datetime.now().isoformat()
    _add_weight_entry(timestamp, weight)
    console.print(f"[green]Logged weight: {weight}.[/green]")

@log_app.command("waist")
def log_waist(
    waist_length: float = typer.Argument(..., help="Your current waist length in inches.")
):
    """Logs a waist length entry for the current time."""
    check_initialized()
    timestamp = datetime.now().isoformat()
    _add_waist_entry(timestamp, waist_length)
    console.print(f"[green]Logged waist length: {waist_length} inches.[/green]")


@app.command("lf", help="Shortcut for 'log food'.")
def lf(
    calories: int = typer.Argument(..., help="The number of calories to log."),
    description: str = typer.Option(None, "--desc", "-d", help="An optional description of the food."),
    time_str: str = typer.Option(None, "--time", "-t", help="Time of the meal in HH:MM format. Defaults to now.")
):
    """Shortcut to log a food entry for a specific time."""
    check_initialized()
    
    now = datetime.now()
    meal_time = now.time()

    if time_str:
        parsed_time = _parse_time(time_str)
        if parsed_time:
            meal_time = parsed_time
        else:
            console.print(f"[bold red]Invalid time format: '{time_str}'. Please use HH:MM.[/bold red]")
            raise typer.Exit()

    timestamp = datetime.combine(now.date(), meal_time).isoformat()
    _add_food_entry(timestamp, calories, description)
    console.print(f"[green]Logged {calories} calories at {meal_time.strftime('%H:%M')}.[/green]")


@app.command("lw", help="Shortcut for 'log weight'.")
def lw(
    weight: float = typer.Argument(..., help="Your current weight.")
):
    """Shortcut to log a weight entry for the current time."""
    check_initialized()
    timestamp = datetime.now().isoformat()
    _add_weight_entry(timestamp, weight)
    console.print(f"[green]Logged weight: {weight}.[/green]")

@app.command("lwl", help="Shortcut for 'log waist'.")
def lwl(
    waist_length: float = typer.Argument(..., help="Your current waist length in inches.")
):
    """Shortcut to log a waist length entry for the current time."""
    check_initialized()
    timestamp = datetime.now().isoformat()
    _add_waist_entry(timestamp, waist_length)
    console.print(f"[green]Logged waist length: {waist_length} inches.[/green]")

@app.command()
def config(tdee: int = typer.Option(None, "--tdee", help="Update your Total Daily Energy Expenditure (TDEE).")):
    """View or update your configuration."""
    check_initialized()
    conf = get_config()
    if tdee:
        conf["USER"]["TDEE"] = str(tdee)
        with open(CONFIG_FILE, "w") as configfile:
            conf.write(configfile)
        console.print(f"[green]TDEE updated to {tdee}[/green]")
    else:
        current_tdee = conf["USER"]["TDEE"]
        console.print(f"Current TDEE: [bold cyan]{current_tdee}[/bold cyan]")

@app.command()
def status():
    """Displays a status summary for the current day."""
    check_initialized()
    config = get_config()
    tdee = int(config["USER"]["TDEE"])

    conn = get_db_connection()
    cursor = conn.cursor()

    # Get today's calories
    today_str = date.today().isoformat()
    cursor.execute(
        "SELECT SUM(calories) FROM food_entries WHERE date(timestamp) = ?", (today_str,)
    )
    calories_today = cursor.fetchone()[0] or 0

    # Get latest weight
    cursor.execute("SELECT weight FROM weight_entries ORDER BY timestamp DESC LIMIT 1")
    latest_weight_row = cursor.fetchone()
    latest_weight = f"{latest_weight_row[0]}" if latest_weight_row else "Not Available"

    # Get 7-day waist average
    seven_days_ago = (date.today() - timedelta(days=7)).isoformat()
    cursor.execute(
        "SELECT AVG(waist_length) FROM waist_entries WHERE date(timestamp) >= ?", (seven_days_ago,)
    )
    avg_waist_row = cursor.fetchone()
    avg_waist = f"{avg_waist_row[0]:.2f} inches" if avg_waist_row and avg_waist_row[0] else "Not Available"

    conn.close()

    # Create renderable content
    progress = min(int((calories_today / tdee) * 100), 100)
    progress_bar = ProgressBar(total=100, completed=progress, width=40)

    panel_group = Group(
        f"[bold]Calories:[/bold] {calories_today} / {tdee} kcal ({progress}%)",
        f"[bold]Weight:[/bold]   {latest_weight}",
        f"[bold]Waist (7d avg):[/bold] {avg_waist}",
        "",  # For a newline
        progress_bar
    )

    console.print(
        Panel(
            panel_group,
            title="Daily Status",
            border_style="blue",
            padding=(1, 2)
        )
    )

def _parse_period(period_str: str) -> tuple[Union[date, None], Union[date, None]]:
    """Parses a period string (e.g., '7d', '4w', 'YYYY-MM-DD:YYYY-MM-DD') and returns start and end dates."""
    if not period_str:
        return None, None

    period_str = period_str.lower().strip()

    if ':' in period_str:
        try:
            start_str, end_str = period_str.split(':')
            start_date = datetime.strptime(start_str, "%Y-%m-%d").date()
            end_date = datetime.strptime(end_str, "%Y-%m-%d").date()
            return start_date, end_date
        except ValueError:
            return None, None

    if len(period_str) < 2 or not period_str[:-1].isdigit():
        return None, None

    num = int(period_str[:-1])
    unit = period_str[-1]
    end_date = date.today()

    if unit == 'd':
        start_date = end_date - timedelta(days=num - 1)
    elif unit == 'w':
        start_date = end_date - timedelta(weeks=num) + timedelta(days=1)
    elif unit == 'm':
        # Approximation: 1 month = 30 days
        start_date = end_date - timedelta(days=num * 30)
    elif unit == 'y':
        # Approximation: 1 year = 365 days
        start_date = end_date - timedelta(days=num * 365)
    else:
        return None, None
    
    return start_date, end_date

def _display_history(start_date: date, end_date: date):
    """Shows a daily summary table for a given date range."""
    config = get_config()
    tdee = int(config["USER"]["TDEE"])

    conn = get_db_connection()
    cursor = conn.cursor()

    num_days = (end_date - start_date).days + 1
    if num_days <= 0:
        console.print("[yellow]Start date must be before end date.[/yellow]")
        return

    table = Table(title=f"Summary from {start_date.isoformat()} to {end_date.isoformat()} ({num_days} days)")
    table.add_column("Date", style="cyan")
    table.add_column("Calories Logged", style="yellow", justify="right")
    table.add_column("Daily Goal", style="blue", justify="right")
    table.add_column("Deficit / Surplus", justify="right")
    table.add_column("Weight", style="magenta", justify="right")
    table.add_column("Waist", style="green", justify="right")

    total_deficit_surplus = 0
    weights = []

    # Get all calories grouped by day for the date range
    cursor.execute(
        "SELECT date(timestamp) as entry_date, SUM(calories) as total_calories FROM food_entries WHERE date(timestamp) BETWEEN ? AND ? GROUP BY entry_date",
        (start_date.isoformat(), end_date.isoformat())
    )
    daily_calories_map = {row['entry_date']: row['total_calories'] for row in cursor.fetchall()}

    # Get all weight entries for the date range, taking the last one per day
    cursor.execute(
        "SELECT date(timestamp) as entry_date, weight FROM weight_entries WHERE date(timestamp) BETWEEN ? AND ? ORDER BY timestamp ASC",
        (start_date.isoformat(), end_date.isoformat()),
    )
    daily_weight_map = {row['entry_date']: row['weight'] for row in cursor.fetchall()}

    # Get all waist entries for the date range, taking the last one per day
    cursor.execute(
        "SELECT date(timestamp) as entry_date, waist_length FROM waist_entries WHERE date(timestamp) BETWEEN ? AND ? ORDER BY timestamp ASC",
        (start_date.isoformat(), end_date.isoformat()),
    )
    daily_waist_map = {row['entry_date']: row['waist_length'] for row in cursor.fetchall()}
    conn.close()

    waist_lengths = []


    # Iterate through the date range backwards
    for i in range(num_days):
        current_date = end_date - timedelta(days=i)
        date_str = current_date.isoformat()

        calories_logged = daily_calories_map.get(date_str, 0)
        deficit_surplus = calories_logged - tdee
        
        # Only add to total if calories were logged
        if calories_logged > 0:
            total_deficit_surplus += deficit_surplus

        weight = daily_weight_map.get(date_str)
        if weight:
            weights.append(weight)
            weight_str = f"{weight:.1f}"
        else:
            weight_str = "N/A"

        waist_length = daily_waist_map.get(date_str)
        if waist_length:
            waist_lengths.append(waist_length)
            waist_length_str = f"{waist_length:.2f}"
        else:
            waist_length_str = "N/A"

        # Color coding for deficit/surplus
        if calories_logged == 0:
            deficit_surplus_str = "N/A"
        elif deficit_surplus < 0:
            deficit_surplus_str = f"[green]{deficit_surplus:+d}[/green]"
        else:
            deficit_surplus_str = f"[red]{deficit_surplus:+d}[/red]"

        table.add_row(
            date_str,
            str(calories_logged) if calories_logged > 0 else "0",
            str(tdee),
            deficit_surplus_str,
            weight_str,
            waist_length_str
        )

    console.print(table)

    # Calculate average weight
    avg_weight = sum(weights) / len(weights) if weights else 0

    # Calculate moving average
    avg_waist = sum(waist_lengths) / len(waist_lengths) if waist_lengths else 0

    # Print total summary panel
    if total_deficit_surplus < 0:
        total_str = f"[green]Total Period Deficit: {total_deficit_surplus:,} kcal[/green]"
    else:
        total_str = f"[red]Total Period Surplus: +{total_deficit_surplus:,} kcal[/red]"

    if avg_weight > 0:
        total_str += f"\n[magenta]Average Weight: {avg_weight:.1f}[/magenta]"
    
    if avg_waist > 0:
        total_str += f"\n[green]Average Waist: {avg_waist:.2f}[/green]"

    console.print(Panel(total_str, title="Period Summary", border_style="magenta", padding=(0, 2)))


def _interactive_history():
    """Runs the history command in interactive mode."""
    console.clear()
    console.print("[bold cyan]Interactive History Mode[/bold cyan]")
    console.print("Use [N]ext/[P]revious, [E]nter a new period, or [Q]uit.")

    # Default to last 7 days on start
    end_date = date.today()
    start_date = end_date - timedelta(days=6)
    _display_history(start_date, end_date)

    while True:
        command = _get_char().lower()

        if command == 'q':
            break

        should_redraw = False
        if command == 'n':
            # Move to next period
            duration = (end_date - start_date)
            start_date = end_date + timedelta(days=1)
            end_date = start_date + duration
            should_redraw = True
        elif command == 'p':
            # Move to previous period
            duration = (end_date - start_date)
            end_date = start_date - timedelta(days=1)
            start_date = end_date - duration
            should_redraw = True
        elif command == 'e':
            period_str = console.input("[cyan]Enter period> [/cyan]").strip().lower()
            if not period_str:
                # Redraw to clear the input line
                should_redraw = True
            else:
                new_start, new_end = _parse_period(period_str)
                if not new_start:
                    console.print(f"[bold red]Invalid period format: '{period_str}'.[/bold red]")
                    console.print("Use formats like '7d', '4w', '1m', '1y', or 'YYYY-MM-DD:YYYY-MM-DD'.")
                    console.input("Press Enter to continue...")
                else:
                    start_date, end_date = new_start, new_end
                should_redraw = True

        if should_redraw:
            console.clear()
            console.print("[bold cyan]Interactive History Mode[/bold cyan]")
            console.print("Use [N]ext/[P]revious, [E]nter a new period, or [Q]uit.")
            _display_history(start_date, end_date)


@app.command()
def history(
    period: str = typer.Argument(None, help="Period to view: e.g., '7d', '4w', '1m', '1y', or a date range 'YYYY-MM-DD:YYYY-MM-DD'. Leave empty for interactive mode.", show_default=False)
):
    """Shows a daily summary of calories, deficits, and weight. Can be run in interactive mode."""
    check_initialized()
    
    if period is None:
        _interactive_history()
    else:
        start_date, end_date = _parse_period(period)
        if not start_date:
            console.print(f"[bold red]Invalid period format: '{period}'.[/bold red]")
            console.print("Use formats like '7d', '4w', '1m', '1y', or 'YYYY-MM-DD:YYYY-MM-DD'.")
            raise typer.Exit()
        _display_history(start_date, end_date)


def _display_waist_history(start_date: date, end_date: date):
    """Shows a daily summary table for a given date range."""
    conn = get_db_connection()
    cursor = conn.cursor()

    num_days = (end_date - start_date).days + 1
    if num_days <= 0:
        console.print("[yellow]Start date must be before end date.[/yellow]")
        return

    table = Table(title=f"Waist Summary from {start_date.isoformat()} to {end_date.isoformat()} ({num_days} days)")
    table.add_column("Date", style="cyan")
    table.add_column("Waist Length", style="magenta", justify="right")

    # Get all waist entries for the date range, taking the last one per day
    cursor.execute(
        "SELECT date(timestamp) as entry_date, waist_length FROM waist_entries WHERE date(timestamp) BETWEEN ? AND ? ORDER BY timestamp ASC",
        (start_date.isoformat(), end_date.isoformat()),
    )
    daily_waist_map = {row['entry_date']: row['waist_length'] for row in cursor.fetchall()}
    conn.close()

    waist_lengths = []
    # Iterate through the date range backwards
    for i in range(num_days):
        current_date = end_date - timedelta(days=i)
        date_str = current_date.isoformat()

        waist_length = daily_waist_map.get(date_str)
        if waist_length:
            waist_lengths.append(waist_length)
            waist_length_str = f"{waist_length:.2f}"
        else:
            waist_length_str = "N/A"

        table.add_row(
            date_str,
            waist_length_str
        )

    console.print(table)

    # Calculate moving average
    avg_waist = sum(waist_lengths) / len(waist_lengths) if waist_lengths else 0

    # Print total summary panel
    if avg_waist > 0:
        total_str = f"[magenta]Average Waist: {avg_waist:.2f}[/magenta]"
        console.print(Panel(total_str, title="Period Summary", border_style="magenta", padding=(0, 2)))


@app.command()
def waist(
    period: str = typer.Argument(None, help="Period to view: e.g., '7d', '4w', '1m', '1y', or a date range 'YYYY-MM-DD:YYYY-MM-DD'. Leave empty for interactive mode.", show_default=False)
):
    """Shows a summary of waist measurements. Can be run in interactive mode."""
    check_initialized()
    
    if period is None:
        # For now, no interactive mode for waist, just show last 7 days
        end_date = date.today()
        start_date = end_date - timedelta(days=6)
        _display_waist_history(start_date, end_date)
    else:
        start_date, end_date = _parse_period(period)
        if not start_date:
            console.print(f"[bold red]Invalid period format: '{period}'.[/bold red]")
            console.print("Use formats like '7d', '4w', '1m', '1y', or 'YYYY-MM-DD:YYYY-MM-DD'.")
            raise typer.Exit()
        _display_waist_history(start_date, end_date)


def _draw_review_screen(current_date: date):
    """Draws the interactive review screen for a given date."""
    console.clear()
    config = get_config()
    tdee = int(config["USER"]["TDEE"])

    conn = get_db_connection()
    cursor = conn.cursor()

    date_str = current_date.isoformat()
    
    # Get all entries for the day
    cursor.execute(
        "SELECT 'food' as type, id, calories, description, timestamp FROM food_entries WHERE date(timestamp) = ? "
        "UNION ALL "
        "SELECT 'weight' as type, id, weight, null, timestamp FROM weight_entries WHERE date(timestamp) = ? "
        "ORDER BY timestamp",
        (date_str, date_str)
    )
    entries = cursor.fetchall()
    
    # Calculate summary
    calories_today = sum(e['calories'] for e in entries if e['type'] == 'food')
    deficit_surplus = calories_today - tdee

    # Build entry lines for display
    entry_lines = []
    # The id_map maps the display index (1, 2, 3...) to the db id and type
    id_map = [None] # Use 1-based indexing for the UI
    for i, entry in enumerate(entries, 1):
        id_map.append({"id": entry["id"], "type": entry["type"]})
        if entry["type"] == "food":
            time_str = datetime.fromisoformat(entry['timestamp']).strftime("%H:%M")
            line = f"  {i}. [bold yellow]Food[/bold yellow]:   {entry['calories']} kcal at {time_str} - '{entry['description'] or ''}'"
        else:
            time_str = datetime.fromisoformat(entry['timestamp']).strftime("%H:%M")
            line = f"  {i}. [bold cyan]Weight[/bold cyan]: {entry['calories']} lbs at {time_str}" # 'calories' column holds weight in the UNION
        entry_lines.append(line)

    summary_text = f"[bold]Calories:[/bold] {calories_today} / {tdee} kcal  |  [bold]Deficit/Surplus:[/bold] {deficit_surplus:+} kcal"
    
    layout = Group(
        summary_text,
        "\n[bold]Entries:[/bold]",
        *entry_lines if entry_lines else ["  No entries for this day."],
    )

    console.print(
        Panel(
            layout,
            title=f"Reviewing: {date_str}",
            border_style="blue",
            padding=(1, 2)
        )
    )
    console.print("[[A]dd [E]dit [D]elete]  |  [[P]rev Day [N]ext Day]  |  [[Q]uit]")
    return id_map


@app.command()
def review(date_str: str = typer.Argument(None, help="The date to review in YYYY-MM-DD format. Defaults to today or 'yesterday'.")):
    """Interactively review, add, edit, or delete entries for a specific day."""
    check_initialized()
    
    if date_str is None or date_str.lower() == "today":
        current_date = date.today()
    elif date_str.lower() == "yesterday":
        current_date = date.today() - timedelta(days=1)
    else:
        try:
            current_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            console.print("[bold red]Invalid date format.[/bold red] Please use YYYY-MM-DD.")
            raise typer.Exit()

    while True:
        id_map = _draw_review_screen(current_date)
        
        action = _get_char().lower()

        if action == "q":
            break
        elif action == "n":
            current_date += timedelta(days=1)
            continue
        elif action == "p":
            current_date -= timedelta(days=1)
            continue
        elif action == "a":
            entry_type = console.input("Add (f)ood or (w)eight? ").lower()
            ts = datetime.combine(current_date, datetime.now().time()).isoformat()
            if entry_type == 'f':
                try:
                    cals = int(console.input("Calories: "))
                    desc = console.input("Description (optional): ")
                    time_str = console.input("Time (HH:MM, optional): ")
                    meal_time = _parse_time(time_str) if time_str else datetime.now().time()
                    if not meal_time:
                        console.input("[red]Invalid time format. Press Enter to continue...[/red]")
                        continue
                    ts = datetime.combine(current_date, meal_time).isoformat()
                    _add_food_entry(ts, cals, desc)
                except ValueError:
                    console.input("[red]Invalid number. Press Enter to continue...[/red]")
            elif entry_type == 'w':
                try:
                    weight = float(console.input("Weight: "))
                    _add_weight_entry(ts, weight)
                except ValueError:
                    console.input("[red]Invalid number. Press Enter to continue...[/red]")
        elif action in ("d", "e"):
            try:
                num_str = console.input(f"Entry number to {'delete' if action == 'd' else 'edit'}: ")
                if not num_str.isdigit():
                    console.input("[red]Invalid entry number. Press Enter to continue...[/red]")
                    continue
                num = int(num_str)
            except (ValueError, TypeError):
                console.input("[red]Invalid entry number. Press Enter to continue...[/red]")
                continue

            if not (0 < num < len(id_map)):
                console.input(f"[red]Invalid entry number: {num}. Press Enter to continue...[/red]")
                continue
            
            entry_info = id_map[num]
            entry_id = entry_info['id']
            entry_type = entry_info['type']

            if action == "d":
                confirm = console.input(f"Delete entry {num}? (y/n) ").lower()
                if confirm == 'y':
                    _delete_entry(entry_type, entry_id)
            
            elif action == "e":
                conn = get_db_connection()
                if entry_type == "food":
                    current = conn.execute("SELECT * FROM food_entries WHERE id = ?", (entry_id,)).fetchone()
                    try:
                        new_cals_str = console.input(f"Calories (current: {current['calories']}): ")
                        new_cals = int(new_cals_str) if new_cals_str else current['calories']
                        new_desc = console.input(f"Description (current: '{current['description'] or ''}'): ")
                        # If user enters nothing, keep original. If they enter something, use it.
                        final_desc = new_desc if new_desc is not None else current['description']

                        time_str = console.input(f"Time (current: {datetime.fromisoformat(current['timestamp']).strftime('%H:%M')} HH:MM, optional): ")
                        meal_time = _parse_time(time_str) if time_str else datetime.fromisoformat(current['timestamp']).time()
                        if not meal_time:
                            console.input("[red]Invalid time format. Press Enter to continue...[/red]")
                            continue
                        ts = datetime.combine(datetime.fromisoformat(current['timestamp']).date(), meal_time).isoformat()

                        _edit_food_entry(entry_id, new_cals, final_desc, ts)
                    except ValueError:
                        console.input("[red]Invalid number. Press Enter to continue...[/red]")
                else: # weight
                    current = conn.execute("SELECT * FROM weight_entries WHERE id = ?", (entry_id,)).fetchone()
                    try:
                        new_weight_str = console.input(f"Weight (current: {current['weight']}): ")
                        new_weight = float(new_weight_str) if new_weight_str else current['weight']
                        _edit_weight_entry(entry_id, new_weight)
                    except ValueError:
                        console.input("[red]Invalid number. Press Enter to continue...[/red]")
                conn.close()



if __name__ == "__main__":
    app()
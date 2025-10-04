import typer
from rich.console import Console, Group
from rich.table import Table
import pathlib
import sqlite3
import configparser
from datetime import datetime

from rich.panel import Panel
from rich.progress_bar import ProgressBar
from datetime import date, timedelta


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
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS food_entries (
            id INTEGER PRIMARY KEY,
            timestamp TEXT NOT NULL,
            calories INTEGER NOT NULL,
            description TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS weight_entries (
            id INTEGER PRIMARY KEY,
            timestamp TEXT NOT NULL,
            weight REAL NOT NULL
        )
    """)
    conn.commit()
    conn.close()


# --- Internal Database Logic ---
def _add_food_entry(timestamp: str, calories: int, description: str | None):
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


def _delete_entry(entry_type: str, entry_id: int):
    """Deletes an entry from the database."""
    table_name = "food_entries" if entry_type == "food" else "weight_entries"
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(f"DELETE FROM {table_name} WHERE id = ?", (entry_id,))
    conn.commit()
    conn.close()


def _edit_food_entry(entry_id: int, calories: int, description: str | None):
    """Updates a food entry in the database."""
    conn = get_db_connection()
    cursor = conn.cursor()
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


@log_app.command("food")
def log_food(
    calories: int = typer.Argument(..., help="The number of calories to log."),
    description: str = typer.Option(None, "--desc", "-d", help="An optional description of the food.")
):
    """Logs a food entry for the current time."""
    check_initialized()
    timestamp = datetime.now().isoformat()
    _add_food_entry(timestamp, calories, description)
    console.print(f"[green]Logged {calories} calories.[/green]")

@log_app.command("weight")
def log_weight(
    weight: float = typer.Argument(..., help="Your current weight.")
):
    """Logs a weight entry for the current time."""
    check_initialized()
    timestamp = datetime.now().isoformat()
    _add_weight_entry(timestamp, weight)
    console.print(f"[green]Logged weight: {weight}.[/green]")

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

    conn.close()

    # Create renderable content
    progress = min(int((calories_today / tdee) * 100), 100)
    progress_bar = ProgressBar(total=100, completed=progress, width=40)

    panel_group = Group(
        f"[bold]Calories:[/bold] {calories_today} / {tdee} kcal ({progress}%)",
        f"[bold]Weight:[/bold]   {latest_weight}",
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

@app.command()
def history():
    """Shows a daily summary and deficit/surplus for the last 7 days."""
    check_initialized()
    config = get_config()
    tdee = int(config["USER"]["TDEE"])

    conn = get_db_connection()
    cursor = conn.cursor()

    table = Table(title="Last 7 Days Summary")
    table.add_column("Date", style="cyan")
    table.add_column("Calories Logged", style="yellow", justify="right")
    table.add_column("Daily Goal", style="blue", justify="right")
    table.add_column("Deficit / Surplus", justify="right")

    total_deficit_surplus = 0

    # Get all calories grouped by day for the last 7 days
    seven_days_ago = (date.today() - timedelta(days=6)).isoformat()
    cursor.execute(
        "SELECT date(timestamp) as entry_date, SUM(calories) as total_calories FROM food_entries WHERE date(timestamp) >= ? GROUP BY entry_date",
        (seven_days_ago,)
    )
    daily_calories_map = {row['entry_date']: row['total_calories'] for row in cursor.fetchall()}
    conn.close()

    # Iterate through the last 7 days from today backwards
    for i in range(7):
        current_date = date.today() - timedelta(days=i)
        date_str = current_date.isoformat()

        calories_logged = daily_calories_map.get(date_str, 0)
        deficit_surplus = calories_logged - tdee
        total_deficit_surplus += deficit_surplus

        # Color coding for deficit/surplus
        if calories_logged == 0:
            # Don't apply color if no calories were logged for that day
            deficit_surplus_str = f"{deficit_surplus:+d}"
        elif deficit_surplus < 0:
            deficit_surplus_str = f"[green]{deficit_surplus:+d}[/green]"
        else:
            deficit_surplus_str = f"[red]{deficit_surplus:+d}[/red]"

        table.add_row(
            date_str,
            str(calories_logged),
            str(tdee),
            deficit_surplus_str
        )

    console.print(table)

    # Print total summary panel
    if total_deficit_surplus < 0:
        total_str = f"[green]Total 7-Day Deficit: {total_deficit_surplus:,} kcal[/green]"
    else:
        total_str = f"[red]Total 7-Day Surplus: +{total_deficit_surplus:,} kcal[/red]"

    console.print(Panel(total_str, title="Weekly Summary", border_style="magenta", padding=(0, 2)))


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
            line = f"  {i}. [bold yellow]Food[/bold yellow]:   {entry['calories']} kcal - '{entry['description'] or ''}'"
        else:
            line = f"  {i}. [bold cyan]Weight[/bold cyan]: {entry['calories']} lbs" # 'calories' column holds weight in the UNION
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
    console.print("[[A]dd [E]dit # [D]elete #]  |  [[P]rev Day [N]ext Day]  |  [[Q]uit]")
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
        
        command = console.input("> ").lower().strip()
        cmd_parts = command.split()
        action = cmd_parts[0] if cmd_parts else ""

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
            if len(cmd_parts) < 2 or not cmd_parts[1].isdigit():
                console.input("[red]Command requires an entry number (e.g., 'd 1'). Press Enter to continue...[/red]")
                continue
            
            num = int(cmd_parts[1])
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
                        _edit_food_entry(entry_id, new_cals, final_desc)
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
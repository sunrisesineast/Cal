# Calorie Tracker CLI

A minimalist, elegant terminal application for tracking daily calories and weight. Designed for a fast, keyboard-driven workflow.

## Features

*   **Minimalist UI:** Clean, aesthetically pleasing interface powered by `rich`.
*   **Fast Entry:** Log calories and weight with simple commands.
*   **Daily Status:** Get a quick overview of your current day's progress with a visual progress bar.
*   **Historical View:** Analyze your performance with a 7-day summary showing daily deficits/surpluses.
*   **Interactive Editing:** A powerful `review` mode to interactively add, edit, or delete entries for any day.
*   **Configurable:** Set your daily calorie goal (TDEE).

## Installation

1.  **Clone the repository (or download the source code):**
    ```bash
    # Make sure to replace with your actual repository URL
    git clone https://github.com/user/repo.git
    cd <repository-folder>
    ```

2.  **Install the application:**
    It is recommended to install the package in "editable" mode. This allows you to modify the source code and have the changes apply instantly without reinstalling.

    ```bash
    pip install -e .
    ```
    This will install the necessary dependencies and add the `cal` command to your system's PATH.

## Usage

The application is used via the `cal` command, followed by a subcommand.

### `cal init`

Initialize the application. This is the **first command you must run**. It will create the database and config file, and prompt you for your Total Daily Energy Expenditure (TDEE).

```bash
cal init
```

### `cal log`

Log food or weight entries for the current time.

*   **Log food:**
    ```bash
    cal log food <calories> --desc "Optional description"
    ```
    *Example:*
    ```bash
    cal log food 550 --desc "Lunch: Sandwich"
    ```

*   **Log weight:**
    ```bash
    cal log weight <your-weight>
    ```
    *Example:*
    ```bash
    cal log weight 185.5
    ```

#### Shortcuts

For even faster logging, you can use the `lf` and `lw` commands:

```bash
# Equivalent to 'cal log food'
cal lf 550 --desc "Lunch: Sandwich"

# Equivalent to 'cal log weight'
cal lw 185.5
```

### `cal status`

Display a summary panel for the current day, including calories consumed vs. your goal, your most recent weight, and a progress bar.

```bash
cal status
```

### `cal history`

Show a summary table of the last 7 days, including calories logged, your daily goal, and the calculated deficit or surplus for each day. It also includes a total weekly deficit/surplus.

```bash
cal history
```

### `cal review [DATE]`

Open an interactive, full-screen mode to manage entries for a specific day. This is the most powerful feature for correcting mistakes or back-filling data.

*   `cal review`: Review today.
*   `cal review yesterday`: Review yesterday.
*   `cal review 2025-10-03`: Review a specific date.

Once in review mode, use the single-key commands displayed at the bottom of the screen:
*   **`a`**: Add a new food or weight entry for the reviewed day.
*   **`e <#>`**: Edit the entry corresponding to the number.
*   **`d <#>`**: Delete the entry corresponding to the number.
*   **`p` / `n`**: Navigate to the previous or next day.
*   **`q`**: Quit the review session.

### `cal config`

View or update your configuration.

*   **View current TDEE:**
    ```bash
    cal config
    ```
*   **Update TDEE:**
    ```bash
    cal config --tdee 2100
    ```

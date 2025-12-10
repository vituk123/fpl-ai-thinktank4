# FPL Optimizer

**Autonomous Fantasy Premier League analysis and optimization system**

A production-ready Python package that provides comprehensive FPL analysis, transfer recommendations, and chip evaluation using data-driven projection models.

## Features

- 🤖 **Autonomous Operation**: Auto-detects the current gameweek and fetches all required data.

- 📊 **Multi-Model Projections**: Combines official FPL data with a custom regression model for robust player forecasts.

- 🎯 **EO-Adjusted Strategy**: Optimizes for differential picks based on your rank and risk tolerance.

- 🔄 **Transfer Optimization**: Finds the best transfer combinations to maximize your squad's expected value (EV).

- 🎴 **Chip Evaluation**: Provides data-driven advice on when to use your Bench Boost, Triple Captain, and Free Hit.

- 📝 **Comprehensive Reports**: Generates detailed Markdown reports summarizing the analysis.

## Installation

1.  **Clone the repository:**

    ```bash
    git clone https://github.com/your-username/fpl-optimizer.git
    cd fpl-optimizer
    ```

2.  **Create a Virtual Environment (Highly Recommended)**

    A virtual environment keeps the project's dependencies isolated from other Python projects on your system.

    ```bash
    # Create the virtual environment (named "venv")
    python -m venv venv

    # Activate the virtual environment
    # On Windows:
    venv\Scripts\activate

    # On macOS and Linux:
    source venv/bin/activate
    ```

    After activation, you should see `(venv)` at the beginning of your terminal prompt.

3.  **Install the Required Libraries**

    Now, install all the libraries listed in `requirements.txt` using pip.

    ```bash
    pip install -r requirements.txt
    ```

    This will download and install pandas, requests, pyyaml, and other necessary packages into your virtual environment.

## Usage

### Step 1: Find Your FPL Team ID

You need your unique FPL ID to run the analysis.

1. Log in to the [official Fantasy Premier League website](https://fantasy.premierleague.com/).
2. Go to the "Points" tab.
3. Look at the URL in your browser's address bar. It will look like this:
   ```
   https://fantasy.premierleague.com/entry/YOUR_ID/event/X
   ```
   Your ID is the number where `YOUR_ID` is.

### Step 2: Run the Script!

You are now ready to run the optimizer. The main script is `src/main.py`. Execute it from your terminal, making sure to replace `12345` with your actual FPL ID.

```bash
python src/main.py --entry-id 12345
```

To see more detailed logs while it's running, add the `--verbose` flag:

```bash
python src/main.py --entry-id 12345 --verbose
```

### Additional Options

The script supports several command-line options:

- `--entry-id`: Your FPL entry/team ID (required if not set in config.yml)
- `--gw`: Target gameweek (default: auto-detect next GW)
- `--max-transfers`: Maximum transfers to consider (default: 4)
- `--output-dir`: Output directory for reports (default: output)
- `--config`: Path to config file (default: config.yml)
- `--cache-dir`: Cache directory (default: .cache)
- `--clear-cache`: Clear API cache before running
- `--verbose`: Enable verbose logging


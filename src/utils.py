"""
FPL Optimizer - Utility Functions

Handles price conversions, constraints, and formatting.
"""
import pandas as pd
from typing import Dict, List, Tuple


def price_from_api(api_price: int) -> float:
    """
    Convert FPL API price (integer) to actual price (float).
    e.g., 55 -> 5.5
    """
    return api_price / 10.0


def validate_squad_constraints(squad: pd.DataFrame) -> Tuple[bool, List[str]]:
    """
    Validate FPL squad constraints.
    """
    violations = []
    
    # Check squad size
    if len(squad) != 15:
        violations.append(f"Squad size is {len(squad)}, must be 15.")
    
    # Check position counts
    position_counts = squad['element_type'].value_counts().to_dict()
    required_positions = {1: 2, 2: 5, 3: 5, 4: 3} # GKP, DEF, MID, FWD
    
    for pos, required_count in required_positions.items():
        count = position_counts.get(pos, 0)
        if count != required_count:
            violations.append(f"Position {pos}: Found {count}, require {required_count}.")
            
    # Check max players from one team
    team_counts = squad['team'].value_counts()
    for team, count in team_counts.items():
        if count > 3:
            violations.append(f"Team {team} has {count} players, max is 3.")
            
    return len(violations) == 0, violations


def create_markdown_table(df: pd.DataFrame) -> str:
    """
    Create a markdown table from a pandas DataFrame.
    """
    header = "| " + " | ".join(df.columns) + " |"
    separator = "| " + " | ".join(["---"] * len(df.columns)) + " |"
    body = "\n".join(["| " + " | ".join(map(str, row)) + " |" for row in df.itertuples(index=False)])
    
    return "\n".join([header, separator, body])


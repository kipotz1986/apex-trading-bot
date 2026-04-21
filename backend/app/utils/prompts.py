"""
Prompt Loading Utility.
"""

import os
from pathlib import Path

def get_prompt(prompt_name: str) -> str:
    """
    Load prompt from txt file in app/agents/prompts/.
    """
    base_path = Path(__file__).parent.parent / "agents" / "prompts"
    file_path = base_path / f"{prompt_name}.txt"
    
    if not file_path.exists():
        raise FileNotFoundError(f"Prompt file not found: {file_path}")
        
    with open(file_path, "r") as f:
        return f.read().strip()

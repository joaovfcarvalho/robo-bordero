#!/usr/bin/env python3
"""
CBF Robot - Launcher script
This script starts the CBF Robot application.
"""
import os
import sys
# Add the src directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

# Import from the src folder directly
from src.main import main

if __name__ == "__main__":
    main()
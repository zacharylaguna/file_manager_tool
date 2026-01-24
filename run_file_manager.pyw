"""
File Manager Tool Launcher (No Console Window)
Double-click this file to run the application without a console window.
"""

import subprocess
import sys
import os

# Get the directory where this script is located
script_dir = os.path.dirname(os.path.abspath(__file__))
file_manager_path = os.path.join(script_dir, 'file_manager.py')

# Run the file manager
subprocess.run([sys.executable, file_manager_path])

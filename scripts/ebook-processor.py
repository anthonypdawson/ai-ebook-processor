#!/usr/bin/env python3
"""
Python-based wrapper for AI Ebook Processor CLI

This allows running the CLI directly from anywhere without needing to install the package.
Works on both Windows and Unix systems.
"""

import os
import sys
import subprocess
from pathlib import Path

def find_python_executable():
    """Find the best Python executable to use"""
    
    # Get the directory where this script is located
    script_dir = Path(__file__).parent.absolute()
    project_dir = script_dir.parent
    
    # Try virtual environment Python first
    if os.name == 'nt':  # Windows
        venv_python = project_dir / '.venv' / 'Scripts' / 'python.exe'
    else:  # Unix-like
        venv_python = project_dir / '.venv' / 'bin' / 'python'
    
    if venv_python.exists():
        return str(venv_python), str(project_dir)
    
    # Fallback to system Python
    python_candidates = ['python3', 'python']
    for python_cmd in python_candidates:
        try:
            result = subprocess.run([python_cmd, '--version'], 
                                  capture_output=True, text=True, check=True)
            if 'Python 3.' in result.stdout:
                return python_cmd, str(project_dir)
        except (subprocess.CalledProcessError, FileNotFoundError):
            continue
    
    raise RuntimeError("No suitable Python interpreter found")

def main():
    """Main entry point"""
    try:
        python_exec, project_dir = find_python_executable()
        
        # Set up environment
        env = os.environ.copy()
        pythonpath = env.get('PYTHONPATH', '')
        if pythonpath:
            env['PYTHONPATH'] = f"{project_dir}{os.pathsep}{pythonpath}"
        else:
            env['PYTHONPATH'] = project_dir
        
        # Build command
        cmd = [python_exec, '-m', 'ai_ebook_processor'] + sys.argv[1:]
        
        # Execute
        result = subprocess.run(cmd, env=env, cwd=project_dir)
        sys.exit(result.returncode)
        
    except RuntimeError as e:
        print(f"Error: {e}")
        print("Please install Python 3.8+ or activate the virtual environment.")
        sys.exit(1)
    except KeyboardInterrupt:
        sys.exit(130)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
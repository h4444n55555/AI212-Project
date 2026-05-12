<#
Create a Python 3.11 virtual environment and install backend dependencies.
Usage (PowerShell):
  .\setup_py311.ps1

This script will try to use the Windows Python launcher to create a venv
targeting Python 3.11. If `py -3.11` is not available it falls back to
`python -m venv` (which you should point to a 3.11 interpreter).
#>
if (Get-Command py -ErrorAction SilentlyContinue) {
    Write-Host "Creating venv with Python 3.11 via 'py -3.11'..."
    py -3.11 -m venv .venv311
} else {
    Write-Host "Python launcher not found; creating venv with default 'python' (ensure it's 3.11)..."
    python -m venv .venv311
}

Write-Host "Activating venv..."
& .\.venv311\Scripts\Activate.ps1

Write-Host "Upgrading pip and installing requirements..."
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

Write-Host "Done. To activate venv later: . \.\venv311\Scripts\Activate.ps1"
Write-Host "Optional: to enable Ray (requires Python 3.8-3.12):"
Write-Host "  py -3.11 -m pip install 'ray[default]>=2.0.0,<3.0.0'"

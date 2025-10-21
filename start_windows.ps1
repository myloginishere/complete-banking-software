Param(
  [string] $AppPort = $(if ($env:APP_PORT) { $env:APP_PORT } else { "5000" }),
  [string] $AppHost = $(if ($env:APP_HOST) { $env:APP_HOST } else { "0.0.0.0" })
)

# Windows PowerShell start script for Complete Banking Software
# - Activates virtual environment
# - Runs the Flask app

$venvActivate = ".\.venv\Scripts\Activate.ps1"
if (!(Test-Path $venvActivate)) {
  Write-Error "[!] Virtual environment not found. Run: python install.py"
  exit 1
}

. $venvActivate
$env:FLASK_ENV = "production"
python app.py

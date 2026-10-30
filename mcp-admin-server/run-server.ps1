# Run the orange-admin MCP server manually (AnythingLLM normally starts this
# for you automatically — this is just for testing it on its own).
#
# Usage: right-click -> "Run with PowerShell", or from any PowerShell prompt:
#   .\run-server.ps1
#
# It'll sit quietly with no output once it starts — that's expected, a bare
# MCP server prints nothing until a client (like AnythingLLM) talks to it
# over stdio. Ctrl+C to stop it.

# cd to this script's own folder, so it works no matter where you launch it from.
Set-Location -Path $PSScriptRoot

$env:ORANGE_ADMIN_EMAIL = "admin@orange.com"
$env:ORANGE_ADMIN_PASSWORD = "password123"

& ".\.venv\Scripts\python.exe" "server.py"

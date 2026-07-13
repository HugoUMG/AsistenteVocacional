# Detiene backend, frontend y la base de datos del Asistente Vocacional.
# Uso:   .\stop.ps1     (la base de datos conserva sus datos)

Get-NetTCPConnection -LocalPort 8000, 5173 -State Listen -ErrorAction SilentlyContinue |
    ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }

docker stop tfg-db 2>$null | Out-Null

Write-Host "Servicios detenidos. La base de datos conserva sus datos." -ForegroundColor Green

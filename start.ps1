# Levanta TODO el Asistente Vocacional: base de datos, backend y frontend.
# Uso:   .\start.ps1
# Si PowerShell lo bloquea:   powershell -ExecutionPolicy Bypass -File .\start.ps1

$root = $PSScriptRoot

function Info($m) { Write-Host $m -ForegroundColor Cyan }
function Ok($m)   { Write-Host $m -ForegroundColor Green }
function Warn($m) { Write-Host $m -ForegroundColor Yellow }

# 1) Asegura que Docker Desktop este corriendo.
docker info 2>$null | Out-Null
if ($LASTEXITCODE -ne 0) {
    Warn "Docker no esta corriendo. Abriendo Docker Desktop..."
    $dd = "$env:ProgramFiles\Docker\Docker\Docker Desktop.exe"
    if (Test-Path $dd) { Start-Process $dd }
    Warn "Esperando a que Docker inicie (puede tardar ~1 min)..."
    $t = 0
    do { Start-Sleep 3; $t += 3; docker info 2>$null | Out-Null } until ($LASTEXITCODE -eq 0 -or $t -ge 120)
    if ($LASTEXITCODE -ne 0) {
        Write-Host "No pude conectar con Docker. Abrelo manualmente y reintenta." -ForegroundColor Red
        return
    }
}

# 2) Base de datos (Postgres). Crea el contenedor la primera vez.
Info "Levantando base de datos..."
docker start tfg-db 2>$null | Out-Null
if ($LASTEXITCODE -ne 0) {
    docker run --name tfg-db -e POSTGRES_PASSWORD=dev -e POSTGRES_DB=tfg -p 5432:5432 -d postgres:16 | Out-Null
}
do { Start-Sleep 1; docker exec tfg-db pg_isready -U postgres 2>$null | Out-Null } until ($LASTEXITCODE -eq 0)
Ok "Base de datos lista."

# 3) Carga/actualiza el catalogo de carreras (idempotente).
Info "Cargando catalogo de carreras..."
Push-Location "$root\backend"
uv run python seed_carreras.py
Pop-Location

# 4) Backend en su propia ventana.
Info "Levantando backend  -> http://localhost:8000"
Start-Process powershell -ArgumentList '-NoExit','-Command',"Set-Location '$root\backend'; uv run uvicorn app.main:app --reload --port 8000"

# 5) Frontend en su propia ventana.
Info "Levantando frontend -> http://localhost:5173"
Start-Process powershell -ArgumentList '-NoExit','-Command',"Set-Location '$root\frontend'; npm run dev"

# 6) Abre el navegador.
Start-Sleep 4
Start-Process "http://localhost:5173"

Ok "`nTodo arriba."
Write-Host "  App:  http://localhost:5173"
Write-Host "  API:  http://localhost:8000"
Write-Host "Para detener: cierra las dos ventanas nuevas, o corre  .\stop.ps1"

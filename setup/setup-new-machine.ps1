# ══════════════════════════════════════════════════════════════
#  setup-new-machine.ps1 — Bootstrap Graphiti en Windows
#
#  ESTRATEGIA A REAL (fix auditoría A1): datos vivos en disco LOCAL
#  (%LOCALAPPDATA%\graphiti), la raíz de sync SOLO recibe backups terminados.
#  El .env con API keys también vive LOCAL (fix A4 — nunca en OneDrive).
#
#  ⚠ Este archivo DEBE guardarse como UTF-8 CON BOM (doc 11, B1):
#    powershell.exe (PS 5.1 / Task Scheduler) lee .ps1 sin BOM como ANSI y
#    los caracteres ─ / — inyectan comillas fantasma que rompen el parseo.
#
#  Ejecutar en PowerShell como administrador:
#    Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
#    .\setup-new-machine.ps1
#    .\setup-new-machine.ps1 -OneDrivePath "D:\OneDrive"
#    .\setup-new-machine.ps1 -Local          # single-laptop, sin OneDrive
# ══════════════════════════════════════════════════════════════

param(
    [string]$OneDrivePath = $(if ($env:OneDrive) { $env:OneDrive } else { "$env:USERPROFILE\OneDrive" }),
    [switch]$Local = $false,          # modo single-laptop: DevSetup en el home, sin OneDrive
    [switch]$SkipRestore = $false,
    [switch]$ForceOneDrive = $false   # escape hatch para Estrategia B (bajo tu riesgo)
)

$ErrorActionPreference = "Stop"

# ── Modo de sincronización ────────────────────────────────────────────────
# multi-laptop (default): DevSetup vive en OneDrive → skills/backups viajan solos.
# single-laptop (-Local o sin OneDrive): DevSetup vive en %USERPROFILE%\DevSetup.
#   Todo lo demás es idéntico; la durabilidad extra la da el remote git del vault.
if (-not $Local -and -not (Test-Path $OneDrivePath)) {
    Write-Host "[INFO] OneDrive no encontrado en $OneDrivePath — cambiando a modo LOCAL (single-laptop)." -ForegroundColor Yellow
    $Local = $true
}
if ($Local) { $OneDrivePath = $env:USERPROFILE }
$SyncMode      = if ($Local) { "single-laptop (local, sin OneDrive)" } else { "multi-laptop (OneDrive)" }
$DevSetup      = "$OneDrivePath\DevSetup"
$GraphitiLocal = "$env:LOCALAPPDATA\graphiti"       # datos + config + .env + scripts (LOCAL)
$BackupDir     = "$DevSetup\graphiti-data\backups"  # lo ÚNICO de Graphiti en la raíz de sync
$Warnings      = @()

function Write-Header { param($msg) Write-Host "`n▶ $msg" -ForegroundColor Blue }
function Write-OK     { param($msg) Write-Host "  [OK] $msg" -ForegroundColor Green }
function Write-Warn   { param($msg) Write-Host "  [WARN] $msg" -ForegroundColor Yellow; $script:Warnings += $msg }
function Write-Err    { param($msg) Write-Host "  [ERR] $msg" -ForegroundColor Red }
function Write-Info   { param($msg) Write-Host "  [INFO] $msg" -ForegroundColor Cyan }

# Convierte C:\foo → /c/foo (formato Docker Desktop), cualquier letra de unidad (fix A7)
function ConvertTo-DockerPath { param($p)
    if ($p -match '^([A-Za-z]):(.*)$') {
        return "/" + $Matches[1].ToLower() + ($Matches[2] -replace '\\', '/')
    }
    return ($p -replace '\\', '/')
}

Write-Host "`n════════════════════════════════════════════════════" -ForegroundColor White
Write-Host " Graphiti + FalkorDB — Setup Windows (Estrategia A)" -ForegroundColor White
Write-Host " Modo          : $SyncMode" -ForegroundColor White
Write-Host " Datos locales : $GraphitiLocal" -ForegroundColor White
Write-Host " Backups       : $BackupDir" -ForegroundColor White
Write-Host "════════════════════════════════════════════════════`n" -ForegroundColor White

# ── 1. Verificar dependencias ──────────────────────────────────────────────
Write-Header "Verificando dependencias"
$errors = 0
try { docker --version | Out-Null; Write-OK "Docker instalado" }
catch { Write-Err "Docker no encontrado. Instala Docker Desktop."; $errors++ }
try { docker compose version | Out-Null; Write-OK "Docker Compose disponible" }
catch { Write-Err "Docker Compose no disponible."; $errors++ }
if ($errors -gt 0) { Write-Err "Corrige $errors errores críticos antes de continuar."; exit 1 }

# Guardia anti-OneDrive (fix A1): los datos vivos JAMÁS en OneDrive
if ($GraphitiLocal -match "OneDrive" -and -not $ForceOneDrive) {
    Write-Err "GraphitiLocal resuelve dentro de OneDrive — prohibido (H2, corrupción silenciosa)."
    Write-Err "Usa -ForceOneDrive solo si sabes exactamente lo que haces (Estrategia B)."
    exit 1
}

# ── 2. Crear directorios ───────────────────────────────────────────────────
Write-Header "Creando directorios"
@("$GraphitiLocal\data", "$GraphitiLocal\config", "$GraphitiLocal\scripts", $BackupDir) | ForEach-Object {
    New-Item -ItemType Directory -Force -Path $_ | Out-Null
}
Write-OK "Local:   $GraphitiLocal\{data,config,scripts}"
Write-OK "Backups: $BackupDir (solo snapshots)"

# ── 3. Copiar compose, config y scripts (fix A2: los scripts SÍ se instalan) ──
Write-Header "Instalando archivos"
$sources = @($PSScriptRoot, "$DevSetup\claude-dotfiles\graphiti") | Where-Object { $_ -and (Test-Path $_) }
function Install-File { param($name, $dest)
    foreach ($src in $sources) {
        if (Test-Path "$src\$name") { Copy-Item "$src\$name" $dest -Force; Write-OK "$name instalado"; return $true }
    }
    Write-Warn "$name no encontrado en $($sources -join ', '). Cópialo manualmente."
    return $false
}
Install-File "docker-compose.yml" "$GraphitiLocal\" | Out-Null
Install-File "config.yaml"        "$GraphitiLocal\config\" | Out-Null
$hasBackupScript  = Install-File "backup-graph.ps1"  "$GraphitiLocal\scripts\"
$hasRestoreScript = Install-File "restore-graph.ps1" "$GraphitiLocal\scripts\"

# ── 4. Crear .env LOCAL (fix A4: API keys nunca en OneDrive) ──────────────
Write-Header "Creando .env (local, fuera de OneDrive)"
$envFile = "$GraphitiLocal\.env"
$dataDocker   = ConvertTo-DockerPath "$GraphitiLocal\data"
$configDocker = ConvertTo-DockerPath "$GraphitiLocal\config"

if (-not (Test-Path $envFile)) {
    Write-Info "Pin de versiones (auditoría A5). Consulta el tag estable actual con:"
    Write-Info "  docker pull falkordb/falkordb:latest ; docker image ls falkordb/falkordb"
    $fkVer  = Read-Host "  FALKORDB_VERSION (tag concreto, ej. v4.2.1 — vacío = decidir después)"
    $mcpVer = Read-Host "  GRAPHITI_MCP_VERSION (tag concreto — vacío = decidir después)"
    @"
# Auto-generado por setup-new-machine.ps1 en $env:COMPUTERNAME - $(Get-Date -Format 'yyyy-MM-dd HH:mm')
# UBICACIÓN LOCAL A PROPÓSITO: contiene API keys (auditoría A4).

# Estrategia A: datos vivos LOCALES (formato Docker), backups a la raíz de sync
FALKORDB_DATA_PATH=$dataDocker
CONFIG_PATH=$configDocker
BACKUP_DIR=$BackupDir

# Pins de versión (OBLIGATORIOS — el compose no arranca sin ellos)
FALKORDB_VERSION=$fkVer
GRAPHITI_MCP_VERSION=$mcpVer

# Extracción de entidades — 3 rutas (detalle en .env.example del repo):
#  openai = pago, óptima | gemini = GRATIS (recomendada sin costo) | groq = gratis, TPM bajo
# La key del provider elegido es obligatoria. Nunca anthropic/haiku (H7).
LLM_PROVIDER=openai
OPENAI_API_KEY=
GOOGLE_API_KEY=
GROQ_API_KEY=
ANTHROPIC_API_KEY=
MODEL_NAME=gpt-4.1-mini
SMALL_MODEL_NAME=gpt-4.1-nano
# Ruta gemini: LLM_PROVIDER=gemini + GOOGLE_API_KEY + MODEL_NAME=gemini-2.0-flash
#   (y en config.yaml cambia el embedder a gemini o sentence_transformers)
# Ruta groq:   LLM_PROVIDER=groq + GROQ_API_KEY + MODEL_NAME=llama-3.3-70b-versatile
#   + SEMAPHORE_LIMIT=2 (free tier ~6k tokens/min)

FALKORDB_PASSWORD=
SEMAPHORE_LIMIT=3
"@ | Out-File -FilePath $envFile -Encoding UTF8
    Write-OK ".env creado en $envFile"
    Write-Warn "Edita el .env: la key del provider elegido (LLM_PROVIDER) es obligatoria."
    $edit = Read-Host "  ¿Abrir .env en Notepad ahora? [s/N]"
    if ($edit -in @('s','S')) { notepad $envFile; Read-Host "  Presiona Enter cuando hayas guardado" }
} else { Write-OK ".env ya existe (no sobreescrito)" }

# Validación fail-fast de lo obligatorio (key según el provider elegido)
$envContent = Get-Content $envFile -Raw
$envReady = $true
$provider = if ($envContent -match "(?m)^LLM_PROVIDER=(\w+)") { $Matches[1] } else { "openai" }
$keyByProvider = @{ openai = "OPENAI_API_KEY"; gemini = "GOOGLE_API_KEY";
                    groq = "GROQ_API_KEY"; anthropic = "ANTHROPIC_API_KEY" }
$keyVar = $keyByProvider[$provider]; if (-not $keyVar) { $keyVar = "OPENAI_API_KEY" }
foreach ($req in @($keyVar, "FALKORDB_VERSION", "GRAPHITI_MCP_VERSION")) {
    if ($envContent -match "(?m)^$req=\s*$") {
        Write-Warn "$req está vacío en .env (LLM_PROVIDER=$provider) — el stack NO se levantará hasta llenarlo."
        $envReady = $false
    }
}
if ($provider -eq "anthropic") { Write-Warn "LLM_PROVIDER=anthropic: extracción con structured output experimental (H7) — usa openai o gemini." }
if (($envContent -match "(?m)^FALKORDB_DATA_PATH=.*OneDrive") -and -not $ForceOneDrive) {
    Write-Err "FALKORDB_DATA_PATH apunta a OneDrive — prohibido (H2)."; exit 1
}

# ── 5. Agregar Graphiti al MCP de Claude Code ────────────────────────────
Write-Header "Configurando MCP"
try {
    $mcpList = claude mcp list 2>&1
    if ($mcpList -match "graphiti") { Write-OK "MCP 'graphiti-memory' ya configurado" }
    else {
        claude mcp add --transport http graphiti-memory "http://localhost:8000/mcp/" -s user
        Write-OK "MCP graphiti-memory agregado"
    }
} catch {
    Write-Warn "No se pudo configurar MCP automáticamente. Ejecuta:"
    Write-Info "claude mcp add --transport http graphiti-memory http://localhost:8000/mcp/ -s user"
}

# ── 5b. Sincronizar skills (raíz de sync → Claude Code + plugin Cowork) ───
Write-Header "Sincronizando skills"
$syncSkills = Join-Path $PSScriptRoot "sync-skills.ps1"
if (Test-Path $syncSkills) {
    try { & $syncSkills -SkillsRoot "$DevSetup\claude-skills" }
    catch { Write-Warn "sync-skills falló: $($_.Exception.Message). Córrelo manualmente." }
} else { Write-Warn "sync-skills.ps1 no encontrado junto a este script." }

# ── 5c. Instalar/cablear hooks de Claude Code (enforcement anti-drift) ────
Write-Header "Instalando hooks"
$syncHooks = Join-Path $PSScriptRoot "sync-hooks.ps1"
if (Test-Path $syncHooks) {
    try { & $syncHooks }
    catch { Write-Warn "sync-hooks falló: $($_.Exception.Message). Córrelo manualmente." }
} else { Write-Warn "sync-hooks.ps1 no encontrado junto a este script." }

# ── 6. Restaurar backup (fix A3: SOLO via restore-graph, AOF-safe) ────────
Write-Header "Verificando backups"
$stackUp = $false
$latestBackup = Get-ChildItem "$BackupDir\*.rdb" -ErrorAction SilentlyContinue |
    Sort-Object LastWriteTime -Descending | Select-Object -First 1

if ($latestBackup -and -not $SkipRestore) {
    Write-Info "Backup encontrado: $($latestBackup.Name) ($($latestBackup.LastWriteTime.ToString('yyyy-MM-dd HH:mm')))"
    if ($hasRestoreScript -and $envReady) {
        $restore = Read-Host "  ¿Restaurar con restore-graph.ps1 (verifica que los datos carguen)? [s/N]"
        if ($restore -in @('s','S')) {
            & "$GraphitiLocal\scripts\restore-graph.ps1" -BackupFile $latestBackup.FullName -GraphitiLocal $GraphitiLocal
            if ($LASTEXITCODE -eq 0) { $stackUp = $true }
        }
    } else {
        Write-Warn "Restore pospuesto (falta restore-graph.ps1 o el .env está incompleto)."
        Write-Warn "NUNCA copies dump.rdb a mano: con AOF activo no restaura nada (A3)."
    }
} else { Write-Info "Sin backups previos. Iniciando con grafo vacío." }

# ── 7. Levantar containers ────────────────────────────────────────────────
if (-not $stackUp) {
    Write-Header "Levantando Docker"
    if ($envReady) {
        docker compose --env-file $envFile -f "$GraphitiLocal\docker-compose.yml" up -d
        if ($LASTEXITCODE -eq 0) { Write-OK "Containers levantados"; $stackUp = $true }
        else { Write-Err "Error al levantar containers. Verifica Docker Desktop." }
    } else {
        Write-Warn "Stack NO levantado: completa el .env y corre:"
        Write-Info "docker compose --env-file `"$envFile`" -f `"$GraphitiLocal\docker-compose.yml`" up -d"
    }
}

# ── 8. Health check ───────────────────────────────────────────────────────
if ($stackUp) {
    Write-Header "Verificando health (espera 10s...)"
    Start-Sleep -Seconds 10
    try {
        $ping = docker exec graphiti-falkordb redis-cli ping 2>&1
        if ($ping -match "PONG") { Write-OK "FalkorDB respondiendo" }
        else { Write-Warn "FalkorDB no responde. Verifica: docker logs graphiti-falkordb" }
    } catch { Write-Warn "No se pudo verificar FalkorDB." }
}

# ── 9. Task Scheduler para backup automático (fix A2) ─────────────────────
Write-Header "Configurando backup automático (Task Scheduler)"
$backupScript = "$GraphitiLocal\scripts\backup-graph.ps1"
if ($hasBackupScript -and (Test-Path $backupScript)) {
    $taskName = "GraphitiBackup"
    $existing = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
    if (-not $existing) {
        $action  = New-ScheduledTaskAction -Execute "powershell.exe" `
            -Argument "-NonInteractive -ExecutionPolicy Bypass -File `"$backupScript`" -OneDrivePath `"$OneDrivePath`""
        # -RepetitionDuration MaxValue: sin él, la repetición no queda registrada en PS 5.1 (fix A2)
        $trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(5) `
            -RepetitionInterval (New-TimeSpan -Hours 4) -RepetitionDuration ([TimeSpan]::MaxValue)
        Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger `
            -Description "Backup del grafo Graphiti cada 4h" -RunLevel Highest | Out-Null
        Write-OK "Task Scheduler: backup cada 4 horas"
        Write-Info "Verifica en unas horas: Get-ScheduledTaskInfo $taskName"
    } else { Write-OK "Task Scheduler ya configurado" }
} else {
    Write-Err "SIN BACKUPS AUTOMÁTICOS: backup-graph.ps1 no está instalado."
    $Warnings += "CRÍTICO: sin backup automático (backup-graph.ps1 ausente)"
}

# ── 9b. Sync de skills al iniciar sesión (fix R8) ─────────────────────────
if (Test-Path $syncSkills) {
    $taskName2 = "ClaudeSkillsSync"
    if (-not (Get-ScheduledTask -TaskName $taskName2 -ErrorAction SilentlyContinue)) {
        $action2  = New-ScheduledTaskAction -Execute "powershell.exe" `
            -Argument "-NonInteractive -ExecutionPolicy Bypass -File `"$syncSkills`" -SkillsRoot `"$DevSetup\claude-skills`" -NoCoworkBuild"
        $trigger2 = New-ScheduledTaskTrigger -AtLogOn
        Register-ScheduledTask -TaskName $taskName2 -Action $action2 -Trigger $trigger2 `
            -Description "Sincroniza skills de Claude al iniciar sesión" | Out-Null
        Write-OK "Skills se sincronizarán en cada inicio de sesión"
    } else { Write-OK "Tarea de sync de skills ya existe" }
}

# ── Resumen ───────────────────────────────────────────────────────────────
Write-Host "`n════════════════════════════════════════════════════" -ForegroundColor White
if ($Warnings.Count -eq 0) { Write-Host " Setup completado sin advertencias" -ForegroundColor Green }
else {
    Write-Host " Setup completado con $($Warnings.Count) advertencia(s):" -ForegroundColor Yellow
    $Warnings | ForEach-Object { Write-Host "   • $_" -ForegroundColor Yellow }
}
Write-Host "════════════════════════════════════════════════════`n" -ForegroundColor White
Write-Info "FalkorDB Browser UI : http://localhost:3000 (solo esta máquina)"
Write-Info "MCP endpoint        : http://localhost:8000/mcp/"
Write-Info "Datos (LOCAL)       : $GraphitiLocal\data\"
Write-Info ".env (LOCAL)        : $envFile"
Write-Info "Backups             : $BackupDir"
Write-Host ""
if ($Local) {
    Write-Warn "Modo single-laptop: los backups quedan en el MISMO disco. Protegen contra"
    Write-Warn "corrupción del grafo, no contra falla del disco — agenda una copia periódica"
    Write-Warn "de $BackupDir a un disco externo o nube, y usa remote git para el vault."
}
Write-Info "Próximos pasos:"
Write-Info "1. Completa el .env si quedó incompleto (key del provider, pins de versión)"
Write-Info "2. SIMULACRO DE RESTORE (auditoría A3): en cuanto haya datos reales,"
Write-Info "   prueba restore-graph.ps1 con un backup — un backup no probado no existe"
Write-Info "3. Copia .graphiti.json a cada proyecto"
Write-Info "4. Cowork: sube claude-skills\_build\dev-skills.zip en Customize > Plugins"
Write-Info "5. Al cambiar de laptop: docker compose stop → backup-graph.ps1 → sync"

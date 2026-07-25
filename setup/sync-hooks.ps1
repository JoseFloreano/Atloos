# ══════════════════════════════════════════════════════════════
#  sync-hooks.ps1 — Instala/sincroniza los hooks de Claude Code
#
#  Fuente de verdad: setup/hooks/ de este repo (ya viaja por OneDrive).
#  Destinos: ~/.claude/hooks/ + cada ~/.claude-*/hooks/ (multi-cuenta),
#            y el cableado en el settings.json de cada config dir.
#
#  Los hooks NO se sincronizan con sync-skills (son otro mecanismo):
#  este script es el equivalente para ellos. Córrelo tras editar un hook
#  y en cada laptop nueva.
#
#  Uso:
#    .\sync-hooks.ps1                 # copia + cablea settings.json
#    .\sync-hooks.ps1 -NoWire         # solo copia los .py
#    .\sync-hooks.ps1 -PythonCmd python3
# ══════════════════════════════════════════════════════════════

param(
    [string]$HooksSource = "",
    [string]$PythonCmd   = "",
    [switch]$NoWire      = $false
)

$ErrorActionPreference = "Stop"
function Write-OK   { param($m) Write-Host "  [OK] $m"   -ForegroundColor Green }
function Write-Warn { param($m) Write-Host "  [WARN] $m" -ForegroundColor Yellow }
function Write-Info { param($m) Write-Host "  [INFO] $m" -ForegroundColor Cyan }

# ── Mapeo hook → evento de Claude Code ────────────────────────────────────
# Si añades un hook nuevo, regístralo aquí o no se cableará.
$HookMap = @(
    @{ File = "validate-graphiti-group-id.py"; Event = "PreToolUse";  Matcher = "mcp__graphiti" }
    @{ File = "mark-code-dirty.py";            Event = "PostToolUse"; Matcher = "Write|Edit|MultiEdit" }
    @{ File = "check-vault-updated.py";        Event = "Stop";        Matcher = $null }
)

if (-not $HooksSource) { $HooksSource = Join-Path $PSScriptRoot "hooks" }
if (-not (Test-Path $HooksSource)) { Write-Error "No existe la carpeta de hooks: $HooksSource"; exit 1 }

# ── Intérprete de Python ──────────────────────────────────────────────────
# En Windows 'python' suele apuntar al stub de Microsoft Store: preferimos 'py'.
if (-not $PythonCmd) {
    $PythonCmd = if (Get-Command py -ErrorAction SilentlyContinue) { "py" }
                 elseif (Get-Command python3 -ErrorAction SilentlyContinue) { "python3" }
                 else { "python" }
}
Write-Info "Intérprete para los hooks: $PythonCmd"

$sourceFiles = Get-ChildItem $HooksSource -Filter *.py -File
if (-not $sourceFiles) { Write-Warn "No hay .py en $HooksSource"; exit 0 }

$configDirs = @("$env:USERPROFILE\.claude") + `
    (Get-ChildItem "$env:USERPROFILE" -Directory -Filter ".claude-*" -Force -ErrorAction SilentlyContinue |
     ForEach-Object { $_.FullName })

foreach ($cfg in $configDirs) {
    if (-not (Test-Path $cfg)) { continue }
    Write-Host "`n▶ $cfg" -ForegroundColor Blue
    $target = Join-Path $cfg "hooks"
    New-Item -ItemType Directory -Force -Path $target | Out-Null

    # ── 1. Copiar (y borrar los que este script instaló y ya no existen) ──
    $manifestPath = Join-Path $target "_sync-hooks.json"
    $previous = @()
    if (Test-Path $manifestPath) {
        try { $previous = (Get-Content $manifestPath -Raw | ConvertFrom-Json).hooks } catch { $previous = @() }
    }
    foreach ($old in $previous) {
        if ($sourceFiles.Name -notcontains $old) {
            Remove-Item (Join-Path $target $old) -Force -ErrorAction SilentlyContinue
            Write-Info "Removido hook obsoleto '$old'"
        }
    }
    foreach ($f in $sourceFiles) { Copy-Item $f.FullName (Join-Path $target $f.Name) -Force }
    @{ syncedAt = (Get-Date -Format 'yyyy-MM-dd HH:mm'); source = $HooksSource
       hooks = @($sourceFiles.Name) } | ConvertTo-Json | Out-File $manifestPath -Encoding UTF8
    Write-OK "$($sourceFiles.Count) hooks copiados"

    if ($NoWire) { continue }

    # ── 2. Cablear settings.json (idempotente) ───────────────────────────
    $settingsPath = Join-Path $cfg "settings.json"
    $raw = if (Test-Path $settingsPath) { Get-Content $settingsPath -Raw } else { "{}" }
    if ([string]::IsNullOrWhiteSpace($raw)) { $raw = "{}" }
    try { $s = $raw | ConvertFrom-Json } catch { Write-Warn "settings.json ilegible, se omite el cableado"; continue }

    if (-not ($s.PSObject.Properties.Name -contains 'hooks')) {
        $s | Add-Member -NotePropertyName hooks -NotePropertyValue ([PSCustomObject]@{})
    }
    $changed = $false

    foreach ($h in $HookMap) {
        if ($sourceFiles.Name -notcontains $h.File) { continue }   # hook no presente en la fuente
        $cmd = "$PythonCmd $((Join-Path $target $h.File) -replace '\\','/')"
        $evt = $h.Event

        if (-not ($s.hooks.PSObject.Properties.Name -contains $evt)) {
            $s.hooks | Add-Member -NotePropertyName $evt -NotePropertyValue @()
        }
        $existing = @($s.hooks.$evt)

        $present = $false
        foreach ($e in $existing) {
            foreach ($inner in @($e.hooks)) { if ($inner.command -eq $cmd) { $present = $true } }
        }
        if ($present) { Write-Info "$($h.File) ya cableado en $evt"; continue }

        $inner = @([PSCustomObject]@{ type = "command"; command = $cmd })
        $entry = if ($h.Matcher) { [PSCustomObject]@{ matcher = $h.Matcher; hooks = $inner } }
                 else            { [PSCustomObject]@{ hooks = $inner } }
        $s.hooks.$evt = @($existing + $entry)
        $changed = $true
        Write-OK "$($h.File) → $evt"
    }

    if ($changed) {
        if (Test-Path $settingsPath) { Copy-Item $settingsPath "$settingsPath.bak" -Force }
        # UTF-8 SIN BOM: un BOM puede romper el parseo de settings.json
        $out = $s | ConvertTo-Json -Depth 25
        [System.IO.File]::WriteAllText($settingsPath, $out, (New-Object System.Text.UTF8Encoding($false)))
        Write-OK "settings.json actualizado (backup en settings.json.bak)"
    } else {
        Write-Info "settings.json ya estaba al día"
    }
}

Write-Host "`nListo. Los hooks aplican en sesiones NUEVAS de Claude Code." -ForegroundColor Green

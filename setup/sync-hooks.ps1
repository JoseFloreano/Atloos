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
    [switch]$NoWire      = $false,
    [switch]$Prune       = $false    # el borrado es opt-in (RFD 10 C1)
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
    @{ File = "memory-flush.py";               Event = "PreCompact";  Matcher = $null }
    # `Bash|PowerShell`, no `Bash` a secas (sprint 7). La herramienta PowerShell
    # manda el comando en el MISMO `tool_input.command` y en Windows va por
    # despliegue progresivo, asi que puede encenderse sin que nadie lo decida:
    # con el matcher viejo, media sesion de una maquina Windows corria sin gate.
    # Arreglar solo esta linea no basta —el hook filtra ADEMAS por `tool_name`,
    # ver HERRAMIENTAS_SHELL en merge-gate-guard.py—; son dos puertas.
    @{ File = "merge-gate-guard.py";           Event = "PreToolUse";  Matcher = "Bash|PowerShell" }
    # Segundo hook en Stop, junto a check-vault-updated.py. Los dos corren, son
    # independientes y el orden lo fija este array (el cableado APENDE, así que
    # check-vault-updated va primero). Ver hooks/tests/test-goal-evidence-guard.py.
    @{ File = "goal-evidence-guard.py";        Event = "Stop";        Matcher = $null }
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
    # Guard por CONJUNTOS (RFD 10 C1, espejo de sync-skills). El guard de la
    # linea ~51 solo cubre la fuente TOTALMENTE vacia; una enumeracion PARCIAL
    # lo pasa y borra igual. Radio de dano menor que en skills (son archivos
    # sueltos, no arboles), pero el patron es el mismo y se cierra igual.
    $faltantes = @($previous | Where-Object { $_ -and $sourceFiles.Name -notcontains $_ })
    if ($faltantes.Count -gt 0) {
        $sourceFiles = Get-ChildItem $HooksSource -Filter *.py -File   # reintento unico
        $faltantes = @($previous | Where-Object { $_ -and $sourceFiles.Name -notcontains $_ })
    }
    if ($faltantes.Count -gt 0) {
        if (-not $Prune) {
            Write-Host "  [HUERFANOS] $($faltantes.Count) hooks instalados y NO en la fuente:" -ForegroundColor Red
            foreach ($f in $faltantes) { Write-Host "      - $f" -ForegroundColor Red }
            Write-Host "  Si los retiraste a proposito:  .\setup\sync-hooks.ps1 -Prune" -ForegroundColor Yellow
        } else {
            foreach ($old in $faltantes) {
                Remove-Item (Join-Path $target $old) -Force -ErrorAction SilentlyContinue
                Write-Info "Podado hook retirado '$old'"
            }
        }
    }
    # .tmp -> rename: los hooks son archivos sueltos, asi que aqui Move-Item
    # -Force SI reemplaza atomicamente y no queda ventana destructiva.
    foreach ($f in $sourceFiles) {
        $dst = Join-Path $target $f.Name
        Copy-Item $f.FullName "$dst.tmp" -Force
        Move-Item "$dst.tmp" $dst -Force
    }
    if ($faltantes.Count -eq 0 -or $Prune) {
        @{ syncedAt = (Get-Date -Format 'yyyy-MM-dd HH:mm'); source = $HooksSource
           hooks = @($sourceFiles.Name) } | ConvertTo-Json | Out-File $manifestPath -Encoding UTF8
    } else {
        Write-Warn "Manifest NO actualizado: sigue recordando los huerfanos."
    }
    $m = if ($previous) { $previous.Count } else { 0 }
    Write-OK "$($sourceFiles.Count) hooks copiados  (manifest: $m)"

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

        # La presencia se mide por COMANDO, pero el matcher tambien es contrato:
        # si cambia (sprint 7, "Bash" -> "Bash|PowerShell") hay que reescribirlo
        # in situ. Sin esto el cableado decia "ya cableado" y dejaba el matcher
        # viejo para siempre: el arreglo estaba en el repo y no llegaba al disco.
        $present = $false
        $reescrito = $false
        foreach ($e in $existing) {
            foreach ($inner in @($e.hooks)) {
                if ($inner.command -eq $cmd) {
                    $present = $true
                    $actual = if ($e.PSObject.Properties.Name -contains 'matcher') { $e.matcher } else { $null }
                    if ($actual -ne $h.Matcher) {
                        if ($h.Matcher) {
                            if ($e.PSObject.Properties.Name -contains 'matcher') { $e.matcher = $h.Matcher }
                            else { $e | Add-Member -NotePropertyName matcher -NotePropertyValue $h.Matcher }
                        } elseif ($e.PSObject.Properties.Name -contains 'matcher') {
                            $e.PSObject.Properties.Remove('matcher')
                        }
                        $changed = $true
                        $reescrito = $true
                        Write-OK "$($h.File) → $evt  (matcher '$actual' → '$($h.Matcher)')"
                    }
                }
            }
        }
        if ($present) {
            if (-not $reescrito) { Write-Info "$($h.File) ya cableado en $evt" }
            continue
        }

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

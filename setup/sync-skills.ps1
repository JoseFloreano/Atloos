# ══════════════════════════════════════════════════════════════
#  sync-skills.ps1 — Instala las skills del REPO en Claude Code
#                    y empaqueta el plugin dev-skills para Cowork
#
#  Fuente ÚNICA:      setup/skills/{shared,claude-code,cowork} de este repo.
#                     El script vive en setup/, así que la resuelve sola: cero
#                     configuración, y funciona igual con OneDrive o sin él.
#  Destinos Code:     ~/.claude/skills/ + cada ~/.claude-*/skills/ (multi-cuenta)
#  Destino Cowork:    setup/_build/dev-skills.zip → subir en Customize→Plugins
#
#  El espejo OneDrive/DevSetup/claude-skills se RETIRÓ (ADR-20260803-skills-
#  fuente-unica): eran dos fuentes de verdad, y el espejo se quedaba atrás sin
#  que nadie lo notara. Ahora los cambios se revisan por diff en git.
#
#  SIEMPRE copia, nunca symlinks (Windows no los soporta bien — H8).
#  Es seguro correrlo cuantas veces quieras: solo gestiona las skills que él
#  mismo instaló (manifest _onedrive-sync.json); no toca tus otras skills.
#
#  Uso:
#    .\sync-skills.ps1
#    .\sync-skills.ps1 -NoCoworkBuild
# ══════════════════════════════════════════════════════════════

param(
    [switch]$NoCoworkBuild = $false
)

$ErrorActionPreference = "Stop"
function Write-OK   { param($m) Write-Host "  [OK] $m"   -ForegroundColor Green }
function Write-Warn { param($m) Write-Host "  [WARN] $m" -ForegroundColor Yellow }
function Write-Info { param($m) Write-Host "  [INFO] $m" -ForegroundColor Cyan }

# ── La fuente es el repo: este script vive en setup/ ──────────────────────
# Sin parámetro ni variable de entorno a propósito. Un interruptor para elegir
# fuente es lo que mantenía vivas las dos, y había que acordarse de usarlo.
$SkillsRoot = Join-Path $PSScriptRoot "skills"
if (-not (Test-Path $SkillsRoot)) {
    Write-Host "  [ERROR] No encuentro $SkillsRoot." -ForegroundColor Red
    Write-Host "          Corre este script desde el repo ClaudeSetup (setup\sync-skills.ps1)." -ForegroundColor Red
    exit 1
}
Write-Info "Fuente: $SkillsRoot"

# ── Recolectar skills fuente (carpetas con SKILL.md) ──────────────────────
function Get-Skills { param($cats)
    $found = @{}
    foreach ($c in $cats) {
        $dir = Join-Path $SkillsRoot $c
        if (-not (Test-Path $dir)) { continue }
        Get-ChildItem $dir -Directory | Where-Object {
            Test-Path (Join-Path $_.FullName "SKILL.md")
        } | ForEach-Object {
            # Orden de $cats importa: la última categoría gana en conflicto de nombre
            $found[$_.Name] = $_.FullName
        }
    }
    return $found
}

# ── 1. Claude Code: copiar shared + claude-code a cada config dir ─────────
Write-Host "`n▶ Sincronizando skills para Claude Code" -ForegroundColor Blue
$codeSkills = Get-Skills @("shared", "claude-code")   # claude-code gana conflictos

$configDirs = @("$env:USERPROFILE\.claude") + `
    (Get-ChildItem "$env:USERPROFILE" -Directory -Filter ".claude-*" -Force -ErrorAction SilentlyContinue |
     ForEach-Object { $_.FullName })

foreach ($cfg in $configDirs) {
    if (-not (Test-Path $cfg)) { continue }
    $target = Join-Path $cfg "skills"
    New-Item -ItemType Directory -Force -Path $target | Out-Null

    # Manifest: qué skills gestiona este script (para poder borrar las removidas).
    # Conserva el nombre heredado a propósito: renombrarlo dejaría huérfano el
    # manifest de las máquinas ya instaladas y las skills retiradas se quedarían
    # ahí para siempre. El nombre miente; romper la limpieza sería peor.
    $manifestPath = Join-Path $target "_onedrive-sync.json"
    $previous = @()
    if (Test-Path $manifestPath) {
        $previous = (Get-Content $manifestPath -Raw | ConvertFrom-Json).skills
    }

    # Borrar skills gestionadas que ya no existen en la fuente
    foreach ($old in $previous) {
        if (-not $codeSkills.ContainsKey($old)) {
            Remove-Item (Join-Path $target $old) -Recurse -Force -ErrorAction SilentlyContinue
            Write-Info "Removida skill obsoleta '$old' de $target"
        }
    }

    # Copiar (reemplazo limpio por skill)
    foreach ($name in $codeSkills.Keys) {
        $dest = Join-Path $target $name
        if (Test-Path $dest) { Remove-Item $dest -Recurse -Force }
        Copy-Item $codeSkills[$name] $dest -Recurse
    }

    @{ syncedAt = (Get-Date -Format 'yyyy-MM-dd HH:mm'); source = $SkillsRoot;
       skills = @($codeSkills.Keys) } | ConvertTo-Json | Out-File $manifestPath -Encoding UTF8
    Write-OK "$($codeSkills.Count) skills → $target"
}

# ── 1b. Scripts auxiliares → ~/.claude/scripts/ ───────────────────────────
# Las skills (adr-writer, project-resume, vault-drift-audit) invocan
# adr-index.py por ruta absoluta, porque corren desde el cwd de cualquier
# proyecto. Antes esa ruta era la del repo DENTRO de OneDrive: inerte en modo
# single-laptop, y dependiente del arbol de carpetas de UNA laptop. Ahora la
# ruta estable es ~/.claude/scripts/ y este paso la materializa en cada
# maquina, igual que sync-hooks hace con ~/.claude/hooks/.
$scriptsSource = Join-Path $PSScriptRoot "scripts"
if (Test-Path $scriptsSource) {
    Write-Host "`n▶ Instalando scripts auxiliares" -ForegroundColor Blue
    foreach ($cfg in $configDirs) {
        $target = Join-Path $cfg "scripts"
        New-Item -ItemType Directory -Force -Path $target | Out-Null
        $py = Get-ChildItem $scriptsSource -Filter "*.py" -File
        foreach ($f in $py) { Copy-Item $f.FullName $target -Force }
        Write-OK "$($py.Count) scripts → $target"
    }
}

# ── 2. Cowork: empaquetar plugin dev-skills (shared + cowork) ─────────────
if (-not $NoCoworkBuild) {
    Write-Host "`n▶ Empaquetando plugin dev-skills para Cowork" -ForegroundColor Blue
    $coworkSkills = Get-Skills @("shared", "cowork")   # cowork gana conflictos

    $buildRoot  = Join-Path $PSScriptRoot "_build"   # artefacto: gitignorado
    $pluginDir  = Join-Path $buildRoot "dev-skills"
    if (Test-Path $pluginDir) { Remove-Item $pluginDir -Recurse -Force }
    New-Item -ItemType Directory -Force -Path (Join-Path $pluginDir ".claude-plugin") | Out-Null
    $skillsDir = Join-Path $pluginDir "skills"
    New-Item -ItemType Directory -Force -Path $skillsDir | Out-Null

    foreach ($name in $coworkSkills.Keys) {
        Copy-Item $coworkSkills[$name] (Join-Path $skillsDir $name) -Recurse
    }

    # B4 (instalacion single-laptop): Out-File -Encoding UTF8 en PS 5.1 escribe BOM y RFC 8259 lo
    # prohíbe en JSON — el validador de plugins de Cowork lo rechaza. Sin BOM:
    $manifestJson = @{ name = "dev-skills"
       description = "Skills personales de desarrollo (fuente: setup/skills del repo ClaudeSetup)"
       version = (Get-Date -Format 'yyyy.MM.dd')
    } | ConvertTo-Json
    [IO.File]::WriteAllText((Join-Path $pluginDir ".claude-plugin\plugin.json"), $manifestJson,
        (New-Object System.Text.UTF8Encoding($false)))

    # B3 (instalacion single-laptop): Compress-Archive en PS 5.1 escribe '\' en las rutas del zip
    # (el spec ZIP exige '/'; Cowork rechaza el archivo). Zip manual con '/'.
    # Verificado además: el plugin root va en la RAÍZ del zip, sin carpeta envolvente.
    $zipPath = Join-Path $buildRoot "dev-skills.zip"
    if (Test-Path $zipPath) { Remove-Item $zipPath -Force }
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $zip = [IO.Compression.ZipFile]::Open($zipPath, 'Create')
    try {
        Get-ChildItem $pluginDir -Recurse -File | ForEach-Object {
            $rel   = $_.FullName.Substring(([string]$pluginDir).Length).TrimStart('\', '/')
            $entry = $zip.CreateEntry(($rel -replace '\\', '/'), 'Optimal')
            $out   = $entry.Open()
            $bytes = [IO.File]::ReadAllBytes($_.FullName)
            $out.Write($bytes, 0, $bytes.Length)
            $out.Dispose()
        }
    } finally { $zip.Dispose() }
    Write-OK "$($coworkSkills.Count) skills → $zipPath"
    Write-Info "Instalar/actualizar en Cowork: desktop app → Customize → Plugins → subir dev-skills.zip"
}

Write-Host "`nListo. Las sesiones nuevas de Claude Code ya ven las skills." -ForegroundColor Green

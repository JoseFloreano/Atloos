# ══════════════════════════════════════════════════════════════
#  sync-skills.ps1 — Sincroniza skills desde OneDrive a Claude Code
#                    y empaqueta el plugin dev-skills para Cowork
#
#  Fuente de verdad:  OneDrive/DevSetup/claude-skills/{shared,claude-code,cowork}
#  Destinos Code:     ~/.claude/skills/ + cada ~/.claude-*/skills/ (multi-cuenta)
#  Destino Cowork:    claude-skills/_build/dev-skills(.zip) → subir en Customize→Plugins
#
#  SIEMPRE copia, nunca symlinks (OneDrive en Windows no los soporta — H8).
#  Es seguro correrlo cuantas veces quieras: solo gestiona las skills que él
#  mismo instaló (manifest _onedrive-sync.json); no toca tus otras skills.
#
#  Uso:
#    .\sync-skills.ps1
#    .\sync-skills.ps1 -SkillsRoot "D:\OneDrive\DevSetup\claude-skills"
#    .\sync-skills.ps1 -NoCoworkBuild
# ══════════════════════════════════════════════════════════════

param(
    [string]$SkillsRoot = "",
    [switch]$NoCoworkBuild = $false
)

$ErrorActionPreference = "Stop"
function Write-OK   { param($m) Write-Host "  [OK] $m"   -ForegroundColor Green }
function Write-Warn { param($m) Write-Host "  [WARN] $m" -ForegroundColor Yellow }
function Write-Info { param($m) Write-Host "  [INFO] $m" -ForegroundColor Cyan }

# ── Resolver la carpeta de skills (OneDrive o local single-laptop) ────────
if (-not $SkillsRoot) {
    # B2 (instalacion single-laptop): if-como-expresión con elseif en línea nueva NO parsea en PS —
    # el salto de línea cierra la expresión. Forma de sentencia, siempre.
    $od = $null
    if ($env:OneDrive -and (Test-Path $env:OneDrive)) { $od = $env:OneDrive }
    elseif (Test-Path "$env:USERPROFILE\OneDrive") { $od = "$env:USERPROFILE\OneDrive" }
    if (-not $od) {
        $od = $env:USERPROFILE
        Write-Info "OneDrive no encontrado — usando raíz LOCAL (single-laptop): $od\DevSetup\claude-skills"
    }
    $SkillsRoot = Join-Path $od "DevSetup\claude-skills"
}

# ── Primera vez: crear estructura y seed desde el repo ────────────────────
$categories = @("shared", "claude-code", "cowork")
if (-not (Test-Path $SkillsRoot)) {
    Write-Info "Creando estructura en $SkillsRoot"
    foreach ($c in $categories + @("_template")) {
        New-Item -ItemType Directory -Force -Path (Join-Path $SkillsRoot $c) | Out-Null
    }
    # Seed: si el script corre desde el repo, copiar plantilla y skills iniciales
    $repoSkills = Join-Path $PSScriptRoot "skills"
    if (Test-Path $repoSkills) {
        Copy-Item "$repoSkills\*" $SkillsRoot -Recurse -Force
        Write-OK "Seed inicial copiado desde el repo ($repoSkills)"
    }
}

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

    # Manifest: qué skills gestiona este script (para poder borrar las removidas)
    $manifestPath = Join-Path $target "_onedrive-sync.json"
    $previous = @()
    if (Test-Path $manifestPath) {
        $previous = (Get-Content $manifestPath -Raw | ConvertFrom-Json).skills
    }

    # Borrar skills gestionadas que ya no existen en OneDrive
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

    $buildRoot  = Join-Path $SkillsRoot "_build"
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
       description = "Skills personales de desarrollo (sincronizadas desde DevSetup/claude-skills)"
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

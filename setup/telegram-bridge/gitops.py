#!/usr/bin/env python3
"""
gitops.py — Operaciones de git y worktrees para el puente Telegram (T2).

No sabe nada de Telegram: recibe rutas y devuelve datos. Toda la política de
"quién puede hacer qué" vive en el daemon; aquí solo está el cómo.

Modelo (RFD 02 v2 §4): **1 conversación = 1 rama = 1 worktree**.

    Repo del usuario (OneDrive)     Worktrees del bot (LOCAL, fuera de OneDrive)
    main + su árbol de trabajo      %LOCALAPPDATA%\\claude-tg-worktrees\\<proj>\\<slug>
      ← el bot NUNCA lo toca          ← rama tg/<fecha>-<slug>

Los worktrees viven fuera de OneDrive a propósito: un checkout completo dentro
de la carpeta sincronizada provoca tormentas de sync y lecturas de bytes
obsoletos (mismo criterio que el fix A4 y el `.git` del vault).
"""
import asyncio
import os
import re
import shutil
import stat
import unicodedata
from datetime import datetime
from pathlib import Path

GIT_TIMEOUT = 120          # segundos por comando de git
BRANCH_PREFIX = "tg"
PROGRESS_DIR = ".tg"       # canal de checkpoints; excluido de commits


class GitError(Exception):
    """Fallo de un comando de git, con la salida ya recortada."""


def worktrees_root() -> Path:
    """Raíz LOCAL de los worktrees. Nunca dentro de OneDrive."""
    base = os.environ.get("LOCALAPPDATA") or os.path.join(
        os.path.expanduser("~"), ".local", "share")
    return Path(base) / "claude-tg-worktrees"


def slugify(text: str, max_len: int = 32) -> str:
    """Texto libre → slug apto para nombre de rama y de carpeta."""
    text = unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode()
    text = re.sub(r"[^\w\s-]", "", text.lower())
    text = re.sub(r"[\s_]+", "-", text).strip("-")
    text = re.sub(r"-{2,}", "-", text)
    return (text[:max_len].rstrip("-")) or "tarea"


def branch_name(slug: str, today: str = "") -> str:
    """tg/YYYYMMDD-slug — fecha primero para que ordenen solas."""
    stamp = today or datetime.now().strftime("%Y%m%d")
    return f"{BRANCH_PREFIX}/{stamp}-{slug}"


# ── Ejecución ─────────────────────────────────────────────────────────────
async def run(args: list, cwd: str, timeout: int = GIT_TIMEOUT) -> tuple:
    """Ejecuta un comando y devuelve (returncode, stdout, stderr) ya decodificados."""
    proc = await asyncio.create_subprocess_exec(
        *args, cwd=cwd,
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    try:
        out, err = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        raise GitError(f"'{' '.join(args[:3])}…' superó {timeout}s")
    return (proc.returncode,
            (out or b"").decode("utf-8", "replace").strip(),
            (err or b"").decode("utf-8", "replace").strip())


async def git(args: list, cwd: str, check: bool = True, timeout: int = GIT_TIMEOUT) -> str:
    rc, out, err = await run(["git"] + args, cwd, timeout)
    if check and rc != 0:
        raise GitError(f"git {' '.join(args[:2])}: {(err or out)[:400]}")
    return out


# ── Consultas ─────────────────────────────────────────────────────────────
async def list_worktrees(repo: str) -> list:
    """[{path, branch, head}] a partir de `git worktree list --porcelain`."""
    out = await git(["worktree", "list", "--porcelain"], repo)
    entries, cur = [], {}
    for line in out.splitlines():
        if line.startswith("worktree "):
            if cur:
                entries.append(cur)
            cur = {"path": line[9:].strip(), "branch": "", "head": ""}
        elif line.startswith("HEAD "):
            cur["head"] = line[5:].strip()
        elif line.startswith("branch "):
            cur["branch"] = line[7:].strip().replace("refs/heads/", "")
    if cur:
        entries.append(cur)
    return entries


async def branch_exists(repo: str, branch: str) -> bool:
    rc, _, _ = await run(["git", "rev-parse", "--verify", f"refs/heads/{branch}"], repo)
    return rc == 0


async def default_branch(repo: str) -> str:
    """Rama principal del repo (main/master), sin adivinar a ciegas."""
    for cand in ("main", "master"):
        if await branch_exists(repo, cand):
            return cand
    return (await git(["rev-parse", "--abbrev-ref", "HEAD"], repo)) or "main"


async def has_remote(repo: str) -> bool:
    return bool(await git(["remote"], repo, check=False))


async def is_clean(path: str) -> bool:
    return not (await git(["status", "--porcelain"], path))


async def head_sha(path: str, short: bool = True) -> str:
    args = ["rev-parse"] + (["--short"] if short else []) + ["HEAD"]
    return await git(args, path)


# ── Ciclo de vida del worktree ────────────────────────────────────────────
async def create_worktree(repo: str, project: str, slug: str) -> dict:
    """Crea rama + worktree aislados. Devuelve {branch, path}.

    Copia el CLAUDE.md del repo original: está gitignorado (es artefacto de
    instancia), así que el worktree nacería SIN Memory Rules — el agente
    perdería el aislamiento de memoria del proyecto.
    """
    branch = branch_name(slug)
    dest = worktrees_root() / project / f"{datetime.now():%Y%m%d}-{slug}"

    if await branch_exists(repo, branch):
        for wt in await list_worktrees(repo):
            if wt["branch"] == branch:
                raise GitError(f"La rama {branch} ya está montada en {wt['path']}")
        branch = f"{branch}-{datetime.now():%H%M%S}"       # colisión de nombre
        dest = dest.with_name(dest.name + f"-{datetime.now():%H%M%S}")

    if dest.exists():
        raise GitError(f"El destino ya existe: {dest}")
    dest.parent.mkdir(parents=True, exist_ok=True)

    base = await default_branch(repo)
    await git(["worktree", "add", "-b", branch, str(dest), base], repo)

    # CLAUDE.md: gitignorado, hay que copiarlo a mano o se pierden las Memory Rules
    src_md = Path(repo) / "CLAUDE.md"
    claude_md = False
    if src_md.is_file():
        try:
            shutil.copyfile(src_md, dest / "CLAUDE.md")
            claude_md = True
        except OSError:
            pass

    # .tg/ (canal de checkpoints) fuera de los commits. En un worktree `.git`
    # es un ARCHIVO apuntador, así que preguntamos a git dónde vive su
    # info/exclude en vez de asumir el layout.
    try:
        (dest / PROGRESS_DIR).mkdir(exist_ok=True)
        info = await git(["rev-parse", "--git-path", "info/exclude"], str(dest))
        exclude_path = Path(info)
        if not exclude_path.is_absolute():
            exclude_path = dest / info
        exclude_path.parent.mkdir(parents=True, exist_ok=True)
        prev = exclude_path.read_text(encoding="utf-8") if exclude_path.is_file() else ""
        if PROGRESS_DIR not in prev:
            exclude_path.write_text(prev.rstrip("\n") + f"\n{PROGRESS_DIR}/\n",
                                    encoding="utf-8")
    except (OSError, GitError):
        pass

    return {"branch": branch, "path": str(dest), "claude_md": claude_md, "base": base}


def _force_rmtree(path: Path) -> bool:
    """Borra un árbol quitando el atributo de solo-lectura por el camino.

    Necesario porque el repo del usuario vive en OneDrive: Files On-Demand
    convierte los archivos internos de `.git/worktrees/**` en *reparse points*
    marcados **ReadOnly**, y el `unlink` de git falla con "Permission denied".
    Limpiar el bit y reintentar es lo que hace `Remove-Item -Force`.
    """
    def _on_error(func, target, _exc):
        try:
            os.chmod(target, stat.S_IWRITE)
            func(target)
        except OSError:
            pass

    try:
        shutil.rmtree(path, onerror=_on_error)
        return not path.exists()
    except OSError:
        return False


async def _cleanup_admin_dir(repo: str, worktree_path: str) -> str:
    """Quita el directorio administrativo `.git/worktrees/<n>` que git no pudo
    borrar, y desregistra con `prune`. Devuelve una nota o cadena vacía."""
    name = Path(worktree_path).name
    try:
        common = await git(["rev-parse", "--git-common-dir"], repo, check=False)
        base = Path(common) if common and Path(common).is_absolute() else Path(repo) / ".git"
        admin = base / "worktrees" / name
        if admin.exists() and not _force_rmtree(admin):
            return f"quedó {admin} (bórralo a mano)"
        await git(["worktree", "prune"], repo, check=False)
        return ""
    except (OSError, GitError) as exc:
        return f"limpieza administrativa incompleta: {exc}"


async def has_tracked_changes(worktree: str) -> bool:
    """¿Hay trabajo real sin commitear? Los archivos sin trackear no cuentan:
    correr tests deja `__pycache__`, `.pytest_cache`, `node_modules`… y eso no
    es trabajo que perder."""
    out = await git(["status", "--porcelain"], worktree, check=False)
    return any(line and not line.startswith("??") for line in out.splitlines())


async def remove_worktree(repo: str, path: str, branch: str = "",
                          merged: bool = False) -> dict:
    """Quita el worktree y su rama.

    - Se niega si quedan cambios sin commitear en archivos TRACKEADOS (eso sí
      sería perder trabajo); la basura de los tests no bloquea.
    - Tras un **squash merge** los commits de la rama no son ancestros de main,
      así que `git branch -d` la ve como "sin mergear". Por eso el daemon pasa
      `merged=True` cuando sabe que se integró, y solo entonces se usa `-D`.
    """
    result = {"worktree_removed": False, "branch_deleted": False,
              "branch_status": "", "notes": []}

    if path and Path(path).exists():
        try:
            if await has_tracked_changes(path):
                result["notes"].append(
                    "hay cambios sin commitear: no se elimina (haz /commit o descarta a mano)")
                return result
        except GitError as exc:
            result["notes"].append(f"no se pudo comprobar el estado: {exc}")
            return result
        # --force: solo quedan archivos sin trackear (artefactos de tests)
        rc, _, err = await run(["git", "worktree", "remove", "--force", path], repo)
        if rc != 0:
            # El checkout puede haberse borrado igualmente y fallar solo al
            # limpiar `.git/worktrees/<n>` (OneDrive lo deja ReadOnly). Si el
            # árbol ya no está, el trabajo está hecho: rematamos la parte
            # administrativa nosotros en vez de reportar un fallo engañoso.
            if Path(path).exists():
                result["notes"].append(f"worktree no removido: {err[:200]}")
                return result
            nota = await _cleanup_admin_dir(repo, path)
            if nota:
                result["notes"].append(nota)
        result["worktree_removed"] = True
        if rc == 0:
            # Aun con éxito, git deja restos si OneDrive bloqueó algún archivo
            nota = await _cleanup_admin_dir(repo, path)
            if nota:
                result["notes"].append(nota)
    else:
        await git(["worktree", "prune"], repo, check=False)
        result["worktree_removed"] = True

    if branch:
        if not await branch_exists(repo, branch):
            # Ya no está (borrada a mano, o por `gh pr merge --delete-branch`).
            # Decir "conservada" aquí sería mentir sobre el estado real.
            result["branch_status"] = "ya no existía"
            return result
        rc, _, _ = await run(["git", "branch", "-d", branch], repo)
        if rc == 0:
            result["branch_deleted"] = True
            result["branch_status"] = "borrada"
        elif merged:
            # Tras un squash, `-d` no la reconoce como integrada: por eso -D,
            # pero solo cuando el daemon confirma que hubo merge.
            rc2, _, err2 = await run(["git", "branch", "-D", branch], repo)
            if rc2 == 0:
                result["branch_deleted"] = True
                result["branch_status"] = "borrada (squash merge)"
            else:
                result["branch_status"] = f"conservada: {err2[:120]}"
        else:
            result["branch_status"] = "conservada (sin mergear; se borra tras /merge)"
    return result


async def reconcile(repo: str, known: list) -> dict:
    """Contrasta el estado guardado con los worktrees reales.

    Devuelve huérfanos en ambos sentidos. NO borra nada: reportar y que decida
    el humano (RFD §4.4).
    """
    real = {wt["path"].replace("/", os.sep).lower(): wt for wt in await list_worktrees(repo)}
    known_paths = {p.replace("/", os.sep).lower() for p in known if p}
    return {
        "missing_on_disk": sorted(p for p in known_paths if p not in real),
        "untracked_on_disk": sorted(
            wt["path"] for key, wt in real.items()
            if key not in known_paths and BRANCH_PREFIX + "/" in (wt["branch"] or "")),
    }


# ── Operaciones sobre la rama de trabajo ──────────────────────────────────
async def diff_summary(worktree: str) -> dict:
    """Resumen y diff completo del trabajo no commiteado + commits de la rama."""
    await git(["add", "-A"], worktree, check=False)      # incluir archivos nuevos
    stat = await git(["diff", "--cached", "--stat"], worktree, check=False)
    full = await git(["diff", "--cached"], worktree, check=False)
    return {"stat": stat, "full": full, "has_changes": bool(stat.strip())}


async def commits_ahead(repo_or_wt: str, branch: str, base: str) -> list:
    out = await git(["log", "--oneline", f"{base}..{branch}"], repo_or_wt, check=False)
    return [l for l in out.splitlines() if l.strip()]


async def commit_all(worktree: str, message: str) -> dict:
    """Commit de todo lo pendiente en la rama del worktree."""
    await git(["add", "-A"], worktree)
    if not (await git(["diff", "--cached", "--name-only"], worktree)).strip():
        return {"committed": False, "reason": "no hay cambios que commitear"}
    await git(["-c", "core.autocrlf=false", "commit", "-m", message], worktree)
    return {"committed": True,
            "sha": await git(["rev-parse", "--short", "HEAD"], worktree),
            "subject": await git(["log", "-1", "--pretty=%s"], worktree)}


async def push_branch(worktree: str, branch: str) -> dict:
    """Publica la rama. Requiere remoto configurado."""
    if not await has_remote(worktree):
        return {"pushed": False, "reason": "el repo no tiene remoto configurado"}
    await git(["push", "-u", "origin", branch], worktree, timeout=180)
    return {"pushed": True}


async def ensure_pr(worktree: str, branch: str, base: str, title: str) -> dict:
    """Crea el PR si no existe (requiere gh); devuelve su URL si la hay."""
    gh = shutil.which("gh")
    if not gh:
        return {"pr": False, "reason": "gh no está instalado"}
    rc, out, _ = await run([gh, "pr", "view", branch, "--json", "url,state",
                            "-q", ".url"], worktree, timeout=90)
    if rc == 0 and out.strip():
        return {"pr": True, "url": out.strip(), "created": False}
    rc, out, err = await run([gh, "pr", "create", "--base", base, "--head", branch,
                              "--title", title, "--body",
                              "Rama creada desde el puente Telegram (T2)."],
                             worktree, timeout=120)
    if rc != 0:
        return {"pr": False, "reason": (err or out)[:200]}
    url = next((l for l in out.splitlines() if l.startswith("http")), out.strip())
    return {"pr": True, "url": url, "created": True}


async def merge_squash(repo: str, branch: str, base: str, message: str,
                       pr_url: str = "") -> dict:
    """Integra la rama en la principal.

    Vía PR si existe (ocurre en el remoto: NO toca el árbol del usuario).
    Si no hay PR, merge local — y ahí sí hace falta el árbol del usuario, así
    que se exige limpio y en la rama base; si no, se rechaza sin tocar nada.
    """
    if pr_url:
        gh = shutil.which("gh")
        if gh:
            # SIN --delete-branch: gh intentaría borrar también la rama LOCAL,
            # que está montada en el worktree del bot; git se niega, gh sale con
            # error y un merge EXITOSO se reportaría como fallido. La limpieza
            # de rama y worktree es responsabilidad de /done, que sabe hacerla.
            rc, out, err = await run([gh, "pr", "merge", branch, "--squash"],
                                     repo, timeout=180)
            if rc == 0:
                return {"merged": True, "via": "pr", "detail": out[:300]}
            # Antes de darlo por fallido, preguntar al remoto: gh puede fallar
            # por un paso posterior al merge y el PR estar ya integrado.
            rc2, state, _ = await run([gh, "pr", "view", branch, "--json", "state",
                                       "-q", ".state"], repo, timeout=90)
            if rc2 == 0 and state.strip().upper() == "MERGED":
                return {"merged": True, "via": "pr",
                        "detail": "el PR quedó integrado (gh devolvió error en un paso posterior)"}
            return {"merged": False, "via": "pr", "reason": (err or out)[:300]}

    # Merge local: es el ÚNICO punto en que T2 escribe en el árbol del usuario,
    # y solo porque `main` no puede actualizarse desde otro worktree. Por eso se
    # exige limpio: hacerlo con cambios encima mezclaría su trabajo con el del bot.
    current = await git(["rev-parse", "--abbrev-ref", "HEAD"], repo)
    if current != base:
        return {"merged": False, "via": "local",
                "reason": f"tu árbol está en la rama '{current}', no en '{base}'. "
                          f"Cámbiate a '{base}' en la laptop y repite /merge."}
    if not await is_clean(repo):
        return {"merged": False, "via": "local",
                "reason": "tu árbol de trabajo tiene cambios sin commitear y el "
                          "merge local escribiría encima.\n\nOpciones: (a) commitea "
                          "o guarda tus cambios en la laptop y repite /merge; o "
                          "(b) configura un remoto y así el merge irá por PR, que "
                          "no toca tu árbol.\n\nMientras tanto la rama del bot "
                          "sigue intacta: nada se ha perdido."}

    # A1 — un `merge --squash` en conflicto deja el índice y el árbol del
    # usuario a medias. Como es SU árbol, no podemos abandonarlo así: se
    # revierte al estado previo y se informa. `reset --merge` preserva los
    # cambios locales no relacionados; si ni eso funciona, se dice claramente.
    rc, out, err = await run(["git", "merge", "--squash", branch], repo)
    if rc != 0:
        limpio = False
        for recuperacion in (["merge", "--abort"], ["reset", "--merge"]):
            rc2, _, _ = await run(["git"] + recuperacion, repo)
            if rc2 == 0:
                limpio = True
                break
        return {"merged": False, "via": "local",
                "reason": (f"conflictos al integrar: {(err or out)[:200]}\n\n"
                           + ("Tu árbol quedó como estaba (revertido)."
                              if limpio else
                              "⚠️ NO pude revertir automáticamente: revisa "
                              "`git status` en la laptop antes de seguir."))}

    rc, out, err = await run(["git", "-c", "core.autocrlf=false", "commit",
                              "-m", message], repo)
    if rc != 0:
        await run(["git", "reset", "--merge"], repo)     # deshacer el squash preparado
        return {"merged": False, "via": "local",
                "reason": f"no se pudo commitear la integración: {(err or out)[:200]}"}
    return {"merged": True, "via": "local",
            "sha": await git(["rev-parse", "--short", "HEAD"], repo)}

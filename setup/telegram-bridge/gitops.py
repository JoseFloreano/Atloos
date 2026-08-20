#!/usr/bin/env python3
"""
gitops.py — Operaciones de git y worktrees para el puente Telegram (T2).

No sabe nada de Telegram: recibe rutas y devuelve datos. Toda la política de
"quién puede hacer qué" vive en el daemon; aquí solo está el cómo.

Modelo (`ADR-20260801-puente-telegram` (worktree por conversación)): **1 conversación = 1 rama = 1 worktree**.

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
async def run(args: list, cwd: str, timeout: int = GIT_TIMEOUT, env: dict = None) -> tuple:
    """Ejecuta un comando y devuelve (returncode, stdout, stderr) ya decodificados.

    `env=None` (default) hereda el entorno del proceso actual, igual que antes
    de que este parámetro existiera — los llamadores que no lo pasan no cambian
    de comportamiento. Existe para que `cmd_test` pueda inyectar `CLAUDE_TG_BOT`
    en el subproceso de test sin tocar el resto de usos de `run`.
    """
    proc = await asyncio.create_subprocess_exec(
        *args, cwd=cwd, env=env,
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


# Secciones que se SUSTITUYEN en la versión bot. Filtrar línea a línea no sirve:
# los puntos numerados ocupan varias líneas y quitar la primera deja
# continuaciones huérfanas — más confusas que la regla original.
BOT_SECCIONES_FUERA = ("memory rules",)

# ── Y por qué "sustituir la sección" NO bastaba (arreglado 2026-08-18) ────
# El `CLAUDE.md` de Atloos tiene TRES encabezados `##` y «Memory Rules» es el
# ÚLTIMO. Como el corte va de un `## ` al siguiente, ese bloque no terminaba:
# llegaba hasta el final del fichero. Sustituirlo se llevaba por delante todo lo
# que el snippet escribe DESPUÉS de las reglas numeradas — párrafos sueltos, sin
# encabezado propio. Medido: **3 443 → 1 254 caracteres**.
#
# Lo que se perdía no eran las órdenes imposibles que este recorte existe para
# quitar, sino TRES reglas que el bot sí puede cumplir, y de las caras:
#   · el disparador de Graphify antes de la primera búsqueda de la sesión;
#   · «para integrar CUALQUIER rama a main, el criterio es workstream-merge-gate»;
#   · la higiene de salida (−91 % a −99 % de bytes), que es la regla que más
#     factura mueve en una sesión por Telegram.
# Y el sello `snippet vN · fecha`, sin el cual una copia no puede decir qué
# versión lleva.
#
# El arreglo NO es cortar por otro sitio: es **partir la sección en dos**. La
# lista numerada se sustituye entera (el motivo original sigue en pie); la cola
# de párrafos se filtra uno a uno, y solo se cae el que nombra algo que en el
# puente no existe. Un párrafo es la unidad correcta porque es como el snippet
# los escribe: separados por línea en blanco, cada uno una regla completa.
#
# `graphiti` y `graphify` son cosas distintas y solo la primera se va: el MCP no
# está en el bot, pero el CLI de grafo sí puede correr en su worktree.
BOT_PARRAFOS_FUERA = (
    "search_facts", "group_ids", "add_episode", "graphiti",
    "_project.md", "10-projects", "nota de sesión", "session-close",
    "memory-keeper", "adr-writer", "codebase-map",
)

# La lista numerada de reglas: un párrafo cuyo primer renglón abre con `N.`.
_NUMERADA = re.compile(r"^\s*\d+\.\s")

BOT_REGLAS = """## Memory Rules — versión puente Telegram

1. **No escribas en el vault.** El contexto del proyecto te lo inyecta el daemon
   al abrir la conversación, y la nota de sesión la escribe él al hacer `/done`.
2. Trabajas en un **worktree aislado**: el árbol del usuario no se toca nunca.
3. Si algo merece quedar registrado, **dilo en tu respuesta** — el daemon lo
   recoge; no intentes guardarlo tú.
4. Un hecho almacenado que contradiga el código actual: manda el presente.
5. **Lo pedido por chat se entrega por chat.** El usuario te lee por Telegram:
   un archivo que escribas para "entregárselo" no lo verá nunca. Los archivos
   son para el trabajo que se commitea (código, docs del repo), no para
   responder. Si pide explícitamente un archivo, la primera línea de tu
   respuesta debe ser `ARCHIVO: nombre.md` y el puente lo adjunta.

<!-- Versión BOT: se han omitido las reglas de vault y de Graphiti del CLAUDE.md
     original porque aquí no aplican (no hay MCP, y el vault lo gestiona el
     daemon). El resto de convenciones del proyecto siguen vigentes. -->
"""


def bot_claude_md(texto: str) -> str:
    """CLAUDE.md del proyecto → versión para el bot (ADR-20260801-bot-memoria-y-perfil).

    Conserva las convenciones del proyecto —que es lo que hace útil el
    CLAUDE.md— y sustituye **la lista de reglas** de Memory Rules por una que el
    bot sí puede cumplir, **conservando la cola de párrafos** que sigue siendo
    válida (ver `BOT_PARRAFOS_FUERA` arriba: hasta el 08-18 esa cola se perdía
    entera). Si el CLAUDE.md no tiene esa sección (otro proyecto, otra
    estructura), se devuelve tal cual: no inventamos recortes.

    **No lanza nunca.** `create_worktree` la llama dentro de un `try` que solo
    captura `OSError`, así que una excepción aquí impediría abrir CUALQUIER
    conversación nueva del bot. Ante lo inesperado devuelve el texto original:
    un CLAUDE.md con tres órdenes que el bot no puede cumplir es un mal día;
    un daemon que no abre conversaciones es un daemon caído.
    """
    # `str(texto or "")` y no `texto or ""`: la rama de rescate hace `.rstrip()`,
    # y si lo que llegó no era una cadena esa llamada lanza DENTRO del `except`
    # — o sea que el envoltorio que existe para no lanzar, lanzaba. Se normaliza
    # antes de entrar, que es el único sitio donde el arreglo es total.
    texto = str(texto) if texto else ""
    try:
        return _bot_claude_md(texto)
    except Exception:
        return texto.rstrip() + "\n"


def _seccion_bot(bloque):
    """La sección de Memory Rules → su versión bot, párrafo a párrafo.

    Se parte por línea en blanco porque es como el snippet escribe las reglas de
    la cola: cada párrafo es una regla completa, así que ninguna se queda a
    medias — que era la objeción original a filtrar línea a línea, y sigue
    siendo válida contra ESA unidad, no contra esta.
    """
    conservados = []
    for parrafo in re.split(r"\n\s*\n", bloque):
        if not parrafo.strip():
            continue
        primera = parrafo.lstrip().splitlines()[0]
        if primera.lstrip().startswith("#"):
            continue                      # el encabezado: lo pone BOT_REGLAS
        if _NUMERADA.match(primera):
            continue                      # la lista de reglas: se sustituye entera
        if any(m in parrafo.lower() for m in BOT_PARRAFOS_FUERA):
            continue                      # nombra algo que en el puente no existe
        conservados.append(parrafo.strip())
    return (BOT_REGLAS.rstrip() + "\n\n" + "\n\n".join(conservados)).rstrip() + "\n"


def _bot_claude_md(texto):
    """El trabajo real. Separado para que el envoltorio de arriba no pueda
    lanzar y para que el arnés pueda ejercer ESTA función sin la red debajo —
    un fallo tapado por el `except` es un fallo que nadie ve."""
    partes = re.split(r"(?m)^(?=## )", texto)
    salida, sustituida = [], False
    for bloque in partes:
        titulo = bloque.splitlines()[0].lstrip("# ").strip().lower() if bloque.strip() else ""
        if any(m in titulo for m in BOT_SECCIONES_FUERA):
            if not sustituida:
                salida.append(_seccion_bot(bloque))
                sustituida = True
            continue
        salida.append(bloque.rstrip() + "\n")
    if not sustituida:
        return texto.rstrip() + "\n"
    return "\n".join(x for x in salida if x.strip()).rstrip() + "\n"


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

    # CLAUDE.md: gitignorado, hay que copiarlo o el worktree nace sin las
    # convenciones del proyecto. Decisión 3 del ADR-20260801-bot-memoria-y-perfil:
    # se copia una VERSIÓN BOT, sin las
    # órdenes que en el puente no aplican — leer/escribir el vault (lo cubren
    # C1b y C4) y Graphiti (no hay MCP aquí). Menos órdenes imposibles = menos
    # contexto y menos intentos fallidos.
    src_md = Path(repo) / "CLAUDE.md"
    claude_md = False
    if src_md.is_file():
        try:
            (dest / "CLAUDE.md").write_text(
                bot_claude_md(src_md.read_text(encoding="utf-8", errors="replace")),
                encoding="utf-8")
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


async def delete_remote_branch(repo: str, branch: str, sha_local: str = "") -> dict:
    """Borra `origin/<branch>`. Devuelve {borrada, motivo}.

    POR QUÉ EXISTE (2026-08-20). `remove_worktree` borraba la rama LOCAL y no
    tocaba el remoto **nunca**: cada conversación del bot publicaba su rama con
    `/push` y ahí se quedaba para siempre. En campo se contaron **cinco**
    `origin/tg/*` de conversaciones ya integradas y cerradas. El paso 7 del
    merge-gate ya avisa de a dónde lleva eso: se llegó a **92 ramas remotas**, y
    bajarlas a 17 se comió una sesión entera sin producir nada.

    ⚠ LA GUARDA DEL SHA, y es la parte que importa. Al llegar aquí la rama local
    ya no existe, así que el remoto puede ser **la única copia**. Si alguien
    empujó a esa rama por fuera (otra laptop, otra sesión), su trabajo no está en
    el merge que acabamos de hacer y borrarla lo tiraría sin rastro. Por eso se
    compara contra el sha que tenía la local: si no coinciden, NO se borra y se
    dice. Fallar cerrado aquí cuesta una rama de más; fallar abierto cuesta el
    trabajo de otro.
    """
    if not branch:
        return {"borrada": False, "motivo": "sin rama que borrar"}
    if not await has_remote(repo):
        return {"borrada": False, "motivo": "el repo no tiene remoto"}

    remoto = await remote_head(repo, branch)
    if not remoto:
        return {"borrada": False, "motivo": "no estaba publicada (nada que borrar)"}
    if sha_local and not (remoto.startswith(sha_local) or sha_local.startswith(remoto)):
        return {"borrada": False,
                "motivo": (f"el remoto está en `{remoto[:7]}` y lo integrado era "
                           f"`{sha_local[:7]}`: alguien empujó ahí por fuera. NO la "
                           f"borro — revísala antes.")}

    rc, out, err = await run(["git", "push", "origin", "--delete", branch], repo, timeout=180)
    if rc != 0:
        salida = (err or out)
        # `remote ref does not exist` no es un fallo: es que ya no estaba (un
        # `gh pr merge --delete-branch`, o un borrado a mano). Decir "no pude"
        # ahí sería alarmar por un trabajo que ya estaba hecho.
        if "remote ref does not exist" in salida or "does not exist" in salida:
            return {"borrada": True, "motivo": "ya no estaba en el remoto"}
        return {"borrada": False, "motivo": salida[:200]}
    return {"borrada": True, "motivo": f"borrada del remoto (estaba en {remoto[:7]})"}


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


# Trailer que marca lo que hizo el puente. Va en `commit_all` —el único sitio
# donde el bot crea commits— y existe por la auditoría 39 (§8.2): los tres
# commits que el puente empujó a `main` el 2026-08-18 llevaban autor Y committer
# del humano, cuerpo vacío y cero trailers, así que **nada en los metadatos de
# git decía que los había hecho un bot**. Ninguna sesión podía saber que `main`
# se había movido por Telegram y no por una persona; el sprint 16 casi trabaja
# sobre una base fantasma por eso.
#
# Trailer y no committer aparte a propósito: `git log --format=%(trailers)` y
# `git interpret-trailers` lo leen sin configurar identidades nuevas en la
# máquina, y no toca la autoría, que sigue siendo de quien pidió el trabajo.
COMMIT_TRAILER = "Via: telegram-bridge"


async def commit_all(worktree: str, message: str) -> dict:
    """Commit de todo lo pendiente en la rama del worktree.

    El mensaje lleva `Via: telegram-bridge` para que un commit del bot se pueda
    distinguir de uno humano por metadatos, no por el estilo del asunto.
    """
    await git(["add", "-A"], worktree)
    if not (await git(["diff", "--cached", "--name-only"], worktree)).strip():
        return {"committed": False, "reason": "no hay cambios que commitear"}
    # El trailer va en su propio párrafo: `git` solo lo reconoce como tal si va
    # en el último bloque del mensaje, separado por una línea en blanco.
    cuerpo = message.rstrip()
    if COMMIT_TRAILER not in cuerpo:
        cuerpo += f"\n\n{COMMIT_TRAILER}"
    await git(["-c", "core.autocrlf=false", "commit", "-m", cuerpo], worktree)
    return {"committed": True,
            "sha": await git(["rev-parse", "--short", "HEAD"], worktree),
            "subject": await git(["log", "-1", "--pretty=%s"], worktree)}


async def remote_head(worktree: str, branch: str) -> str:
    """SHA de la punta de la rama EN EL REMOTO, o "" si no se puede saber.

    Sirve para confirmar que lo que se va a mergear es exactamente lo que se
    probó en local: un PR desactualizado integra menos de lo que crees.
    """
    rc, out, _ = await run(["git", "ls-remote", "origin", f"refs/heads/{branch}"],
                           worktree, timeout=60)
    if rc != 0 or not out.strip():
        return ""
    return out.split()[0]


async def push_branch(worktree: str, branch: str) -> dict:
    """Publica la rama. Requiere remoto configurado.

    Tras un `/pull` la rama se rebasa, así que su historia deja de ser
    descendiente de lo publicado y git rechaza el push (`non-fast-forward`).
    En ese caso se reintenta con **`--force-with-lease`**, que sobrescribe SOLO
    si el remoto sigue donde creíamos: si alguien más publicó ahí mientras
    tanto, falla en vez de pisarlo. Un `--force` a secas sí lo pisaría.

    El forzado se limita a las ramas `tg/*` (las del bot). Nunca se fuerza una
    rama del usuario: el daemon no tiene por qué reescribir su historia.
    """
    if not await has_remote(worktree):
        return {"pushed": False, "reason": "el repo no tiene remoto configurado"}

    rc, out, err = await run(["git", "push", "-u", "origin", branch], worktree, timeout=180)
    if rc == 0:
        return {"pushed": True}

    salida = (err or out)
    # P4: "rejected" a secas también lo escupe branch protection, y ahí el
    # diagnóstico "divergió por el rebase" sería falso. Se exige la causa real
    # que git nombra; el lease fallaría igual, pero el mensaje no mentiría.
    rebasada = "non-fast-forward" in salida or "fetch first" in salida
    if not rebasada:
        return {"pushed": False, "reason": salida[:250]}
    if not branch.startswith(f"{BRANCH_PREFIX}/"):
        return {"pushed": False,
                "reason": f"la rama '{branch}' divergió del remoto y NO es una rama "
                          f"del bot: no la fuerzo. Resuélvelo en la laptop."}

    rc2, out2, err2 = await run(
        ["git", "push", "--force-with-lease", "-u", "origin", branch], worktree, timeout=180)
    if rc2 == 0:
        return {"pushed": True, "forzado": True}
    return {"pushed": False,
            "reason": f"la rama divergió (rebase) y el push forzado también falló — "
                      f"probablemente alguien publicó en ella mientras tanto:\n"
                      f"{(err2 or out2)[:200]}"}


async def ensure_pr(worktree: str, branch: str, base: str, title: str) -> dict:
    """Crea el PR si no existe (requiere gh); devuelve su URL si la hay."""
    gh = shutil.which("gh")
    if not gh:
        # La razón lleva la CURA dentro, y va aquí —en quien la sabe— y no en
        # cada llamador: `ensure_pr` tiene dos (/push y /merge) y la cura es la
        # misma. Sin esto el humano pide un PR, no pasa nada, y no hay forma de
        # saber por qué (sprint 16, A3).
        return {"pr": False,
                "reason": "`gh` no está instalado en la máquina donde corre el "
                          "bot, así que desde aquí no se pueden crear PRs. "
                          "Cura: instálalo y autentícalo EN ESA MÁQUINA "
                          "(`gh auth login`), o abre el PR desde la laptop."}
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


async def pull_base(worktree: str, base: str) -> dict:
    """Trae `base` (main) a la rama del worktree, con rebase.

    Cierra el gap del `ADR-20260801-puente-telegram` (gate de merge): una conversación larga trabaja días sobre un
    `main` viejo y llega al `/merge` con más conflicto del necesario.

    Rebase y no merge, porque la rama es desechable y su historia se aplasta al
    integrar: un merge commit ahí solo añade ruido. Si hay conflicto se aborta
    y se deja la rama como estaba — resolverlo desde el móvil no es realista.
    """
    if not await is_clean(worktree):
        return {"ok": False, "reason": "hay cambios sin commitear; haz /commit primero"}

    antes = await head_sha(worktree)
    if await has_remote(worktree):
        rc, _, err = await run(["git", "fetch", "origin", base], worktree, timeout=180)
        if rc != 0:
            return {"ok": False, "reason": f"no pude traer el remoto: {err[:150]}"}
        objetivo = f"origin/{base}"
    else:
        objetivo = base

    # P3: "" NO es "0". Si el comando falló, `check=False` devuelve cadena vacía
    # y reportar "ya estabas al día" sería inventarse un estado.
    detras = (await git(["rev-list", "--count", f"HEAD..{objetivo}"],
                        worktree, check=False)).strip()
    if not detras.isdigit():
        return {"ok": False, "reason": f"no pude contar cuántos commits te faltan "
                                       f"de {objetivo}; no toco la rama"}
    if detras == "0":
        return {"ok": True, "sin_cambios": True, "detras": 0}

    rc, out, err = await run(["git", "rebase", objetivo], worktree, timeout=180)
    if rc != 0:
        # P2: no basta con lanzar el abort — hay que comprobar que DEJÓ la rama
        # como estaba. Si el abort falla y decimos "quedó intacta", mentimos y
        # el siguiente comando se encuentra un rebase a medias. Mismo linaje que
        # A1, que en merge_squash sí se verificó.
        await run(["git", "rebase", "--abort"], worktree, timeout=60)
        restaurada = (await head_sha(worktree) == antes) and await is_clean(worktree)
        if not restaurada:
            return {"ok": False, "conflicto": True, "detras": int(detras),
                    "reason": f"{(err or out)[:200]}\n\n⚠️ Y el `rebase --abort` NO "
                              f"dejó la rama como estaba: hay un rebase a medias en el "
                              f"worktree. NO corras más comandos aquí — resuélvelo en "
                              f"la laptop (`git rebase --abort` o `--skip`)."}
        return {"ok": False, "conflicto": True, "detras": int(detras),
                "reason": f"{(err or out)[:200]}\n\nLa rama quedó intacta (verificado). "
                          f"Resuélvelo en la laptop o pide los cambios en otra rama."}
    return {"ok": True, "detras": int(detras), "antes": antes,
            "ahora": await head_sha(worktree)}


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

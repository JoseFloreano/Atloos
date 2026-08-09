---
name: gdb-sanitizers-runbook
description: >
  Runbook de debugging nativo C/C++: segfaults, memory leaks, use-after-free,
  data races y comportamiento indefinido, usando sanitizers (ASan/UBSan/TSan),
  gdb y Valgrind. Use when the user says "segfault", "crashea", "memory leak",
  "use after free", "heap corruption", "core dump", "UB", or a C/C++ program
  fails in ways the code doesn't explain. Requiere toolchain C++ local.
---

# GDB + Sanitizers Runbook (C/C++)

Elige la herramienta por síntoma y extrae el diagnóstico. Complementa a
`superpowers:systematic-debugging` (el protocolo) poniendo la instrumentación nativa; para
fuzzing/coverage ver las skills `tob-*` (Trail of Bits).

## Requisitos

- clang o gcc recientes, CMake, y de preferencia build de Debug — solo Claude Code.
- Valgrind solo en Linux (en Windows usa WSL o quédate con ASan).

## Herramienta por síntoma

| Síntoma | Primera herramienta |
|---------|---------------------|
| Crash/segfault reproducible | **ASan** (rápido y con stack claro) → gdb si necesitas inspección viva |
| Leak | **ASan/LSan** (`detect_leaks=1`) · Valgrind si ASan no lo ve |
| Valores basura, "no puede pasar" | **UBSan** (overflow, aliasing, uninit) |
| Falla solo con hilos / a veces | **TSan** (data races) — no combinar con ASan en el mismo build |
| Crash NO reproducible | Habilita core dumps (`ulimit -c unlimited`) y autopsia post-mortem |

## Pasos

1. **Build instrumentado** (Debug + frames legibles):
   ```bash
   cmake -B build-asan -DCMAKE_BUILD_TYPE=Debug \
     -DCMAKE_CXX_FLAGS="-fsanitize=address,undefined -fno-omit-frame-pointer -g"
   ```
   (TSan: `-fsanitize=thread` en un build SEPARADO.)
2. **Corre el reproductor** con el sanitizer activo; opciones útiles:
   `ASAN_OPTIONS=detect_leaks=1:abort_on_error=1 UBSAN_OPTIONS=print_stacktrace=1`.
3. **Lee el reporte de abajo hacia arriba**: la primera línea con código PROPIO
   (no de libc/STL) es el sospechoso; el reporte de ASan además dice dónde se
   asignó y dónde se liberó — cita ambos stacks en el diagnóstico.
4. **gdb cuando necesites estado vivo**: `gdb --args ./bin <args>` → `run`,
   y al parar: `bt full`, `frame N`, `print var`, `watch var` (para corrupción),
   `info threads` + `thread apply all bt` (hilos). Post-mortem: `gdb ./bin core`.
5. **Confirma la causa** con la fase 3 de `superpowers:systematic-debugging` (hipótesis única
   + test mínimo que falla) — un stack trace es evidencia, no diagnóstico.
6. **Fix + verificación doble**: el test nuevo pasa Y el binario instrumentado
   corre limpio (cero reportes de ASan/UBSan, no solo "ya no crashea").
7. **Registra** con `memory-keeper`: síntoma, herramienta que lo destapó, causa
   raíz, fix — y si fue UB latente, qué patrón del código lo permitió.

## Trampas conocidas

- Release sin `-g` da stacks inútiles: instrumenta SIEMPRE sobre Debug.
- ASan cambia el layout de memoria: un bug que "desaparece" con ASan suele ser
  timing/uninit — pásalo por UBSan/TSan antes de declararlo arreglado.
- No mezcles ASan y TSan en el mismo binario; son builds separados.

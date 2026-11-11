#!/usr/bin/env python3
"""PreToolUse hook (Bash): bloqueia comandos destrutivos de alto risco.

Recebe o JSON do Claude Code via stdin. Sai com código 2 (bloqueia e informa o
motivo ao Claude) quando o comando casa com um padrão proibido.
"""
from __future__ import annotations

import json
import re
import sys

BLOCKED_PATTERNS: list[tuple[str, str]] = [
    (r"\brm\s+(-[a-zA-Z]*r[a-zA-Z]*f|-[a-zA-Z]*f[a-zA-Z]*r)\b", "rm -rf é proibido; remova arquivos específicos com aprovação"),
    (r"\brm\s+-[a-zA-Z]*r\b.*\s(/|~|\.|\*)(\s|$)", "remoção recursiva de raiz/home/diretório atual"),
    (r"\bgit\s+push\b.*(--force\b|-f\b|--force-with-lease\b)", "git push forçado é proibido"),
    (r"\bgit\s+reset\s+--hard\b", "git reset --hard descarta trabalho"),
    (r"\bgit\s+clean\s+-[a-zA-Z]*[fdx]", "git clean apaga arquivos não versionados"),
    (r"\bgit\s+checkout\s+--\s+\.", "descarta todas as alterações locais"),
    (r"\bgit\s+lfs\s+prune\b", "lfs prune exige aprovação"),
    (r"\b(format|mkfs|diskpart)\b", "operação de disco"),
    (r"\bRemove-Item\b.*-Recurse\b", "Remove-Item -Recurse é proibido"),
    (r"\bdel\s+/[sS]\b", "del /s é proibido"),
    (r"\brmdir\s+/[sS]\b", "rmdir /s é proibido"),
    (r"\bSet-ExecutionPolicy\b", "não altere a política de execução global"),
    (r"(curl|wget|iwr|Invoke-WebRequest)[^|]*\|\s*(sh|bash|iex|python)", "executar script baixado da internet"),
    (r"\b(shutdown|reboot)\b", "desligar/reiniciar a máquina"),
]


def check_command(command: str) -> str | None:
    """Retorna o motivo do bloqueio ou None se o comando é permitido."""
    for pattern, reason in BLOCKED_PATTERNS:
        if re.search(pattern, command, flags=re.IGNORECASE):
            return reason
    return None


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0  # não bloqueia por entrada inesperada
    command = (payload.get("tool_input") or {}).get("command", "")
    reason = check_command(command)
    if reason:
        print(f"Bloqueado pelo guard_bash: {reason}. Comando: {command!r}. "
              "Peça aprovação ao usuário (ver .claude/rules/safety.md).", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())

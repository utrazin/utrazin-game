#!/usr/bin/env python3
"""Informa o que há na máquina para as ferramentas OPCIONAIS (ACE-Step, Audio2Face, Blender MCP).

Somente leitura: não instala nada e não baixa modelos. A saída nunca é motivo para falhar o jogo.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

# Faixas de VRAM documentadas pelo ACE-Step 1.5 (README). Confirme na versão instalada.
ACESTEP_TIERS = [
    (24000, "24 GB+: DiT XL com LM 4B"),
    (20000, "20-24 GB: DiT XL com LM 1.7B"),
    (16000, "16-20 GB: DiT 2B sft ou XL turbo com LM 1.7B"),
    (8000, "8-16 GB: DiT 2B com LM 0.6B ou 1.7B"),
    (6000, "6-8 GB: DiT 2B turbo com LM 0.6B"),
    (0, "ate 6 GB: DiT 2B turbo sem LM, INT8 e offload para CPU"),
]


def acestep_tier(vram_mb: int | None) -> str:
    if vram_mb is None:
        return "sem GPU NVIDIA detectada: CPU, MPS, ROCm ou XPU possíveis, bem mais lento"
    for floor, label in ACESTEP_TIERS:
        if vram_mb >= floor:
            return label
    return ACESTEP_TIERS[-1][1]


def nvidia_vram_mb() -> int | None:
    exe = shutil.which("nvidia-smi")
    if not exe:
        return None
    try:
        out = subprocess.run([exe, "--query-gpu=memory.total", "--format=csv,noheader,nounits"],
                             capture_output=True, text=True, timeout=10).stdout.split()
        return max(int(x) for x in out) if out else None
    except (OSError, ValueError, subprocess.SubprocessError):
        return None


def probe_url(url: str) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=3):
            return True
    except Exception:
        return False


def collect(path: Path, acestep_url: str | None) -> dict:
    vram = nvidia_vram_mb()
    free_gb = round(shutil.disk_usage(path).free / 1e9, 1)
    return {
        "python": sys.version.split()[0],
        "uv": bool(shutil.which("uv")),
        "ffmpeg": bool(shutil.which("ffmpeg")),
        "blender_no_path": bool(shutil.which("blender")),
        "nvidia_vram_mb": vram,
        "disco_livre_gb": free_gb,
        "acestep_faixa_sugerida": acestep_tier(vram),
        "acestep_servidor_ativo": probe_url(acestep_url + "/health") if acestep_url else None,
        "mcp_json_presente": (Path(__file__).resolve().parents[2] / ".mcp.json").exists(),
        "observacao": "Tudo aqui é opcional. O jogo e a pipeline funcionam sem essas ferramentas.",
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--path", type=Path, default=Path("."))
    ap.add_argument("--acestep-url", default=None, help="ex.: http://localhost:8001")
    args = ap.parse_args(argv)
    print(json.dumps(collect(args.path, args.acestep_url), ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())

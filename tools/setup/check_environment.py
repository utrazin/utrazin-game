#!/usr/bin/env python3
"""Inspeção do ambiente de desenvolvimento (Etapa 0 do prompt mestre).

Não instala nada. Verifica: SO, Git, Git LFS, Python, uv, Claude Code,
Unreal Engine (versão e caminho), Visual Studio/MSVC/Windows SDK, Blender,
disco livre, RAM, GPU e o próprio repositório.

Exemplos:
  python tools/setup/check_environment.py
  python tools/setup/check_environment.py --json reports/environment.json
  python tools/setup/check_environment.py --ue-root "E:/Epic/UE_5.8"
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import re
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import REPO_ROOT, setup_logger  # noqa: E402

REQUIRED_UE = "5.8.4"
REQUIRED_BLENDER_MAJOR_MINOR = "5.2"
MIN_FREE_GB = 150


@dataclass
class Check:
    name: str
    status: str  # ok | warn | missing | error
    detail: str


def run(cmd: list[str], timeout: int = 20) -> str | None:
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return (out.stdout or out.stderr).strip() if out.returncode == 0 else None


def parse_build_version(text: str) -> str | None:
    """Lê Engine/Build/Build.version (JSON) e devolve 'Major.Minor.Patch'."""
    try:
        data = json.loads(text)
        return f"{data['MajorVersion']}.{data['MinorVersion']}.{data['PatchVersion']}"
    except (ValueError, KeyError, TypeError):
        return None


def parse_blender_version(text: str) -> str | None:
    m = re.search(r"Blender\s+(\d+\.\d+(?:\.\d+)?)", text)
    return m.group(1) if m else None


def ue_candidates(explicit: str | None) -> list[Path]:
    roots = []
    if explicit:
        roots.append(Path(explicit))
    if os.environ.get("UE_ROOT"):
        roots.append(Path(os.environ["UE_ROOT"]))
    for drive in ("C:", "D:", "E:"):
        for base in ("Program Files/Epic Games", "Epic Games", "Epic", "UnrealEngine"):
            for ver in ("UE_5.8", "UE_5.8.4"):
                roots.append(Path(f"{drive}/{base}/{ver}"))
    return roots


def check_unreal(explicit: str | None) -> Check:
    for root in ue_candidates(explicit):
        bv = root / "Engine" / "Build" / "Build.version"
        if bv.is_file():
            version = parse_build_version(bv.read_text(encoding="utf-8", errors="ignore"))
            status = "ok" if version == REQUIRED_UE else "warn"
            return Check("Unreal Engine", status, f"{version} em {root} (exigido {REQUIRED_UE})")
    return Check("Unreal Engine", "missing", f"{REQUIRED_UE} não encontrada (defina UE_ROOT ou --ue-root)")


def check_visual_studio() -> list[Check]:
    if platform.system() != "Windows":
        return [Check("Visual Studio", "warn", "verificação só no Windows")]
    vswhere = Path(os.environ.get("ProgramFiles(x86)", "C:/Program Files (x86)")) / "Microsoft Visual Studio/Installer/vswhere.exe"
    if not vswhere.is_file():
        return [Check("Visual Studio", "missing", "vswhere.exe não encontrado (VS não instalado)")]
    out = run([str(vswhere), "-latest", "-products", "*", "-requires",
               "Microsoft.VisualStudio.Component.VC.Tools.x86.x64", "-format", "json"])
    checks = []
    try:
        items = json.loads(out or "[]")
    except ValueError:
        items = []
    if items:
        vs = items[0]
        checks.append(Check("Visual Studio + MSVC", "ok", f"{vs.get('displayName')} {vs.get('installationVersion')}"))
    else:
        checks.append(Check("Visual Studio + MSVC", "missing", "VS sem ferramentas C++ (workload Game development with C++)"))
    sdk_root = Path(os.environ.get("ProgramFiles(x86)", "C:/Program Files (x86)")) / "Windows Kits/10/Include"
    sdks = sorted(p.name for p in sdk_root.glob("10.*")) if sdk_root.is_dir() else []
    checks.append(Check("Windows SDK", "ok" if sdks else "missing", ", ".join(sdks[-3:]) or "não encontrado"))
    return checks


def check_blender() -> Check:
    exe = os.environ.get("BLENDER_EXE") or shutil.which("blender")
    if not exe:
        return Check("Blender", "missing", "não encontrado no PATH nem em BLENDER_EXE")
    version = parse_blender_version(run([exe, "--version"], timeout=60) or "")
    if not version:
        return Check("Blender", "error", f"não foi possível ler a versão de {exe}")
    status = "ok" if version.startswith(REQUIRED_BLENDER_MAJOR_MINOR) else "warn"
    return Check("Blender", status, f"{version} ({exe}); alvo {REQUIRED_BLENDER_MAJOR_MINOR} LTS")


def check_tool(name: str, cmd: list[str], required: bool = True) -> Check:
    out = run(cmd)
    if out:
        return Check(name, "ok", out.splitlines()[0])
    return Check(name, "missing" if required else "warn", "não encontrado")


def check_disk(path: Path) -> Check:
    usage = shutil.disk_usage(path)
    free_gb = usage.free / 1024**3
    return Check("Disco livre", "ok" if free_gb >= MIN_FREE_GB else "warn",
                 f"{free_gb:.0f} GB livres em {path.anchor or path} (recomendado {MIN_FREE_GB} GB)")


def check_ram() -> Check:
    total = None
    try:
        if platform.system() == "Windows":
            import ctypes

            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                            ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                            ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                            ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                            ("sullAvailExtendedVirtual", ctypes.c_ulonglong)]
            stat = MEMORYSTATUSEX()
            stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))  # type: ignore[attr-defined]
            total = stat.ullTotalPhys
        elif hasattr(os, "sysconf"):
            total = os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES")
    except (OSError, ValueError, AttributeError):
        total = None
    if not total:
        return Check("RAM", "warn", "não foi possível medir")
    gb = total / 1024**3
    return Check("RAM", "ok" if gb >= 32 else "warn", f"{gb:.0f} GB (recomendado 32 GB)")


def check_gpu() -> Check:
    if platform.system() == "Windows":
        out = run(["powershell", "-NoProfile", "-Command",
                   "Get-CimInstance Win32_VideoController | Select-Object -ExpandProperty Name"])
    else:
        out = run(["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"])
    return Check("GPU", "ok" if out else "warn", out.replace("\n", "; ") if out else "não detectada")


def check_repo(root: Path) -> list[Check]:
    checks = [Check("Repositório", "ok" if (root / ".git").exists() else "warn", str(root))]
    attrs = root / ".gitattributes"
    checks.append(Check(".gitattributes LFS", "ok" if attrs.is_file() and "filter=lfs" in attrs.read_text(encoding="utf-8") else "missing", str(attrs)))
    uproject = root / "unreal" / "JogoResgate" / "JogoResgate.uproject"
    checks.append(Check("JogoResgate.uproject", "ok" if uproject.is_file() else "missing", str(uproject)))
    hooks = run(["git", "-C", str(root), "config", "core.hooksPath"])
    checks.append(Check("Git hooks (.githooks)", "ok" if hooks == ".githooks" else "warn",
                        hooks or "não configurado: git config core.hooksPath .githooks"))
    return checks


def collect(ue_root: str | None) -> list[Check]:
    checks = [
        Check("Sistema operacional", "ok" if platform.system() == "Windows" and platform.machine().endswith("64") else "warn",
              f"{platform.system()} {platform.release()} {platform.machine()}"),
        Check("Python", "ok" if sys.version_info >= (3, 11) else "warn", sys.version.split()[0]),
        check_tool("Git", ["git", "--version"]),
        check_tool("Git LFS", ["git", "lfs", "version"]),
        check_tool("uv", ["uv", "--version"], required=False),
        check_tool("Claude Code", ["claude", "--version"], required=False),
        check_unreal(ue_root),
        *check_visual_studio(),
        check_blender(),
        check_disk(REPO_ROOT),
        check_ram(),
        check_gpu(),
        *check_repo(REPO_ROOT),
    ]
    return checks


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ue-root", help="pasta da engine (contém Engine/Build/Build.version)")
    ap.add_argument("--json", type=Path, help="grava resultado em JSON")
    args = ap.parse_args(argv)
    log = setup_logger("check_environment")
    checks = collect(args.ue_root)
    width = max(len(c.name) for c in checks)
    for c in checks:
        print(f"[{c.status.upper():7}] {c.name:<{width}}  {c.detail}")
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps([asdict(c) for c in checks], ensure_ascii=False, indent=2), encoding="utf-8")
        log.info("resultado salvo em %s", args.json)
    missing = [c.name for c in checks if c.status in {"missing", "error"}]
    if missing:
        log.warning("pendências: %s", ", ".join(missing))
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())

"""Utilitários compartilhados pelos scripts de pipeline (sem dependências externas)."""
from __future__ import annotations

import hashlib
import json
import logging
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]


def setup_logger(name: str, verbose: bool = False, log_file: Path | None = None) -> logging.Logger:
    """Logger com saída em stderr e, opcionalmente, arquivo (auditoria)."""
    logger = logging.getLogger(name)
    logger.handlers.clear()
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s", "%Y-%m-%dT%H:%M:%S")
    stream = logging.StreamHandler(sys.stderr)
    stream.setFormatter(fmt)
    logger.addHandler(stream)
    if log_file is not None:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        fh = logging.FileHandler(log_file, encoding="utf-8")
        fh.setFormatter(fmt)
        logger.addHandler(fh)
    logger.propagate = False
    return logger


def sha256_file(path: Path, chunk: int = 1 << 20) -> str:
    """Hash no formato usado pelo manifesto: 'sha256:<hex>'."""
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(chunk), b""):
            h.update(block)
    return "sha256:" + h.hexdigest()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def resolve_repo_path(value: str, root: Path = REPO_ROOT) -> Path:
    """Converte caminho relativo do repositório (com / ou \\) em Path absoluto."""
    p = Path(value.replace("\\", "/"))
    return p if p.is_absolute() else root / p

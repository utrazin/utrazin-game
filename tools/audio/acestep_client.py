#!/usr/bin/env python3
"""Cliente mínimo (somente biblioteca padrão) para a API REST local do ACE-Step 1.5.

OPCIONAL. A pipeline funciona sem o ACE-Step instalado. Este cliente só fala com um servidor
já em execução (`uv run acestep-api`, porta padrão 8001) e nunca baixa modelos.

Endpoints usados (conforme docs/en/API.md do ACE-Step 1.5): GET /health, POST /release_task,
POST /query_result, GET /v1/audio?path=...  Status em /query_result: 0 em andamento,
1 sucesso, 2 falha.

Uso:
    python tools/audio/acestep_client.py health
    python tools/audio/acestep_client.py generate --prompt "ambient alien forest" --duration 60 \
        --bpm 90 --batch 2 --out audio/music/candidates/L01_Z01
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

DEFAULT_URL = os.environ.get("ACESTEP_URL", "http://localhost:8001")


class AceStepError(RuntimeError):
    pass


def _request(method: str, url: str, body: dict | None = None, token: str | None = None,
             timeout: float = 30.0) -> bytes:
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    if body is not None:
        req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read()
    except urllib.error.HTTPError as exc:
        raise AceStepError(f"HTTP {exc.code} em {url}: {exc.read()[:200]!r}") from exc
    except urllib.error.URLError as exc:
        raise AceStepError(f"servidor inacessível em {url}: {exc.reason}") from exc


def _json(method: str, url: str, body: dict | None = None, token: str | None = None) -> dict:
    return json.loads(_request(method, url, body, token).decode("utf-8"))


def health(base: str = DEFAULT_URL, token: str | None = None) -> dict:
    return _json("GET", f"{base}/health", None, token)


def build_payload(prompt: str, duration: float | None = None, bpm: int | None = None,
                  lyrics: str = "", seed: int | None = None, batch: int = 1,
                  audio_format: str = "wav", steps: int | None = None, thinking: bool = False,
                  vocal_language: str = "en") -> dict:
    if not prompt.strip():
        raise ValueError("prompt vazio")
    if duration is not None and not 10 <= duration <= 600:
        raise ValueError("duration deve estar entre 10 e 600 s")
    if bpm is not None and not 30 <= bpm <= 300:
        raise ValueError("bpm deve estar entre 30 e 300")
    if not 1 <= batch <= 8:
        raise ValueError("batch deve estar entre 1 e 8")
    payload: dict = {"prompt": prompt, "lyrics": lyrics, "batch_size": batch,
                     "audio_format": audio_format, "thinking": thinking,
                     "vocal_language": vocal_language}
    if duration is not None:
        payload["audio_duration"] = duration
    if bpm is not None:
        payload["bpm"] = bpm
    if steps is not None:
        payload["inference_steps"] = steps
    if seed is not None:
        payload["seed"] = seed
        payload["use_random_seed"] = False
    return payload


def release_task(payload: dict, base: str = DEFAULT_URL, token: str | None = None) -> str:
    resp = _json("POST", f"{base}/release_task", payload, token)
    task_id = (resp.get("data") or {}).get("task_id")
    if not task_id:
        raise AceStepError(f"resposta sem task_id: {resp}")
    return task_id


def query_result(task_id: str, base: str = DEFAULT_URL, token: str | None = None) -> dict:
    resp = _json("POST", f"{base}/query_result", {"task_id_list": [task_id]}, token)
    items = resp.get("data") or []
    if not items:
        raise AceStepError(f"sem dados para a tarefa {task_id}: {resp}")
    item = items[0]
    result = item.get("result")
    if isinstance(result, str) and result:
        try:
            item["result"] = json.loads(result)
        except json.JSONDecodeError:
            pass
    return item


def result_files(item: dict) -> list[dict]:
    """Normaliza `result` (dict ou lista de dicts) numa lista de entradas com `file`."""
    res = item.get("result")
    entries = res if isinstance(res, list) else [res] if isinstance(res, dict) else []
    return [e for e in entries if isinstance(e, dict) and e.get("file")]


def download(file_ref: str, out_path: Path, base: str = DEFAULT_URL, token: str | None = None) -> Path:
    url = file_ref if file_ref.startswith("http") else base + (
        file_ref if file_ref.startswith("/") else "/v1/audio?path=" + urllib.parse.quote(file_ref, safe=""))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(_request("GET", url, None, token, timeout=120.0))
    return out_path


def generate(payload: dict, out_dir: Path, base: str = DEFAULT_URL, token: str | None = None,
             poll: float = 2.0, timeout: float = 900.0, stem: str = "cand") -> list[Path]:
    """Cria a tarefa, espera, baixa cada candidato e grava um .json de metadados ao lado."""
    task_id = release_task(payload, base, token)
    deadline = time.monotonic() + timeout
    while True:
        item = query_result(task_id, base, token)
        status = item.get("status")
        if status == 1:
            break
        if status == 2:
            raise AceStepError(f"tarefa {task_id} falhou: {item}")
        if time.monotonic() > deadline:
            raise AceStepError(f"tempo esgotado na tarefa {task_id}")
        time.sleep(poll)
    saved: list[Path] = []
    for i, entry in enumerate(result_files(item), start=1):
        ext = payload.get("audio_format", "wav")
        audio = download(entry["file"], out_dir / f"{stem}_{i:02d}.{ext}", base, token)
        meta = {"task_id": task_id, "payload": payload, "entry": entry,
                "generator_name": "ACE-Step", "generator_version": "1.5",
                "creation_method": "ai_generated"}
        audio.with_suffix(".json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
        saved.append(audio)
    if not saved:
        raise AceStepError(f"tarefa {task_id} terminou sem arquivos de áudio: {item}")
    return saved


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--url", default=DEFAULT_URL)
    ap.add_argument("--token", default=os.environ.get("ACESTEP_API_KEY"))
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("health")
    g = sub.add_parser("generate")
    g.add_argument("--prompt", required=True)
    g.add_argument("--lyrics", default="")
    g.add_argument("--duration", type=float)
    g.add_argument("--bpm", type=int)
    g.add_argument("--seed", type=int)
    g.add_argument("--batch", type=int, default=2)
    g.add_argument("--format", default="wav")
    g.add_argument("--out", type=Path, required=True)
    g.add_argument("--stem", default="cand")
    args = ap.parse_args(argv)
    try:
        if args.cmd == "health":
            print(json.dumps(health(args.url, args.token), ensure_ascii=False))
            return 0
        payload = build_payload(args.prompt, args.duration, args.bpm, args.lyrics, args.seed,
                                args.batch, args.format)
        for p in generate(payload, args.out, args.url, args.token, stem=args.stem):
            print(p)
        return 0
    except (AceStepError, ValueError) as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())

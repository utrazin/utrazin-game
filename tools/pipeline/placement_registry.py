#!/usr/bin/env python3
"""Registro de footprints para evitar sobreposição entre objetos colocados no mapa.

Todo script que coloca objetos (props, rochas, árvores, prédios) consulta e grava aqui.
Unidades: centímetros (como a Unreal). Sem dependências externas.

Pares permitidos (ok_pairs): alguns tipos PODEM se sobrepor de propósito (pedra debaixo da copa de uma árvore,
baú dentro da barraca, peças do mesmo blockout encostadas). O registro guarda esses pares e os usa tanto na
colocação (can_place/add com `tag`) quanto na auditoria (find_overlaps). Sem ok_pairs, tudo conflita com tudo.

Uso (CLI):
    python tools/pipeline/placement_registry.py check reports/placement_L01.json
    python tools/pipeline/placement_registry.py stats reports/placement_L01.json
"""
from __future__ import annotations

import argparse
import json
import math
import random
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterable

CELL = 500.0  # tamanho da célula do índice espacial (cm)


@dataclass
class Footprint:
    x: float
    y: float
    radius: float
    tag: str = "prop"
    reason: str = ""
    id: str = ""


def pair(a: str, b: str) -> tuple[str, str]:
    """Par de tags sem ordem (chave de ok_pairs)."""
    return (a, b) if a <= b else (b, a)


@dataclass
class Registry:
    items: list[Footprint] = field(default_factory=list)
    _grid: dict = field(default_factory=dict, repr=False)
    _max_r: float = 0.0
    ok_pairs: set = field(default_factory=set)

    def allow(self, a: str, b: str) -> None:
        """Permite que objetos com as tags a e b se sobreponham (a == b: mesmo tipo pode encostar)."""
        self.ok_pairs.add(pair(a, b))

    def allowed(self, a: str | None, b: str) -> bool:
        return a is not None and pair(a, b) in self.ok_pairs

    def _cell(self, x: float, y: float) -> tuple[int, int]:
        return (math.floor(x / CELL), math.floor(y / CELL))

    def _index(self, fp: Footprint) -> None:
        self._grid.setdefault(self._cell(fp.x, fp.y), []).append(fp)
        self._max_r = max(self._max_r, fp.radius)

    def _near(self, x: float, y: float, r: float) -> Iterable[Footprint]:
        reach = r + self._max_r
        span = int(math.ceil(reach / CELL))
        cx, cy = self._cell(x, y)
        for i in range(cx - span, cx + span + 1):
            for j in range(cy - span, cy + span + 1):
                yield from self._grid.get((i, j), ())

    def conflict(self, x: float, y: float, radius: float, margin: float = 0.0,
                 ignore_tags: Iterable[str] = (), tag: str | None = None) -> Footprint | None:
        """Primeiro footprint que bloqueia (x, y, radius), ou None."""
        ignore = set(ignore_tags)
        for o in self._near(x, y, radius + margin):
            if o.tag in ignore or self.allowed(tag, o.tag):
                continue
            if math.hypot(o.x - x, o.y - y) < o.radius + radius + margin:
                return o
        return None

    def can_place(self, x: float, y: float, radius: float, margin: float = 0.0,
                  ignore_tags: Iterable[str] = (), tag: str | None = None) -> bool:
        return self.conflict(x, y, radius, margin, ignore_tags, tag) is None

    def add(self, x: float, y: float, radius: float, tag: str = "prop", reason: str = "",
            id: str = "", margin: float = 0.0, force: bool = False, ignore_tags: Iterable[str] = ()) -> bool:
        """Registra o footprint. Retorna False (e não registra) se houver sobreposição não permitida."""
        if not force and not self.can_place(x, y, radius, margin, ignore_tags, tag):
            return False
        fp = Footprint(x, y, radius, tag, reason, id)
        self.items.append(fp)
        self._index(fp)
        return True

    def _rebuild(self, keep: list[Footprint]) -> None:
        self.items, self._grid, self._max_r = [], {}, 0.0
        for f in keep:
            self.items.append(f)
            self._index(f)

    def remove_tag(self, tag: str) -> int:
        keep = [f for f in self.items if f.tag != tag]
        removed = len(self.items) - len(keep)
        self._rebuild(keep)
        return removed

    def remove_ids(self, ids: Iterable[str]) -> int:
        """Tira do registro os footprints com esses ids (ex.: peça de blockout trocada por modelo do usuário)."""
        drop = {i for i in ids if i}
        keep = [f for f in self.items if f.id not in drop]
        removed = len(self.items) - len(keep)
        if removed:
            self._rebuild(keep)
        return removed

    def find_overlaps(self) -> list[tuple[Footprint, Footprint]]:
        seen, out = set(), []
        for a in self.items:
            for b in self._near(a.x, a.y, a.radius):
                if b is a:
                    continue
                key = tuple(sorted((id(a), id(b))))
                if key in seen:
                    continue
                seen.add(key)
                if self.allowed(a.tag, b.tag):
                    continue
                if math.hypot(a.x - b.x, a.y - b.y) < a.radius + b.radius:
                    out.append((a, b))
        return out

    def missing_reason(self, tags: Iterable[str] = ("landmark", "prop", "ruin")) -> list[Footprint]:
        wanted = set(tags)
        return [f for f in self.items if f.tag in wanted and not f.reason.strip()]

    def to_json(self, compact: bool = False, meta: dict | None = None) -> str:
        data = {"version": 1, "unit": "cm", "ok_pairs": sorted(list(p) for p in self.ok_pairs)}
        if meta:
            data["meta"] = meta
        data["items"] = [asdict(f) for f in self.items]
        if compact:
            return json.dumps(data, ensure_ascii=False, separators=(",", ":"))
        return json.dumps(data, ensure_ascii=False, indent=1)

    @classmethod
    def from_json(cls, text: str) -> "Registry":
        data = json.loads(text)
        reg = cls()
        for a, b in data.get("ok_pairs", []):
            reg.allow(a, b)
        for d in data.get("items", []):
            reg.add(d["x"], d["y"], d["radius"], d.get("tag", "prop"), d.get("reason", ""),
                    d.get("id", ""), force=True)
        return reg

    def save(self, path: Path, compact: bool = False, meta: dict | None = None) -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(self.to_json(compact, meta), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> "Registry":
        return cls.from_json(Path(path).read_text(encoding="utf-8"))


def poisson_sample(registry: Registry, bounds: tuple[float, float, float, float], radius: float,
                   count: int, tag: str = "veg", reason: str = "", margin: float = 0.0,
                   seed: int = 1, tries_per_point: int = 30,
                   keep_out: Iterable[tuple[float, float, float]] = ()) -> list[tuple[float, float]]:
    """Sorteia até `count` pontos em `bounds` (xmin, ymin, xmax, ymax) sem sobrepor o registro.

    Cada ponto aceito é gravado no registro. `keep_out` lista círculos (x, y, r) proibidos
    (estradas, trilhas, portas). Determinístico para um mesmo `seed`.
    """
    xmin, ymin, xmax, ymax = bounds
    rng = random.Random(seed)
    placed: list[tuple[float, float]] = []
    attempts = 0
    limit = max(count, 1) * tries_per_point
    while len(placed) < count and attempts < limit:
        attempts += 1
        x, y = rng.uniform(xmin, xmax), rng.uniform(ymin, ymax)
        if any(math.hypot(x - kx, y - ky) < kr + radius for kx, ky, kr in keep_out):
            continue
        if registry.add(x, y, radius, tag, reason, margin=margin):
            placed.append((x, y))
    return placed


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Auditoria do registro de posicionamento.")
    ap.add_argument("command", choices=["check", "stats"])
    ap.add_argument("path", type=Path)
    args = ap.parse_args(argv)
    reg = Registry.load(args.path)
    if args.command == "stats":
        tags: dict[str, int] = {}
        for f in reg.items:
            tags[f.tag] = tags.get(f.tag, 0) + 1
        print(json.dumps({"total": len(reg.items), "por_tag": tags, "pares_permitidos": len(reg.ok_pairs)},
                         ensure_ascii=False, indent=1))
        return 0
    overlaps = reg.find_overlaps()
    no_reason = reg.missing_reason()
    for a, b in overlaps[:50]:
        print(f"SOBREPOSTO: {a.id or a.tag}@({a.x:.0f},{a.y:.0f}) x {b.id or b.tag}@({b.x:.0f},{b.y:.0f})")
    for f in no_reason[:50]:
        print(f"SEM MOTIVO: {f.id or f.tag}@({f.x:.0f},{f.y:.0f})")
    print(f"{len(reg.items)} itens, {len(overlaps)} sobreposições, {len(no_reason)} sem motivo")
    return 1 if overlaps or no_reason else 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Auditoria de licenças do manifesto de assets.

Bloqueia: licença ausente em conteúdo de terceiros, origem desconhecida,
restrições NonCommercial/NoDerivatives/uso pessoal, e aprovação com licença
não liberada. Gera relatório Markdown e, opcionalmente, créditos.

Exemplos:
  python tools/pipeline/check_licenses.py
  python tools/pipeline/check_licenses.py --report docs/licenses/audit.md --credits docs/licenses/CREDITS.md
  python tools/pipeline/check_licenses.py --ids ENM-001 WPN-001
"""
from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import REPO_ROOT, load_json, setup_logger  # noqa: E402

DEFAULT_MANIFEST = REPO_ROOT / "assets" / "manifest" / "assets.json"

BLOCK_PATTERNS = [
    (re.compile(r"\bNC\b|non[- ]?commercial|n[aã]o[- ]comercial", re.I), "restrição NonCommercial"),
    (re.compile(r"\bND\b|no[- ]?deriv", re.I), "restrição NoDerivatives"),
    (re.compile(r"personal use|uso pessoal|editorial", re.I), "apenas uso pessoal/editorial"),
    (re.compile(r"^\s*(unknown|desconhecida|n/?a|none|\?)\s*$", re.I), "licença desconhecida"),
]
REVIEW_PATTERNS = [
    (re.compile(r"\bSA\b|share[- ]?alike|GPL", re.I), "copyleft: avaliar caso a caso"),
    (re.compile(r"mixamo|fab|standard license", re.I), "termos de plataforma: confirmar termos vigentes"),
]
ATTRIBUTION_REQUIRED = re.compile(r"CC[- ]?BY(?![- ]?NC)", re.I)
THIRD_PARTY_METHODS = {"library", "ai_assisted"}


@dataclass
class Finding:
    asset_id: str
    level: str  # "block" | "review" | "ok"
    reasons: list[str] = field(default_factory=list)


def audit_asset(asset: dict) -> Finding:
    """Função pura: avalia um asset do manifesto."""
    aid = asset.get("id", "?")
    lic = (asset.get("license") or "").strip()
    method = asset.get("creation_method")
    status = asset.get("status")
    cus = asset.get("commercial_use_status")
    blocks: list[str] = []
    reviews: list[str] = []

    if method in THIRD_PARTY_METHODS or (method != "original" and method != "placeholder"):
        if not lic:
            blocks.append("licença ausente em conteúdo de terceiros/IA")
        if method == "library" and not asset.get("origin_url"):
            blocks.append("origem (origin_url) ausente")
    if method == "original" and not lic:
        reviews.append("licença do conteúdo original não registrada")
    if method == "ai_assisted" and not (asset.get("generator_name") and asset.get("generator_version")):
        blocks.append("gerador/versão da IA não registrados")
    for pattern, reason in BLOCK_PATTERNS:
        if lic and pattern.search(lic):
            blocks.append(reason)
    for pattern, reason in REVIEW_PATTERNS:
        if lic and pattern.search(lic):
            reviews.append(reason)
    if lic and ATTRIBUTION_REQUIRED.search(lic) and not asset.get("attribution"):
        blocks.append("CC BY exige texto de atribuição")
    if cus in {"blocked", "unknown"} and status not in {"planned", "rejected", "deprecated"}:
        blocks.append(f"commercial_use_status={cus} com asset em produção ({status})")
    if cus == "needs_review":
        reviews.append("commercial_use_status=needs_review (aprovação humana pendente)")
    if status == "approved" and cus != "allowed":
        blocks.append("asset aprovado sem licença liberada")
    if method == "placeholder" and status == "approved":
        blocks.append("placeholder aprovado")

    level = "block" if blocks else ("review" if reviews else "ok")
    return Finding(aid, level, blocks + reviews)


def audit(data: dict, ids: list[str] | None = None) -> list[Finding]:
    assets = data.get("assets", [])
    if ids:
        wanted = set(ids)
        missing = wanted - {a.get("id") for a in assets}
        findings = [Finding(m, "block", ["id não encontrado no manifesto"]) for m in sorted(missing)]
        assets = [a for a in assets if a.get("id") in wanted]
    else:
        findings = []
    return findings + [audit_asset(a) for a in assets]


def render_report(findings: list[Finding], today: date | None = None) -> str:
    today = today or date.today()
    counts = {k: sum(1 for f in findings if f.level == k) for k in ("block", "review", "ok")}
    lines = [f"# Auditoria de licenças - {today.isoformat()}", "",
             f"Bloqueados: **{counts['block']}** | Revisão: **{counts['review']}** | OK: **{counts['ok']}**", "",
             "| Asset | Resultado | Motivos |", "|---|---|---|"]
    for f in sorted(findings, key=lambda x: ({"block": 0, "review": 1, "ok": 2}[x.level], x.asset_id)):
        lines.append(f"| {f.asset_id} | {f.level} | {'; '.join(f.reasons) or '-'} |")
    lines += ["", "Aprovação de licença comercial é sempre humana (ASSET_LICENSES.md)."]
    return "\n".join(lines) + "\n"


def render_credits(data: dict) -> str:
    lines = ["# Créditos", "", "Gerado por `tools/pipeline/check_licenses.py --credits`. Não edite à mão.", ""]
    rows = [a for a in data.get("assets", []) if a.get("attribution")]
    if not rows:
        lines.append("Nenhuma atribuição de terceiros registrada.")
    for a in sorted(rows, key=lambda x: x["id"]):
        lines.append(f"- **{a['name']}** ({a['id']}): {a['attribution']} | Licença: {a.get('license')} | {a.get('origin_url') or ''}".rstrip(" |"))
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    p.add_argument("--ids", nargs="*", help="auditar apenas estes IDs")
    p.add_argument("--report", type=Path, help="grava relatório Markdown")
    p.add_argument("--credits", type=Path, help="grava CREDITS.md")
    p.add_argument("--strict", action="store_true", help="itens em revisão também falham")
    p.add_argument("-v", "--verbose", action="store_true")
    args = p.parse_args(argv)
    log = setup_logger("check_licenses", args.verbose)
    try:
        data = load_json(args.manifest)
    except FileNotFoundError:
        log.error("manifesto não encontrado: %s", args.manifest)
        return 1
    findings = audit(data, args.ids)
    for f in findings:
        if f.level != "ok":
            (log.error if f.level == "block" else log.warning)("%s [%s] %s", f.asset_id, f.level, "; ".join(f.reasons))
    report = render_report(findings)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(report, encoding="utf-8")
        log.info("relatório: %s", args.report)
    if args.credits:
        args.credits.parent.mkdir(parents=True, exist_ok=True)
        args.credits.write_text(render_credits(data), encoding="utf-8")
        log.info("créditos: %s", args.credits)
    blocked = any(f.level == "block" for f in findings)
    review = any(f.level == "review" for f in findings)
    log.info("%d assets auditados", len(findings))
    return 1 if blocked or (args.strict and review) else 0


if __name__ == "__main__":
    sys.exit(main())

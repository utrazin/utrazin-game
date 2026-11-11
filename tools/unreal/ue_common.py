"""Lógica pura compartilhada pelos scripts Unreal (testável sem a engine)."""
from __future__ import annotations

import re

CATEGORY_IMPORT = {
    "character": {"kind": "skeletal", "subdir": "Meshes"},
    "skin": {"kind": "skeletal", "subdir": "Meshes"},
    "enemy": {"kind": "skeletal", "subdir": "Meshes"},
    "vehicle": {"kind": "skeletal", "subdir": "Meshes"},
    "weapon": {"kind": "skeletal", "subdir": "Meshes"},
    "prop": {"kind": "static", "subdir": "Meshes"},
    "environment": {"kind": "static", "subdir": "Meshes"},
    "animation": {"kind": "animation", "subdir": ""},
}
REQUIRED_PREFIX_BY_CLASS = {
    "Blueprint": ("BP_", "ABP_"), "WidgetBlueprint": ("WBP_",), "StaticMesh": ("SM_",),
    "SkeletalMesh": ("SK_",), "Skeleton": ("SKEL_",), "PhysicsAsset": ("PHYS_",), "Material": ("M_",),
    "MaterialInstanceConstant": ("MI_",), "MaterialFunction": ("MF_",), "Texture2D": ("T_",),
    "AnimBlueprint": ("ABP_",), "AnimSequence": ("A_",), "AnimMontage": ("AM_",), "BlendSpace": ("BS_",),
    "BlendSpace1D": ("BS_",), "NiagaraSystem": ("NS_",), "NiagaraEmitter": ("NE_",),
    "SoundWave": ("SFX_", "MUS_", "AMB_"), "SoundCue": ("SC_",), "MetaSoundSource": ("MS_",),
    "SoundClass": ("SCL_",), "SoundAttenuation": ("ATT_",), "DataTable": ("DT_",), "CurveFloat": ("CF_",),
    "InputAction": ("IA_",), "InputMappingContext": ("IMC_",), "StateTree": ("ST_",),
    "BehaviorTree": ("BT_",), "BlackboardData": ("BB_",), "LevelSequence": ("LS_",), "Font": ("FNT_",),
    "IKRigDefinition": ("IK_",), "IKRetargeter": ("RTG_",), "StringTable": ("ST_Text_",),
}
MAP_RE = re.compile(r"^L\d{2}_[A-Z][A-Za-z0-9]*(_[A-Z][A-Za-z0-9]*)*$")


def import_destination(asset: dict) -> str:
    """Pasta /Game de destino a partir do manifesto."""
    base = asset.get("engine_path")
    if not base or not base.startswith("/Game/"):
        raise ValueError(f"{asset.get('id')}: engine_path inválido: {base!r}")
    sub = CATEGORY_IMPORT.get(asset.get("category"), {}).get("subdir", "")
    return f"{base}/{sub}".rstrip("/")


def import_decision(asset: dict, existing_status_approved: bool, file_exists: bool, hash_ok: bool) -> tuple[bool, str]:
    """Decide se o asset pode ser importado. Retorna (pode, motivo)."""
    if asset.get("category") not in CATEGORY_IMPORT:
        return False, f"categoria {asset.get('category')} não importável por este script"
    if not asset.get("export_file"):
        return False, "export_file ausente"
    if not file_exists:
        return False, f"arquivo inexistente: {asset['export_file']}"
    if not hash_ok:
        return False, "hash do arquivo difere do manifesto (re-export não registrado)"
    if asset.get("status") == "approved" or existing_status_approved:
        return False, "asset aprovado: não substituir silenciosamente (crie nova versão)"
    if asset.get("status") not in {"exported", "imported"}:
        return False, f"status {asset.get('status')} não permite import (esperado exported)"
    return True, "ok"


def check_asset_name(asset_name: str, asset_class: str, is_map: bool = False) -> str | None:
    if is_map or asset_class in {"World", "Level"}:
        return None if MAP_RE.match(asset_name) else "mapa deve seguir L<NN>_<Nome>"
    prefixes = REQUIRED_PREFIX_BY_CLASS.get(asset_class)
    if prefixes is None:
        return None
    if asset_class == "Blueprint" and asset_name.startswith(("DA_", "BP_")):
        return None
    if not asset_name.startswith(prefixes):
        return f"{asset_class} deve começar com {' ou '.join(prefixes)}"
    return None


def level_problems(counts: dict[str, int], required: dict[str, int]) -> list[str]:
    """Verifica contagem mínima de atores por classe num mapa. counts = {classe: quantidade}."""
    out = []
    for cls, minimum in required.items():
        count = counts.get(cls, 0)
        if count < minimum:
            out.append(f"{cls}: {count} encontrado(s), mínimo {minimum}")
    return out

"""Leva um asset pronto das ferramentas Noct para dentro do repositorio do jogo.

3D (GLB do Forge 3D):
  python tools/noct/entregar_asset.py glb E:/game/noct-tools/forge3d/projects/jogo_resgate/assets/unreal/galao.glb --nome SM_Galao --estatico
  -> roda o bake de escala no Blender e grava assets/work/forge3d/SM_Galao.glb
  -> copia as receitas (scripts/<asset>) para assets/source/forge3d/<asset>/ (versionar)

2D (PNG do Forge 2D, com o .json do atlas se existir):
  python tools/noct/entregar_asset.py png E:/game/noct-tools/forge2d/projects/jogo_resgate/assets/hud/gasolina.png --nome T_Icone_Gasolina --pasta hud
  -> grava assets/work/forge2d/hud/T_Icone_Gasolina.png (+ .json)
  -> copia o fonte .ts para assets/source/forge2d/<pasta>/

Depois importe na Unreal com tools/unreal/import_forge_asset.py.
Blender: usa a variavel BLENDER, ou "blender" no PATH, ou o modulo bpy do Python atual.
"""
import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
BAKE = Path(__file__).resolve().parent / "bake_glb_scale.py"


def _blender_cmd():
    exe = os.environ.get("BLENDER") or shutil.which("blender")
    if exe:
        return [exe, "-b", "--python", str(BAKE), "--"]
    try:
        import bpy  # noqa: F401
        return [sys.executable, str(BAKE), "--"]
    except ImportError:
        sys.exit("[entregar] Blender nao encontrado: defina BLENDER=C:/caminho/blender.exe")


def _forge_root(p: Path, marcador: str):
    for pai in p.resolve().parents:
        if (pai / marcador).exists():
            return pai
    return None


def entregar_glb(a):
    src = Path(a.arquivo)
    nome = a.nome if a.nome.lower().endswith(".glb") else a.nome + ".glb"
    if not nome.startswith(("SM_", "SK_")):
        sys.exit("[entregar] use SM_ (estatico) ou SK_ (com esqueleto) no --nome")
    dst = REPO / "assets" / "work" / "forge3d" / nome
    dst.parent.mkdir(parents=True, exist_ok=True)
    cmd = _blender_cmd() + [str(src), str(dst)] + (["--juntar"] if a.estatico else [])
    r = subprocess.run(cmd, capture_output=True, text=True)
    linhas = [l for l in (r.stdout + r.stderr).splitlines() if "[bake]" in l]
    print("\n".join(linhas) or r.stderr[-2000:])
    if r.returncode != 0 or not dst.exists():
        sys.exit("[entregar] bake falhou")
    # receitas: <projeto>/assets/... -> <projeto>/scripts/<asset>
    projeto = _forge_root(src, "project.json")
    if projeto and a.asset:
        rec = projeto / "scripts" / a.asset
        if rec.is_dir():
            alvo = REPO / "assets" / "source" / "forge3d" / a.asset
            shutil.copytree(rec, alvo, dirs_exist_ok=True)
            print(f"[entregar] receitas copiadas para {alvo.relative_to(REPO)}")
    print(f"[entregar] OK {dst.relative_to(REPO)}")


def entregar_png(a):
    src = Path(a.arquivo)
    nome = a.nome if a.nome.lower().endswith(".png") else a.nome + ".png"
    pasta = REPO / "assets" / "work" / "forge2d" / (a.pasta or "")
    pasta.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, pasta / nome)
    atlas = src.with_suffix(".json")
    if atlas.exists():
        shutil.copy2(atlas, (pasta / nome).with_suffix(".json"))
    # fonte .ts: <projeto>/assets/<sub>.png -> <projeto>/source/<sub>.ts
    raiz = _forge_root(src, "source")
    if raiz:
        rel = src.resolve().relative_to(raiz / "assets").with_suffix(".ts")
        fonte = raiz / "source" / rel
        if fonte.exists():
            alvo = REPO / "assets" / "source" / "forge2d" / (a.pasta or "") / fonte.name
            alvo.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(fonte, alvo)
    print(f"[entregar] OK {(pasta / nome).relative_to(REPO)}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("tipo", choices=["glb", "png"])
    p.add_argument("arquivo")
    p.add_argument("--nome", required=True)
    p.add_argument("--estatico", action="store_true", help="GLB sem esqueleto: junta as pecas")
    p.add_argument("--asset", default=None, help="id do asset no Forge 3D (para copiar as receitas)")
    p.add_argument("--pasta", default=None, help="subpasta para PNG (hud, icones, vfx...)")
    a = p.parse_args()
    (entregar_glb if a.tipo == "glb" else entregar_png)(a)


if __name__ == "__main__":
    main()

"""[A-098] Procura (e, com --fix, tira) faces duplicadas e sobrepostas nos modelos do Tripo: causa de z-fighting.

Uso (Blender 5.3):
  blender -b --factory-startup --python tools/blender/check_dup_faces.py -- [--fix] [--fix-coplanar] [arquivos...]
Sem arquivos: assets/work/tripo/SM_BLD_*.fbx e SM_CON_*.fbx (os prédios/casas da cidade).
Atalho no Windows: E:\\game\\checar_faces.bat  (ou checar_faces.bat --fix)

Mede em cada malha (as caixas UCX_ ficam de fora):
  vertices_duplicados   vértices a menos de 0,1 mm de outro (Tripo costuma soltar a malha por UV)
  faces_duplicadas      faces com os mesmos vértices depois de juntar os duplicados (duas faces no mesmo lugar)
  faces_sobrepostas     faces paralelas a menos de 2 mm uma da outra, sem dividir aresta (z-fighting de verdade)
--fix          junta vértices (merge by distance 0,1 mm) e apaga faces duplicadas; regrava o FBX (cópia .bak antes)
--fix-coplanar também apaga a menor de cada par de faces sobrepostas (confira o resultado no Blender antes de usar)
Depois do --fix: reimporte na Unreal (import_user_assets.py force) e rode fix_building_collision.py de novo.
Relatório: reports/check_dup_faces.json
"""
import glob
import json
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
MERGE_DIST = 0.0001   # m
OVERLAP_DIST = 0.002  # m
PARALLEL = 0.985


def args():
    a = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    flags = {x for x in a if x.startswith("--")}
    files = [x for x in a if not x.startswith("--")]
    if not files:
        w = os.path.join(REPO, "assets", "work", "tripo")
        files = sorted(glob.glob(os.path.join(w, "SM_BLD_*.fbx")) + glob.glob(os.path.join(w, "SM_CON_*.fbx")))
    return flags, files


def analyse(bm, fix, fix_coplanar):
    import bmesh
    from mathutils.bvhtree import BVHTree

    rep = {"faces": len(bm.faces), "verts": len(bm.verts)}
    dbl = bmesh.ops.find_doubles(bm, verts=bm.verts, dist=MERGE_DIST)["targetmap"]
    rep["vertices_duplicados"] = len(dbl)
    if fix and dbl:
        bmesh.ops.weld_verts(bm, targetmap=dbl)
    # faces duplicadas: mesmo conjunto de vértices (com posições arredondadas, para valer mesmo sem juntar)
    seen, dup = {}, []
    for f in bm.faces:
        key = tuple(sorted((round(v.co.x / MERGE_DIST), round(v.co.y / MERGE_DIST), round(v.co.z / MERGE_DIST)) for v in f.verts))
        if key in seen:
            dup.append(f)
        else:
            seen[key] = f
    rep["faces_duplicadas"] = len(dup)
    if fix and dup:
        bmesh.ops.delete(bm, geom=dup, context="FACES_ONLY")
    bm.faces.ensure_lookup_table()
    bm.normal_update()
    # sobrepostas: paralelas, a menos de 2 mm, sem aresta em comum
    bvh = BVHTree.FromBMesh(bm)
    pairs = set()
    for f in bm.faces:
        c, n = f.calc_center_median(), f.normal
        if n.length < 0.5:
            continue
        for _loc, _nor, idx, _d in bvh.find_nearest_range(c, OVERLAP_DIST):
            if idx is None or idx == f.index:
                continue
            g = bm.faces[idx]
            if abs(n.dot(g.normal)) < PARALLEL:
                continue
            if set(f.verts) & set(g.verts):
                continue
            pairs.add((min(f.index, idx), max(f.index, idx)))
    rep["faces_sobrepostas"] = len(pairs)
    if pairs:
        rep["exemplo_sobreposta_m"] = [round(x, 3) for x in bm.faces[next(iter(pairs))[0]].calc_center_median()]
    if fix_coplanar and pairs:
        kill = set()
        for a, b in pairs:
            fa, fb = bm.faces[a], bm.faces[b]
            kill.add(fa if fa.calc_area() < fb.calc_area() else fb)
        bmesh.ops.delete(bm, geom=list(kill), context="FACES_ONLY")
        rep["sobrepostas_apagadas"] = len(kill)
    rep["faces_depois"] = len(bm.faces)
    return rep


def process(path, fix, fix_coplanar):
    import bmesh
    import bpy

    bpy.ops.wm.read_factory_settings(use_empty=True)
    if path.lower().endswith((".glb", ".gltf")):
        bpy.ops.import_scene.gltf(filepath=path)
    else:
        bpy.ops.import_scene.fbx(filepath=path)
    out = {}
    meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    for o in meshes:
        if o.name.upper().startswith("UCX_"):
            continue
        bm = bmesh.new()
        bm.from_mesh(o.data)
        out[o.name] = analyse(bm, fix or fix_coplanar, fix_coplanar)
        if fix or fix_coplanar:
            bm.to_mesh(o.data)
            o.data.update()
        bm.free()
    if (fix or fix_coplanar) and path.lower().endswith(".fbx"):
        changed = any(r["vertices_duplicados"] or r["faces_duplicadas"] or r.get("sobrepostas_apagadas") for r in out.values())
        if changed:
            bak = path + ".bak"
            if not os.path.exists(bak):
                shutil.copy2(path, bak)
            for x in bpy.context.scene.objects:
                x.select_set(x.type == "MESH")
            bpy.context.view_layer.objects.active = meshes[0]
            # mesmos parâmetros do prep_tripo.py (export_fbx)
            bpy.ops.export_scene.fbx(filepath=path, use_selection=True, object_types={"MESH"}, apply_unit_scale=True,
                                     mesh_smooth_type="FACE", add_leaf_bones=False, colors_type="NONE", path_mode="STRIP")
            out["_regravado"] = True
    return out


def main():
    if "--help" in sys.argv:
        print(__doc__)
        return 0
    flags, files = args()
    fix, fix_cop = "--fix" in flags, "--fix-coplanar" in flags
    rep = {"fix": fix, "fix_coplanar": fix_cop, "files": {}}
    for f in files:
        try:
            rep["files"][os.path.basename(f)] = process(f, fix, fix_cop)
        except Exception as exc:  # noqa: BLE001
            rep["files"][os.path.basename(f)] = {"erro": str(exc)}
        r = rep["files"][os.path.basename(f)]
        tot = {k: sum(v.get(k, 0) for v in r.values() if isinstance(v, dict)) for k in
               ("vertices_duplicados", "faces_duplicadas", "faces_sobrepostas")}
        print(f"[faces] {os.path.basename(f)}: {tot}{' (regravado)' if r.get('_regravado') else ''}")
    os.makedirs(os.path.join(REPO, "reports"), exist_ok=True)
    with open(os.path.join(REPO, "reports", "check_dup_faces.json"), "w", encoding="utf-8") as fh:
        json.dump(rep, fh, ensure_ascii=False, indent=1)
    print("[faces] relatório em reports/check_dup_faces.json")
    return 0


if __name__ == "__main__":
    main()

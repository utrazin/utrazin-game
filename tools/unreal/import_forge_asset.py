"""Importa na Unreal um asset gerado pelas ferramentas Noct (GLB 3D ou PNG 2D)
e ja confere/conserta o que costuma quebrar neste projeto.

Rodar na caixa Cmd do editor (Python), por exemplo:
  py "E:/game/utrazin-game/tools/unreal/import_forge_asset.py" --arquivo "E:/game/utrazin-game/assets/work/forge3d/SM_Galao.glb" --destino /Game/Forge/Props
  py ".../import_forge_asset.py" --arquivo ".../assets/work/forge2d/hud/T_Icone_Gasolina.png" --destino /Game/UI/Icones --ui

O que ele faz:
  1. Importa o arquivo (Interchange; GLB e PNG).
  2. StaticMesh: confere o tamanho (avisa se parece 100x grande ou pequeno demais)
     e cria colisao simples (caixa) se nao veio nenhuma. Ver A-078: UCX nao vira
     colisao na importacao deste projeto, entao NUNCA confiar na colisao do arquivo.
  3. SkeletalMesh: confere a escala do osso raiz na pose de referencia (o problema
     do Hips em escala 100 dos zumbis) e se tem Physics Asset (ragdoll).
  4. Textura com --ui: compressao de interface, sem mipmaps, grupo UI.
  5. Salva tudo e escreve um relatorio em Saved/ForgeImport/<nome>.json.

O GLB 3D precisa ter passado antes por tools/noct/bake_glb_scale.py
(o Forge 3D exporta com escala 0.0625 no no raiz). O script recusa GLB sem o
sufixo de conferencia se --exigir-bake estiver ligado (padrao: so avisa).
"""
import argparse
import json
import os
import sys

import unreal


def _args():
    p = argparse.ArgumentParser()
    p.add_argument("--arquivo", required=True, help="Caminho do .glb ou .png no disco")
    p.add_argument("--destino", default="/Game/Forge", help="Pasta de destino no Content Browser")
    p.add_argument("--nome", default=None, help="Nome do asset (padrao: nome do arquivo)")
    p.add_argument("--ui", action="store_true", help="Textura de HUD/UI")
    p.add_argument("--sem-colisao", action="store_true", help="Nao criar colisao automatica")
    p.add_argument("--tamanho-esperado-cm", type=float, default=None,
                   help="Maior lado esperado em cm (ex.: 51 para o galao). So para conferir.")
    return p.parse_args(sys.argv[1:])


def _importar(arquivo, destino, nome):
    task = unreal.AssetImportTask()
    task.filename = arquivo
    task.destination_path = destino
    if nome:
        task.destination_name = nome
    task.automated = True
    task.replace_existing = True
    task.save = True
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    caminhos = list(task.imported_object_paths or [])
    return [unreal.EditorAssetLibrary.load_asset(c) for c in caminhos]


def _conferir_static(mesh, args, rel):
    caixa = mesh.get_bounding_box()
    tam = caixa.max - caixa.min
    maior = max(tam.x, tam.y, tam.z)
    info = {"tipo": "StaticMesh", "asset": mesh.get_path_name(),
            "tamanho_cm": [round(tam.x, 1), round(tam.y, 1), round(tam.z, 1)]}
    if maior > 5000:
        info["aviso_escala"] = "Maior lado acima de 50 m: provavelmente faltou o bake (escala 0.0625) ou veio 100x."
    elif maior < 1:
        info["aviso_escala"] = "Maior lado abaixo de 1 cm: provavelmente unidade errada."
    if args.tamanho_esperado_cm:
        razao = maior / args.tamanho_esperado_cm
        info["razao_tamanho"] = round(razao, 3)
        if not 0.8 <= razao <= 1.25:
            info["aviso_tamanho"] = f"Esperado ~{args.tamanho_esperado_cm} cm, veio {maior:.1f} cm."

    sub = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
    n = sub.get_simple_collision_count(mesh)
    info["colisao_simples_antes"] = n
    if n == 0 and not args.sem_colisao:
        sub.add_simple_collisions(mesh, unreal.ScriptingCollisionShapeType.BOX)
        info["colisao_simples_depois"] = sub.get_simple_collision_count(mesh)
        info["colisao"] = "caixa criada automaticamente (trocar por Complex as Simple se for oco, ex.: construcao)"
    unreal.EditorAssetLibrary.save_loaded_asset(mesh)
    rel.append(info)


def _conferir_skeletal(mesh, rel):
    info = {"tipo": "SkeletalMesh", "asset": mesh.get_path_name()}
    try:
        info["physics_asset"] = bool(mesh.get_editor_property("physics_asset"))
    except Exception as e:  # propriedade pode mudar de nome entre versoes
        info["physics_asset"] = f"nao conferido ({e})"
    if info["physics_asset"] is False:
        info["aviso_physics"] = "Sem Physics Asset: ragdoll nao funciona. Clique direito na malha > Create > Physics Asset."
    try:
        esqueleto = mesh.get_editor_property("skeleton")
        pose = unreal.AnimPoseExtensions.get_reference_pose(esqueleto)
        ossos = unreal.AnimPoseExtensions.get_bone_names(pose)
        raiz = ossos[0]
        t = unreal.AnimPoseExtensions.get_bone_pose(pose, raiz, unreal.AnimPoseSpaces.LOCAL)
        esc = t.scale3d
        info["osso_raiz"] = str(raiz)
        info["escala_osso_raiz"] = [round(esc.x, 4), round(esc.y, 4), round(esc.z, 4)]
        if max(abs(esc.x - 1), abs(esc.y - 1), abs(esc.z - 1)) > 0.01:
            info["aviso_escala"] = ("Osso raiz com escala diferente de 1 (o mesmo problema do Hips 100 dos zumbis). "
                                    "Rode tools/noct/bake_glb_scale.py no GLB e importe de novo.")
    except Exception as e:
        info["escala_osso_raiz"] = f"nao conferido ({e})"
    rel.append(info)


def _conferir_textura(tex, args, rel):
    info = {"tipo": "Texture2D", "asset": tex.get_path_name()}
    if args.ui:
        tex.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_EDITOR_ICON)
        tex.set_editor_property("mip_gen_settings", unreal.TextureMipGenSettings.TMGS_NO_MIPMAPS)
        tex.set_editor_property("lod_group", unreal.TextureGroup.TEXTUREGROUP_UI)
        tex.set_editor_property("never_stream", True)
        info["ui"] = "compressao UserInterface2D, sem mipmaps, grupo UI"
    unreal.EditorAssetLibrary.save_loaded_asset(tex)
    rel.append(info)


def main():
    args = _args()
    arquivo = args.arquivo.replace("\\", "/")
    if not os.path.isfile(arquivo):
        unreal.log_error(f"[forge-import] arquivo nao existe: {arquivo}")
        return
    if arquivo.lower().endswith(".glb") and not os.path.basename(arquivo).startswith(("SM_", "SK_")):
        unreal.log_warning("[forge-import] Use o prefixo SM_ (estatico) ou SK_ (com esqueleto) no nome do GLB.")

    assets = _importar(arquivo, args.destino, args.nome)
    rel = []
    for a in assets:
        if isinstance(a, unreal.StaticMesh):
            _conferir_static(a, args, rel)
        elif isinstance(a, unreal.SkeletalMesh):
            _conferir_skeletal(a, rel)
        elif isinstance(a, unreal.Texture2D):
            _conferir_textura(a, args, rel)
        elif a is not None:
            rel.append({"tipo": a.get_class().get_name(), "asset": a.get_path_name()})

    estaticas = [r for r in rel if r["tipo"] == "StaticMesh"]
    if len(estaticas) > 1:
        unreal.log_warning(f"[forge-import] {len(estaticas)} StaticMesh separadas. Para prop, gere o GLB com "
                           "bake_glb_scale.py --juntar (vira uma malha so).")

    pasta = os.path.join(unreal.Paths.project_saved_dir(), "ForgeImport")
    os.makedirs(pasta, exist_ok=True)
    nome = args.nome or os.path.splitext(os.path.basename(arquivo))[0]
    with open(os.path.join(pasta, f"{nome}.json"), "w", encoding="utf-8") as f:
        json.dump({"arquivo": arquivo, "destino": args.destino, "assets": rel}, f, ensure_ascii=False, indent=2)
    for r in rel:
        avisos = [v for k, v in r.items() if k.startswith("aviso")]
        msg = f"[forge-import] {r['tipo']} {r['asset']}"
        (unreal.log_warning if avisos else unreal.log)(msg + ("  AVISO: " + " | ".join(avisos) if avisos else "  OK"))
    if not rel:
        unreal.log_error("[forge-import] nada foi importado. Veja o Output Log (Interchange).")


main()

# blender/

- Cenas: `scenes/<categoria>/<ASSET-ID>_<nome>_v001.blend`. Nunca sobrescreva versão aprovada.
- Unidades métricas, escala 1.0, frente -Y, transformações aplicadas. Coleções `EXPORT`, `WIP`, `REF`.
- Esqueleto com nomes UE5 (`tools/blender/ue5_required_bones.txt`). Armature chamada `root`.
- Colisão `UCX_<Mesh>_NN`. LODs `<Mesh>_LODn`.
- Rode `validate_scene.py` e `validate_rig.py` antes de exportar; export só com `export_assets.py` e preset de `export-presets/`.
- Lock LFS antes de editar `.blend` (`git lfs lock`). Um agente por arquivo.
- Blender MCP desabilitado por padrão (ver `docs/pipeline/MCP_SECURITY.md`).

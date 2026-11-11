# Regras de arquivos Blender e assets

- Arquivo: `<ASSET-ID>_<Nome>_v<NNN>.blend` (ex.: `VEH-001_SUV_v003.blend`).
- Objetos de export: mesmo prefixo da Unreal (`SM_`, `SK_`), colisão `UCX_<Mesh>_NN`, LOD `<Mesh>_LOD<n>`.
- Armature: `root`; ossos com nomes do esqueleto UE5; sem leaf bones.
- Coleções: `EXPORT`, `WIP`, `REF`.
- Unidades métricas, escala 1.0, transformações aplicadas, frente -Y.
- Materiais com nome igual ao da Unreal (`M_`/`MI_`), sem slots vazios.
- Texturas embutidas proibidas no `.blend` final: referenciadas de `assets/work/` ou `assets/final/textures/`.
- Toda versão exportada tem hash no manifesto; versão aprovada nunca é sobrescrita.

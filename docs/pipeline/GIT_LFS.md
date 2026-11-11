# Git LFS

## O que vai para LFS

Definido em `.gitattributes`: `.uasset`, `.umap`, `.blend`, `.fbx`, `.glb`, `.obj`, `.abc`, `.bvh`, áudio (`.wav`, `.flac`, `.ogg`, `.mp3`), fontes de imagem (`.psd`, `.kra`, `.xcf`, `.exr`, `.tga`, `.tif`, `.hdr`), PNG/JPG apenas em `assets/` e `design/concepts/`, fontes tipográficas e vídeo.

Scripts, docs, `.json`, `.ini`, C++ e `.gltf` (texto) **não** vão para LFS.

## Limites (GitHub, plano gratuito)

O plano gratuito do GitHub inclui cota pequena de armazenamento e banda LFS (historicamente 1 GiB cada; **confira o valor atual** em https://docs.github.com/billing/managing-billing-for-git-large-file-storage). Um projeto Unreal ultrapassa isso rápido.

## Estratégia

1. **Fase M0 a M1**: LFS no GitHub é suficiente (pouco binário).
2. Monitorar: `git lfs ls-files -s` e a página de billing do GitHub.
3. Ao se aproximar do limite, opções gratuitas:
   - Manter `.blend`/fontes pesadas fora do Git, com backup próprio (ver `BACKUP_RECOVERY.md`), e versionar só exports.
   - Servidor LFS próprio / Git em servidor local (ex.: Gitea no próprio PC ou NAS).
4. Nunca commitar `Saved/`, `Intermediate/`, `DerivedDataCache/` (já no `.gitignore`).

## Locks

```bash
git lfs lock unreal/JogoResgate/Content/Levels/L01_Zombies/L01_Zombies.umap
git lfs locks
git lfs unlock <arquivo>
```

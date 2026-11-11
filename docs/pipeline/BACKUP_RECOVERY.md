# Backup e recuperação

## O que proteger

| Dado | Onde | Frequência |
|---|---|---|
| Repositório (código, docs, Content) | GitHub (`origin`) | a cada push |
| `.blend` e fontes grandes | Git LFS **e** backup externo | diário durante produção |
| Configurações locais (`.mcp.json`, `settings.local.json`) | backup externo | ao alterar |
| Saves de teste | não precisam de backup | n/a |

## Regra 3-2-1

3 cópias, 2 mídias, 1 fora de casa. Sugestão gratuita: SSD E: (trabalho) + HD externo + nuvem gratuita para arquivos-fonte críticos.

## Rotina

```powershell
# Antes de qualquer automação em binários (MCP, scripts em lote)
git status            # árvore limpa
git lfs locks         # ninguém editando
robocopy E:\game\utrazin-game\blender D:\backup\utrazin-game\blender /MIR /XD autosave
```

## Recuperação

- Arquivo apagado/alterado: `git restore <arquivo>` ou `git checkout <commit> -- <arquivo>`.
- `.blend` corrompido: `.blend1` (backup automático do Blender, ignorado pelo Git) ou backup externo.
- Asset Unreal quebrado: `git log -- <caminho.uasset>` e restaurar versão anterior; rodar "Fix Up Redirectors".
- Repositório local destruído: `git clone` + `git lfs pull`.

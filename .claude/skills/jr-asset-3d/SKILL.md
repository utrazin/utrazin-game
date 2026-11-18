---
name: jr-asset-3d
description: Gerar um asset 3D do Jogo de Resgate com o Noct Asset Forge 3D (props, moveis, pecas de cenario, personagens estilizados com esqueleto, animacao de objetos) e levar ate a Unreal com escala e colisao certas.
---

# Asset 3D com o Forge 3D

Ferramenta em `E:\game\noct-tools\forge3d`. Antes de escrever receita, leia as skills dela:
`forge3d\AGENTS.md` e `forge3d\.agents\skills\forge-3d-orchestrator\SKILL.md` (ela manda para model, texture, animation, export). Siga as regras dela (por exemplo: nunca `python -c`, so rodar estagios pedidos).

Projeto do jogo dentro do forge: `projects\jogo_resgate` (um projeto, varios assets). Nao criar um projeto por asset.

## Passo a passo

1. **Combinar o pedido**: o que e, tamanho real em cm, onde aparece no mapa, se tem animacao. Converta para unidades do forge (16 = 1 m). Se tiver foto de referencia, salve em `projects\jogo_resgate\reference.png`.
2. **Criar o asset** (so na primeira vez):
   `py -3.12 -m Tools.forge asset init projects/jogo_resgate --asset <id> --mode free`
3. **Modelo**: escrever `projects/jogo_resgate/scripts/<id>/generate_model.py` e rodar
   `py -3.12 -m Tools.forge model projects/jogo_resgate --asset <id>`. Precisa sair `PASS`.
   Conferir: `py -3.12 -m Tools.forge inspect projects/jogo_resgate --asset <id> --validate --summary`.
4. **Ver**: `py -3.12 -m Tools.forge preview projects/jogo_resgate --asset <id>` (render de argila) ou `viewer.bat`. Mostrar a imagem ao usuario.
5. **UV**: props pequenos precisam de densidade maior:
   `py -3.12 -m Tools.forge uv projects/jogo_resgate --asset <id> --uv-scale 16`
   (com `--uv-scale 1` peca fina da erro "polygon collapses").
6. **Textura**: `generate_texture.py` e `py -3.12 -m Tools.forge texture projects/jogo_resgate --asset <id>`. Para o visual liso (nao pixel art), `texture_filter: linear` no asset.
7. **Animacao** (so se pedida): `generate_animation.py`. Osso usa `clip.bone("nome")`; grupo rigido usa `clip.group("nome")`. Conferir com `--check` e `--inspect`.
8. **Exportar**: `py -3.12 -m Tools.forge export projects/jogo_resgate --asset <id> --output unreal/<id>.glb --overwrite` (`--animations ""` se nao quiser clipes).
9. **Entregar no repositorio** (faz o bake de escala no Blender e copia as receitas):
   - prop sem esqueleto: `python tools/noct/entregar_asset.py glb <forge3d>/projects/jogo_resgate/assets/unreal/<id>.glb --nome SM_<Nome> --estatico --asset <id>`
   - com esqueleto: `... --nome SK_<Nome> --asset <id>` (sem `--estatico`)
10. **Importar na Unreal** (caixa Cmd do editor):
   `py "E:/game/utrazin-game/tools/unreal/import_forge_asset.py" --arquivo "E:/game/utrazin-game/assets/work/forge3d/SM_<Nome>.glb" --destino /Game/Forge/Props --tamanho-esperado-cm <maior lado>`
   Ler o relatorio em `unreal/JogoResgate/Saved/ForgeImport/SM_<Nome>.json`. Se tiver AVISO, consertar antes de colocar no mapa.
11. **Colocar no mapa** pelos scripts de nivel do projeto (respeitar o registro anti-sobreposicao, A-062) e testar no Play. Conferir a frente do objeto (o forge usa frente em +Z; ainda nao confirmado como chega na Unreal, ver A-079).

## Armadilhas ja vistas

- `add_box(..., no_overlap_check=True)` nao existe; pecas encostadas levam `tags=("assembly:<id>",)`.
- O GLB do forge vem em pecas separadas; `--estatico` no entregar junta tudo numa malha so (vira 1 StaticMesh).
- Escala: o GLB cru tem `scale 0.0625` no no raiz e ossos em unidades do forge. O bake deixa tudo em metros com escala 1. Nunca importar o GLB cru.
- Colisao nunca vem do arquivo: o import cria caixa. Construcao oca precisa de Complex as Simple.
- Personagem com esqueleto: depois de importar, conferir `escala_osso_raiz` = 1 e `physics_asset` no relatorio.

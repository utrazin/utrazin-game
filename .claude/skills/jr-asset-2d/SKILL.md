---
name: jr-asset-2d
description: Gerar arte 2D do Jogo de Resgate com o Noct Asset Forge 2D v2.5 (icones de HUD, roda de itens, pinos do minimapa, bussola, placas e cartazes para decal, sprites animados de fogo, fumaca e faisca) e importar na Unreal.
---

# Arte 2D com o Forge 2D

Ferramenta em `E:\game\noct-tools\forge2d`. Antes de escrever codigo de asset, leia:
`.agents\skills\noct-asset-forge\SKILL.md` (regras de producao) e `.agents\skills\noct-review\SKILL.md` (conferencia). Primeira vez na maquina: `.agents\skills\noct-setup\SKILL.md`.

Projeto do jogo dentro do forge: `projects\jogo_resgate`. A paleta e os tracos ficam em `projects\jogo_resgate\source\_theme.ts`: toda cor sai dali (o HUD atual do jogo e a referencia; pedir print se nao souber as cores).

## Passo a passo

1. Projeto (so uma vez): `npm run new-project -- jogo_resgate --style`.
2. Asset:
   - icone vetorial: `npm run new-asset -- jogo_resgate hud/gasolina --engine brush --size 64x64`
   - pixel art: `--engine pixel --size 32x32`
   - animado: `--frames 8 --fps 12` (exporta tira horizontal + JSON com `frame_0..N`)
3. Escrever o `render()` em `projects/jogo_resgate/source/<subpasta>.ts` e checar tipos: `npm run check -- jogo_resgate`.
4. Ver ao vivo: `dev.bat` (ou `npm run view`) e abrir `localhost:5173`. Para ver varios juntos (barra de vida, grade da roda de itens), pedir um sandbox: `npm run new-sandbox -- jogo_resgate`.
5. Mockup primeiro, final depois: exportar e mostrar ao usuario antes de entregar.
   `npm run export -- jogo_resgate hud/gasolina`. Spritesheet agrupada: ver opcoes de export (grade uniforme ou compacta).
6. Entregar no repositorio:
   `python tools/noct/entregar_asset.py png <forge2d>/projects/jogo_resgate/assets/hud/gasolina.png --nome T_Icone_Gasolina --pasta hud`
7. Importar na Unreal (caixa Cmd):
   `py ".../tools/unreal/import_forge_asset.py" --arquivo ".../assets/work/forge2d/hud/T_Icone_Gasolina.png" --destino /Game/UI/Icones --ui`
   `--ui` deixa compressao de interface, sem mipmap e grupo UI.

## Onde cada coisa entra no jogo

| Arte | Uso na Unreal |
|---|---|
| Icones de item / roda de itens | `UI/JRHUD` e `make_item_wheel_ui.py` (trocar os icones atuais) |
| Pinos do objetivo, minimapa, bussola | minimapa v4 (A-067) |
| Medidor de gasolina | HUD (A-075) |
| Placas, cartazes, pichacoes | Decal material sobre paredes dos interiores (A-070, A-076) |
| Fogo, fumaca, faisca (animado) | Flipbook ou Niagara SubUV: linhas x colunas iguais ao atlas JSON |

Tamanho: icones exportam em escala 2 (64 logicos = 128 px). Para HUD em 4K, gerar 128 logicos.

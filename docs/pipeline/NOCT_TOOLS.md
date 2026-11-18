# Ferramentas Noct no pipeline do Jogo de Resgate (A-079)

Data: 17/11/2026. Complementa `PIPELINE_V2.md`.

## Ideia

Em vez do Claude "chutar" geometria ou desenhar imagem na mao, ele escreve uma receita pequena (Python no 3D, TypeScript no 2D), a ferramenta gera o arquivo, o Claude confere (render, medidas, validacao) e so entao o asset entra na Unreal por um script que ja conserta escala e colisao. A receita fica versionada no repositorio, entao da para mudar cor, tamanho ou forma e gerar de novo.

## As 4 ferramentas

| Ferramenta | O que faz | Entra | Sai | Licenca |
|---|---|---|---|---|
| Noct Asset Forge 3D (bb-v2) | Modelagem procedural em Python, UV, pintura, esqueleto, animacao | receita `.py` | `.bbmodel` (editavel) e **GLB** | Uso livre inclusive comercial; nao redistribuir a ferramenta. O que ela gera e nosso. |
| Noct Asset Forge 2D (v2.5) | Vetor procedural (brush) e pixel art, animacao por frames, sandboxes | receita `.ts` | **PNG 2x** + JSON de atlas | Igual ao 3D. |
| Noct3DViewer | Visualizador/inspetor de FBX/GLB, ossos, timeline, retarget automatico (estilo Unity) | FBX/GLB (Mixamo etc.) | nada (so olhar) | **So uso pessoal e nao comercial.** |
| GamejamProject | 8 skills de agente (designer, critico, diretor de arte, QA...) + asset-kit Three.js/Manifold/SDF | pedido | docs, GLB/PNG | Sem arquivo de licenca: tratar como privado. |

Instaladas FORA do repositorio em `E:\game\noct-tools\` (`tools\noct\setup_noct_tools.ps1`), porque o repositorio vai para o GitHub e as licencas proibem redistribuir.

## Mapa: criacao do jogo, passo a passo, e onde cada ferramenta entra

| # | Etapa | Hoje no projeto | Com as ferramentas Noct | Skill |
|---|---|---|---|---|
| 1 | Ideia e design de mecanica | docs em `docs/gameplay`, decisoes em `OPEN_DECISIONS.md` | Critico red team do GamejamProject estressa a proposta antes de programar | `jr-design-critica` |
| 2 | Direcao de arte | implicita (Tripo + texturas) | Briefing de assets (diretor de arte) + paleta unica no `_theme.ts` do 2D e no tema do 3D | `jr-design-critica` |
| 3 | Terreno e layout do L01 | `gen_l01_v3.py` (Blender) + `build_l01.py` | Sem mudanca (Forge nao faz terreno) | |
| 4 | Props e moveis (interiores, acampamento, posto) | Tripo, Blender, primitivas | **Forge 3D**: galao, caixas, prateleiras, barricadas, placas 3D, pecas de carro. Receita reaproveitavel, tamanho exato em cm | `jr-asset-3d` |
| 5 | Personagens | Tripo + rig Blender + Mixamo | Continua igual para os realistas. Forge 3D so para estilizados/low poly. **Noct3DViewer** para conferir rig e animacao antes de importar | `jr-inspecionar-animacao` |
| 6 | Animacao de objetos | C++ (`AJRDoor`) e timelines | Forge 3D anima porta, tampa de bau, bandeira, ventilador e exporta o clipe no GLB | `jr-asset-3d` |
| 7 | Animacao de personagem | Mixamo + retarget + `fix_zombie_anim_scale.py` | Noct3DViewer confere o FBX antes (escala do Hips, pe deslizando) | `jr-inspecionar-animacao` |
| 8 | Texturas | Tripo, materiais `fix_l01_materiais.py` | Forge 3D pinta textura no proprio modelo; Forge 2D faz decals (cartaz, placa, pichacao) | `jr-asset-3d`, `jr-asset-2d` |
| 9 | HUD e UI | `JRHUD.cpp`, `make_item_wheel_ui.py`, minimapa v4 | **Forge 2D**: icones da roda de itens, pinos, bussola, medidor de gasolina, tudo na mesma paleta | `jr-asset-2d` |
| 10 | Efeitos (VFX) | Niagara simples | Forge 2D gera spritesheet animada (fogo, fumaca, faisca, sangue estilizado) para Flipbook/SubUV | `jr-asset-2d` |
| 11 | Importacao na Unreal | scripts por tipo, colisao consertada depois (A-078) | `entregar_asset.py` (bake de escala) + `import_forge_asset.py` (tamanho, colisao, osso raiz, Physics Asset, relatorio) | todas |
| 12 | Montagem no mapa | `build_l01.py`, registro anti-sobreposicao | Sem mudanca: assets novos entram pelos mesmos scripts | |
| 13 | QA | `docs/qa/reports`, Play pela tela | Checklist do `game-reviewer-qa` adaptado; prints do Noct3DViewer anexados | `jr-design-critica` |

## Fluxo de um asset 3D (exemplo testado: galao de gasolina)

```
receita (forge3d/projects/jogo_resgate/scripts/galao/*.py)
  -> forge model / uv --uv-scale 16 / texture / export      (GLB em unidades do forge, scale 0.0625 no raiz)
  -> tools/noct/entregar_asset.py glb ... --estatico         (bake no Blender: metros, escala 1, 1 malha)
       grava assets/work/forge3d/SM_Galao.glb
       copia a receita para assets/source/forge3d/galao/
  -> tools/unreal/import_forge_asset.py                       (Unreal: tamanho, colisao, relatorio)
  -> scripts de nivel -> Play
```

Resultado do teste na nuvem (17/11): modelo PASS, UV PASS, textura PASS, export PASS; bounds depois do bake 34 x 17 x 51,5 cm (real: 34 x 17 x 47 cm de corpo + alca); 7 pecas juntadas em 1 malha. Rig de teste (pernas com 5 ossos e clipe `walk`): antes do bake ossos em unidades do forge (hips em y=15) com escala 0.0625 no raiz; depois, hips em 0,938 m e escala 1 em todos os nos, clipe preservado.

## Fluxo de um asset 2D (exemplo testado: icone de gasolina)

```
receita (forge2d/projects/jogo_resgate/source/hud/gasolina.ts)
  -> npm run check / npm run export                           (PNG 128x128, escala 2)
  -> tools/noct/entregar_asset.py png ... --pasta hud         (assets/work/forge2d/hud/T_Icone_Gasolina.png)
  -> tools/unreal/import_forge_asset.py --ui                  (compressao UI, sem mip)
  -> JRHUD
```

## O que NAO foi feito ainda (honesto)

- Nada disso rodou no PC do usuario nem na Unreal. Testado so na nuvem (Linux, Python 3.12, bpy 5.3, Chromium do Playwright do container).
- `import_forge_asset.py` nunca rodou na Unreal 5.8: nomes de API do Interchange/AnimPose podem precisar de ajuste no primeiro uso.
- Nao confirmado: como a frente (+Z do forge) chega na Unreal; se o Interchange cria Physics Asset sozinho para GLB com esqueleto.
- Noct3DViewer e Windows: nao testado (so lido o manual).
- Os assets existentes nao foram trocados. Os exemplos (galao, icone) sao prova de pipeline, nao arte final.

## Decisoes abertas novas

- **OD-P09** Estilo: o Forge 3D gera low poly/estilizado. Misturar com os modelos realistas do Tripo, ou usar o Forge so para props de fundo, ou mudar o jogo todo para estilizado?
- **OD-P10** Noct3DViewer e so nao comercial. O jogo vai ser vendido? Se sim, usar so enquanto for projeto pessoal.

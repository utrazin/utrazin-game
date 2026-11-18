---
name: jr-design-critica
description: Revisar uma mecanica ou feature do Jogo de Resgate usando as skills de design do GamejamProject (critico red team, QA, diretor de arte), adaptadas para Unreal e para os documentos que o projeto ja tem.
---

# Critica de design e QA com as skills do GamejamProject

As skills originais ficam em `E:\game\noct-tools\gamejam\.agents\skills\`. Elas foram escritas para jogos pequenos em qualquer engine e comecam perguntando engine, pasta e escopo: aqui isso ja esta decidido (Unreal 5.8.4, C++ modulo `JogoResgate`, prefixo `JR`, mapa L01). Nao refazer o intake nem criar `GDD.md` novo do zero.

Leia so a skill da fase que estiver fazendo:

| Fase | Skill original | Como adaptar aqui |
|---|---|---|
| Ideia nova de mecanica | `game-designer` (+ `references/techniques_action_arcade.md`) | Escrever a proposta em `docs/gameplay/`, com verbos, recursos e loop. Game feel e prioridade do usuario (`docs/gameplay/GAME_FEEL.md`). |
| Estressar a proposta | `game-design-critic` (+ `references/empirical_heuristics.md`) | Rodar como subagente isolado sobre o doc. Saida: lista de mecanicas orfas, loops rasos e o que cortar, com opcoes A/B/C para o usuario decidir em `OPEN_DECISIONS.md`. |
| Visual | `game-art-director` (`styles/style_dark_earthy.md` e `style_industrial_rust.md` sao os mais proximos do jogo) | Gerar o briefing de assets que depois vira pedido para `jr-asset-3d` e `jr-asset-2d`. |
| Testar | `game-reviewer-qa` | O "rodar o jogo" aqui e o Play na Unreal pela tela do usuario. Relatorio em `docs/qa/reports/`, separando visto no Play / so compilado / pendente. |

O `tools/asset-kit` do GamejamProject (Three.js, Manifold, SDF) serve para formas organicas que o Forge 3D faz mal (pedras, raizes, escombros arredondados). Usar so quando o Forge 3D nao der conta, e entregar o GLB pelo mesmo `tools/noct/entregar_asset.py` (ele ja vem em metros; rodar o bake mesmo assim para juntar as pecas).

O GamejamProject nao tem arquivo de licenca: tratar como privado, nunca copiar para o repositorio.

---
name: gamedev-router
description: Use no INÍCIO de qualquer tarefa do jogo para decidir engine, disciplina, skills, agentes e ferramentas a carregar. Também use quando houver dúvida sobre qual skill ou agente serve.
---

# /gamedev-router

Despachante da pipeline. Não ensina API de engine: identifica o contexto e manda ler só as skills necessárias.

## Pré-requisitos
- Pedido do usuário em mãos e acesso de leitura ao repositório
- Tabela completa em `references/routing-table.md` (lida só quando a tabela abaixo não resolver)

## Passos
1. **Projeto e engine**: procure `*.uproject` (hoje `unreal/JogoResgate/JogoResgate.uproject`). Leia `EngineAssociation` e compare com `CLAUDE.md`. Se houver outro projeto (`project.godot`, `Assets/ProjectSettings`), preserve cada um e use a engine do projeto tocado. Nunca troque a versão da engine para acomodar uma ferramenta.
2. **Classifique a tarefa** em uma ou mais disciplinas: gameplay, IA, arte 3D, animação, animação facial, áudio/música, UI/HUD, nível/mapa, câmera/cinemática, materiais/iluminação, performance, QA, licenças.
3. **Resolva o conjunto mínimo**: 1 agente líder + no máximo 3 skills de apoio. Tarefa simples (um valor, um bug de uma linha) não carrega skill nenhuma.
4. **Ferramentas e MCPs**: confira o que existe de verdade (`.mcp.json` presente? `blender` no PATH? servidor ACE-Step respondendo em `/health`? Audio2Face instalado?). Ferramenta opcional ausente não bloqueia: use o caminho alternativo documentado.
5. **Tarefa multidisciplinar** (3 ou mais áreas, ou 2 agentes mexendo em arquivos próximos): passe o controle para `/team-orchestrate`.
6. **Antes de declarar pronto**: `/visual-qa-gate` quando o resultado é visível no jogo.
7. Ordem de leitura: engine > disciplina > especialidade > workflow. Leia `references/` de uma skill só sob demanda.

## Tabela rápida (problema > líder > skills)
| Pedido | Agente líder | Skills |
|---|---|---|
| Mão fora do lugar, arma, pose, primeira pessoa | `animation-specialist` | `character-pose-validation`, `blender-rigging` |
| Prédio sem interior, loja vazia, container oco | `level-designer` | `enterable-interior`, `blender-prop-artist`, `level-design` |
| Câmera ruim, troca de câmera, cutscene | `cinematics-director` | `camera-shots-and-cutscenes`, `camera-systems` |
| Início do jogo, tela de start, nave caindo | `cinematics-director` | `intro-sequence`, `camera-shots-and-cutscenes` |
| Mapa vazio, morros, objetos soltos, sobreposição | `world-builder` | `map-composition`, `procedural-gen`, `level-design` |
| Brilho estourado, materiais, luz, céu | `technical-artist` | `material-lighting-audit`, `shader-programming` |
| Música, trilha, ambiente sonoro | `sound-designer` | `music-production-acestep`, `audio-design` |
| Efeitos sonoros ruins ou fora de contexto | `sound-designer` | `audio-design` |
| Lip sync, diálogo falado, expressão facial | `animation-specialist` | `facial-animation-lipsync`, `dialogue-systems` |
| Modelagem 3D, asset novo, export | `blender-specialist` | `blender-director` e a especialista |
| IA de inimigo | `enemy-ai-engineer` | `game-ai`, `unreal-behavior-trees` |
| Desempenho | `performance-engineer` | `performance-optimization` |
| Licença de qualquer coisa de terceiros | `asset-license-auditor` | `/audit-licenses` |

## Ferramentas necessárias
- Leitura do repositório (Read, Glob, Grep)

## Diretórios afetados
- Nenhum (somente leitura)

## Verificações
- O conjunto escolhido tem 1 agente líder e no máximo 3 skills de apoio
- Nenhum pré-requisito opcional (ACE-Step, Audio2Face, Blender MCP) foi tratado como obrigatório
- Todo nome de skill/agente citado existe (`python tools/pipeline/validate_pipeline.py`)

## Erros comuns
- Carregar dezenas de skills para uma tarefa pequena
- Assumir que o Blender MCP está ligado só porque existe `.mcp.json.example`
- Trocar versão da engine para caber um plugin

## Critério de sucesso
Plano de uma tela: agente líder, skills, ferramentas disponíveis, ordem e como validar. A execução começa em seguida.

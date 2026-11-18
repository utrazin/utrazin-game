# Tabela de roteamento completa

Todo skill e agente instalado aparece aqui (o validador confere). Lider = agente que coordena.

## Orquestração e qualidade
| Item | Quando |
|---|---|
| `gamedev-router` | início de qualquer tarefa |
| `team-orchestrate` | 3+ especialidades |
| `visual-qa-gate` | antes de aprovar algo visível |
| `validate-pipeline` | depois de editar skills/agentes |

## Skills do projeto (já existentes)
| Skill | Quando |
|---|---|
| `create-asset`, `generate-concept`, `review-art-style` | ciclo de arte e conceito |
| `export-blender`, `import-unreal`, `validate-asset` | ciclo de assets |
| `add-level`, `add-character`, `add-skin`, `add-enemy` | conteúdo de jogo |
| `test-gameplay`, `profile-performance` | testes e desempenho |
| `audit-licenses`, `prepare-release` | licenças e release |

## Skills originais do projeto (pipeline v2)
| Skill | Líder | Quando |
|---|---|---|
| `enterable-interior` | `level-designer` | prédios entráveis |
| `map-composition` | `world-builder` | mapa, morros, vegetação, props |
| `camera-shots-and-cutscenes` | `cinematics-director` | câmera e cutscenes |
| `intro-sequence` | `cinematics-director` | abertura |
| `character-pose-validation` | `animation-specialist` | mãos, armas, primeira pessoa |
| `material-lighting-audit` | `technical-artist` | brilho, materiais, luzes |
| `music-production-acestep` | `sound-designer` | música (opcional) |
| `facial-animation-lipsync` | `animation-specialist` | rosto e fala (opcional) |

## Skills de engine e disciplina (origem: awesome-gamedev-agent-skills)
| Skill | Quando |
|---|---|
| `unreal-blueprints`, `unreal-cpp-gameplay`, `unreal-enhanced-input`, `unreal-behavior-trees`, `unreal-niagara`, `unreal-packaging` | Unreal (detectada por `*.uproject`) |
| `audio-design` | buses, ducking, SFX, música adaptativa |
| `camera-systems` | braço de câmera, colisão, zoom |
| `game-feel` | impacto, feedback, juice |
| `game-ui-ux` | HUD, menus, acessibilidade |
| `level-design` | fluxo, ritmo, espaços |
| `physics-tuning` | física, colisão, massa |
| `performance-optimization` | CPU/GPU, LOD, culling |
| `procedural-gen` | distribuição procedural |
| `dialogue-systems` | diálogos, narrativa interativa |
| `game-ai` | IA de NPC e inimigos |
| `shader-programming` | shaders e efeitos |
| `fps-shooter` | primeira pessoa e tiro |

## Blender (origem: blender-skills)
| Skill | Quando |
|---|---|
| `blender-director` | planejar qualquer asset 3D |
| `blender-modeler`, `blender-hard-surface`, `blender-prop-artist`, `blender-vehicle-artist`, `blender-character-artist`, `blender-environment-artist`, `blender-vegetation-artist` | modelagem por tipo |
| `blender-retopology`, `blender-uv-workflow`, `blender-materials`, `blender-texture-workflow`, `blender-lighting`, `blender-geometry-nodes`, `blender-stylized-style` | técnicas |
| `blender-rigging`, `blender-animation` | rig e animação |
| `blender-asset-optimization`, `blender-lod-pipeline`, `blender-collision-proxy` | otimização |
| `blender-unreal-export`, `blender-export-pipeline`, `blender-scene-assembly`, `blender-qa-review`, `blender-camera-cinematography` | export, cena, QA, câmera |

## Agentes
| Agente | Domínio |
|---|---|
| `studio-producer` | coordenação, plano, dependências |
| `technical-architect` | arquitetura e contratos |
| `art-director` | Art Bible, briefs |
| `blender-specialist` | modelagem, rig, export |
| `animation-specialist` | animação e retarget |
| `vehicle-engineer` | física do carro |
| `gameplay-engineer` | personagem, combate, interação |
| `enemy-ai-engineer` | IA de inimigos |
| `world-builder` | terreno, mapa, checkpoints |
| `level-designer` | espaços, interiores, fluxo e objetivos |
| `technical-artist` | materiais, luz, shaders |
| `cinematics-director` | câmera, cutscenes, abertura |
| `sound-designer` | música, ambiente, mix, SFX |
| `ui-audio-engineer` | HUD, menus, feedback, VFX |
| `performance-engineer` | budgets e profiling |
| `qa-engineer` | testes e regressão |
| `asset-license-auditor` | procedência e licenças |

## Lacunas conhecidas (sem skill dedicada, de propósito)
Motion capture, geração de textura por IA, controle de versão avançado e documentação automática ficam em INVESTIGAR (`docs/pipeline/INTEGRATION_MATRIX.md`).

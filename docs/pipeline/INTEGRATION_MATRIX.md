# Matriz de decisão da integração

Legenda: INTEGRAR, ADAPTAR, MANTER COMO OPCIONAL, NÃO INTEGRAR, INVESTIGAR. "Equivalente" é o que já existia no repositório. Data: 2026-11-16.

## 1. awesome-gamedev-agent-skills (Apache-2.0)

| Funcionalidade | O que faz / problema que resolve | Equivalente existente | Benefício | Conflitos ou dependências | Decisão | Onde |
|---|---|---|---|---|---|---|
| Router de skills | Detecta engine por `*.uproject` e carrega só as skills da tarefa | Tabela de agentes no `CLAUDE.md` | Roteamento por tarefa, menos contexto | Roteador original cobre 12 engines que o projeto não usa | ADAPTAR | `gamedev-router` (próprio, em português, aponta agentes e skills reais) |
| `unreal-cpp-gameplay`, `unreal-blueprints`, `unreal-enhanced-input`, `unreal-niagara`, `unreal-packaging` | Conhecimento da API Unreal por tema | `.claude/rules/cpp.md` (só convenções) | Menos erro de API, boas práticas | Baseline declarada UE 5.8; conferir contra o 5.8.4 em uso | INTEGRAR | `.claude/skills/` |
| `unreal-behavior-trees` | Behavior Trees e percepção | Agente `enemy-ai-engineer` (usa StateTree) | Apoio à IA | O projeto usa StateTree; usar só onde servir | INTEGRAR | `.claude/skills/` |
| `audio-design` | Buses, ducking, SFX, música adaptativa | `ui-audio-engineer` | Base para áudio por zona | Nenhum | INTEGRAR | `.claude/skills/` |
| `camera-systems` | Câmera, braço, colisão | `gameplay-engineer` (sem skill) | Base para câmera de interação | Nenhum | INTEGRAR | `.claude/skills/` |
| `game-feel`, `game-ui-ux`, `level-design`, `physics-tuning`, `performance-optimization`, `procedural-gen`, `dialogue-systems`, `game-ai`, `shader-programming`, `fps-shooter` | Disciplinas transversais | Agentes sem skill de apoio | Cobrem lacunas de design e execução | Nenhum | INTEGRAR | `.claude/skills/` |
| `save-systems`, `input-systems`, `ai-behavior-trees-utility-ai` | Persistência, entrada, IA utilitária | Save em C++ (`USaveGame`), Enhanced Input, `game-ai` | Pouco ganho agora | Sobreposição | NÃO INTEGRAR (agora) | Pode entrar depois (`EXTENDING.md`) |
| `create-game-assets` | Sprites, pixel art, tilesets | Pipeline 3D em Blender | Nenhum no projeto 3D | Foco 2D | NÃO INTEGRAR | n/a |
| Skills de Godot, Unity, web, Bevy e outras; gêneros e workflows de publicação | Outras engines e gêneros | Não se aplica | Nenhum | Instalar tudo estoura o orçamento de descrições | NÃO INTEGRAR | Preservar a opção futura |
| `scripts/validate-skills.py` | Valida skills | Testes de estrutura do repositório | Evita skills quebradas | Regras próprias do projeto | ADAPTAR | `tools/pipeline/validate_pipeline.py` |
| Testes de gatilho (`run-trigger-evals.py`) | Mede se a descrição aciona a skill | Nenhum | Qualidade do roteamento | Exige execução do agente | INVESTIGAR | Futuro |

## 2. Claude Code Game Studios (MIT)

| Funcionalidade | O que faz / problema que resolve | Equivalente existente | Benefício | Conflitos ou dependências | Decisão | Onde |
|---|---|---|---|---|---|---|
| Hierarquia diretores, líderes, especialistas | Delegação vertical e consulta horizontal | 12 agentes planos, coordenação no `CLAUDE.md` | Coordenação de tarefas grandes | 49 agentes seriam excesso para um projeto solo | ADAPTAR | `studio-producer` mais papéis que faltavam |
| `producer` + skills `team-*` | Orquestra equipes por funcionalidade | Nenhuma | Plano com dono por arquivo e dependências | Nenhum | ADAPTAR | `studio-producer`, `team-orchestrate` |
| `level-designer`, `technical-artist`, `sound-designer` | Especializações ausentes | `world-builder` e `ui-audio-engineer` acumulavam | Responsabilidade clara | Divisão com os agentes existentes (ver `PIPELINE_V2.md`) | ADAPTAR | `.claude/agents/` |
| Direção de câmera e cinemática | Não existe no original como agente próprio | Nenhum | Atende os problemas de câmera e abertura | Nenhum | INTEGRAR (próprio) | `cinematics-director`, `camera-shots-and-cutscenes`, `intro-sequence` |
| `gate-check` | Portões de qualidade por fase | `tests/gameplay/checklists/` manuais | Evita "pronto" sem evidência | Nenhum | ADAPTAR | `visual-qa-gate` |
| `skill-test` e `skill-improve` | Testa e melhora skills e agentes | Nenhum | Qualidade das skills | O ciclo de melhoria exige execução com pontuação | ADAPTAR (parte estática) / INVESTIGAR (ciclo) | `validate-pipeline`, `test_pipeline_integrity.py` |
| Agentes `creative-director`, `game-designer`, `narrative-director`, `writer` | Direção criativa, design, narrativa | GDD e decisões do usuário | Poderiam ajudar na história | Decisões criativas são do usuário; narrativa em aberto (OD-008) | INVESTIGAR | Reavaliar quando a narrativa for definida |
| Agentes de rede, replicação, live ops, analytics, comunidade, localização | Serviços online | Não se aplica | Nenhum | O projeto é single player, sem telemetria | NÃO INTEGRAR | n/a |
| Especialistas Unreal (Blueprint, GAS, UMG, replicação) | Conhecimento por área | Skills `unreal-*` | Já coberto por skills | GAS e replicação não são usados | NÃO INTEGRAR | n/a |
| 18 hooks bash, `session-start`, regras por caminho | Automação e estado de sessão | 3 hooks Python próprios; handoff em `docs/handoff/` | Possível ganho em estado de sessão | Hooks em bash; risco de conflito com os atuais | INVESTIGAR | Futuro, um por vez |
| `project.yaml`, pastas `production/`, `src/` | Estrutura do projeto exemplo | Estrutura própria já madura | Nenhum | Conflita com a estrutura atual | NÃO INTEGRAR | n/a |

## 3. ACE-Step 1.5 (MIT)

| Funcionalidade | O que faz / problema que resolve | Equivalente existente | Benefício | Conflitos ou dependências | Decisão | Onde |
|---|---|---|---|---|---|---|
| Geração de música por texto | Trilha, loops, ambiente, variações | Música gerada por script (`gen_game_audio.py`), avaliada como fraca pelo usuário | Candidatos de música melhores | GPU/VRAM, Python 3.11 a 3.12, disco | MANTER COMO OPCIONAL | Skill `music-production-acestep` |
| API REST local | Integração por script | Nenhum | Gerar e baixar candidatos em lote | Servidor local ativo | MANTER COMO OPCIONAL | `tools/audio/acestep_client.py` |
| Pesos dos modelos | Necessários para gerar | Nenhum | n/a | Download de vários GB; licença por modelo | NÃO INSTALADO (documentado) | `EXTERNAL_TOOLS.md` |
| Cover, repaint, extract, lego, complete | Edição e transformação de áudio | Nenhum | Variações adaptativas | Mesmas dependências | INVESTIGAR | Futuro |

## 4. NVIDIA Audio2Face-3D

| Funcionalidade | O que faz / problema que resolve | Equivalente existente | Benefício | Conflitos ou dependências | Decisão | Onde |
|---|---|---|---|---|---|---|
| Plugin Unreal | Lip sync em tempo real | Nenhum | Diálogos e cutscenes | Documentado até UE 5.6; projeto em 5.8.4 | NÃO INTEGRAR | Não instalar sem teste real; não rebaixar a engine |
| SDK, Maya (MACE) e NIM | Geração de curvas faciais fora da engine | Nenhum | Caminho independente da versão da Unreal | GPU NVIDIA; Maya é pago; NIM é contrato NVIDIA | INVESTIGAR | `facial-animation-lipsync` (caminho A) |
| Skill de animação facial | Fluxo, requisitos de rig, validação | `animation-specialist` sem tema facial | Padroniza o trabalho | Heróis atuais sem shape keys faciais | ADAPTAR (opcional) | `facial-animation-lipsync` |
| Validação de blend shapes | Confere nomes ARKit | Nenhum | Descobre o que falta no rig | Nenhum | INTEGRAR | `tools/blender/validate_face_blendshapes.py` |
| Alternativa livre de visemas (ex. Rhubarb) | Lip sync sem GPU NVIDIA | Nenhum | Plano B grátis | Licença não confirmada | INVESTIGAR | `facial-animation-lipsync` (caminho C) |

## 5. Blender Skills (MIT)

| Funcionalidade | O que faz / problema que resolve | Equivalente existente | Benefício | Conflitos ou dependências | Decisão | Onde |
|---|---|---|---|---|---|---|
| `blender-director` | Planejamento de produção de assets | `blender-specialist`, `create-asset` | Plano antes de modelar | Quer MCP por padrão | ADAPTAR | Aviso de adaptação: MCP opcional, regras do repositório vencem |
| Modelagem por tipo (prop, hard surface, veículo, personagem, ambiente, vegetação) | Especialistas de modelagem | `blender-specialist` genérico | Qualidade por tipo de asset | Nomes prefixados para evitar colisão | INTEGRAR | `blender-*` |
| Retopologia, UV, materiais, texturas, luz, geometry nodes, estilo estilizado | Técnicas | Scripts de validação apenas | Conhecimento de técnica | Nenhum | INTEGRAR | `blender-*` |
| Rigging e animação | Rig e animação no Blender | `animation-specialist` | Complementa retarget | Rig Mixamo-compatível do projeto vence | INTEGRAR | `blender-rigging`, `blender-animation` |
| Otimização, LOD, colisão, export Unreal, validação, montagem de cena | Final de produção | `export-blender`, `validate-asset` | Valida antes de exportar | Preset de export do projeto vence | INTEGRAR | `blender-*` |
| Análise de imagem de referência | Reproduz modelo a partir de foto | `generate-concept` | Referência para modelagem | Exige execução no Blender | INTEGRAR | `blender-director` + `blender-references` |
| Escultura, lookdev, modelagem procedural, set dressing, renderização, composição, física, criaturas | Skills extras | Parcialmente cobertas | Pouco ganho agora | Excesso de skills | NÃO INTEGRAR (agora) | Opção futura |
| Estilos (horror, pixel, anime...), gêneros, humores, eras, export Godot e Unity | Direção de estilo e outras engines | Art Bible própria | Nenhum | Conflito com o estilo cartunesco já definido | NÃO INTEGRAR | n/a |
| Blender MCP | Executa operações no Blender | Scripts `tools/blender/` | Iteração com prévia | Python arbitrário; conexão real não testada | MANTER COMO OPCIONAL | `.mcp.json.example` (existente), `EXTERNAL_TOOLS.md` |

## 6. Lacunas identificadas fora dos cinco repositórios

| Lacuna | Decisão | Onde |
|---|---|---|
| Sobreposição de objetos no mapa | INTEGRAR (nova) | `tools/pipeline/placement_registry.py`, `map-composition` |
| Interiores sem conteúdo | INTEGRAR (nova) | `enterable-interior`, `level-designer` |
| Abertura do jogo e câmera de interação | INTEGRAR (nova) | `intro-sequence`, `camera-shots-and-cutscenes`, `cinematics-director` |
| Pose de mão, arma e primeira pessoa | INTEGRAR (nova) | `character-pose-validation` |
| Auditoria de brilho e materiais | INTEGRAR (nova) | `material-lighting-audit`, `technical-artist` |
| Portão de QA visual | INTEGRAR (nova) | `visual-qa-gate` |
| Documentação automática do catálogo | INTEGRAR (nova) | `tools/pipeline/gen_catalog.py` |
| Motion capture (Mixamo cobre o básico) | INVESTIGAR | Alternativas livres a pesquisar |
| Geração de texturas por IA | INVESTIGAR | Licenças e hardware |
| Script de auditoria de materiais na Unreal | INVESTIGAR | Precisa ser escrito e testado no Editor (o assistente não roda a Unreal) |
| Validação de build automatizada | INVESTIGAR | `UnrealEditor-Cmd` e Automation Tests |

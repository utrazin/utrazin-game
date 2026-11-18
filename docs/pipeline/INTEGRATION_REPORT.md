# Relatório de integração da pipeline v2

Data: 2026-11-16 e 17. Decisões linha a linha: `INTEGRATION_MATRIX.md`. Visão geral: `PIPELINE_V2.md`.

## Legenda de estado

| Estado | Significado |
|---|---|
| Implementado | Arquivos criados |
| Configurado | Ligado a roteador, agentes e documentação |
| Validado estruturalmente | Passa em `validate_pipeline.py` e nos testes de estrutura |
| Testado em execução | Código executado em teste automatizado |
| Dependente de instalação externa | Precisa de software ou hardware fora do repositório |
| Pendente de validação manual | Só dá para confirmar rodando o jogo, o Blender ou a ferramenta real |

## O que foi encontrado

12 agentes, 14 skills (fluxo de assets e QA), 3 hooks Python, 5 regras, `CLAUDE.md` curto com tabela de delegação, nenhum MCP ativo (só `.mcp.json.example`), scripts em `tools/blender`, `tools/unreal`, `tools/pipeline`, e 11 arquivos de teste. Sem skills de API da Unreal, sem roteador, sem agentes de level design, câmera, material e música, e sem tratamento de interiores, abertura, pose de mão ou sobreposição de objetos. O repositório já tinha alterações não commitadas do usuário; nenhuma foi tocada.

## O que foi feito

| Item | Estado |
|---|---|
| 18 skills de engine e disciplina (awesome-gamedev-agent-skills) | Implementado, configurado, validado estruturalmente |
| 25 skills `blender-*` + `blender-references` (blender-skills) | Implementado, configurado, validado estruturalmente |
| Skill `gamedev-router` com tabela completa | Implementado, validado estruturalmente (cobertura da tabela testada). Qualidade do roteamento em uso real: pendente |
| 5 agentes novos (`studio-producer`, `level-designer`, `technical-artist`, `cinematics-director`, `sound-designer`) | Implementado, validado estruturalmente |
| 12 agentes existentes ganharam a seção "Skills que consulta" | Implementado |
| 8 skills originais (interior, mapa, câmera, abertura, pose, material e luz, música, rosto) + `team-orchestrate`, `visual-qa-gate`, `validate-pipeline` | Implementado, validado estruturalmente. Eficácia no jogo: pendente de validação manual |
| `tools/pipeline/validate_pipeline.py`, `gen_catalog.py` | Testado em execução |
| `tools/pipeline/placement_registry.py` (evita sobreposição) | Testado em execução (pytest). **Ainda não ligado** a `build_l01.py`, `scatter_l01*.py` e `l01_user_dressing.py` |
| `tools/audio/acestep_client.py` | Testado em execução contra servidor falso. **Nunca falou com o ACE-Step real** |
| `tools/blender/validate_face_blendshapes.py` | Parte pura testada. Parte `bpy` nunca rodou no Blender |
| `tools/setup/check_optional_ai_tools.py` | Testado em execução (leitura apenas) |
| Catálogos de agentes e skills (gerados) | Implementado; teste confere que estão atualizados |
| ACE-Step | Dependente de instalação externa; **nada instalado ou baixado** |
| Audio2Face-3D | Plugin Unreal não integrado (sem suporte documentado à 5.8.4); fluxo externo em INVESTIGAR |
| Blender MCP | Mantido opcional e desligado; `.mcp.json` não criado; **conexão real não testada** |

## O que foi descartado e por quê

Skills de outras engines, gêneros e estilos (excesso de contexto, engine ausente, conflito com o estilo cartunesco), 40+ agentes do Game Studios sem uso aqui (rede, live ops, localização, GAS), hooks em bash e estrutura de pastas do exemplo (conflitam com o que existe), plugin Unreal do Audio2Face (versão), `create-game-assets` (2D). Detalhes na matriz.

## Testes executados

- Suíte de testes novos: 40 testes, todos passando (validador, catálogos, registro de posicionamento, cliente ACE-Step com servidor falso, blend shapes, ferramentas opcionais).
- `validate_pipeline.py` no repositório real: 0 erros, 0 avisos.
- Suíte completa `tests/python` no repositório real: 222 passaram, 7 falharam. Nenhuma das 7 envolve arquivos desta integração: 5 em `test_manifest.py` (o `jsonschema` da máquina de teste é antigo e não tem `Draft202012Validator`), 1 em `test_repo_structure.py` (caminho `C:/` literal em `tools/pipeline/make_item_wheel_ui.py`) e 1 em `test_l01_user_dressing.py` (catálogo de 56 modelos; causa não investigada). Não foram corrigidas por serem trabalho em andamento do usuário ou do ambiente.
- Não executado: Unreal Editor, Blender, ACE-Step, Audio2Face, Blender MCP, validadores de gatilho das skills.

## Limitações

- Skills vendorizadas estão em inglês e foram escritas para outros projetos; só a estrutura foi validada, não o conteúdo técnico contra a Unreal 5.8.4.
- Nenhum problema do jogo (colisão, câmera, mapa, interiores, brilho, música) foi corrigido ainda. A pipeline define como fazer e validar; as correções vêm no tratamento do handoff.
- Faltam scripts de auditoria dentro da Unreal (materiais, colisão); o assistente não roda o Editor.
- A divisão de áreas entre `sound-designer` e `ui-audio-engineer`, e entre `level-designer` e `world-builder`, é nova e ainda não foi exercitada.
- Versão do Blender divergente na documentação (5.2 LTS x 5.3): OD-P04.

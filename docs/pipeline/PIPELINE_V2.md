# Pipeline de desenvolvimento v2: visão geral

Evolução da pipeline original (M0) com roteamento, equipe de agentes ampliada e skills de produção. Nada foi reconstruído do zero: os 12 agentes, as 14 skills, os 3 hooks, as 5 regras e os scripts existentes continuam como estavam.

## Camadas

| Camada | Onde | O que faz |
|---|---|---|
| Instruções | `CLAUDE.md` (curto) + `CLAUDE.md` por pasta + `.claude/rules/` | Regras fixas, sempre carregadas |
| Roteamento | skill `gamedev-router` | Escolhe agente líder, skills e ferramentas por tarefa |
| Coordenação | agente `studio-producer` + skill `team-orchestrate` | Plano multidisciplinar com dono por arquivo |
| Especialistas | `.claude/agents/` (17 agentes) | Cada um com escopo, proibições e formato de retorno |
| Conhecimento | `.claude/skills/` (skills do projeto, de engine/disciplina e de Blender) | Carregado só quando necessário |
| Portões de qualidade | `visual-qa-gate`, `validate-pipeline`, testes em `tests/python/` | Impedem declarar "pronto" sem evidência |
| Ferramentas opcionais | ACE-Step, Audio2Face, Blender MCP | Fora do caminho crítico; ver `EXTERNAL_TOOLS.md` |

## Fluxo padrão de uma tarefa

1. `gamedev-router` identifica engine (`*.uproject`), disciplina e ferramentas disponíveis.
2. Tarefa simples: o agente líder resolve com no máximo 3 skills de apoio.
3. Tarefa com 3 ou mais especialidades: `studio-producer` roda `team-orchestrate` e delega.
4. Entrega visível passa por `visual-qa-gate`; mudanças na pipeline por `validate-pipeline`.
5. Relatório curto de cada agente, com evidência (print, JSON, saída de teste).

## Mapa dos problemas conhecidos para a pipeline

| Problema relatado | Líder | Skill principal |
|---|---|---|
| Mão fora de posição, arma invisível em primeira pessoa | `animation-specialist` | `character-pose-validation` |
| Interiores vazios ou pequenos demais | `level-designer` | `enterable-interior` |
| Câmera ruim ou trocas sem animação | `cinematics-director` | `camera-shots-and-cutscenes` |
| Mapa sem coerência, morros vazios, objetos sobrepostos | `world-builder` | `map-composition` + `tools/pipeline/placement_registry.py` |
| Música fraca, som fora de contexto | `sound-designer` | `music-production-acestep` (opcional), `audio-design` |
| Sem abertura de jogo | `cinematics-director` | `intro-sequence` |
| Iluminação, brilho, material branco | `technical-artist` | `material-lighting-audit` |

Estas skills definem **como** trabalhar e validar. Corrigir o jogo em si (cenas, Blueprints, C++) é o próximo passo, a partir do handoff.

## Responsabilidades sem sobreposição

- `level-designer` desenha o espaço; `world-builder` o constrói no motor.
- `sound-designer` cuida de música, ambiente e mix; `ui-audio-engineer` de HUD, menus e feedback.
- `technical-artist` audita materiais e luz; `art-director` decide a direção visual.
- `cinematics-director` define câmeras; `gameplay-engineer` implementa a classe de câmera do personagem.
- Dois agentes nunca editam o mesmo binário (`.uasset`, `.umap`, `.blend`).

## Carga de contexto

- `CLAUDE.md` raiz continua curto; conhecimento especializado fica nas skills.
- Para listar skills sem poluir o contexto, instale só o que o projeto usa (ver `INTEGRATION_MATRIX.md`). Skills de outras engines e de estilos não foram instaladas e podem ser adicionadas depois (`EXTENDING.md`).

## Validação da pipeline

`python tools/pipeline/validate_pipeline.py` e `python -m pytest tests/python/test_pipeline_integrity.py -q`. O que está validado e o que não está: `INTEGRATION_REPORT.md`.

## Documentos relacionados

`AGENT_CATALOG.md`, `SKILL_CATALOG.md` (gerados), `INTEGRATION_MATRIX.md`, `INTEGRATION_REPORT.md`, `EXTERNAL_TOOLS.md`, `EXTENDING.md`, `MCP_SECURITY.md`, `docs/licenses/THIRD_PARTY_SOURCES.md`.

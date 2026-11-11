# CLAUDE.md (raiz)

Você trabalha no **Jogo de Resgate**: single player, offline, terceira pessoa, Unreal Engine 5.8.4 + Blender 5.2 LTS, somente ferramentas e assets gratuitos com licença conhecida.

## Fontes de verdade (nesta ordem)

1. [`GDD_jogo_resgate.md`](GDD_jogo_resgate.md): decisões de design. Prevalece sobre qualquer suposição.
2. [`docs/decisions/ASSUMPTIONS.md`](docs/decisions/ASSUMPTIONS.md): valores provisórios **não aprovados** pelo usuário.
3. [`docs/decisions/OPEN_DECISIONS.md`](docs/decisions/OPEN_DECISIONS.md): o que ainda falta decidir.
4. [`docs/architecture/ARCHITECTURE.md`](docs/architecture/ARCHITECTURE.md) e ADRs em `docs/architecture/adr/`.
5. [`docs/roadmap/ROADMAP.md`](docs/roadmap/ROADMAP.md): marco atual e critérios de aceite.

Não mude escopo nem identidade do jogo: registre uma proposta em `OPEN_DECISIONS.md`.

## Limites do projeto

- Sem multiplayer, replication, backend, banco de dados, contas ou telemetria.
- Save **apenas local** (`USaveGame` versionado).
- Windows 64 bits primeiro.
- Nada de franquias protegidas: design original, apenas "inspirado".
- Placeholders permitidos só no protótipo, com `status` no manifesto.
- Sem plugins experimentais ou pagos. World Partition, Nanite, Lumen e PCG só com medição (ver `docs/architecture/RENDERING.md`).

## Mapa da arquitetura

| Pasta | Conteúdo | CLAUDE.md local |
|---|---|---|
| `unreal/JogoResgate/Source/JogoResgate/` | C++: Core, Characters, Vehicles, Combat, AI, Levels, Progression, Save, Interactions, Utilities | [`unreal/CLAUDE.md`](unreal/CLAUDE.md) |
| `unreal/JogoResgate/Content/` | Blueprints, mapas, Data Assets | idem |
| `blender/` | Cenas-fonte, rigs, presets | [`blender/CLAUDE.md`](blender/CLAUDE.md) |
| `assets/` | Manifesto, raw/work/final, licenças | [`assets/CLAUDE.md`](assets/CLAUDE.md) |
| `design/` | Art/Audio Bible, conceitos | [`design/CLAUDE.md`](design/CLAUDE.md) |
| `tools/` | Scripts Python | [`tools/CLAUDE.md`](tools/CLAUDE.md) |
| `tests/` | Testes e checklists | [`tests/CLAUDE.md`](tests/CLAUDE.md) |
| `docs/` | Documentação | [`docs/CLAUDE.md`](docs/CLAUDE.md) |
| `audio/` | Fontes de áudio | [`audio/CLAUDE.md`](audio/CLAUDE.md) |

## Comandos de desenvolvimento

```bash
python -m pytest tests/python -q                      # testes rápidos
python tools/pipeline/manifest.py validate            # manifesto + schema
python tools/pipeline/check_licenses.py               # auditoria de licenças
python tools/pipeline/validate_naming.py <paths...>   # convenções de nome
python tools/pipeline/validate_references.py          # links locais em .md
python tools/setup/check_environment.py               # inspeção do ambiente
```

Unreal (quando instalada): ver `docs/setup/INSTALL_UNREAL.md` para build e `UnrealEditor-Cmd` com scripts Python.

## Delegação a subagentes (`.claude/agents/`)

Delegue tarefas independentes quando isso reduzir contexto ou risco. Antes de delegar defina: escopo fechado, arquivos permitidos, entradas, saídas, critérios de aceite, dependências e conflitos. **Nunca** dois agentes no mesmo binário (`.uasset`, `.umap`, `.blend`). Peça retorno curto (formato definido em cada agente). O agente principal integra, revisa contratos e roda a validação transversal.

| Tarefa | Agente |
|---|---|
| Arquitetura, contratos, ADR | `technical-architect` |
| Art Bible, briefs, prompts de conceito | `art-director` |
| Modelagem, UV, rig, export | `blender-specialist` |
| Animações, retarget, montages | `animation-specialist` |
| Física e dano do carro | `vehicle-engineer` |
| Personagem, combate, interação, possession | `gameplay-engineer` |
| IA, aggro, hordas | `enemy-ai-engineer` |
| Terreno, greybox, streaming, checkpoints | `world-builder` |
| HUD, menus, áudio de feedback, VFX | `ui-audio-engineer` |
| Profiling, LOD, budgets | `performance-engineer` |
| Testes e regressão | `qa-engineer` |
| Procedência e licenças | `asset-license-auditor` |

## Padrões críticos

- Convenções Unreal (prefixos U/A/F/E/I, prefixo de projeto `JR`). Regras em `.claude/rules/cpp.md`.
- Assets: prefixos `BP_ WBP_ SM_ SK_ M_ MI_ T_ ABP_ AM_ BS_ NS_ SFX_ DA_ DT_ IA_ IMC_` e complementares em `.claude/rules/unreal-content.md`.
- Composition over inheritance, delegates em vez de polling, Tick só com justificativa.
- Estado de fase nunca em widgets. Sem caminhos absolutos.
- Toda suposição nova vai para `docs/decisions/ASSUMPTIONS.md`.

## Fluxo de QA

1. Testes automáticos (`pytest`; Automation Tests da Unreal quando disponível).
2. Checklist manual em `tests/gameplay/checklists/`.
3. Relatório em `docs/qa/` com data, build e evidências.

## Checklist de veracidade

Não declarar que: a Unreal abriu, o build compilou, um Blueprint existe, uma animação foi validada, uma licença é comercial ou um QA passou **sem evidência real**. Não esconder impedimentos: registre em `docs/decisions/OPEN_DECISIONS.md` ou `docs/qa/`.

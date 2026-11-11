# Jogo de Resgate (título provisório)

Jogo 3D **single player, offline, em terceira pessoa**: em cada fase o jogador dirige um SUV por terreno acidentado, chega ao checkpoint, continua a pé, enfrenta inimigos e uma horda final e liberta uma pessoa presa.

- Design: [`GDD_jogo_resgate.md`](GDD_jogo_resgate.md) (documento vivo)
- Instruções para agentes: [`CLAUDE.md`](CLAUDE.md)
- Decisões provisórias: [`docs/decisions/ASSUMPTIONS.md`](docs/decisions/ASSUMPTIONS.md) e [`docs/decisions/OPEN_DECISIONS.md`](docs/decisions/OPEN_DECISIONS.md)
- Roadmap: [`docs/roadmap/ROADMAP.md`](docs/roadmap/ROADMAP.md)
- Primeiros passos no Editor: [`docs/setup/FIRST_EDITOR_STEPS.md`](docs/setup/FIRST_EDITOR_STEPS.md)
- Origem: `prompt.md` (prompt mestre usado para criar o repositório) e `GDD_jogo_resgate_1.md` (GDD original v0.1, preservado)

## Estado atual

| Item | Estado |
|---|---|
| Marco atual | **M0 Fundação** (estrutura, docs, pipeline, agentes) |
| Unreal Engine | **Não instalada** na máquina de desenvolvimento. Projeto Unreal existe só como código-fonte C++ e `.uproject`, **nunca compilado**. |
| Blender | Não instalado |
| Scripts Python de pipeline | Implementados e cobertos por testes (`pytest`, 171 testes) |
| Lógica C++ pura | Compilada e testada **fora** da Unreal com stubs (`tests/cpp`) |
| Scripts Blender | Smoke test real com Blender 5.2.4 (módulo `bpy`) |
| Assets | Nenhum asset de produção ainda |

Nada neste repositório deve ser entendido como "compila" ou "funciona no Editor" até existir log de build em `docs/qa/`.

## Pré-requisitos (Windows 10/11 64 bits)

| Ferramenta | Versão alvo | Gratuita | Guia |
|---|---|---|---|
| Unreal Engine | 5.8.4 (via Epic Games Launcher) | Sim (royalties só acima de US$ 1 mi brutos, ver EULA) | [`docs/setup/INSTALL_UNREAL.md`](docs/setup/INSTALL_UNREAL.md) |
| Visual Studio | 2022 Community + workload "Game development with C++" | Sim | idem |
| Blender | 5.2 LTS | Sim (GPL) | [`docs/setup/INSTALL_BLENDER.md`](docs/setup/INSTALL_BLENDER.md) |
| Git + Git LFS | recentes | Sim | [`docs/setup/SETUP_WINDOWS.md`](docs/setup/SETUP_WINDOWS.md) |
| Python | 3.11+ (para ferramentas fora das engines) | Sim | idem |
| uv (opcional) | recente | Sim | idem |

Hardware recomendado: ver [`docs/setup/HARDWARE.md`](docs/setup/HARDWARE.md). Resumo: 32 GB RAM, GPU com 8 GB+ VRAM (DX12 / SM6), SSD NVMe com **150 GB livres** (engine ~60 GB + projeto + DDC).

## Primeiros passos

```powershell
git clone https://github.com/utrazin/utrazin-game.git E:\game\utrazin-game
cd E:\game\utrazin-game
git lfs install
powershell -ExecutionPolicy Bypass -File tools\setup\setup_windows.ps1   # instala .claude/.github de _bootstrap (1a vez), hooks, venv, testes
python tools\setup\check_environment.py          # diagnóstico do ambiente
python -m pytest tests\python -q                # testes do pipeline
```

Depois de instalar a Unreal 5.8.4 e o Visual Studio:

1. Clique com o botão direito em `unreal\JogoResgate\JogoResgate.uproject` > **Generate Visual Studio project files**.
2. Abra `JogoResgate.sln`, configuração **Development Editor / Win64**, compile.
3. Corrija o que o compilador apontar (o código ainda não foi compilado nenhuma vez) e registre o log em `docs/qa/`.

## Arquitetura (visão rápida)

```
utrazin-game/
  GDD_jogo_resgate.md   design vivo
  CLAUDE.md             regras para o Claude Code (+ CLAUDE.md por área)
  .claude/              subagentes, skills, rules, hooks
  design/               Art Bible, Audio Bible, conceitos, narrativa, níveis
  assets/               manifesto + raw/work/final + licenças
  blender/              cenas-fonte .blend, rigs, presets de export
  unreal/JogoResgate/   projeto Unreal (C++ em Source/, conteúdo em Content/)
  audio/                gravações, edição, música, exports
  tools/                scripts Python (blender/, unreal/, pipeline/, setup/)
  tests/                testes Python, checklists de gameplay, performance
  docs/                 arquitetura, pipeline, decisões, setup, QA, roadmap
  build/                scripts de empacotamento (artefatos ignorados)
```

Gameplay em C++ (sistemas-base) + Blueprint (composição/configuração). Detalhes em [`docs/architecture/ARCHITECTURE.md`](docs/architecture/ARCHITECTURE.md).

## Comandos úteis

```powershell
python tools\pipeline\manifest.py validate                 # valida assets/manifest/assets.json
python tools\pipeline\check_licenses.py --report reports\licenses.md
python tools\pipeline\validate_naming.py assets\final unreal\JogoResgate\Content
python tools\pipeline\validate_references.py               # links locais quebrados em .md
python -m pytest tests\python -q
```

## Contribuição

Fluxo de branches, commits e PRs em [`CONTRIBUTING.md`](CONTRIBUTING.md). Regras de licença de assets em [`ASSET_LICENSES.md`](ASSET_LICENSES.md).

## Licença

Código e conteúdo original: todos os direitos reservados (provisório, ver [`LICENSE`](LICENSE)).

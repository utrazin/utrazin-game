# unreal/

Projeto: `JogoResgate/JogoResgate.uproject` (UE 5.8.4). **Código nunca compilado** até existir log em `docs/qa/`.

- C++ em `Source/JogoResgate/<Área>/`, prefixo `JR`. Regras: `.claude/rules/cpp.md`.
- Conteúdo em `Content/<Área>/`; nomes conforme `.claude/rules/unreal-content.md`.
- Blueprints herdam das classes C++ e só compõem/configuram. Regras de jogo ficam em C++.
- Não crie `.uasset`/`.umap` por texto. Assets binários só via Editor ou `tools/unreal/*.py` rodando no Editor.
- Novas fases: Data Asset `DA_Level_*` + mapa; sem código novo (skill `/add-level`).
- Não habilitar World Partition, Nanite, Lumen ou PCG sem medição (`docs/architecture/RENDERING.md`).
- Sem replication/multiplayer.
- Testes: Automation Tests `JR.*` em `Source/JogoResgate/Tests/`.

Build (PowerShell):
```
& "$env:UE_ROOT\Engine\Build\BatchFiles\Build.bat" JogoResgateEditor Win64 Development -Project="$PWD\unreal\JogoResgate\JogoResgate.uproject" -WaitMutex
```

# Baseline de performance

Ainda não medido (Unreal não instalada, IMP-001).

## Método

1. Build `Development` standalone, 1080p, settings "High".
2. Rota fixa de câmera/gameplay (gravada com Sequencer ou replay) por trecho: carro, a pé, horda.
3. `stat unit`, `stat gpu`, `stat memory`; captura Unreal Insights (`-trace=cpu,gpu,frame`).
4. Registrar média, 1% low e picos em `docs/qa/perf/AAAA-MM-DD.md`.

| Trecho | Frame (ms) | Game | Render | GPU | Memória | Data | Commit |
|---|---|---|---|---|---|---|---|
| Carro | | | | | | | |
| A pé | | | | | | | |
| Horda | | | | | | | |

# Processo de QA

1. **Automático rápido** (todo PR, CI Ubuntu): `pytest`, schema do manifesto, licenças, nomes, links.
2. **Automático completo** (runner Windows self-hosted opcional, workflow `validate.yml` job `unreal-full`): build C++ + Automation Tests `JR.*`.
3. **Manual**: checklists em `tests/gameplay/checklists/`.
4. **Relatório**: `docs/qa/reports/AAAA-MM-DD_<marco>.md` com commit, build, resultados e evidências.

Regra: só marcar "passou" o que foi executado. Itens não executados ficam "não executado" com motivo.

## Template de relatório

```markdown
# QA <marco> - <data>
- commit: <sha> | build: <config> | máquina: <cpu/gpu/ram>
| Passo | Resultado | Evidência | Observações |
|---|---|---|---|
```

Regressão: [`REGRESSION.md`](REGRESSION.md).

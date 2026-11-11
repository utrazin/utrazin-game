# docs/

- Escreva em pt-BR, direto, sem texto genérico. Se faltar informação, registre em `decisions/OPEN_DECISIONS.md` em vez de inventar.
- Toda suposição nova: `decisions/ASSUMPTIONS.md` (ID `A-NNN`, status `pendente`).
- Decisão de arquitetura: novo ADR em `architecture/adr/` e linha no `adr/README.md`.
- Relatórios de QA em `qa/reports/` com data e commit. Nunca registre resultado não executado.
- Links relativos; `python tools/pipeline/validate_references.py` deve passar.

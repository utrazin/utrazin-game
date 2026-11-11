# tests/

- `python/`: pytest das ferramentas (`python -m pytest tests/python -q`). Testes devem falhar quando o código está errado; nada de asserts triviais.
- `fixtures/`: arquivos pequenos (JSON, manifestos, markdown) usados pelos testes.
- `blender/` e `unreal/`: instruções e scripts de teste que exigem as aplicações.
- `gameplay/checklists/`: QA manual. Preencha resultado real, nunca presuma.
- `performance/`: baseline e método de medição.
- Testes C++ vivem em `unreal/JogoResgate/Source/JogoResgate/Tests/` (prefixo `JR.`).

# tools/

- `pipeline/` e `setup/`: Python 3.11+ padrão, rodam em qualquer SO e no CI.
- `blender/`: rodam dentro do Blender (`blender -b --python script.py -- args`). Funções puras separadas das que usam `bpy` (importado só dentro de funções de editor).
- `unreal/`: rodam só no Python do Editor Unreal. Mesma separação: `unreal` importado tardiamente.
- Todos com `--help`, logs auditáveis (`tools/common.py`), código de saída != 0 em falha, sem caminhos absolutos.
- Todo script novo ganha teste em `tests/python/` com fixtures em `tests/fixtures/`.

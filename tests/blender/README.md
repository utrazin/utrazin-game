# Testes Blender

A lógica pura de `tools/blender/*.py` é testada em `tests/python/` (sem Blender). O teste de integração roda dentro do Blender:

```powershell
# Com o Blender instalado
blender -b --factory-startup --python tests\blender\smoke_test.py
# Ou com o Blender como módulo Python (mesmo usado no CI)
python -m pip install "bpy==5.2.4"
python tests\blender\smoke_test.py
```

O smoke test cria uma cena mínima, roda `validate_scene` com snapshot real do Blender, exporta FBX com o preset `fbx_unreal.json`, cria uma armature com a hierarquia UE5 e roda `validate_rig` (caso positivo e negativo).

Último resultado: **SMOKE OK** em 2026-11-11 com `bpy 5.2.4 LTS` (módulo do PyPI, Linux). Ainda não executado com o Blender instalado no Windows.

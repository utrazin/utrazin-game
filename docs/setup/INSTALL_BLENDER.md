# Instalar Blender 5.2 LTS

1. Baixe em https://www.blender.org/download/lts/ (versão **5.2 LTS**, instalador Windows ou portable `.zip`).
2. Instale no SSD E: (ex.: `E:\Tools\Blender\5.2`).
3. Adicione a pasta ao `PATH` **ou** defina a variável `BLENDER_EXE` apontando para `blender.exe` (usada por `tools/blender/*.py` e pelo `check_environment.py`).
4. Preferências recomendadas:
   - **Edit > Preferences > System**: GPU em Cycles (CUDA/OptiX/HIP).
   - **Save & Load**: Auto Save ativo a cada 2 min.
   - **Units** nas cenas de produção: Metric, Unit Scale 1.0 (o template em `blender/templates/` já define isso).

Licença: GPL. O que você cria no Blender é seu; a GPL não se aplica às suas malhas.

## Rodar scripts do pipeline

```powershell
blender -b blender\scenes\characters\CHR-001_v001.blend --python tools\blender\validate_scene.py -- --config tools\blender\validation_config.json --report reports\CHR-001_scene.json
```

Tudo depois de `--` vai para o script. Ver `--help` de cada script:

```powershell
blender -b --python tools\blender\export_assets.py -- --help
```

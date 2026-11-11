# Setup no Windows

Ordem recomendada. Tudo gratuito.

1. **Git for Windows** (inclui Git LFS): https://git-scm.com/download/win
   - Depois: `git lfs install`
2. **Python 3.11+**: https://www.python.org/downloads/ (marque "Add python.exe to PATH")
3. **uv** (opcional, gerenciador rápido de Python): `powershell -c "irm https://astral.sh/uv/install.ps1 | iex"`
4. **Epic Games Launcher + Unreal Engine 5.8.4**: ver [`INSTALL_UNREAL.md`](INSTALL_UNREAL.md)
5. **Visual Studio 2022 Community**: ver [`INSTALL_UNREAL.md`](INSTALL_UNREAL.md)
6. **Blender 5.2 LTS**: ver [`INSTALL_BLENDER.md`](INSTALL_BLENDER.md)
7. **Claude Code** (opcional para trabalhar no repo localmente): https://docs.claude.com/en/docs/claude-code

Em seguida, na raiz do repo:

```powershell
powershell -ExecutionPolicy Bypass -File tools\setup\setup_windows.ps1
```

O script **não instala nada sozinho**: verifica as ferramentas, cria `.venv`, instala dependências de `tools/requirements.txt`, configura Git LFS e roda `check_environment.py`.

## Espaço em disco

- Unreal 5.8 (sem plataformas extras e sem símbolos de debug): ~60 GB
- Visual Studio com workload de C++: ~30 GB
- Projeto + DerivedDataCache: 20 a 50 GB ao longo do desenvolvimento
- **Reserve 150 GB no SSD E:** e instale a engine nele se o C: estiver cheio (o Epic Launcher permite escolher a pasta).

## Execução de scripts

Se o PowerShell bloquear scripts: use `-ExecutionPolicy Bypass` só no comando, sem alterar a política global.

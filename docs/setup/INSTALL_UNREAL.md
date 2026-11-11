# Instalar Unreal Engine 5.8.4 e Visual Studio

## 1. Epic Games Launcher

1. Baixe em https://store.epicgames.com/download e faça login.
2. Aba **Unreal Engine > Library > + (Engine Versions)** e selecione **5.8.4**.
3. Em **Options**, desmarque plataformas que não usará (Android, iOS, Linux) e "Editor symbols for debugging" (economiza dezenas de GB). Mantenha **Starter Content** e **Templates and Feature Packs**.
4. Escolha a pasta de instalação no **SSD E:** (ex.: `E:\Epic\UE_5.8`).

Licença: Unreal Engine EULA (gratuito para desenvolvimento; royalties de 5% somente acima de US$ 1 milhão de receita bruta por produto, confira o EULA vigente).

## 2. Visual Studio 2022 Community

1. https://visualstudio.microsoft.com/vs/community/
2. Workloads: **Game development with C++** e **Desktop development with C++**.
3. Componentes individuais: **MSVC v143 (última)**, **Windows 11 SDK** (o recomendado pela página "Setting up Visual Studio" da UE 5.8), **.NET 8 runtime**, **Unreal Engine installer** e **Unreal Engine Test Adapter** (opcional).
4. Confira a versão exata de MSVC/SDK exigida nas release notes da 5.8: https://dev.epicgames.com/documentation/unreal-engine/unreal-engine-5-8-release-notes

## 3. Primeira compilação do projeto

O projeto já existe em `unreal/JogoResgate/` (código C++ **ainda não compilado**).

```powershell
# Ajuste o caminho da engine
$UE = "E:\Epic\UE_5.8"
& "$UE\Engine\Build\BatchFiles\Build.bat" JogoResgateEditor Win64 Development -Project="$PWD\unreal\JogoResgate\JogoResgate.uproject" -WaitMutex 2>&1 | Tee-Object docs\qa\build-first.log
```

Ou: botão direito no `.uproject` > **Generate Visual Studio project files**, abra o `.sln`, compile `Development Editor`.

Se houver erros: são esperados na primeira compilação (o código foi escrito sem engine disponível). Peça ao Claude Code para corrigir passando o log `docs/qa/build-first.log`.

## 4. Abrir o Editor

Duplo clique em `JogoResgate.uproject`. Na primeira abertura, compile shaders (pode levar 20 a 60 min).

## 5. Plugins usados (todos nativos da engine)

| Plugin | Motivo |
|---|---|
| ChaosVehiclesPlugin | Física do SUV |
| EnhancedInput | Input por contexto (padrão na 5.x) |
| StateTree + GameplayStateTree | IA (ADR-002) |
| PythonScriptPlugin + EditorScriptingUtilities | Importação/validação por script |
| DataValidation | Validação de conteúdo |

## 6. Python dentro da Unreal

Scripts de `tools/unreal/` rodam só no Python embutido do Editor:

```powershell
& "$UE\Engine\Binaries\Win64\UnrealEditor-Cmd.exe" "$PWD\unreal\JogoResgate\JogoResgate.uproject" -run=pythonscript -script="$PWD\tools\unreal\validate_content.py" -unattended -nullrhi
```

# Testes Unreal

Automation Tests em C++ ficam em `unreal/JogoResgate/Source/JogoResgate/Tests/` (filtro `JR.`).

```powershell
& "$env:UE_ROOT\Engine\Binaries\Win64\UnrealEditor-Cmd.exe" "$PWD\unreal\JogoResgate\JogoResgate.uproject" -ExecCmds="Automation RunTests JR.; Quit" -unattended -nullrhi -nosplash -log -ReportExportPath="$PWD\reports\automation"
```

Status: 7/7 ok em 2026-11-11 (UE 5.8.4, Windows 11).

| Grupo | O que cobre |
|---|---|
| `JR.Save.Migration` | migração de SaveGame entre versões |
| `JR.Vehicle.DamageModel` | zonas, pneus, integridade, escala de torque |
| `JR.Combat.Ammo` | disparo, recarga, reserva |
| `JR.AI.AimPrediction` | interceptação e dispersão |

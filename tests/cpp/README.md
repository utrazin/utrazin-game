# Testes C++ da lógica pura (fora da Unreal)

Compila com `g++`/`clang++` os arquivos de lógica pura do jogo usando stubs mínimos de tipos da Unreal (`stubs/CoreMinimal.h`) e roda as verificações de `pure_logic_tests.cpp`.

```bash
sh tests/cpp/run_pure_tests.sh
```

Cobre: `FJRVehicleDamageState`, `FJRAmmoState`, `FJRAimPrediction`, `FJREnemyStateLogic`.

**Limite**: prova que a matemática e as regras estão corretas, **não** que o código compila com a Unreal (UHT, macros reais, `FVector` da engine). A verificação definitiva são os Automation Tests `JR.*` com a engine instalada.

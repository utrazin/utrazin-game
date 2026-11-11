# Regras de C++ (Unreal)

- Prefixos: `U` (UObject), `A` (Actor), `F` (struct/valor), `E` (enum), `I` (interface), `T` (template). Prefixo de projeto `JR` após o prefixo de tipo: `AJRCharacter`, `FJRAmmoState`.
- Um tipo principal por arquivo; arquivo com o nome sem prefixo de tipo (`JRCharacter.h`).
- `#pragma once`; inclua o `.generated.h` por último.
- Responsabilidade única; prefira **componentes** (composition over inheritance).
- Interfaces (`UINTERFACE`) para sistemas desacoplados (`IJRInteractable`).
- Eventos por **delegates** (`DECLARE_DYNAMIC_MULTICAST_DELEGATE_*`). Sem polling.
- `PrimaryComponentTick.bCanEverTick = false` por padrão. Tick exige comentário justificando.
- Estados e eventos relevantes como **Gameplay Tags** nativas (`JRGameplayTags.h`).
- Configuração em `UPROPERTY(EditDefaultsOnly)` ou Data Assets, nunca números mágicos espalhados.
- Lógica pura em `F` structs/funções estáticas sem dependência de mundo, com Automation Test.
- `check`/`ensure` para invariantes; `UE_LOG(LogJR, ...)` para diagnósticos. Sem `GEngine->AddOnScreenDebugMessage` em código final.
- Referências a assets: `TSoftObjectPtr`/`TSoftClassPtr` em Data Assets; nada de caminhos absolutos ou `ConstructorHelpers` para conteúdo de produção.
- Sem replication, RPC ou `bReplicates`.
- `const` correctness; `TObjectPtr` em membros `UPROPERTY`.
- Comentários documentam o **porquê**; decisões não triviais vão para ADR.
- Formatação: tabs, chaves em nova linha (estilo Epic).

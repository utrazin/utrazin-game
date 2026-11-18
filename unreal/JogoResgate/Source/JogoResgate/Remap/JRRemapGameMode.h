// Copyright utrazin. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"
#include "Core/JRGameMode.h"
#include "JRRemapGameMode.generated.h"

/**
 * [Remap F1] Regras da cidade Villa Star e da arena: sempre a pé, nasce no PlayerStart, recebe as armas
 * compradas e a Bancada. Na arena, morrer encerra a corrida (contrato de morte) e volta para a cidade.
 * Os mapas do F1 usam esta classe direto no World Settings (build_remap_f1.py).
 */
UCLASS()
class JOGORESGATE_API AJRRemapGameMode : public AJRGameMode
{
	GENERATED_BODY()

public:
	AJRRemapGameMode();

	virtual void StartPlay() override;
	virtual AActor* FindPlayerStart_Implementation(AController* Player, const FString& IncomingName) override;
	virtual UClass* GetDefaultPawnClassForController_Implementation(AController* InController) override;
	virtual APawn* SpawnDefaultPawnFor_Implementation(AController* NewPlayer, AActor* StartSpot) override;
	virtual void SetPlayerDefaults(APawn* PlayerPawn) override;
	virtual void HandlePlayerFailure(APawn* FailedPawn) override;

protected:
	/** Tempo entre cair e voltar para a cidade (dá para ver a morte). */
	UPROPERTY(EditDefaultsOnly, Category = "Remap", meta = (Units = "s"))
	float DeathReturnDelay = 3.f;

private:
	void ReturnAfterDeath();

	FTimerHandle DeathTimer;
	bool bDeathPending = false;
};

// Copyright utrazin. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/GameModeBase.h"
#include "JRGameMode.generated.h"

class AJRCharacter;
class AJRCheckpoint;
class UJRLevelDefinition;

/**
 * Regras de uma fase: escolhe onde e com qual pawn o jogador começa (veículo ou a pé)
 * a partir do último checkpoint salvo, e reinicia no checkpoint após falha (A-013, A-014).
 * Cada mapa usa um BP filho (ex.: BP_GameMode_L01) com o LevelDefinition preenchido.
 */
UCLASS()
class JOGORESGATE_API AJRGameMode : public AGameModeBase
{
	GENERATED_BODY()

public:
	AJRGameMode();

	virtual void StartPlay() override;
	virtual AActor* FindPlayerStart_Implementation(AController* Player, const FString& IncomingName) override;
	virtual UClass* GetDefaultPawnClassForController_Implementation(AController* InController) override;
	virtual APawn* SpawnDefaultPawnFor_Implementation(AController* NewPlayer, AActor* StartSpot) override;
	virtual void SetPlayerDefaults(APawn* PlayerPawn) override;

	/** Morte do personagem ou carro inutilizado. Idempotente. */
	UFUNCTION(BlueprintCallable, Category = "Game")
	void HandlePlayerFailure(APawn* FailedPawn);

	/** Classe do personagem selecionado (save + catálogo), com fallback. */
	TSubclassOf<AJRCharacter> ResolveCharacterClass() const;

	/** Aplica a skin selecionada no save. */
	void ApplySelectedSkin(AJRCharacter* Character) const;

	UFUNCTION(BlueprintPure, Category = "Game")
	UJRLevelDefinition* GetLevelDefinition() const { return LevelDefinition; }

protected:
	AJRCheckpoint* ResolveRespawnCheckpoint() const;
	void RestartFromCheckpoint();

	UPROPERTY(EditDefaultsOnly, Category = "Game")
	TObjectPtr<UJRLevelDefinition> LevelDefinition;

	/** Usado se a fase não definir VehicleClass. */
	UPROPERTY(EditDefaultsOnly, Category = "Game")
	TSubclassOf<APawn> FallbackVehicleClass;

	/** Usado se o personagem selecionado não tiver classe própria. */
	UPROPERTY(EditDefaultsOnly, Category = "Game")
	TSubclassOf<AJRCharacter> FallbackCharacterClass;

	UPROPERTY(EditDefaultsOnly, Category = "Game", meta = (Units = "s"))
	float RestartDelay = 1.5f;

private:
	FTimerHandle RestartTimer;
	bool bFailurePending = false;
};

// Copyright utrazin. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/GameModeBase.h"
#include "JRGameMode.generated.h"

class AJRCharacter;
class AJRCheckpoint;
class AJRVehiclePawn;
class UJRLevelDefinition;
struct FJRSkinDefinition;

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
	virtual void HandlePlayerFailure(APawn* FailedPawn); // [Remap F1] virtual

	/** Classe do personagem selecionado (save + catálogo), com fallback. */
	TSubclassOf<AJRCharacter> ResolveCharacterClass() const;

	/** Aplica a skin selecionada no save. */
	void ApplySelectedSkin(AJRCharacter* Character) const;

	/** Armas do checkpoint onde a fase (re)começou (herói criado ao sair do carro depois de renascer nele). */
	void ApplyRespawnLoadout(AJRCharacter* Character) const;

	/** O carro colocado no mapa (buggy do acampamento), se houver e não estiver destruído. */
	AJRVehiclePawn* FindLevelVehicle() const;

	/** Skin selecionada no save (ou a primeira do personagem). Nulo se não houver. */
	const FJRSkinDefinition* ResolveSelectedSkin() const;

	UFUNCTION(BlueprintPure, Category = "Game")
	UJRLevelDefinition* GetLevelDefinition() const { return LevelDefinition; }

	/**
	 * [A-074] A abertura (tela de start + queda da nave) roda nesta carga do mapa: há um AJRIntroDirector ligado,
	 * a fase começa do início e não é um renascer depois de morrer. Aí o herói nasce no ponto do diretor (ao lado da nave).
	 * Decidido uma vez por carga do mapa.
	 */
	bool ShouldPlayIntro() const;

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

	/** No Editor (PIE), cada Play começa do início da fase; o checkpoint salvo só vale após morrer. */
	UPROPERTY(EditDefaultsOnly, Category = "Game")
	bool bStartFromBeginningInEditor = true;

	/** Altura extra ao spawnar personagem num checkpoint (meia altura da cápsula + folga). */
	UPROPERTY(EditDefaultsOnly, Category = "Game", meta = (Units = "cm"))
	float CharacterSpawnHeight = 110.f;

	/** Altura extra ao spawnar veículo num checkpoint. */
	UPROPERTY(EditDefaultsOnly, Category = "Game", meta = (Units = "cm"))
	float VehicleSpawnHeight = 80.f;

	/**
	 * Fase com carro colocado no mapa (L01 v3): renascer "no carro" usa esse carro (não cria outro) e
	 * renascer a pé estaciona o carro no ponto do checkpoint (bParkVehicleOnRespawn).
	 */
	UPROPERTY(EditDefaultsOnly, Category = "Game")
	bool bUseLevelVehicle = true;

private:
	/** Checkpoint usado no começo desta carga do mapa (guardado no StartPlay). */
	TWeakObjectPtr<AJRCheckpoint> StartCheckpoint;

	FTimerHandle RestartTimer;
	bool bFailurePending = false;

	/** [A-074] -1 = ainda não decidido, 0 = sem abertura, 1 = com abertura. */
	mutable int8 IntroDecision = -1;
};

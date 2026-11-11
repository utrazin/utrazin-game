// Copyright utrazin. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"
#include "Subsystems/GameInstanceSubsystem.h"
#include "JRProgressionSubsystem.generated.h"

class UJRSaveGame;

DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FJROnProgressSaved, bool, bSuccess);

/**
 * Dono do save local (A-016). Vive enquanto o jogo roda, independente de mapa e de pawn.
 * Escrita síncrona simples: o save é pequeno.
 */
UCLASS()
class JOGORESGATE_API UJRProgressionSubsystem : public UGameInstanceSubsystem
{
	GENERATED_BODY()

public:
	virtual void Initialize(FSubsystemCollectionBase& Collection) override;

	UFUNCTION(BlueprintCallable, Category = "Progression")
	bool SaveNow();

	/** Carrega do disco (migrando) ou cria um save novo. */
	UFUNCTION(BlueprintCallable, Category = "Progression")
	void LoadOrCreate();

	UFUNCTION(BlueprintCallable, Category = "Progression")
	void RecordCheckpoint(FName LevelId, FName CheckpointId);

	UFUNCTION(BlueprintCallable, Category = "Progression")
	void CompleteLevel(FName LevelId, FName NextLevelId);

	UFUNCTION(BlueprintCallable, Category = "Progression")
	void SelectCharacter(FName CharacterId, FName SkinId);

	UFUNCTION(BlueprintPure, Category = "Progression")
	FName GetLastCheckpoint(FName LevelId) const;

	UFUNCTION(BlueprintPure, Category = "Progression")
	bool IsLevelUnlocked(FName LevelId) const;

	/** Apaga o checkpoint de uma fase (novo jogo na fase). */
	UFUNCTION(BlueprintCallable, Category = "Progression")
	void ClearCheckpoint(FName LevelId);

	UFUNCTION(BlueprintPure, Category = "Progression")
	UJRSaveGame* GetSave() const { return Save; }

	UPROPERTY(BlueprintAssignable, Category = "Progression")
	FJROnProgressSaved OnProgressSaved;

	static const FString SlotName;
	static constexpr int32 UserIndex = 0;

private:
	UPROPERTY()
	TObjectPtr<UJRSaveGame> Save;
};

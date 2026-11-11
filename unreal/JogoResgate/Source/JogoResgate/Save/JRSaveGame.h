// Copyright utrazin. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/SaveGame.h"
#include "JRSaveGame.generated.h"

/** Progresso de uma fase. */
USTRUCT(BlueprintType)
struct FJRLevelProgress
{
	GENERATED_BODY()

	UPROPERTY(BlueprintReadOnly, Category = "Save")
	FName LevelId;

	UPROPERTY(BlueprintReadOnly, Category = "Save")
	FName LastCheckpointId;

	UPROPERTY(BlueprintReadOnly, Category = "Save")
	bool bCompleted = false;
};

/** Configurações do jogador (GDD 3.1). */
USTRUCT(BlueprintType)
struct FJRPlayerSettings
{
	GENERATED_BODY()

	UPROPERTY(BlueprintReadWrite, Category = "Settings")
	float MasterVolume = 1.f;

	UPROPERTY(BlueprintReadWrite, Category = "Settings")
	float MusicVolume = 0.8f;

	UPROPERTY(BlueprintReadWrite, Category = "Settings")
	float SfxVolume = 1.f;

	UPROPERTY(BlueprintReadWrite, Category = "Settings")
	float MouseSensitivity = 1.f;

	UPROPERTY(BlueprintReadWrite, Category = "Settings")
	bool bInvertY = false;

	UPROPERTY(BlueprintReadWrite, Category = "Settings")
	FString Culture = TEXT("pt-BR");
};

/**
 * Save local versionado (A-016). Ao mudar campos: incremente CurrentVersion e
 * adicione o passo em FJRSaveMigration::Migrate + teste JR.Save.Migration.
 */
UCLASS()
class JOGORESGATE_API UJRSaveGame : public USaveGame
{
	GENERATED_BODY()

public:
	static constexpr int32 CurrentVersion = 1;

	/** 0 = save criado antes do versionamento ou recém-criado sem migração. */
	UPROPERTY()
	int32 SaveVersion = 0;

	UPROPERTY(BlueprintReadOnly, Category = "Save")
	FName SelectedCharacterId;

	UPROPERTY(BlueprintReadOnly, Category = "Save")
	FName SelectedSkinId;

	UPROPERTY(BlueprintReadOnly, Category = "Save")
	FName CurrentLevelId;

	UPROPERTY(BlueprintReadOnly, Category = "Save")
	TArray<FJRLevelProgress> Levels;

	UPROPERTY(BlueprintReadOnly, Category = "Save")
	TArray<FName> UnlockedLevels;

	UPROPERTY(BlueprintReadOnly, Category = "Save")
	FJRPlayerSettings Settings;

	FJRLevelProgress& FindOrAddLevel(FName LevelId);
	const FJRLevelProgress* FindLevel(FName LevelId) const;
};

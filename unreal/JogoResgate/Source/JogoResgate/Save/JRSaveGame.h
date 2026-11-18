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
	static constexpr int32 CurrentVersion = 3; // [A-074] v2: bIntroSeen; [Remap F1] v3: carteira, bancada, armas compradas

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

	/** [A-074] Já viu a abertura inteira (ou pulou): "Jogar" vai direto ao fim; "Ver abertura" mostra de novo. */
	UPROPERTY(BlueprintReadWrite, Category = "Save")
	bool bIntroSeen = false;

	// ---------------- [Remap F1] v3: cidade Villa Star + arena
	/** Créditos (dinheiro). */
	UPROPERTY(BlueprintReadOnly, Category = "Save|Remap")
	int64 Credits = 0;

	/** Sucata e cristais (F3; já guardados para não precisar de outra versão). */
	UPROPERTY(BlueprintReadOnly, Category = "Save|Remap")
	int64 Scrap = 0;

	UPROPERTY(BlueprintReadOnly, Category = "Save|Remap")
	int64 Crystals = 0;

	/** Nível da Bancada (cada nível = +10% de dano). */
	UPROPERTY(BlueprintReadOnly, Category = "Save|Remap")
	int32 BenchLevel = 0;

	/** Armas compradas no Armeiro (valores de EJRWeaponSlot). Graveto e pistola são de graça. */
	UPROPERTY(BlueprintReadOnly, Category = "Save|Remap")
	TArray<uint8> OwnedWeaponSlots;

	/** Recorde de ondas numa corrida e corridas jogadas. */
	UPROPERTY(BlueprintReadOnly, Category = "Save|Remap")
	int32 BestWave = 0;

	UPROPERTY(BlueprintReadOnly, Category = "Save|Remap")
	int32 RunsPlayed = 0;

	FJRLevelProgress& FindOrAddLevel(FName LevelId);
	const FJRLevelProgress* FindLevel(FName LevelId) const;
};

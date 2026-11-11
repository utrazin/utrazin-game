// Copyright utrazin. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"
#include "Engine/DataAsset.h"
#include "JRLevelDefinition.generated.h"

class APawn;
class UJRCharacterDefinition;
class UJREnemyArchetype;
class USoundBase;
class UWorld;

UENUM(BlueprintType)
enum class EJRPerformanceProfile : uint8
{
	Low,
	Medium,
	High
};

/**
 * Configuração de uma fase (docs/gameplay/LEVELS.md). Nova fase = novo Data Asset + mapa, sem código.
 */
UCLASS(BlueprintType)
class JOGORESGATE_API UJRLevelDefinition : public UPrimaryDataAsset
{
	GENERATED_BODY()

public:
	virtual FPrimaryAssetId GetPrimaryAssetId() const override
	{
		return FPrimaryAssetId(TEXT("JRLevel"), LevelId);
	}

	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Level")
	FName LevelId = TEXT("L01");

	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Level")
	FText DisplayName;

	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Level")
	FText Theme;

	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Level")
	TSoftObjectPtr<UWorld> Map;

	/** Fase seguinte a desbloquear ao concluir (None = última). */
	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Level")
	FName NextLevelId;

	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Level|Gameplay")
	TArray<TSoftObjectPtr<UJRCharacterDefinition>> AvailableCharacters;

	/** Blueprint do veículo (BP_Vehicle_*) usado na fase. */
	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Level|Gameplay")
	TSoftClassPtr<APawn> VehicleClass;

	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Level|Gameplay")
	TArray<TSoftObjectPtr<UJREnemyArchetype>> EnemyArchetypes;

	/** Ids dos checkpoints na ordem do percurso (devem existir no mapa como AJRCheckpoint). */
	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Level|Gameplay")
	TArray<FName> CheckpointIds;

	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Level|Gameplay")
	FName RescueTargetId;

	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Level|Mood")
	TSoftObjectPtr<USoundBase> Ambience;

	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Level|Mood")
	TSoftObjectPtr<USoundBase> Music;

	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Level|Mood")
	FName WeatherPreset;

	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Level|Mood")
	FName LightingPreset;

	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Level|Performance")
	EJRPerformanceProfile PerformanceProfile = EJRPerformanceProfile::High;

	/** Orçamento de inimigos com atualização completa (A-029). */
	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Level|Performance", meta = (ClampMin = "1"))
	int32 MaxFullUpdateEnemies = 12;

	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Level|Performance", meta = (ClampMin = "1"))
	int32 MaxVisibleEnemies = 30;
};

// Copyright utrazin. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"
#include "Engine/DataAsset.h"
#include "JRLevelDefinition.generated.h"

class APawn;
class UJRCharacterDefinition;
class UJREnemyArchetype;
class USoundBase;
class UTexture2D;
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

	/** Imagem de cima da fase (norte para cima) usada no minimapa e no mapa grande. */
	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Level|Minimap")
	TSoftObjectPtr<UTexture2D> MinimapTexture;

	/** [A-067] Imagem do mapa grande (tecla M), com os nomes dos lugares. Vazio = usa MinimapTexture. Mesmo enquadramento. */
	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Level|Minimap")
	TSoftObjectPtr<UTexture2D> BigMapTexture;

	/** Canto da imagem no mundo (cm): X mínimo, Y mínimo (topo-esquerda = X mín, Y mín). */
	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Level|Minimap")
	FVector2D MinimapWorldMin = FVector2D(-100000.f, -100000.f);

	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Level|Minimap")
	FVector2D MinimapWorldMax = FVector2D(100000.f, 100000.f);

	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Level|Performance")
	EJRPerformanceProfile PerformanceProfile = EJRPerformanceProfile::High;

	/** Orçamento de inimigos com atualização completa (A-029). */
	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Level|Performance", meta = (ClampMin = "1"))
	int32 MaxFullUpdateEnemies = 12;

	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Level|Performance", meta = (ClampMin = "1"))
	int32 MaxVisibleEnemies = 30;
};

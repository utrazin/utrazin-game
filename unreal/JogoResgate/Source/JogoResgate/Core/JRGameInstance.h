// Copyright utrazin. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"
#include "Engine/GameInstance.h"
#include "JRGameInstance.generated.h"

class UJRCharacterDefinition;
class UJRLevelDefinition;

/** Catálogo de conteúdo jogável. Configurado no Blueprint BP_GameInstance. */
UCLASS()
class JOGORESGATE_API UJRGameInstance : public UGameInstance
{
	GENERATED_BODY()

public:
	UFUNCTION(BlueprintCallable, Category = "Catalog")
	UJRCharacterDefinition* FindCharacterDefinition(FName CharacterId) const;

	UFUNCTION(BlueprintCallable, Category = "Catalog")
	UJRLevelDefinition* FindLevelDefinition(FName LevelId) const;

	const TArray<TSoftObjectPtr<UJRCharacterDefinition>>& GetCharacters() const { return Characters; }

	const TArray<TSoftObjectPtr<UJRLevelDefinition>>& GetLevels() const { return Levels; }

protected:
	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Catalog")
	TArray<TSoftObjectPtr<UJRCharacterDefinition>> Characters;

	/** Fases na ordem de progressão linear (A-012). */
	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Catalog")
	TArray<TSoftObjectPtr<UJRLevelDefinition>> Levels;
};

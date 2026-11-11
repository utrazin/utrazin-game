// Copyright utrazin. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"
#include "Engine/DataAsset.h"
#include "JRCharacterDefinition.generated.h"

class AJRCharacter;
class UMaterialInterface;
class USkeletalMesh;
class UTexture2D;

/** Skin cosmética (A-006): mesma cápsula e esqueleto, troca malha e materiais. */
USTRUCT(BlueprintType)
struct FJRSkinDefinition
{
	GENERATED_BODY()

	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Skin")
	FName SkinId;

	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Skin")
	FText DisplayName;

	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Skin")
	TSoftObjectPtr<USkeletalMesh> Mesh;

	/** Opcional: sobrescreve materiais por slot (índice = slot). */
	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Skin")
	TArray<TSoftObjectPtr<UMaterialInterface>> MaterialOverrides;

	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Skin")
	TSoftObjectPtr<UTexture2D> Portrait;
};

/** Personagem jogável (DA_Character_*). */
UCLASS(BlueprintType)
class JOGORESGATE_API UJRCharacterDefinition : public UPrimaryDataAsset
{
	GENERATED_BODY()

public:
	virtual FPrimaryAssetId GetPrimaryAssetId() const override
	{
		return FPrimaryAssetId(TEXT("JRCharacter"), CharacterId);
	}

	const FJRSkinDefinition* FindSkin(FName SkinId) const
	{
		return Skins.FindByPredicate([SkinId](const FJRSkinDefinition& Skin) { return Skin.SkinId == SkinId; });
	}

	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Character")
	FName CharacterId = TEXT("CHR-001");

	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Character")
	FText DisplayName;

	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Character")
	TSoftClassPtr<AJRCharacter> CharacterClass;

	/** Pelo menos 2 skins no MVP (GDD 5). A primeira é a padrão. */
	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Character")
	TArray<FJRSkinDefinition> Skins;
};

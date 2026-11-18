// Copyright utrazin. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "Interactions/JRInteractable.h"
#include "Remap/JRRemapTypes.h"
#include "JRShopkeeper.generated.h"

class UAnimationAsset;
class UCapsuleComponent;
class USkeletalMesh;
class USkeletalMeshComponent;
class UStaticMeshComponent;
class UTextRenderComponent;

/**
 * [Remap F1] Vendedor da cidade (REMAP 4 e 9.3): chega perto, aperta E, abre a lista ao lado (desenhada pela
 * AJRRemapHUD). Sem modelo, aparece uma cápsula colorida com o nome em cima. Com SK_NPC_* importado, o
 * build_remap_f1.py põe a malha e a animação parada (Breathing_Idle) e a cápsula some.
 * Krug = Armeiro, Ix-Vel = Bancada, Kaar = Portão (ver docs/design/ALIENIGENAS_NPC.md).
 */
UCLASS()
class JOGORESGATE_API AJRShopkeeper : public AActor, public IJRInteractable
{
	GENERATED_BODY()

public:
	AJRShopkeeper();

	virtual void OnConstruction(const FTransform& Transform) override;

	virtual bool CanInteract_Implementation(AActor* InstigatorActor) const override;
	virtual void Interact_Implementation(AActor* InstigatorActor) override;
	virtual FText GetInteractionText_Implementation() const override;

	UFUNCTION(BlueprintPure, Category = "Shop")
	EJRShopType GetShopType() const { return ShopType; }

	UFUNCTION(BlueprintPure, Category = "Shop")
	FText GetDisplayName() const { return DisplayName; }

	/** Fala curta ao abrir (sorteia uma). */
	FString PickGreeting() const;

	/** Toca a animação de fala por alguns segundos e volta para a parada. */
	void PlayTalk();

protected:
	virtual void BeginPlay() override;
	void BackToIdle();
	/** Cápsula colorida sem modelo; com modelo, ajusta cápsula, pés e nome à altura da malha. */
	void RefreshVisual();

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Shop")
	EJRShopType ShopType = EJRShopType::Armeiro;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Shop")
	FText DisplayName;

	UPROPERTY(EditAnywhere, Category = "Shop")
	TArray<FString> Greetings;

	UPROPERTY(EditAnywhere, Category = "Shop")
	FLinearColor PlaceholderColor = FLinearColor(0.6f, 0.6f, 0.6f);

	/** Giro da malha para ela olhar para a frente do ator (+X). GLB do Blender costuma precisar de -90. */
	UPROPERTY(EditAnywhere, Category = "Shop|Visual")
	float MeshYawOffset = -90.f;

	UPROPERTY(EditAnywhere, Category = "Shop|Visual")
	TObjectPtr<UAnimationAsset> IdleAnim;

	UPROPERTY(EditAnywhere, Category = "Shop|Visual")
	TObjectPtr<UAnimationAsset> TalkAnim;

	UPROPERTY(VisibleAnywhere, Category = "Shop")
	TObjectPtr<UCapsuleComponent> Capsule;

	UPROPERTY(VisibleAnywhere, Category = "Shop")
	TObjectPtr<USkeletalMeshComponent> Mesh;

	UPROPERTY(VisibleAnywhere, Category = "Shop")
	TObjectPtr<UStaticMeshComponent> Placeholder;

	UPROPERTY(VisibleAnywhere, Category = "Shop")
	TObjectPtr<UTextRenderComponent> NameTag;

private:
	FTimerHandle TalkTimer;
};

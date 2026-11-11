// Copyright utrazin. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "Interactions/JRInteractable.h"
#include "JRRescueTarget.generated.h"

class UAnimMontage;
class USkeletalMeshComponent;
class UStaticMeshComponent;

/**
 * Pessoa presa (GDD 4.1, passo 7). Só pode ser libertada no estágio Rescue.
 * Abre a cela (evento BP), alinha jogador e vítima, toca o abraço e conclui a fase.
 */
UCLASS()
class JOGORESGATE_API AJRRescueTarget : public AActor, public IJRInteractable
{
	GENERATED_BODY()

public:
	AJRRescueTarget();

	virtual bool CanInteract_Implementation(AActor* InstigatorActor) const override;
	virtual void Interact_Implementation(AActor* InstigatorActor) override;
	virtual FText GetInteractionText_Implementation() const override;

	UFUNCTION(BlueprintPure, Category = "Rescue")
	FName GetRescueId() const { return RescueId; }

protected:
	/** Animação/efeito de abrir a grade (implementado no BP). */
	UFUNCTION(BlueprintImplementableEvent, Category = "Rescue")
	void OnCageOpened();

	UFUNCTION(BlueprintImplementableEvent, Category = "Rescue")
	void OnRescueCompleted();

	void FinishRescue();

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Rescue")
	TObjectPtr<USceneComponent> Root;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Rescue")
	TObjectPtr<UStaticMeshComponent> CageMesh;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Rescue")
	TObjectPtr<USkeletalMeshComponent> VictimMesh;

	/** Onde o jogador é posicionado para o abraço. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Rescue")
	TObjectPtr<USceneComponent> PlayerAlignPoint;

	UPROPERTY(EditAnywhere, Category = "Rescue")
	FName RescueId = TEXT("Victim01");

	UPROPERTY(EditDefaultsOnly, Category = "Rescue")
	TObjectPtr<UAnimMontage> VictimHugMontage;

	UPROPERTY(EditDefaultsOnly, Category = "Rescue")
	FText InteractionText;

	/** Usado se nenhuma montage tiver duração. */
	UPROPERTY(EditDefaultsOnly, Category = "Rescue", meta = (Units = "s"))
	float FallbackHugDuration = 3.f;

private:
	FTimerHandle FinishTimer;
	bool bRescued = false;
};

// Copyright utrazin. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "JRInteractionComponent.generated.h"

/** Encontra e aciona IJRInteractable à frente da câmera. Chamado por input, sem Tick. */
UCLASS(ClassGroup = (JogoResgate), meta = (BlueprintSpawnableComponent))
class JOGORESGATE_API UJRInteractionComponent : public UActorComponent
{
	GENERATED_BODY()

public:
	UJRInteractionComponent();

	/** Retorna o ator interagível sob a mira (ou nullptr). */
	UFUNCTION(BlueprintCallable, Category = "Interaction")
	AActor* FindInteractable() const;

	UFUNCTION(BlueprintCallable, Category = "Interaction")
	bool TryInteract();

protected:
	UPROPERTY(EditDefaultsOnly, Category = "Interaction", meta = (Units = "cm"))
	float InteractionDistance = 250.f;

	UPROPERTY(EditDefaultsOnly, Category = "Interaction", meta = (Units = "cm"))
	float TraceRadius = 20.f;
};

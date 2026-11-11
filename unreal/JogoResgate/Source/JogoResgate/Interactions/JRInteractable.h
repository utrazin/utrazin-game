// Copyright utrazin. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"
#include "UObject/Interface.h"
#include "JRInteractable.generated.h"

UINTERFACE(MinimalAPI, BlueprintType)
class UJRInteractable : public UInterface
{
	GENERATED_BODY()
};

/** Objetos interagíveis: portas, grades, cela do resgate, itens. */
class JOGORESGATE_API IJRInteractable
{
	GENERATED_BODY()

public:
	UFUNCTION(BlueprintNativeEvent, BlueprintCallable, Category = "Interaction")
	bool CanInteract(AActor* InstigatorActor) const;

	UFUNCTION(BlueprintNativeEvent, BlueprintCallable, Category = "Interaction")
	void Interact(AActor* InstigatorActor);

	/** Texto do prompt no HUD (via String Table). */
	UFUNCTION(BlueprintNativeEvent, BlueprintCallable, Category = "Interaction")
	FText GetInteractionText() const;
};

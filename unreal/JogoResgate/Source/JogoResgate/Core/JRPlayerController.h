// Copyright utrazin. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/PlayerController.h"
#include "JRPlayerController.generated.h"

class AJRCharacter;
class AJRVehiclePawn;
class UInputMappingContext;

DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FJROnControlledPawnChanged, APawn*, NewPawn);

/**
 * Controller independente do pawn atual (veículo ou personagem). Troca o Input Mapping Context
 * por contexto e conduz a transição carro -> a pé sem duplicar personagens.
 */
UCLASS()
class JOGORESGATE_API AJRPlayerController : public APlayerController
{
	GENERATED_BODY()

public:
	/** Sai do veículo atual: estaciona, spawna/reutiliza o personagem, possui e toca a animação. */
	UFUNCTION(BlueprintCallable, Category = "Player")
	bool RequestExitVehicle(const FTransform& FallbackTransform);

	UPROPERTY(BlueprintAssignable, Category = "Player")
	FJROnControlledPawnChanged OnControlledPawnChanged;

protected:
	virtual void OnPossess(APawn* InPawn) override;

	void ApplyMappingContextFor(const APawn* InPawn);

	UPROPERTY(EditDefaultsOnly, Category = "Input")
	TObjectPtr<UInputMappingContext> VehicleMappingContext;

	UPROPERTY(EditDefaultsOnly, Category = "Input")
	TObjectPtr<UInputMappingContext> OnFootMappingContext;

	/** Mapeamento sempre ativo (pausa, menu). */
	UPROPERTY(EditDefaultsOnly, Category = "Input")
	TObjectPtr<UInputMappingContext> GlobalMappingContext;

private:
	UPROPERTY()
	TObjectPtr<AJRCharacter> OnFootCharacter;

	UPROPERTY()
	TObjectPtr<AJRVehiclePawn> ParkedVehicle;

	bool bExitInProgress = false;
};

// Copyright utrazin. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "JRExtractionShip.generated.h"

class AJRArenaDirector;
class UPointLightComponent;
class USphereComponent;
class UStaticMeshComponent;

/**
 * [Remap F1] Nave de extração (REMAP 6.5): aparece a cada 3 ondas por ExtractionSeconds. Entrou no círculo, sai
 * da arena com tudo x multiplicador. Não entrou, vai embora e o multiplicador da próxima sobe.
 * Cinza no F1: pouso (disco) + feixe de luz alto para achar de longe. O modelo bom vem depois.
 */
UCLASS()
class JOGORESGATE_API AJRExtractionShip : public AActor
{
	GENERATED_BODY()

public:
	AJRExtractionShip();

	void Activate(AJRArenaDirector* InDirector, float Seconds, float InMultiplier);

	UFUNCTION(BlueprintPure, Category = "Extraction")
	float GetSecondsLeft() const;

	UFUNCTION(BlueprintPure, Category = "Extraction")
	float GetMultiplier() const { return Multiplier; }

protected:
	UFUNCTION()
	void HandleOverlap(UPrimitiveComponent* OverlappedComponent, AActor* OtherActor, UPrimitiveComponent* OtherComp,
		int32 OtherBodyIndex, bool bFromSweep, const FHitResult& SweepResult);

	void Leave();

	UPROPERTY(VisibleAnywhere, Category = "Extraction")
	TObjectPtr<USphereComponent> Trigger;

	UPROPERTY(VisibleAnywhere, Category = "Extraction")
	TObjectPtr<UStaticMeshComponent> Pad;

	UPROPERTY(VisibleAnywhere, Category = "Extraction")
	TObjectPtr<UStaticMeshComponent> Beam;

	UPROPERTY(VisibleAnywhere, Category = "Extraction")
	TObjectPtr<UPointLightComponent> Light;

private:
	TWeakObjectPtr<AJRArenaDirector> Director;
	FTimerHandle LeaveTimer;
	double ExpireTime = 0.0;
	float Multiplier = 1.f;
	bool bUsed = false;
};

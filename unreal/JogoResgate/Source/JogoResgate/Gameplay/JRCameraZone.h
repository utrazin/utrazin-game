// Copyright utrazin. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "JRCameraZone.generated.h"

class AJRCharacter;
class UBoxComponent;

/**
 * [A-070] Zona de câmera de interior (loja, casa, galpão...). Enquanto o herói está dentro da caixa, o braço da
 * câmera de terceira pessoa encurta para ArmLength: a câmera fica dentro do prédio, mostrando o personagem,
 * em vez de ir para cima do telhado. Ao sair, volta ao normal (suave, pelo CameraBlendSpeed do herói).
 * Colocada por tools/unreal/build_interiors_l01.py, uma por construção com interior.
 */
UCLASS()
class JOGORESGATE_API AJRCameraZone : public AActor
{
	GENERATED_BODY()

public:
	AJRCameraZone();

protected:
	virtual void BeginPlay() override;
	virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;

	UFUNCTION()
	void HandleBeginOverlap(UPrimitiveComponent* OverlappedComponent, AActor* OtherActor, UPrimitiveComponent* OtherComp,
		int32 OtherBodyIndex, bool bFromSweep, const FHitResult& SweepResult);

	UFUNCTION()
	void HandleEndOverlap(UPrimitiveComponent* OverlappedComponent, AActor* OtherActor, UPrimitiveComponent* OtherComp,
		int32 OtherBodyIndex);

	UPROPERTY(VisibleAnywhere, Category = "Camera")
	TObjectPtr<UBoxComponent> Box;

	/** Comprimento do braço da câmera dentro da zona (o normal é 300 cm). */
	UPROPERTY(EditAnywhere, Category = "Camera", meta = (Units = "cm", ClampMin = "80"))
	float ArmLength = 190.f;

private:
	TArray<TWeakObjectPtr<AJRCharacter>> HeroesInside;
};

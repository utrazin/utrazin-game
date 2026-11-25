// Copyright utrazin. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "Interactions/JRInteractable.h"
#include "JRInteriorPortal.generated.h"

class UBoxComponent;

/**
 * [A-097] Porta que leva para dentro de um prédio da cidade (e de volta). Os prédios da Villa são modelos fechados
 * (Tripo), então o cômodo fica embaixo do prédio, fora da vista, e a porta "transporta": E escurece a tela, o herói
 * aparece do outro lado (TargetId) de frente para o cômodo e a tela clareia. Usado no Armeiro (Krug), na Bancada
 * (Ix-Vel), na Casa do herói, na Casa saqueada e no Bar.
 * Eixos: X do ator aponta para onde a pessoa chega (para dentro do cômodo, ou para a rua na porta de fora).
 * Colocada por tools/unreal/build_interiors_vila.py.
 */
UCLASS()
class JOGORESGATE_API AJRInteriorPortal : public AActor, public IJRInteractable
{
	GENERATED_BODY()

public:
	AJRInteriorPortal();

	virtual bool CanInteract_Implementation(AActor* InstigatorActor) const override;
	virtual void Interact_Implementation(AActor* InstigatorActor) override;
	virtual FText GetInteractionText_Implementation() const override;

	/** Onde quem chega por esta porta aparece (na frente dela, olhando para +X). */
	FTransform GetArrivalTransform(float CapsuleHalfHeight) const;

	FName GetPortalId() const { return PortalId; }

protected:
	AJRInteriorPortal* FindTarget() const;
	void FinishTravel();

	UPROPERTY(VisibleAnywhere, Category = "Portal")
	TObjectPtr<USceneComponent> Root;

	/** Área de interação (o E pega pela proximidade). */
	UPROPERTY(VisibleAnywhere, Category = "Portal")
	TObjectPtr<UBoxComponent> Box;

	UPROPERTY(EditAnywhere, Category = "Portal")
	FName PortalId;

	/** PortalId da outra ponta. */
	UPROPERTY(EditAnywhere, Category = "Portal")
	FName TargetId;

	/** Texto do E (vazio = "Entrar"). */
	UPROPERTY(EditAnywhere, Category = "Portal")
	FText Prompt;

	UPROPERTY(EditAnywhere, Category = "Portal", meta = (Units = "cm"))
	float ArrivalDistance = 150.f;

	UPROPERTY(EditAnywhere, Category = "Portal", meta = (Units = "s", ClampMin = "0.05"))
	float FadeSeconds = 0.3f;

private:
	TWeakObjectPtr<APawn> Traveler;
	TWeakObjectPtr<AJRInteriorPortal> Destination;
	FTimerHandle TravelTimer;
	bool bBusy = false;
};

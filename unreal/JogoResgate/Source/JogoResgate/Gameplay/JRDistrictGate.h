// Copyright utrazin. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "Interactions/JRInteractable.h"
#include "JRDistrictGate.generated.h"

class UBoxComponent;
class UPointLightComponent;
class UTextRenderComponent;

/**
 * [A-098] Posto de controle de um bairro da Villa Star. O bairro fica fechado por barricadas de verdade (contêineres
 * e barricadas com colisão, nada de parede invisível) até a arena do nível RequiredArenaLevel ser liberada (recorde de
 * ondas, FJRRemapRules::UnlockedArenaLevel). As barricadas são atores do mapa com a tag BarrierTag (postos pelo
 * dress_city_v6.py, mobilidade Movable). Na primeira vez que o herói chega perto depois de liberar, elas afundam
 * com tremor e aparece a faixa "Bairro liberado"; depois disso já começam escondidas.
 * E no posto fechado diz o que falta. Uma placa (texto 3D) mostra o nome do bairro e o nível.
 */
UCLASS()
class JOGORESGATE_API AJRDistrictGate : public AActor, public IJRInteractable
{
	GENERATED_BODY()

public:
	AJRDistrictGate();

	virtual bool CanInteract_Implementation(AActor* InstigatorActor) const override;
	virtual void Interact_Implementation(AActor* InstigatorActor) override;
	virtual FText GetInteractionText_Implementation() const override;
	virtual void OnConstruction(const FTransform& Transform) override;

	UFUNCTION(BlueprintPure, Category = "District")
	bool IsUnlocked() const;

	/** Console/teste: abre já (com a animação). */
	void ForceOpen();

	FName GetDistrictId() const { return DistrictId; }
	int32 GetRequiredArenaLevel() const { return RequiredArenaLevel; }
	const FString& GetDistrictName() const { return DistrictName; }

protected:
	virtual void BeginPlay() override;
	void Poll();
	void StartCollapse();
	void TickCollapse();
	void SetPiecesHidden();
	void RefreshLook();

	UPROPERTY(VisibleAnywhere, Category = "District")
	TObjectPtr<USceneComponent> Root;

	UPROPERTY(VisibleAnywhere, Category = "District")
	TObjectPtr<UBoxComponent> Box;

	UPROPERTY(VisibleAnywhere, Category = "District")
	TObjectPtr<UTextRenderComponent> Sign;

	UPROPERTY(VisibleAnywhere, Category = "District")
	TObjectPtr<UPointLightComponent> Lamp;

	UPROPERTY(EditAnywhere, Category = "District")
	FName DistrictId;

	UPROPERTY(EditAnywhere, Category = "District")
	FString DistrictName = TEXT("Bairro");

	UPROPERTY(EditAnywhere, Category = "District", meta = (ClampMin = "1", ClampMax = "5"))
	int32 RequiredArenaLevel = 2;

	/** Tag das barricadas deste bairro (None = usa DistrictId). */
	UPROPERTY(EditAnywhere, Category = "District")
	FName BarrierTag;

	/** Distância em que a abertura acontece (para o herói ver as barricadas caírem). */
	UPROPERTY(EditAnywhere, Category = "District", meta = (Units = "cm"))
	float RevealDistance = 3500.f;

	UPROPERTY(EditAnywhere, Category = "District", meta = (Units = "s"))
	float CollapseSeconds = 1.6f;

private:
	struct FPiece
	{
		TWeakObjectPtr<AActor> Actor;
		FVector Start;
		FRotator StartRot;
		float Delay = 0.f;
		float Tilt = 0.f;
	};
	TArray<FPiece> Pieces;
	FTimerHandle PollTimer;
	FTimerHandle CollapseTimer;
	double CollapseStart = 0.0;
	bool bOpened = false;
};

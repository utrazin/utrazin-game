// Copyright utrazin. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "Characters/JRCharacter.h"
#include "Interactions/JRInteractable.h"
#include "JRLootChest.generated.h"

class UPointLightComponent;
class UStaticMeshComponent;

/**
 * Baú que o herói abre com E (animação de abrir), entregando arma, munição e/ou vida.
 * Ex.: o baú da casa da Vila 1 tem a pistola (storyboard L01, passo 9).
 */
UCLASS()
class JOGORESGATE_API AJRLootChest : public AActor, public IJRInteractable
{
	GENERATED_BODY()

public:
	AJRLootChest();

	virtual bool CanInteract_Implementation(AActor* InstigatorActor) const override;
	virtual void Interact_Implementation(AActor* InstigatorActor) override;
	virtual FText GetInteractionText_Implementation() const override;

	/** [A-064] Já foi aberto (a tarefa "abra o baú" do HUD termina). */
	bool IsOpened() const { return bOpened; }

	/** [A-067] O que tem dentro (ícone do marcador do HUD: chave, galão, explosivo, arma). */
	FName GetKeyItemInside() const { return KeyItemInside; }
	EJRWeaponSlot GetWeaponInside() const { return WeaponInside; }

protected:
	void OpenAndGive();

	UPROPERTY(VisibleAnywhere, Category = "Chest")
	TObjectPtr<UStaticMeshComponent> Base;

	UPROPERTY(VisibleAnywhere, Category = "Chest")
	TObjectPtr<USceneComponent> LidPivot;

	UPROPERTY(VisibleAnywhere, Category = "Chest")
	TObjectPtr<UStaticMeshComponent> Lid;

	UPROPERTY(VisibleAnywhere, Category = "Chest")
	TObjectPtr<UPointLightComponent> Glow;

	/** Arma dentro do baú (None = só munição/vida). */
	UPROPERTY(EditAnywhere, Category = "Chest")
	EJRWeaponSlot WeaponInside = EJRWeaponSlot::Pistol;

	UPROPERTY(EditAnywhere, Category = "Chest")
	int32 AmmoInside = 24;

	UPROPERTY(EditAnywhere, Category = "Chest")
	float HealthInside = 0.f;

	/** Bandagens dentro (vão para a bolsa do herói, até o limite; A-055). */
	UPROPERTY(EditAnywhere, Category = "Chest", meta = (ClampMin = "0"))
	int32 BandagesInside = 0;

	/** Kits médicos dentro (vão para a bolsa do herói, até o limite; A-055). */
	UPROPERTY(EditAnywhere, Category = "Chest", meta = (ClampMin = "0"))
	int32 MedkitsInside = 0;

	/** Velocidade da animação de abrir (o arquivo é longo). */
	UPROPERTY(EditAnywhere, Category = "Chest")
	float OpenPlayRate = 1.8f;

	UPROPERTY(EditAnywhere, Category = "Chest", meta = (Units = "s"))
	float OpenDuration = 2.4f;

	/** Item-chave dentro (CarKey, Fuel, Explosive...). None = nenhum. Vai para o AJRPlayerController. */
	UPROPERTY(EditAnywhere, Category = "Chest|Key Item")
	FName KeyItemInside;

	/** Nome mostrado ("CHAVE DO BUGGY"). */
	UPROPERTY(EditAnywhere, Category = "Chest|Key Item")
	FString KeyItemLabel;

	/** Abrir faz barulho e chama uma horda do diretor de IA (ex.: a bomba de gasolina). */
	UPROPERTY(EditAnywhere, Category = "Chest|Horde")
	bool bTriggerHordeOnOpen = false;

	UPROPERTY(EditAnywhere, Category = "Chest|Horde", meta = (EditCondition = "bTriggerHordeOnOpen"))
	int32 HordeSize = 20;

	UPROPERTY(EditAnywhere, Category = "Chest|Horde", meta = (EditCondition = "bTriggerHordeOnOpen", Units = "s"))
	float HordeDuration = 45.f;

private:
	TWeakObjectPtr<AJRCharacter> Opener;
	FTimerHandle OpenTimer;
	bool bOpened = false;
};

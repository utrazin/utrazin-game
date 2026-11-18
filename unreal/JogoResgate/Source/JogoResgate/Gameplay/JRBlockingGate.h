// Copyright utrazin. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "Interactions/JRInteractable.h"
#include "JRBlockingGate.generated.h"

class UBoxComponent;
class UNiagaraSystem;
class UPointLightComponent;
class USoundBase;
class UStaticMeshComponent;
class AJRBlockingGate;

DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FJROnGateOpened, AJRBlockingGate*, Gate);

/**
 * Portão que bloqueia a rota (ex.: árvore caída sobre a ponte, L01 v3 zona 4).
 * O herói aperta E com o item exigido (ex.: "Explosive" do baú da colmeia): o pavio queima FuseTime,
 * explode (dano em área), o bloqueio some e o diretor de IA manda uma horda (fuga de carro, zona 5).
 * Sem item exigido (RequiredItem = None) abre direto com E. Sem Tick.
 */
UCLASS()
class JOGORESGATE_API AJRBlockingGate : public AActor, public IJRInteractable
{
	GENERATED_BODY()

public:
	AJRBlockingGate();

	virtual bool CanInteract_Implementation(AActor* InstigatorActor) const override;
	virtual void Interact_Implementation(AActor* InstigatorActor) override;
	virtual FText GetInteractionText_Implementation() const override;

	/** Abre na hora (sem pavio). */
	UFUNCTION(BlueprintCallable, Category = "Gate")
	void OpenGate();

	UFUNCTION(BlueprintPure, Category = "Gate")
	bool IsOpen() const { return bOpen; }

	UPROPERTY(BlueprintAssignable, Category = "Gate")
	FJROnGateOpened OnGateOpened;

protected:
	/** Gancho Blueprint para som/VFX de verdade. */
	UFUNCTION(BlueprintImplementableEvent, Category = "Gate")
	void BP_OnGateOpened();

	void Detonate();
	void EndFlash();

	UPROPERTY(VisibleAnywhere, Category = "Gate")
	TObjectPtr<USceneComponent> Root;

	/** Visual do bloqueio (ex.: tronco DeadTree_5 deitado). A malha é posta pelo build_l01.py. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Gate")
	TObjectPtr<UStaticMeshComponent> BlockerMesh;

	/** Caixa invisível que segura o carro e o herói (a malha pode ter vãos). */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Gate")
	TObjectPtr<UBoxComponent> BlockVolume;

	UPROPERTY(VisibleAnywhere, Category = "Gate")
	TObjectPtr<UPointLightComponent> FlashLight;

	/** Item exigido (None = abre direto). */
	UPROPERTY(EditAnywhere, Category = "Gate")
	FName RequiredItem = TEXT("Explosive");

	/** Nome do item na mensagem ("explosivos"). */
	UPROPERTY(EditAnywhere, Category = "Gate")
	FString RequiredItemLabel = TEXT("explosivos");

	UPROPERTY(EditAnywhere, Category = "Gate")
	FString HintWithoutItem = TEXT("Precisa de explosivos. Procure na colmeia, além do lago.");

	UPROPERTY(EditAnywhere, Category = "Gate", meta = (Units = "s"))
	float FuseTime = 4.f;

	UPROPERTY(EditAnywhere, Category = "Gate|Explosion", meta = (Units = "cm"))
	float ExplosionRadius = 900.f;

	UPROPERTY(EditAnywhere, Category = "Gate|Explosion")
	float ExplosionDamage = 150.f;

	UPROPERTY(EditAnywhere, Category = "Gate|Explosion")
	TObjectPtr<UNiagaraSystem> ExplosionSystem;

	UPROPERTY(EditAnywhere, Category = "Gate|Explosion")
	TObjectPtr<USoundBase> ExplosionSound;

	/** A explosão chama uma horda do AJRAIDirector (perto do portão). */
	UPROPERTY(EditAnywhere, Category = "Gate|Horde")
	bool bTriggerHorde = true;

	UPROPERTY(EditAnywhere, Category = "Gate|Horde", meta = (EditCondition = "bTriggerHorde"))
	int32 HordeSize = 30;

	UPROPERTY(EditAnywhere, Category = "Gate|Horde", meta = (EditCondition = "bTriggerHorde", Units = "s"))
	float HordeDuration = 60.f;

private:
	FTimerHandle FuseTimer;
	FTimerHandle FlashTimer;
	bool bArmed = false;
	bool bOpen = false;
};

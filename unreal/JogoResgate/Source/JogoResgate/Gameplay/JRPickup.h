// Copyright utrazin. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "Interactions/JRInteractable.h"
#include "JRPickup.generated.h"

class UPointLightComponent;
class URotatingMovementComponent;
class USphereComponent;
class UStaticMesh;
class UStaticMeshComponent;

/** Tipos de item coletável. */
UENUM(BlueprintType)
enum class EJRPickupType : uint8
{
	Ammo,     // munição de reserva (a pé)
	Health,   // cura o personagem
	Nitro,    // carga de nitro (no carro)
	Fury,     // poder temporário: tiro mais forte e rápido
	Repair,   // conserta o carro
	WeaponMelee,   // graveto alien (pegar com E)
	WeaponPistol,  // pistola (pegar com E)
	WeaponShotgun, // escopeta alien (pegar com E)
	Bandage,       // vai para a bolsa (A-055); Amount = quantidade
	Medkit,        // vai para a bolsa (A-055); Amount = quantidade
	WeaponSniper   // [A-058] rifle de precisão alien (pegar com E); no fim para não mudar valores salvos
};

/**
 * Item no mapa ou dropado por zumbi. Visual simples (formas básicas da engine coloridas) ou malha do usuário.
 * [A-063] Fica parado e apoiado no chão ou em cima de algo (mesa, caixa): no BeginPlay desce até a primeira
 * superfície sólida embaixo dele. Coleta por sobreposição. Sem Tick.
 */
UCLASS()
class JOGORESGATE_API AJRPickup : public AActor, public IJRInteractable
{
	GENERATED_BODY()

public:
	AJRPickup();

	/** Define tipo e quantidade (use antes de FinishSpawning ou logo após o spawn). */
	UFUNCTION(BlueprintCallable, Category = "Pickup")
	void Setup(EJRPickupType InType, float InAmount);

	/** Spawna um item no chão (usado no drop dos zumbis). */
	static AJRPickup* SpawnPickup(UWorld* World, EJRPickupType InType, float InAmount, const FVector& Location, float LifeSeconds = 0.f);

	UFUNCTION(BlueprintPure, Category = "Pickup")
	EJRPickupType GetPickupType() const { return Type; }

	/** [A-064] Já foi pego (a tarefa "pegue o item" do HUD termina). */
	bool IsTaken() const { return bTaken; }

	void SetDisplayMesh(UStaticMesh* InMesh, float InScale)
	{
		DisplayMesh = InMesh;
		DisplayScale = InScale;
		ApplyVisual();
	}

	/** Armas não são coletadas encostando: o jogador aperta E e pega do chão (animação). */
	bool IsWeapon() const
	{
		return (Type >= EJRPickupType::WeaponMelee && Type <= EJRPickupType::WeaponShotgun) || Type == EJRPickupType::WeaponSniper;
	}

	virtual bool CanInteract_Implementation(AActor* InstigatorActor) const override;
	virtual void Interact_Implementation(AActor* InstigatorActor) override;
	virtual FText GetInteractionText_Implementation() const override;

protected:
	virtual void BeginPlay() override;
	virtual void OnConstruction(const FTransform& Transform) override;

	UFUNCTION()
	void HandleOverlap(UPrimitiveComponent* OverlappedComponent, AActor* OtherActor, UPrimitiveComponent* OtherComp,
		int32 OtherBodyIndex, bool bFromSweep, const FHitResult& SweepResult);

	bool TryApply(AActor* Collector);
	void ApplyVisual();
	/** [A-063] Desce o item até a superfície embaixo dele (terreno, mesa, caixa). */
	void SnapToGround();

	UPROPERTY(VisibleAnywhere, Category = "Pickup")
	TObjectPtr<USphereComponent> Trigger;

	UPROPERTY(VisibleAnywhere, Category = "Pickup")
	TObjectPtr<UStaticMeshComponent> Mesh;

	UPROPERTY(VisibleAnywhere, Category = "Pickup")
	TObjectPtr<UPointLightComponent> Glow;

	UPROPERTY(VisibleAnywhere, Category = "Pickup")
	TObjectPtr<URotatingMovementComponent> Rotator;

	UPROPERTY(EditAnywhere, Category = "Pickup")
	EJRPickupType Type = EJRPickupType::Ammo;

	/**
	 * Ammo: balas; Health: vida; Nitro: carga 0..1; Fury: segundos; Repair: 0..1 do carro;
	 * Bandage/Medkit: quantidade (o drop dos zumbis usa 1).
	 */
	UPROPERTY(EditAnywhere, Category = "Pickup")
	float Amount = 12.f;

	/**
	 * Malha mostrada no item (arma deitada; outros itens girando, ex.: kit médico e munição do usuário). Vazio = forma básica.
	 * Medkit vazio usa sozinho /Game/Environment/User/Itens/SM_ITM_KitMedico, se existir.
	 */
	UPROPERTY(EditAnywhere, Category = "Pickup")
	TObjectPtr<UStaticMesh> DisplayMesh;

	UPROPERTY(EditAnywhere, Category = "Pickup")
	float DisplayScale = 1.f;

	/** [A-063] Apoiar no chão ao começar o jogo (desligue só para item pendurado de propósito). */
	UPROPERTY(EditAnywhere, Category = "Pickup")
	bool bSnapToGround = true;

	/** [A-063] Até quantos cm abaixo do ator o item procura o chão. */
	UPROPERTY(EditAnywhere, Category = "Pickup", meta = (Units = "cm", ClampMin = "0"))
	float SnapMaxDrop = 400.f;

	bool bTaken = false;
};

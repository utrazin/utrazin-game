// Copyright utrazin. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "Interactions/JRInteractable.h"
#include "JRPickup.generated.h"

class AJRCharacter;
class APawn;
class UMaterialInstanceDynamic;
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

/** [A-082] Fase da animação do item (interna, sem reflexão). */
enum class EJRPickupPhase : uint8
{
	Idle,   // no chão: flutua, gira, pulsa
	Toss,   // saindo do zumbi num arco com quique
	Magnet, // sendo puxado para o herói
	Pop     // pego: cresce, encolhe e some
};

/**
 * Item no mapa ou dropado por zumbi.
 * [A-082] Visual 3D de verdade por tipo (malhas SM_Pickup_* do tools/unreal/setup_pickups_3d.py; sem elas cai nas
 * formas antigas), flutuando baixo, girando devagar, com núcleo e anel de chão pulsando. Munição e cura são pegas
 * só de passar perto: um ímã curto puxa o item para o herói, ele dá um "pop" (cresce, encolhe, clarão) e some.
 * Item que não cabe (bolsa cheia) não é puxado: só dá um pulinho e avisa. Drop de zumbi sai num arco com quique.
 * Armas continuam no chão deitadas e são pegas com E (animação).
 * [A-063] Fica apoiado no chão ou em cima de algo (mesa, caixa): no BeginPlay desce até a primeira superfície sólida.
 * Tick justificado: animação contínua (flutuar, girar, pulsar, arco, ímã); fora da tela e longe do herói só confere a
 * distância (a parte visual é pulada).
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

	/** Spawna um item no chão (usado no drop dos zumbis). [A-082] Sai num arco curto e quica até o chão. */
	static AJRPickup* SpawnPickup(UWorld* World, EJRPickupType InType, float InAmount, const FVector& Location, float LifeSeconds = 0.f);

	UFUNCTION(BlueprintPure, Category = "Pickup")
	EJRPickupType GetPickupType() const { return Type; }

	/** [A-086] Nome curto para a etiqueta no chão ("Munição +12", "Bandagem x2"...). */
	FString GetLabelText() const;
	FLinearColor GetLabelColor() const { return GlowColor; }
	/** [A-087] Ícone pintado do item na HUD (T_HUD2_V3_Item_*); vazio = sem ícone. */
	FString GetLabelIcon() const
	{
		switch (Type)
		{
		case EJRPickupType::Ammo: return TEXT("V3_Item_AmmoPistol");
		case EJRPickupType::Health: return TEXT("V3_Item_Health");
		case EJRPickupType::Fury: return TEXT("V3_Item_Fury");
		case EJRPickupType::Bandage: return TEXT("V3_Item_Bandage");
		case EJRPickupType::Medkit: return TEXT("V3_Item_Medkit");
		default: return FString();
		}
	}

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

	/** [A-082] O herói pode levar este item agora? (munição sempre; cura e bolsa só se couber). Armas: não (é com E). */
	bool CanBeCollectedBy(const AJRCharacter* Hero) const;

	/** [A-082] Lança o item num arco curto a partir de From até o chão perto (drop do zumbi). */
	void StartDropToss(const FVector& From);

	virtual bool CanInteract_Implementation(AActor* InstigatorActor) const override;
	virtual void Interact_Implementation(AActor* InstigatorActor) override;
	virtual FText GetInteractionText_Implementation() const override;

	virtual void Tick(float DeltaSeconds) override;

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
	/** [A-063/A-082] Primeira superfície que segura o personagem abaixo de From (até MaxDrop cm). */
	bool FindGroundBelow(const FVector& From, float MaxDrop, FVector& OutPoint) const;

	UPROPERTY(VisibleAnywhere, Category = "Pickup")
	TObjectPtr<USphereComponent> Trigger;

	UPROPERTY(VisibleAnywhere, Category = "Pickup")
	TObjectPtr<UStaticMeshComponent> Mesh;

	UPROPERTY(VisibleAnywhere, Category = "Pickup")
	TObjectPtr<UPointLightComponent> Glow;

	/** Sem uso desde A-082 (o giro é feito no Tick); fica para não quebrar Blueprints e instâncias salvas. */
	UPROPERTY(VisibleAnywhere, Category = "Pickup")
	TObjectPtr<URotatingMovementComponent> Rotator;

	/** [A-082] Anel de brilho no chão, embaixo do item (SM_Pickup_Ring, aditivo). */
	UPROPERTY(VisibleAnywhere, Category = "Pickup")
	TObjectPtr<UStaticMeshComponent> Ring;

	/** [A-086] Feixe de luz vertical na cor do item (dá para ver de longe o que caiu e onde). */
	UPROPERTY(VisibleAnywhere, Category = "Pickup")
	TObjectPtr<UStaticMeshComponent> Beam;

	UPROPERTY(EditAnywhere, Category = "Pickup|Visual 3D")
	TSoftObjectPtr<UMaterialInterface> BeamMaterial;

	UPROPERTY(EditAnywhere, Category = "Pickup|Visual 3D", meta = (Units = "cm"))
	float BeamHeight = 260.f;

	/** Os itens 3D tinham ~15 cm e sumiam no chão: aumento só no visual (não muda o raio de pegar). */
	UPROPERTY(EditAnywhere, Category = "Pickup|Visual 3D", meta = (ClampMin = "0.5"))
	float VisualScaleBoost = 1.8f;

	UPROPERTY(EditAnywhere, Category = "Pickup")
	EJRPickupType Type = EJRPickupType::Ammo;

	/**
	 * Ammo: balas; Health: vida; Nitro: carga 0..1; Fury: segundos; Repair: 0..1 do carro;
	 * Bandage/Medkit: quantidade (o drop dos zumbis usa 1).
	 */
	UPROPERTY(EditAnywhere, Category = "Pickup")
	float Amount = 12.f;

	/**
	 * Malha mostrada no item no lugar da padrão (arma deitada; outros itens com o material da própria malha).
	 * Vazio = malha 3D padrão do tipo (A-082) ou, sem ela, a forma básica antiga.
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

	// ---------------------------------------------------------------- [A-082] malhas 3D por tipo
	/** Munição quando o herói está de pistola (ou sem arma de fogo): 3 células violeta num pente. */
	UPROPERTY(EditAnywhere, Category = "Pickup|Visual 3D")
	TSoftObjectPtr<UStaticMesh> MeshAmmoPistol;

	/** Munição quando o herói está de escopeta: 3 cartuchos laranja. */
	UPROPERTY(EditAnywhere, Category = "Pickup|Visual 3D")
	TSoftObjectPtr<UStaticMesh> MeshAmmoShotgun;

	/** Munição quando o herói está de rifle: célula longa ciano. */
	UPROPERTY(EditAnywhere, Category = "Pickup|Visual 3D")
	TSoftObjectPtr<UStaticMesh> MeshAmmoSniper;

	UPROPERTY(EditAnywhere, Category = "Pickup|Visual 3D")
	TSoftObjectPtr<UStaticMesh> MeshHealth;

	UPROPERTY(EditAnywhere, Category = "Pickup|Visual 3D")
	TSoftObjectPtr<UStaticMesh> MeshBandage;

	UPROPERTY(EditAnywhere, Category = "Pickup|Visual 3D")
	TSoftObjectPtr<UStaticMesh> MeshMedkit;

	UPROPERTY(EditAnywhere, Category = "Pickup|Visual 3D")
	TSoftObjectPtr<UStaticMesh> MeshFury;

	UPROPERTY(EditAnywhere, Category = "Pickup|Visual 3D")
	TSoftObjectPtr<UStaticMesh> MeshNitro;

	UPROPERTY(EditAnywhere, Category = "Pickup|Visual 3D")
	TSoftObjectPtr<UStaticMesh> MeshRepair;

	/** Armas no chão sem DisplayMesh: malha da própria arma (antes virava um cone). */
	UPROPERTY(EditAnywhere, Category = "Pickup|Visual 3D")
	TSoftObjectPtr<UStaticMesh> MeshWeaponMelee;

	UPROPERTY(EditAnywhere, Category = "Pickup|Visual 3D")
	TSoftObjectPtr<UStaticMesh> MeshWeaponPistol;

	UPROPERTY(EditAnywhere, Category = "Pickup|Visual 3D")
	TSoftObjectPtr<UStaticMesh> MeshWeaponShotgun;

	UPROPERTY(EditAnywhere, Category = "Pickup|Visual 3D")
	TSoftObjectPtr<UStaticMesh> MeshWeaponSniper;

	/** Anel de brilho do chão (quad de 1 m com o material M_Pickup_Ring). Vazio ou ausente = sem anel. */
	UPROPERTY(EditAnywhere, Category = "Pickup|Visual 3D")
	TSoftObjectPtr<UStaticMesh> RingMesh;

	// ---------------------------------------------------------------- [A-082] sensação (game feel)
	/** Altura em que o item flutua acima do chão (armas ficam deitadas, sem flutuar). */
	UPROPERTY(EditAnywhere, Category = "Pickup|Feel", meta = (Units = "cm", ClampMin = "0"))
	float HoverHeight = 10.f;

	/** Sobe e desce (amplitude) em volta da altura de flutuar. */
	UPROPERTY(EditAnywhere, Category = "Pickup|Feel", meta = (Units = "cm", ClampMin = "0"))
	float BobAmplitude = 3.f;

	UPROPERTY(EditAnywhere, Category = "Pickup|Feel", meta = (ClampMin = "0"))
	float BobFrequency = 0.6f;

	/** Giro lento no próprio eixo (graus por segundo). */
	UPROPERTY(EditAnywhere, Category = "Pickup|Feel", meta = (ClampMin = "0"))
	float SpinDegreesPerSecond = 70.f;

	/** Brilho do núcleo (parâmetro Intensity do material M_Pickup_Core). O pulso varia em volta deste valor. */
	UPROPERTY(EditAnywhere, Category = "Pickup|Feel", meta = (ClampMin = "0"))
	float CoreGlowIntensity = 6.f;

	/** Brilho do anel do chão (parâmetro Intensity do M_Pickup_Ring). */
	UPROPERTY(EditAnywhere, Category = "Pickup|Feel", meta = (ClampMin = "0"))
	float RingGlowIntensity = 1.5f;

	/** Luz pontual fraca do item, em candelas (A-063: valores altos estouram o item de branco). */
	UPROPERTY(EditAnywhere, Category = "Pickup|Feel", meta = (ClampMin = "0"))
	float GlowCandelas = 6.f;

	/** Ritmo do pulso de brilho (vezes por segundo). */
	UPROPERTY(EditAnywhere, Category = "Pickup|Feel", meta = (ClampMin = "0"))
	float PulseFrequency = 1.1f;

	/** Distância (no plano) em que o ímã começa a puxar o item para o herói. */
	UPROPERTY(EditAnywhere, Category = "Pickup|Feel", meta = (Units = "cm", ClampMin = "0"))
	float MagnetRadius = 150.f;

	/** Velocidade máxima do ímã (cm/s); começa devagar e acelera. */
	UPROPERTY(EditAnywhere, Category = "Pickup|Feel", meta = (ClampMin = "0"))
	float MagnetMaxSpeed = 1800.f;

	/** Últimos segundos de vida (drop com tempo) em que o item pisca avisando que vai sumir. */
	UPROPERTY(EditAnywhere, Category = "Pickup|Feel", meta = (Units = "s", ClampMin = "0"))
	float BlinkBeforeExpire = 3.f;

	bool bTaken = false;

private:
	/** Malha 3D padrão do tipo (TSoftObjectPtr carregado sem aviso). Nulo = ainda não importada. */
	UStaticMesh* ResolveDefaultMesh(FLinearColor& OutCoreColor, float& OutScale) const;
	void UpdateVisual(float Dt);
	void TickToss(float Dt);
	void TickMagnet(float Dt);
	void TickPop(float Dt);
	void TryStartMagnet(float Now);
	void StartMagnet(APawn* Hero);
	void CancelMagnet(float Now);
	void Collect(AActor* Collector, APawn* FollowPawn);
	void NotifyBlocked(float Now);
	void Kick(float Strength);
	FVector MagnetTargetFor(const APawn* Hero) const;

	EJRPickupPhase Phase = EJRPickupPhase::Idle;

	UPROPERTY(Transient)
	TObjectPtr<UMaterialInstanceDynamic> CoreMID;

	UPROPERTY(Transient)
	TObjectPtr<UMaterialInstanceDynamic> RingMID;

	/** [A-090] feixe pisca de leve junto com o brilho */
	UPROPERTY(Transient)
	TObjectPtr<UMaterialInstanceDynamic> BeamMID;
	float BeamBaseIntensity = 0.75f;

	TWeakObjectPtr<APawn> MagnetPawn;

	/** Pose base da malha (calculada no ApplyVisual); o Tick soma flutuar, giro e escala. */
	FVector VisualBaseLocation = FVector::ZeroVector;
	FRotator VisualBaseRotation = FRotator::ZeroRotator;
	FVector VisualBaseScale = FVector::OneVector;
	FVector RingBaseScale = FVector::OneVector;
	FLinearColor GlowColor = FLinearColor::White;
	bool bBeamReady = false; // [A-086] material do feixe carregou (sem ele o cilindro ficaria branco)
	FLinearColor CoreColor = FLinearColor::White;
	/** Item que flutua e gira (falso para armas deitadas). */
	bool bFloats = true;

	float AnimTime = 0.f;
	float PhaseSeed = 0.f;
	float SpinYaw = 0.f;
	float SpinBoost = 0.f;
	float KickTime = 10.f;
	float KickStrength = 0.f;

	FVector TossFrom = FVector::ZeroVector;
	FVector TossTo = FVector::ZeroVector;
	float TossTime = 0.f;
	float TossDuration = 0.4f;
	float TossHeight = 50.f;
	int32 TossBounces = 0;

	FVector MagnetVelocity = FVector::ZeroVector;
	float MagnetSpeed = 0.f;
	float MagnetTime = 0.f;
	float NextMagnetTime = 0.f;
	float NextBlockedToastTime = 0.f;

	float PopTime = 0.f;
	TWeakObjectPtr<APawn> PopFollow;
};

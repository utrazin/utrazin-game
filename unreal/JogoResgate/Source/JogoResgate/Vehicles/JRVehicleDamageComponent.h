// Copyright utrazin. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "Vehicles/JRVehicleDamageModel.h"
#include "JRVehicleDamageComponent.generated.h"

class UChaosWheeledVehicleMovementComponent;

DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FJROnVehicleIntegrityChanged, float, Integrity);
DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FJROnTireFlat, EJRWheel, Wheel);
DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FJROnEngineSmoke, bool, bSmoking);
DECLARE_DYNAMIC_MULTICAST_DELEGATE(FJROnVehicleDisabled);

/**
 * Liga FJRVehicleDamageState (lógica pura) ao Chaos Vehicles (ADR-003):
 * impactos e tiros -> dano por zona; pneu furado -> atrito/raio da roda; motor -> torque.
 * Orientado a eventos (OnActorHit, OnTakePointDamage); sem Tick.
 */
UCLASS(ClassGroup = (JogoResgate), meta = (BlueprintSpawnableComponent))
class JOGORESGATE_API UJRVehicleDamageComponent : public UActorComponent
{
	GENERATED_BODY()

public:
	UJRVehicleDamageComponent();

	UFUNCTION(BlueprintCallable, Category = "Vehicle|Damage")
	void ApplyZoneDamage(EJRVehicleZone Zone, float Amount);

	UFUNCTION(BlueprintCallable, Category = "Vehicle|Damage")
	void SetTireFlat(EJRWheel Wheel, bool bFlat);

	UFUNCTION(BlueprintCallable, Category = "Vehicle|Damage")
	void RepairAll();

	UFUNCTION(BlueprintPure, Category = "Vehicle|Damage")
	float GetIntegrity() const { return State.GetIntegrity(); }

	UFUNCTION(BlueprintPure, Category = "Vehicle|Damage")
	float GetZoneHealth(EJRVehicleZone Zone) const { return State.GetZoneHealth(Zone); }

	UFUNCTION(BlueprintPure, Category = "Vehicle|Damage")
	bool IsTireFlat(EJRWheel Wheel) const { return State.IsTireFlat(Wheel); }

	UFUNCTION(BlueprintPure, Category = "Vehicle|Damage")
	bool IsDisabled() const { return State.IsDisabled(); }

	/** Viés de direção dos pneus furados, somado ao input de direção pelo pawn. */
	UFUNCTION(BlueprintPure, Category = "Vehicle|Damage")
	float GetSteeringBias() const { return State.GetSteeringBias(); }

	UPROPERTY(BlueprintAssignable, Category = "Vehicle|Damage")
	FJROnVehicleIntegrityChanged OnIntegrityChanged;

	UPROPERTY(BlueprintAssignable, Category = "Vehicle|Damage")
	FJROnTireFlat OnTireFlat;

	UPROPERTY(BlueprintAssignable, Category = "Vehicle|Damage")
	FJROnEngineSmoke OnEngineSmoke;

	UPROPERTY(BlueprintAssignable, Category = "Vehicle|Damage")
	FJROnVehicleDisabled OnVehicleDisabled;

protected:
	virtual void BeginPlay() override;

	UFUNCTION()
	void HandleActorHit(AActor* SelfActor, AActor* OtherActor, FVector NormalImpulse, const FHitResult& Hit);

	UFUNCTION()
	void HandlePointDamage(AActor* DamagedActor, float Damage, AController* InstigatedBy, FVector HitLocation,
		UPrimitiveComponent* HitComponent, FName BoneName, FVector ShotFromDirection, const UDamageType* DamageType,
		AActor* DamageCauser);

	void ApplyEffectsToMovement();
	int32 FindNearestWheel(const FVector& WorldLocation, float& OutDistance) const;
	UChaosWheeledVehicleMovementComponent* GetMovement() const;

	/** Meia extensão do chassi (cm) para mapear impactos em zonas. */
	UPROPERTY(EditDefaultsOnly, Category = "Vehicle|Damage")
	float HalfLength = 230.f;

	UPROPERTY(EditDefaultsOnly, Category = "Vehicle|Damage")
	float HalfWidth = 95.f;

	/** Fração do dano frontal repassada ao motor. */
	UPROPERTY(EditDefaultsOnly, Category = "Vehicle|Damage", meta = (ClampMin = "0", ClampMax = "1"))
	float FrontToEngineDamageRatio = 0.5f;

	UPROPERTY(EditDefaultsOnly, Category = "Vehicle|Damage", meta = (Units = "s"))
	float MinTimeBetweenImpacts = 0.25f;

	/** Impacto lateral nesta velocidade (km/h) perto de uma roda pode furar o pneu. */
	UPROPERTY(EditDefaultsOnly, Category = "Vehicle|Damage")
	float TireBurstImpactKmh = 55.f;

	UPROPERTY(EditDefaultsOnly, Category = "Vehicle|Damage", meta = (Units = "cm"))
	float TireHitRadius = 60.f;

	UPROPERTY(EditDefaultsOnly, Category = "Vehicle|Damage", meta = (ClampMin = "0", ClampMax = "1"))
	float TireFlatChanceFromProjectile = 0.35f;

	/** Atropelamento (A-010): dano no alvo por km/h e fração aplicada à frente do carro. */
	UPROPERTY(EditDefaultsOnly, Category = "Vehicle|Damage")
	float RunOverDamagePerKmh = 3.f;

	UPROPERTY(EditDefaultsOnly, Category = "Vehicle|Damage", meta = (ClampMin = "0"))
	float RunOverSelfDamageScale = 0.25f;

private:
	FJRVehicleDamageState State;
	TArray<float> BaseWheelRadius;
	float BaseMaxTorque = 0.f;
	double LastImpactTime = -1000.0;
	bool bWasSmoking = false;
	bool bDisabledBroadcast = false;
	FRandomStream Random;
};

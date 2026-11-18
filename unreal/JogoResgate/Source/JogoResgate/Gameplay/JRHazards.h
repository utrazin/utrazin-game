// Copyright utrazin. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "JRHazards.generated.h"

class UBoxComponent;
class UPointLightComponent;
class UStaticMeshComponent;

/**
 * Barril explosivo: explode com tiro, golpe ou batida do carro (acima de MinVehicleSpeedKmh).
 * Dano em área (zumbis, jogador, carro) + empurrão físico. Visual: malha + flash de luz.
 */
UCLASS()
class JOGORESGATE_API AJRExplosiveBarrel : public AActor
{
	GENERATED_BODY()

public:
	AJRExplosiveBarrel();

	virtual float TakeDamage(float DamageAmount, struct FDamageEvent const& DamageEvent, AController* EventInstigator, AActor* DamageCauser) override;

	UFUNCTION(BlueprintCallable, Category = "Hazard")
	void Explode(AActor* Causer);

protected:
	virtual void BeginPlay() override;

	UFUNCTION()
	void HandleHit(UPrimitiveComponent* HitComp, AActor* OtherActor, UPrimitiveComponent* OtherComp, FVector NormalImpulse, const FHitResult& Hit);

	UPROPERTY(VisibleAnywhere, Category = "Hazard")
	TObjectPtr<UStaticMeshComponent> Mesh;

	UPROPERTY(VisibleAnywhere, Category = "Hazard")
	TObjectPtr<UPointLightComponent> Flash;

	UPROPERTY(EditAnywhere, Category = "Hazard")
	float Health = 20.f;

	UPROPERTY(EditAnywhere, Category = "Hazard")
	float ExplosionDamage = 120.f;

	UPROPERTY(EditAnywhere, Category = "Hazard", meta = (Units = "cm"))
	float ExplosionRadius = 650.f;

	UPROPERTY(EditAnywhere, Category = "Hazard")
	float ExplosionImpulse = 2200.f;

	/** Dano extra direto no carro (0..100 por zona) quando ele está no raio. */
	UPROPERTY(EditAnywhere, Category = "Hazard")
	float VehicleZoneDamage = 25.f;

	UPROPERTY(EditAnywhere, Category = "Hazard", meta = (Units = "km/h"))
	float MinVehicleSpeedKmh = 15.f;

private:
	bool bExploded = false;
};

/** Tapete de pregos: fura os pneus do carro que passar por cima. */
UCLASS()
class JOGORESGATE_API AJRSpikeStrip : public AActor
{
	GENERATED_BODY()

public:
	AJRSpikeStrip();

protected:
	virtual void BeginPlay() override;

	UFUNCTION()
	void HandleOverlap(UPrimitiveComponent* OverlappedComponent, AActor* OtherActor, UPrimitiveComponent* OtherComp,
		int32 OtherBodyIndex, bool bFromSweep, const FHitResult& SweepResult);

	UPROPERTY(VisibleAnywhere, Category = "Hazard")
	TObjectPtr<UBoxComponent> Trigger;

	UPROPERTY(VisibleAnywhere, Category = "Hazard")
	TObjectPtr<UStaticMeshComponent> Mesh;

	/** Fura só os 2 pneus mais próximos (true) ou todos (false). */
	UPROPERTY(EditAnywhere, Category = "Hazard")
	bool bOnlyNearestTires = true;
};

/**
 * Volume de perigo: lago tóxico (dano por segundo) ou abismo (falha imediata -> checkpoint).
 */
UCLASS()
class JOGORESGATE_API AJRHazardVolume : public AActor
{
	GENERATED_BODY()

public:
	AJRHazardVolume();

protected:
	virtual void BeginPlay() override;
	void ApplyDamageTick();

	UFUNCTION()
	void HandleBegin(UPrimitiveComponent* OverlappedComponent, AActor* OtherActor, UPrimitiveComponent* OtherComp,
		int32 OtherBodyIndex, bool bFromSweep, const FHitResult& SweepResult);

	UFUNCTION()
	void HandleEnd(UPrimitiveComponent* OverlappedComponent, AActor* OtherActor, UPrimitiveComponent* OtherComp, int32 OtherBodyIndex);

	UPROPERTY(VisibleAnywhere, Category = "Hazard")
	TObjectPtr<UBoxComponent> Box;

	/** Abismo: o jogador (a pé ou no carro) falha na hora e volta ao checkpoint. */
	UPROPERTY(EditAnywhere, Category = "Hazard")
	bool bInstantFail = false;

	UPROPERTY(EditAnywhere, Category = "Hazard")
	float DamagePerSecond = 30.f;

private:
	TArray<TWeakObjectPtr<AActor>> Inside;
	FTimerHandle DamageTimer;
};

// Copyright utrazin. All Rights Reserved.

#include "Vehicles/JRVehicleDamageComponent.h"
#include "ChaosVehicleWheel.h"
#include "ChaosWheeledVehicleMovementComponent.h"
#include "Combat/JRHealthComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/World.h"
#include "JogoResgate.h"
#include "Kismet/GameplayStatics.h"
#include "WheeledVehiclePawn.h"

namespace
{
	constexpr float CmPerSecToKmh = 0.036f;
}

UJRVehicleDamageComponent::UJRVehicleDamageComponent()
{
	PrimaryComponentTick.bCanEverTick = false;
}

UChaosWheeledVehicleMovementComponent* UJRVehicleDamageComponent::GetMovement() const
{
	const AWheeledVehiclePawn* Vehicle = Cast<AWheeledVehiclePawn>(GetOwner());
	return Vehicle ? Cast<UChaosWheeledVehicleMovementComponent>(Vehicle->GetVehicleMovementComponent()) : nullptr;
}

void UJRVehicleDamageComponent::BeginPlay()
{
	Super::BeginPlay();
	Random.GenerateNewSeed();

	if (UChaosWheeledVehicleMovementComponent* Movement = GetMovement())
	{
		BaseMaxTorque = Movement->EngineSetup.MaxTorque;
		BaseWheelRadius.Reset();
		for (const UChaosVehicleWheel* Wheel : Movement->Wheels)
		{
			BaseWheelRadius.Add(Wheel ? Wheel->WheelRadius : 0.f);
		}
	}
	else
	{
		UE_LOG(LogJR, Warning, TEXT("%s: UJRVehicleDamageComponent requer UChaosWheeledVehicleMovementComponent"), *GetNameSafe(GetOwner()));
	}

	if (AActor* Owner = GetOwner())
	{
		Owner->OnActorHit.AddDynamic(this, &UJRVehicleDamageComponent::HandleActorHit);
		Owner->OnTakePointDamage.AddDynamic(this, &UJRVehicleDamageComponent::HandlePointDamage);
	}
}

void UJRVehicleDamageComponent::ApplyZoneDamage(EJRVehicleZone Zone, float Amount)
{
	if (State.ApplyZoneDamage(Zone, Amount) > 0.f)
	{
		ApplyEffectsToMovement();
	}
}

void UJRVehicleDamageComponent::SetTireFlat(EJRWheel Wheel, bool bFlat)
{
	if (State.IsTireFlat(Wheel) == bFlat)
	{
		return;
	}
	State.SetTireFlat(Wheel, bFlat);
	if (bFlat)
	{
		UE_LOG(LogJR, Log, TEXT("%s: pneu %s furado"), *GetNameSafe(GetOwner()), *UEnum::GetValueAsString(Wheel));
		OnTireFlat.Broadcast(Wheel);
	}
	ApplyEffectsToMovement();
}

void UJRVehicleDamageComponent::RepairAll()
{
	State.Reset();
	bDisabledBroadcast = false;
	ApplyEffectsToMovement();
}

void UJRVehicleDamageComponent::ApplyEffectsToMovement()
{
	if (UChaosWheeledVehicleMovementComponent* Movement = GetMovement())
	{
		// As rodas podem ser criadas depois do BeginPlay (criação do estado físico): captura tardia.
		if (BaseWheelRadius.Num() == 0)
		{
			for (const UChaosVehicleWheel* Wheel : Movement->Wheels)
			{
				BaseWheelRadius.Add(Wheel ? Wheel->WheelRadius : 0.f);
			}
		}
		if (BaseMaxTorque > 0.f)
		{
			Movement->SetMaxEngineTorque(BaseMaxTorque * State.GetEngineTorqueScale());
		}
		for (int32 i = 0; i < FJRVehicleDamageState::NumWheels && i < BaseWheelRadius.Num(); ++i)
		{
			const bool bFlat = State.IsTireFlat(static_cast<EJRWheel>(i));
			Movement->SetWheelFrictionMultiplier(i, bFlat ? FJRVehicleDamageState::FlatTireFrictionScale : 1.f);
			Movement->SetWheelRadius(i, BaseWheelRadius[i] * (bFlat ? FJRVehicleDamageState::FlatTireRadiusScale : 1.f));
		}
	}

	OnIntegrityChanged.Broadcast(State.GetIntegrity());

	const bool bSmoking = State.ShouldEmitEngineSmoke();
	if (bSmoking != bWasSmoking)
	{
		bWasSmoking = bSmoking;
		OnEngineSmoke.Broadcast(bSmoking);
	}
	if (State.IsDisabled() && !bDisabledBroadcast)
	{
		bDisabledBroadcast = true;
		UE_LOG(LogJR, Log, TEXT("%s inutilizado"), *GetNameSafe(GetOwner()));
		OnVehicleDisabled.Broadcast();
	}
}

int32 UJRVehicleDamageComponent::FindNearestWheel(const FVector& WorldLocation, float& OutDistance) const
{
	OutDistance = TNumericLimits<float>::Max();
	const AWheeledVehiclePawn* Vehicle = Cast<AWheeledVehiclePawn>(GetOwner());
	const UChaosWheeledVehicleMovementComponent* Movement = GetMovement();
	if (!Vehicle || !Movement)
	{
		return INDEX_NONE;
	}
	int32 Best = INDEX_NONE;
	for (int32 i = 0; i < Movement->WheelSetups.Num() && i < FJRVehicleDamageState::NumWheels; ++i)
	{
		const FVector WheelLocation = Vehicle->GetMesh()->GetSocketLocation(Movement->WheelSetups[i].BoneName);
		const float Dist = FVector::Dist(WheelLocation, WorldLocation);
		if (Dist < OutDistance)
		{
			OutDistance = Dist;
			Best = i;
		}
	}
	return Best;
}

void UJRVehicleDamageComponent::HandleActorHit(AActor* SelfActor, AActor* OtherActor, FVector NormalImpulse, const FHitResult& Hit)
{
	const double Now = GetWorld()->GetTimeSeconds();
	if (Now - LastImpactTime < MinTimeBetweenImpacts)
	{
		return;
	}

	const FVector OtherVelocity = OtherActor ? OtherActor->GetVelocity() : FVector::ZeroVector;
	const FVector Relative = SelfActor->GetVelocity() - OtherVelocity;
	const float ImpactKmh = static_cast<float>(FMath::Abs(FVector::DotProduct(Relative, Hit.ImpactNormal))) * CmPerSecToKmh;
	const float Damage = FJRVehicleDamageState::ImpactDamageFromSpeed(ImpactKmh);
	if (Damage <= 0.f)
	{
		return;
	}
	LastImpactTime = Now;

	// Atropelamento: alvos com saúde recebem dano; o carro sofre uma fração na frente (A-010).
	if (OtherActor && OtherActor->FindComponentByClass<UJRHealthComponent>())
	{
		// Carro estacionado/sem motorista não "atropela" (ex.: personagem saindo do carro).
		const APawn* SelfPawn = Cast<APawn>(SelfActor);
		if (!SelfPawn || !SelfPawn->GetController())
		{
			return;
		}
		UGameplayStatics::ApplyDamage(OtherActor, ImpactKmh * RunOverDamagePerKmh, SelfActor->GetInstigatorController(), SelfActor, nullptr);
		ApplyZoneDamage(EJRVehicleZone::Front, Damage * RunOverSelfDamageScale);
		return;
	}

	const FVector Local = SelfActor->GetActorTransform().InverseTransformPosition(Hit.ImpactPoint);
	const EJRVehicleZone Zone = FJRVehicleDamageState::ZoneFromLocalPoint(Local, HalfLength, HalfWidth);
	State.ApplyZoneDamage(Zone, Damage);
	if (Zone == EJRVehicleZone::Front)
	{
		State.ApplyZoneDamage(EJRVehicleZone::Engine, Damage * FrontToEngineDamageRatio);
	}

	if ((Zone == EJRVehicleZone::Left || Zone == EJRVehicleZone::Right) && ImpactKmh >= TireBurstImpactKmh)
	{
		float Dist = 0.f;
		const int32 Wheel = FindNearestWheel(Hit.ImpactPoint, Dist);
		if (Wheel != INDEX_NONE && Dist <= TireHitRadius * 1.5f)
		{
			SetTireFlat(static_cast<EJRWheel>(Wheel), true);
			return; // SetTireFlat já aplicou os efeitos
		}
	}
	ApplyEffectsToMovement();
}

void UJRVehicleDamageComponent::HandlePointDamage(AActor* DamagedActor, float Damage, AController* InstigatedBy,
	FVector HitLocation, UPrimitiveComponent* HitComponent, FName BoneName, FVector ShotFromDirection,
	const UDamageType* DamageType, AActor* DamageCauser)
{
	float Dist = 0.f;
	const int32 Wheel = FindNearestWheel(HitLocation, Dist);
	if (Wheel != INDEX_NONE && Dist <= TireHitRadius && Random.FRand() < TireFlatChanceFromProjectile)
	{
		SetTireFlat(static_cast<EJRWheel>(Wheel), true);
		return;
	}
	const FVector Local = DamagedActor->GetActorTransform().InverseTransformPosition(HitLocation);
	ApplyZoneDamage(FJRVehicleDamageState::ZoneFromLocalPoint(Local, HalfLength, HalfWidth), Damage);
}

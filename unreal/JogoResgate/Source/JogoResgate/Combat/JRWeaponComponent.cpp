// Copyright utrazin. All Rights Reserved.

#include "Combat/JRWeaponComponent.h"
#include "AI/JRAimPrediction.h"
#include "Combat/JRWeaponDefinition.h"
#include "Engine/World.h"
#include "GameFramework/Controller.h"
#include "GameFramework/Pawn.h"
#include "JogoResgate.h"
#include "Kismet/GameplayStatics.h"
#include "DrawDebugHelpers.h"
#include "TimerManager.h"

UJRWeaponComponent::UJRWeaponComponent()
{
	PrimaryComponentTick.bCanEverTick = false;
}

void UJRWeaponComponent::BeginPlay()
{
	Super::BeginPlay();
	SpreadStream.GenerateNewSeed();
	EquipDefinition(Definition);
}

void UJRWeaponComponent::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
	CancelAll();
	Super::EndPlay(EndPlayReason);
}

void UJRWeaponComponent::EquipDefinition(UJRWeaponDefinition* NewDefinition)
{
	CancelAll();
	Definition = NewDefinition;
	if (Definition)
	{
		Ammo.Initialize(Definition->MagazineSize, Definition->StartingReserve);
		OnAmmoChanged.Broadcast(Ammo.Magazine, Ammo.Reserve);
	}
}

void UJRWeaponComponent::StartFire()
{
	if (!Definition || bReloading)
	{
		return;
	}
	bWantsToFire = true;
	UWorld* World = GetWorld();
	const float Interval = 1.f / Definition->FireRate;
	const double Elapsed = World->GetTimeSeconds() - LastFireTime;
	const float FirstDelay = FMath::Max(0.f, Interval - static_cast<float>(Elapsed));
	World->GetTimerManager().SetTimer(FireTimer, this, &UJRWeaponComponent::FireOnce, Interval, true, FirstDelay);
}

void UJRWeaponComponent::StopFire()
{
	bWantsToFire = false;
	if (UWorld* World = GetWorld())
	{
		World->GetTimerManager().ClearTimer(FireTimer);
	}
}

bool UJRWeaponComponent::StartReload()
{
	if (!Definition || bReloading || !Ammo.CanReload())
	{
		return false;
	}
	StopFire();
	bReloading = true;
	OnReloadStateChanged.Broadcast(true);
	GetWorld()->GetTimerManager().SetTimer(ReloadTimer, this, &UJRWeaponComponent::FinishReload, Definition->ReloadTime, false);
	return true;
}

void UJRWeaponComponent::FinishReload()
{
	bReloading = false;
	Ammo.Reload();
	OnReloadStateChanged.Broadcast(false);
	OnAmmoChanged.Broadcast(Ammo.Magazine, Ammo.Reserve);
}

void UJRWeaponComponent::AddReserveAmmo(int32 Amount)
{
	Ammo.AddReserve(Amount);
	OnAmmoChanged.Broadcast(Ammo.Magazine, Ammo.Reserve);
}

void UJRWeaponComponent::CancelAll()
{
	StopFire();
	if (bReloading)
	{
		bReloading = false;
		if (UWorld* World = GetWorld())
		{
			World->GetTimerManager().ClearTimer(ReloadTimer);
		}
		OnReloadStateChanged.Broadcast(false);
	}
}

bool UJRWeaponComponent::GetAimViewPoint(FVector& OutLocation, FRotator& OutRotation) const
{
	const APawn* Pawn = Cast<APawn>(GetOwner());
	if (!Pawn)
	{
		return false;
	}
	if (const AController* Controller = Pawn->GetController())
	{
		Controller->GetPlayerViewPoint(OutLocation, OutRotation);
		return true;
	}
	Pawn->GetActorEyesViewPoint(OutLocation, OutRotation);
	return true;
}

void UJRWeaponComponent::FireOnce()
{
	if (!Definition || !bWantsToFire)
	{
		StopFire();
		return;
	}
	if (!Ammo.ConsumeShot())
	{
		StopFire();
		StartReload();
		return;
	}
	LastFireTime = GetWorld()->GetTimeSeconds();

	FVector ViewLocation;
	FRotator ViewRotation;
	if (!GetAimViewPoint(ViewLocation, ViewRotation))
	{
		return;
	}
	const float Spread = bAiming ? Definition->SpreadHalfAngleDegrees * 0.5f : Definition->SpreadHalfAngleDegrees;
	const FVector Direction = FJRAimPrediction::ApplySpread(ViewRotation.Vector(), Spread, SpreadStream);
	const FVector End = ViewLocation + Direction * Definition->Range;

	FCollisionQueryParams Params(SCENE_QUERY_STAT(JRWeaponTrace), true, GetOwner());
	FHitResult Hit;
	const bool bHit = GetWorld()->LineTraceSingleByChannel(Hit, ViewLocation, End, TraceChannel, Params);
	if (bHit && Hit.GetActor())
	{
		UGameplayStatics::ApplyPointDamage(Hit.GetActor(), Definition->Damage, Direction, Hit,
			GetOwner()->GetInstigatorController(), GetOwner(), nullptr);
	}
	if (bDrawDebugTracer)
	{
		// Greybox: rastro visível do tiro até existir arma/VFX de verdade.
		const FVector Muzzle = GetOwner()->GetActorLocation() + FVector(0.f, 0.f, 50.f);
		const FVector Impact = bHit ? FVector(Hit.ImpactPoint) : End;
		DrawDebugLine(GetWorld(), Muzzle, Impact, FColor::Cyan, false, 0.12f, 0, 2.f);
		if (bHit)
		{
			DrawDebugSphere(GetWorld(), Impact, 12.f, 8, FColor::Red, false, 0.3f);
		}
	}
	OnWeaponFired.Broadcast(ViewLocation, bHit ? Hit.ImpactPoint : End);
	OnAmmoChanged.Broadcast(Ammo.Magazine, Ammo.Reserve);
}

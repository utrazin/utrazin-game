// Copyright utrazin. All Rights Reserved.

#include "Gameplay/JRHazards.h"
#include "Audio/JRAudio.h" // [Áudio/A-061]
#include "Components/BoxComponent.h"
#include "Components/PointLightComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Core/JRGameMode.h"
#include "Engine/DamageEvents.h"
#include "Engine/OverlapResult.h"
#include "Engine/World.h"
#include "GameFramework/Character.h"
#include "Kismet/GameplayStatics.h"
#include "TimerManager.h"
#include "Vehicles/JRVehicleDamageComponent.h"
#include "Vehicles/JRVehicleDamageModel.h"
#include "Vehicles/JRVehiclePawn.h"

// ===================================================================== barril explosivo

AJRExplosiveBarrel::AJRExplosiveBarrel()
{
	PrimaryActorTick.bCanEverTick = false;
	Mesh = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Mesh"));
	RootComponent = Mesh;
	Mesh->SetCollisionProfileName(TEXT("PhysicsActor"));
	Mesh->SetNotifyRigidBodyCollision(true);
	Flash = CreateDefaultSubobject<UPointLightComponent>(TEXT("Flash"));
	Flash->SetupAttachment(Mesh);
	Flash->SetIntensity(0.f);
	Flash->SetAttenuationRadius(1500.f);
	Flash->SetLightColor(FLinearColor(1.f, 0.55f, 0.15f));
}

void AJRExplosiveBarrel::BeginPlay()
{
	Super::BeginPlay();
	Mesh->OnComponentHit.AddDynamic(this, &AJRExplosiveBarrel::HandleHit);
}

float AJRExplosiveBarrel::TakeDamage(float DamageAmount, FDamageEvent const& DamageEvent, AController* EventInstigator, AActor* DamageCauser)
{
	const float Applied = Super::TakeDamage(DamageAmount, DamageEvent, EventInstigator, DamageCauser);
	Health -= DamageAmount;
	if (Health <= 0.f)
	{
		Explode(DamageCauser);
	}
	return Applied;
}

void AJRExplosiveBarrel::HandleHit(UPrimitiveComponent* HitComp, AActor* OtherActor, UPrimitiveComponent* OtherComp, FVector NormalImpulse, const FHitResult& Hit)
{
	if (const AJRVehiclePawn* Vehicle = Cast<AJRVehiclePawn>(OtherActor))
	{
		if (Vehicle->GetSpeedKmh() >= MinVehicleSpeedKmh)
		{
			Explode(OtherActor);
		}
	}
}

void AJRExplosiveBarrel::Explode(AActor* Causer)
{
	if (bExploded)
	{
		return;
	}
	bExploded = true;
	const FVector Origin = GetActorLocation();
	UJRAudio::PlayAt(this, TEXT("World.Barrel.Explode"), Origin); // [Áudio/A-061]
	UGameplayStatics::ApplyRadialDamageWithFalloff(this, ExplosionDamage, ExplosionDamage * 0.2f, Origin,
		ExplosionRadius * 0.35f, ExplosionRadius, 1.f, nullptr, TArray<AActor*>{ this }, this,
		Causer ? Causer->GetInstigatorController() : nullptr);

	TArray<FOverlapResult> Overlaps;
	FCollisionObjectQueryParams Objects(FCollisionObjectQueryParams::AllDynamicObjects);
	GetWorld()->OverlapMultiByObjectType(Overlaps, Origin, FQuat::Identity, Objects, FCollisionShape::MakeSphere(ExplosionRadius));
	TSet<AActor*> Done;
	for (const FOverlapResult& O : Overlaps)
	{
		UPrimitiveComponent* Comp = O.GetComponent();
		AActor* Other = O.GetActor();
		if (Comp && Comp->IsSimulatingPhysics() && Other != this)
		{
			Comp->AddRadialImpulse(Origin, ExplosionRadius, ExplosionImpulse, ERadialImpulseFalloff::RIF_Linear, true);
		}
		if (AJRVehiclePawn* Vehicle = Cast<AJRVehiclePawn>(Other))
		{
			if (!Done.Contains(Vehicle))
			{
				Done.Add(Vehicle);
				if (UJRVehicleDamageComponent* Damage = Vehicle->GetDamageComponent())
				{
					const FVector Local = Vehicle->GetActorTransform().InverseTransformPosition(Origin);
					Damage->ApplyZoneDamage(Local.X >= 0.f ? EJRVehicleZone::Front : EJRVehicleZone::Rear, VehicleZoneDamage);
				}
			}
		}
		else if (ACharacter* Char = Cast<ACharacter>(Other))
		{
			if (!Done.Contains(Char))
			{
				Done.Add(Char);
				const FVector Dir = (Char->GetActorLocation() - Origin).GetSafeNormal2D();
				Char->LaunchCharacter(Dir * 900.f + FVector(0.f, 0.f, 600.f), true, true);
			}
		}
	}
	// Flash rápido e some.
	Flash->SetIntensity(80000.f);
	Mesh->SetVisibility(false);
	Mesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	SetLifeSpan(0.25f);
}

// ===================================================================== tapete de pregos

AJRSpikeStrip::AJRSpikeStrip()
{
	PrimaryActorTick.bCanEverTick = false;
	Trigger = CreateDefaultSubobject<UBoxComponent>(TEXT("Trigger"));
	Trigger->SetBoxExtent(FVector(200.f, 40.f, 60.f));
	Trigger->SetCollisionProfileName(TEXT("OverlapAllDynamic"));
	RootComponent = Trigger;
	Mesh = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Mesh"));
	Mesh->SetupAttachment(Trigger);
	Mesh->SetRelativeLocation(FVector(0.f, 0.f, -60.f));
	Mesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
}

void AJRSpikeStrip::BeginPlay()
{
	Super::BeginPlay();
	Trigger->OnComponentBeginOverlap.AddDynamic(this, &AJRSpikeStrip::HandleOverlap);
}

void AJRSpikeStrip::HandleOverlap(UPrimitiveComponent* OverlappedComponent, AActor* OtherActor, UPrimitiveComponent* OtherComp,
	int32 OtherBodyIndex, bool bFromSweep, const FHitResult& SweepResult)
{
	AJRVehiclePawn* Vehicle = Cast<AJRVehiclePawn>(OtherActor);
	UJRVehicleDamageComponent* Damage = Vehicle ? Vehicle->GetDamageComponent() : nullptr;
	if (!Damage)
	{
		return;
	}
	UJRAudio::PlayAt(this, TEXT("World.Spikes"), Vehicle->GetActorLocation()); // [Áudio/A-061]
	if (!bOnlyNearestTires)
	{
		for (int32 i = 0; i < static_cast<int32>(EJRWheel::Count); ++i)
		{
			Damage->SetTireFlat(static_cast<EJRWheel>(i), true);
		}
		return;
	}
	// Lado do carro que passou por cima (pela posição relativa ao tapete).
	const FVector Local = Vehicle->GetActorTransform().InverseTransformPosition(GetActorLocation());
	const bool bLeft = Local.Y < 0.f;
	Damage->SetTireFlat(bLeft ? EJRWheel::FrontLeft : EJRWheel::FrontRight, true);
	Damage->SetTireFlat(bLeft ? EJRWheel::RearLeft : EJRWheel::RearRight, true);
}

// ===================================================================== volume de perigo

AJRHazardVolume::AJRHazardVolume()
{
	PrimaryActorTick.bCanEverTick = false;
	Box = CreateDefaultSubobject<UBoxComponent>(TEXT("Box"));
	Box->SetBoxExtent(FVector(500.f, 500.f, 200.f));
	Box->SetCollisionProfileName(TEXT("OverlapAllDynamic"));
	RootComponent = Box;
}

void AJRHazardVolume::BeginPlay()
{
	Super::BeginPlay();
	Box->OnComponentBeginOverlap.AddDynamic(this, &AJRHazardVolume::HandleBegin);
	Box->OnComponentEndOverlap.AddDynamic(this, &AJRHazardVolume::HandleEnd);
}

void AJRHazardVolume::HandleBegin(UPrimitiveComponent* OverlappedComponent, AActor* OtherActor, UPrimitiveComponent* OtherComp,
	int32 OtherBodyIndex, bool bFromSweep, const FHitResult& SweepResult)
{
	APawn* Pawn = Cast<APawn>(OtherActor);
	if (!Pawn)
	{
		return;
	}
	if (bInstantFail)
	{
		if (Pawn->IsPlayerControlled())
		{
			if (AJRGameMode* GameMode = GetWorld()->GetAuthGameMode<AJRGameMode>())
			{
				GameMode->HandlePlayerFailure(Pawn);
			}
		}
		else
		{
			UGameplayStatics::ApplyDamage(Pawn, 9999.f, nullptr, this, nullptr); // zumbi caiu no abismo
		}
		return;
	}
	Inside.AddUnique(Pawn);
	if (!GetWorldTimerManager().IsTimerActive(DamageTimer))
	{
		GetWorldTimerManager().SetTimer(DamageTimer, this, &AJRHazardVolume::ApplyDamageTick, 0.25f, true, 0.f);
	}
}

void AJRHazardVolume::HandleEnd(UPrimitiveComponent* OverlappedComponent, AActor* OtherActor, UPrimitiveComponent* OtherComp, int32 OtherBodyIndex)
{
	Inside.Remove(OtherActor);
}

void AJRHazardVolume::ApplyDamageTick()
{
	Inside.RemoveAll([](const TWeakObjectPtr<AActor>& A) { return !A.IsValid(); });
	if (Inside.Num() == 0)
	{
		GetWorldTimerManager().ClearTimer(DamageTimer);
		return;
	}
	for (const TWeakObjectPtr<AActor>& A : Inside)
	{
		UGameplayStatics::ApplyDamage(A.Get(), DamagePerSecond * 0.25f, nullptr, this, nullptr);
	}
}

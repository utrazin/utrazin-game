// Copyright utrazin. All Rights Reserved.

#include "AI/JRZombieBarricade.h"
#include "AI/JREnemyCharacter.h"
#include "Components/BoxComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/CollisionProfile.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "JogoResgate.h"
#include "Kismet/GameplayStatics.h"
#include "TimerManager.h"
#include "UI/JRHUD.h"
#include "Vehicles/JRVehicleDamageComponent.h"
#include "Vehicles/JRVehiclePawn.h"

namespace
{
	constexpr float CmPerSecToKmh = 0.036f;
	/** Folga da área de detecção à frente dos destroços (o carro é visto chegando). */
	constexpr float ApproachMargin = 500.f;
	/** Intervalo da conferência enquanto o carro está na área (100 km/h anda ~55 cm nesse tempo). */
	constexpr float RamCheckInterval = 0.02f;
}

AJRZombieBarricade::AJRZombieBarricade()
{
	PrimaryActorTick.bCanEverTick = false;
	RamArea = CreateDefaultSubobject<UBoxComponent>(TEXT("RamArea"));
	RootComponent = RamArea;
	RamArea->SetBoxExtent(FVector(250.f, 450.f, 150.f));
	RamArea->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
	RamArea->SetCollisionResponseToAllChannels(ECR_Ignore);
	RamArea->SetCollisionResponseToChannel(ECC_Vehicle, ECR_Overlap);
	RamArea->SetCollisionResponseToChannel(ECC_PhysicsBody, ECR_Overlap);
	RamArea->SetGenerateOverlapEvents(true);
	RamArea->SetCanEverAffectNavigation(false);
}

void AJRZombieBarricade::BeginPlay()
{
	Super::BeginPlay();
	Random.GenerateNewSeed();
	BuildProps();

	// Área: cobre zumbis e destroços, com folga na frente para ver o carro chegando.
	float HalfX = FMath::Max(Depth * 0.5f, 150.f);
	for (const UBoxComponent* Body : PropBodies)
	{
		if (Body)
		{
			const FVector Local = GetActorTransform().InverseTransformPositionNoScale(Body->GetComponentLocation());
			const FVector Ext = Body->GetScaledBoxExtent();
			HalfX = FMath::Max(HalfX, static_cast<float>(FMath::Abs(Local.X) + FMath::Max(Ext.X, Ext.Y)));
		}
	}
	if (PropBodies.Num() > 0)
	{
		HalfX += ApproachMargin;
	}
	RamArea->SetBoxExtent(FVector(HalfX, FMath::Max(Width * 0.5f + 250.f, 150.f), 250.f));
	RamArea->OnComponentBeginOverlap.AddDynamic(this, &AJRZombieBarricade::HandleRamOverlap);
	RamArea->OnComponentEndOverlap.AddDynamic(this, &AJRZombieBarricade::HandleRamEndOverlap);

	if (SpawnWhenPlayerWithin <= 0.f)
	{
		SpawnZombies();
	}
	else
	{
		GetWorldTimerManager().SetTimer(CheckTimer, this, &AJRZombieBarricade::CheckPlayerDistance, 1.f, true, Random.FRandRange(0.f, 1.f));
	}
}

void AJRZombieBarricade::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
	GetWorldTimerManager().ClearTimer(CheckTimer);
	GetWorldTimerManager().ClearTimer(RamTimer);
	GetWorldTimerManager().ClearTimer(DebrisSleepTimer);
	Super::EndPlay(EndPlayReason);
}

void AJRZombieBarricade::BuildProps()
{
	PropBodies.Reset();
	if (PropMeshes.Num() == 0 || PropCount <= 0)
	{
		return;
	}
	const FVector Forward = GetActorForwardVector().GetSafeNormal2D();
	const FVector Right = GetActorRightVector().GetSafeNormal2D();
	// Fileira de destroços na frente dos zumbis (lado de onde o carro vem), atravessando a estrada.
	const float LineX = Depth * 0.5f + 200.f;
	for (int32 i = 0; i < PropCount; ++i)
	{
		UStaticMesh* Mesh = PropMeshes[Random.RandRange(0, PropMeshes.Num() - 1)];
		if (!Mesh)
		{
			continue;
		}
		const FBoxSphereBounds Bounds = Mesh->GetBounds();
		const FVector Extent = Bounds.BoxExtent * PropScale;
		const float Y = PropCount > 1 ? FMath::Lerp(-Width * 0.5f, Width * 0.5f, static_cast<float>(i) / (PropCount - 1)) : 0.f;
		FVector Location = GetActorLocation() + Forward * (LineX + Random.FRandRange(-60.f, 60.f)) + Right * (Y + Random.FRandRange(-50.f, 50.f));
		FHitResult Hit;
		FCollisionQueryParams Query(SCENE_QUERY_STAT(JRBarricadePropGround), false, this);
		if (GetWorld()->LineTraceSingleByChannel(Hit, Location + FVector(0.f, 0.f, 500.f), Location - FVector(0.f, 0.f, 1500.f), ECC_Visibility, Query))
		{
			Location.Z = Hit.ImpactPoint.Z;
		}
		Location.Z += Extent.Z;
		// De lado (comprimento atravessando a estrada), um pouco torto.
		const FRotator Rotation(0.f, GetActorRotation().Yaw + 90.f + Random.FRandRange(-25.f, 25.f), 0.f);

		// Corpo físico = caixa do tamanho da malha (serve para malhas com colisão complexa também).
		UBoxComponent* Body = NewObject<UBoxComponent>(this, MakeUniqueObjectName(this, UBoxComponent::StaticClass(), TEXT("PropBody")));
		Body->SetMobility(EComponentMobility::Movable);
		Body->SetupAttachment(RootComponent);
		Body->SetBoxExtent(Extent, false);
		Body->SetCollisionProfileName(UCollisionProfile::BlockAll_ProfileName);
		Body->SetGenerateOverlapEvents(false);
		Body->SetCanEverAffectNavigation(false);
		Body->RegisterComponent();
		Body->SetWorldLocationAndRotation(Location, Rotation);

		UStaticMeshComponent* Visual = NewObject<UStaticMeshComponent>(this, MakeUniqueObjectName(this, UStaticMeshComponent::StaticClass(), TEXT("PropMesh")));
		Visual->SetMobility(EComponentMobility::Movable);
		Visual->SetStaticMesh(Mesh);
		Visual->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		Visual->SetGenerateOverlapEvents(false);
		Visual->SetCanEverAffectNavigation(false);
		Visual->SetupAttachment(Body);
		Visual->SetRelativeScale3D(FVector(PropScale));
		Visual->SetRelativeLocation(-Bounds.Origin * PropScale); // centro da malha no centro da caixa
		Visual->RegisterComponent();

		PropBodies.Add(Body);
	}
	UE_LOG(LogJR, Log, TEXT("%s: %d destroços na barricada"), *GetName(), PropBodies.Num());
}

void AJRZombieBarricade::CheckPlayerDistance()
{
	const APawn* Player = UGameplayStatics::GetPlayerPawn(this, 0);
	if (Player && FVector::Dist2D(Player->GetActorLocation(), GetActorLocation()) <= SpawnWhenPlayerWithin)
	{
		GetWorldTimerManager().ClearTimer(CheckTimer);
		SpawnZombies();
	}
}

void AJRZombieBarricade::SpawnZombies()
{
	if (bSpawned)
	{
		return;
	}
	bSpawned = true;
	if (Count <= 0)
	{
		return;
	}
	if (EnemyClasses.Num() == 0)
	{
		UE_LOG(LogJR, Warning, TEXT("%s: EnemyClasses vazia, barricada sem zumbis"), *GetName());
		return;
	}
	const FVector Forward = GetActorForwardVector().GetSafeNormal2D();
	const FVector Right = GetActorRightVector().GetSafeNormal2D();
	// Fileiras atravessando a estrada, com um pouco de bagunça.
	const int32 PerRow = FMath::Max(1, FMath::CeilToInt(FMath::Sqrt(static_cast<float>(Count) * Width / FMath::Max(Depth, 1.f))));
	const int32 Rows = FMath::Max(1, FMath::DivideAndRoundUp(Count, PerRow));
	for (int32 i = 0; i < Count; ++i)
	{
		const int32 Row = i / PerRow;
		const int32 Col = i % PerRow;
		const float Y = PerRow > 1 ? FMath::Lerp(-Width * 0.5f, Width * 0.5f, static_cast<float>(Col) / (PerRow - 1)) : 0.f;
		const float X = Rows > 1 ? FMath::Lerp(-Depth * 0.5f, Depth * 0.5f, static_cast<float>(Row) / (Rows - 1)) : 0.f;
		FVector Location = GetActorLocation() + Right * (Y + Random.FRandRange(-40.f, 40.f)) + Forward * (X + Random.FRandRange(-40.f, 40.f));
		// Apoia no chão.
		FHitResult Hit;
		FCollisionQueryParams Query(SCENE_QUERY_STAT(JRBarricadeGround), false, this);
		if (GetWorld()->LineTraceSingleByChannel(Hit, Location + FVector(0.f, 0.f, 500.f), Location - FVector(0.f, 0.f, 1500.f), ECC_Visibility, Query))
		{
			Location.Z = Hit.ImpactPoint.Z + 95.f;
		}
		const TSubclassOf<AJREnemyCharacter> Cls = EnemyClasses[Random.RandRange(0, EnemyClasses.Num() - 1)];
		if (!Cls)
		{
			continue;
		}
		FActorSpawnParameters Params;
		Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AdjustIfPossibleButAlwaysSpawn;
		const FRotator Facing(0.f, GetActorRotation().Yaw + Random.FRandRange(-30.f, 30.f), 0.f);
		if (AJREnemyCharacter* Zombie = GetWorld()->SpawnActor<AJREnemyCharacter>(Cls, Location, Facing, Params))
		{
			Zombie->SetHoldPosition(!bRammed);
			Zombies.Add(Zombie);
		}
	}
	UE_LOG(LogJR, Log, TEXT("%s: barricada com %d zumbis"), *GetName(), Zombies.Num());
}

void AJRZombieBarricade::HandleRamOverlap(UPrimitiveComponent* OverlappedComponent, AActor* OtherActor, UPrimitiveComponent* OtherComp,
	int32 OtherBodyIndex, bool bFromSweep, const FHitResult& SweepResult)
{
	AJRVehiclePawn* Car = Cast<AJRVehiclePawn>(OtherActor);
	if (!Car || bRammed)
	{
		return;
	}
	CarInArea = Car;
	if (!GetWorldTimerManager().IsTimerActive(RamTimer))
	{
		GetWorldTimerManager().SetTimer(RamTimer, this, &AJRZombieBarricade::CheckRam, RamCheckInterval, true);
	}
	CheckRam();
}

void AJRZombieBarricade::HandleRamEndOverlap(UPrimitiveComponent* OverlappedComponent, AActor* OtherActor, UPrimitiveComponent* OtherComp,
	int32 OtherBodyIndex)
{
	if (OtherActor && OtherActor == CarInArea.Get())
	{
		CarInArea.Reset();
		GetWorldTimerManager().ClearTimer(RamTimer);
	}
}

void AJRZombieBarricade::CheckRam()
{
	AJRVehiclePawn* Car = CarInArea.Get();
	if (!Car || bRammed)
	{
		GetWorldTimerManager().ClearTimer(RamTimer);
		return;
	}
	const FVector Velocity = Car->GetVelocity();
	const float Kmh = static_cast<float>(Velocity.Size()) * CmPerSecToKmh;

	if (PropBodies.Num() == 0)
	{
		// Só zumbis: furar a RamMinSpeedKmh+ com alguém de pé.
		int32 Standing = 0;
		for (const TWeakObjectPtr<AJREnemyCharacter>& Zombie : Zombies)
		{
			Standing += (Zombie.IsValid() && !Zombie->IsDead()) ? 1 : 0;
		}
		if (bSpawned && Standing > 0 && Kmh >= RamMinSpeedKmh)
		{
			BreakBarricade(Car, Kmh);
		}
		return;
	}

	// Destroços: mede a folga entre a lataria e o destroço mais próximo à frente do carro.
	float MinGap = TNumericLimits<float>::Max();
	for (const UBoxComponent* Body : PropBodies)
	{
		if (!Body)
		{
			continue;
		}
		const FTransform BodyTransform = Body->GetComponentTransform();
		const FVector Ext = Body->GetScaledBoxExtent();
		const FVector Local = BodyTransform.InverseTransformPositionNoScale(Car->GetActorLocation());
		const FVector Clamped(FMath::Clamp(Local.X, -Ext.X, Ext.X), FMath::Clamp(Local.Y, -Ext.Y, Ext.Y), FMath::Clamp(Local.Z, -Ext.Z, Ext.Z));
		const FVector Closest = BodyTransform.TransformPositionNoScale(Clamped);
		if (Kmh > 5.f && FVector::DotProduct(Closest - Car->GetActorLocation(), Velocity) <= 0.0)
		{
			continue; // destroço ficou para trás
		}
		MinGap = FMath::Min(MinGap, Car->GetDistanceToBody(Closest));
	}
	// Folga de gatilho cresce com a velocidade (quebra um instante antes de encostar).
	const float Trigger = 120.f + static_cast<float>(Velocity.Size()) * RamCheckInterval * 2.f;
	if (MinGap > Trigger)
	{
		return;
	}
	if (Kmh >= BreakSpeedKmh)
	{
		BreakBarricade(Car, Kmh);
	}
	else if (!bHintShown && Car->IsPlayerControlled())
	{
		bHintShown = true;
		AJRHUD::Toast(this, FString::Printf(TEXT("Barricada! Dê ré e venha a %.0f+ km/h, ou desvie."), BreakSpeedKmh), FLinearColor(1.f, 0.8f, 0.2f));
	}
}

void AJRZombieBarricade::BreakBarricade(AJRVehiclePawn* Car, float SpeedKmh)
{
	if (bRammed)
	{
		return;
	}
	bRammed = true;
	GetWorldTimerManager().ClearTimer(RamTimer);
	const bool bHasProps = PropBodies.Num() > 0;

	// O "tranco" de furar o bloqueio (cada zumbi atropelado ainda dá o próprio dano).
	if (Car)
	{
		if (UJRVehicleDamageComponent* Damage = Car->GetDamageComponent())
		{
			const float Amount = bHasProps ? BreakDamage : RamDamage;
			Damage->ApplyZoneDamage(EJRVehicleZone::Front, Amount);
			if (!Car->IsWrecked())
			{
				Damage->ApplyZoneDamage(EJRVehicleZone::Engine, Amount * 0.5f);
			}
		}
	}

	// Destroços viram física leve, voam para frente e deixam de bater no carro e nos zumbis.
	const FVector CarVelocity = Car ? Car->GetVelocity() : -GetActorForwardVector() * 1500.f;
	const FVector From = Car ? Car->GetActorLocation() : GetActorLocation() + GetActorForwardVector() * 500.f;
	for (UBoxComponent* Body : PropBodies)
	{
		if (!Body)
		{
			continue;
		}
		Body->DetachFromComponent(FDetachmentTransformRules::KeepWorldTransform);
		Body->SetCollisionObjectType(ECC_PhysicsBody);
		Body->SetCollisionResponseToChannel(ECC_Vehicle, ECR_Ignore);
		Body->SetCollisionResponseToChannel(ECC_Pawn, ECR_Ignore);
		Body->SetCollisionResponseToChannel(ECC_PhysicsBody, ECR_Block);
		Body->SetSimulatePhysics(true);
		Body->SetMassOverrideInKg(NAME_None, PropMassKg, true);
		const FVector Away = (Body->GetComponentLocation() - From).GetSafeNormal2D();
		Body->SetPhysicsLinearVelocity(CarVelocity * Random.FRandRange(0.55f, 0.85f) + Away * 300.f
			+ FVector(0.f, 0.f, 250.f + SpeedKmh * 6.f));
		Body->SetPhysicsAngularVelocityInDegrees(Random.GetUnitVector() * Random.FRandRange(90.f, 240.f));
	}
	if (bHasProps)
	{
		GetWorldTimerManager().SetTimer(DebrisSleepTimer, this, &AJRZombieBarricade::SleepDebris, 10.f, false);
	}

	for (const TWeakObjectPtr<AJREnemyCharacter>& Zombie : Zombies)
	{
		if (AJREnemyCharacter* Z = Zombie.Get())
		{
			Z->SetHoldPosition(false);
		}
	}
	AJRHUD::Toast(this, bHasProps ? TEXT("Furou a barricada!") : TEXT("Furou a barricada de zumbis!"), FLinearColor(1.f, 0.6f, 0.1f));
	UE_LOG(LogJR, Log, TEXT("%s: barricada furada a %.0f km/h"), *GetName(), SpeedKmh);

	OnBarricadeBroken(SpeedKmh);
	OnBarricadeBrokenDelegate.Broadcast(this, SpeedKmh);
	if (Car)
	{
		Car->NotifyZombieCarEvent(EJRZombieCarEvent::BarricadeBroken, nullptr, GetActorLocation(), SpeedKmh);
	}
}

void AJRZombieBarricade::SleepDebris()
{
	// Destroços parados não gastam física.
	for (UBoxComponent* Body : PropBodies)
	{
		if (Body && Body->IsSimulatingPhysics())
		{
			Body->PutRigidBodyToSleep();
		}
	}
}

// Copyright utrazin. All Rights Reserved.

#include "AI/JRAmbientSpawner.h"
#include "AI/JRAIDirector.h"
#include "AI/JREnemyCharacter.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "Kismet/GameplayStatics.h"
#include "NavigationPath.h"
#include "NavigationSystem.h"
#include "TimerManager.h"

AJRAmbientSpawner::AJRAmbientSpawner()
{
	PrimaryActorTick.bCanEverTick = false;
	RootComponent = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
}

void AJRAmbientSpawner::BeginPlay()
{
	Super::BeginPlay();
	Random.GenerateNewSeed();
	ScheduleNext();
}

void AJRAmbientSpawner::ScheduleNext()
{
	GetWorldTimerManager().SetTimer(Timer, this, &AJRAmbientSpawner::TrySpawnGroup,
		Random.FRandRange(MinInterval, FMath::Max(MinInterval, MaxInterval)), false);
}

bool AJRAmbientSpawner::FindSpawnPoint(const APawn* Player, FVector& OutPoint) const
{
	UNavigationSystemV1* Nav = FNavigationSystem::GetCurrent<UNavigationSystemV1>(GetWorld());
	const APlayerController* PC = Cast<APlayerController>(Player->GetController());
	if (!Nav || !PC)
	{
		return false;
	}
	FVector ViewLoc;
	FRotator ViewRot;
	PC->GetPlayerViewPoint(ViewLoc, ViewRot);
	const FVector ViewDir = ViewRot.Vector().GetSafeNormal2D();
	const float CosHidden = FMath::Cos(FMath::DegreesToRadians(HiddenConeHalfAngle));
	for (int32 Try = 0; Try < 12; ++Try)
	{
		const float Ang = Random.FRandRange(0.f, 2.f * PI);
		const FVector Dir(FMath::Cos(Ang), FMath::Sin(Ang), 0.f);
		if (FVector::DotProduct(Dir, ViewDir) > CosHidden)
		{
			continue; // na frente da câmera: o jogador veria nascer
		}
		const FVector Candidate = Player->GetActorLocation() + Dir * Random.FRandRange(MinDistance, MaxDistance);
		FNavLocation NavPoint;
		if (!Nav->ProjectPointToNavigation(Candidate, NavPoint, FVector(600.f, 600.f, 3000.f)))
		{
			continue;
		}
		// Precisa haver caminho até o jogador (não nascer atrás de um penhasco).
		const UNavigationPath* Path = Nav->FindPathToLocationSynchronously(GetWorld(), NavPoint.Location, Player->GetActorLocation());
		if (!Path || !Path->IsValid() || Path->IsPartial())
		{
			continue;
		}
		OutPoint = NavPoint.Location + FVector(0.f, 0.f, 100.f);
		return true;
	}
	return false;
}

void AJRAmbientSpawner::TrySpawnGroup()
{
	ScheduleNext();
	Spawned.RemoveAll([](const TWeakObjectPtr<AJREnemyCharacter>& E) { return !E.IsValid() || E->IsDead(); });
	const UJRObjectiveSubsystem* Objective = GetWorld()->GetSubsystem<UJRObjectiveSubsystem>();
	APawn* Player = UGameplayStatics::GetPlayerPawn(this, 0);
	if (!Objective || Objective->GetStage() != ActiveStage || !Player || EnemyClasses.Num() == 0)
	{
		return;
	}
	if (bYieldToDirector)
	{
		const AJRAIDirector* Director = AJRAIDirector::Find(this);
		if (Director && Director->IsActiveNow())
		{
			return;
		}
	}
	const int32 Want = FMath::Min(Random.RandRange(MinGroup, FMath::Max(MinGroup, MaxGroup)), MaxAlive - Spawned.Num());
	if (Want <= 0)
	{
		return;
	}
	FVector Point;
	if (!FindSpawnPoint(Player, Point))
	{
		return;
	}
	for (int32 i = 0; i < Want; ++i)
	{
		const TSubclassOf<AJREnemyCharacter> Cls = EnemyClasses[Random.RandRange(0, EnemyClasses.Num() - 1)];
		if (!Cls)
		{
			continue;
		}
		FActorSpawnParameters Params;
		Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AdjustIfPossibleButAlwaysSpawn;
		const FVector Offset(Random.FRandRange(-250.f, 250.f), Random.FRandRange(-250.f, 250.f), 0.f);
		const FRotator Face = (Player->GetActorLocation() - Point).Rotation();
		if (AJREnemyCharacter* Enemy = GetWorld()->SpawnActor<AJREnemyCharacter>(Cls, Point + Offset, FRotator(0.f, Face.Yaw, 0.f), Params))
		{
			Enemy->SetForceAggro(true);
			Spawned.Add(Enemy);
		}
	}
}

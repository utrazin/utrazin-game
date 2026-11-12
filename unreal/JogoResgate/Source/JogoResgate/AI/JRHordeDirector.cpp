// Copyright utrazin. All Rights Reserved.

#include "AI/JRHordeDirector.h"
#include "AI/JREnemyCharacter.h"
#include "Camera/PlayerCameraManager.h"
#include "Components/BoxComponent.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "JogoResgate.h"
#include "Kismet/GameplayStatics.h"
#include "Levels/JRObjectiveSubsystem.h"
#include "TimerManager.h"

AJRHordeDirector::AJRHordeDirector()
{
	PrimaryActorTick.bCanEverTick = false;
	ActivationTrigger = CreateDefaultSubobject<UBoxComponent>(TEXT("ActivationTrigger"));
	ActivationTrigger->SetBoxExtent(FVector(1500.f, 1500.f, 500.f));
	ActivationTrigger->SetCollisionProfileName(TEXT("Trigger"));
	RootComponent = ActivationTrigger;
}

void AJRHordeDirector::BeginPlay()
{
	Super::BeginPlay();
	ActivationTrigger->OnComponentBeginOverlap.AddDynamic(this, &AJRHordeDirector::HandleTriggerOverlap);
}

void AJRHordeDirector::HandleTriggerOverlap(UPrimitiveComponent* OverlappedComponent, AActor* OtherActor,
	UPrimitiveComponent* OtherComp, int32 OtherBodyIndex, bool bFromSweep, const FHitResult& SweepResult)
{
	const APawn* Pawn = Cast<APawn>(OtherActor);
	if (Pawn && Pawn->IsPlayerControlled())
	{
		StartHorde();
	}
}

void AJRHordeDirector::StartHorde()
{
	if (bRunning || bCompleted)
	{
		return;
	}
	if (Waves.Num() == 0 || SpawnPoints.Num() == 0)
	{
		UE_LOG(LogJR, Error, TEXT("%s: horda sem ondas ou pontos de spawn"), *GetName());
		return;
	}
	bRunning = true;
	if (bIsFinalHorde)
	{
		if (UJRObjectiveSubsystem* Objective = GetWorld()->GetSubsystem<UJRObjectiveSubsystem>())
		{
			Objective->SetStage(EJRLevelStage::FinalHorde);
		}
	}
	BeginWave(0);
}

void AJRHordeDirector::BeginWave(int32 WaveIndex)
{
	CurrentWave = WaveIndex;
	UE_LOG(LogJR, Log, TEXT("Horda: onda %d de %d"), WaveIndex + 1, Waves.Num());
	SpawnedInWave = 0;
	OnWaveStarted.Broadcast(WaveIndex, Waves.Num());
	GetWorldTimerManager().SetTimer(SpawnTimer, this, &AJRHordeDirector::SpawnTick,
		FMath::Max(0.05f, Waves[WaveIndex].SpawnInterval), true, 0.f);
}

bool AJRHordeDirector::IsSpawnPointValid(const AActor* Point) const
{
	if (!Point)
	{
		return false;
	}
	const APlayerController* PC = UGameplayStatics::GetPlayerController(this, 0);
	const APawn* Player = PC ? PC->GetPawn() : nullptr;
	if (!Player)
	{
		return true;
	}
	const FVector Location = Point->GetActorLocation();
	if (FVector::Dist(Location, Player->GetActorLocation()) < MinSpawnDistance)
	{
		return false;
	}
	// Fora da visão: atrás da câmera/fora do FOV, ou com linha de visão bloqueada.
	FVector CamLocation;
	FRotator CamRotation;
	PC->GetPlayerViewPoint(CamLocation, CamRotation);
	const FVector ToPoint = (Location - CamLocation).GetSafeNormal();
	const float HalfFovCos = FMath::Cos(FMath::DegreesToRadians(PC->PlayerCameraManager ? PC->PlayerCameraManager->GetFOVAngle() * 0.5f + 10.f : 55.f));
	if (FVector::DotProduct(CamRotation.Vector(), ToPoint) < HalfFovCos)
	{
		return true;
	}
	FHitResult Hit;
	FCollisionQueryParams Params(SCENE_QUERY_STAT(JRHordeSpawnVisibility), false, Player);
	Params.AddIgnoredActor(Point);
	return GetWorld()->LineTraceSingleByChannel(Hit, CamLocation, Location + FVector(0.f, 0.f, 100.f), ECC_Visibility, Params);
}

void AJRHordeDirector::SpawnTick()
{
	const FJRWave& Wave = Waves[CurrentWave];
	Alive.RemoveAll([](const TWeakObjectPtr<AJREnemyCharacter>& W) { return !W.IsValid() || W->IsDead(); });
	if (SpawnedInWave >= Wave.Count)
	{
		GetWorldTimerManager().ClearTimer(SpawnTimer);
		CheckWaveFinished();
		return;
	}
	if (Alive.Num() >= MaxAlive || !Wave.EnemyClass)
	{
		return;
	}

	TArray<AActor*> Candidates;
	for (AActor* Point : SpawnPoints)
	{
		if (IsSpawnPointValid(Point))
		{
			Candidates.Add(Point);
		}
	}
	if (Candidates.Num() == 0)
	{
		UE_LOG(LogJR, Verbose, TEXT("Horda: nenhum ponto de spawn válido agora (todos à vista ou perto demais)"));
		return; // tenta de novo no próximo tick: nunca spawna à vista
	}
	const AActor* Point = Candidates[FMath::RandRange(0, Candidates.Num() - 1)];
	FActorSpawnParameters Params;
	Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AdjustIfPossibleButDontSpawnIfColliding;
	if (AJREnemyCharacter* Enemy = GetWorld()->SpawnActor<AJREnemyCharacter>(Wave.EnemyClass, Point->GetActorTransform(), Params))
	{
		Enemy->OnEnemyDied.AddDynamic(this, &AJRHordeDirector::HandleEnemyDied);
		Alive.Add(Enemy);
		++SpawnedInWave;
		UE_LOG(LogJR, Log, TEXT("Horda onda %d: spawn %d/%d (%s) em %s"), CurrentWave + 1, SpawnedInWave, Wave.Count,
			*Enemy->GetName(), *Point->GetName());
	}
	else
	{
		UE_LOG(LogJR, Warning, TEXT("Horda: SpawnActor falhou em %s (colisão?)"), *Point->GetName());
	}
}

void AJRHordeDirector::HandleEnemyDied(AJREnemyCharacter* Enemy)
{
	Alive.Remove(Enemy);
	CheckWaveFinished();
}

void AJRHordeDirector::CheckWaveFinished()
{
	if (!bRunning || CurrentWave == INDEX_NONE || SpawnedInWave < Waves[CurrentWave].Count)
	{
		return;
	}
	Alive.RemoveAll([](const TWeakObjectPtr<AJREnemyCharacter>& W) { return !W.IsValid() || W->IsDead(); });
	if (Alive.Num() > 0 || GetWorldTimerManager().IsTimerActive(NextWaveTimer))
	{
		return;
	}
	const int32 Next = CurrentWave + 1;
	if (Next >= Waves.Num())
	{
		bRunning = false;
		bCompleted = true;
		OnHordeCompleted.Broadcast();
		if (bIsFinalHorde)
		{
			if (UJRObjectiveSubsystem* Objective = GetWorld()->GetSubsystem<UJRObjectiveSubsystem>())
			{
				Objective->SetStage(EJRLevelStage::Rescue);
			}
		}
		return;
	}
	FTimerDelegate Delegate = FTimerDelegate::CreateUObject(this, &AJRHordeDirector::BeginWave, Next);
	GetWorldTimerManager().SetTimer(NextWaveTimer, Delegate, FMath::Max(0.01f, Waves[CurrentWave].DelayAfterWave), false);
}

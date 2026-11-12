// Copyright utrazin. All Rights Reserved.

#include "AI/JREnemyBudgetSubsystem.h"
#include "AI/JREnemyCharacter.h"
#include "Engine/World.h"
#include "Kismet/GameplayStatics.h"
#include "TimerManager.h"

bool UJREnemyBudgetSubsystem::DoesSupportWorldType(const EWorldType::Type WorldType) const
{
	return WorldType == EWorldType::Game || WorldType == EWorldType::PIE;
}

void UJREnemyBudgetSubsystem::OnWorldBeginPlay(UWorld& InWorld)
{
	Super::OnWorldBeginPlay(InWorld);
	InWorld.GetTimerManager().SetTimer(RebalanceTimer, this, &UJREnemyBudgetSubsystem::Rebalance, RebalanceInterval, true);
}

void UJREnemyBudgetSubsystem::Deinitialize()
{
	if (UWorld* World = GetWorld())
	{
		World->GetTimerManager().ClearTimer(RebalanceTimer);
	}
	Enemies.Reset();
	Super::Deinitialize();
}

void UJREnemyBudgetSubsystem::RegisterEnemy(AJREnemyCharacter* Enemy)
{
	if (Enemy)
	{
		Enemies.AddUnique(Enemy);
		// Liga o "cérebro" já no registro (mesmo sem jogador ainda); o rebalanceamento ajusta depois.
		Enemy->SetFullUpdate(Enemies.Num() <= MaxFullUpdateEnemies);
		Rebalance();
	}
}

void UJREnemyBudgetSubsystem::UnregisterEnemy(AJREnemyCharacter* Enemy)
{
	Enemies.Remove(Enemy);
}

void UJREnemyBudgetSubsystem::SetMaxFullUpdateEnemies(int32 NewMax)
{
	MaxFullUpdateEnemies = FMath::Max(1, NewMax);
	Rebalance();
}

int32 UJREnemyBudgetSubsystem::GetAliveEnemyCount() const
{
	int32 Count = 0;
	for (const TWeakObjectPtr<AJREnemyCharacter>& Weak : Enemies)
	{
		Count += (Weak.IsValid() && !Weak->IsDead()) ? 1 : 0;
	}
	return Count;
}

void UJREnemyBudgetSubsystem::Rebalance()
{
	Enemies.RemoveAll([](const TWeakObjectPtr<AJREnemyCharacter>& Weak) { return !Weak.IsValid() || Weak->IsDead(); });
	const APawn* Player = UGameplayStatics::GetPlayerPawn(this, 0);
	if (!Player)
	{
		return;
	}
	const FVector PlayerLocation = Player->GetActorLocation();
	Enemies.Sort([&PlayerLocation](const TWeakObjectPtr<AJREnemyCharacter>& A, const TWeakObjectPtr<AJREnemyCharacter>& B)
	{
		return FVector::DistSquared(A->GetActorLocation(), PlayerLocation) < FVector::DistSquared(B->GetActorLocation(), PlayerLocation);
	});
	for (int32 i = 0; i < Enemies.Num(); ++i)
	{
		Enemies[i]->SetFullUpdate(i < MaxFullUpdateEnemies);
	}
}

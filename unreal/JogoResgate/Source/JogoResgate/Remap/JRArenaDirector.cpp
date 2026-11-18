// Copyright utrazin. All Rights Reserved.

#include "Remap/JRArenaDirector.h"
#include "AI/JREnemyCharacter.h"
#include "Camera/PlayerCameraManager.h"
#include "Characters/JRCharacter.h"
#include "Combat/JRHealthComponent.h"
#include "Combat/JRWeaponComponent.h"
#include "Engine/World.h"
#include "Engine/Engine.h"
#include "EngineUtils.h"
#include "GameFramework/PlayerController.h"
#include "JogoResgate.h"
#include "Kismet/GameplayStatics.h"
#include "NavigationSystem.h"
#include "Remap/JRExtractionShip.h"
#include "Remap/JRRemapTypes.h"
#include "Remap/JRRunSubsystem.h"
#include "TimerManager.h"
#include "UI/JRHUD.h"

AJRArenaDirector::AJRArenaDirector()
{
	PrimaryActorTick.bCanEverTick = true;
	PrimaryActorTick.TickInterval = 0.f;
	ShipClass = AJRExtractionShip::StaticClass();

	auto Add = [this](const TCHAR* Path, int32 Cost, int32 FirstWave, float Chance)
	{
		FJRArenaEnemy E;
		E.EnemyClass = TSoftClassPtr<AJREnemyCharacter>(FSoftClassPath(Path));
		E.Cost = Cost;
		E.FirstWave = FirstWave;
		E.Chance = Chance;
		Enemies.Add(E);
	};
	Add(TEXT("/Game/Enemies/BP_Enemy_ZombieMelee.BP_Enemy_ZombieMelee_C"), 1, 1, 0.f);
	Add(TEXT("/Game/Enemies/BP_Enemy_ZombieArcher.BP_Enemy_ZombieArcher_C"), 3, 3, 0.18f);
	Add(TEXT("/Game/Enemies/BP_Enemy_ZombieGunner.BP_Enemy_ZombieGunner_C"), 4, 5, 0.12f);
	Add(TEXT("/Game/Enemies/BP_Enemy_ZombieElite.BP_Enemy_ZombieElite_C"), 6, 5, 0.f);
}

AJRArenaDirector* AJRArenaDirector::FindInWorld(const UObject* WorldContext)
{
	const UWorld* World = GEngine ? GEngine->GetWorldFromContextObject(WorldContext, EGetWorldErrorMode::ReturnNull) : nullptr;
	if (!World)
	{
		return nullptr;
	}
	for (TActorIterator<AJRArenaDirector> It(World); It; ++It)
	{
		return *It;
	}
	return nullptr;
}

UJRRunSubsystem* AJRArenaDirector::GetRun() const
{
	const UGameInstance* GI = GetGameInstance();
	return GI ? GI->GetSubsystem<UJRRunSubsystem>() : nullptr;
}

AJRCharacter* AJRArenaDirector::GetHero() const
{
	return Cast<AJRCharacter>(UGameplayStatics::GetPlayerPawn(this, 0));
}

void AJRArenaDirector::BeginPlay()
{
	Super::BeginPlay();

	LoadedClasses.Reset();
	for (const FJRArenaEnemy& E : Enemies)
	{
		LoadedClasses.Add(E.EnemyClass.LoadSynchronous());
		if (!LoadedClasses.Last())
		{
			UE_LOG(LogJR, Warning, TEXT("Arena: classe de inimigo não carregou (%s)"), *E.EnemyClass.ToString());
		}
	}
	for (TActorIterator<AActor> It(GetWorld()); It; ++It)
	{
		if (It->ActorHasTag(TEXT("ArenaSpawn")))
		{
			SpawnPoints.Add(*It);
		}
		if (It->ActorHasTag(TEXT("ArenaExtracao")))
		{
			ExtractionPoints.Add(*It);
		}
	}
	UE_LOG(LogJR, Log, TEXT("Arena: %d pontos de surgimento, %d pontos de extração"), SpawnPoints.Num(), ExtractionPoints.Num());

	if (UJRRunSubsystem* Run = GetRun())
	{
		if (!Run->IsRunActive())
		{
			Run->StartRun(DefaultSectorLevel); // Play direto na arena
		}
	}
	GetWorldTimerManager().SetTimer(HeroTimer, this, &AJRArenaDirector::PrepareHero, 0.25f, true, 0.1f);
}

void AJRArenaDirector::PrepareHero()
{
	AJRCharacter* Hero = GetHero();
	if (!Hero)
	{
		return;
	}
	GetWorldTimerManager().ClearTimer(HeroTimer);
	bHeroReady = true;
	if (const UJRRunSubsystem* Run = GetRun())
	{
		Run->ApplyStatsToHero(Hero, true);
	}
	Hero->SetWeaponEquipped(true);
	BreakEndTime = GetWorld()->GetTimeSeconds() + FirstWaveDelay;
	bInBreak = true;
	AJRHUD::Toast(this, TEXT("A horda está chegando. Aguente o quanto quiser."), FLinearColor(1.f, 0.8f, 0.2f));
	GetWorldTimerManager().SetTimer(WaveTimer, FTimerDelegate::CreateUObject(this, &AJRArenaDirector::BeginWave, 1), FirstWaveDelay, false);
}

float AJRArenaDirector::GetBreakSecondsLeft() const
{
	return bInBreak ? FMath::Max(0.f, static_cast<float>(BreakEndTime - GetWorld()->GetTimeSeconds())) : 0.f;
}

void AJRArenaDirector::BeginWave(int32 WaveNumber)
{
	if (bEnded)
	{
		return;
	}
	Wave = WaveNumber;
	WaveTotal = FJRRemapRules::WaveEnemyCount(Wave);
	SpawnedInWave = 0;
	bInBreak = false;
	if (UJRRunSubsystem* Run = GetRun())
	{
		Run->SetWave(Wave);
	}
	UE_LOG(LogJR, Log, TEXT("Arena: onda %d (%d inimigos)"), Wave, WaveTotal);
	AJRHUD::Toast(this, FString::Printf(TEXT("ONDA %d"), Wave), FLinearColor(1.f, 0.35f, 0.25f));
	GetWorldTimerManager().SetTimer(SpawnTimer, this, &AJRArenaDirector::SpawnTick, FMath::Max(0.05f, SpawnInterval), true, 0.f);
}

int32 AJRArenaDirector::PickEnemyIndex(bool bForceElite) const
{
	if (bForceElite && LoadedClasses.IsValidIndex(EliteIndex) && LoadedClasses[EliteIndex])
	{
		return EliteIndex;
	}
	const float Roll = FMath::FRand();
	float Acc = 0.f;
	for (int32 i = 1; i < Enemies.Num(); ++i)
	{
		if (i == EliteIndex || Wave < Enemies[i].FirstWave || !LoadedClasses.IsValidIndex(i) || !LoadedClasses[i])
		{
			continue;
		}
		Acc += Enemies[i].Chance;
		if (Roll < Acc)
		{
			return i;
		}
	}
	return 0;
}

bool AJRArenaDirector::IsHiddenFromPlayer(const FVector& Location) const
{
	const APlayerController* PC = UGameplayStatics::GetPlayerController(this, 0);
	const APawn* Player = PC ? PC->GetPawn() : nullptr;
	if (!Player)
	{
		return true;
	}
	if (FVector::Dist(Location, Player->GetActorLocation()) < MinSpawnDistance)
	{
		return false;
	}
	FVector CamLocation;
	FRotator CamRotation;
	PC->GetPlayerViewPoint(CamLocation, CamRotation);
	const FVector ToPoint = (Location - CamLocation).GetSafeNormal();
	const float HalfFov = PC->PlayerCameraManager ? PC->PlayerCameraManager->GetFOVAngle() * 0.5f + 10.f : 55.f;
	if (FVector::DotProduct(CamRotation.Vector(), ToPoint) < FMath::Cos(FMath::DegreesToRadians(HalfFov)))
	{
		return true; // fora do campo de visão
	}
	FHitResult Hit;
	FCollisionQueryParams Params(SCENE_QUERY_STAT(JRArenaSpawnVisibility), false, Player);
	return GetWorld()->LineTraceSingleByChannel(Hit, CamLocation, Location + FVector(0.f, 0.f, 100.f), ECC_Visibility, Params);
}

bool AJRArenaDirector::PickSpawnLocation(FVector& OutLocation) const
{
	TArray<FVector> Candidates;
	for (const AActor* Point : SpawnPoints)
	{
		if (Point && IsHiddenFromPlayer(Point->GetActorLocation()))
		{
			Candidates.Add(Point->GetActorLocation());
		}
	}
	if (Candidates.Num() == 0 && SpawnPoints.Num() == 0)
	{
		// Sem pontos marcados: sorteia na navmesh em volta do diretor.
		if (const UNavigationSystemV1* Nav = FNavigationSystem::GetCurrent<UNavigationSystemV1>(GetWorld()))
		{
			for (int32 Try = 0; Try < 12; ++Try)
			{
				FNavLocation NavLoc;
				if (Nav->GetRandomReachablePointInRadius(GetActorLocation(), RandomSpawnRadius, NavLoc)
					&& IsHiddenFromPlayer(NavLoc.Location))
				{
					Candidates.Add(NavLoc.Location);
					break;
				}
			}
		}
	}
	if (Candidates.Num() == 0)
	{
		return false;
	}
	OutLocation = Candidates[FMath::RandRange(0, Candidates.Num() - 1)] + FVector(0.f, 0.f, 100.f);
	return true;
}

void AJRArenaDirector::SpawnTick()
{
	if (bEnded)
	{
		GetWorldTimerManager().ClearTimer(SpawnTimer);
		return;
	}
	Alive.RemoveAll([](const TWeakObjectPtr<AJREnemyCharacter>& W) { return !W.IsValid() || W->IsDead(); });
	if (SpawnedInWave >= WaveTotal)
	{
		if (Alive.Num() == 0)
		{
			GetWorldTimerManager().ClearTimer(SpawnTimer);
			FinishWave();
		}
		return;
	}
	if (Alive.Num() >= MaxAlive)
	{
		return;
	}
	FVector Location;
	if (!PickSpawnLocation(Location))
	{
		return; // tenta no próximo tick: nunca nasce à vista
	}
	const bool bElite = EliteIndex >= 0 && Wave % EliteEveryWaves == 0 && SpawnedInWave == WaveTotal - 1;
	const int32 Index = PickEnemyIndex(bElite);
	UClass* Class = LoadedClasses.IsValidIndex(Index) ? LoadedClasses[Index].Get() : nullptr;
	if (!Class)
	{
		Class = LoadedClasses.Num() > 0 ? LoadedClasses[0].Get() : nullptr;
	}
	if (!Class)
	{
		UE_LOG(LogJR, Error, TEXT("Arena: nenhuma classe de inimigo carregada"));
		GetWorldTimerManager().ClearTimer(SpawnTimer);
		return;
	}
	const APawn* Player = UGameplayStatics::GetPlayerPawn(this, 0);
	const FRotator Facing = Player ? (Player->GetActorLocation() - Location).GetSafeNormal2D().Rotation() : FRotator::ZeroRotator;
	FActorSpawnParameters Params;
	Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AdjustIfPossibleButDontSpawnIfColliding;
	AJREnemyCharacter* Enemy = GetWorld()->SpawnActor<AJREnemyCharacter>(Class, Location, Facing, Params);
	if (!Enemy)
	{
		return;
	}
	++SpawnedInWave;
	const UJRRunSubsystem* Run = GetRun();
	const float Level = FJRRemapRules::GetEffectiveLevel(Run ? Run->GetSectorLevel() : 1, Wave);
	if (UJRHealthComponent* Health = Enemy->FindComponentByClass<UJRHealthComponent>())
	{
		Health->SetMaxHealth(Health->GetMaxHealth() * FJRRemapRules::EnemyHealthScale(Level), true);
	}
	Enemy->SetForceAggro(true);
	Enemy->OnEnemyDied.AddDynamic(this, &AJRArenaDirector::HandleEnemyDied);
	Alive.Add(Enemy);
	CostOf.Add(Enemy, Enemies.IsValidIndex(Index) ? Enemies[Index].Cost : 1);
}

void AJRArenaDirector::HandleEnemyDied(AJREnemyCharacter* Enemy)
{
	const int32* CostPtr = CostOf.Find(Enemy);
	const int32 Cost = CostPtr ? *CostPtr : 1;
	CostOf.Remove(Enemy);
	Alive.Remove(Enemy);
	UJRRunSubsystem* Run = GetRun();
	if (!Run || bEnded)
	{
		return;
	}
	Run->RegisterKill(Cost, FJRRemapRules::GetEffectiveLevel(Run->GetSectorLevel(), Wave));
	if (Run->GetStats().LifeOnKill > 0.f)
	{
		if (AJRCharacter* Hero = GetHero())
		{
			if (UJRHealthComponent* Health = Hero->GetHealthComponent())
			{
				Health->Heal(Health->GetMaxHealth() * Run->GetStats().LifeOnKill);
			}
		}
	}
}

void AJRArenaDirector::FinishWave()
{
	if (bEnded)
	{
		return;
	}
	UJRRunSubsystem* Run = GetRun();
	if (Run)
	{
		Run->MarkWaveCleared(Wave);
	}
	if (AJRCharacter* Hero = GetHero())
	{
		if (UJRWeaponComponent* Weapon = Hero->GetWeaponComponent())
		{
			Weapon->AddReserveAmmo(AmmoPerWave + 5 * Wave);
		}
	}
	UE_LOG(LogJR, Log, TEXT("Arena: onda %d vencida"), Wave);
	if (Wave % ExtractionEveryWaves == 0)
	{
		SpawnShip();
	}
	else
	{
		AJRHUD::Toast(this, FString::Printf(TEXT("Onda %d vencida!"), Wave), FLinearColor(0.4f, 1.f, 0.6f));
	}
	bInBreak = true;
	BreakEndTime = GetWorld()->GetTimeSeconds() + BreakBetweenWaves;
	GetWorldTimerManager().SetTimer(WaveTimer, FTimerDelegate::CreateUObject(this, &AJRArenaDirector::BeginWave, Wave + 1),
		BreakBetweenWaves, false);
}

void AJRArenaDirector::SpawnShip()
{
	if (ActiveShip.IsValid() || !ShipClass)
	{
		return;
	}
	FVector Location = GetActorLocation();
	const APawn* Player = UGameplayStatics::GetPlayerPawn(this, 0);
	if (ExtractionPoints.Num() > 0)
	{
		// O ponto mais longe do herói entre 2 sorteados: obriga a atravessar a arena.
		const AActor* A = ExtractionPoints[FMath::RandRange(0, ExtractionPoints.Num() - 1)];
		const AActor* B = ExtractionPoints[FMath::RandRange(0, ExtractionPoints.Num() - 1)];
		const AActor* Pick = A;
		if (Player && B && FVector::DistSquared(B->GetActorLocation(), Player->GetActorLocation())
			> FVector::DistSquared(A->GetActorLocation(), Player->GetActorLocation()))
		{
			Pick = B;
		}
		Location = Pick->GetActorLocation();
	}
	else if (const UNavigationSystemV1* Nav = FNavigationSystem::GetCurrent<UNavigationSystemV1>(GetWorld()))
	{
		FNavLocation NavLoc;
		if (Nav->GetRandomReachablePointInRadius(GetActorLocation(), RandomSpawnRadius * 0.7f, NavLoc))
		{
			Location = NavLoc.Location;
		}
	}
	const UJRRunSubsystem* Run = GetRun();
	const float Mult = FJRRemapRules::ExtractionMultiplier(Run ? Run->GetWavesCleared() : Wave);
	FActorSpawnParameters Params;
	Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
	AJRExtractionShip* Ship = GetWorld()->SpawnActor<AJRExtractionShip>(ShipClass, Location + FVector(0.f, 0.f, 350.f),
		FRotator::ZeroRotator, Params);
	if (Ship)
	{
		ActiveShip = Ship;
		Ship->Activate(this, ExtractionSeconds, Mult);
		AJRHUD::Toast(this, FString::Printf(TEXT("NAVE DE EXTRAÇÃO! %.0f s para embarcar (x%.2f)"), ExtractionSeconds, Mult),
			FLinearColor(0.3f, 0.95f, 1.f));
	}
}

void AJRArenaDirector::HandleShipLeft(AJRExtractionShip* Ship)
{
	if (ActiveShip.Get() == Ship)
	{
		ActiveShip.Reset();
	}
	if (!bEnded)
	{
		AJRHUD::Toast(this, TEXT("A nave foi embora. A próxima paga mais."), FLinearColor(1.f, 0.7f, 0.3f));
	}
}

void AJRArenaDirector::Extract(float Multiplier)
{
	if (bEnded)
	{
		return;
	}
	if (UJRRunSubsystem* Run = GetRun())
	{
		Run->EndRun(true, Multiplier);
	}
	StopArena();
	if (AJRCharacter* Hero = GetHero())
	{
		if (UJRHealthComponent* Health = Hero->GetHealthComponent())
		{
			Health->SetInvulnerableFor(999.f);
		}
		if (APlayerController* PC = Cast<APlayerController>(Hero->GetController()))
		{
			Hero->DisableInput(PC);
		}
	}
	AJRHUD::Toast(this, TEXT("EXTRAÇÃO! Voltando para Villa Star..."), FLinearColor(0.3f, 0.95f, 1.f));
	GetWorldTimerManager().SetTimer(ExitTimer, this, &AJRArenaDirector::ReturnToCity, 2.5f, false);
}

void AJRArenaDirector::StopArena()
{
	bEnded = true;
	GetWorldTimerManager().ClearTimer(SpawnTimer);
	GetWorldTimerManager().ClearTimer(WaveTimer);
	if (bChoiceOpen)
	{
		UGameplayStatics::SetGlobalTimeDilation(this, 1.f);
		bChoiceOpen = false;
	}
	for (const TWeakObjectPtr<AJREnemyCharacter>& W : Alive)
	{
		if (AJREnemyCharacter* E = W.Get())
		{
			E->SetForceAggro(false);
		}
	}
}

void AJRArenaDirector::ReturnToCity()
{
	UGameplayStatics::OpenLevel(this, FName(FJRRemapRules::CityMap));
}

void AJRArenaDirector::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	if (bEnded || !bHeroReady || bChoiceOpen)
	{
		return;
	}
	const UJRRunSubsystem* Run = GetRun();
	if (Run && Run->WantsCardChoice())
	{
		OpenCardChoice();
	}
}

void AJRArenaDirector::OpenCardChoice()
{
	UJRRunSubsystem* Run = GetRun();
	AJRCharacter* Hero = GetHero();
	if (!Run || !Hero)
	{
		return;
	}
	bChoiceOpen = true;
	Run->BeginCardChoice();
	if (UJRWeaponComponent* Weapon = Hero->GetWeaponComponent())
	{
		Weapon->StopFire();
	}
	if (APlayerController* PC = Cast<APlayerController>(Hero->GetController()))
	{
		Hero->DisableInput(PC);
	}
	// "Congela" o jogo (pausa de verdade bloquearia a HUD de ler as teclas).
	UGameplayStatics::SetGlobalTimeDilation(this, 0.0001f);
	Hero->PlayFeedback(0.35f, 0.f, 4.f);
}

void AJRArenaDirector::ConfirmCard(int32 Index)
{
	UJRRunSubsystem* Run = GetRun();
	if (!bChoiceOpen || !Run)
	{
		return;
	}
	const EJRRunCard Card = Run->PickCard(Index);
	if (Card == EJRRunCard::Count)
	{
		return;
	}
	bChoiceOpen = false;
	UGameplayStatics::SetGlobalTimeDilation(this, 1.f);
	AJRCharacter* Hero = GetHero();
	if (!Hero)
	{
		return;
	}
	if (APlayerController* PC = Cast<APlayerController>(Hero->GetController()))
	{
		Hero->EnableInput(PC);
	}
	Run->ApplyStatsToHero(Hero, false);
	if (UJRHealthComponent* Health = Hero->GetHealthComponent())
	{
		if (Card == EJRRunCard::HealNow)
		{
			Health->Heal(Health->GetMaxHealth() * 0.5f);
		}
		Health->SetInvulnerableFor(InvulnerableAfterCard);
	}
	Shockwave(Hero);
	AJRHUD::Toast(this, FString::Printf(TEXT("%s: %s"), *FJRRemapRules::CardTitle(Card).ToString(),
		*FJRRemapRules::CardDescription(Card).ToString()), FLinearColor(0.75f, 0.55f, 1.f));
}

void AJRArenaDirector::Shockwave(AJRCharacter* Hero)
{
	const FVector Origin = Hero->GetActorLocation();
	AController* InstigatorController = Hero->GetController();
	for (const TWeakObjectPtr<AJREnemyCharacter>& W : Alive)
	{
		AJREnemyCharacter* E = W.Get();
		if (!E || E->IsDead())
		{
			continue;
		}
		const FVector Delta = E->GetActorLocation() - Origin;
		const float Dist = Delta.Size();
		if (Dist > ShockwaveRadius)
		{
			continue;
		}
		const float Falloff = 1.f - 0.6f * (Dist / ShockwaveRadius);
		E->LaunchCharacter(Delta.GetSafeNormal2D() * 1100.f * Falloff + FVector(0.f, 0.f, 380.f), true, true);
		UGameplayStatics::ApplyDamage(E, ShockwaveDamage * Falloff, InstigatorController, Hero, nullptr);
	}
	Hero->PlayFeedback(0.8f, 0.06f, 8.f);
}

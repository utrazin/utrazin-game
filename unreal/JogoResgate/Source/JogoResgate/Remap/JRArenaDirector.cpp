// Copyright utrazin. All Rights Reserved.

#include "Remap/JRArenaDirector.h"
#include "AI/JREnemyCharacter.h"
#include "Audio/JRAudio.h"
#include "Camera/PlayerCameraManager.h"
#include "Characters/JRCharacter.h"
#include "Combat/JRHealthComponent.h"
#include "Combat/JRWeaponComponent.h"
#include "Components/PointLightComponent.h"
#include "Engine/Engine.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "FX/JRFXSubsystem.h"
#include "GameFramework/PlayerController.h"
#include "JogoResgate.h"
#include "Kismet/GameplayStatics.h"
#include "NavigationSystem.h"
#include "Remap/JRArenaGenerator.h"
#include "Remap/JRArenaInteractives.h"
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

	auto AddEnemy = [this](const TCHAR* InLabel, const TCHAR* ClassPath, int32 InCost, int32 InFirstWave, float InWeight,
		int32 InGroupMin, int32 InGroupMax, float InHealth, float InPace, float InScale)
	{
		FJRArenaEnemy E;
		E.Label = InLabel;
		E.EnemyClass = TSoftClassPtr<AJREnemyCharacter>(FSoftClassPath(ClassPath));
		E.Cost = InCost;
		E.FirstWave = InFirstWave;
		E.Weight = InWeight;
		E.GroupMin = InGroupMin;
		E.GroupMax = InGroupMax;
		E.HealthMultiplier = InHealth;
		E.Pace = InPace;
		E.Scale = InScale;
		Enemies.Add(E);
	};
	// REMAP 6.3: comum 1, corredor 2, arqueiro 3, atirador 4, tanque 8 (elite de qualquer um = x6).
	// O corredor é o zumbi comum mais rápido (ritmo 1,35) e com menos vida: não existe BP próprio ainda.
	AddEnemy(TEXT("Comum"), TEXT("/Game/Enemies/BP_Enemy_ZombieMelee.BP_Enemy_ZombieMelee_C"), 1, 1, 10.f, 3, 5, 1.f, 1.f, 1.f);
	AddEnemy(TEXT("Corredor"), TEXT("/Game/Enemies/BP_Enemy_ZombieMelee.BP_Enemy_ZombieMelee_C"), 2, 2, 5.f, 2, 4, 0.7f, 1.35f, 0.95f);
	AddEnemy(TEXT("Arqueiro"), TEXT("/Game/Enemies/BP_Enemy_ZombieArcher.BP_Enemy_ZombieArcher_C"), 3, 3, 4.f, 1, 3, 1.f, 1.f, 1.f);
	AddEnemy(TEXT("Atirador"), TEXT("/Game/Enemies/BP_Enemy_ZombieGunner.BP_Enemy_ZombieGunner_C"), 4, 5, 3.f, 1, 2, 1.f, 1.f, 1.f);
	AddEnemy(TEXT("Tanque"), TEXT("/Game/Enemies/BP_Enemy_ZombieElite.BP_Enemy_ZombieElite_C"), 8, 6, 1.5f, 1, 1, 1.6f, 0.9f, 1.15f);
}

AJRArenaDirector* AJRArenaDirector::FindInWorld(const UObject* WorldContext)
{
	const UWorld* Wld = GEngine ? GEngine->GetWorldFromContextObject(WorldContext, EGetWorldErrorMode::ReturnNull) : nullptr;
	if (!Wld)
	{
		return nullptr;
	}
	for (TActorIterator<AJRArenaDirector> It(Wld); It; ++It)
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

int32 AJRArenaDirector::GetSectorLevelSafe() const
{
	const UJRRunSubsystem* Run = GetRun();
	return Run ? FMath::Max(1, Run->GetSectorLevel()) : FMath::Max(1, DefaultSectorLevel);
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

	// A corrida começa antes do gerador: ele lê o nível do setor dela.
	if (UJRRunSubsystem* Run = GetRun())
	{
		if (!Run->IsRunActive())
		{
			Run->StartRun(DefaultSectorLevel); // Play direto na arena
		}
	}

	if (AJRArenaGenerator* Gen = AJRArenaGenerator::FindInWorld(this))
	{
		Generator = Gen;
		Gen->EnsureBuilt();
		SpawnSpots = Gen->GetSpawnPoints();
		ExtractionSpots = Gen->GetExtractionPoints();
		ObjectiveSpots = Gen->GetObjectivePoints();
	}
	if (SpawnSpots.Num() == 0 || ExtractionSpots.Num() == 0)
	{
		// Arena fixa do F1 (sem gerador): pontos marcados por tag.
		for (TActorIterator<AActor> It(GetWorld()); It; ++It)
		{
			if (SpawnSpots.Num() == 0 && It->ActorHasTag(TEXT("ArenaSpawn")))
			{
				SpawnSpots.Add(It->GetActorLocation());
			}
			if (ExtractionSpots.Num() == 0 && It->ActorHasTag(TEXT("ArenaExtracao")))
			{
				ExtractionSpots.Add(It->GetActorLocation());
			}
		}
	}
	UE_LOG(LogJR, Log, TEXT("Arena: %d pontos de surgimento, %d pontos de extração, %d pontos de objetivo"),
		SpawnSpots.Num(), ExtractionSpots.Num(), ObjectiveSpots.Num());

	SetupObjectives();
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
	// O PlayerStart deve ficar no gerador; se alguém mexeu, leva o herói para o centro livre.
	if (const AJRArenaGenerator* Gen = Generator.Get())
	{
		const FVector StartPoint = Gen->GetPlayerStartPoint();
		if (FVector::Dist2D(StartPoint, Hero->GetActorLocation()) > 400.f)
		{
			Hero->TeleportTo(StartPoint + FVector(0.f, 0.f, 120.f), Hero->GetActorRotation());
		}
	}
	if (const UJRRunSubsystem* Run = GetRun())
	{
		Run->ApplyStatsToHero(Hero, true);
	}
	Hero->SetWeaponEquipped(true);
	if (UJRHealthComponent* Health = Hero->GetHealthComponent())
	{
		Health->OnHealthChanged.AddUniqueDynamic(this, &AJRArenaDirector::HandleHeroHealthChanged);
	}
	SpawnNests();

	FString Intro = TEXT("A horda está chegando. Aguente o quanto quiser.");
	if (const AJRArenaGenerator* Gen = Generator.Get())
	{
		Intro = FString::Printf(TEXT("%s. A horda está chegando."), *Gen->GetThemeName());
		// [A-085] semente e tamanho só no log (era texto de depuração na tela do jogador)
		UE_LOG(LogJR, Log, TEXT("Arena: %s, %s, %d m, semente %d"), *Gen->GetThemeName(), *Gen->GetShapeName(),
			Gen->GetArenaMeters(), Gen->GetSeed());
	}
	AJRHUD::Toast(this, Intro, FLinearColor(1.f, 0.8f, 0.2f));
	if (OptionalObjective.Type != EJRArenaObjective::None)
	{
		AJRHUD::Toast(this, DescribeObjective(OptionalObjective), FLinearColor(0.55f, 1.f, 0.55f));
	}
	BreakEndTime = GetWorld()->GetTimeSeconds() + FirstWaveDelay;
	bInBreak = true;
	GetWorldTimerManager().SetTimer(WaveTimer, FTimerDelegate::CreateUObject(this, &AJRArenaDirector::BeginWave, 1), FirstWaveDelay, false);
}

float AJRArenaDirector::GetBreakSecondsLeft() const
{
	return bInBreak ? FMath::Max(0.f, static_cast<float>(BreakEndTime - GetWorld()->GetTimeSeconds())) : 0.f;
}

int32 AJRArenaDirector::RemainingWaveBudget() const
{
	return FMath::Max(0, WaveBudget - WaveSpent);
}

int32 AJRArenaDirector::CostOfEntry(int32 EnemyIndex, bool bElite) const
{
	const int32 Base = Enemies.IsValidIndex(EnemyIndex) ? FMath::Max(1, Enemies[EnemyIndex].Cost) : 1;
	return bElite ? Base * FMath::Max(1, EliteCostMultiplier) : Base;
}

int32 AJRArenaDirector::GetEnemiesLeftInWave() const
{
	if (bInBreak)
	{
		return Alive.Num();
	}
	// O que falta comprar vira "inimigos" pela média de custo (~1,6): só uma estimativa para a HUD.
	return Alive.Num() + Pending.Num() + FMath::CeilToInt(RemainingWaveBudget() / 1.6f);
}

// ============================================================================ ondas e ritmo

void AJRArenaDirector::BeginWave(int32 WaveNumber)
{
	if (bEnded)
	{
		return;
	}
	Wave = WaveNumber;
	const int32 Level = GetSectorLevelSafe();
	WaveBudget = FJRRemapRules::DirectorWaveBudget(Wave, Level);
	WaveSpent = 0;
	Wallet = WaveBudget * WaveStartWallet;
	PlannedPick = INDEX_NONE; // [A-098]
	PlannedCount = 0;
	bTankThisWave = false;
	PeakCost = FJRRemapRules::DirectorPeakCost(Wave);
	Pacing = EJRArenaPacing::BuildUp;
	GroupsThisWave = 0;
	LastDirectorTime = GetWorld()->GetTimeSeconds();
	bInBreak = false;
	if (UJRRunSubsystem* Run = GetRun())
	{
		Run->SetWave(Wave);
	}

	// Elite marcado do objetivo opcional: de graça, fora do orçamento.
	if (OptionalObjective.Type == EJRArenaObjective::KillMarkedElite && !OptionalObjective.bDone && !bMarkedEliteSpawned
		&& Wave >= MarkedEliteWave)
	{
		FJRArenaPendingSpawn Entry;
		Entry.EnemyIndex = LoadedClasses.IsValidIndex(2) && LoadedClasses[2] && Wave >= 3 ? 2 : 0;
		Entry.bElite = true;
		Entry.bMarked = true;
		Pending.Add(Entry);
		bMarkedEliteSpawned = true;
	}

	UE_LOG(LogJR, Log, TEXT("Arena: onda %d (orçamento %d, pico %d)"), Wave, WaveBudget, PeakCost);
	AJRHUD::Toast(this, FString::Printf(TEXT("ONDA %d"), Wave), FLinearColor(1.f, 0.35f, 0.25f));
	UJRAudio::Play2D(this, TEXT("Zombie.Horde"), 0.8f);
	UJRAudio::PlayMusic(this, TEXT("Music.Horde"), 1.5f);
	GetWorldTimerManager().SetTimer(SpawnTimer, this, &AJRArenaDirector::DirectorTick, FMath::Max(0.05f, DirectorInterval), true, 0.f);
}

void AJRArenaDirector::DirectorTick()
{
	if (bEnded)
	{
		GetWorldTimerManager().ClearTimer(SpawnTimer);
		return;
	}
	Alive.RemoveAll([](const TWeakObjectPtr<AJREnemyCharacter>& W) { return !W.IsValid() || W->IsDead(); });

	const double Now = GetWorld()->GetTimeSeconds();
	const float Dt = static_cast<float>(FMath::Max(0.0, Now - LastDirectorTime));
	LastDirectorTime = Now;
	const int32 Level = GetSectorLevelSafe();

	// 1) Renda do diretor (mais rápida em nível alto e em ondas altas). Nunca passa do que sobra do orçamento.
	Wallet = FMath::Min(Wallet + Dt * FJRRemapRules::DirectorIncomePerSecond(Wave, Level), static_cast<float>(RemainingWaveBudget()));

	// 2) Fila: nasce um por vez (dá o efeito de "chegando aos poucos").
	if (Pending.Num() > 0 && Alive.Num() < MaxAlive)
	{
		FJRArenaPendingSpawn Entry = Pending[0];
		Pending.RemoveAt(0);
		if (!SpawnPending(Entry))
		{
			++Entry.Fails;
			if (Entry.Fails < 25)
			{
				Pending.Add(Entry); // tenta de novo depois: nunca nasce à vista
			}
		}
	}

	// 3) Ritmo de tensão: junta até o pico, espera baixar, respira.
	int32 PressureCost = 0;
	for (const TWeakObjectPtr<AJREnemyCharacter>& W : Alive)
	{
		const int32* CostPtr = CostOf.Find(W);
		PressureCost += CostPtr ? *CostPtr : 1;
	}
	for (const FJRArenaPendingSpawn& P : Pending)
	{
		PressureCost += CostOfEntry(P.EnemyIndex, P.bElite);
	}
	switch (Pacing)
	{
	case EJRArenaPacing::BuildUp:
		if (PressureCost >= PeakCost)
		{
			Pacing = EJRArenaPacing::Peak;
		}
		else if (Alive.Num() + Pending.Num() < MaxAlive)
		{
			TryBuyGroup();
		}
		break;
	case EJRArenaPacing::Peak:
		if (PressureCost <= FMath::CeilToInt(PeakCost * 0.35f))
		{
			float Breath = RelaxSeconds;
			const AJRCharacter* Hero = GetHero();
			const UJRHealthComponent* HeroHealth = Hero ? Hero->GetHealthComponent() : nullptr;
			if (HeroHealth && HeroHealth->GetHealthNormalized() < 0.4f)
			{
				Breath += MercySeconds; // herói machucado: respiro maior
			}
			RelaxEndTime = Now + Breath;
			Pacing = EJRArenaPacing::Relax;
		}
		break;
	default:
		if (Now >= RelaxEndTime)
		{
			Pacing = EJRArenaPacing::BuildUp;
		}
		break;
	}

	// 4) Objetivo de combo (o combo sobe no RegisterKill e zera ao levar dano).
	if (OptionalObjective.Type == EJRArenaObjective::Combo && !OptionalObjective.bDone)
	{
		if (const UJRRunSubsystem* Run = GetRun())
		{
			OptionalObjective.Progress = Run->GetMaxCombo();
			if (OptionalObjective.Progress >= OptionalObjective.Target)
			{
				CompleteObjective(OptionalObjective);
			}
		}
	}

	// 5) Fim da onda: nada mais para comprar, fila vazia, ninguém vivo.
	int32 Cheapest = MAX_int32;
	for (int32 i = 0; i < Enemies.Num(); ++i)
	{
		if (LoadedClasses.IsValidIndex(i) && LoadedClasses[i] && Wave >= Enemies[i].FirstWave)
		{
			Cheapest = FMath::Min(Cheapest, FMath::Max(1, Enemies[i].Cost));
		}
	}
	if (Cheapest == MAX_int32)
	{
		Cheapest = 1;
	}
	if (RemainingWaveBudget() < Cheapest && Pending.Num() == 0 && Alive.Num() == 0)
	{
		GetWorldTimerManager().ClearTimer(SpawnTimer);
		FinishWave();
	}
}

bool AJRArenaDirector::TryBuyGroup()
{
	// [A-098] 1) escolhe o próximo grupo pelo que SOBRA da onda (não pelo que tem na carteira agora)...
	if (PlannedPick == INDEX_NONE)
	{
		const int32 PlanBudget = RemainingWaveBudget();
		if (PlanBudget <= 0)
		{
			return false;
		}
		TArray<int32> Choices;
		int32 MaxCost = 1;
		int32 TankIndex = INDEX_NONE;
		for (int32 i = 0; i < Enemies.Num(); ++i)
		{
			if (LoadedClasses.IsValidIndex(i) && LoadedClasses[i] && Wave >= Enemies[i].FirstWave && Enemies[i].Cost <= PlanBudget
				&& Enemies[i].Weight > 0.f)
			{
				Choices.Add(i);
				MaxCost = FMath::Max(MaxCost, Enemies[i].Cost);
				if (Enemies[i].Cost >= 8)
				{
					TankIndex = i;
				}
			}
		}
		if (Choices.Num() == 0)
		{
			return false;
		}
		int32 Pick = Choices.Last();
		if (TankIndex != INDEX_NONE && !bTankThisWave && GroupsThisWave >= 1)
		{
			Pick = TankIndex; // a partir da onda dele, pelo menos um Tanque (o gordão) por onda, depois do primeiro grupo
		}
		else
		{
			// Rico: puxa para os caros (não gasta tudo em zumbi comum).
			const bool bRich = PlanBudget >= 3 * MaxCost;
			float Total = 0.f;
			for (const int32 i : Choices)
			{
				Total += Enemies[i].Weight * (bRich ? 1.f + Enemies[i].Cost * 0.5f : 1.f);
			}
			float Roll = FMath::FRand() * Total;
			for (const int32 i : Choices)
			{
				Roll -= Enemies[i].Weight * (bRich ? 1.f + Enemies[i].Cost * 0.5f : 1.f);
				if (Roll <= 0.f)
				{
					Pick = i;
					break;
				}
			}
		}
		const FJRArenaEnemy& PDef = Enemies[Pick];
		const int32 EliteCostPlan = CostOfEntry(Pick, true);
		const bool bCanElite = Wave >= EliteFirstWave && EliteCostPlan <= PlanBudget;
		bPlannedElite = bCanElite && FMath::FRand() < (PlanBudget >= EliteCostPlan * 3 / 2 ? EliteChanceWhenRich : 0.08f);
		const int32 PlanUnit = CostOfEntry(Pick, bPlannedElite);
		PlannedCount = bPlannedElite ? 1 : FMath::RandRange(FMath::Max(1, PDef.GroupMin), FMath::Max(PDef.GroupMin, PDef.GroupMax));
		PlannedCount = FMath::Clamp(PlannedCount, 1, FMath::Max(1, PlanBudget / FMath::Max(1, PlanUnit)));
		PlannedPick = Pick;
	}
	// ...2) e só compra quando a carteira cobre o grupo inteiro.
	const int32 Pick = PlannedPick;
	const bool bElite = bPlannedElite;
	const FJRArenaEnemy& Def = Enemies[Pick];
	const int32 UnitCost = CostOfEntry(Pick, bElite);
	const int32 Budget = FMath::Min(FMath::FloorToInt(Wallet), RemainingWaveBudget());
	if (Budget < UnitCost * PlannedCount)
	{
		if (RemainingWaveBudget() < UnitCost)
		{
			PlannedPick = INDEX_NONE; // não cabe mais nesta onda: escolhe de novo
		}
		return false;
	}
	int32 Count = FMath::Min(PlannedCount, MaxAlive - Alive.Num() - Pending.Num());
	if (Count <= 0)
	{
		return false;
	}
	bool bFromNest = false;
	for (const TWeakObjectPtr<AJRArenaNest>& N : Nests)
	{
		bFromNest |= N.IsValid() && !N->IsNestDestroyed();
	}
	bFromNest = bFromNest && FMath::FRand() < 0.4f;
	FVector GroupSpot;
	if (!PickSpawnLocation(GroupSpot, bFromNest))
	{
		return false; // nenhum ponto escondido agora: tenta no próximo pensamento
	}
	for (int32 k = 0; k < Count; ++k)
	{
		FJRArenaPendingSpawn Entry;
		Entry.EnemyIndex = Pick;
		Entry.bElite = bElite;
		const FVector Offset = k == 0 ? FVector::ZeroVector
			: FRotator(0.f, FMath::FRandRange(0.f, 360.f), 0.f).Vector() * FMath::FRandRange(140.f, 300.f);
		Entry.Location = GroupSpot + Offset;
		Entry.PaidCost = UnitCost;
		Pending.Add(Entry);
	}
	Wallet -= Count * UnitCost;
	WaveSpent += Count * UnitCost;
	++GroupsThisWave;
	bTankThisWave |= Def.Cost >= 8;
	PlannedPick = INDEX_NONE;
	UE_LOG(LogJR, Log, TEXT("Arena: grupo %d x %s%s (custo %d)"), Count, *Def.Label, bElite ? TEXT(" ELITE") : TEXT(""), Count * UnitCost);
	AnnounceGroup(GroupSpot, bElite, false, Count * UnitCost);
	if (Def.Cost >= 8 && !bElite) // [A-098] o gordão chega anunciado (o elite já tem o próprio aviso)
	{
		UJRAudio::PlayAt(this, TEXT("Zombie.EliteRoar"), GroupSpot, 1.3f);
		AJRHUD::Toast(this, TEXT("O GORDÃO está chegando!"), FLinearColor(1.f, 0.45f, 0.2f));
	}
	return true;
}

bool AJRArenaDirector::SpawnPending(FJRArenaPendingSpawn& Entry)
{
	if (Entry.Location.IsNearlyZero() || !IsHiddenFromPlayer(Entry.Location))
	{
		FVector NewSpot;
		if (!PickSpawnLocation(NewSpot, false))
		{
			return false;
		}
		Entry.Location = NewSpot;
		if (Entry.bMarked || Entry.bElite)
		{
			AnnounceGroup(NewSpot, true, Entry.bMarked, CostOfEntry(Entry.EnemyIndex, true));
		}
	}
	UClass* Class = LoadedClasses.IsValidIndex(Entry.EnemyIndex) ? LoadedClasses[Entry.EnemyIndex].Get() : nullptr;
	if (!Class)
	{
		Class = LoadedClasses.Num() > 0 ? LoadedClasses[0].Get() : nullptr;
	}
	if (!Class)
	{
		UE_LOG(LogJR, Error, TEXT("Arena: nenhuma classe de inimigo carregada"));
		return false;
	}
	FVector SpawnAt = Entry.Location;
	if (UNavigationSystemV1* Nav = FNavigationSystem::GetCurrent<UNavigationSystemV1>(GetWorld()))
	{
		FNavLocation Projected;
		if (Nav->ProjectPointToNavigation(Entry.Location, Projected, FVector(250.f, 250.f, 400.f)))
		{
			SpawnAt = Projected.Location;
		}
	}
	SpawnAt.Z += 100.f;
	const APawn* Player = UGameplayStatics::GetPlayerPawn(this, 0);
	const FRotator Facing = Player ? (Player->GetActorLocation() - SpawnAt).GetSafeNormal2D().Rotation() : FRotator::ZeroRotator;
	FActorSpawnParameters Params;
	Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AdjustIfPossibleButDontSpawnIfColliding;
	AJREnemyCharacter* Enemy = GetWorld()->SpawnActor<AJREnemyCharacter>(Class, SpawnAt, Facing, Params);
	if (!Enemy)
	{
		return false;
	}
	const FJRArenaEnemy* Def = Enemies.IsValidIndex(Entry.EnemyIndex) ? &Enemies[Entry.EnemyIndex] : nullptr;
	const float Level = FJRRemapRules::GetEffectiveLevel(GetSectorLevelSafe(), Wave);
	float HealthMult = FJRRemapRules::EnemyHealthScale(Level) * (Def ? Def->HealthMultiplier : 1.f);
	float BodyScale = Def ? Def->Scale : 1.f;
	if (Entry.bElite)
	{
		HealthMult *= EliteHealthMultiplier * (Entry.bMarked ? 1.5f : 1.f);
		BodyScale *= 1.2f;
	}
	if (UJRHealthComponent* Health = Enemy->FindComponentByClass<UJRHealthComponent>())
	{
		Health->SetMaxHealth(Health->GetMaxHealth() * HealthMult, true);
	}
	Enemy->CustomTimeDilation = Def ? Def->Pace : 1.f;
	if (!FMath::IsNearlyEqual(BodyScale, 1.f))
	{
		Enemy->SetActorScale3D(FVector(BodyScale));
	}
	if (Entry.bElite)
	{
		MakeElite(Enemy, Entry.bMarked);
	}
	Enemy->SetForceAggro(true);
	Enemy->OnEnemyDied.AddDynamic(this, &AJRArenaDirector::HandleEnemyDied);
	Alive.Add(Enemy);
	CostOf.Add(Enemy, Entry.PaidCost > 0 ? Entry.PaidCost : CostOfEntry(Entry.EnemyIndex, Entry.bElite));
	if (Entry.bMarked)
	{
		MarkedElite = Enemy;
	}
	return true;
}

void AJRArenaDirector::MakeElite(AJREnemyCharacter* Enemy, bool bMarked) const
{
	if (!Enemy)
	{
		return;
	}
	// Aura: luz colada no corpo (roxa; dourada no elite marcado do objetivo).
	UPointLightComponent* Aura = NewObject<UPointLightComponent>(Enemy);
	Aura->SetMobility(EComponentMobility::Movable);
	Aura->SetIntensity(bMarked ? 7000.f : 4500.f);
	Aura->SetAttenuationRadius(bMarked ? 700.f : 520.f);
	Aura->SetLightColor(bMarked ? FLinearColor(1.f, 0.78f, 0.15f) : FLinearColor(0.75f, 0.25f, 1.f));
	Aura->SetCastShadows(false);
	Aura->SetupAttachment(Enemy->GetRootComponent());
	Aura->SetRelativeLocation(FVector(0.f, 0.f, 110.f));
	Aura->RegisterComponent();
	Enemy->AddInstanceComponent(Aura);
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
	FCollisionQueryParams QueryParams(SCENE_QUERY_STAT(JRArenaSpawnVisibility), false, Player);
	return GetWorld()->LineTraceSingleByChannel(Hit, CamLocation, Location + FVector(0.f, 0.f, 100.f), ECC_Visibility, QueryParams);
}

bool AJRArenaDirector::PickSpawnLocation(FVector& OutLocation, bool bPreferNest) const
{
	const APawn* Player = UGameplayStatics::GetPlayerPawn(this, 0);
	TArray<FVector> Near;
	TArray<FVector> Far;
	auto Consider = [&](const FVector& Spot)
	{
		if (!IsHiddenFromPlayer(Spot))
		{
			return;
		}
		const float D = Player ? FVector::Dist2D(Spot, Player->GetActorLocation()) : 0.f;
		(D <= PreferredMaxSpawnDistance ? Near : Far).Add(Spot);
	};
	if (bPreferNest)
	{
		for (const TWeakObjectPtr<AJRArenaNest>& N : Nests)
		{
			if (N.IsValid() && !N->IsNestDestroyed())
			{
				FVector Spot = N->GetActorLocation() + FRotator(0.f, FMath::FRandRange(0.f, 360.f), 0.f).Vector() * 260.f;
				Spot.Z = GetActorLocation().Z;
				Consider(Spot);
			}
		}
		const TArray<FVector>& FromNests = Near.Num() > 0 ? Near : Far;
		if (FromNests.Num() > 0)
		{
			OutLocation = FromNests[FMath::RandRange(0, FromNests.Num() - 1)];
			return true;
		}
	}
	for (const FVector& Spot : SpawnSpots)
	{
		Consider(Spot);
	}
	if (SpawnSpots.Num() == 0)
	{
		// Sem pontos: sorteia na navmesh em volta do diretor.
		if (const UNavigationSystemV1* Nav = FNavigationSystem::GetCurrent<UNavigationSystemV1>(GetWorld()))
		{
			for (int32 Try = 0; Try < 12; ++Try)
			{
				FNavLocation NavLoc;
				if (Nav->GetRandomReachablePointInRadius(GetActorLocation(), RandomSpawnRadius, NavLoc) && IsHiddenFromPlayer(NavLoc.Location))
				{
					Near.Add(NavLoc.Location);
					break;
				}
			}
		}
	}
	const TArray<FVector>& Pool = Near.Num() > 0 ? Near : Far;
	if (Pool.Num() == 0)
	{
		return false;
	}
	OutLocation = Pool[FMath::RandRange(0, Pool.Num() - 1)];
	return true;
}

FString AJRArenaDirector::DirectionFromHero(const FVector& Location) const
{
	const APlayerController* PC = UGameplayStatics::GetPlayerController(this, 0);
	const APawn* Player = PC ? PC->GetPawn() : nullptr;
	if (!Player)
	{
		return FString();
	}
	const float ViewYaw = PC->GetControlRotation().Yaw;
	const float ToYaw = (Location - Player->GetActorLocation()).Rotation().Yaw;
	const float Diff = FRotator::NormalizeAxis(ToYaw - ViewYaw);
	if (FMath::Abs(Diff) <= 45.f)
	{
		return TEXT("pela frente");
	}
	if (FMath::Abs(Diff) >= 135.f)
	{
		return TEXT("por trás");
	}
	return Diff > 0.f ? TEXT("pela direita") : TEXT("pela esquerda");
}

void AJRArenaDirector::AnnounceGroup(const FVector& Location, bool bElite, bool bMarked, int32 GroupCost)
{
	// Som no lugar de onde vêm (dá direção sem mostrar o surgimento) e poeira (se der para ver de longe).
	UJRAudio::PlayAt(this, bElite ? TEXT("Zombie.EliteRoar") : TEXT("Zombie.Growl"), Location, bElite ? 1.2f : 0.9f);
	if (UJRFXSubsystem* FX = UJRFXSubsystem::Get(this))
	{
		FX->SpawnDustPuff(Location + FVector(0.f, 0.f, 20.f), FLinearColor(0.35f, 0.3f, 0.25f), 14, 380.f);
	}
	const FString Dir = DirectionFromHero(Location);
	if (bMarked)
	{
		AJRHUD::Toast(this, FString::Printf(TEXT("ELITE MARCADO chegando %s! Elimine para o bônus."), *Dir), FLinearColor(1.f, 0.8f, 0.15f));
	}
	else if (bElite)
	{
		AJRHUD::Toast(this, FString::Printf(TEXT("ELITE chegando %s!"), *Dir), FLinearColor(0.8f, 0.4f, 1.f));
	}
	else if (GroupsThisWave == 1 || GroupCost >= 8)
	{
		AJRHUD::Toast(this, FString::Printf(TEXT("Horda chegando %s"), *Dir), FLinearColor(1.f, 0.55f, 0.35f));
	}
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
	if (Enemy && MarkedElite.Get() == Enemy && OptionalObjective.Type == EJRArenaObjective::KillMarkedElite && !OptionalObjective.bDone)
	{
		OptionalObjective.Progress = 1;
		CompleteObjective(OptionalObjective);
	}
}

void AJRArenaDirector::HandleHeroHealthChanged(UJRHealthComponent* ChangedHealth, float NewHealth, float Delta)
{
	if (Delta < 0.f && !bEnded)
	{
		if (UJRRunSubsystem* Run = GetRun())
		{
			Run->NotifyHeroDamaged(); // combo zera ao levar dano
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
	if (PrimaryObjective.Type == EJRArenaObjective::SurviveWaves && !PrimaryObjective.bDone)
	{
		PrimaryObjective.Progress = Run ? Run->GetWavesCleared() : Wave;
		if (PrimaryObjective.Progress >= PrimaryObjective.Target)
		{
			CompleteObjective(PrimaryObjective);
		}
	}
	if (Wave % ExtractionEveryWaves == 0)
	{
		SpawnShip();
	}
	else
	{
		AJRHUD::Toast(this, FString::Printf(TEXT("Onda %d vencida!"), Wave), FLinearColor(0.4f, 1.f, 0.6f));
	}
	UJRAudio::PlayMusic(this, TEXT("Music.Tension"), 2.f);
	bInBreak = true;
	BreakEndTime = GetWorld()->GetTimeSeconds() + BreakBetweenWaves;
	GetWorldTimerManager().SetTimer(WaveTimer, FTimerDelegate::CreateUObject(this, &AJRArenaDirector::BeginWave, Wave + 1),
		BreakBetweenWaves, false);
}

// ============================================================================ objetivos

void AJRArenaDirector::SetupObjectives()
{
	const int32 Level = GetSectorLevelSafe();
	PrimaryObjective = FJRArenaObjectiveState();
	PrimaryObjective.Type = EJRArenaObjective::SurviveWaves;
	PrimaryObjective.Target = FMath::Max(1, SurviveWavesTarget);
	PrimaryObjective.Reward = static_cast<int64>(PrimaryRewardPerLevel) * Level;

	TArray<EJRArenaObjective> Options;
	if (LoadedClasses.Num() > 0 && LoadedClasses[0])
	{
		Options.Add(EJRArenaObjective::KillMarkedElite);
	}
	if (ObjectiveSpots.Num() >= NestCount)
	{
		Options.Add(EJRArenaObjective::DestroyNests);
	}
	Options.Add(EJRArenaObjective::Combo);
	const int32 ObjSeed = Generator.IsValid() ? Generator->GetSeed() * 31 + 7 : FMath::Rand();
	const FRandomStream ObjRng(ObjSeed);
	OptionalObjective = FJRArenaObjectiveState();
	OptionalObjective.Type = Options[ObjRng.RandRange(0, Options.Num() - 1)];
	OptionalObjective.Reward = static_cast<int64>(OptionalRewardPerLevel) * Level;
	switch (OptionalObjective.Type)
	{
	case EJRArenaObjective::KillMarkedElite: OptionalObjective.Target = 1; break;
	case EJRArenaObjective::DestroyNests: OptionalObjective.Target = NestCount; break;
	default: OptionalObjective.Target = FMath::Clamp(10 + 2 * Level, 12, 30); break;
	}
	UE_LOG(LogJR, Log, TEXT("Arena: objetivos: %s | %s"), *DescribeObjective(PrimaryObjective), *DescribeObjective(OptionalObjective));
}

void AJRArenaDirector::SpawnNests()
{
	if (OptionalObjective.Type != EJRArenaObjective::DestroyNests || Nests.Num() > 0)
	{
		return;
	}
	const float NestHealth = NestBaseHealth * FJRRemapRules::EnemyHealthScale(static_cast<float>(GetSectorLevelSafe()));
	FActorSpawnParameters Params;
	Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
	for (int32 i = 0; i < NestCount && i < ObjectiveSpots.Num(); ++i)
	{
		AJRArenaNest* Nest = GetWorld()->SpawnActor<AJRArenaNest>(AJRArenaNest::StaticClass(), ObjectiveSpots[i],
			FRotator(0.f, FMath::FRandRange(0.f, 360.f), 0.f), Params);
		if (!Nest)
		{
			continue;
		}
		Nest->SetupNest(NestHealth);
		Nest->GetHealthComponent()->OnDeath.AddDynamic(this, &AJRArenaDirector::HandleNestDestroyed);
		Nests.Add(Nest);
	}
	if (Nests.Num() < NestCount)
	{
		OptionalObjective.Target = Nests.Num();
	}
}

void AJRArenaDirector::HandleNestDestroyed(UJRHealthComponent* DeadHealth, AActor* Killer)
{
	if (OptionalObjective.Type != EJRArenaObjective::DestroyNests || OptionalObjective.bDone || bEnded)
	{
		return;
	}
	++OptionalObjective.Progress;
	if (OptionalObjective.Progress >= OptionalObjective.Target)
	{
		CompleteObjective(OptionalObjective);
	}
	else
	{
		AJRHUD::Toast(this, FString::Printf(TEXT("Ninho destruído (%d/%d)"), OptionalObjective.Progress, OptionalObjective.Target),
			FLinearColor(0.55f, 1.f, 0.35f));
	}
}

void AJRArenaDirector::CompleteObjective(FJRArenaObjectiveState& Objective)
{
	if (Objective.bDone || Objective.Type == EJRArenaObjective::None)
	{
		return;
	}
	Objective.bDone = true;
	Objective.Progress = FMath::Max(Objective.Progress, Objective.Target);
	if (UJRRunSubsystem* Run = GetRun())
	{
		Run->AddBonusCredits(Objective.Reward);
		Run->MarkObjectiveCompleted();
	}
	UJRAudio::Play2D(this, TEXT("UI.Objective"));
	AJRHUD::Toast(this, FString::Printf(TEXT("OBJETIVO CUMPRIDO! +%lld créditos"), Objective.Reward), FLinearColor(0.4f, 1.f, 0.55f));
	UE_LOG(LogJR, Log, TEXT("Arena: objetivo cumprido (%d), +%lld"), static_cast<int32>(Objective.Type), Objective.Reward);
}

FString AJRArenaDirector::DescribeObjective(const FJRArenaObjectiveState& Objective) const
{
	switch (Objective.Type)
	{
	case EJRArenaObjective::SurviveWaves:
		return FString::Printf(TEXT("Sobreviva %d ondas (%d/%d)  +%lld"), Objective.Target,
			FMath::Min(Objective.Progress, Objective.Target), Objective.Target, Objective.Reward);
	case EJRArenaObjective::KillMarkedElite:
		return bMarkedEliteSpawned
			? FString::Printf(TEXT("Opcional: elimine o elite marcado  +%lld"), Objective.Reward)
			: FString::Printf(TEXT("Opcional: elimine o elite marcado (chega na onda %d)  +%lld"), MarkedEliteWave, Objective.Reward);
	case EJRArenaObjective::DestroyNests:
		return FString::Printf(TEXT("Opcional: destrua os ninhos (%d/%d)  +%lld"), Objective.Progress, Objective.Target, Objective.Reward);
	case EJRArenaObjective::Combo:
		// Sem o combo atual no texto: a HUD reage a cada troca de texto (a barra de progresso mostra o combo).
		return FString::Printf(TEXT("Opcional: %d abates seguidos sem levar dano  +%lld"), Objective.Target, Objective.Reward);
	default:
		return FString();
	}
}

FString AJRArenaDirector::GetObjectiveLine() const
{
	if (OptionalObjective.Type != EJRArenaObjective::None && !OptionalObjective.bDone)
	{
		return DescribeObjective(OptionalObjective);
	}
	if (PrimaryObjective.Type != EJRArenaObjective::None && !PrimaryObjective.bDone)
	{
		return DescribeObjective(PrimaryObjective);
	}
	return FString();
}

float AJRArenaDirector::GetObjectiveProgress() const
{
	const FJRArenaObjectiveState* Obj = nullptr;
	if (OptionalObjective.Type != EJRArenaObjective::None && !OptionalObjective.bDone)
	{
		Obj = &OptionalObjective;
	}
	else if (PrimaryObjective.Type != EJRArenaObjective::None && !PrimaryObjective.bDone)
	{
		Obj = &PrimaryObjective;
	}
	if (!Obj || Obj->Target <= 0)
	{
		return -1.f;
	}
	switch (Obj->Type)
	{
	case EJRArenaObjective::KillMarkedElite:
	{
		// barra = vida que já tirou do elite marcado
		const AJREnemyCharacter* Elite = MarkedElite.Get();
		const UJRHealthComponent* EliteHealth = Elite ? Elite->FindComponentByClass<UJRHealthComponent>() : nullptr;
		return EliteHealth ? FMath::Clamp(1.f - EliteHealth->GetHealthNormalized(), 0.f, 1.f) : -1.f;
	}
	case EJRArenaObjective::Combo:
	{
		const UJRRunSubsystem* Run = GetRun();
		return Run ? FMath::Clamp(static_cast<float>(Run->GetCombo()) / Obj->Target, 0.f, 1.f) : -1.f;
	}
	default:
		return FMath::Clamp(static_cast<float>(Obj->Progress) / Obj->Target, 0.f, 1.f);
	}
}

// ============================================================================ nave, cartas, fim (como no F1)

void AJRArenaDirector::SpawnShip()
{
	if (ActiveShip.IsValid() || !ShipClass)
	{
		return;
	}
	FVector Location = GetActorLocation();
	const APawn* Player = UGameplayStatics::GetPlayerPawn(this, 0);
	if (ExtractionSpots.Num() > 0)
	{
		// O ponto mais longe do herói entre 2 sorteados: obriga a atravessar a arena.
		const FVector A = ExtractionSpots[FMath::RandRange(0, ExtractionSpots.Num() - 1)];
		const FVector B = ExtractionSpots[FMath::RandRange(0, ExtractionSpots.Num() - 1)];
		Location = A;
		if (Player && FVector::DistSquared(B, Player->GetActorLocation()) > FVector::DistSquared(A, Player->GetActorLocation()))
		{
			Location = B;
		}
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
		AJRHUD::Toast(this, FString::Printf(TEXT("NAVE DE EXTRAÇÃO %s! %.0f s para embarcar (x%.2f)"), *DirectionFromHero(Location),
			ExtractionSeconds, Mult), FLinearColor(0.3f, 0.95f, 1.f));
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
	Pending.Reset();
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

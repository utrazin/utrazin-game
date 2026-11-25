// Copyright utrazin. All Rights Reserved.

#include "Remap/JRRunSubsystem.h"
#include "Characters/JRCharacter.h"
#include "Combat/JRHealthComponent.h"
#include "Combat/JRWeaponComponent.h"
#include "JogoResgate.h"
#include "Remap/JREconomySubsystem.h"

void UJRRunSubsystem::Initialize(FSubsystemCollectionBase& Collection)
{
	Collection.InitializeDependency<UJREconomySubsystem>();
	Super::Initialize(Collection);
	Rng.GenerateNewSeed();
}

void UJRRunSubsystem::StartRun(int32 InSectorLevel)
{
	bActive = true;
	SectorLevel = FMath::Max(1, InSectorLevel);
	Wave = 0;
	WavesCleared = 0;
	Kills = 0;
	RunLevel = 1;
	Energy = 0.f;
	RunCredits = 0;
	Combo = 0;
	MaxCombo = 0;
	ObjectivesCompleted = 0;
	Picked.Reset();
	PendingChoices = 0;
	// [A-098] a Árvore-Mãe vira a base da corrida (as cartas somam em cima) e pode dar cartas logo no começo
	if (const UJREconomySubsystem* Economy = GetGameInstance()->GetSubsystem<UJREconomySubsystem>())
	{
		Stats = Economy->MakeTreeBaseStats();
		PendingChoices = FMath::Min(FJRRemapRules::MaxBankedChoices, FMath::RoundToInt(Economy->GetTreeBonus(EJRTreeStat::StartCards)));
	}
	else
	{
		Stats = FJRRunStats();
	}
	bChoosing = false;
	Offered.Reset();
	Rng.GenerateNewSeed();
	UE_LOG(LogJR, Log, TEXT("Corrida: começou no nível %d"), SectorLevel);
}

void UJRRunSubsystem::EndRun(bool bExtracted, float Multiplier)
{
	if (!bActive)
	{
		return;
	}
	bActive = false;
	bChoosing = false;
	PendingChoices = 0;

	Report = FJRRunReport();
	Report.bExtracted = bExtracted;
	Report.SectorLevel = SectorLevel;
	Report.Waves = WavesCleared;
	Report.Kills = Kills;
	Report.RunLevel = RunLevel;
	Report.CreditsEarned = RunCredits;
	Report.Multiplier = bExtracted ? Multiplier : FJRRemapRules::DeathKeepCredits;
	Report.CreditsKept = bExtracted ? FMath::RoundToInt64(RunCredits * Multiplier) : GetCreditsIfDie();
	Report.ObjectivesCompleted = ObjectivesCompleted;
	Report.MaxCombo = MaxCombo;

	if (UJREconomySubsystem* Economy = GetGameInstance()->GetSubsystem<UJREconomySubsystem>())
	{
		Report.bNewRecord = Economy->RecordRun(WavesCleared);
		Economy->AddCredits(Report.CreditsKept, false);
		// [A-098] cristais para a Árvore-Mãe
		Report.CrystalsEarned = FJRRemapRules::RunCrystals(WavesCleared, ObjectivesCompleted, SectorLevel, bExtracted,
			1.f + Economy->GetTreeBonus(EJRTreeStat::Crystals));
		Economy->AddCrystals(Report.CrystalsEarned, false);
		Economy->Save();
	}
	bHasReport = true;
	UE_LOG(LogJR, Log, TEXT("Corrida: %s na onda %d, %d abates, %lld créditos -> fica com %lld"),
		bExtracted ? TEXT("extraiu") : TEXT("morreu"), WavesCleared, Kills, RunCredits, Report.CreditsKept);
}

int64 UJRRunSubsystem::RegisterKill(int32 EnemyCost, float EffectiveLevel)
{
	if (!bActive)
	{
		return 0;
	}
	++Kills;
	++Combo;
	MaxCombo = FMath::Max(MaxCombo, Combo);
	const int32 Cost = FMath::Max(1, EnemyCost);
	const int64 Gain = FMath::RoundToInt64(FJRRemapRules::CreditsPerCost(EffectiveLevel) * Cost * Stats.Credits);
	RunCredits += Gain;
	AddEnergy(Cost * Stats.Energy);
	return Gain;
}

void UJRRunSubsystem::AddBonusCredits(int64 Amount)
{
	if (bActive && Amount > 0)
	{
		RunCredits += Amount;
	}
}

void UJRRunSubsystem::AddEnergy(float Amount)
{
	if (!bActive || Amount <= 0.f)
	{
		return;
	}
	Energy += Amount;
	while (Energy >= GetEnergyNeeded())
	{
		Energy -= GetEnergyNeeded();
		++RunLevel;
		PendingChoices = FMath::Min(PendingChoices + 1, FJRRemapRules::MaxBankedChoices);
		UE_LOG(LogJR, Log, TEXT("Corrida: subiu para o nível %d (%d escolha(s) guardada(s))"), RunLevel, PendingChoices);
	}
}

void UJRRunSubsystem::BeginCardChoice()
{
	if (PendingChoices <= 0 || bChoosing)
	{
		return;
	}
	Offered.Reset();
	TArray<EJRRunCard> Pool;
	for (int32 i = 0; i < static_cast<int32>(EJRRunCard::Count); ++i)
	{
		Pool.Add(static_cast<EJRRunCard>(i));
	}
	while (Offered.Num() < 3 && Pool.Num() > 0)
	{
		int32 Total = 0;
		for (const EJRRunCard C : Pool)
		{
			Total += FJRRemapRules::CardWeight(C);
		}
		int32 Roll = Rng.RandRange(0, FMath::Max(0, Total - 1));
		for (int32 i = 0; i < Pool.Num(); ++i)
		{
			Roll -= FJRRemapRules::CardWeight(Pool[i]);
			if (Roll < 0)
			{
				Offered.Add(Pool[i]);
				Pool.RemoveAt(i);
				break;
			}
		}
	}
	bChoosing = true;
}

EJRRunCard UJRRunSubsystem::PickCard(int32 Index)
{
	if (!bChoosing || !Offered.IsValidIndex(Index))
	{
		return EJRRunCard::Count;
	}
	const EJRRunCard Card = Offered[Index];
	FJRRemapRules::ApplyCard(Card, Stats);
	Picked.Add(Card);
	Offered.Reset();
	bChoosing = false;
	PendingChoices = FMath::Max(0, PendingChoices - 1);
	UE_LOG(LogJR, Log, TEXT("Corrida: carta %s"), *FJRRemapRules::CardTitle(Card).ToString());
	return Card;
}

void UJRRunSubsystem::ApplyStatsToHero(AJRCharacter* Hero, bool bRefillHealth) const
{
	if (!Hero)
	{
		return;
	}
	const UJREconomySubsystem* Economy = GetGameInstance()->GetSubsystem<UJREconomySubsystem>();
	const float Bench = Economy ? Economy->GetPermanentDamageMultiplier() : 1.f;
	const FJRRunStats S = bActive ? Stats : (Economy ? Economy->MakeTreeBaseStats() : FJRRunStats()); // [A-098]
	if (UJRWeaponComponent* Weapon = Hero->GetWeaponComponent())
	{
		Weapon->SetUpgradeMultipliers(Bench * S.Damage, S.FireRate);
	}
	Hero->SetMoveSpeedMultiplier(S.MoveSpeed);
	if (UJRHealthComponent* Health = Hero->GetHealthComponent())
	{
		// Vida base guardada na primeira vez (o BP do herói define a vida máxima original).
		if (Hero->RemapBaseMaxHealth < 0.f)
		{
			Hero->RemapBaseMaxHealth = Health->GetMaxHealth();
		}
		const float Base = Hero->RemapBaseMaxHealth;
		const float OldMax = Health->GetMaxHealth();
		const float NewMax = Base * S.MaxHealth;
		Health->SetMaxHealth(NewMax, bRefillHealth);
		if (!bRefillHealth && NewMax > OldMax)
		{
			Health->Heal(NewMax - OldMax);
		}
		Health->SetDamageTakenMultiplier(S.DamageTaken);
	}
}

// Copyright utrazin. All Rights Reserved.

#include "Remap/JREconomySubsystem.h"
#include "Characters/JRCharacter.h"
#include "Combat/JRWeaponComponent.h"
#include "JogoResgate.h"
#include "Progression/JRProgressionSubsystem.h"
#include "Save/JRSaveGame.h"

void UJREconomySubsystem::Initialize(FSubsystemCollectionBase& Collection)
{
	Collection.InitializeDependency<UJRProgressionSubsystem>();
	Super::Initialize(Collection);
}

UJRSaveGame* UJREconomySubsystem::GetSaveGame() const
{
	const UJRProgressionSubsystem* Progression = GetGameInstance()->GetSubsystem<UJRProgressionSubsystem>();
	return Progression ? Progression->GetSave() : nullptr;
}

void UJREconomySubsystem::Save()
{
	if (UJRProgressionSubsystem* Progression = GetGameInstance()->GetSubsystem<UJRProgressionSubsystem>())
	{
		Progression->SaveNow();
	}
}

int64 UJREconomySubsystem::GetCredits() const
{
	const UJRSaveGame* S = GetSaveGame();
	return S ? S->Credits : 0;
}

void UJREconomySubsystem::AddCredits(int64 Amount, bool bSave)
{
	UJRSaveGame* S = GetSaveGame();
	if (!S || Amount == 0)
	{
		return;
	}
	S->Credits = FMath::Max<int64>(0, S->Credits + Amount);
	UE_LOG(LogJR, Log, TEXT("Carteira: %+lld créditos (agora %lld)"), Amount, S->Credits);
	OnWalletChanged.Broadcast(S->Credits);
	if (bSave)
	{
		Save();
	}
}

bool UJREconomySubsystem::SpendCredits(int64 Amount)
{
	UJRSaveGame* S = GetSaveGame();
	if (!S || Amount < 0 || S->Credits < Amount)
	{
		return false;
	}
	AddCredits(-Amount);
	return true;
}

int32 UJREconomySubsystem::GetBenchLevel() const
{
	const UJRSaveGame* S = GetSaveGame();
	return S ? S->BenchLevel : 0;
}

bool UJREconomySubsystem::BuyBenchLevel()
{
	UJRSaveGame* S = GetSaveGame();
	if (!S)
	{
		return false;
	}
	const int64 Cost = FJRRemapRules::BenchCost(S->BenchLevel);
	if (S->Credits < Cost)
	{
		return false;
	}
	S->Credits -= Cost;
	++S->BenchLevel;
	UE_LOG(LogJR, Log, TEXT("Bancada: nível %d (pagou %lld)"), S->BenchLevel, Cost);
	OnWalletChanged.Broadcast(S->Credits);
	Save();
	return true;
}

bool UJREconomySubsystem::OwnsWeapon(EJRWeaponSlot Slot) const
{
	if (Slot == EJRWeaponSlot::Melee || Slot == EJRWeaponSlot::Pistol)
	{
		return true;
	}
	const UJRSaveGame* S = GetSaveGame();
	return S && S->OwnedWeaponSlots.Contains(static_cast<uint8>(Slot));
}

bool UJREconomySubsystem::BuyWeapon(EJRWeaponSlot Slot)
{
	UJRSaveGame* S = GetSaveGame();
	const int64 Price = FJRRemapRules::WeaponPrice(Slot);
	if (!S || Price <= 0 || OwnsWeapon(Slot) || S->Credits < Price)
	{
		return false;
	}
	S->Credits -= Price;
	S->OwnedWeaponSlots.AddUnique(static_cast<uint8>(Slot));
	UE_LOG(LogJR, Log, TEXT("Armeiro: comprou %s por %lld"), *UEnum::GetValueAsString(Slot), Price);
	OnWalletChanged.Broadcast(S->Credits);
	Save();
	return true;
}

void UJREconomySubsystem::GrantOwnedWeapons(AJRCharacter* Hero) const
{
	if (!Hero)
	{
		return;
	}
	Hero->GrantWeapon(EJRWeaponSlot::Melee, false);
	EJRWeaponSlot Best = EJRWeaponSlot::Pistol;
	Hero->GrantWeapon(EJRWeaponSlot::Pistol, false);
	for (const EJRWeaponSlot Slot : { EJRWeaponSlot::Shotgun, EJRWeaponSlot::Sniper })
	{
		if (OwnsWeapon(Slot))
		{
			Hero->GrantWeapon(Slot, false);
			if (Slot == EJRWeaponSlot::Shotgun)
			{
				Best = Slot; // escopeta é a melhor para ondas (o rifle de precisão fica na roda)
			}
			else if (Best == EJRWeaponSlot::Pistol)
			{
				Best = Slot;
			}
		}
	}
	Hero->GrantWeapon(Best, true);
	if (UJRWeaponComponent* Weapon = Hero->GetWeaponComponent())
	{
		Weapon->AddReserveAmmo(60 + FMath::RoundToInt(GetTreeBonus(EJRTreeStat::ReserveAmmo))); // [A-098] Bolsa de Brotos
		Weapon->SetUpgradeMultipliers(GetPermanentDamageMultiplier(), 1.f);
	}
}

int32 UJREconomySubsystem::GetBestWave() const
{
	const UJRSaveGame* S = GetSaveGame();
	return S ? S->BestWave : 0;
}

bool UJREconomySubsystem::RecordRun(int32 Waves)
{
	UJRSaveGame* S = GetSaveGame();
	if (!S)
	{
		return false;
	}
	++S->RunsPlayed;
	const bool bRecord = Waves > S->BestWave;
	S->BestWave = FMath::Max(S->BestWave, Waves);
	return bRecord;
}


// ---------------------------------------------------------------- [A-098] arenas, bairros e Árvore-Mãe
int32 UJREconomySubsystem::GetUnlockedArenaLevel() const
{
	return FJRRemapRules::UnlockedArenaLevel(GetBestWave());
}

bool UJREconomySubsystem::IsDistrictSeen(FName DistrictId) const
{
	const UJRSaveGame* S = GetSaveGame();
	return S && S->SeenDistricts.Contains(DistrictId);
}

void UJREconomySubsystem::MarkDistrictSeen(FName DistrictId)
{
	if (UJRSaveGame* S = GetSaveGame())
	{
		if (!S->SeenDistricts.Contains(DistrictId))
		{
			S->SeenDistricts.Add(DistrictId);
			Save();
		}
	}
}

int64 UJREconomySubsystem::GetCrystals() const
{
	const UJRSaveGame* S = GetSaveGame();
	return S ? S->Crystals : 0;
}

void UJREconomySubsystem::AddCrystals(int64 Amount, bool bSave)
{
	UJRSaveGame* S = GetSaveGame();
	if (!S || Amount == 0)
	{
		return;
	}
	S->Crystals = FMath::Max<int64>(0, S->Crystals + Amount);
	UE_LOG(LogJR, Log, TEXT("Cristais: %+lld (agora %lld)"), Amount, S->Crystals);
	if (bSave)
	{
		Save();
	}
}

int32 UJREconomySubsystem::GetTreeRank(FName NodeId) const
{
	const UJRSaveGame* S = GetSaveGame();
	const int32* Rank = S ? S->TreeRanks.Find(NodeId) : nullptr;
	return Rank ? *Rank : 0;
}

bool UJREconomySubsystem::IsTreeNodeOpen(FName NodeId, FString* OutWhy) const
{
	const FJRTreeNodeDef* Node = FJRSkillTree::Find(NodeId);
	if (!Node)
	{
		return false;
	}
	if (GetTreeRank(NodeId) >= Node->MaxRank)
	{
		if (OutWhy) { *OutWhy = TEXT("Esse galho já está no máximo."); }
		return false;
	}
	if (!Node->Requires.IsNone() && GetTreeRank(Node->Requires) < Node->RequiresRank)
	{
		if (OutWhy)
		{
			const FJRTreeNodeDef* Parent = FJRSkillTree::Find(Node->Requires);
			*OutWhy = FString::Printf(TEXT("Precisa de %s nível %d antes."), Parent ? Parent->Label : TEXT("?"), Node->RequiresRank);
		}
		return false;
	}
	return true;
}

bool UJREconomySubsystem::BuyTreeNode(FName NodeId)
{
	UJRSaveGame* S = GetSaveGame();
	const FJRTreeNodeDef* Node = FJRSkillTree::Find(NodeId);
	if (!S || !Node || !IsTreeNodeOpen(NodeId))
	{
		return false;
	}
	const int32 Rank = GetTreeRank(NodeId);
	const int64 Price = FJRSkillTree::Cost(*Node, Rank);
	if (S->Crystals < Price)
	{
		return false;
	}
	S->Crystals -= Price;
	S->TreeRanks.FindOrAdd(NodeId) = Rank + 1;
	UE_LOG(LogJR, Log, TEXT("Árvore-Mãe: %s nível %d por %lld cristais"), *NodeId.ToString(), Rank + 1, Price);
	Save();
	return true;
}

float UJREconomySubsystem::GetTreeBonus(EJRTreeStat Stat) const
{
	float Sum = 0.f;
	for (const FJRTreeNodeDef& Node : FJRSkillTree::Nodes())
	{
		if (Node.Stat == Stat)
		{
			Sum += Node.PerRank * GetTreeRank(Node.Id);
		}
	}
	return Sum;
}

FJRRunStats UJREconomySubsystem::MakeTreeBaseStats() const
{
	FJRRunStats S;
	S.Damage += GetTreeBonus(EJRTreeStat::Damage);
	S.FireRate += GetTreeBonus(EJRTreeStat::FireRate);
	S.MaxHealth += GetTreeBonus(EJRTreeStat::MaxHealth);
	S.MoveSpeed += GetTreeBonus(EJRTreeStat::MoveSpeed);
	S.DamageTaken = FMath::Max(0.4f, S.DamageTaken + GetTreeBonus(EJRTreeStat::DamageTaken));
	S.LifeOnKill += GetTreeBonus(EJRTreeStat::LifeOnKill);
	S.Credits += GetTreeBonus(EJRTreeStat::Credits);
	S.Energy += GetTreeBonus(EJRTreeStat::Energy);
	return S;
}

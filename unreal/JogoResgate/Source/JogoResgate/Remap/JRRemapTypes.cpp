// Copyright utrazin. All Rights Reserved.

#include "Remap/JRRemapTypes.h"

#define LOCTEXT_NAMESPACE "JRRemap"

const TCHAR* FJRRemapRules::CityMap = TEXT("/Game/Levels/Remap/L_Cidade");
const TCHAR* FJRRemapRules::ArenaMap = TEXT("/Game/Levels/Remap/L_Arena_F1");

int64 FJRRemapRules::BenchCost(int32 CurrentLevel)
{
	return FMath::RoundToInt64(300.0 * FMath::Pow(1.17, static_cast<double>(FMath::Max(0, CurrentLevel) + 1)));
}

int64 FJRRemapRules::WeaponPrice(EJRWeaponSlot Slot)
{
	switch (Slot)
	{
	case EJRWeaponSlot::Shotgun: return 2000;
	case EJRWeaponSlot::Sniper: return 28000;
	default: return 0;
	}
}

FText FJRRemapRules::CardTitle(EJRRunCard Card)
{
	switch (Card)
	{
	case EJRRunCard::Damage: return LOCTEXT("CardDamage", "Força");
	case EJRRunCard::FireRate: return LOCTEXT("CardFireRate", "Gatilho leve");
	case EJRRunCard::MoveSpeed: return LOCTEXT("CardSpeed", "Pernas rápidas");
	case EJRRunCard::MaxHealth: return LOCTEXT("CardMaxHealth", "Couro grosso");
	case EJRRunCard::LifeOnKill: return LOCTEXT("CardLifeOnKill", "Vampiro");
	case EJRRunCard::Credits: return LOCTEXT("CardCredits", "Bolso fundo");
	case EJRRunCard::HealNow: return LOCTEXT("CardHealNow", "Fôlego");
	case EJRRunCard::Energy: return LOCTEXT("CardEnergy", "Ímã de energia");
	case EJRRunCard::Armor: return LOCTEXT("CardArmor", "Couraça");
	default: return FText::GetEmpty();
	}
}

FText FJRRemapRules::CardDescription(EJRRunCard Card)
{
	switch (Card)
	{
	case EJRRunCard::Damage: return LOCTEXT("CardDamageD", "+15% de dano");
	case EJRRunCard::FireRate: return LOCTEXT("CardFireRateD", "+15% de cadência");
	case EJRRunCard::MoveSpeed: return LOCTEXT("CardSpeedD", "+12% de velocidade");
	case EJRRunCard::MaxHealth: return LOCTEXT("CardMaxHealthD", "+25% de vida máxima");
	case EJRRunCard::LifeOnKill: return LOCTEXT("CardLifeOnKillD", "Cura 2% da vida a cada abate");
	case EJRRunCard::Credits: return LOCTEXT("CardCreditsD", "+30% de créditos nesta corrida");
	case EJRRunCard::HealNow: return LOCTEXT("CardHealNowD", "Cura 50% da vida agora");
	case EJRRunCard::Energy: return LOCTEXT("CardEnergyD", "+25% de energia por abate");
	case EJRRunCard::Armor: return LOCTEXT("CardArmorD", "-15% de dano recebido");
	default: return FText::GetEmpty();
	}
}

int32 FJRRemapRules::CardWeight(EJRRunCard Card)
{
	switch (Card)
	{
	case EJRRunCard::LifeOnKill:
	case EJRRunCard::Armor: return 5;    // raras
	case EJRRunCard::Credits: return 6;
	default: return 10;                  // comuns
	}
}

int32 FJRRemapRules::CardRarity(EJRRunCard Card)
{
	switch (Card)
	{
	case EJRRunCard::LifeOnKill:
	case EJRRunCard::Armor: return 1;
	default: return 0;
	}
}

void FJRRemapRules::ApplyCard(EJRRunCard Card, FJRRunStats& Stats)
{
	switch (Card)
	{
	case EJRRunCard::Damage: Stats.Damage += 0.15f; break;
	case EJRRunCard::FireRate: Stats.FireRate += 0.15f; break;
	case EJRRunCard::MoveSpeed: Stats.MoveSpeed += 0.12f; break;
	case EJRRunCard::MaxHealth: Stats.MaxHealth += 0.25f; break;
	case EJRRunCard::LifeOnKill: Stats.LifeOnKill += 0.02f; break;
	case EJRRunCard::Credits: Stats.Credits += 0.30f; break;
	case EJRRunCard::Energy: Stats.Energy += 0.25f; break;
	case EJRRunCard::Armor: Stats.DamageTaken = FMath::Max(0.4f, Stats.DamageTaken * 0.85f); break;
	default: break; // HealNow é instantâneo
	}
}

#undef LOCTEXT_NAMESPACE


// ---------------------------------------------------------------- [A-098] Árvore-Mãe
const TArray<FJRTreeNodeDef>& FJRSkillTree::Nodes()
{
	static TArray<FJRTreeNodeDef> Table = []()
	{
		TArray<FJRTreeNodeDef> T;
		auto Add = [&T](const TCHAR* Id, int32 Branch, int32 Depth, const TCHAR* Label, const TCHAR* Detail, const TCHAR* Icon,
			EJRTreeStat Stat, float Per, int32 MaxRank, int64 Base, float Growth, const TCHAR* Req, int32 ReqRank)
		{
			FJRTreeNodeDef N;
			N.Id = FName(Id); N.Branch = Branch; N.Depth = Depth; N.Label = Label; N.Detail = Detail; N.Icon = Icon; N.Stat = Stat;
			N.PerRank = Per; N.MaxRank = MaxRank; N.BaseCost = Base; N.CostGrowth = Growth;
			N.Requires = Req ? FName(Req) : NAME_None; N.RequiresRank = ReqRank;
			T.Add(N);
		};
		// raiz: abre os 4 galhos
		Add(TEXT("Semente"), 0, 0, TEXT("Semente da Árvore-Mãe"), TEXT("Desperta a árvore: %s e abre os galhos"), TEXT("R_Star"), EJRTreeStat::MaxHealth, 0.05f, 1, 2, 1.f, nullptr, 0);
		// Fúria (combate)
		Add(TEXT("Forca"), 1, 1, TEXT("Seiva de Fúria"), TEXT("%s"), TEXT("Stat_Damage"), EJRTreeStat::Damage, 0.06f, 10, 3, 1.32f, TEXT("Semente"), 1);
		Add(TEXT("Gatilho"), 1, 2, TEXT("Espinho Ligeiro"), TEXT("%s"), TEXT("Stat_FireRate"), EJRTreeStat::FireRate, 0.04f, 8, 5, 1.35f, TEXT("Forca"), 2);
		Add(TEXT("Sede"), 1, 3, TEXT("Raiz Sedenta"), TEXT("%s"), TEXT("R_CardLifeOnKill"), EJRTreeStat::LifeOnKill, 0.008f, 5, 9, 1.45f, TEXT("Gatilho"), 3);
		// Casca (sobrevivência)
		Add(TEXT("Seiva"), 2, 1, TEXT("Casca Grossa"), TEXT("%s"), TEXT("R_Heart"), EJRTreeStat::MaxHealth, 0.08f, 10, 3, 1.32f, TEXT("Semente"), 1);
		Add(TEXT("Couraca"), 2, 2, TEXT("Couraça de Resina"), TEXT("%s"), TEXT("R_Shield"), EJRTreeStat::DamageTaken, -0.04f, 6, 5, 1.4f, TEXT("Seiva"), 2);
		Add(TEXT("Brotos"), 2, 3, TEXT("Bolsa de Brotos"), TEXT("%s"), TEXT("Stat_Ammo"), EJRTreeStat::ReserveAmmo, 30.f, 5, 4, 1.3f, TEXT("Seiva"), 1);
		// Raízes (economia)
		Add(TEXT("Ouro"), 3, 1, TEXT("Raiz Dourada"), TEXT("%s"), TEXT("R_Coins"), EJRTreeStat::Credits, 0.06f, 10, 3, 1.32f, TEXT("Semente"), 1);
		Add(TEXT("Cristalina"), 3, 2, TEXT("Veio Cristalino"), TEXT("%s"), TEXT("R_Trophy"), EJRTreeStat::Crystals, 0.10f, 5, 6, 1.4f, TEXT("Ouro"), 2);
		Add(TEXT("Presente"), 3, 3, TEXT("Fruto do Começo"), TEXT("%s"), TEXT("V3_CardRare"), EJRTreeStat::StartCards, 1.f, 2, 15, 2.0f, TEXT("Cristalina"), 2);
		// Vento (mobilidade)
		Add(TEXT("Passo"), 4, 1, TEXT("Folha ao Vento"), TEXT("%s"), TEXT("R_CardSpeed"), EJRTreeStat::MoveSpeed, 0.03f, 6, 3, 1.35f, TEXT("Semente"), 1);
		Add(TEXT("Pulso"), 4, 2, TEXT("Pulso da Seiva"), TEXT("%s"), TEXT("R_Energy"), EJRTreeStat::Energy, 0.06f, 5, 5, 1.4f, TEXT("Passo"), 2);
		return T;
	}();
	return Table;
}

const FJRTreeNodeDef* FJRSkillTree::Find(FName Id)
{
	return Nodes().FindByPredicate([Id](const FJRTreeNodeDef& N) { return N.Id == Id; });
}

int64 FJRSkillTree::Cost(const FJRTreeNodeDef& Node, int32 Rank)
{
	return FMath::Max<int64>(1, FMath::RoundToInt64(Node.BaseCost * FMath::Pow(Node.CostGrowth, FMath::Max(0, Rank))));
}

FString FJRSkillTree::BranchName(int32 Branch)
{
	switch (Branch)
	{
	case 1: return TEXT("Fúria");
	case 2: return TEXT("Casca");
	case 3: return TEXT("Raízes");
	case 4: return TEXT("Vento");
	default: return TEXT("Tronco");
	}
}

FString FJRSkillTree::EffectText(const FJRTreeNodeDef& Node, int32 Ranks)
{
	const float V = Node.PerRank * FMath::Max(0, Ranks);
	switch (Node.Stat)
	{
	case EJRTreeStat::Damage: return FString::Printf(TEXT("+%.0f%% dano"), V * 100.f);
	case EJRTreeStat::FireRate: return FString::Printf(TEXT("+%.0f%% cadência"), V * 100.f);
	case EJRTreeStat::MaxHealth: return FString::Printf(TEXT("+%.0f%% vida máxima"), V * 100.f);
	case EJRTreeStat::MoveSpeed: return FString::Printf(TEXT("+%.0f%% velocidade"), V * 100.f);
	case EJRTreeStat::DamageTaken: return FString::Printf(TEXT("-%.0f%% dano recebido"), -V * 100.f);
	case EJRTreeStat::LifeOnKill: return FString::Printf(TEXT("cura %.1f%% da vida por abate"), V * 100.f);
	case EJRTreeStat::Credits: return FString::Printf(TEXT("+%.0f%% créditos"), V * 100.f);
	case EJRTreeStat::Energy: return FString::Printf(TEXT("+%.0f%% energia por abate"), V * 100.f);
	case EJRTreeStat::Crystals: return FString::Printf(TEXT("+%.0f%% cristais"), V * 100.f);
	case EJRTreeStat::StartCards: return FString::Printf(TEXT("%d carta(s) logo no começo"), FMath::RoundToInt(V));
	case EJRTreeStat::ReserveAmmo: return FString::Printf(TEXT("+%d munição reserva"), FMath::RoundToInt(V));
	default: return FString();
	}
}

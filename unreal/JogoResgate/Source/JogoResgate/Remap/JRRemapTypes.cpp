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

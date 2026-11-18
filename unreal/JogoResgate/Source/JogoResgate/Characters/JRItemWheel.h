// Copyright utrazin. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"

/**
 * Roda de itens (segurar Tab / LB), estilo GTA (A-055), com duas abas (HUD v2, A-059):
 * ARMAS e CONSUMÍVEIS, 8 setores cada, no sentido horário a partir do topo.
 * Itens que o jogador ainda não tem aparecem bloqueados (cadeado); setores sem item ficam vazios.
 */
enum class EJRWheelEntry : uint8
{
	Unarmed,  // "Nada" na aba ARMAS: guarda a arma
	Melee,
	Pistol,
	Shotgun,
	Grenade,  // futuro (sempre bloqueada)
	Fury,
	Medkit,
	Bandage,
	Count,
	/**
	 * [A-058] Rifle de precisão: DEPOIS de Count de propósito (os valores antigos não mudam).
	 * Na roda com abas ele é o setor de baixo da aba ARMAS.
	 */
	Sniper,
	// [A-059] Novos itens da roda com abas (sempre no fim)
	NoItem,     // "Nada" na aba CONSUMÍVEIS: fecha sem usar nada
	CarKey,     // itens-chave da fase: só informação (usados sozinhos no lugar certo)
	Fuel,
	Explosive,
	Empty       // setor vazio
};

/** O que a roda mostra num setor (preenchido por AJRCharacter::GetWheelEntryInfo). */
struct FJRWheelEntryInfo
{
	/** Nome grande no centro ("BANDAGEM"). */
	FString Name;
	/** Linha pequena acima do nome ("ARMA DE FOGO", "CONSUMÍVEL"...). */
	FString Category;
	/** Linhas de detalhe no centro (separadas por \n). */
	FString Detail;
	/** Ícone: /Game/UI/HUD/V2/T_HUD2_Icon_<Icon>. */
	FName Icon;
	/** Tem o item (arma achada / pelo menos 1 na bolsa / item-chave coletado). */
	bool bOwned = false;
	/** Espaço reservado para o futuro (sempre bloqueado). */
	bool bFuture = false;
	/** Setor sem item. */
	bool bEmpty = false;
	/** Item-chave (não é usado pela roda). */
	bool bKeyItem = false;
	/** Quantidade na bolsa (consumível) e limite; -1 = não mostra. */
	int32 Count = -1;
	int32 MaxCount = -1;
	/** Arma de fogo: no pente / reserva; -1 = não mostra. */
	int32 Loaded = -1;
	int32 Reserve = -1;
	/** É o que está na mão agora. */
	bool bCurrent = false;
	/** Atributos 0..1 (Dano, Precisão, Cadência, Alcance), tirados das definições das armas. */
	bool bHasStats = false;
	float StatDamage = 0.f;
	float StatAccuracy = 0.f;
	float StatFireRate = 0.f;
	float StatRange = 0.f;
};

namespace JRItemWheel
{
	/** Setores por aba. */
	constexpr int32 NumSectors = static_cast<int32>(EJRWheelEntry::Count);
	constexpr int32 NumTabs = 2;
	constexpr int32 TabWeapons = 0;
	constexpr int32 TabConsumables = 1;

	/** O que fica em cada setor de cada aba (0 = topo, sentido horário). */
	inline EJRWheelEntry EntryAt(int32 Tab, int32 Sector)
	{
		static const EJRWheelEntry Weapons[NumSectors] = {
			EJRWheelEntry::Unarmed, EJRWheelEntry::Melee, EJRWheelEntry::Pistol, EJRWheelEntry::Shotgun,
			EJRWheelEntry::Sniper, EJRWheelEntry::Grenade, EJRWheelEntry::Empty, EJRWheelEntry::Empty };
		static const EJRWheelEntry Consumables[NumSectors] = {
			EJRWheelEntry::NoItem, EJRWheelEntry::Bandage, EJRWheelEntry::Medkit, EJRWheelEntry::Fury,
			EJRWheelEntry::CarKey, EJRWheelEntry::Fuel, EJRWheelEntry::Explosive, EJRWheelEntry::Empty };
		if (Sector < 0 || Sector >= NumSectors)
		{
			return EJRWheelEntry::Empty;
		}
		return Tab == TabConsumables ? Consumables[Sector] : Weapons[Sector];
	}

	/** Aba e setor onde um item fica (-1 se não estiver na roda). */
	inline bool FindEntry(EJRWheelEntry Entry, int32& OutTab, int32& OutSector)
	{
		for (int32 TabIndex = 0; TabIndex < NumTabs; ++TabIndex)
		{
			for (int32 SectorIndex = 0; SectorIndex < NumSectors; ++SectorIndex)
			{
				if (EntryAt(TabIndex, SectorIndex) == Entry)
				{
					OutTab = TabIndex;
					OutSector = SectorIndex;
					return true;
				}
			}
		}
		OutTab = -1;
		OutSector = -1;
		return false;
	}

	/** Ângulo do centro do setor em graus (0 = topo, sentido horário). */
	inline float SectorCenterDeg(int32 Index)
	{
		return static_cast<float>(Index) * (360.f / static_cast<float>(NumSectors));
	}

	/**
	 * Setor apontado por uma direção (X = direita, Y = para cima). -1 se o comprimento for menor que DeadZone
	 * (aí a roda mantém o destaque anterior, como no GTA).
	 */
	inline int32 SectorFromDirection(const FVector2D& Dir, float DeadZone)
	{
		if (Dir.Size() < static_cast<double>(DeadZone))
		{
			return -1;
		}
		const float AngleDeg = FMath::RadiansToDegrees(FMath::Atan2(static_cast<float>(Dir.X), static_cast<float>(Dir.Y)));
		const float Step = 360.f / static_cast<float>(NumSectors);
		const int32 Raw = FMath::FloorToInt((AngleDeg + Step * 0.5f) / Step);
		return ((Raw % NumSectors) + NumSectors) % NumSectors;
	}

	/**
	 * Atributo 0..1 para as barrinhas da roda (raiz quadrada: diferenças pequenas continuam visíveis).
	 * Value / Max, preso entre MinShown e 1.
	 */
	inline float StatFraction(float Value, float Max, float MinShown = 0.06f)
	{
		if (Max <= 0.f)
		{
			return MinShown;
		}
		return FMath::Clamp(FMath::Sqrt(FMath::Max(0.f, Value) / Max), MinShown, 1.f);
	}
}

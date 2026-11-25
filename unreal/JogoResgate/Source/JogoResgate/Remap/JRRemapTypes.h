// Copyright utrazin. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"
#include "Characters/JRCharacter.h"
#include "JRRemapTypes.generated.h"

/**
 * [Remap F1] Tipos e fórmulas do loop cidade -> arena (docs/design/REMAP_CIDADE_ARENA.md, seções 6 e 7).
 * As fórmulas ficam aqui, puras, para serem testadas e ajustadas num lugar só.
 */

/** Cartas da corrida (estilo Archero, seção 6.6). Somem no fim da corrida. */
UENUM(BlueprintType)
enum class EJRRunCard : uint8
{
	Damage,      // +15% dano
	FireRate,    // +15% cadência
	MoveSpeed,   // +12% velocidade
	MaxHealth,   // +25% vida máxima (e cura o que ganhou)
	LifeOnKill,  // cura 2% da vida máxima a cada abate
	Credits,     // +30% créditos nesta corrida
	HealNow,     // cura 50% agora
	Energy,      // +25% energia por abate
	Armor,       // -15% dano recebido
	Count UMETA(Hidden)
};

/** O que o vendedor da cidade faz. */
UENUM(BlueprintType)
enum class EJRShopType : uint8
{
	Armeiro,  // Krug: vende armas
	Bancada,  // Ix-Vel: +10% de dano por nível
	Portao,   // Kaar: sai para a arena
	Arvore    // [A-098] Árvore-Mãe: árvore de melhorias permanentes paga com cristais
};

/** Atributos da corrida (multiplicadores que as cartas mexem). */
USTRUCT(BlueprintType)
struct FJRRunStats
{
	GENERATED_BODY()

	UPROPERTY(BlueprintReadOnly, Category = "Run") float Damage = 1.f;
	UPROPERTY(BlueprintReadOnly, Category = "Run") float FireRate = 1.f;
	UPROPERTY(BlueprintReadOnly, Category = "Run") float MoveSpeed = 1.f;
	UPROPERTY(BlueprintReadOnly, Category = "Run") float MaxHealth = 1.f;
	UPROPERTY(BlueprintReadOnly, Category = "Run") float LifeOnKill = 0.f;   // fração da vida máxima
	UPROPERTY(BlueprintReadOnly, Category = "Run") float Credits = 1.f;
	UPROPERTY(BlueprintReadOnly, Category = "Run") float Energy = 1.f;
	UPROPERTY(BlueprintReadOnly, Category = "Run") float DamageTaken = 1.f;
};

/** Relatório do fim da corrida (mostrado na cidade). */
USTRUCT(BlueprintType)
struct FJRRunReport
{
	GENERATED_BODY()

	UPROPERTY(BlueprintReadOnly, Category = "Run") bool bExtracted = false;
	UPROPERTY(BlueprintReadOnly, Category = "Run") int32 SectorLevel = 1;
	UPROPERTY(BlueprintReadOnly, Category = "Run") int32 Waves = 0;
	UPROPERTY(BlueprintReadOnly, Category = "Run") int32 Kills = 0;
	UPROPERTY(BlueprintReadOnly, Category = "Run") int32 RunLevel = 1;
	UPROPERTY(BlueprintReadOnly, Category = "Run") int64 CreditsEarned = 0;
	UPROPERTY(BlueprintReadOnly, Category = "Run") float Multiplier = 1.f;
	UPROPERTY(BlueprintReadOnly, Category = "Run") int64 CreditsKept = 0;
	UPROPERTY(BlueprintReadOnly, Category = "Run") bool bNewRecord = false;
	/** [Remap F2] Objetivos da arena cumpridos (principal + opcional). */
	UPROPERTY(BlueprintReadOnly, Category = "Run") int32 ObjectivesCompleted = 0;
	/** [Remap F2] Maior sequência de abates sem levar dano. */
	UPROPERTY(BlueprintReadOnly, Category = "Run") int32 MaxCombo = 0;
	/** [A-098] Cristais ganhos na corrida (moeda da Árvore-Mãe). */
	UPROPERTY(BlueprintReadOnly, Category = "Run") int32 CrystalsEarned = 0;
};

/** [A-098] O que cada nó da Árvore-Mãe melhora. */
enum class EJRTreeStat : uint8
{
	Damage,       // +x dano (somado ao 1,0 base, antes das cartas)
	FireRate,
	MaxHealth,
	MoveSpeed,
	DamageTaken,  // negativo: menos dano recebido
	LifeOnKill,   // fração da vida máxima por abate
	Credits,
	Energy,
	Crystals,     // +x cristais no fim da corrida
	StartCards,   // cartas para escolher logo no começo
	ReserveAmmo   // munição reserva extra ao sair da cidade
};

/** [A-098] Um nó da árvore (tabela fixa em JRRemapTypes.cpp; docs/design/ARVORE_MAE.md). */
struct FJRTreeNodeDef
{
	FName Id;
	int32 Branch = 0;          // 0 raiz, 1 Fúria, 2 Casca, 3 Raízes, 4 Vento
	int32 Depth = 0;           // posição no galho (0 = perto do tronco)
	const TCHAR* Label = TEXT("");
	const TCHAR* Detail = TEXT("");   // "%s" = efeito do próximo nível
	const TCHAR* Icon = TEXT("R_Star");
	EJRTreeStat Stat = EJRTreeStat::Damage;
	float PerRank = 0.f;
	int32 MaxRank = 1;
	int64 BaseCost = 1;        // cristais do 1o nível
	float CostGrowth = 1.35f;
	FName Requires;            // nó pai (None = sem)
	int32 RequiresRank = 1;
};

struct JOGORESGATE_API FJRSkillTree
{
	static const TArray<FJRTreeNodeDef>& Nodes();
	static const FJRTreeNodeDef* Find(FName Id);
	/** Cristais para ir do nível Rank para Rank+1. */
	static int64 Cost(const FJRTreeNodeDef& Node, int32 Rank);
	static FString BranchName(int32 Branch);
	/** Texto do efeito de N níveis (ex.: "+12% dano"). */
	static FString EffectText(const FJRTreeNodeDef& Node, int32 Ranks);
};

/** Fórmulas e números do REMAP (seção 0 e 7.2). */
struct JOGORESGATE_API FJRRemapRules
{
	/** Mapas do protótipo F1 (criados por tools/unreal/build_remap_f1.py). */
	static const TCHAR* CityMap;
	static const TCHAR* ArenaMap;

	/** Custo do próximo nível da Bancada: 300 x 1,17^(nível+1). Nível 0 -> 1 custa 351. */
	static int64 BenchCost(int32 CurrentLevel);
	/** +10% de dano por nível. */
	static float BenchDamageMultiplier(int32 Level) { return 1.f + 0.10f * FMath::Max(0, Level); }

	/** Preço fixo das armas do Armeiro (0 = de graça/não vende). */
	static int64 WeaponPrice(EJRWeaponSlot Slot);

	/** Vida do zumbi: x 1,14^(L-1). L efetivo = nível do setor + 0,5 por onda. */
	static float EnemyHealthScale(float EffectiveLevel) { return FMath::Pow(1.14f, FMath::Max(0.f, EffectiveLevel - 1.f)); }
	/** Créditos por ponto de custo do inimigo: 6 x 1,11^(L-1). */
	static float CreditsPerCost(float EffectiveLevel) { return 6.f * FMath::Pow(1.11f, FMath::Max(0.f, EffectiveLevel - 1.f)); }
	static float GetEffectiveLevel(int32 SectorLevel, int32 Wave) { return FMath::Max(1, SectorLevel) + 0.5f * FMath::Max(0, Wave - 1); }

	/** Energia para sair do nível de corrida N para N+1: 20 x 1,17^(N-1). */
	static float EnergyForLevel(int32 RunLevel) { return 20.f * FMath::Pow(1.17f, FMath::Max(0, RunLevel - 1)); }

	/** Inimigos na onda W: 6 + 2W (onda 1 = 8). */
	static int32 WaveEnemyCount(int32 Wave) { return 6 + 2 * FMath::Max(1, Wave); }

	/** [Remap F2] Orçamento do diretor por onda (REMAP 6.3): (8 + 3W) x (1 + 0,12 (L-1)). Onda 1 nível 1 = 11. */
	static int32 DirectorWaveBudget(int32 Wave, int32 SectorLevel)
	{
		return FMath::RoundToInt((8.f + 3.f * FMath::Max(1, Wave)) * (1.f + 0.12f * (FMath::Max(1, SectorLevel) - 1)));
	}
	/** [Remap F2] Pontos por segundo do diretor: (1,2 + 0,12W) x (1 + 0,15 (L-1)). Mais rápido em nível alto. */
	static float DirectorIncomePerSecond(int32 Wave, int32 SectorLevel)
	{
		return (1.2f + 0.12f * FMath::Max(1, Wave)) * (1.f + 0.15f * (FMath::Max(1, SectorLevel) - 1));
	}
	/** [Remap F2] Pressão (custo vivo + fila) que fecha um pico antes do respiro: 6 + 2W. */
	static int32 DirectorPeakCost(int32 Wave) { return 6 + 2 * FMath::Max(1, Wave); }

	/** Multiplicador da extração depois de W ondas vencidas: x1,0 (3), x1,25 (6), x1,5 (9)... */
	static float ExtractionMultiplier(int32 WavesCleared) { return 1.f + 0.25f * FMath::Max(0, WavesCleared / 3 - 1); }

	/** Contrato de morte (decisão do usuário, REMAP seção 0): fica com 50% dos créditos e 25% dos cristais. */
	static constexpr float DeathKeepCredits = 0.5f;
	static constexpr float DeathKeepCrystals = 0.25f;

	/** [A-098] Arena liberada pelo recorde: nível novo a cada 6 ondas, até 5. Também libera os bairros da cidade. */
	static int32 UnlockedArenaLevel(int32 BestWave) { return FMath::Clamp(1 + FMath::Max(0, BestWave) / 6, 1, 5); }
	/** [A-098] Cristais da corrida: (ondas + 2 x objetivos) x (1 + 0,15 (setor-1)); morrer guarda 25%. */
	static int32 RunCrystals(int32 Waves, int32 Objectives, int32 SectorLevel, bool bExtracted, float Bonus)
	{
		const float Raw = (FMath::Max(0, Waves) + 2.f * FMath::Max(0, Objectives)) * (1.f + 0.15f * (FMath::Max(1, SectorLevel) - 1)) * FMath::Max(0.f, Bonus);
		return FMath::Max(Waves > 0 ? 1 : 0, FMath::RoundToInt(bExtracted ? Raw : Raw * DeathKeepCrystals));
	}

	/** No máximo quantas escolhas de carta podem ficar guardadas. */
	static constexpr int32 MaxBankedChoices = 3;

	static FText CardTitle(EJRRunCard Card);
	static FText CardDescription(EJRRunCard Card);
	/** Peso no sorteio (maior = mais comum). */
	static int32 CardWeight(EJRRunCard Card);
	/** Raridade só para cor: 0 comum, 1 rara, 2 épica. */
	static int32 CardRarity(EJRRunCard Card);
	/** Aplica a carta nos atributos (efeitos instantâneos como "cura agora" ficam com quem chama). */
	static void ApplyCard(EJRRunCard Card, FJRRunStats& Stats);
};

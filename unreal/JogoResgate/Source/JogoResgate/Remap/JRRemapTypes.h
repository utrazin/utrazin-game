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
	Portao    // Kaar: sai para a arena
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

	/** Multiplicador da extração depois de W ondas vencidas: x1,0 (3), x1,25 (6), x1,5 (9)... */
	static float ExtractionMultiplier(int32 WavesCleared) { return 1.f + 0.25f * FMath::Max(0, WavesCleared / 3 - 1); }

	/** Contrato de morte (decisão do usuário, REMAP seção 0): fica com 50% dos créditos e 25% dos cristais. */
	static constexpr float DeathKeepCredits = 0.5f;
	static constexpr float DeathKeepCrystals = 0.25f;

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

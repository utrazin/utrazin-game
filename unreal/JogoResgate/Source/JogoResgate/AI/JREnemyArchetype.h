// Copyright utrazin. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"
#include "Engine/DataAsset.h"
#include "JREnemyArchetype.generated.h"

class UAnimMontage;
class USoundBase;

UENUM(BlueprintType)
enum class EJREnemyAttackType : uint8
{
	Melee,
	/** Projétil com travessia (flecha): usa ProjectileClass e antecipação. */
	Projectile,
	/** Hitscan em rajadas (pistola) com antecipação pela velocidade nominal. */
	Burst
};

/** Arquétipo de inimigo (DA_Enemy_*). Valores iniciais em docs/gameplay/ENEMY_AI.md. */
UCLASS(BlueprintType)
class JOGORESGATE_API UJREnemyArchetype : public UPrimaryDataAsset
{
	GENERATED_BODY()

public:
	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Enemy")
	FName ArchetypeId = TEXT("ENM-001");

	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Enemy", meta = (ClampMin = "1"))
	float MaxHealth = 60.f;

	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Enemy|Movement", meta = (Units = "cm/s"))
	float MoveSpeed = 380.f;

	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Enemy|Perception", meta = (Units = "cm"))
	float AggroRadius = 2500.f;

	/** Maior que AggroRadius para evitar oscilação (histerese). */
	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Enemy|Perception", meta = (Units = "cm"))
	float LoseAggroRadius = 3500.f;

	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Enemy|Perception", meta = (Units = "s"))
	float AlertDuration = 1.5f;

	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Enemy|Combat")
	EJREnemyAttackType AttackType = EJREnemyAttackType::Melee;

	/** Distância em que ataca (corpo a corpo ~150; arqueiro ~1800 = distância preferida). */
	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Enemy|Combat", meta = (Units = "cm"))
	float AttackRange = 150.f;

	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Enemy|Combat")
	float AttackDamage = 15.f;

	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Enemy|Combat", meta = (Units = "s"))
	float AttackInterval = 1.f;

	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Enemy|Combat", meta = (ClampMin = "1"))
	int32 BurstCount = 1;

	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Enemy|Combat", meta = (Units = "s"))
	float BurstShotInterval = 0.15f;

	/** Velocidade usada na antecipação (cm/s). Para Burst, velocidade nominal do tiro. */
	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Enemy|Combat")
	float ProjectileSpeed = 3000.f;

	/** Imprecisão: meio-ângulo do cone em graus. Nunca 0 para ataques à distância. */
	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Enemy|Combat", meta = (ClampMin = "0"))
	float SpreadHalfAngleDegrees = 3.f;

	/** Ator com UProjectileMovementComponent (ex.: BP_Arrow). */
	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Enemy|Combat")
	TSubclassOf<AActor> ProjectileClass;

	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Enemy|Feedback")
	TObjectPtr<UAnimMontage> AttackMontage;

	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Enemy|Feedback")
	TObjectPtr<UAnimMontage> HitReactMontage;

	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Enemy|Feedback")
	TObjectPtr<USoundBase> AlertSound;

	/** Tempo até o corpo ser removido após a morte. */
	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Enemy", meta = (Units = "s"))
	float CorpseLifetime = 10.f;

	// ---------------------------------------------------------------- Vida própria (A-048)

	/** Vagando: distância mínima do ponto de origem até o próximo destino. */
	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Enemy|Life", meta = (Units = "cm", ClampMin = "0"))
	float WanderRadiusMin = 600.f;

	/** Vagando: distância máxima do ponto de origem (o zumbi nunca se afasta muito de "casa"). */
	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Enemy|Life", meta = (Units = "cm", ClampMin = "0"))
	float WanderRadiusMax = 2000.f;

	/** Velocidade arrastada ao vagar: cada zumbi sorteia uma entre o mínimo e o máximo. */
	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Enemy|Life", meta = (Units = "cm/s", ClampMin = "10"))
	float WanderSpeedMin = 90.f;

	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Enemy|Life", meta = (Units = "cm/s", ClampMin = "10"))
	float WanderSpeedMax = 140.f;

	/** Pausa entre uma caminhada e outra (sorteada a cada vez). */
	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Enemy|Life", meta = (Units = "s", ClampMin = "0"))
	float WanderPauseMin = 2.f;

	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Enemy|Life", meta = (Units = "s", ClampMin = "0"))
	float WanderPauseMax = 6.f;

	/** Chance de virar para outro lado durante a pausa. */
	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Enemy|Life", meta = (ClampMin = "0", ClampMax = "1"))
	float TurnChance = 0.45f;

	/** Chance de seguir um zumbi vizinho (manada) em vez de andar sozinho. */
	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Enemy|Life", meta = (ClampMin = "0", ClampMax = "1"))
	float HerdChance = 0.3f;

	/** Colado num destroço/corpo: chance de ficar "comendo" agachado. */
	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Enemy|Life", meta = (ClampMin = "0", ClampMax = "1"))
	float FeedChance = 0.6f;

	/** Colado numa parede/destroço: chance de ficar batendo nele. */
	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Enemy|Life", meta = (ClampMin = "0", ClampMax = "1"))
	float BangChance = 0.35f;

	/** Chance de um "espasmo" (HitReact lento) numa pausa quando não há IdleVariationMontages. 0 desliga. */
	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Enemy|Life", meta = (ClampMin = "0", ClampMax = "1"))
	float IdleTwitchChance = 0.12f;

	/** Variações tocadas de vez em quando parado (coçar, olhar em volta, rosnar). Opcional. */
	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Enemy|Life")
	TArray<TObjectPtr<UAnimMontage>> IdleVariationMontages;

	/** "Comendo" agachado perto de corpo/destroço. Vazio: usa o AttackMontage devagar. */
	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Enemy|Life")
	TObjectPtr<UAnimMontage> FeedMontage;

	/** Andar rápido indo ver um barulho. */
	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Enemy|Life", meta = (Units = "cm/s", ClampMin = "10"))
	float InvestigateSpeed = 230.f;

	/** Tempo máximo procurando o barulho antes de desistir e voltar a vagar. */
	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Enemy|Perception", meta = (Units = "s", ClampMin = "1"))
	float InvestigateTime = 15.f;

	/** Meio-ângulo do cone de visão (55 = cone de 110 graus). Perseguindo, não usa cone. */
	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Enemy|Perception", meta = (ClampMin = "5", ClampMax = "180"))
	float SightHalfAngleDegrees = 55.f;

	/** Abaixo desta distância percebe o jogador mesmo de costas (passos, cheiro). */
	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Enemy|Perception", meta = (Units = "cm", ClampMin = "0"))
	float CloseSenseRadius = 400.f;

	/** Multiplica o raio de todo barulho que este zumbi ouve (1 = normal). */
	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Enemy|Perception", meta = (ClampMin = "0"))
	float HearingScale = 1.f;

	/** Chance de nascer "corredor" (persegue na MoveSpeed). Os outros perseguem mais devagar. */
	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Enemy|Movement", meta = (ClampMin = "0", ClampMax = "1"))
	float RunnerChance = 1.f;

	/** Velocidade de perseguição dos não corredores = MoveSpeed x este valor. */
	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Enemy|Movement", meta = (ClampMin = "0.1", ClampMax = "1"))
	float WalkerChaseSpeedScale = 0.72f;

	/**
	 * Variação de velocidade das animações por zumbi (0,1 = de 0,9x a 1,1x): ninguém anda sincronizado.
	 * Com LocomotionRunSpeed > 0 só vale parado (andando, a animação segue a velocidade real: A-081).
	 */
	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Enemy|Feedback", meta = (ClampMin = "0", ClampMax = "0.5"))
	float AnimRateJitter = 0.1f;

	// ---------------------------------------------------------------- Passo x velocidade (A-081)

	/**
	 * Velocidade (cm/s) em que a blend space toca a animação de CORRER sem o pé escorregar
	 * (medida pelo tools/unreal/setup_zombie_feel.py). Acima dela a animação acelera junto
	 * (até MaxLocomotionRate) e a perseguição não passa de LocomotionRunSpeed x MaxLocomotionRate.
	 * 0 = desligado (comportamento antigo).
	 */
	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Enemy|Movement", meta = (Units = "cm/s", ClampMin = "0"))
	float LocomotionRunSpeed = 0.f;

	/** Maior aceleração da animação de correr (1,5 = 50% mais rápida que a original). */
	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Enemy|Movement", meta = (ClampMin = "1", ClampMax = "3"))
	float MaxLocomotionRate = 1.5f;
};

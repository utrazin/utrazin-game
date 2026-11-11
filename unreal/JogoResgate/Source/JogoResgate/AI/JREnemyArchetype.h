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
};

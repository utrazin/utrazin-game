// Copyright utrazin. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"
#include "JREnemyStateLogic.generated.h"

/** Estados de IA do GDD 8.2. */
UENUM(BlueprintType)
enum class EJREnemyState : uint8
{
	Idle,
	Patrol,
	Alert,
	Chase,
	Attack,
	Dead
};

/** Parâmetros de decisão (copiados do UJREnemyArchetype). */
struct FJREnemyDecisionParams
{
	float AggroRadius = 2500.f;
	float LoseAggroRadius = 3500.f;
	float AttackRange = 150.f;
	float AlertDuration = 1.5f;
	bool bHasPatrol = false;
};

/** Entrada de uma decisão. */
struct FJREnemyDecisionInput
{
	EJREnemyState Current = EJREnemyState::Idle;
	float DistanceToTarget = TNumericLimits<float>::Max();
	bool bHasLineOfSight = false;
	bool bIsDead = false;
	float TimeInState = 0.f;
};

/**
 * Máquina de estados pura (JR.AI.StateLogic.*). Pode ser chamada por tasks de StateTree
 * ou pelo "cérebro" simples do AJREnemyCharacter.
 */
struct JOGORESGATE_API FJREnemyStateLogic
{
	static EJREnemyState Decide(const FJREnemyDecisionInput& In, const FJREnemyDecisionParams& P);
};

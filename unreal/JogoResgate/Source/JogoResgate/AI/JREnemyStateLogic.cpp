// Copyright utrazin. All Rights Reserved.

#include "AI/JREnemyStateLogic.h"

EJREnemyState FJREnemyStateLogic::Decide(const FJREnemyDecisionInput& In, const FJREnemyDecisionParams& P)
{
	if (In.bIsDead || In.Current == EJREnemyState::Dead)
	{
		return EJREnemyState::Dead;
	}

	const EJREnemyState Calm = P.bHasPatrol ? EJREnemyState::Patrol : EJREnemyState::Idle;
	const bool bEngaged = In.Current == EJREnemyState::Alert || In.Current == EJREnemyState::Chase
		|| In.Current == EJREnemyState::Attack;

	// Perde o alvo além do raio de desistência (histerese evita oscilar na borda do aggro).
	if (bEngaged && In.DistanceToTarget > P.LoseAggroRadius)
	{
		return Calm;
	}

	if (!bEngaged)
	{
		const bool bNoticed = In.DistanceToTarget <= P.AggroRadius && In.bHasLineOfSight;
		return bNoticed ? EJREnemyState::Alert : Calm;
	}

	// Alert telegrafa o ataque por um tempo mínimo antes de agir.
	if (In.Current == EJREnemyState::Alert && In.TimeInState < P.AlertDuration)
	{
		return EJREnemyState::Alert;
	}

	if (In.DistanceToTarget <= P.AttackRange && In.bHasLineOfSight)
	{
		return EJREnemyState::Attack;
	}
	return EJREnemyState::Chase;
}

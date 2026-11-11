// Copyright utrazin. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"

/**
 * Mira com antecipação e dispersão para inimigos à distância. Lógica pura (JR.AI.AimPrediction.*).
 */
struct JOGORESGATE_API FJRAimPrediction
{
	/**
	 * Ponto de interceptação para um projétil com velocidade constante contra um alvo com velocidade constante.
	 * Retorna false se não houver solução (alvo mais rápido que o projétil e se afastando); nesse caso
	 * OutAimPoint recebe a posição atual do alvo.
	 */
	static bool PredictInterceptPoint(const FVector& ShooterLocation, const FVector& TargetLocation,
		const FVector& TargetVelocity, double ProjectileSpeed, FVector& OutAimPoint, double& OutTimeToHit);

	/** Direção com dispersão cônica (meio-ângulo em graus). Com 0 retorna a direção normalizada. */
	static FVector ApplySpread(const FVector& Direction, float HalfAngleDegrees, FRandomStream& Stream);
};

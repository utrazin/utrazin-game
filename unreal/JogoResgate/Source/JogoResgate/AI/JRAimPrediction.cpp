// Copyright utrazin. All Rights Reserved.

#include "AI/JRAimPrediction.h"

bool FJRAimPrediction::PredictInterceptPoint(const FVector& ShooterLocation, const FVector& TargetLocation,
	const FVector& TargetVelocity, double ProjectileSpeed, FVector& OutAimPoint, double& OutTimeToHit)
{
	OutAimPoint = TargetLocation;
	OutTimeToHit = 0.0;
	if (ProjectileSpeed <= 0.0)
	{
		return false;
	}

	// |R + V t| = S t  =>  (V.V - S^2) t^2 + 2 (R.V) t + R.R = 0
	const FVector R = TargetLocation - ShooterLocation;
	const double A = FVector::DotProduct(TargetVelocity, TargetVelocity) - ProjectileSpeed * ProjectileSpeed;
	const double B = 2.0 * FVector::DotProduct(R, TargetVelocity);
	const double C = FVector::DotProduct(R, R);

	double T = -1.0;
	if (FMath::Abs(A) < KINDA_SMALL_NUMBER)
	{
		if (FMath::Abs(B) > KINDA_SMALL_NUMBER)
		{
			T = -C / B;
		}
	}
	else
	{
		const double Disc = B * B - 4.0 * A * C;
		if (Disc >= 0.0)
		{
			const double Sqrt = FMath::Sqrt(Disc);
			const double T1 = (-B - Sqrt) / (2.0 * A);
			const double T2 = (-B + Sqrt) / (2.0 * A);
			const double MinT = FMath::Min(T1, T2);
			const double MaxT = FMath::Max(T1, T2);
			T = MinT > 0.0 ? MinT : MaxT;
		}
	}

	if (T <= 0.0)
	{
		return false;
	}
	OutTimeToHit = T;
	OutAimPoint = TargetLocation + TargetVelocity * T;
	return true;
}

FVector FJRAimPrediction::ApplySpread(const FVector& Direction, float HalfAngleDegrees, FRandomStream& Stream)
{
	const FVector Dir = Direction.GetSafeNormal();
	if (HalfAngleDegrees <= 0.f || Dir.IsNearlyZero())
	{
		return Dir;
	}
	return Stream.VRandCone(Dir, FMath::DegreesToRadians(HalfAngleDegrees));
}

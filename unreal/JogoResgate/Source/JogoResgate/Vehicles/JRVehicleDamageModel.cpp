// Copyright utrazin. All Rights Reserved.

#include "Vehicles/JRVehicleDamageModel.h"

FJRVehicleDamageState::FJRVehicleDamageState()
{
	Reset();
}

void FJRVehicleDamageState::Reset()
{
	for (int32 i = 0; i < NumZones; ++i)
	{
		ZoneHealth[i] = MaxZoneHealth;
	}
	for (int32 i = 0; i < NumWheels; ++i)
	{
		bTireFlat[i] = false;
	}
}

float FJRVehicleDamageState::ApplyZoneDamage(EJRVehicleZone Zone, float Amount)
{
	const int32 Index = static_cast<int32>(Zone);
	if (Index < 0 || Index >= NumZones || Amount <= 0.f)
	{
		return 0.f;
	}
	const float Before = ZoneHealth[Index];
	ZoneHealth[Index] = FMath::Clamp(Before - Amount, 0.f, MaxZoneHealth);
	return Before - ZoneHealth[Index];
}

void FJRVehicleDamageState::SetTireFlat(EJRWheel Wheel, bool bFlat)
{
	const int32 Index = static_cast<int32>(Wheel);
	if (Index >= 0 && Index < NumWheels)
	{
		bTireFlat[Index] = bFlat;
	}
}

bool FJRVehicleDamageState::IsTireFlat(EJRWheel Wheel) const
{
	const int32 Index = static_cast<int32>(Wheel);
	return Index >= 0 && Index < NumWheels && bTireFlat[Index];
}

int32 FJRVehicleDamageState::NumFlatTires() const
{
	int32 Count = 0;
	for (int32 i = 0; i < NumWheels; ++i)
	{
		Count += bTireFlat[i] ? 1 : 0;
	}
	return Count;
}

float FJRVehicleDamageState::GetZoneHealth(EJRVehicleZone Zone) const
{
	const int32 Index = static_cast<int32>(Zone);
	return (Index >= 0 && Index < NumZones) ? ZoneHealth[Index] : 0.f;
}

float FJRVehicleDamageState::GetIntegrity() const
{
	float WeightedSum = 0.f;
	float TotalWeight = 0.f;
	for (int32 i = 0; i < NumZones; ++i)
	{
		const float Weight = (i == static_cast<int32>(EJRVehicleZone::Engine)) ? 2.f : 1.f;
		WeightedSum += ZoneHealth[i] * Weight;
		TotalWeight += Weight;
	}
	return FMath::Clamp(WeightedSum / (TotalWeight * MaxZoneHealth), 0.f, 1.f);
}

float FJRVehicleDamageState::GetEngineTorqueScale() const
{
	const float Alpha = GetZoneHealth(EJRVehicleZone::Engine) / MaxZoneHealth;
	return FMath::Lerp(MinEngineTorqueScale, 1.f, FMath::Clamp(Alpha, 0.f, 1.f));
}

bool FJRVehicleDamageState::ShouldEmitEngineSmoke() const
{
	return GetZoneHealth(EJRVehicleZone::Engine) < SmokeEngineThreshold;
}

bool FJRVehicleDamageState::IsDisabled() const
{
	return GetZoneHealth(EJRVehicleZone::Engine) <= 0.f || GetIntegrity() < DisabledIntegrity;
}

float FJRVehicleDamageState::GetSteeringBias() const
{
	float Bias = 0.f;
	if (IsTireFlat(EJRWheel::FrontLeft) || IsTireFlat(EJRWheel::RearLeft))
	{
		Bias -= FlatTireSteeringBias;
	}
	if (IsTireFlat(EJRWheel::FrontRight) || IsTireFlat(EJRWheel::RearRight))
	{
		Bias += FlatTireSteeringBias;
	}
	return Bias;
}

float FJRVehicleDamageState::ImpactDamageFromSpeed(float RelativeSpeedKmh)
{
	return FMath::Max(0.f, (RelativeSpeedKmh - ImpactSpeedThresholdKmh) * ImpactDamagePerKmh);
}

EJRVehicleZone FJRVehicleDamageState::ZoneFromLocalPoint(const FVector& LocalPoint, float HalfLength, float HalfWidth)
{
	const double NormX = HalfLength > 0.f ? LocalPoint.X / HalfLength : 0.0;
	const double NormY = HalfWidth > 0.f ? LocalPoint.Y / HalfWidth : 0.0;
	if (FMath::Abs(NormX) >= FMath::Abs(NormY))
	{
		return NormX >= 0.0 ? EJRVehicleZone::Front : EJRVehicleZone::Rear;
	}
	return NormY >= 0.0 ? EJRVehicleZone::Right : EJRVehicleZone::Left;
}

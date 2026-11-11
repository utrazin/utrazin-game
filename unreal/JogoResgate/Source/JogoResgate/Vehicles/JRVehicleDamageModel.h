// Copyright utrazin. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"
#include "JRVehicleDamageModel.generated.h"

/** Zonas de dano do veículo (docs/gameplay/VEHICLE.md). */
UENUM(BlueprintType)
enum class EJRVehicleZone : uint8
{
	Front,
	Rear,
	Left,
	Right,
	Engine,
	Count UMETA(Hidden)
};

/** Rodas na ordem do WheelSetups do Chaos: FL, FR, RL, RR. */
UENUM(BlueprintType)
enum class EJRWheel : uint8
{
	FrontLeft,
	FrontRight,
	RearLeft,
	RearRight,
	Count UMETA(Hidden)
};

/**
 * Lógica pura de dano do veículo. Não depende de mundo nem de UObject:
 * testada por Automation Tests (JR.Vehicle.DamageModel.*) e por tests/cpp.
 */
struct JOGORESGATE_API FJRVehicleDamageState
{
	static constexpr int32 NumZones = static_cast<int32>(EJRVehicleZone::Count);
	static constexpr int32 NumWheels = static_cast<int32>(EJRWheel::Count);
	static constexpr float MaxZoneHealth = 100.f;
	static constexpr float MinEngineTorqueScale = 0.35f;
	static constexpr float SmokeEngineThreshold = 25.f;
	static constexpr float DisabledIntegrity = 0.1f;
	static constexpr float FlatTireFrictionScale = 0.45f;
	static constexpr float FlatTireRadiusScale = 0.88f;
	static constexpr float FlatTireSteeringBias = 0.12f;
	static constexpr float ImpactSpeedThresholdKmh = 15.f;
	static constexpr float ImpactDamagePerKmh = 0.8f;

	FJRVehicleDamageState();

	/** Aplica dano a uma zona. Retorna o dano efetivamente aplicado. */
	float ApplyZoneDamage(EJRVehicleZone Zone, float Amount);

	/** Repara todas as zonas e pneus (usado ao recarregar checkpoint). */
	void Reset();

	void SetTireFlat(EJRWheel Wheel, bool bFlat);
	bool IsTireFlat(EJRWheel Wheel) const;
	int32 NumFlatTires() const;

	float GetZoneHealth(EJRVehicleZone Zone) const;

	/** Integridade global 0..1: média ponderada das zonas (motor com peso 2). */
	float GetIntegrity() const;

	/** Escala de torque do motor: 1.0 com motor intacto até MinEngineTorqueScale com motor destruído. */
	float GetEngineTorqueScale() const;

	bool ShouldEmitEngineSmoke() const;

	/** Inutilizado quando o motor zera ou a integridade cai abaixo de DisabledIntegrity. */
	bool IsDisabled() const;

	/**
	 * Viés de direção causado por pneus furados (-1..1, positivo = puxa para a direita).
	 * Pneu esquerdo furado puxa para a esquerda e vice-versa.
	 */
	float GetSteeringBias() const;

	/** Dano de impacto a partir da velocidade relativa em km/h. */
	static float ImpactDamageFromSpeed(float RelativeSpeedKmh);

	/**
	 * Zona atingida a partir de um ponto no espaço local do veículo (X frente, Y direita).
	 * HalfLength/HalfWidth: meia extensão do chassi em cm.
	 */
	static EJRVehicleZone ZoneFromLocalPoint(const FVector& LocalPoint, float HalfLength, float HalfWidth);

private:
	float ZoneHealth[NumZones];
	bool bTireFlat[NumWheels];
};

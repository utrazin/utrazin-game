// Copyright utrazin. All Rights Reserved.
// Automation Tests da lógica pura. Rodar: Automation RunTests JR.  (ver tests/unreal/README.md)
// Os mesmos casos rodam fora da engine em tests/cpp/pure_logic_tests.cpp.

#include "AI/JRAimPrediction.h"
#include "AI/JREnemyStateLogic.h"
#include "Combat/JRAmmoState.h"
#include "Misc/AutomationTest.h"
#include "Vehicles/JRVehicleDamageModel.h"

#if WITH_DEV_AUTOMATION_TESTS

#define JR_TEST_FLAGS (EAutomationTestFlags::EditorContext | EAutomationTestFlags::ClientContext | EAutomationTestFlags::ProductFilter)

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FJRVehicleDamageIntegrityTest, "JR.Vehicle.DamageModel.Integrity", JR_TEST_FLAGS)
bool FJRVehicleDamageIntegrityTest::RunTest(const FString& Parameters)
{
	FJRVehicleDamageState S;
	TestEqual(TEXT("Integridade inicial"), S.GetIntegrity(), 1.f);
	TestEqual(TEXT("Dano aplicado"), S.ApplyZoneDamage(EJRVehicleZone::Front, 30.f), 30.f);
	TestEqual(TEXT("Clamp"), S.ApplyZoneDamage(EJRVehicleZone::Front, 500.f), 70.f);
	TestEqual(TEXT("Negativo ignorado"), S.ApplyZoneDamage(EJRVehicleZone::Front, -5.f), 0.f);
	TestTrue(TEXT("Integridade ponderada"), FMath::IsNearlyEqual(S.GetIntegrity(), 500.f / 600.f, 1e-5f));
	S.ApplyZoneDamage(EJRVehicleZone::Engine, 50.f);
	TestTrue(TEXT("Torque escala"), FMath::IsNearlyEqual(S.GetEngineTorqueScale(), 0.35f + 0.65f * 0.5f, 1e-5f));
	S.ApplyZoneDamage(EJRVehicleZone::Engine, 100.f);
	TestTrue(TEXT("Motor zerado inutiliza"), S.IsDisabled());
	S.Reset();
	TestFalse(TEXT("Reset"), S.IsDisabled());
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FJRVehicleTireTest, "JR.Vehicle.DamageModel.Tires", JR_TEST_FLAGS)
bool FJRVehicleTireTest::RunTest(const FString& Parameters)
{
	FJRVehicleDamageState S;
	TestEqual(TEXT("Sem viés"), S.GetSteeringBias(), 0.f);
	S.SetTireFlat(EJRWheel::FrontLeft, true);
	TestTrue(TEXT("Pneu furado"), S.IsTireFlat(EJRWheel::FrontLeft));
	TestTrue(TEXT("Puxa para a esquerda"), S.GetSteeringBias() < 0.f);
	S.SetTireFlat(EJRWheel::RearRight, true);
	TestEqual(TEXT("Lados se anulam"), S.GetSteeringBias(), 0.f);
	TestEqual(TEXT("Impacto lento"), FJRVehicleDamageState::ImpactDamageFromSpeed(10.f), 0.f);
	TestTrue(TEXT("Impacto 65 km/h"), FMath::IsNearlyEqual(FJRVehicleDamageState::ImpactDamageFromSpeed(65.f), 40.f, 1e-4f));
	TestTrue(TEXT("Zona frente"), FJRVehicleDamageState::ZoneFromLocalPoint(FVector(200, 10, 0), 230, 95) == EJRVehicleZone::Front);
	TestTrue(TEXT("Zona direita"), FJRVehicleDamageState::ZoneFromLocalPoint(FVector(30, 90, 0), 230, 95) == EJRVehicleZone::Right);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FJRAmmoTest, "JR.Combat.Ammo.FireAndReload", JR_TEST_FLAGS)
bool FJRAmmoTest::RunTest(const FString& Parameters)
{
	FJRAmmoState A;
	A.Initialize(12, 20);
	for (int32 i = 0; i < 12; ++i)
	{
		A.ConsumeShot();
	}
	TestFalse(TEXT("Pente vazio"), A.ConsumeShot());
	TestEqual(TEXT("Recarga completa"), A.Reload(), 12);
	TestEqual(TEXT("Reserva"), A.Reserve, 8);
	for (int32 i = 0; i < 12; ++i)
	{
		A.ConsumeShot();
	}
	TestEqual(TEXT("Recarga parcial"), A.Reload(), 8);
	TestEqual(TEXT("Reserva zerada"), A.Reserve, 0);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FJRAimPredictionTest, "JR.AI.AimPrediction.Intercept", JR_TEST_FLAGS)
bool FJRAimPredictionTest::RunTest(const FString& Parameters)
{
	FVector P;
	double T = 0.0;
	TestTrue(TEXT("Alvo parado"), FJRAimPrediction::PredictInterceptPoint(FVector::ZeroVector, FVector(1000, 0, 0), FVector::ZeroVector, 2000.0, P, T));
	TestTrue(TEXT("Tempo"), FMath::IsNearlyEqual(T, 0.5, 1e-9));
	TestTrue(TEXT("Cruzando"), FJRAimPrediction::PredictInterceptPoint(FVector::ZeroVector, FVector(3000, 0, 0), FVector(0, 1000, 0), 3000.0, P, T));
	TestTrue(TEXT("Chega junto"), FMath::IsNearlyEqual((FVector(3000, 0, 0) + FVector(0, 1000, 0) * T).Size(), 3000.0 * T, 1e-3));
	TestFalse(TEXT("Sem solução"), FJRAimPrediction::PredictInterceptPoint(FVector::ZeroVector, FVector(1000, 0, 0), FVector(5000, 0, 0), 2000.0, P, T));

	FRandomStream Stream(42);
	for (int32 i = 0; i < 100; ++i)
	{
		const FVector D = FJRAimPrediction::ApplySpread(FVector::ForwardVector, 5.f, Stream);
		const double AngleDeg = FMath::RadiansToDegrees(FMath::Acos(FMath::Clamp(FVector::DotProduct(D, FVector::ForwardVector), -1.0, 1.0)));
		TestTrue(TEXT("Dentro do cone"), AngleDeg <= 5.0 + 1e-3);
	}
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FJREnemyStateTest, "JR.AI.StateLogic.Transitions", JR_TEST_FLAGS)
bool FJREnemyStateTest::RunTest(const FString& Parameters)
{
	FJREnemyDecisionParams P;
	FJREnemyDecisionInput In;
	In.DistanceToTarget = 3000.f;
	In.bHasLineOfSight = true;
	TestTrue(TEXT("Fora do aggro"), FJREnemyStateLogic::Decide(In, P) == EJREnemyState::Idle);
	In.DistanceToTarget = 2000.f;
	TestTrue(TEXT("Nota o alvo"), FJREnemyStateLogic::Decide(In, P) == EJREnemyState::Alert);
	In.Current = EJREnemyState::Alert;
	In.TimeInState = 2.f;
	TestTrue(TEXT("Persegue"), FJREnemyStateLogic::Decide(In, P) == EJREnemyState::Chase);
	In.Current = EJREnemyState::Chase;
	In.DistanceToTarget = 100.f;
	TestTrue(TEXT("Ataca"), FJREnemyStateLogic::Decide(In, P) == EJREnemyState::Attack);
	In.DistanceToTarget = 4000.f;
	TestTrue(TEXT("Desiste"), FJREnemyStateLogic::Decide(In, P) == EJREnemyState::Idle);
	return true;
}

#undef JR_TEST_FLAGS

#endif // WITH_DEV_AUTOMATION_TESTS

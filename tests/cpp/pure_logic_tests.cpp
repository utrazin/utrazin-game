// Testes da lógica pura do jogo compilados FORA da Unreal com stubs (tests/cpp/stubs).
// Espelham os Automation Tests JR.* em Source/JogoResgate/Tests. Rode: tests/cpp/run_pure_tests.sh
#include "Vehicles/JRVehicleDamageModel.h"
#include "Combat/JRAmmoState.h"
#include "AI/JRAimPrediction.h"
#include "AI/JREnemyStateLogic.h"

#include <cstdio>

static int Failures = 0;
static int Checks = 0;
#define CHECK(cond) do { ++Checks; if (!(cond)) { ++Failures; std::printf("FALHA %s:%d: %s\n", __FILE__, __LINE__, #cond); } } while (0)
#define NEAR(a, b, tol) CHECK(std::fabs((double)(a) - (double)(b)) <= (tol))

static void VehicleDamage()
{
	FJRVehicleDamageState S;
	NEAR(S.GetIntegrity(), 1.0, 1e-6);
	NEAR(S.GetEngineTorqueScale(), 1.0, 1e-6);
	CHECK(!S.IsDisabled());
	NEAR(S.ApplyZoneDamage(EJRVehicleZone::Front, 30.f), 30.0, 1e-6);
	NEAR(S.ApplyZoneDamage(EJRVehicleZone::Front, 500.f), 70.0, 1e-6);   // clamp
	NEAR(S.ApplyZoneDamage(EJRVehicleZone::Front, -5.f), 0.0, 1e-6);     // dano negativo ignorado
	NEAR(S.GetIntegrity(), 500.0 / 600.0, 1e-5);                         // 4x100 + 2x100 de 600
	S.ApplyZoneDamage(EJRVehicleZone::Engine, 50.f);
	NEAR(S.GetEngineTorqueScale(), 0.35 + 0.65 * 0.5, 1e-5);
	CHECK(!S.ShouldEmitEngineSmoke());
	S.ApplyZoneDamage(EJRVehicleZone::Engine, 30.f);
	CHECK(S.ShouldEmitEngineSmoke());
	S.ApplyZoneDamage(EJRVehicleZone::Engine, 100.f);
	CHECK(S.IsDisabled());                                               // motor zerado inutiliza
	NEAR(S.GetEngineTorqueScale(), 0.35, 1e-6);
	S.Reset();
	CHECK(!S.IsDisabled() && S.NumFlatTires() == 0);

	NEAR(S.GetSteeringBias(), 0.0, 1e-6);
	S.SetTireFlat(EJRWheel::FrontLeft, true);
	CHECK(S.IsTireFlat(EJRWheel::FrontLeft) && S.NumFlatTires() == 1);
	CHECK(S.GetSteeringBias() < 0.f);                                    // puxa para a esquerda
	S.SetTireFlat(EJRWheel::RearRight, true);
	NEAR(S.GetSteeringBias(), 0.0, 1e-6);                                // lados se anulam

	NEAR(FJRVehicleDamageState::ImpactDamageFromSpeed(10.f), 0.0, 1e-6);
	NEAR(FJRVehicleDamageState::ImpactDamageFromSpeed(65.f), 40.0, 1e-4);

	CHECK(FJRVehicleDamageState::ZoneFromLocalPoint(FVector(200, 10, 0), 230, 95) == EJRVehicleZone::Front);
	CHECK(FJRVehicleDamageState::ZoneFromLocalPoint(FVector(-220, -20, 0), 230, 95) == EJRVehicleZone::Rear);
	CHECK(FJRVehicleDamageState::ZoneFromLocalPoint(FVector(30, 90, 0), 230, 95) == EJRVehicleZone::Right);
	CHECK(FJRVehicleDamageState::ZoneFromLocalPoint(FVector(-30, -90, 0), 230, 95) == EJRVehicleZone::Left);

	// Integridade baixa sem motor zerado também inutiliza
	FJRVehicleDamageState T;
	for (EJRVehicleZone Z : {EJRVehicleZone::Front, EJRVehicleZone::Rear, EJRVehicleZone::Left, EJRVehicleZone::Right})
	{
		T.ApplyZoneDamage(Z, 100.f);
	}
	T.ApplyZoneDamage(EJRVehicleZone::Engine, 75.f);                     // integridade = 50/600 < 0.1
	CHECK(T.IsDisabled());
}

static void Ammo()
{
	FJRAmmoState A;
	A.Initialize(12, 20);
	CHECK(A.Magazine == 12 && A.Reserve == 20 && !A.CanReload());
	for (int i = 0; i < 12; ++i) { CHECK(A.ConsumeShot()); }
	CHECK(!A.CanFire() && !A.ConsumeShot());
	CHECK(A.Reload() == 12 && A.Magazine == 12 && A.Reserve == 8);
	A.ConsumeShot(); A.ConsumeShot(); A.ConsumeShot();
	CHECK(A.Reload() == 3 && A.Reserve == 5);
	for (int i = 0; i < 12; ++i) { A.ConsumeShot(); }
	CHECK(A.Reload() == 5 && A.Magazine == 5 && A.Reserve == 0);
	for (int i = 0; i < 5; ++i) { A.ConsumeShot(); }
	CHECK(A.IsCompletelyEmpty() && A.Reload() == 0);
	A.Initialize(0, -3);
	CHECK(A.MagazineSize == 1 && A.Reserve == 0);
}

static void Aim()
{
	FVector P; double T = 0;
	// Alvo parado: mira no alvo, tempo = distância / velocidade
	CHECK(FJRAimPrediction::PredictInterceptPoint(FVector(0, 0, 0), FVector(1000, 0, 0), FVector(0, 0, 0), 2000.0, P, T));
	NEAR(P.X, 1000.0, 1e-6); NEAR(T, 0.5, 1e-9);
	// Alvo cruzando a 1000 cm/s, projétil a 3000 cm/s
	CHECK(FJRAimPrediction::PredictInterceptPoint(FVector(0, 0, 0), FVector(3000, 0, 0), FVector(0, 1000, 0), 3000.0, P, T));
	const FVector Hit = FVector(3000, 0, 0) + FVector(0, 1000, 0) * T;
	NEAR((Hit - FVector(0, 0, 0)).Size(), 3000.0 * T, 1e-3);            // projétil chega junto
	CHECK(P.Y > 0.0);
	// Alvo mais rápido fugindo: sem solução
	CHECK(!FJRAimPrediction::PredictInterceptPoint(FVector(0, 0, 0), FVector(1000, 0, 0), FVector(5000, 0, 0), 2000.0, P, T));
	NEAR(P.X, 1000.0, 1e-6);
	CHECK(!FJRAimPrediction::PredictInterceptPoint(FVector(0, 0, 0), FVector(1000, 0, 0), FVector(0, 0, 0), 0.0, P, T));

	FRandomStream Stream(42);
	const FVector Dir(1, 0, 0);
	const FVector NoSpread = FJRAimPrediction::ApplySpread(Dir, 0.f, Stream);
	NEAR(NoSpread.X, 1.0, 1e-9);
	bool bAnyDeviation = false;
	for (int i = 0; i < 200; ++i)
	{
		const FVector S = FJRAimPrediction::ApplySpread(Dir, 5.f, Stream);
		const double Angle = std::acos(std::min(1.0, FVector::DotProduct(S, Dir))) * 180.0 / 3.14159265358979323846;
		CHECK(Angle <= 5.0 + 1e-6);
		bAnyDeviation |= Angle > 0.5;
	}
	CHECK(bAnyDeviation);                                                // imprecisão existe
}

static void EnemyStates()
{
	FJREnemyDecisionParams P;
	P.AggroRadius = 2500.f; P.LoseAggroRadius = 3500.f; P.AttackRange = 150.f; P.AlertDuration = 1.5f;
	FJREnemyDecisionInput In;
	In.DistanceToTarget = 3000.f; In.bHasLineOfSight = true;
	CHECK(FJREnemyStateLogic::Decide(In, P) == EJREnemyState::Idle);    // fora do aggro
	P.bHasPatrol = true;
	CHECK(FJREnemyStateLogic::Decide(In, P) == EJREnemyState::Patrol);
	In.DistanceToTarget = 2000.f; In.bHasLineOfSight = false;
	CHECK(FJREnemyStateLogic::Decide(In, P) == EJREnemyState::Patrol);  // sem visão não nota
	In.bHasLineOfSight = true;
	CHECK(FJREnemyStateLogic::Decide(In, P) == EJREnemyState::Alert);
	In.Current = EJREnemyState::Alert; In.TimeInState = 0.5f;
	CHECK(FJREnemyStateLogic::Decide(In, P) == EJREnemyState::Alert);   // telegrafa
	In.TimeInState = 2.f;
	CHECK(FJREnemyStateLogic::Decide(In, P) == EJREnemyState::Chase);
	In.Current = EJREnemyState::Chase; In.DistanceToTarget = 100.f;
	CHECK(FJREnemyStateLogic::Decide(In, P) == EJREnemyState::Attack);
	In.Current = EJREnemyState::Attack; In.DistanceToTarget = 3000.f;
	CHECK(FJREnemyStateLogic::Decide(In, P) == EJREnemyState::Chase);   // histerese: ainda persegue
	In.DistanceToTarget = 4000.f;
	CHECK(FJREnemyStateLogic::Decide(In, P) == EJREnemyState::Patrol);  // desiste
	In.bIsDead = true;
	CHECK(FJREnemyStateLogic::Decide(In, P) == EJREnemyState::Dead);
}

int main()
{
	VehicleDamage();
	Ammo();
	Aim();
	EnemyStates();
	std::printf("%d verificações, %d falha(s)\n", Checks, Failures);
	return Failures == 0 ? 0 : 1;
}

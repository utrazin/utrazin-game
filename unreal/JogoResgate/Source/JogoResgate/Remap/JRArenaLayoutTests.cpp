// Copyright utrazin. All Rights Reserved.
// [Remap F2] Automation Tests da planta da arena procedural. Rodar: Automation RunTests JR.Remap

#include "Misc/AutomationTest.h"
#include "Remap/JRArenaLayout.h"
#include "Remap/JRRemapTypes.h"

#if WITH_DEV_AUTOMATION_TESTS

#define JR_REMAP_TEST_FLAGS (EAutomationTestFlags::EditorContext | EAutomationTestFlags::ClientContext | EAutomationTestFlags::ProductFilter)

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FJRArenaLayoutSeedsTest, "JR.Remap.ArenaLayout.Seeds", JR_REMAP_TEST_FLAGS)
bool FJRArenaLayoutSeedsTest::RunTest(const FString& Parameters)
{
	// Critério do F2: 10 sementes seguidas sem arena quebrada. Aqui: 5 níveis x 5 moldes x 20 sementes.
	const int32 TestLevels[] = { 1, 3, 6, 10, 15 };
	for (const int32 TestLevel : TestLevels)
	{
		for (int32 ShapeIndex = 0; ShapeIndex < static_cast<int32>(EJRArenaShape::Count); ++ShapeIndex)
		{
			for (int32 TestSeed = 1; TestSeed <= 20; ++TestSeed)
			{
				FJRArenaLayout Plan;
				int32 Attempts = 0;
				FString Problem;
				const bool bOk = FJRArenaLayout::GenerateWithRetries(TestSeed * 977 + ShapeIndex, TestLevel, ShapeIndex, 12, Plan,
					Attempts, Problem);
				const FString Label = FString::Printf(TEXT("nível %d, molde %d, semente %d"), TestLevel, ShapeIndex, TestSeed);
				if (!TestTrue(FString::Printf(TEXT("Gera (%s): %s"), *Label, *Problem), bOk))
				{
					continue;
				}
				TestTrue(FString::Printf(TEXT("Conferência (%s): %s"), *Label, *Plan.Validate()), Plan.Validate().IsEmpty());
				TestEqual(FString::Printf(TEXT("Tamanho (%s)"), *Label), Plan.Size, FJRArenaLayout::SizeForLevel(TestLevel));
				TestTrue(FString::Printf(TEXT("Visão (%s)"), *Label), Plan.LongestSightRun() <= FJRArenaLayout::MaxSightRun);
				TestTrue(FString::Printf(TEXT("Saídas (%s)"), *Label), Plan.CountCenterExits() >= 3);
				TestEqual(FString::Printf(TEXT("Tudo alcançável (%s)"), *Label), Plan.CountUnreachableFree(), 0);
			}
		}
	}
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FJRArenaLayoutDeterministicTest, "JR.Remap.ArenaLayout.Deterministic", JR_REMAP_TEST_FLAGS)
bool FJRArenaLayoutDeterministicTest::RunTest(const FString& Parameters)
{
	FJRArenaLayout PlanA;
	FJRArenaLayout PlanB;
	FString ProblemA;
	FString ProblemB;
	PlanA.Generate(4242, 5, -1, true, ProblemA);
	PlanB.Generate(4242, 5, -1, true, ProblemB);
	TestEqual(TEXT("Mesma semente, mesmo desenho"), PlanA.ToAscii(), PlanB.ToAscii());
	TestEqual(TEXT("Mesmo molde"), static_cast<int32>(PlanA.Shape), static_cast<int32>(PlanB.Shape));
	TestEqual(TEXT("80 m no nível 1"), FJRArenaLayout::SizeForLevel(1), 10);
	TestEqual(TEXT("160 m no máximo"), FJRArenaLayout::SizeForLevel(40), 20);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FJRArenaLayoutPlacementRulesTest, "JR.Remap.ArenaLayout.PlacementRules", JR_REMAP_TEST_FLAGS)
bool FJRArenaLayoutPlacementRulesTest::RunTest(const FString& Parameters)
{
	// [A-089] regras por item: conjuntos colados no muro e longe do centro, zona central aberta, baú com 2 acessos,
	// área livre mínima. (Validate já recusa; aqui também conta quantos conjuntos saem em média.)
	int32 Plans = 0;
	int32 AssemblyTotal = 0;
	for (int32 TestLevel = 1; TestLevel <= 15; TestLevel += 7)
	{
		for (int32 TestSeed = 1; TestSeed <= 30; ++TestSeed)
		{
			FJRArenaLayout Plan;
			int32 Attempts = 0;
			FString Problem;
			if (!FJRArenaLayout::GenerateWithRetries(TestSeed * 131, TestLevel, -1, 12, Plan, Attempts, Problem))
			{
				AddError(FString::Printf(TEXT("nível %d semente %d: %s"), TestLevel, TestSeed, *Problem));
				continue;
			}
			++Plans;
			AssemblyTotal += Plan.Assemblies.Num();
			TestTrue(TEXT("Área livre mínima"), Plan.FreeRatio() >= FJRArenaLayout::MinFreeRatio);
			for (const FJRArenaAssembly& Asm : Plan.Assemblies)
			{
				for (const FIntPoint& Cell : Asm.Cells)
				{
					TestFalse(TEXT("Conjunto fora da zona central"), Plan.IsCenterZone(Cell));
				}
			}
			for (const FIntPoint& Chest : Plan.ChestCells)
			{
				TestTrue(TEXT("Baú com 2 acessos"), Plan.CountFreeNeighbors4(Chest) >= 2);
			}
		}
	}
	TestTrue(TEXT("Em média pelo menos 1,5 conjunto por arena"), Plans > 0 && AssemblyTotal * 2 >= 3 * Plans);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FJRArenaDirectorRulesTest, "JR.Remap.DirectorRules", JR_REMAP_TEST_FLAGS)
bool FJRArenaDirectorRulesTest::RunTest(const FString& Parameters)
{
	TestEqual(TEXT("Orçamento onda 1 nível 1"), FJRRemapRules::DirectorWaveBudget(1, 1), 11);
	TestTrue(TEXT("Orçamento cresce com a onda"), FJRRemapRules::DirectorWaveBudget(10, 1) > FJRRemapRules::DirectorWaveBudget(5, 1));
	TestTrue(TEXT("Orçamento cresce com o nível"), FJRRemapRules::DirectorWaveBudget(3, 10) > FJRRemapRules::DirectorWaveBudget(3, 1));
	TestTrue(TEXT("Renda mais rápida em nível alto"),
		FJRRemapRules::DirectorIncomePerSecond(3, 10) > FJRRemapRules::DirectorIncomePerSecond(3, 1));
	TestEqual(TEXT("Pico onda 1"), FJRRemapRules::DirectorPeakCost(1), 8);
	return true;
}

#endif

// Copyright utrazin. All Rights Reserved.
// Automation Test da leitura dos registros de vegetação (AJRInstancedScatter::DecodeRecords). Rodar: Automation RunTests JR.

#include "Gameplay/JRInstancedScatter.h"
#include "Misc/AutomationTest.h"

#if WITH_DEV_AUTOMATION_TESTS

#define JR_SCATTER_TEST_FLAGS (EAutomationTestFlags::EditorContext | EAutomationTestFlags::ClientContext | EAutomationTestFlags::ProductFilter)

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FJRScatterDecodeTest, "JR.Levels.Scatter.DecodeRecords", JR_SCATTER_TEST_FLAGS)
bool FJRScatterDecodeTest::RunTest(const FString& Parameters)
{
	// 2 registros: posição, quaternion (90 graus em Z no segundo), escala xy / z
	const float Raw[2 * AJRInstancedScatter::RecordFloats] = {
		100.f, -200.f, 50.f, 0.f, 0.f, 0.f, 1.f, 2.f, 3.f,
		0.f, 0.f, 0.f, 0.f, 0.f, 0.70710678f, 0.70710678f, 1.f, 1.f};
	TArray<uint8> Bytes;
	Bytes.Append(reinterpret_cast<const uint8*>(Raw), static_cast<int32>(sizeof(Raw)));

	TArray<FTransform> Out;
	TestTrue(TEXT("Decodifica"), AJRInstancedScatter::DecodeRecords(Bytes, 0.5f, Out));
	TestEqual(TEXT("Dois registros"), Out.Num(), 2);
	if (Out.Num() == 2)
	{
		TestTrue(TEXT("Posição"), Out[0].GetLocation().Equals(FVector(100.0, -200.0, 50.0), 1e-3));
		TestTrue(TEXT("Escala com multiplicador"), Out[0].GetScale3D().Equals(FVector(1.0, 1.0, 1.5), 1e-4));
		const FVector Fwd = Out[1].GetRotation().RotateVector(FVector::ForwardVector);
		TestTrue(TEXT("Rotação 90 graus em Z"), Fwd.Equals(FVector::RightVector, 1e-3));
	}

	Bytes.RemoveAt(Bytes.Num() - 1);
	TestFalse(TEXT("Tamanho quebrado é recusado"), AJRInstancedScatter::DecodeRecords(Bytes, 1.f, Out));
	return true;
}

#undef JR_SCATTER_TEST_FLAGS

#endif // WITH_DEV_AUTOMATION_TESTS

// Copyright utrazin. All Rights Reserved.

#include "Misc/AutomationTest.h"
#include "Save/JRSaveGame.h"
#include "Save/JRSaveMigration.h"
#include "UObject/Package.h"

#if WITH_DEV_AUTOMATION_TESTS

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FJRSaveMigrationTest, "JR.Save.Migration.V0ToCurrent",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::ClientContext | EAutomationTestFlags::ProductFilter)
bool FJRSaveMigrationTest::RunTest(const FString& Parameters)
{
	UJRSaveGame* Save = NewObject<UJRSaveGame>(GetTransientPackage());
	Save->SaveVersion = 0;
	Save->Settings.Culture.Empty();
	FString Error;
	TestTrue(TEXT("Migra v0"), FJRSaveMigration::Migrate(*Save, Error));
	TestEqual(TEXT("Versão atual"), Save->SaveVersion, UJRSaveGame::CurrentVersion);
	TestTrue(TEXT("Fase 1 liberada"), Save->UnlockedLevels.Contains(FJRSaveMigration::FirstLevelId));
	TestEqual(TEXT("Cultura padrão"), Save->Settings.Culture, FString(TEXT("pt-BR")));

	TestTrue(TEXT("Idempotente"), FJRSaveMigration::Migrate(*Save, Error));
	TestEqual(TEXT("Sem duplicar fase"), Save->UnlockedLevels.Num(), 1);

	Save->SaveVersion = UJRSaveGame::CurrentVersion + 1;
	TestFalse(TEXT("Versão futura rejeitada"), FJRSaveMigration::Migrate(*Save, Error));
	TestFalse(TEXT("Mensagem de erro"), Error.IsEmpty());
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FJRSaveProgressTest, "JR.Save.Progress.FindOrAdd",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::ClientContext | EAutomationTestFlags::ProductFilter)
bool FJRSaveProgressTest::RunTest(const FString& Parameters)
{
	UJRSaveGame* Save = NewObject<UJRSaveGame>(GetTransientPackage());
	Save->FindOrAddLevel(TEXT("L01")).LastCheckpointId = TEXT("Transition");
	Save->FindOrAddLevel(TEXT("L01")).bCompleted = true;
	TestEqual(TEXT("Uma entrada"), Save->Levels.Num(), 1);
	const FJRLevelProgress* P = Save->FindLevel(TEXT("L01"));
	TestTrue(TEXT("Encontrada"), P && P->bCompleted && P->LastCheckpointId == FName(TEXT("Transition")));
	TestNull(TEXT("Inexistente"), Save->FindLevel(TEXT("L02")));
	return true;
}

#endif // WITH_DEV_AUTOMATION_TESTS

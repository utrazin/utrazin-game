// Copyright utrazin. All Rights Reserved.

#include "Save/JRSaveMigration.h"
#include "Save/JRSaveGame.h"

const FName FJRSaveMigration::FirstLevelId(TEXT("L01"));

bool FJRSaveMigration::Migrate(UJRSaveGame& Save, FString& OutError)
{
	if (Save.SaveVersion > UJRSaveGame::CurrentVersion)
	{
		OutError = FString::Printf(TEXT("Save versão %d é mais nova que o jogo (%d)."), Save.SaveVersion, UJRSaveGame::CurrentVersion);
		return false;
	}
	if (Save.SaveVersion < 0)
	{
		OutError = FString::Printf(TEXT("Save com versão inválida %d."), Save.SaveVersion);
		return false;
	}

	// v0 -> v1: garante a primeira fase desbloqueada e cultura padrão.
	if (Save.SaveVersion == 0)
	{
		Save.UnlockedLevels.AddUnique(FirstLevelId);
		if (Save.Settings.Culture.IsEmpty())
		{
			Save.Settings.Culture = TEXT("pt-BR");
		}
		Save.SaveVersion = 1;
	}

	// Próximos passos: if (Save.SaveVersion == 1) { ...; Save.SaveVersion = 2; }

	return Save.SaveVersion == UJRSaveGame::CurrentVersion;
}

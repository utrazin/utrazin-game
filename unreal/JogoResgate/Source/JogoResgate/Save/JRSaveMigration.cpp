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

	// v1 -> v2 [A-074]: flag da abertura (quem já jogava ainda não viu a abertura nova).
	if (Save.SaveVersion == 1)
	{
		Save.bIntroSeen = false;
		Save.SaveVersion = 2;
	}

	// v2 -> v3 [Remap F1]: carteira e bancada começam zeradas (quem já jogava o L01 começa a cidade do zero).
	if (Save.SaveVersion == 2)
	{
		Save.Credits = 0;
		Save.Scrap = 0;
		Save.Crystals = 0;
		Save.BenchLevel = 0;
		Save.OwnedWeaponSlots.Reset();
		Save.BestWave = 0;
		Save.RunsPlayed = 0;
		Save.SaveVersion = 3;
	}

	// Próximos passos: if (Save.SaveVersion == 3) { ...; Save.SaveVersion = 4; }

	return Save.SaveVersion == UJRSaveGame::CurrentVersion;
}

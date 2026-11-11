// Copyright utrazin. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"

class UJRSaveGame;

/** Migração passo a passo de saves antigos (JR.Save.Migration.*). */
struct JOGORESGATE_API FJRSaveMigration
{
	/** Leva o save até UJRSaveGame::CurrentVersion. Falha para versões futuras (save de build mais novo). */
	static bool Migrate(UJRSaveGame& Save, FString& OutError);

	/** Nome da primeira fase, desbloqueada por padrão. */
	static const FName FirstLevelId;
};

// Copyright utrazin. All Rights Reserved.

#include "Core/JRGameInstance.h"
#include "Characters/JRCharacterDefinition.h"
#include "Levels/JRLevelDefinition.h"

UJRCharacterDefinition* UJRGameInstance::FindCharacterDefinition(FName CharacterId) const
{
	for (const TSoftObjectPtr<UJRCharacterDefinition>& Soft : Characters)
	{
		UJRCharacterDefinition* Def = Soft.LoadSynchronous();
		if (Def && (CharacterId.IsNone() || Def->CharacterId == CharacterId))
		{
			return Def;
		}
	}
	return nullptr;
}

UJRLevelDefinition* UJRGameInstance::FindLevelDefinition(FName LevelId) const
{
	for (const TSoftObjectPtr<UJRLevelDefinition>& Soft : Levels)
	{
		UJRLevelDefinition* Def = Soft.LoadSynchronous();
		if (Def && Def->LevelId == LevelId)
		{
			return Def;
		}
	}
	return nullptr;
}

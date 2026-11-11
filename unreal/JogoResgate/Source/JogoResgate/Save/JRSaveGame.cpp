// Copyright utrazin. All Rights Reserved.

#include "Save/JRSaveGame.h"

FJRLevelProgress& UJRSaveGame::FindOrAddLevel(FName LevelId)
{
	for (FJRLevelProgress& Progress : Levels)
	{
		if (Progress.LevelId == LevelId)
		{
			return Progress;
		}
	}
	FJRLevelProgress& NewProgress = Levels.AddDefaulted_GetRef();
	NewProgress.LevelId = LevelId;
	return NewProgress;
}

const FJRLevelProgress* UJRSaveGame::FindLevel(FName LevelId) const
{
	return Levels.FindByPredicate([LevelId](const FJRLevelProgress& P) { return P.LevelId == LevelId; });
}

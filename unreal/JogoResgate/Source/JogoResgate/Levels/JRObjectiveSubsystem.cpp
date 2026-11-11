// Copyright utrazin. All Rights Reserved.

#include "Levels/JRObjectiveSubsystem.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "JogoResgate.h"
#include "Levels/JRCheckpoint.h"
#include "Levels/JRLevelDefinition.h"
#include "Progression/JRProgressionSubsystem.h"

bool UJRObjectiveSubsystem::DoesSupportWorldType(const EWorldType::Type WorldType) const
{
	return WorldType == EWorldType::Game || WorldType == EWorldType::PIE;
}

void UJRObjectiveSubsystem::InitializeLevel(UJRLevelDefinition* Definition, EJRLevelStage StartStage)
{
	LevelDefinition = Definition;
	SetStage(StartStage);
}

FName UJRObjectiveSubsystem::GetLevelId() const
{
	return LevelDefinition ? LevelDefinition->LevelId : NAME_None;
}

void UJRObjectiveSubsystem::SetStage(EJRLevelStage NewStage)
{
	if (NewStage == Stage)
	{
		return;
	}
	const EJRLevelStage Old = Stage;
	Stage = NewStage;
	UE_LOG(LogJR, Log, TEXT("Estágio da fase: %s -> %s"), *UEnum::GetValueAsString(Old), *UEnum::GetValueAsString(NewStage));
	OnStageChanged.Broadcast(Old, NewStage);
}

void UJRObjectiveSubsystem::ReachCheckpoint(AJRCheckpoint* Checkpoint)
{
	if (!Checkpoint || Stage == EJRLevelStage::Completed || Stage == EJRLevelStage::Failed)
	{
		return;
	}
	if (UJRProgressionSubsystem* Progression = GetWorld()->GetGameInstance()->GetSubsystem<UJRProgressionSubsystem>())
	{
		Progression->RecordCheckpoint(GetLevelId(), Checkpoint->GetCheckpointId());
	}
	if (static_cast<uint8>(Checkpoint->GetStageOnRespawn()) > static_cast<uint8>(Stage))
	{
		SetStage(Checkpoint->GetStageOnRespawn());
	}
	OnCheckpointReached.Broadcast(Checkpoint);
}

void UJRObjectiveSubsystem::CompleteLevel()
{
	if (Stage == EJRLevelStage::Completed)
	{
		return;
	}
	if (UJRProgressionSubsystem* Progression = GetWorld()->GetGameInstance()->GetSubsystem<UJRProgressionSubsystem>())
	{
		Progression->CompleteLevel(GetLevelId(), LevelDefinition ? LevelDefinition->NextLevelId : NAME_None);
	}
	SetStage(EJRLevelStage::Completed);
}

void UJRObjectiveSubsystem::FailLevel()
{
	if (Stage != EJRLevelStage::Completed)
	{
		SetStage(EJRLevelStage::Failed);
	}
}

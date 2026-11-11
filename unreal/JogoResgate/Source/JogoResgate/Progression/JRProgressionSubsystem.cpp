// Copyright utrazin. All Rights Reserved.

#include "Progression/JRProgressionSubsystem.h"
#include "JogoResgate.h"
#include "Kismet/GameplayStatics.h"
#include "Save/JRSaveGame.h"
#include "Save/JRSaveMigration.h"

const FString UJRProgressionSubsystem::SlotName(TEXT("JR_Slot_0"));

void UJRProgressionSubsystem::Initialize(FSubsystemCollectionBase& Collection)
{
	Super::Initialize(Collection);
	LoadOrCreate();
}

void UJRProgressionSubsystem::LoadOrCreate()
{
	UJRSaveGame* Loaded = nullptr;
	if (UGameplayStatics::DoesSaveGameExist(SlotName, UserIndex))
	{
		Loaded = Cast<UJRSaveGame>(UGameplayStatics::LoadGameFromSlot(SlotName, UserIndex));
		if (!Loaded)
		{
			UE_LOG(LogJR, Warning, TEXT("Save %s ilegível; criando novo (o arquivo antigo não é apagado)."), *SlotName);
		}
	}
	if (!Loaded)
	{
		Loaded = Cast<UJRSaveGame>(UGameplayStatics::CreateSaveGameObject(UJRSaveGame::StaticClass()));
	}

	FString Error;
	if (!FJRSaveMigration::Migrate(*Loaded, Error))
	{
		UE_LOG(LogJR, Error, TEXT("Migração do save falhou: %s. Usando save novo em memória; disco preservado."), *Error);
		Loaded = Cast<UJRSaveGame>(UGameplayStatics::CreateSaveGameObject(UJRSaveGame::StaticClass()));
		FJRSaveMigration::Migrate(*Loaded, Error);
	}
	Save = Loaded;
}

bool UJRProgressionSubsystem::SaveNow()
{
	const bool bOk = Save && UGameplayStatics::SaveGameToSlot(Save, SlotName, UserIndex);
	if (!bOk)
	{
		UE_LOG(LogJR, Error, TEXT("Falha ao salvar em %s"), *SlotName);
	}
	OnProgressSaved.Broadcast(bOk);
	return bOk;
}

void UJRProgressionSubsystem::RecordCheckpoint(FName LevelId, FName CheckpointId)
{
	if (!Save || LevelId.IsNone())
	{
		return;
	}
	Save->CurrentLevelId = LevelId;
	Save->FindOrAddLevel(LevelId).LastCheckpointId = CheckpointId;
	SaveNow();
}

void UJRProgressionSubsystem::CompleteLevel(FName LevelId, FName NextLevelId)
{
	if (!Save)
	{
		return;
	}
	FJRLevelProgress& Progress = Save->FindOrAddLevel(LevelId);
	Progress.bCompleted = true;
	Progress.LastCheckpointId = NAME_None;
	if (!NextLevelId.IsNone())
	{
		Save->UnlockedLevels.AddUnique(NextLevelId);
		Save->CurrentLevelId = NextLevelId;
	}
	SaveNow();
}

void UJRProgressionSubsystem::SelectCharacter(FName CharacterId, FName SkinId)
{
	if (!Save)
	{
		return;
	}
	Save->SelectedCharacterId = CharacterId;
	Save->SelectedSkinId = SkinId;
	SaveNow();
}

FName UJRProgressionSubsystem::GetLastCheckpoint(FName LevelId) const
{
	const FJRLevelProgress* Progress = Save ? Save->FindLevel(LevelId) : nullptr;
	return Progress ? Progress->LastCheckpointId : NAME_None;
}

bool UJRProgressionSubsystem::IsLevelUnlocked(FName LevelId) const
{
	return Save && Save->UnlockedLevels.Contains(LevelId);
}

void UJRProgressionSubsystem::ClearCheckpoint(FName LevelId)
{
	if (Save)
	{
		Save->FindOrAddLevel(LevelId).LastCheckpointId = NAME_None;
		SaveNow();
	}
}

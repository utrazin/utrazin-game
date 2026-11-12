// Copyright utrazin. All Rights Reserved.

#include "Core/JRGameMode.h"
#include "Characters/JRCharacter.h"
#include "Characters/JRCharacterDefinition.h"
#include "Core/JRGameInstance.h"
#include "Core/JRPlayerController.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "JogoResgate.h"
#include "Kismet/GameplayStatics.h"
#include "Levels/JRCheckpoint.h"
#include "Levels/JRLevelDefinition.h"
#include "Levels/JRObjectiveSubsystem.h"
#include "Progression/JRProgressionSubsystem.h"
#include "Save/JRSaveGame.h"
#include "TimerManager.h"
#include "Vehicles/JRVehiclePawn.h"

AJRGameMode::AJRGameMode()
{
	PlayerControllerClass = AJRPlayerController::StaticClass();
	DefaultPawnClass = nullptr; // decidido por checkpoint (veículo ou personagem)
}

AJRCheckpoint* AJRGameMode::ResolveRespawnCheckpoint() const
{
	FName SavedId = NAME_None;
	if (LevelDefinition)
	{
		if (const UJRProgressionSubsystem* Progression = GetGameInstance()->GetSubsystem<UJRProgressionSubsystem>())
		{
			const bool bFreshEditorRun = bStartFromBeginningInEditor && GetWorld()->IsPlayInEditor()
				&& !Progression->bRestartingFromCheckpoint;
			if (!bFreshEditorRun)
			{
				SavedId = Progression->GetLastCheckpoint(LevelDefinition->LevelId);
			}
		}
	}
	AJRCheckpoint* StartCheckpoint = nullptr;
	for (TActorIterator<AJRCheckpoint> It(GetWorld()); It; ++It)
	{
		if (!SavedId.IsNone() && It->GetCheckpointId() == SavedId)
		{
			return *It;
		}
		if (It->IsLevelStart() && !StartCheckpoint)
		{
			StartCheckpoint = *It;
		}
	}
	return StartCheckpoint;
}

void AJRGameMode::StartPlay()
{
	const AJRCheckpoint* Checkpoint = ResolveRespawnCheckpoint();
	const EJRLevelStage Stage = Checkpoint ? Checkpoint->GetStageOnRespawn() : EJRLevelStage::Driving;
	if (UJRObjectiveSubsystem* Objective = GetWorld()->GetSubsystem<UJRObjectiveSubsystem>())
	{
		Objective->InitializeLevel(LevelDefinition, Stage);
	}
	UE_LOG(LogJR, Log, TEXT("StartPlay: GameMode=%s LevelDefinition=%s Checkpoint=%s Stage=%s"),
		*GetClass()->GetPathName(), *GetNameSafe(LevelDefinition), *GetNameSafe(Checkpoint), *UEnum::GetValueAsString(Stage));
	if (!LevelDefinition)
	{
		UE_LOG(LogJR, Warning, TEXT("%s sem LevelDefinition: progresso não será salvo."), *GetName());
	}
	Super::StartPlay();
	if (UJRProgressionSubsystem* Progression = GetGameInstance()->GetSubsystem<UJRProgressionSubsystem>())
	{
		Progression->bRestartingFromCheckpoint = false;
	}
}

AActor* AJRGameMode::FindPlayerStart_Implementation(AController* Player, const FString& IncomingName)
{
	if (AJRCheckpoint* Checkpoint = ResolveRespawnCheckpoint())
	{
		return Checkpoint;
	}
	return Super::FindPlayerStart_Implementation(Player, IncomingName);
}

UClass* AJRGameMode::GetDefaultPawnClassForController_Implementation(AController* InController)
{
	const AJRCheckpoint* Checkpoint = ResolveRespawnCheckpoint();
	const bool bOnFoot = Checkpoint && static_cast<uint8>(Checkpoint->GetStageOnRespawn()) >= static_cast<uint8>(EJRLevelStage::OnFoot);
	if (bOnFoot)
	{
		return ResolveCharacterClass();
	}
	if (LevelDefinition && !LevelDefinition->VehicleClass.IsNull())
	{
		return LevelDefinition->VehicleClass.LoadSynchronous();
	}
	return FallbackVehicleClass ? FallbackVehicleClass.Get() : Super::GetDefaultPawnClassForController_Implementation(InController);
}

APawn* AJRGameMode::SpawnDefaultPawnFor_Implementation(AController* NewPlayer, AActor* StartSpot)
{
	APawn* Spawned = nullptr;
	if (const AJRCheckpoint* Checkpoint = Cast<AJRCheckpoint>(StartSpot))
	{
		FTransform SpawnTransform = Checkpoint->GetRespawnTransform();
		SpawnTransform.SetScale3D(FVector::OneVector);
		UClass* PawnClass = GetDefaultPawnClassForController(NewPlayer);
		const bool bVehicle = PawnClass && PawnClass->IsChildOf(AJRVehiclePawn::StaticClass());
		// Nasce acima do chão (rodas/cápsula não podem começar dentro do terreno).
		SpawnTransform.AddToTranslation(FVector(0.f, 0.f, bVehicle ? VehicleSpawnHeight : CharacterSpawnHeight));
		if (PawnClass)
		{
			FActorSpawnParameters Params;
			Params.Instigator = GetInstigator();
			Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AdjustIfPossibleButAlwaysSpawn;
			Params.ObjectFlags |= RF_Transient;
			Spawned = GetWorld()->SpawnActor<APawn>(PawnClass, SpawnTransform, Params);
		}
	}
	else
	{
		Spawned = Super::SpawnDefaultPawnFor_Implementation(NewPlayer, StartSpot);
	}
	UE_LOG(LogJR, Log, TEXT("SpawnDefaultPawnFor: classe=%s inicio=%s resultado=%s em %s"),
		*GetNameSafe(GetDefaultPawnClassForController(NewPlayer)), *GetNameSafe(StartSpot), *GetNameSafe(Spawned),
		Spawned ? *Spawned->GetActorLocation().ToString() : TEXT("-"));
	return Spawned;
}

void AJRGameMode::SetPlayerDefaults(APawn* PlayerPawn)
{
	Super::SetPlayerDefaults(PlayerPawn);
	ApplySelectedSkin(Cast<AJRCharacter>(PlayerPawn));
}

TSubclassOf<AJRCharacter> AJRGameMode::ResolveCharacterClass() const
{
	const UJRProgressionSubsystem* Progression = GetGameInstance()->GetSubsystem<UJRProgressionSubsystem>();
	const UJRGameInstance* GI = Cast<UJRGameInstance>(GetGameInstance());
	const FName Selected = (Progression && Progression->GetSave()) ? Progression->GetSave()->SelectedCharacterId : NAME_None;
	if (GI)
	{
		if (const UJRCharacterDefinition* Def = GI->FindCharacterDefinition(Selected))
		{
			if (UClass* Class = Def->CharacterClass.LoadSynchronous())
			{
				return Class;
			}
		}
	}
	return FallbackCharacterClass;
}

void AJRGameMode::ApplySelectedSkin(AJRCharacter* Character) const
{
	const UJRProgressionSubsystem* Progression = GetGameInstance()->GetSubsystem<UJRProgressionSubsystem>();
	const UJRGameInstance* GI = Cast<UJRGameInstance>(GetGameInstance());
	if (!Character || !Progression || !Progression->GetSave() || !GI)
	{
		return;
	}
	const UJRSaveGame* Save = Progression->GetSave();
	if (const UJRCharacterDefinition* Def = GI->FindCharacterDefinition(Save->SelectedCharacterId))
	{
		const FJRSkinDefinition* Skin = Def->FindSkin(Save->SelectedSkinId);
		if (!Skin && Def->Skins.Num() > 0)
		{
			Skin = &Def->Skins[0];
		}
		if (Skin)
		{
			Character->ApplySkin(*Skin);
		}
	}
}

void AJRGameMode::HandlePlayerFailure(APawn* FailedPawn)
{
	if (bFailurePending)
	{
		return;
	}
	bFailurePending = true;
	UE_LOG(LogJR, Log, TEXT("Falha do jogador (%s). Reiniciando no checkpoint."), *GetNameSafe(FailedPawn));
	if (UJRObjectiveSubsystem* Objective = GetWorld()->GetSubsystem<UJRObjectiveSubsystem>())
	{
		Objective->FailLevel();
	}
	if (UJRProgressionSubsystem* Progression = GetGameInstance()->GetSubsystem<UJRProgressionSubsystem>())
	{
		Progression->bRestartingFromCheckpoint = true;
	}
	GetWorldTimerManager().SetTimer(RestartTimer, this, &AJRGameMode::RestartFromCheckpoint, RestartDelay, false);
}

void AJRGameMode::RestartFromCheckpoint()
{
	// Recarregar o mapa garante estado limpo (inimigos, veículo, objetos); o save define o checkpoint.
	UGameplayStatics::OpenLevel(this, FName(*UGameplayStatics::GetCurrentLevelName(this)));
}

// Copyright utrazin. All Rights Reserved.

#include "Core/JRGameMode.h"
#include "UI/JRHUD.h"
#include "UI/JRIntroHUD.h" // [A-074]
#include "Cinematics/JRIntroDirector.h" // [A-074]
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
	HUDClass = AJRIntroHUD::StaticClass(); // [A-074] o HUD de sempre + tela de start e abertura
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
	AJRCheckpoint* LevelStartCheckpoint = nullptr;
	for (TActorIterator<AJRCheckpoint> It(GetWorld()); It; ++It)
	{
		if (!SavedId.IsNone() && It->GetCheckpointId() == SavedId)
		{
			return *It;
		}
		if (It->IsLevelStart() && !LevelStartCheckpoint)
		{
			LevelStartCheckpoint = *It;
		}
	}
	return LevelStartCheckpoint;
}

void AJRGameMode::StartPlay()
{
	AJRCheckpoint* Checkpoint = ResolveRespawnCheckpoint();
	StartCheckpoint = Checkpoint;
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

bool AJRGameMode::ShouldPlayIntro() const
{
	// [A-074]
	if (IntroDecision < 0)
	{
		bool bPlay = false;
		const AJRIntroDirector* Director = AJRIntroDirector::FindInWorld(GetWorld());
		const UGameInstance* GI = GetGameInstance();
		const UJRProgressionSubsystem* Progression = GI ? GI->GetSubsystem<UJRProgressionSubsystem>() : nullptr;
		const bool bRestarting = Progression && Progression->bRestartingFromCheckpoint;
		if (Director && Director->CanPlayIntro() && !bRestarting)
		{
			const AJRCheckpoint* Checkpoint = ResolveRespawnCheckpoint();
			bPlay = !Checkpoint || Checkpoint->IsLevelStart();
		}
		IntroDecision = bPlay ? 1 : 0;
		UE_LOG(LogJR, Log, TEXT("Abertura: %s"), bPlay ? TEXT("vai rodar") : TEXT("não roda nesta carga"));
	}
	return IntroDecision == 1;
}

AActor* AJRGameMode::FindPlayerStart_Implementation(AController* Player, const FString& IncomingName)
{
	if (ShouldPlayIntro())
	{
		// [A-074] o herói nasce ao lado da nave caída (no ator da abertura); fica escondido até o Ato 4
		if (AJRIntroDirector* Director = AJRIntroDirector::FindInWorld(GetWorld()))
		{
			return Director;
		}
	}
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
		AJRVehiclePawn* LevelVehicle = bUseLevelVehicle ? FindLevelVehicle() : nullptr;
		if (bVehicle && LevelVehicle)
		{
			// Renasce no carro do mapa (sem criar um segundo buggy).
			LevelVehicle->MoveToTransform(SpawnTransform);
			LevelVehicle->EnableDriving();
			Spawned = LevelVehicle;
		}
		else if (PawnClass)
		{
			FActorSpawnParameters Params;
			Params.Instigator = GetInstigator();
			Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AdjustIfPossibleButAlwaysSpawn;
			Params.ObjectFlags |= RF_Transient;
			Spawned = GetWorld()->SpawnActor<APawn>(PawnClass, SpawnTransform, Params);
		}
		if (!bVehicle && LevelVehicle && Checkpoint->bParkVehicleOnRespawn)
		{
			// Renasce a pé numa zona a pé: o carro fica estacionado onde o jogador o deixou.
			const FTransform Park(FRotator(0.f, Checkpoint->VehicleParkYaw, 0.f), Checkpoint->VehicleParkLocation);
			LevelVehicle->MoveToTransform(Park);
			LevelVehicle->ParkAndDisable();
			if (!Checkpoint->VehicleNeedsItem.IsNone())
			{
				LevelVehicle->SetPendingRequiredItem(Checkpoint->VehicleNeedsItem, Checkpoint->VehicleNeedsItemLabel);
			}
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
	AJRCharacter* Hero = Cast<AJRCharacter>(PlayerPawn);
	ApplySelectedSkin(Hero);
	// Renascer no meio da fase a pé: devolve as armas que o jogador já teria.
	ApplyRespawnLoadout(Hero);
	// Itens-chave que o jogador já teria (ex.: a chave do buggy depois do acampamento).
	const AJRCheckpoint* Checkpoint = StartCheckpoint.IsValid() ? StartCheckpoint.Get() : ResolveRespawnCheckpoint();
	AJRPlayerController* PC = PlayerPawn ? Cast<AJRPlayerController>(PlayerPawn->GetController()) : nullptr;
	if (Checkpoint && PC)
	{
		for (const FName& Item : Checkpoint->RespawnKeyItems)
		{
			PC->GiveKeyItem(Item);
		}
	}
}

void AJRGameMode::ApplyRespawnLoadout(AJRCharacter* Hero) const
{
	if (!Hero)
	{
		return;
	}
	const AJRCheckpoint* Checkpoint = StartCheckpoint.IsValid() ? StartCheckpoint.Get() : ResolveRespawnCheckpoint();
	if (!Checkpoint)
	{
		return;
	}
	if (Checkpoint->bRespawnWithMelee)
	{
		Hero->GrantWeapon(EJRWeaponSlot::Melee, false);
	}
	if (Checkpoint->bRespawnWithPistol)
	{
		Hero->GrantWeapon(EJRWeaponSlot::Pistol, false);
	}
	if (Checkpoint->bRespawnWithShotgun)
	{
		Hero->GrantWeapon(EJRWeaponSlot::Shotgun, false);
	}
}

AJRVehiclePawn* AJRGameMode::FindLevelVehicle() const
{
	for (TActorIterator<AJRVehiclePawn> It(GetWorld()); It; ++It)
	{
		if (!It->IsWrecked() && !It->IsPlayerControlled())
		{
			return *It;
		}
	}
	return nullptr;
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

const FJRSkinDefinition* AJRGameMode::ResolveSelectedSkin() const
{
	const UGameInstance* GameInstance = GetGameInstance();
	const UJRProgressionSubsystem* Progression = GameInstance ? GameInstance->GetSubsystem<UJRProgressionSubsystem>() : nullptr;
	const UJRGameInstance* GI = Cast<UJRGameInstance>(GameInstance);
	if (!Progression || !Progression->GetSave() || !GI)
	{
		return nullptr;
	}
	const UJRSaveGame* Save = Progression->GetSave();
	const UJRCharacterDefinition* Def = GI->FindCharacterDefinition(Save->SelectedCharacterId);
	if (!Def)
	{
		return nullptr;
	}
	const FJRSkinDefinition* Skin = Def->FindSkin(Save->SelectedSkinId);
	if (!Skin && Def->Skins.Num() > 0)
	{
		Skin = &Def->Skins[0];
	}
	return Skin;
}

void AJRGameMode::ApplySelectedSkin(AJRCharacter* Character) const
{
	if (!Character)
	{
		return;
	}
	if (const FJRSkinDefinition* Skin = ResolveSelectedSkin())
	{
		Character->ApplySkin(*Skin);
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

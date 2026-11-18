// Copyright utrazin. All Rights Reserved.

#include "Remap/JRRemapGameMode.h"
#include "Characters/JRCharacter.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "JogoResgate.h"
#include "Kismet/GameplayStatics.h"
#include "Levels/JRObjectiveSubsystem.h"
#include "Remap/JRArenaDirector.h"
#include "Remap/JREconomySubsystem.h"
#include "Remap/JRRemapHUD.h"
#include "Remap/JRRemapTypes.h"
#include "Remap/JRRunSubsystem.h"
#include "TimerManager.h"
#include "UI/JRHUD.h"
#include "UObject/ConstructorHelpers.h"

AJRRemapGameMode::AJRRemapGameMode()
{
	HUDClass = AJRRemapHUD::StaticClass();
	bUseLevelVehicle = false;
	bStartFromBeginningInEditor = true;
	// O BP do controle tem os mapas de teclas (IMC) do herói; a classe C++ pura não tem nenhum.
	static ConstructorHelpers::FClassFinder<APlayerController> PCClass(TEXT("/Game/Core/BP_PlayerController"));
	if (PCClass.Succeeded())
	{
		PlayerControllerClass = PCClass.Class;
	}
	static ConstructorHelpers::FClassFinder<AJRCharacter> HeroClass(TEXT("/Game/Characters/Hero01/BP_Character_Hero01"));
	if (HeroClass.Succeeded())
	{
		FallbackCharacterClass = HeroClass.Class;
	}
}

void AJRRemapGameMode::StartPlay()
{
	// Pula o StartPlay do L01 (checkpoints/abertura): aqui não tem fase nem checkpoint.
	if (UJRObjectiveSubsystem* Objective = GetWorld()->GetSubsystem<UJRObjectiveSubsystem>())
	{
		Objective->InitializeLevel(nullptr, EJRLevelStage::OnFoot);
	}
	AGameModeBase::StartPlay();
}

AActor* AJRRemapGameMode::FindPlayerStart_Implementation(AController* Player, const FString& IncomingName)
{
	return AGameModeBase::FindPlayerStart_Implementation(Player, IncomingName);
}

UClass* AJRRemapGameMode::GetDefaultPawnClassForController_Implementation(AController* InController)
{
	UClass* Class = ResolveCharacterClass();
	return Class ? Class : AGameModeBase::GetDefaultPawnClassForController_Implementation(InController);
}

APawn* AJRRemapGameMode::SpawnDefaultPawnFor_Implementation(AController* NewPlayer, AActor* StartSpot)
{
	return AGameModeBase::SpawnDefaultPawnFor_Implementation(NewPlayer, StartSpot);
}

void AJRRemapGameMode::SetPlayerDefaults(APawn* PlayerPawn)
{
	AGameModeBase::SetPlayerDefaults(PlayerPawn);
	AJRCharacter* Hero = Cast<AJRCharacter>(PlayerPawn);
	if (!Hero)
	{
		return;
	}
	ApplySelectedSkin(Hero);
	if (const UJREconomySubsystem* Economy = GetGameInstance()->GetSubsystem<UJREconomySubsystem>())
	{
		Economy->GrantOwnedWeapons(Hero);
	}
	// Na cidade a arma fica guardada; na arena o diretor equipa e aplica as cartas.
	if (!AJRArenaDirector::FindInWorld(this))
	{
		Hero->SetWeaponEquipped(false);
	}
}

void AJRRemapGameMode::HandlePlayerFailure(APawn* FailedPawn)
{
	if (bDeathPending)
	{
		return;
	}
	bDeathPending = true;
	if (AJRArenaDirector* Director = AJRArenaDirector::FindInWorld(this))
	{
		Director->StopArena();
	}
	UJRRunSubsystem* Run = GetGameInstance()->GetSubsystem<UJRRunSubsystem>();
	if (Run && Run->IsRunActive())
	{
		Run->EndRun(false, 1.f);
		AJRHUD::Toast(this, FString::Printf(TEXT("Você caiu. Fica com %s créditos."), *FString::Printf(TEXT("%lld"), Run->GetReport().CreditsKept)),
			FLinearColor(1.f, 0.4f, 0.35f));
	}
	UE_LOG(LogJR, Log, TEXT("Remap: herói caiu (%s), voltando para a cidade"), *GetNameSafe(FailedPawn));
	GetWorldTimerManager().SetTimer(DeathTimer, this, &AJRRemapGameMode::ReturnAfterDeath, DeathReturnDelay, false);
}

void AJRRemapGameMode::ReturnAfterDeath()
{
	UGameplayStatics::OpenLevel(this, FName(FJRRemapRules::CityMap));
}

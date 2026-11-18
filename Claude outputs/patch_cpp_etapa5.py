"""Aplica as mudanças de C++ da Etapa 5 (Mapa v3). Uso: python3 patch_cpp.py <pasta Source/JogoResgate>"""
import os
import sys

ROOT = sys.argv[1]
EDITS = []


def E(path, old, new):
    EDITS.append((path, old, new))


# ---------------------------------------------------------------- PlayerController
E("Core/JRPlayerController.h", """	/** Sai do veículo atual: estaciona, spawna/reutiliza o personagem, possui e toca a animação. */
	UFUNCTION(BlueprintCallable, Category = "Player")
	bool RequestExitVehicle(const FTransform& FallbackTransform);
""", """	/** Sai do veículo atual: estaciona, spawna/reutiliza o personagem, possui e toca a animação. */
	UFUNCTION(BlueprintCallable, Category = "Player")
	bool RequestExitVehicle(const FTransform& FallbackTransform);

	/**
	 * Entra no veículo a pé (E perto do carro): precisa do item-chave do carro (ex.: CarKey) e, se o carro
	 * estiver sem combustível, do item pendente (ex.: Fuel). Esconde o herói, liga o carro e possui.
	 */
	UFUNCTION(BlueprintCallable, Category = "Player")
	bool RequestEnterVehicle(AJRVehiclePawn* Vehicle);

	/** Itens-chave da fase (CarKey, Fuel, Explosive...). Ficam no controller: valem a pé e no carro. */
	UFUNCTION(BlueprintCallable, Category = "Player|Items")
	void GiveKeyItem(FName Item);

	UFUNCTION(BlueprintPure, Category = "Player|Items")
	bool HasKeyItem(FName Item) const { return !Item.IsNone() && KeyItems.Contains(Item); }

	/** Gasta o item (true se tinha). */
	UFUNCTION(BlueprintCallable, Category = "Player|Items")
	bool ConsumeKeyItem(FName Item);

	/** Console (teste): "JRItens" dá chave do buggy, galão e explosivos. */
	UFUNCTION(Exec)
	void JRItens();
""")
E("Core/JRPlayerController.h", """	UPROPERTY()
	TObjectPtr<AJRVehiclePawn> ParkedVehicle;
""", """	UPROPERTY()
	TObjectPtr<AJRVehiclePawn> ParkedVehicle;

	UPROPERTY()
	TSet<FName> KeyItems;
""")
E("Core/JRPlayerController.cpp", """#include "EnhancedInputComponent.h"
""", """#include "EnhancedInputComponent.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Levels/JRObjectiveSubsystem.h"
""")
E("Core/JRPlayerController.cpp", """	// Reutiliza o personagem se já existir: a transição nunca duplica personagens.
	AJRCharacter* OnFootChar = OnFootCharacter;
	if (OnFootChar)
	{
		OnFootChar->SetActorTransform(SpawnTransform, false, nullptr, ETeleportType::TeleportPhysics);
	}
""", """	// Reutiliza o personagem se já existir: a transição nunca duplica personagens.
	AJRCharacter* OnFootChar = OnFootCharacter;
	bool bNewCharacter = false;
	if (OnFootChar)
	{
		// Estava escondido dentro do carro (RequestEnterVehicle): volta a aparecer, colidir e andar.
		OnFootChar->DetachFromActor(FDetachmentTransformRules::KeepWorldTransform);
		OnFootChar->SetActorHiddenInGame(false);
		OnFootChar->SetActorEnableCollision(true);
		if (UCharacterMovementComponent* Move = OnFootChar->GetCharacterMovement())
		{
			Move->SetMovementMode(MOVE_Walking);
		}
		OnFootChar->SetActorTransform(SpawnTransform, false, nullptr, ETeleportType::TeleportPhysics);
	}
""")
E("Core/JRPlayerController.cpp", """		if (!OnFootChar)
		{
			UE_LOG(LogJR, Error, TEXT("RequestExitVehicle: falha ao spawnar personagem."));
			bExitInProgress = false;
			return false;
		}
	}
""", """		if (!OnFootChar)
		{
			UE_LOG(LogJR, Error, TEXT("RequestExitVehicle: falha ao spawnar personagem."));
			bExitInProgress = false;
			return false;
		}
		bNewCharacter = true;
	}
""")
E("Core/JRPlayerController.cpp", """	if (GameMode)
	{
		GameMode->ApplySelectedSkin(OnFootChar);
	}
	OnFootChar->PlayExitFromVehicle(Vehicle, Vehicle->GetSeatTransform());
	bExitInProgress = false;
	return true;
}
""", """	if (GameMode)
	{
		GameMode->ApplySelectedSkin(OnFootChar);
		if (bNewCharacter)
		{
			// Renasceu no carro: o herói novo recebe as armas do checkpoint (o mapa recarregou).
			GameMode->ApplyRespawnLoadout(OnFootChar);
		}
	}
	if (UJRObjectiveSubsystem* Objective = GetWorld()->GetSubsystem<UJRObjectiveSubsystem>())
	{
		if (Objective->GetStage() == EJRLevelStage::Driving)
		{
			Objective->SetStage(EJRLevelStage::OnFoot);
		}
	}
	OnFootChar->PlayExitFromVehicle(Vehicle, Vehicle->GetSeatTransform());
	bExitInProgress = false;
	return true;
}

bool AJRPlayerController::RequestEnterVehicle(AJRVehiclePawn* Vehicle)
{
	AJRCharacter* Hero = Cast<AJRCharacter>(GetPawn());
	if (!Vehicle || !Hero || bExitInProgress || Vehicle->IsWrecked() || Vehicle->IsPlayerControlled())
	{
		return false;
	}
	const FName CarKey = Vehicle->GetRequiredKeyItem();
	if (!CarKey.IsNone() && !HasKeyItem(CarKey))
	{
		AJRHUD::Toast(this, TEXT("Trancado. Você precisa da chave do buggy."), FLinearColor(1.f, 0.6f, 0.2f));
		return false;
	}
	const FName Pending = Vehicle->GetPendingRequiredItem();
	if (!Pending.IsNone())
	{
		if (!HasKeyItem(Pending))
		{
			AJRHUD::Toast(this, FString::Printf(TEXT("O carro não anda: falta %s."), *Vehicle->GetPendingRequiredItemLabel()),
				FLinearColor(1.f, 0.6f, 0.2f));
			return false;
		}
		ConsumeKeyItem(Pending);
		Vehicle->ClearPendingRequiredItem();
		AJRHUD::Toast(this, TEXT("Tanque abastecido!"), FLinearColor(0.4f, 1.f, 0.5f));
	}

	// O herói "entra": some, para de colidir e vai junto com o carro (volta em RequestExitVehicle).
	OnFootCharacter = Hero;
	if (UCharacterMovementComponent* Move = Hero->GetCharacterMovement())
	{
		Move->StopMovementImmediately();
		Move->DisableMovement();
	}
	Hero->SetActorEnableCollision(false);
	Hero->SetActorHiddenInGame(true);
	Hero->AttachToActor(Vehicle, FAttachmentTransformRules::KeepWorldTransform);

	Vehicle->EnableDriving();
	Possess(Vehicle); // PossessedBy do carro mostra o motorista
	if (UJRObjectiveSubsystem* Objective = GetWorld()->GetSubsystem<UJRObjectiveSubsystem>())
	{
		if (Objective->GetStage() == EJRLevelStage::OnFoot)
		{
			Objective->SetStage(EJRLevelStage::Driving);
		}
	}
	UE_LOG(LogJR, Log, TEXT("RequestEnterVehicle: %s entrou em %s"), *GetNameSafe(Hero), *GetNameSafe(Vehicle));
	return true;
}

void AJRPlayerController::GiveKeyItem(FName Item)
{
	if (!Item.IsNone())
	{
		KeyItems.Add(Item);
	}
}

bool AJRPlayerController::ConsumeKeyItem(FName Item)
{
	return KeyItems.Remove(Item) > 0;
}

void AJRPlayerController::JRItens()
{
	GiveKeyItem(TEXT("CarKey"));
	GiveKeyItem(TEXT("Fuel"));
	GiveKeyItem(TEXT("Explosive"));
	AJRHUD::Toast(this, TEXT("Teste: chave do buggy, galão e explosivos."), FLinearColor(0.6f, 0.9f, 1.f));
}
""")

# ---------------------------------------------------------------- GameMode
E("Core/JRGameMode.h", """class AJRCharacter;
class AJRCheckpoint;
""", """class AJRCharacter;
class AJRCheckpoint;
class AJRVehiclePawn;
""")
E("Core/JRGameMode.h", """	/** Aplica a skin selecionada no save. */
	void ApplySelectedSkin(AJRCharacter* Character) const;
""", """	/** Aplica a skin selecionada no save. */
	void ApplySelectedSkin(AJRCharacter* Character) const;

	/** Armas do checkpoint onde a fase (re)começou (herói criado ao sair do carro depois de renascer nele). */
	void ApplyRespawnLoadout(AJRCharacter* Character) const;

	/** O carro colocado no mapa (buggy do acampamento), se houver e não estiver destruído. */
	AJRVehiclePawn* FindLevelVehicle() const;
""")
E("Core/JRGameMode.h", """	UPROPERTY(EditDefaultsOnly, Category = "Game", meta = (Units = "cm"))
	float VehicleSpawnHeight = 80.f;

private:
""", """	UPROPERTY(EditDefaultsOnly, Category = "Game", meta = (Units = "cm"))
	float VehicleSpawnHeight = 80.f;

	/**
	 * Fase com carro colocado no mapa (L01 v3): renascer "no carro" usa esse carro (não cria outro) e
	 * renascer a pé estaciona o carro no ponto do checkpoint (bParkVehicleOnRespawn).
	 */
	UPROPERTY(EditDefaultsOnly, Category = "Game")
	bool bUseLevelVehicle = true;

private:
	/** Checkpoint usado no começo desta carga do mapa (guardado no StartPlay). */
	TWeakObjectPtr<AJRCheckpoint> StartCheckpoint;

""")
E("Core/JRGameMode.cpp", """void AJRGameMode::StartPlay()
{
	const AJRCheckpoint* Checkpoint = ResolveRespawnCheckpoint();
""", """void AJRGameMode::StartPlay()
{
	AJRCheckpoint* Checkpoint = ResolveRespawnCheckpoint();
	StartCheckpoint = Checkpoint;
""")
E("Core/JRGameMode.cpp", """		if (PawnClass)
		{
			FActorSpawnParameters Params;
			Params.Instigator = GetInstigator();
			Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AdjustIfPossibleButAlwaysSpawn;
			Params.ObjectFlags |= RF_Transient;
			Spawned = GetWorld()->SpawnActor<APawn>(PawnClass, SpawnTransform, Params);
		}
	}
""", """		AJRVehiclePawn* LevelVehicle = bUseLevelVehicle ? FindLevelVehicle() : nullptr;
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
""")
E("Core/JRGameMode.cpp", """	Super::SetPlayerDefaults(PlayerPawn);
	AJRCharacter* Hero = Cast<AJRCharacter>(PlayerPawn);
	ApplySelectedSkin(Hero);
	// Renascer no meio da fase a pé: devolve as armas que o jogador já teria.
	if (Hero)
	{
		if (const AJRCheckpoint* Checkpoint = ResolveRespawnCheckpoint())
		{
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
	}
}
""", """	Super::SetPlayerDefaults(PlayerPawn);
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
""")

# ---------------------------------------------------------------- Checkpoint
E("Levels/JRCheckpoint.h", """	UPROPERTY(EditInstanceOnly, Category = "Checkpoint|Respawn")
	bool bRespawnWithShotgun = false;
""", """	UPROPERTY(EditInstanceOnly, Category = "Checkpoint|Respawn")
	bool bRespawnWithShotgun = false;

	/** Itens-chave que o jogador já tem ao renascer aqui (ex.: CarKey). */
	UPROPERTY(EditInstanceOnly, Category = "Checkpoint|Respawn")
	TArray<FName> RespawnKeyItems;

	/** Renascer aqui (a pé) estaciona o carro do mapa em VehicleParkLocation/VehicleParkYaw (mundo). */
	UPROPERTY(EditInstanceOnly, Category = "Checkpoint|Vehicle")
	bool bParkVehicleOnRespawn = false;

	UPROPERTY(EditInstanceOnly, Category = "Checkpoint|Vehicle", meta = (EditCondition = "bParkVehicleOnRespawn"))
	FVector VehicleParkLocation = FVector::ZeroVector;

	UPROPERTY(EditInstanceOnly, Category = "Checkpoint|Vehicle", meta = (EditCondition = "bParkVehicleOnRespawn"))
	float VehicleParkYaw = 0.f;

	/** Carro parado aqui (transição) só volta a andar com este item (ex.: Fuel no posto). Vazio = nada. */
	UPROPERTY(EditInstanceOnly, Category = "Checkpoint|Vehicle")
	FName VehicleNeedsItem;

	/** Nome mostrado na mensagem ("o galão de gasolina"). */
	UPROPERTY(EditInstanceOnly, Category = "Checkpoint|Vehicle")
	FString VehicleNeedsItemLabel = TEXT("combustível");
""")
E("Levels/JRCheckpoint.cpp", """		if (AJRVehiclePawn* Vehicle = Cast<AJRVehiclePawn>(const_cast<APawn*>(Pawn)))
		{
			Vehicle->StopThenExit(GetRespawnTransform()); // freia antes de descer
		}
""", """		if (AJRVehiclePawn* Vehicle = Cast<AJRVehiclePawn>(const_cast<APawn*>(Pawn)))
		{
			if (!VehicleNeedsItem.IsNone())
			{
				Vehicle->SetPendingRequiredItem(VehicleNeedsItem, VehicleNeedsItemLabel);
			}
			Vehicle->StopThenExit(GetRespawnTransform()); // freia antes de descer
		}
""")

# ---------------------------------------------------------------- Objective: carro <-> a pé alternam
E("Levels/JRObjectiveSubsystem.cpp", """	if (static_cast<uint8>(Checkpoint->GetStageOnRespawn()) > static_cast<uint8>(Stage))
	{
		SetStage(Checkpoint->GetStageOnRespawn());
	}
""", """	// Fase com zonas alternadas (L01 v3): Driving e OnFoot podem ir e voltar; o resto só avança.
	const EJRLevelStage CheckpointStage = Checkpoint->GetStageOnRespawn();
	const bool bCarFootToggle = (Stage == EJRLevelStage::Driving || Stage == EJRLevelStage::OnFoot)
		&& (CheckpointStage == EJRLevelStage::Driving || CheckpointStage == EJRLevelStage::OnFoot);
	if (bCarFootToggle || static_cast<uint8>(CheckpointStage) > static_cast<uint8>(Stage))
	{
		SetStage(CheckpointStage);
	}
""")

# ---------------------------------------------------------------- Vehicle
E("Vehicles/JRVehiclePawn.h", """#include "WheeledVehiclePawn.h"
""", """#include "WheeledVehiclePawn.h"
#include "Interactions/JRInteractable.h"
""")
E("Vehicles/JRVehiclePawn.h", """class JOGORESGATE_API AJRVehiclePawn : public AWheeledVehiclePawn
{
	GENERATED_BODY()

public:
	AJRVehiclePawn();
""", """class JOGORESGATE_API AJRVehiclePawn : public AWheeledVehiclePawn, public IJRInteractable
{
	GENERATED_BODY()

public:
	AJRVehiclePawn();

	// ---- Entrar a pé (E perto do carro): ver AJRPlayerController::RequestEnterVehicle
	virtual bool CanInteract_Implementation(AActor* InstigatorActor) const override;
	virtual void Interact_Implementation(AActor* InstigatorActor) override;
	virtual FText GetInteractionText_Implementation() const override;

	/** Religa o carro estacionado (depois de ParkAndDisable/StopThenExit). */
	UFUNCTION(BlueprintCallable, Category = "Vehicle")
	void EnableDriving();

	/** Teleporta parado (zera velocidades): respawn e estacionar no checkpoint. */
	void MoveToTransform(const FTransform& NewTransform);

	UFUNCTION(BlueprintPure, Category = "Vehicle|Enter")
	FName GetRequiredKeyItem() const { return RequiredKeyItem; }

	/** Item que falta para o carro andar de novo (ex.: Fuel no posto). None = nenhum. */
	UFUNCTION(BlueprintPure, Category = "Vehicle|Enter")
	FName GetPendingRequiredItem() const { return PendingRequiredItem; }

	const FString& GetPendingRequiredItemLabel() const { return PendingRequiredItemLabel; }

	void SetPendingRequiredItem(FName Item, const FString& Label)
	{
		PendingRequiredItem = Item;
		PendingRequiredItemLabel = Label;
	}

	void ClearPendingRequiredItem() { PendingRequiredItem = NAME_None; }
""")
E("Vehicles/JRVehiclePawn.h", """	/** Tempo máximo freando antes de forçar a parada e descer. */
	UPROPERTY(EditDefaultsOnly, Category = "Vehicle", meta = (Units = "s"))
	float ExitStopTimeout = 3.f;
""", """	/** Tempo máximo freando antes de forçar a parada e descer. */
	UPROPERTY(EditDefaultsOnly, Category = "Vehicle", meta = (Units = "s"))
	float ExitStopTimeout = 3.f;

	/** Item-chave para entrar a pé (None = destrancado). O baú da barraca dá "CarKey". */
	UPROPERTY(EditAnywhere, Category = "Vehicle|Enter")
	FName RequiredKeyItem = TEXT("CarKey");
""")
E("Vehicles/JRVehiclePawn.h", """	FTransform PendingExitFallback;
	float StopExitElapsed = 0.f;
""", """	FTransform PendingExitFallback;
	float StopExitElapsed = 0.f;
	FName PendingRequiredItem;
	FString PendingRequiredItemLabel;
""")
E("Vehicles/JRVehiclePawn.cpp", """	if (IsPlayerControlled())
	{
		RefreshDriver();
	}
}
""", """	if (IsPlayerControlled())
	{
		RefreshDriver();
	}
	else
	{
		// Carro estacionado no mapa (buggy do acampamento): banco vazio até o jogador entrar.
		SetDriverVisible(false);
	}
}

bool AJRVehiclePawn::CanInteract_Implementation(AActor* InstigatorActor) const
{
	return !bExploded && !IsPlayerControlled() && Cast<AJRCharacter>(InstigatorActor) != nullptr;
}

void AJRVehiclePawn::Interact_Implementation(AActor* InstigatorActor)
{
	const APawn* Hero = Cast<APawn>(InstigatorActor);
	if (AJRPlayerController* PC = Hero ? Cast<AJRPlayerController>(Hero->GetController()) : nullptr)
	{
		PC->RequestEnterVehicle(this);
	}
}

FText AJRVehiclePawn::GetInteractionText_Implementation() const
{
	return NSLOCTEXT("JogoResgate", "EnterVehicle", "Entrar no buggy");
}

void AJRVehiclePawn::EnableDriving()
{
	GetWorldTimerManager().ClearTimer(SleepTimer);
	GetWorldTimerManager().ClearTimer(StopExitTimer);
	bDriveEnabled = !bExploded;
	ZeroInputs(false);
	GetMesh()->WakeAllRigidBodies();
}

void AJRVehiclePawn::MoveToTransform(const FTransform& NewTransform)
{
	GetMesh()->SetPhysicsLinearVelocity(FVector::ZeroVector);
	GetMesh()->SetPhysicsAngularVelocityInDegrees(FVector::ZeroVector);
	SetActorTransform(NewTransform, false, nullptr, ETeleportType::ResetPhysics);
}
""")

# ---------------------------------------------------------------- Interação: acha o carro (canal Vehicle) também
E("Interactions/JRInteractionComponent.cpp", """	Objects.AddObjectTypesToQuery(ECC_WorldStatic);
""", """	Objects.AddObjectTypesToQuery(ECC_WorldStatic);
	Objects.AddObjectTypesToQuery(ECC_Vehicle);     // buggy (entrar com E)
	Objects.AddObjectTypesToQuery(ECC_PhysicsBody);
""")

# ---------------------------------------------------------------- Baú: item-chave e horda
E("Interactions/JRLootChest.h", """	UPROPERTY(EditAnywhere, Category = "Chest", meta = (Units = "s"))
	float OpenDuration = 2.4f;
""", """	UPROPERTY(EditAnywhere, Category = "Chest", meta = (Units = "s"))
	float OpenDuration = 2.4f;

	/** Item-chave dentro (CarKey, Fuel, Explosive...). None = nenhum. Vai para o AJRPlayerController. */
	UPROPERTY(EditAnywhere, Category = "Chest|Key Item")
	FName KeyItemInside;

	/** Nome mostrado ("CHAVE DO BUGGY"). */
	UPROPERTY(EditAnywhere, Category = "Chest|Key Item")
	FString KeyItemLabel;

	/** Abrir faz barulho e chama uma horda do diretor de IA (ex.: a bomba de gasolina). */
	UPROPERTY(EditAnywhere, Category = "Chest|Horde")
	bool bTriggerHordeOnOpen = false;

	UPROPERTY(EditAnywhere, Category = "Chest|Horde", meta = (EditCondition = "bTriggerHordeOnOpen"))
	int32 HordeSize = 20;

	UPROPERTY(EditAnywhere, Category = "Chest|Horde", meta = (EditCondition = "bTriggerHordeOnOpen", Units = "s"))
	float HordeDuration = 45.f;
""")
E("Interactions/JRLootChest.cpp", """#include "Interactions/JRLootChest.h"
""", """#include "Interactions/JRLootChest.h"
#include "AI/JRAIDirector.h"
#include "Core/JRPlayerController.h"
""")
E("Interactions/JRLootChest.cpp", """	if (HealthInside > 0.f)
	{
		Hero->GetHealthComponent()->Heal(HealthInside);
	}
""", """	if (HealthInside > 0.f)
	{
		Hero->GetHealthComponent()->Heal(HealthInside);
	}
	if (!KeyItemInside.IsNone())
	{
		if (AJRPlayerController* PC = Cast<AJRPlayerController>(Hero->GetController()))
		{
			PC->GiveKeyItem(KeyItemInside);
		}
		AJRHUD::Toast(this, FString::Printf(TEXT("Você achou: %s!"), KeyItemLabel.IsEmpty() ? *KeyItemInside.ToString() : *KeyItemLabel),
			FLinearColor(0.2f, 1.f, 0.8f));
	}
	if (bTriggerHordeOnOpen)
	{
		if (AJRAIDirector* Director = AJRAIDirector::Find(this))
		{
			Director->TriggerHordeAt(TEXT("Bau"), GetActorLocation(), HordeDuration, HordeSize);
			AJRHUD::Toast(this, TEXT("O barulho atraiu a horda! Aguente firme."), FLinearColor(1.f, 0.35f, 0.2f));
		}
	}
""")

# ---------------------------------------------------------------- Gatilho de história: fim da fase
E("Gameplay/JRStoryTrigger.h", """	/** Só dispara a pé (true) ou também no carro. */
	UPROPERTY(EditAnywhere, Category = "Story")
	bool bOnFootOnly = false;
""", """	/** Só dispara a pé (true) ou também no carro. */
	UPROPERTY(EditAnywhere, Category = "Story")
	bool bOnFootOnly = false;

	/** Portão de saída: conclui a fase (só depois de libertar todos os AJRRescueTarget do mapa). */
	UPROPERTY(EditAnywhere, Category = "Story")
	bool bCompletesLevel = false;
""")
E("Gameplay/JRStoryTrigger.cpp", """#include "Characters/JRCharacter.h"
""", """#include "Characters/JRCharacter.h"
#include "EngineUtils.h"
#include "Interactions/JRRescueTarget.h"
#include "Levels/JRObjectiveSubsystem.h"
""")
E("Gameplay/JRStoryTrigger.cpp", """	if (bDone || !Pawn || !Pawn->IsPlayerControlled() || (bOnFootOnly && !Pawn->IsA<AJRCharacter>()))
	{
		return;
	}
	bDone = true;
""", """	if (bDone || !Pawn || !Pawn->IsPlayerControlled() || (bOnFootOnly && !Pawn->IsA<AJRCharacter>()))
	{
		return;
	}
	if (bCompletesLevel)
	{
		for (TActorIterator<AJRRescueTarget> It(GetWorld()); It; ++It)
		{
			if (!It->IsRescued())
			{
				AJRHUD::Toast(this, TEXT("Falta a sobrevivente! Volte à vila."), FLinearColor(1.f, 0.5f, 0.3f));
				return; // dispara de novo quando ela estiver livre
			}
		}
	}
	bDone = true;
	if (bCompletesLevel)
	{
		if (UJRObjectiveSubsystem* Objective = GetWorld()->GetSubsystem<UJRObjectiveSubsystem>())
		{
			Objective->CompleteLevel();
		}
	}
""")

# ---------------------------------------------------------------- Resgate sem fim automático
E("Interactions/JRRescueTarget.h", """	UFUNCTION(BlueprintPure, Category = "Rescue")
	FName GetRescueId() const { return RescueId; }
""", """	UFUNCTION(BlueprintPure, Category = "Rescue")
	FName GetRescueId() const { return RescueId; }

	UFUNCTION(BlueprintPure, Category = "Rescue")
	bool IsRescued() const { return bRescued; }
""")
E("Interactions/JRRescueTarget.h", """	UPROPERTY(EditAnywhere, Category = "Rescue")
	FName RescueId = TEXT("Victim01");
""", """	UPROPERTY(EditAnywhere, Category = "Rescue")
	FName RescueId = TEXT("Victim01");

	/** true: libertar conclui a fase (L01 v2). false (L01 v3): o jogador ainda dirige até o portão de saída. */
	UPROPERTY(EditAnywhere, Category = "Rescue")
	bool bCompleteLevelOnRescue = true;
""")
E("Interactions/JRRescueTarget.h", """private:
	FTimerHandle FinishTimer;
	bool bRescued = false;
""", """private:
	FTimerHandle FinishTimer;
	bool bRescued = false;
	TWeakObjectPtr<AController> Rescuer;
""")
E("Interactions/JRRescueTarget.cpp", """#include "TimerManager.h"
""", """#include "TimerManager.h"
#include "UI/JRHUD.h"
""")
E("Interactions/JRRescueTarget.cpp", """	if (AController* C = Character->GetController())
	{
		C->SetIgnoreMoveInput(true);
	}
""", """	if (AController* C = Character->GetController())
	{
		C->SetIgnoreMoveInput(true);
		Rescuer = C;
	}
""")
E("Interactions/JRRescueTarget.cpp", """	OnRescueCompleted();
	if (UJRObjectiveSubsystem* Objective = GetWorld()->GetSubsystem<UJRObjectiveSubsystem>())
	{
		Objective->CompleteLevel();
	}
}""", """	OnRescueCompleted();
	if (!bCompleteLevelOnRescue)
	{
		if (AController* C = Rescuer.Get())
		{
			C->SetIgnoreMoveInput(false);
		}
		AJRHUD::Toast(this, TEXT("Ela está livre! Voltem ao buggy e saiam pelo portão norte."), FLinearColor(0.4f, 1.f, 0.6f));
		return;
	}
	if (UJRObjectiveSubsystem* Objective = GetWorld()->GetSubsystem<UJRObjectiveSubsystem>())
	{
		Objective->CompleteLevel();
	}
}""")

GATE_H = r'''// Copyright utrazin. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "Interactions/JRInteractable.h"
#include "JRBlockingGate.generated.h"

class UBoxComponent;
class UNiagaraSystem;
class UPointLightComponent;
class USoundBase;
class UStaticMeshComponent;
class AJRBlockingGate;

DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FJROnGateOpened, AJRBlockingGate*, Gate);

/**
 * Portão que bloqueia a rota (ex.: árvore caída sobre a ponte, L01 v3 zona 4).
 * O herói aperta E com o item exigido (ex.: "Explosive" do baú da colmeia): o pavio queima FuseTime,
 * explode (dano em área), o bloqueio some e o diretor de IA manda uma horda (fuga de carro, zona 5).
 * Sem item exigido (RequiredItem = None) abre direto com E. Sem Tick.
 */
UCLASS()
class JOGORESGATE_API AJRBlockingGate : public AActor, public IJRInteractable
{
	GENERATED_BODY()

public:
	AJRBlockingGate();

	virtual bool CanInteract_Implementation(AActor* InstigatorActor) const override;
	virtual void Interact_Implementation(AActor* InstigatorActor) override;
	virtual FText GetInteractionText_Implementation() const override;

	/** Abre na hora (sem pavio). */
	UFUNCTION(BlueprintCallable, Category = "Gate")
	void OpenGate();

	UFUNCTION(BlueprintPure, Category = "Gate")
	bool IsOpen() const { return bOpen; }

	UPROPERTY(BlueprintAssignable, Category = "Gate")
	FJROnGateOpened OnGateOpened;

protected:
	/** Gancho Blueprint para som/VFX de verdade. */
	UFUNCTION(BlueprintImplementableEvent, Category = "Gate")
	void BP_OnGateOpened();

	void Detonate();
	void EndFlash();

	UPROPERTY(VisibleAnywhere, Category = "Gate")
	TObjectPtr<USceneComponent> Root;

	/** Visual do bloqueio (ex.: tronco DeadTree_5 deitado). A malha é posta pelo build_l01.py. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Gate")
	TObjectPtr<UStaticMeshComponent> BlockerMesh;

	/** Caixa invisível que segura o carro e o herói (a malha pode ter vãos). */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Gate")
	TObjectPtr<UBoxComponent> BlockVolume;

	UPROPERTY(VisibleAnywhere, Category = "Gate")
	TObjectPtr<UPointLightComponent> FlashLight;

	/** Item exigido (None = abre direto). */
	UPROPERTY(EditAnywhere, Category = "Gate")
	FName RequiredItem = TEXT("Explosive");

	/** Nome do item na mensagem ("explosivos"). */
	UPROPERTY(EditAnywhere, Category = "Gate")
	FString RequiredItemLabel = TEXT("explosivos");

	UPROPERTY(EditAnywhere, Category = "Gate")
	FString HintWithoutItem = TEXT("Precisa de explosivos. Procure na colmeia, além do lago.");

	UPROPERTY(EditAnywhere, Category = "Gate", meta = (Units = "s"))
	float FuseTime = 4.f;

	UPROPERTY(EditAnywhere, Category = "Gate|Explosion", meta = (Units = "cm"))
	float ExplosionRadius = 900.f;

	UPROPERTY(EditAnywhere, Category = "Gate|Explosion")
	float ExplosionDamage = 150.f;

	UPROPERTY(EditAnywhere, Category = "Gate|Explosion")
	TObjectPtr<UNiagaraSystem> ExplosionSystem;

	UPROPERTY(EditAnywhere, Category = "Gate|Explosion")
	TObjectPtr<USoundBase> ExplosionSound;

	/** A explosão chama uma horda do AJRAIDirector (perto do portão). */
	UPROPERTY(EditAnywhere, Category = "Gate|Horde")
	bool bTriggerHorde = true;

	UPROPERTY(EditAnywhere, Category = "Gate|Horde", meta = (EditCondition = "bTriggerHorde"))
	int32 HordeSize = 30;

	UPROPERTY(EditAnywhere, Category = "Gate|Horde", meta = (EditCondition = "bTriggerHorde", Units = "s"))
	float HordeDuration = 60.f;

private:
	FTimerHandle FuseTimer;
	FTimerHandle FlashTimer;
	bool bArmed = false;
	bool bOpen = false;
};
'''

GATE_CPP = r'''// Copyright utrazin. All Rights Reserved.

#include "Gameplay/JRBlockingGate.h"
#include "AI/JRAIDirector.h"
#include "Characters/JRCharacter.h"
#include "Components/BoxComponent.h"
#include "Components/PointLightComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Core/JRPlayerController.h"
#include "Engine/World.h"
#include "GameFramework/DamageType.h"
#include "JogoResgate.h"
#include "Kismet/GameplayStatics.h"
#include "NiagaraFunctionLibrary.h"
#include "NiagaraSystem.h"
#include "TimerManager.h"
#include "UI/JRHUD.h"

AJRBlockingGate::AJRBlockingGate()
{
	PrimaryActorTick.bCanEverTick = false;
	Root = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
	RootComponent = Root;
	BlockerMesh = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("BlockerMesh"));
	BlockerMesh->SetupAttachment(Root);
	BlockerMesh->SetCollisionProfileName(TEXT("BlockAll"));
	BlockVolume = CreateDefaultSubobject<UBoxComponent>(TEXT("BlockVolume"));
	BlockVolume->SetupAttachment(Root);
	BlockVolume->SetBoxExtent(FVector(180.f, 750.f, 350.f));
	BlockVolume->SetRelativeLocation(FVector(0.f, 0.f, 300.f));
	BlockVolume->SetCollisionProfileName(TEXT("BlockAll"));
	BlockVolume->SetHiddenInGame(true);
	FlashLight = CreateDefaultSubobject<UPointLightComponent>(TEXT("FlashLight"));
	FlashLight->SetupAttachment(Root);
	FlashLight->SetRelativeLocation(FVector(0.f, 0.f, 300.f));
	FlashLight->SetIntensity(0.f);
	FlashLight->SetAttenuationRadius(3000.f);
	FlashLight->SetLightColor(FLinearColor(1.f, 0.55f, 0.2f));
	FlashLight->SetCastShadows(false);
}

bool AJRBlockingGate::CanInteract_Implementation(AActor* InstigatorActor) const
{
	return !bOpen && !bArmed && Cast<AJRCharacter>(InstigatorActor) != nullptr;
}

FText AJRBlockingGate::GetInteractionText_Implementation() const
{
	return RequiredItem.IsNone() ? NSLOCTEXT("JogoResgate", "GateOpen", "Abrir passagem")
		: NSLOCTEXT("JogoResgate", "GateArm", "Armar explosivo");
}

void AJRBlockingGate::Interact_Implementation(AActor* InstigatorActor)
{
	if (!Execute_CanInteract(this, InstigatorActor))
	{
		return;
	}
	if (RequiredItem.IsNone())
	{
		OpenGate();
		return;
	}
	const APawn* Hero = Cast<APawn>(InstigatorActor);
	AJRPlayerController* PC = Hero ? Cast<AJRPlayerController>(Hero->GetController()) : nullptr;
	if (!PC || !PC->HasKeyItem(RequiredItem))
	{
		AJRHUD::Toast(this, HintWithoutItem, FLinearColor(1.f, 0.6f, 0.2f));
		return;
	}
	PC->ConsumeKeyItem(RequiredItem);
	bArmed = true;
	AJRHUD::Toast(this, FString::Printf(TEXT("Explosivo armado! Afaste-se (%.0f s)."), FuseTime), FLinearColor(1.f, 0.35f, 0.1f));
	GetWorldTimerManager().SetTimer(FuseTimer, this, &AJRBlockingGate::Detonate, FMath::Max(FuseTime, 0.1f), false);
}

void AJRBlockingGate::Detonate()
{
	const FVector Origin = BlockVolume->GetComponentLocation();
	OpenGate(); // antes do dano: a caixa não pode "proteger" quem está do outro lado
	UGameplayStatics::ApplyRadialDamage(this, ExplosionDamage, Origin, ExplosionRadius, UDamageType::StaticClass(),
		TArray<AActor*>(), this, nullptr, true);
	if (ExplosionSystem)
	{
		UNiagaraFunctionLibrary::SpawnSystemAtLocation(this, ExplosionSystem, Origin);
	}
	if (ExplosionSound)
	{
		UGameplayStatics::PlaySoundAtLocation(this, ExplosionSound, Origin);
	}
	FlashLight->SetIntensity(200000.f);
	GetWorldTimerManager().SetTimer(FlashTimer, this, &AJRBlockingGate::EndFlash, 0.35f, false);
	if (bTriggerHorde)
	{
		if (AJRAIDirector* Director = AJRAIDirector::Find(this))
		{
			Director->TriggerHordeAt(TEXT("Portao"), Origin, HordeDuration, HordeSize);
		}
		AJRHUD::Toast(this, TEXT("BUM! Caminho livre... e a horda ouviu! Corra para o buggy!"), FLinearColor(1.f, 0.3f, 0.2f));
	}
}

void AJRBlockingGate::EndFlash()
{
	FlashLight->SetIntensity(0.f);
}

void AJRBlockingGate::OpenGate()
{
	if (bOpen)
	{
		return;
	}
	bOpen = true;
	bArmed = false;
	BlockerMesh->SetVisibility(false, true);
	BlockerMesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	BlockVolume->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	UE_LOG(LogJR, Log, TEXT("%s aberto"), *GetName());
	OnGateOpened.Broadcast(this);
	BP_OnGateOpened();
}
'''


def main():
    errors = []
    for path, old, new in EDITS:
        fp = os.path.join(ROOT, path)
        s = open(fp, encoding="utf-8", newline="").read()
        if "\r\n" in s:
            old, new = old.replace("\n", "\r\n"), new.replace("\n", "\r\n")
        if new in s:
            print("já aplicado:", path)
            continue
        n = s.count(old)
        if n != 1:
            errors.append(f"{path}: trecho encontrado {n} vezes: {old[:70]!r}")
            continue
        s = s.replace(old, new)
        with open(fp, "w", encoding="utf-8", newline="") as f:
            f.write(s)
        print("ok:", path)
    for name, text in (("Gameplay/JRBlockingGate.h", GATE_H), ("Gameplay/JRBlockingGate.cpp", GATE_CPP)):
        with open(os.path.join(ROOT, name), "w", encoding="utf-8", newline="") as f:
            f.write(text)
        print("novo:", name)
    if errors:
        print("\n".join(errors))
        sys.exit(1)


main()

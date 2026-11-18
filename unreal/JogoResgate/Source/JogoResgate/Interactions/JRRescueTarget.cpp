// Copyright utrazin. All Rights Reserved.

#include "Interactions/JRRescueTarget.h"
#include "Animation/AnimInstance.h"
#include "Animation/AnimSequenceBase.h"
#include "Camera/PlayerCameraManager.h"
#include "CollisionQueryParams.h"
#include "Engine/SkeletalMesh.h"
#include "GameFramework/Pawn.h"
#include "GameFramework/PlayerController.h"
#include "Kismet/GameplayStatics.h"
#include "Vehicles/JRVehiclePawn.h"
#include "Characters/JRCharacter.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "FX/JRInteractionCameraComponent.h"
#include "Engine/World.h"
#include "GameFramework/Controller.h"
#include "Levels/JRObjectiveSubsystem.h"
#include "TimerManager.h"
#include "UI/JRHUD.h"

AJRRescueTarget::AJRRescueTarget()
{
	// [A-075] Tick só depois de solta (seguir o herói e embarcar no buggy).
	PrimaryActorTick.bCanEverTick = true;
	PrimaryActorTick.bStartWithTickEnabled = false;
	PrimaryActorTick.TickInterval = 0.f;
	Root = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
	RootComponent = Root;
	CageMesh = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("CageMesh"));
	CageMesh->SetupAttachment(Root);
	VictimMesh = CreateDefaultSubobject<USkeletalMeshComponent>(TEXT("VictimMesh"));
	VictimMesh->SetupAttachment(Root);
	PlayerAlignPoint = CreateDefaultSubobject<USceneComponent>(TEXT("PlayerAlignPoint"));
	PlayerAlignPoint->SetupAttachment(Root);
	PlayerAlignPoint->SetRelativeLocation(FVector(80.f, 0.f, 0.f));
	PlayerAlignPoint->SetRelativeRotation(FRotator(0.f, 180.f, 0.f));
	InteractionText = NSLOCTEXT("JogoResgate", "RescueInteract", "Libertar");
}

bool AJRRescueTarget::CanInteract_Implementation(AActor* InstigatorActor) const
{
	const UJRObjectiveSubsystem* Objective = GetWorld()->GetSubsystem<UJRObjectiveSubsystem>();
	return !bRescued && Objective && Objective->GetStage() == EJRLevelStage::Rescue && InstigatorActor && InstigatorActor->IsA<AJRCharacter>();
}

FText AJRRescueTarget::GetInteractionText_Implementation() const
{
	return InteractionText;
}

void AJRRescueTarget::Interact_Implementation(AActor* InstigatorActor)
{
	if (!Execute_CanInteract(this, InstigatorActor))
	{
		return;
	}
	bRescued = true;
	OnCageOpened();

	AJRCharacter* Character = Cast<AJRCharacter>(InstigatorActor);
	Character->SetActorLocationAndRotation(PlayerAlignPoint->GetComponentLocation(), PlayerAlignPoint->GetComponentRotation(),
		false, nullptr, ETeleportType::TeleportPhysics);
	if (AController* C = Character->GetController())
	{
		C->SetIgnoreMoveInput(true);
		Rescuer = C;
	}
	const float PlayerDuration = Character->PlayRescueHug();
	float VictimDuration = 0.f;
	if (VictimHugMontage && VictimMesh->GetAnimInstance())
	{
		VictimDuration = VictimMesh->GetAnimInstance()->Montage_Play(VictimHugMontage);
	}
	const float Duration = FMath::Max3(PlayerDuration, VictimDuration, 0.f);
	// [A-058] plano com os dois (mesmo com zumbis por perto: é o momento da fase).
	if (UJRInteractionCameraComponent* ShotCam = Character->GetInteractionCamera())
	{
		ShotCam->PlayShot(EJRInteractionShot::Rescue, this, Duration > 0.f ? Duration : FallbackHugDuration, true);
	}
	GetWorldTimerManager().SetTimer(FinishTimer, this, &AJRRescueTarget::FinishRescue, Duration > 0.f ? Duration : FallbackHugDuration, false);
}

void AJRRescueTarget::FinishRescue()
{
	OnRescueCompleted();
	if (!bCompleteLevelOnRescue)
	{
		if (AController* C = Rescuer.Get())
		{
			C->SetIgnoreMoveInput(false);
		}
		AJRHUD::Toast(this, TEXT("Ela está livre! Voltem ao buggy e saiam pelo portão norte."), FLinearColor(0.4f, 1.f, 0.6f));
		StartFollowing(); // [A-075]
		return;
	}
	if (UJRObjectiveSubsystem* Objective = GetWorld()->GetSubsystem<UJRObjectiveSubsystem>())
	{
		Objective->CompleteLevel();
	}
}

// ---------------------------------------------------------------- [A-075] seguir e embarcar

void AJRRescueTarget::StartFollowing()
{
	if (!bFollowAfterRescue && !bBoardVehicleWithHero)
	{
		return;
	}
	IdleAnimCache = Cast<UAnimSequenceBase>(VictimMesh->AnimationData.AnimToPlay);
	// Carrega uma vez só (caminho sem asset = nullptr, e ela fica parada esperando o embarque).
	WalkAnimCache = FollowWalkAnim.IsNull() ? nullptr : FollowWalkAnim.LoadSynchronous();
	RunAnimCache = FollowRunAnim.IsNull() ? nullptr : FollowRunAnim.LoadSynchronous();
	if (!RunAnimCache)
	{
		RunAnimCache = WalkAnimCache;
	}
	bFollowing = true;
	CurrentGait = -1;
	SetActorTickEnabled(true);
}

void AJRRescueTarget::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	if (!bFollowing || BoardedVehicle.IsValid())
	{
		return;
	}
	const APlayerController* PC = UGameplayStatics::GetPlayerController(this, 0);
	const APawn* PlayerPawn = PC ? PC->GetPawn() : nullptr;
	if (!PlayerPawn)
	{
		return;
	}
	if (AJRVehiclePawn* Vehicle = Cast<AJRVehiclePawn>(const_cast<APawn*>(PlayerPawn)))
	{
		if (bBoardVehicleWithHero && !Vehicle->IsWrecked())
		{
			BoardVehicle(Vehicle);
		}
		return;
	}
	if (bFollowAfterRescue)
	{
		TickFollow(DeltaSeconds, PlayerPawn);
	}
}

void AJRRescueTarget::SetFollowGait(int32 Gait, float PlayRate)
{
	UAnimSequenceBase* Anim = Gait == 1 ? WalkAnimCache.Get() : (Gait == 2 ? RunAnimCache.Get() : IdleAnimCache.Get());
	if (Gait != CurrentGait && Anim)
	{
		VictimMesh->SetAnimationMode(EAnimationMode::AnimationSingleNode);
		VictimMesh->PlayAnimation(Anim, true);
		CurrentGait = Gait;
	}
	VictimMesh->SetPlayRate(Gait == 0 ? 1.f : FMath::Clamp(PlayRate, 0.6f, 1.6f));
}

void AJRRescueTarget::TickFollow(float DeltaSeconds, const APawn* Hero)
{
	// Sem animação de andar ela não desliza pelo mapa: espera no lugar e embarca com o fade.
	if (!WalkAnimCache)
	{
		return;
	}
	const FVector HeroLoc = Hero->GetActorLocation();
	FVector Loc = VictimMesh->GetComponentLocation();
	FVector ToHero = HeroLoc - Loc;
	ToHero.Z = 0.f;
	const float Dist = ToHero.Size();
	UWorld* World = GetWorld();
	FCollisionQueryParams Params(SCENE_QUERY_STAT(JRRescueFollow), false, this);
	Params.AddIgnoredActor(Hero);
	auto GroundAt = [&](const FVector& P, float& OutZ) -> bool
	{
		FHitResult Hit;
		// Só chão estático (terreno, prédios): não "sobe" em zumbi nem no carro.
		if (World->LineTraceSingleByObjectType(Hit, P + FVector(0.f, 0.f, 150.f), P - FVector(0.f, 0.f, 400.f),
			FCollisionObjectQueryParams(ECC_WorldStatic), Params))
		{
			OutZ = Hit.ImpactPoint.Z;
			return true;
		}
		return false;
	};

	if (Dist > FollowCatchUpDistance)
	{
		// Ficou para trás: reaparece atrás do herói (longe da câmera de terceira pessoa ela não é vista surgindo).
		const FVector Behind = HeroLoc - Hero->GetActorForwardVector() * (FollowStopDistance + 150.f);
		float Z = Behind.Z - 90.f;
		GroundAt(Behind, Z);
		VictimMesh->SetWorldLocation(FVector(Behind.X, Behind.Y, Z + 2.f));
		SetFollowGait(0, 1.f);
		return;
	}
	if (Dist <= FollowStopDistance)
	{
		SetFollowGait(0, 1.f);
		if (Dist > 1.f)
		{
			const float FaceYaw = ToHero.Rotation().Yaw + VictimMeshYawOffset;
			const FRotator Now = VictimMesh->GetComponentRotation();
			VictimMesh->SetWorldRotation(FRotator(0.f, FMath::FixedTurn(Now.Yaw, FaceYaw, 240.f * DeltaSeconds), 0.f));
		}
		return;
	}
	const bool bRun = Dist > FollowRunDistance;
	const float Speed = bRun ? FollowRunSpeed : FollowWalkSpeed;
	const FVector Dir = ToHero / Dist;
	const float Step = FMath::Min(Speed * DeltaSeconds, Dist - FollowStopDistance);
	FVector Next = Loc + Dir * Step;
	float Z = Loc.Z;
	if (GroundAt(Next, Z))
	{
		// Degrau alto demais (parede, carro): não sobe; espera o herói voltar ou o catch-up.
		if (Z - Loc.Z > 60.f)
		{
			SetFollowGait(0, 1.f);
			return;
		}
		Next.Z = FMath::FInterpTo(Loc.Z, Z + 2.f, DeltaSeconds, 12.f);
	}
	VictimMesh->SetWorldLocation(Next);
	const float MoveYaw = Dir.Rotation().Yaw + VictimMeshYawOffset;
	const FRotator Cur = VictimMesh->GetComponentRotation();
	VictimMesh->SetWorldRotation(FRotator(0.f, FMath::FixedTurn(Cur.Yaw, MoveYaw, 360.f * DeltaSeconds), 0.f));
	SetFollowGait(bRun ? 2 : 1, Speed / FMath::Max(1.f, bRun ? RunAnimSpeed : WalkAnimSpeed));
}

void AJRRescueTarget::BoardVehicle(AJRVehiclePawn* Vehicle)
{
	if (!Vehicle || !VictimMesh->GetSkeletalMeshAsset())
	{
		return;
	}
	// Sentada (setup_passenger.py) ou, sem ela, a pose atual com as pernas escondidas.
	UAnimSequenceBase* Sit = PassengerSitAnim.IsNull() ? nullptr : PassengerSitAnim.LoadSynchronous();
	Vehicle->SetPassenger(VictimMesh, Sit ? Sit : IdleAnimCache.Get(), Sit != nullptr);
	VictimMesh->SetHiddenInGame(true);
	VictimMesh->SetComponentTickEnabled(false);
	BoardedVehicle = Vehicle;
	bFollowing = false;
	SetActorTickEnabled(false);
	if (APlayerController* PC = UGameplayStatics::GetPlayerController(this, 0))
	{
		if (PC->PlayerCameraManager)
		{
			// Corte rápido para o preto e volta: cobre ela "aparecendo" no banco.
			PC->PlayerCameraManager->StartCameraFade(1.f, 0.f, 0.7f, FLinearColor::Black, false, false);
		}
	}
	AJRHUD::Toast(this, TEXT("Ela subiu no buggy! Saiam pelo portão norte."), FLinearColor(0.4f, 1.f, 0.6f));
}

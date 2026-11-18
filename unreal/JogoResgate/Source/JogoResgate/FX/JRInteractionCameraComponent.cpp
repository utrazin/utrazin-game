// Copyright utrazin. All Rights Reserved.

#include "FX/JRInteractionCameraComponent.h"
#include "Camera/CameraActor.h"
#include "Camera/CameraComponent.h"
#include "Camera/PlayerCameraManager.h"
#include "Characters/JRCharacter.h"
#include "Combat/JRHealthComponent.h"
#include "Components/CapsuleComponent.h"
#include "Engine/OverlapResult.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "TimerManager.h"

namespace
{
	FJRInteractionShotFraming MakeShot(const FVector& Offset, float FocusHeight, float TowardTarget, float FOV,
		float BlendIn, float BlendOut)
	{
		FJRInteractionShotFraming Framing;
		Framing.CameraOffset = Offset;
		Framing.FocusHeight = FocusHeight;
		Framing.FocusTowardTarget = TowardTarget;
		Framing.FOV = FOV;
		Framing.BlendIn = BlendIn;
		Framing.BlendOut = BlendOut;
		return Framing;
	}
}

UJRInteractionCameraComponent::UJRInteractionCameraComponent()
{
	// Tick só durante a cena em primeira pessoa (virar o olhar suave); desligado o resto do tempo.
	PrimaryComponentTick.bCanEverTick = true;
	PrimaryComponentTick.bStartWithTickEnabled = false;

	// Enquadramentos padrão (ajustáveis no Blueprint do herói). Offset: X = para o objeto, Y = direita, Z = cima.
	Shots.Add(EJRInteractionShot::Chest, MakeShot(FVector(-110.f, 170.f, 60.f), 85.f, 0.45f, 55.f, 0.45f, 0.5f));
	// [A-073] pegar do chão: era de frente e rente ao chão (via-se o topo da cabeça abaixando e nada do item).
	// Agora 3/4 de lado, um pouco à frente, câmera a ~1,15 m olhando levemente para baixo: mão e item no quadro.
	Shots.Add(EJRInteractionShot::PickupGround, MakeShot(FVector(40.f, 175.f, 45.f), 70.f, 0.55f, 55.f, 0.5f, 0.55f));
	Shots.Add(EJRInteractionShot::VehicleExit, MakeShot(FVector(120.f, -420.f, 120.f), 100.f, 0.f, 55.f, 0.5f, 0.6f));
	Shots.Add(EJRInteractionShot::VehicleEnter, MakeShot(FVector(120.f, -420.f, 120.f), 100.f, 0.f, 55.f, 0.5f, 0.6f));
	Shots.Add(EJRInteractionShot::GatePlant, MakeShot(FVector(-280.f, 70.f, 230.f), 60.f, 0.3f, 60.f, 0.5f, 0.6f));
	Shots.Add(EJRInteractionShot::Rescue, MakeShot(FVector(30.f, 340.f, 60.f), 120.f, 0.5f, 50.f, 0.6f, 0.7f));
	Shots.Add(EJRInteractionShot::FuelPump, MakeShot(FVector(-80.f, -190.f, 70.f), 110.f, 0.4f, 55.f, 0.45f, 0.5f));
}

bool UJRInteractionCameraComponent::IsEnemyNearby() const
{
	const AActor* Owner = GetOwner();
	UWorld* World = GetWorld();
	if (!Owner || !World || SafetyRadius <= 0.f)
	{
		return false;
	}
	TArray<FOverlapResult> Overlaps;
	FCollisionObjectQueryParams Objects;
	Objects.AddObjectTypesToQuery(ECC_Pawn);
	FCollisionQueryParams Query(SCENE_QUERY_STAT(JRShotSafety), false, Owner);
	World->OverlapMultiByObjectType(Overlaps, Owner->GetActorLocation(), FQuat::Identity, Objects,
		FCollisionShape::MakeSphere(SafetyRadius), Query);
	for (const FOverlapResult& Overlap : Overlaps)
	{
		const APawn* Other = Cast<APawn>(Overlap.GetActor());
		if (!Other || Other->IsPlayerControlled())
		{
			continue;
		}
		const UJRHealthComponent* OtherHealth = Other->FindComponentByClass<UJRHealthComponent>();
		if (OtherHealth && !OtherHealth->IsDead())
		{
			return true;
		}
	}
	return false;
}

bool UJRInteractionCameraComponent::PlayShot(EJRInteractionShot Shot, AActor* Target, float ActionSeconds, bool bIgnoreEnemies,
	AActor* BlendFrom)
{
	APawn* Pawn = Cast<APawn>(GetOwner());
	APlayerController* PC = Pawn ? Cast<APlayerController>(Pawn->GetController()) : nullptr;
	UWorld* World = GetWorld();
	const FJRInteractionShotFraming* Framing = Shots.Find(Shot);
	if (!bShotsEnabled || !PC || !World || !Framing || ActionSeconds <= 0.f)
	{
		return false;
	}
	if (!bIgnoreEnemies && IsEnemyNearby())
	{
		return false; // em combate a câmera fica livre
	}
	StopShot(true);

	// Referencial: herói virado para o objeto (sem objeto: para onde o herói olha).
	const FVector HeroLoc = Pawn->GetActorLocation();
	FVector Facing = Target ? (Target->GetActorLocation() - HeroLoc).GetSafeNormal2D() : FVector::ZeroVector;
	if (Facing.IsNearlyZero())
	{
		Facing = Pawn->GetActorForwardVector().GetSafeNormal2D();
	}
	const FRotator Frame(0.f, Facing.Rotation().Yaw, 0.f);
	const ACharacter* Char = Cast<ACharacter>(Pawn);
	const float HalfHeight = Char && Char->GetCapsuleComponent() ? Char->GetCapsuleComponent()->GetScaledCapsuleHalfHeight() : 90.f;
	FVector Focus = HeroLoc + FVector(0.f, 0.f, Framing->FocusHeight - HalfHeight);
	if (Target)
	{
		const FVector TargetLoc = Target->GetActorLocation();
		Focus = FMath::Lerp(Focus, FVector(TargetLoc.X, TargetLoc.Y, Focus.Z), Framing->FocusTowardTarget);
	}
	ActiveBlendOut = Framing->BlendOut;
	bShotActive = true;

	// Trava andar/olhar (pausa continua funcionando). Contadores da engine: o "desfazer" é simétrico.
	PC->SetIgnoreMoveInput(true);
	PC->SetIgnoreLookInput(true);
	LockedController = PC;
	bInputLocked = true;

	const AJRCharacter* Hero = Cast<AJRCharacter>(Pawn);
	bFirstPersonShot = Hero && Hero->IsFirstPersonActive();
	if (bFirstPersonShot)
	{
		// Primeira pessoa: fica no corpo e só vira o olhar suave para o objeto (pegar do chão: para os pés).
		const FVector Eye = Pawn->GetPawnViewLocation();
		const FVector LookPoint = Target ? Target->GetActorLocation()
			: HeroLoc + Facing * 90.f - FVector(0.f, 0.f, HalfHeight);
		FirstPersonLookAt = (LookPoint - Eye).Rotation();
		FirstPersonLookAt.Roll = 0.f;
		SetComponentTickEnabled(true);
	}
	else
	{
		// Não atravessa parede: recua até o que estiver entre o foco e a câmera.
		FCollisionQueryParams Query(SCENE_QUERY_STAT(JRShotCamera), false, Pawn);
		if (Target)
		{
			Query.AddIgnoredActor(Target);
		}
		// [A-073] tenta o lado pedido e o espelhado (Y trocado): fica com o que tem mais espaço livre.
		// Antes a câmera só "recuava" e, encostada numa parede, colava no rosto do herói.
		float BestFree = -1.f;
		FVector CamLoc = Focus;
		for (int32 Side = 0; Side < 2; ++Side)
		{
			FVector Offset = Framing->CameraOffset;
			if (Side == 1)
			{
				Offset.Y = -Offset.Y;
			}
			const FVector Wanted = Focus + Frame.RotateVector(Offset);
			FVector Got = Wanted;
			FHitResult Block;
			if (World->SweepSingleByChannel(Block, Focus, Wanted, FQuat::Identity, ECC_Camera, FCollisionShape::MakeSphere(12.f), Query))
			{
				Got = Block.Location;
			}
			const float Free = static_cast<float>(FVector::Dist(Focus, Got) / FMath::Max(1.0, FVector::Dist(Focus, Wanted)));
			// o lado pedido ganha empates (só troca se o outro estiver claramente mais livre)
			if (Free > BestFree + (Side == 1 ? 0.25f : 0.f))
			{
				BestFree = Free;
				CamLoc = Got;
			}
			if (Side == 0 && Free > 0.95f)
			{
				break;
			}
		}
		FActorSpawnParameters Params;
		Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
		Params.ObjectFlags |= RF_Transient;
		ShotCamera = World->SpawnActor<ACameraActor>(ACameraActor::StaticClass(), FTransform((Focus - CamLoc).Rotation(), CamLoc), Params);
		if (ShotCamera)
		{
			if (UCameraComponent* CamComp = ShotCamera->GetCameraComponent())
			{
				CamComp->SetFieldOfView(Framing->FOV);
				CamComp->SetConstraintAspectRatio(false);
			}
			if (BlendFrom)
			{
				PC->SetViewTarget(BlendFrom); // parte da câmera de onde o jogador estava (ex.: carro)
			}
			PC->SetViewTargetWithBlend(ShotCamera, Framing->BlendIn, VTBlend_EaseInOut, 2.f, false);
		}
	}
	const float Hold = FMath::Max(Framing->BlendIn + 0.1f, ActionSeconds - Framing->BlendOut * 0.5f);
	World->GetTimerManager().SetTimer(HoldTimer, this, &UJRInteractionCameraComponent::FinishHold, Hold, false);
	return true;
}

void UJRInteractionCameraComponent::FinishHold()
{
	StopShot(false);
}

void UJRInteractionCameraComponent::ReleaseInput()
{
	if (!bInputLocked)
	{
		return;
	}
	bInputLocked = false;
	APlayerController* PC = LockedController.Get();
	const AJRCharacter* Hero = Cast<AJRCharacter>(GetOwner());
	// Morto: a morte já travou o olhar; o respawn zera tudo (não destrava aqui).
	if (PC && !(Hero && Hero->GetHealthComponent() && Hero->GetHealthComponent()->IsDead()))
	{
		PC->SetIgnoreMoveInput(false);
		PC->SetIgnoreLookInput(false);
	}
	LockedController.Reset();
}

void UJRInteractionCameraComponent::StopShot(bool bInstant)
{
	UWorld* World = GetWorld();
	if (World)
	{
		World->GetTimerManager().ClearTimer(HoldTimer);
	}
	SetComponentTickEnabled(false);
	APlayerController* PC = LockedController.Get();
	ReleaseInput();
	if (ShotCamera && PC)
	{
		// Volta para o pawn atual do jogador (normalmente o herói).
		if (AActor* Back = PC->GetPawn())
		{
			if (bInstant)
			{
				PC->SetViewTarget(Back);
			}
			else if (PC->GetViewTarget() == ShotCamera.Get())
			{
				PC->SetViewTargetWithBlend(Back, ActiveBlendOut, VTBlend_EaseInOut, 2.f, false);
			}
		}
	}
	if (ShotCamera)
	{
		if (bInstant || !World)
		{
			DestroyShotCamera();
		}
		else
		{
			World->GetTimerManager().SetTimer(CleanupTimer, this, &UJRInteractionCameraComponent::DestroyShotCamera, ActiveBlendOut + 0.2f, false);
		}
	}
	bShotActive = false;
	bFirstPersonShot = false;
}

void UJRInteractionCameraComponent::DestroyShotCamera()
{
	if (ShotCamera)
	{
		ShotCamera->Destroy();
		ShotCamera = nullptr;
	}
}

void UJRInteractionCameraComponent::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
	StopShot(true);
	DestroyShotCamera();
	Super::EndPlay(EndPlayReason);
}

void UJRInteractionCameraComponent::TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction)
{
	Super::TickComponent(DeltaTime, TickType, ThisTickFunction);
	APlayerController* PC = LockedController.Get();
	if (!bFirstPersonShot || !PC)
	{
		SetComponentTickEnabled(false);
		return;
	}
	PC->SetControlRotation(FMath::RInterpTo(PC->GetControlRotation(), FirstPersonLookAt, DeltaTime, FirstPersonLookSpeed));
}

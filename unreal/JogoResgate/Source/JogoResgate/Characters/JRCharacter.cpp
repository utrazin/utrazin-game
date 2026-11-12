// Copyright utrazin. All Rights Reserved.

#include "Characters/JRCharacter.h"
#include "Animation/AnimInstance.h"
#include "Animation/AnimMontage.h"
#include "Camera/CameraComponent.h"
#include "Characters/JRCharacterDefinition.h"
#include "Combat/JRHealthComponent.h"
#include "Combat/JRWeaponComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Core/JRGameMode.h"
#include "EnhancedInputComponent.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/SpringArmComponent.h"
#include "InputActionValue.h"
#include "Interactions/JRInteractionComponent.h"
#include "Materials/MaterialInterface.h"
#include "TimerManager.h"

AJRCharacter::AJRCharacter()
{
	PrimaryActorTick.bCanEverTick = false;

	bUseControllerRotationYaw = false;
	UCharacterMovementComponent* Move = GetCharacterMovement();
	Move->bOrientRotationToMovement = true;
	Move->RotationRate = FRotator(0.f, 540.f, 0.f);
	Move->MaxWalkSpeed = WalkSpeed;
	Move->JumpZVelocity = 450.f;
	// Empurrar objetos físicos de forma plausível (GDD 7).
	Move->bEnablePhysicsInteraction = true;
	Move->PushForceFactor = 300000.f;

	SpringArm = CreateDefaultSubobject<USpringArmComponent>(TEXT("SpringArm"));
	SpringArm->SetupAttachment(RootComponent);
	SpringArm->TargetArmLength = DefaultArmLength;
	SpringArm->SocketOffset = FVector(0.f, 50.f, 60.f);
	SpringArm->bUsePawnControlRotation = true;
	SpringArm->bEnableCameraLag = true;
	SpringArm->CameraLagSpeed = 12.f;

	Camera = CreateDefaultSubobject<UCameraComponent>(TEXT("Camera"));
	Camera->SetupAttachment(SpringArm, USpringArmComponent::SocketName);

	HealthComponent = CreateDefaultSubobject<UJRHealthComponent>(TEXT("HealthComponent"));
	WeaponComponent = CreateDefaultSubobject<UJRWeaponComponent>(TEXT("WeaponComponent"));
	InteractionComponent = CreateDefaultSubobject<UJRInteractionComponent>(TEXT("InteractionComponent"));
}

void AJRCharacter::BeginPlay()
{
	Super::BeginPlay();
	GetCharacterMovement()->MaxWalkSpeed = WalkSpeed;
	HealthComponent->OnDeath.AddDynamic(this, &AJRCharacter::HandleDeath);
}

void AJRCharacter::SetupPlayerInputComponent(UInputComponent* PlayerInputComponent)
{
	Super::SetupPlayerInputComponent(PlayerInputComponent);
	UEnhancedInputComponent* Input = Cast<UEnhancedInputComponent>(PlayerInputComponent);
	if (!Input)
	{
		return;
	}
	if (MoveAction) { Input->BindAction(MoveAction, ETriggerEvent::Triggered, this, &AJRCharacter::HandleMove); }
	if (LookAction) { Input->BindAction(LookAction, ETriggerEvent::Triggered, this, &AJRCharacter::HandleLook); }
	if (JumpAction)
	{
		Input->BindAction(JumpAction, ETriggerEvent::Started, this, &ACharacter::Jump);
		Input->BindAction(JumpAction, ETriggerEvent::Completed, this, &ACharacter::StopJumping);
	}
	if (SprintAction)
	{
		Input->BindAction(SprintAction, ETriggerEvent::Started, this, &AJRCharacter::HandleSprint);
		Input->BindAction(SprintAction, ETriggerEvent::Completed, this, &AJRCharacter::HandleSprint);
	}
	if (AimAction)
	{
		Input->BindAction(AimAction, ETriggerEvent::Started, this, &AJRCharacter::HandleAim);
		Input->BindAction(AimAction, ETriggerEvent::Completed, this, &AJRCharacter::HandleAim);
	}
	if (FireAction)
	{
		Input->BindAction(FireAction, ETriggerEvent::Started, this, &AJRCharacter::HandleFireStarted);
		Input->BindAction(FireAction, ETriggerEvent::Completed, this, &AJRCharacter::HandleFireStopped);
	}
	if (ReloadAction) { Input->BindAction(ReloadAction, ETriggerEvent::Started, this, &AJRCharacter::HandleReload); }
	if (InteractAction) { Input->BindAction(InteractAction, ETriggerEvent::Started, this, &AJRCharacter::HandleInteract); }
}

void AJRCharacter::HandleMove(const FInputActionValue& Value)
{
	const FVector2D Axis = Value.Get<FVector2D>();
	if (!Controller)
	{
		return;
	}
	const FRotator Yaw(0.f, Controller->GetControlRotation().Yaw, 0.f);
	AddMovementInput(FRotationMatrix(Yaw).GetUnitAxis(EAxis::X), Axis.Y);
	AddMovementInput(FRotationMatrix(Yaw).GetUnitAxis(EAxis::Y), Axis.X);
}

void AJRCharacter::HandleLook(const FInputActionValue& Value)
{
	const FVector2D Axis = Value.Get<FVector2D>();
	AddControllerYawInput(Axis.X);
	AddControllerPitchInput(Axis.Y);
}

void AJRCharacter::HandleSprint(const FInputActionValue& Value)
{
	bIsSprinting = Value.Get<bool>();
	GetCharacterMovement()->MaxWalkSpeed = bIsSprinting ? SprintSpeed : WalkSpeed;
}

void AJRCharacter::HandleAim(const FInputActionValue& Value)
{
	const bool bAim = Value.Get<bool>();
	WeaponComponent->SetAiming(bAim);
	SpringArm->TargetArmLength = bAim ? AimArmLength : DefaultArmLength;
	// Mirando, o personagem acompanha a câmera para o tiro sair na direção vista.
	bUseControllerRotationYaw = bAim;
	GetCharacterMovement()->bOrientRotationToMovement = !bAim;
}

void AJRCharacter::HandleFireStarted(const FInputActionValue& Value)
{
	WeaponComponent->StartFire();
}

void AJRCharacter::HandleFireStopped(const FInputActionValue& Value)
{
	WeaponComponent->StopFire();
}

void AJRCharacter::HandleReload(const FInputActionValue& Value)
{
	WeaponComponent->StartReload();
}

void AJRCharacter::HandleInteract(const FInputActionValue& Value)
{
	InteractionComponent->TryInteract();
}

void AJRCharacter::PlayExitVehicleSequence()
{
	UAnimInstance* Anim = GetMesh()->GetAnimInstance();
	if (!ExitVehicleMontage || !Anim)
	{
		return;
	}
	if (AController* C = GetController())
	{
		C->SetIgnoreMoveInput(true);
	}
	Anim->Montage_Play(ExitVehicleMontage);
	FOnMontageEnded EndDelegate;
	EndDelegate.BindUObject(this, &AJRCharacter::HandleMontageEnded);
	Anim->Montage_SetEndDelegate(EndDelegate, ExitVehicleMontage);
}

void AJRCharacter::HandleMontageEnded(UAnimMontage* Montage, bool bInterrupted)
{
	if (AController* C = GetController())
	{
		C->ResetIgnoreMoveInput();
	}
}

float AJRCharacter::PlayRescueHug()
{
	WeaponComponent->CancelAll();
	return RescueHugMontage ? PlayAnimMontage(RescueHugMontage) : 0.f;
}

void AJRCharacter::ApplySkin(const FJRSkinDefinition& Skin)
{
	if (USkeletalMesh* SkinMesh = Skin.Mesh.LoadSynchronous())
	{
		GetMesh()->SetSkeletalMeshAsset(SkinMesh);
	}
	for (int32 Slot = 0; Slot < Skin.MaterialOverrides.Num(); ++Slot)
	{
		if (UMaterialInterface* Material = Skin.MaterialOverrides[Slot].LoadSynchronous())
		{
			GetMesh()->SetMaterial(Slot, Material);
		}
	}
}

void AJRCharacter::HandleDeath(UJRHealthComponent* Health, AActor* Killer)
{
	WeaponComponent->CancelAll();
	if (AController* C = GetController())
	{
		C->SetIgnoreMoveInput(true);
		C->SetIgnoreLookInput(true);
	}
	GetCharacterMovement()->DisableMovement();
	if (DeathMontage)
	{
		PlayAnimMontage(DeathMontage);
	}
	GetWorldTimerManager().SetTimer(FailureTimer, this, &AJRCharacter::NotifyFailure, FailureDelay, false);
}

void AJRCharacter::NotifyFailure()
{
	if (AJRGameMode* GameMode = GetWorld()->GetAuthGameMode<AJRGameMode>())
	{
		GameMode->HandlePlayerFailure(this);
	}
}

void AJRCharacter::ResetForRespawn()
{
	HealthComponent->ResetHealth();
	GetCharacterMovement()->SetMovementMode(MOVE_Walking);
	if (AController* C = GetController())
	{
		C->ResetIgnoreInputFlags();
	}
}

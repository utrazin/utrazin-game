// Copyright utrazin. All Rights Reserved.

#include "Vehicles/JRVehiclePawn.h"
#include "Camera/CameraComponent.h"
#include "ChaosVehicleMovementComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Core/JRGameMode.h"
#include "EnhancedInputComponent.h"
#include "Engine/World.h"
#include "GameFramework/SpringArmComponent.h"
#include "InputActionValue.h"
#include "TimerManager.h"
#include "Vehicles/JRVehicleDamageComponent.h"

AJRVehiclePawn::AJRVehiclePawn()
{
	SpringArm = CreateDefaultSubobject<USpringArmComponent>(TEXT("SpringArm"));
	SpringArm->SetupAttachment(GetMesh());
	// Origem do braço acima do chão: evita a câmera "afundar" quando o traço de colisão nasce no terreno.
	SpringArm->SetRelativeLocation(FVector(0.f, 0.f, 200.f));
	SpringArm->TargetArmLength = 900.f;
	SpringArm->SocketOffset = FVector(0.f, 0.f, 120.f);
	SpringArm->bUsePawnControlRotation = true;
	SpringArm->bEnableCameraLag = true;
	SpringArm->CameraLagSpeed = 8.f;

	Camera = CreateDefaultSubobject<UCameraComponent>(TEXT("Camera"));
	Camera->SetupAttachment(SpringArm, USpringArmComponent::SocketName);

	auto MakeVisual = [this](const TCHAR* Name, FName Socket) -> UStaticMeshComponent*
	{
		UStaticMeshComponent* Comp = CreateDefaultSubobject<UStaticMeshComponent>(Name);
		Comp->SetupAttachment(GetMesh(), Socket);
		Comp->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		Comp->SetCanEverAffectNavigation(false);
		return Comp;
	};
	ChassisMesh = MakeVisual(TEXT("ChassisMesh"), NAME_None);
	TireFL = MakeVisual(TEXT("TireFL"), TEXT("VisWheel_FL"));
	TireFR = MakeVisual(TEXT("TireFR"), TEXT("VisWheel_FR"));
	TireBL = MakeVisual(TEXT("TireBL"), TEXT("VisWheel_BL"));
	TireBR = MakeVisual(TEXT("TireBR"), TEXT("VisWheel_BR"));

	ExitPoint = CreateDefaultSubobject<USceneComponent>(TEXT("ExitPoint"));
	ExitPoint->SetupAttachment(GetMesh());
	ExitPoint->SetRelativeLocation(FVector(0.f, -180.f, 50.f));

	DamageComponent = CreateDefaultSubobject<UJRVehicleDamageComponent>(TEXT("DamageComponent"));

	// Necessário para disparar AJRCheckpoint e outros gatilhos (malha esquelética vem desligada).
	GetMesh()->SetGenerateOverlapEvents(true);
}

void AJRVehiclePawn::BeginPlay()
{
	Super::BeginPlay();
	DamageComponent->OnVehicleDisabled.AddDynamic(this, &AJRVehiclePawn::HandleVehicleDisabled);
}

FTransform AJRVehiclePawn::GetExitTransform() const
{
	return ExitPoint->GetComponentTransform();
}

float AJRVehiclePawn::GetSpeedKmh() const
{
	return GetVehicleMovementComponent() ? GetVehicleMovementComponent()->GetForwardSpeed() * 0.036f : 0.f;
}

void AJRVehiclePawn::SetupPlayerInputComponent(UInputComponent* PlayerInputComponent)
{
	Super::SetupPlayerInputComponent(PlayerInputComponent);
	UEnhancedInputComponent* Input = Cast<UEnhancedInputComponent>(PlayerInputComponent);
	if (!Input)
	{
		return;
	}
	if (ThrottleAction)
	{
		Input->BindAction(ThrottleAction, ETriggerEvent::Triggered, this, &AJRVehiclePawn::HandleThrottle);
		Input->BindAction(ThrottleAction, ETriggerEvent::Completed, this, &AJRVehiclePawn::HandleThrottle);
	}
	if (BrakeAction)
	{
		Input->BindAction(BrakeAction, ETriggerEvent::Triggered, this, &AJRVehiclePawn::HandleBrake);
		Input->BindAction(BrakeAction, ETriggerEvent::Completed, this, &AJRVehiclePawn::HandleBrake);
	}
	if (SteerAction)
	{
		Input->BindAction(SteerAction, ETriggerEvent::Triggered, this, &AJRVehiclePawn::HandleSteer);
		Input->BindAction(SteerAction, ETriggerEvent::Completed, this, &AJRVehiclePawn::HandleSteerReleased);
	}
	if (HandbrakeAction)
	{
		Input->BindAction(HandbrakeAction, ETriggerEvent::Started, this, &AJRVehiclePawn::HandleHandbrake);
		Input->BindAction(HandbrakeAction, ETriggerEvent::Completed, this, &AJRVehiclePawn::HandleHandbrake);
	}
	if (LookAction)
	{
		Input->BindAction(LookAction, ETriggerEvent::Triggered, this, &AJRVehiclePawn::HandleLook);
	}
	if (MouseLookAction)
	{
		Input->BindAction(MouseLookAction, ETriggerEvent::Triggered, this, &AJRVehiclePawn::HandleLook);
	}
}

void AJRVehiclePawn::HandleThrottle(const FInputActionValue& Value)
{
	if (bDriveEnabled)
	{
		GetVehicleMovementComponent()->SetThrottleInput(Value.Get<float>());
	}
}

void AJRVehiclePawn::HandleBrake(const FInputActionValue& Value)
{
	if (bDriveEnabled)
	{
		GetVehicleMovementComponent()->SetBrakeInput(Value.Get<float>());
	}
}

void AJRVehiclePawn::HandleSteer(const FInputActionValue& Value)
{
	if (bDriveEnabled)
	{
		const float Steering = FMath::Clamp(Value.Get<float>() + DamageComponent->GetSteeringBias(), -1.f, 1.f);
		GetVehicleMovementComponent()->SetSteeringInput(Steering);
	}
}

void AJRVehiclePawn::HandleSteerReleased(const FInputActionValue& Value)
{
	if (bDriveEnabled)
	{
		// Sem input o pneu furado continua puxando para o lado.
		GetVehicleMovementComponent()->SetSteeringInput(DamageComponent->GetSteeringBias());
	}
}

void AJRVehiclePawn::HandleHandbrake(const FInputActionValue& Value)
{
	if (bDriveEnabled)
	{
		GetVehicleMovementComponent()->SetHandbrakeInput(Value.Get<bool>());
	}
}

void AJRVehiclePawn::HandleLook(const FInputActionValue& Value)
{
	const FVector2D Look = Value.Get<FVector2D>();
	AddControllerYawInput(Look.X);
	AddControllerPitchInput(Look.Y);
}

void AJRVehiclePawn::ZeroInputs(bool bApplyHandbrake)
{
	if (UChaosVehicleMovementComponent* Movement = GetVehicleMovementComponent())
	{
		Movement->SetThrottleInput(0.f);
		Movement->SetSteeringInput(0.f);
		Movement->SetBrakeInput(bApplyHandbrake ? 1.f : 0.f);
		Movement->SetHandbrakeInput(bApplyHandbrake);
	}
}

void AJRVehiclePawn::UnPossessed()
{
	// Requisito de teste: o veículo não continua acelerando quando o controle muda.
	ZeroInputs(true);
	Super::UnPossessed();
}

void AJRVehiclePawn::ParkAndDisable()
{
	bDriveEnabled = false;
	ZeroInputs(true);
	GetWorldTimerManager().SetTimer(SleepTimer, this, &AJRVehiclePawn::SleepPhysics, SleepDelayAfterPark, false);
}

void AJRVehiclePawn::SleepPhysics()
{
	GetMesh()->PutAllRigidBodiesToSleep();
}

void AJRVehiclePawn::HandleVehicleDisabled()
{
	bDriveEnabled = false;
	ZeroInputs(true);
	if (IsPlayerControlled())
	{
		if (AJRGameMode* GameMode = GetWorld()->GetAuthGameMode<AJRGameMode>())
		{
			GameMode->HandlePlayerFailure(this);
		}
	}
}

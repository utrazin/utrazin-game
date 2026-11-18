// Copyright utrazin. All Rights Reserved.

#include "Vehicles/JRVehiclePawn.h"
#include "AI/JREnemyCharacter.h"
#include "Animation/AnimSequenceBase.h"
#include "Camera/CameraComponent.h"
#include "Camera/CameraTypes.h"
#include "ChaosVehicleMovementComponent.h"
#include "Characters/JRCharacter.h"
#include "Characters/JRCharacterDefinition.h"
#include "FX/JRGameFeel.h" // [A-073]
#include "CollisionQueryParams.h"
#include "Components/PointLightComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Core/JRGameMode.h"
#include "Core/JRPlayerController.h"
#include "EnhancedInputComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "JogoResgate.h"
#include "Materials/MaterialInterface.h"
#include "PhysicalMaterials/PhysicalMaterial.h"
#include "GameFramework/SpringArmComponent.h"
#include "InputActionValue.h"
#include "InputCoreTypes.h"
#include "Kismet/GameplayStatics.h"
#include "Levels/JRObjectiveSubsystem.h"
#include "NiagaraComponent.h"
#include "NiagaraFunctionLibrary.h"
#include "NiagaraSystem.h"
#include "TimerManager.h"
#include "UI/JRHUD.h"
#include "Vehicles/JRVehicleDamageComponent.h"

AJRVehiclePawn::AJRVehiclePawn()
{
	// Tick só para a ajuda de aderência (física precisa de força a cada frame).
	PrimaryActorTick.bCanEverTick = true;

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

	// Volante separado, preso à carroceria. Posição em cm no espaço da malha SM_Car_AlienBuggy
	// (tools/blender/make_car_buggy.py: WHEEL_C = 0,08 / 0 / 1,165 m); a escala do chassi vale para ele.
	SteeringWheelMesh = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("SteeringWheelMesh"));
	SteeringWheelMesh->SetupAttachment(ChassisMesh);
	SteeringWheelMesh->SetRelativeLocation(FVector(8.f, 0.f, 116.5f));
	SteeringWheelMesh->SetRelativeRotation(SteeringWheelBaseRotation);
	SteeringWheelMesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	SteeringWheelMesh->SetCanEverAffectNavigation(false);

	ExitPoint = CreateDefaultSubobject<USceneComponent>(TEXT("ExitPoint"));
	ExitPoint->SetupAttachment(GetMesh());
	ExitPoint->SetRelativeLocation(FVector(0.f, -320.f, 120.f)); // longe o bastante do Offroad (largo)

	SeatPoint = CreateDefaultSubobject<USceneComponent>(TEXT("SeatPoint"));
	SeatPoint->SetupAttachment(GetMesh());
	SeatPoint->SetRelativeLocation(FVector(-25.5f, 0.f, 64.5f)); // banco central do buggy (assento x 0,849)

	// Motorista só visual, no banco central do buggy. DriverPivot = quadril (cm no espaço da malha do buggy):
	// assento em z 76, quadril 12 acima; 7,6 para a esquerda centraliza as mãos no volante.
	DriverPivot = CreateDefaultSubobject<USceneComponent>(TEXT("DriverPivot"));
	DriverPivot->SetupAttachment(ChassisMesh);
	DriverPivot->SetRelativeLocation(FVector(-30.f, -7.6f, 88.f));

	// Na pose "Driving" o quadril fica ~62,6 cm acima dos pés (herói de ~1,7 m) = 73,8 na escala do chassi (0,849).
	// Escala de mundo 1 (igual ao herói a pé). Herói UE5 olha para +Y, por isso yaw -90.
	DriverMesh = CreateDefaultSubobject<USkeletalMeshComponent>(TEXT("DriverMesh"));
	DriverMesh->SetupAttachment(DriverPivot);
	DriverMesh->SetRelativeLocation(FVector(0.f, 0.f, -73.8f));
	DriverMesh->SetRelativeRotation(FRotator(0.f, -90.f, 0.f));
	DriverMesh->SetUsingAbsoluteScale(true);
	DriverMesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	DriverMesh->SetGenerateOverlapEvents(false);
	DriverMesh->SetCanEverAffectNavigation(false);
	DriverMesh->SetHiddenInGame(true);

	// [A-075] Carona: sentada na caixa de munição à direita do banco central (no Blender a caixa fica em y -0,59 m;
	// o FBX inverte o Y). Topo da caixa em z 92; quadril um pouco acima. Escondida até a sobrevivente embarcar.
	PassengerPivot = CreateDefaultSubobject<USceneComponent>(TEXT("PassengerPivot"));
	PassengerPivot->SetupAttachment(ChassisMesh);
	PassengerPivot->SetRelativeLocation(FVector(-42.f, 59.f, 102.f));
	PassengerMesh = CreateDefaultSubobject<USkeletalMeshComponent>(TEXT("PassengerMesh"));
	PassengerMesh->SetupAttachment(PassengerPivot);
	PassengerMesh->SetRelativeLocation(FVector(0.f, 0.f, -73.8f));
	PassengerMesh->SetRelativeRotation(FRotator(0.f, -90.f, 0.f));
	PassengerMesh->SetUsingAbsoluteScale(true);
	PassengerMesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	PassengerMesh->SetGenerateOverlapEvents(false);
	PassengerMesh->SetCanEverAffectNavigation(false);
	PassengerMesh->SetHiddenInGame(true);

	DamageComponent = CreateDefaultSubobject<UJRVehicleDamageComponent>(TEXT("DamageComponent"));

	// Pontos de agarre dos zumbis (presos ao chassi). Valores iniciais; o BeginPlay recalcula pela malha.
	// O eixo X de cada ponto aponta para dentro do carro (o zumbi olha para a cabine).
	auto MakeGrabPoint = [this](const TCHAR* Name, const FVector& Location, float Yaw) -> USceneComponent*
	{
		USceneComponent* Point = CreateDefaultSubobject<USceneComponent>(Name);
		Point->SetupAttachment(ChassisMesh);
		Point->SetRelativeLocationAndRotation(Location, FRotator(0.f, Yaw, 0.f));
		return Point;
	};
	GrabPointHood = MakeGrabPoint(TEXT("GrabPointHood"), FVector(170.f, 0.f, 150.f), 180.f);
	GrabPointLeft = MakeGrabPoint(TEXT("GrabPointLeft"), FVector(-20.f, -150.f, 110.f), 90.f);
	GrabPointRight = MakeGrabPoint(TEXT("GrabPointRight"), FVector(-20.f, 150.f, 110.f), -90.f);

	// Fumaça e fogo do motor (desligados até a integridade cair).
	SmokeFX = CreateDefaultSubobject<UNiagaraComponent>(TEXT("SmokeFX"));
	SmokeFX->SetupAttachment(ChassisMesh);
	SmokeFX->SetRelativeLocation(FVector(160.f, 0.f, 110.f));
	SmokeFX->SetAutoActivate(false);
	FireFX = CreateDefaultSubobject<UNiagaraComponent>(TEXT("FireFX"));
	FireFX->SetupAttachment(ChassisMesh);
	FireFX->SetRelativeLocation(FVector(160.f, 0.f, 100.f));
	FireFX->SetAutoActivate(false);
	FireLight = CreateDefaultSubobject<UPointLightComponent>(TEXT("FireLight"));
	FireLight->SetupAttachment(ChassisMesh);
	FireLight->SetRelativeLocation(FVector(160.f, 0.f, 140.f));
	FireLight->SetLightColor(FLinearColor(1.f, 0.45f, 0.1f));
	FireLight->SetIntensity(8000.f);
	FireLight->SetAttenuationRadius(600.f);
	FireLight->SetCastShadows(false);
	FireLight->SetVisibility(false);

	// Necessário para disparar AJRCheckpoint e outros gatilhos (malha esquelética vem desligada).
	GetMesh()->SetGenerateOverlapEvents(true);
}

void AJRVehiclePawn::BeginPlay()
{
	Super::BeginPlay();
	DamageComponent->OnVehicleDisabled.AddDynamic(this, &AJRVehiclePawn::HandleVehicleDisabled);
	DamageComponent->OnIntegrityChanged.AddDynamic(this, &AJRVehiclePawn::HandleIntegrityChanged);
	PlaceBodyPointsFromChassis();
	if (SmokeSystem)
	{
		SmokeFX->SetAsset(SmokeSystem);
	}
	if (FireSystem)
	{
		FireFX->SetAsset(FireSystem);
	}
	NitroCharge = StartingNitro;
	// [A-075] Começa na reserva (o checkpoint do posto zera com o item Fuel pendente).
	if (PendingRequiredItem.IsNone())
	{
		FuelLevel = FMath::Clamp(StartingFuel, FuelLimpLevel, 1.f);
	}
	PassengerMesh->SetRelativeLocation(FVector(0.f, 0.f, -PassengerHipsHeight));
	GetWorldTimerManager().SetTimer(NitroTimer, this, &AJRVehiclePawn::TickNitro, 0.05f, true);

	// Só o corpo físico do esqueleto colide. Carroceria e pneus são enfeite (evita "agarrar" em rampas e paredes).
	UStaticMeshComponent* Visuals[] = { ChassisMesh, TireFL, TireFR, TireBL, TireBR, SteeringWheelMesh };
	for (UStaticMeshComponent* Visual : Visuals)
	{
		if (Visual)
		{
			Visual->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		}
	}
	// CCD: em alta velocidade (nitro) o chassi não atravessa rampas e paredes finas.
	GetMesh()->SetUseCCD(true);
	GetMesh()->SetAngularDamping(ChassisAngularDamping);
	// Atrito baixo na carroceria: raspa nas paredes em vez de grudar.
	if (ChassisPhysMaterial)
	{
		GetMesh()->SetPhysMaterialOverride(ChassisPhysMaterial);
	}
	GetMesh()->SetNotifyRigidBodyCollision(true);
	OnActorHit.AddDynamic(this, &AJRVehiclePawn::HandleVehicleHit);
	if (IsPlayerControlled())
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

void AJRVehiclePawn::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	if (bRecovering)
	{
		// Desvirando: nenhuma ajuda de física briga com o movimento suave.
		TickRecover(DeltaSeconds);
		UpdateSteeringVisuals(DeltaSeconds);
		return;
	}
	// Ajudas de direção só com o jogador dirigindo (carro estacionado fica com a física pura).
	const bool bAssists = bDriveEnabled && !bExploded && IsPlayerControlled() && GetMesh()->IsSimulatingPhysics();
	const bool bGrounded = bAssists && IsNearGround();
	if (bAssists)
	{
		ApplyGripAssist(DeltaSeconds, bGrounded);
		ApplyBrakeAssist(bGrounded);
		ApplyRollStabilization(bGrounded);
		TickAutoRecover(DeltaSeconds);
		TickFuel(DeltaSeconds); // [A-075]
	}
	if (bNitroActive && BrakeInputValue < 0.1f)
	{
		// Empurrão para frente a cada frame (independente da massa). Nunca junto com o freio.
		GetMesh()->AddForce(GetActorForwardVector() * NitroAcceleration, NAME_None, true);
	}
	UpdateSteeringVisuals(DeltaSeconds);
	TickGrabbers(DeltaSeconds);
}

void AJRVehiclePawn::PlaceBodyPointsFromChassis()
{
	const UStaticMesh* ChassisAsset = ChassisMesh ? ChassisMesh->GetStaticMesh() : nullptr;
	if (!ChassisAsset)
	{
		return; // sem malha: ficam os valores do BP
	}
	// Caixa da carroceria no espaço do carro (usada para distância/contato dos zumbis).
	const FTransform ChassisToActor = ChassisMesh->GetComponentTransform().GetRelativeTransform(GetActorTransform());
	const FBoxSphereBounds ActorSpace = ChassisMesh->CalcBounds(ChassisToActor);
	BodyCenter = ActorSpace.Origin;
	BodyHalfExtent = ActorSpace.BoxExtent;
	if (!bAutoPlaceGrabPoints)
	{
		return;
	}
	// Pontos no espaço da malha do chassi (a escala do chassi vale para eles).
	const FBox Box = ChassisAsset->GetBoundingBox();
	const FVector Center = Box.GetCenter();
	const float Scale = FMath::Max(static_cast<float>(ChassisMesh->GetComponentScale().Z), 0.01f);
	const float HalfCapsule = 88.f / Scale; // a origem do zumbi é o meio da cápsula
	const double HoodX = FMath::Lerp(Center.X, Box.Max.X, 0.55);
	const double HoodTopZ = FMath::Lerp(Box.Min.Z, Box.Max.Z, 0.45);
	GrabPointHood->SetRelativeLocation(FVector(HoodX, Center.Y, HoodTopZ + HalfCapsule * 0.55f));
	const double SideX = Center.X - (Box.Max.X - Box.Min.X) * 0.1;
	const double SideZ = Box.Min.Z + HalfCapsule + 20.f / Scale;
	GrabPointLeft->SetRelativeLocation(FVector(SideX, Box.Min.Y - 20.f / Scale, SideZ));
	GrabPointRight->SetRelativeLocation(FVector(SideX, Box.Max.Y + 20.f / Scale, SideZ));
	const FVector EnginePoint(HoodX, Center.Y, HoodTopZ);
	SmokeFX->SetRelativeLocation(EnginePoint);
	FireFX->SetRelativeLocation(EnginePoint);
	FireLight->SetRelativeLocation(EnginePoint + FVector(0.f, 0.f, 40.f / Scale));
}

float AJRVehiclePawn::GetDistanceToBody(const FVector& WorldPoint, FVector* OutClosestPoint) const
{
	const FTransform& ActorTransform = GetActorTransform();
	const FVector Local = ActorTransform.InverseTransformPosition(WorldPoint) - BodyCenter;
	const FVector Clamped(
		FMath::Clamp(Local.X, -BodyHalfExtent.X, BodyHalfExtent.X),
		FMath::Clamp(Local.Y, -BodyHalfExtent.Y, BodyHalfExtent.Y),
		FMath::Clamp(Local.Z, -BodyHalfExtent.Z, BodyHalfExtent.Z));
	if (OutClosestPoint)
	{
		*OutClosestPoint = ActorTransform.TransformPosition(Clamped + BodyCenter);
	}
	return static_cast<float>(FVector::Dist(Local, Clamped));
}

USceneComponent* AJRVehiclePawn::GetGrabPoint(int32 Slot) const
{
	switch (Slot)
	{
	case 0: return GrabPointHood;
	case 1: return GrabPointLeft;
	case 2: return GrabPointRight;
	default: return nullptr;
	}
}

EJRVehicleZone AJRVehiclePawn::GetGrabZone(int32 Slot) const
{
	switch (Slot)
	{
	case 1: return EJRVehicleZone::Left;
	case 2: return EJRVehicleZone::Right;
	default: return EJRVehicleZone::Front;
	}
}

int32 AJRVehiclePawn::GetGrabberCount() const
{
	int32 Count = 0;
	for (const TWeakObjectPtr<AJREnemyCharacter>& Grabber : Grabbers)
	{
		Count += Grabber.IsValid() ? 1 : 0;
	}
	return Count;
}

int32 AJRVehiclePawn::TryReserveGrabSlot(AJREnemyCharacter* Zombie)
{
	if (!Zombie || bExploded || FMath::Abs(GetSpeedKmh()) > GrabMaxSpeedKmh)
	{
		return INDEX_NONE;
	}
	// Só pela frente e pelos lados: atrás do carro não há onde se segurar.
	const FVector ZombieLocal = GetActorTransform().InverseTransformPosition(Zombie->GetActorLocation()) - BodyCenter;
	if (ZombieLocal.X < -BodyHalfExtent.X * 0.6)
	{
		return INDEX_NONE;
	}
	int32 Best = INDEX_NONE;
	double BestDistSq = FMath::Square(450.0); // não "teletransporta" o zumbi para o outro lado do carro
	for (int32 Slot = 0; Slot < NumGrabSlots; ++Slot)
	{
		if (Grabbers[Slot].IsValid() && !Grabbers[Slot]->IsDead())
		{
			continue;
		}
		const USceneComponent* Point = GetGrabPoint(Slot);
		const double DistSq = Point ? FVector::DistSquared(Point->GetComponentLocation(), Zombie->GetActorLocation()) : TNumericLimits<double>::Max();
		if (DistSq < BestDistSq)
		{
			BestDistSq = DistSq;
			Best = Slot;
		}
	}
	if (Best != INDEX_NONE)
	{
		Grabbers[Best] = Zombie;
		GrabStartTime[Best] = GetWorld()->GetTimeSeconds();
		if (IsPlayerControlled() && GetGrabberCount() == 1)
		{
			AJRHUD::Toast(this, TEXT("Zumbi no carro! Vire forte ou freie para derrubar."), FLinearColor(1.f, 0.7f, 0.2f));
		}
	}
	return Best;
}

void AJRVehiclePawn::ReleaseGrabSlot(AJREnemyCharacter* Zombie)
{
	for (TWeakObjectPtr<AJREnemyCharacter>& Grabber : Grabbers)
	{
		if (Grabber.Get() == Zombie)
		{
			Grabber.Reset();
		}
	}
}

void AJRVehiclePawn::ReleaseAllGrabbers(bool bKill)
{
	// Cópia: cada zumbi libera o próprio ponto durante o laço.
	TArray<AJREnemyCharacter*> Current;
	for (const TWeakObjectPtr<AJREnemyCharacter>& Grabber : Grabbers)
	{
		if (AJREnemyCharacter* Zombie = Grabber.Get())
		{
			Current.Add(Zombie);
		}
	}
	const FVector CarVelocity = GetVelocity();
	for (AJREnemyCharacter* Zombie : Current)
	{
		const FVector Out = (Zombie->GetActorLocation() - GetActorLocation()).GetSafeNormal2D();
		const FVector Launch = CarVelocity * 0.8f + Out * 700.f + FVector(0.f, 0.f, 400.f);
		Zombie->ReleaseFromVehicle(bKill, Launch);
	}
	for (TWeakObjectPtr<AJREnemyCharacter>& Grabber : Grabbers)
	{
		Grabber.Reset();
	}
}

void AJRVehiclePawn::TickGrabbers(float DeltaSeconds)
{
	if (!GetMesh()->IsSimulatingPhysics())
	{
		return;
	}
	const FVector Velocity = GetMesh()->GetPhysicsLinearVelocity();
	// Desaceleração para frente (suavizada: a física oscila de um frame para o outro).
	const float ForwardSpeed = static_cast<float>(FVector::DotProduct(Velocity, GetActorForwardVector()));
	const float RawDecel = DeltaSeconds > KINDA_SMALL_NUMBER ? (FMath::Abs(PrevForwardSpeed) - FMath::Abs(ForwardSpeed)) / DeltaSeconds : 0.f;
	FilteredBrakeDecel = FMath::Lerp(FilteredBrakeDecel, RawDecel, 0.5f);
	PrevForwardSpeed = ForwardSpeed;

	const int32 Count = GetGrabberCount();
	if (Count == 0)
	{
		if (bGrabSteerApplied)
		{
			// O último caiu: volante volta ao normal sem esperar o próximo input.
			bGrabSteerApplied = false;
			if (bDriveEnabled)
			{
				GetVehicleMovementComponent()->SetSteeringInput(ComputeSteering(LastSteerInput));
			}
		}
		return;
	}
	const float Kmh = static_cast<float>(Velocity.Size()) * 0.036f;
	const float YawRate = FMath::DegreesToRadians(FMath::Abs(static_cast<float>(GetMesh()->GetPhysicsAngularVelocityInDegrees().Z)));
	const float LateralAccel = YawRate * static_cast<float>(Velocity.Size2D());
	const bool bHardBrake = FilteredBrakeDecel > ShakeOffBrakeDecel && Kmh > 8.f;
	const double Now = GetWorld()->GetTimeSeconds();
	if (Kmh > ShakeOffSpeedKmh || LateralAccel > ShakeOffLateralAccel || bHardBrake)
	{
		// Só cai quem já está agarrado há um tempinho.
		TArray<AJREnemyCharacter*> Shaken;
		for (int32 Slot = 0; Slot < NumGrabSlots; ++Slot)
		{
			if (Grabbers[Slot].IsValid() && Now - GrabStartTime[Slot] >= ShakeOffGraceTime)
			{
				Shaken.Add(Grabbers[Slot].Get());
			}
		}
		for (AJREnemyCharacter* Zombie : Shaken)
		{
			const FVector Out = (Zombie->GetActorLocation() - GetActorLocation()).GetSafeNormal2D();
			// Freada: o zumbi do capô voa para frente (inércia); curva: voa para fora.
			const FVector Inertia = bHardBrake ? GetActorForwardVector() * 500.f : FVector::ZeroVector;
			Zombie->ReleaseFromVehicle(true, Velocity * 0.8f + Out * 700.f + Inertia + FVector(0.f, 0.f, 400.f));
		}
		if (Shaken.Num() > 0)
		{
			UE_LOG(LogJR, Log, TEXT("%s: %d zumbi(s) sacudido(s) (%.0f km/h, lateral %.0f, freada %.0f)"), *GetName(), Shaken.Num(),
				Kmh, LateralAccel, FilteredBrakeDecel);
		}
		return;
	}
	// O peso dos zumbis segura o carro (só andando).
	if (Kmh > 5.f)
	{
		const FVector Back = -Velocity.GetSafeNormal2D();
		GetMesh()->AddForce(Back * (GrabberDeceleration * Count), NAME_None, true);
	}
	// E puxam o volante (o jogador sente o carro "torto").
	if (bDriveEnabled && IsPlayerControlled())
	{
		GetVehicleMovementComponent()->SetSteeringInput(ComputeSteering(LastSteerInput));
		bGrabSteerApplied = true;
	}
}

float AJRVehiclePawn::GetGrabSteerBias() const
{
	float Bias = 0.f;
	if (Grabbers[1].IsValid())
	{
		Bias -= GrabberSteerPull; // esquerda puxa para a esquerda
	}
	if (Grabbers[2].IsValid())
	{
		Bias += GrabberSteerPull;
	}
	if (Grabbers[0].IsValid())
	{
		// No capô: balança de um lado para o outro.
		const UWorld* World = GetWorld();
		const float Time = World ? static_cast<float>(World->GetTimeSeconds()) : 0.f;
		Bias += FMath::Sin(Time * 2.3f) * GrabberSteerPull * 0.6f;
	}
	return Bias;
}

float AJRVehiclePawn::ComputeSteering(float RawInput) const
{
	// Menos volante em alta velocidade: toque no teclado não vira pião.
	const float Speed = FMath::Abs(GetSpeedKmh());
	const float Alpha = FMath::Clamp((Speed - SteerFullUntilKmh) / FMath::Max(SteerMinAtKmh - SteerFullUntilKmh, 1.f), 0.f, 1.f);
	const float SteerScale = FMath::Lerp(1.f, SteerAtHighSpeed, Alpha);
	return FMath::Clamp(RawInput * SteerScale + DamageComponent->GetSteeringBias() + GetGrabSteerBias(), -1.f, 1.f);
}

void AJRVehiclePawn::NotifyZombieCarEvent(EJRZombieCarEvent Event, AActor* Zombie, FVector Location, float Value)
{
	OnZombieCarEvent.Broadcast(Event, Zombie, Location, Value);
	BP_OnZombieCarEvent(Event, Zombie, Location, Value);
}

bool AJRVehiclePawn::IsCarBombArmed() const
{
	return GetWorldTimerManager().IsTimerActive(CarBombTimer);
}

void AJRVehiclePawn::ApplyZombieDrag(float Fraction)
{
	const double Now = GetWorld()->GetTimeSeconds();
	ZombieDragUsed = FMath::Max(0.f, ZombieDragUsed - static_cast<float>(Now - LastZombieDragTime) * ZombieDragRecoveryPerSecond);
	LastZombieDragTime = Now;
	const float Allowed = FMath::Clamp(FMath::Min(Fraction, ZombieDragMaxBurst - ZombieDragUsed), 0.f, 1.f);
	if (Allowed <= 0.f || FMath::Abs(GetSpeedKmh()) < ZombieDragMinSpeedKmh || !GetMesh()->IsSimulatingPhysics())
	{
		return;
	}
	ZombieDragUsed += Allowed;
	GetMesh()->SetPhysicsLinearVelocity(GetMesh()->GetPhysicsLinearVelocity() * (1.f - Allowed));
}

void AJRVehiclePawn::HandleIntegrityChanged(float Integrity)
{
	const bool bWantSmoke = Integrity < SmokeBelowIntegrity;
	const bool bWantFire = Integrity < FireBelowIntegrity || bExploded;
	if (!bLoggedMissingFX && (bWantSmoke || bWantFire) && (!SmokeSystem || !FireSystem))
	{
		bLoggedMissingFX = true;
		UE_LOG(LogJR, Warning, TEXT("%s: sem SmokeSystem/FireSystem (Niagara) no BP; só a luz do fogo aparece. Rode tools/unreal/setup_car_zombies.py."), *GetName());
	}
	if (bWantSmoke != bSmokeOn)
	{
		bSmokeOn = bWantSmoke;
		if (bSmokeOn)
		{
			SmokeFX->Activate(true);
			if (IsPlayerControlled())
			{
				AJRHUD::Toast(this, TEXT("O carro está soltando fumaça!"), FLinearColor(1.f, 0.8f, 0.2f));
			}
		}
		else
		{
			SmokeFX->Deactivate();
		}
	}
	const EJRVehicleDamageFXState NewState = bExploded ? EJRVehicleDamageFXState::Wrecked
		: bWantFire ? EJRVehicleDamageFXState::Burning
		: bWantSmoke ? EJRVehicleDamageFXState::Smoking
		: EJRVehicleDamageFXState::Intact;
	if (NewState != DamageFXState)
	{
		DamageFXState = NewState;
		UE_LOG(LogJR, Log, TEXT("%s: estado de dano %s (integridade %.0f%%)"), *GetName(), *UEnum::GetValueAsString(NewState), Integrity * 100.f);
		OnDamageStateChanged(NewState);
		OnDamageFXStateChanged.Broadcast(NewState);
	}
	if (bWantFire != bFireOn)
	{
		bFireOn = bWantFire;
		FireLight->SetVisibility(bFireOn);
		if (bFireOn && !bExploded && BurnEngineDamagePerSecond > 0.f)
		{
			GetWorldTimerManager().SetTimer(BurnTimer, this, &AJRVehiclePawn::TickBurn, 1.f, true);
		}
		else
		{
			GetWorldTimerManager().ClearTimer(BurnTimer);
		}
		if (bFireOn)
		{
			FireFX->Activate(true);
			if (IsPlayerControlled() && !bExploded)
			{
				AJRHUD::Toast(this, TEXT("O carro pegou fogo! Vai explodir!"), FLinearColor(1.f, 0.3f, 0.1f));
			}
		}
		else
		{
			FireFX->Deactivate();
		}
	}
}

void AJRVehiclePawn::Explode()
{
	if (bExploded)
	{
		return;
	}
	bExploded = true;
	bDriveEnabled = false;
	GetWorldTimerManager().ClearTimer(CarBombTimer);
	GetWorldTimerManager().ClearTimer(BurnTimer);
	ZeroInputs(true);
	const FVector Origin = GetActorLocation();
	UE_LOG(LogJR, Log, TEXT("%s explodiu"), *GetName());
	NotifyZombieCarEvent(EJRZombieCarEvent::Explosion, nullptr, Origin, ExplosionRadius);

	// Quem estava agarrado voa junto.
	ReleaseAllGrabbers(true);

	if (ExplosionSystem)
	{
		UNiagaraFunctionLibrary::SpawnSystemAtLocation(this, ExplosionSystem, Origin);
	}
	if (ExplosionSound)
	{
		UGameplayStatics::PlaySoundAtLocation(this, ExplosionSound, Origin);
	}
	// Clarão (funciona mesmo sem partícula) e o carro fica queimando.
	FireLight->SetVisibility(true);
	FireLight->SetIntensity(400000.f);
	FireLight->SetAttenuationRadius(ExplosionRadius * 2.f);
	GetWorldTimerManager().SetTimer(ExplosionFlashTimer, this, &AJRVehiclePawn::EndExplosionFlash, 0.25f, false);
	HandleIntegrityChanged(0.f);
	// Empurrão do próprio carro (pula um pouco com a explosão).
	if (GetMesh()->IsSimulatingPhysics())
	{
		GetMesh()->WakeAllRigidBodies();
		GetMesh()->AddImpulse(FVector(0.f, 0.f, 450.f), NAME_None, true);
	}

	// "Bomba": zumbis no raio morrem arremessados (mais forte perto do centro).
	AController* InstigatorController = GetController();
	for (TActorIterator<AJREnemyCharacter> It(GetWorld()); It; ++It)
	{
		AJREnemyCharacter* Enemy = *It;
		if (!Enemy || Enemy->IsDead())
		{
			continue;
		}
		const FVector Offset = Enemy->GetActorLocation() - Origin;
		const float Dist = static_cast<float>(Offset.Size());
		if (Dist > ExplosionRadius)
		{
			continue;
		}
		const float Alpha = 1.f - Dist / FMath::Max(ExplosionRadius, 1.f);
		const FVector Launch = Offset.GetSafeNormal2D() * (ExplosionLaunchSpeed * (0.4f + 0.6f * Alpha))
			+ FVector(0.f, 0.f, ExplosionLaunchSpeed * (0.3f + 0.4f * Alpha));
		Enemy->KillWithLaunch(Launch, InstigatorController, this);
	}
	// Barris, caixas e outros alvos com dano.
	TArray<AActor*> Ignore;
	Ignore.Add(this);
	UGameplayStatics::ApplyRadialDamageWithFalloff(this, ExplosionDamage, ExplosionDamage * 0.1f, Origin,
		ExplosionRadius * 0.4f, ExplosionRadius, 1.f, nullptr, Ignore, this, InstigatorController);

	if (!IsPlayerControlled())
	{
		return;
	}
	const UJRObjectiveSubsystem* Objective = GetWorld()->GetSubsystem<UJRObjectiveSubsystem>();
	const bool bDrivingStage = Objective && Objective->GetStage() == EJRLevelStage::Driving;
	AJRPlayerController* PC = Cast<AJRPlayerController>(GetController());
	if (PC && (!bDrivingStage || bEjectOnExplodeWhileDriving))
	{
		AJRHUD::Toast(this, TEXT("O carro explodiu! Continue a pé."), FLinearColor(1.f, 0.4f, 0.1f));
		PC->RequestExitVehicle(GetExitTransform());
	}
	else if (AJRGameMode* GameMode = GetWorld()->GetAuthGameMode<AJRGameMode>())
	{
		AJRHUD::Toast(this, TEXT("O carro explodiu!"), FLinearColor(1.f, 0.3f, 0.1f));
		GameMode->HandlePlayerFailure(this);
	}
}

void AJRVehiclePawn::TickBurn()
{
	if (bExploded || !bFireOn)
	{
		GetWorldTimerManager().ClearTimer(BurnTimer);
		return;
	}
	DamageComponent->ApplyZoneDamage(EJRVehicleZone::Engine, BurnEngineDamagePerSecond);
}

void AJRVehiclePawn::EndExplosionFlash()
{
	FireLight->SetIntensity(8000.f);
	FireLight->SetAttenuationRadius(600.f);
}

void AJRVehiclePawn::UpdateSteeringVisuals(float DeltaSeconds)
{
	const float Target = bDriveEnabled ? LastSteerInput : 0.f;
	VisualSteer = FMath::FInterpTo(VisualSteer, Target, DeltaSeconds, SteerVisualSpeed);
	// Roll gira em volta do eixo local X do volante (aplicado antes da inclinação da coluna).
	SteeringWheelMesh->SetRelativeRotation(FRotator(SteeringWheelBaseRotation.Pitch, SteeringWheelBaseRotation.Yaw,
		SteeringWheelBaseRotation.Roll + VisualSteer * SteeringWheelMaxDegrees));
	// Motorista inclina e vira o tronco para dentro da curva (gira no quadril).
	DriverPivot->SetRelativeRotation(FRotator(0.f, VisualSteer * DriverYawDegrees, VisualSteer * DriverLeanDegrees));
}

void AJRVehiclePawn::HandleVehicleHit(AActor* SelfActor, AActor* OtherActor, FVector NormalImpulse, const FHitResult& Hit)
{
	// Batida forte em algo (não zumbi) derruba quem está agarrado.
	if (GetGrabberCount() > 0 && !(OtherActor && OtherActor->IsA<APawn>()) && NormalImpulse.Size() > ShakeOffImpactImpulse)
	{
		ReleaseAllGrabbers(true);
	}
	if (!bWallScrapeEnabled || !bDriveEnabled || !GetMesh()->IsSimulatingPhysics())
	{
		return;
	}
	// Zumbis e objetos soltos (barris, caixas) seguem a física normal.
	if (OtherActor && OtherActor->IsA<APawn>())
	{
		return;
	}
	const UPrimitiveComponent* OtherComp = Hit.GetComponent();
	if (OtherComp && OtherComp->IsSimulatingPhysics())
	{
		return;
	}
	FVector WallNormal = Hit.ImpactNormal;
	if (FMath::Abs(WallNormal.Z) > 0.5)
	{
		return; // chão, rampa ou teto: não é parede
	}
	WallNormal.Z = 0.0;
	if (!WallNormal.Normalize())
	{
		return;
	}
	const FVector Velocity = GetMesh()->GetPhysicsLinearVelocity();
	const FVector Flat(Velocity.X, Velocity.Y, 0.0);
	const double FlatSpeed = Flat.Size();
	if (FlatSpeed * 0.036 < WallScrapeMinSpeedKmh)
	{
		return;
	}
	if (FVector::DotProduct(Flat, WallNormal) > 0.0)
	{
		WallNormal = -WallNormal; // agora aponta da parede para o carro
	}
	const double Into = -FVector::DotProduct(Flat, WallNormal);
	const float AngleDeg = FMath::RadiansToDegrees(FMath::Asin(static_cast<float>(FMath::Clamp(Into / FlatSpeed, 0.0, 1.0))));
	if (AngleDeg > WallScrapeMaxAngle)
	{
		return; // quase de frente: a batida para o carro (física normal)
	}
	const double Now = GetWorld()->GetTimeSeconds();
	const bool bNewImpact = Now - LastScrapeTime > 0.25;
	float Keep = 1.f;
	if (bNewImpact)
	{
		const float Alpha = FMath::Clamp((AngleDeg - 10.f) / FMath::Max(WallScrapeMaxAngle - 10.f, 1.f), 0.f, 1.f);
		Keep = FMath::Lerp(WallScrapeKeepShallow, WallScrapeKeepSteep, Alpha);
	}
	else
	{
		Keep = 1.f - WallScrapeDragPerSecond * static_cast<float>(FMath::Min(Now - LastScrapeTime, 0.1));
	}
	LastScrapeTime = Now;

	// Tira só a parte da velocidade que entra na parede; o resto segue junto ao muro.
	const FVector Tangent = Flat + WallNormal * Into;
	FVector NewVelocity = Tangent * Keep + WallNormal * 30.0;
	NewVelocity.Z = Velocity.Z;
	GetMesh()->SetPhysicsLinearVelocity(NewVelocity);

	// Alinha o carro com a parede (só andando para frente).
	const FVector Forward = GetActorForwardVector();
	if (FVector::DotProduct(Forward, Tangent) > 0.0)
	{
		const float YawError = FMath::FindDeltaAngleDegrees(static_cast<float>(Forward.Rotation().Yaw), static_cast<float>(Tangent.Rotation().Yaw));
		FVector Angular = GetMesh()->GetPhysicsAngularVelocityInDegrees();
		Angular.Z = FMath::Clamp(YawError * WallAlignStrength, -90.f, 90.f);
		GetMesh()->SetPhysicsAngularVelocityInDegrees(Angular);
	}
	if (bNewImpact)
	{
		UE_LOG(LogJR, Verbose, TEXT("%s: raspão na parede a %.0f graus, %.0f km/h"), *GetName(), AngleDeg, FlatSpeed * 0.036);
		OnWallScrape(Hit.ImpactPoint, static_cast<float>(FlatSpeed * 0.036), AngleDeg);
	}
}

bool AJRVehiclePawn::IsNearGround() const
{
	const FVector Up = GetActorUpVector();
	const FVector Start = GetActorLocation() + Up * 50.f;
	const FVector End = Start - Up * (GroundCheckDistance + 50.f);
	FCollisionQueryParams Params(SCENE_QUERY_STAT(JRVehicleGround), false, this);
	FCollisionObjectQueryParams ObjectParams;
	ObjectParams.AddObjectTypesToQuery(ECC_WorldStatic);
	ObjectParams.AddObjectTypesToQuery(ECC_WorldDynamic);
	FHitResult Hit;
	return GetWorld()->LineTraceSingleByObjectType(Hit, Start, End, ObjectParams, Params);
}

void AJRVehiclePawn::ApplyGripAssist(float DeltaSeconds, bool bGrounded)
{
	if (LateralGripAssist <= 0.f || !bGrounded)
	{
		return; // no ar o carro voa livre
	}
	const FVector Right = GetActorRightVector();
	const double Lateral = FVector::DotProduct(GetMesh()->GetPhysicsLinearVelocity(), Right);
	const float Scale = bHandbrakeHeld ? HandbrakeGripScale : 1.f;
	// Limitado para nunca inverter a derrapagem num único frame.
	const float Rate = FMath::Min(LateralGripAssist * Scale, 1.f / FMath::Max(DeltaSeconds, 0.001f));
	GetMesh()->AddForce(-Right * (Lateral * Rate), NAME_None, true);
}

void AJRVehiclePawn::ApplyBrakeAssist(bool bGrounded)
{
	if (BrakeAssistDecel <= 0.f || !bGrounded)
	{
		return;
	}
	const FVector Forward = GetActorForwardVector();
	const float ForwardSpeed = static_cast<float>(FVector::DotProduct(GetMesh()->GetPhysicsLinearVelocity(), Forward));
	const float ForwardKmh = ForwardSpeed * 0.036f;
	// Freio andando para frente; acelerador andando de ré também freia (o Chaos troca os pedais na ré).
	float Pedal = 0.f;
	if (ForwardKmh > BrakeAssistMinKmh)
	{
		Pedal = BrakeInputValue;
	}
	else if (ForwardKmh < -BrakeAssistMinKmh)
	{
		Pedal = ThrottleInputValue;
	}
	if (Pedal <= KINDA_SMALL_NUMBER)
	{
		return;
	}
	// Cresce com a velocidade: perto de parar some, e o Chaos engata a ré normalmente.
	const float SpeedAlpha = FMath::Clamp((FMath::Abs(ForwardKmh) - BrakeAssistMinKmh)
		/ FMath::Max(BrakeAssistFullAtKmh - BrakeAssistMinKmh, 1.f), 0.f, 1.f);
	const float Direction = ForwardSpeed > 0.f ? -1.f : 1.f;
	GetMesh()->AddForce(Forward * (Direction * BrakeAssistDecel * Pedal * SpeedAlpha), NAME_None, true);
}

void AJRVehiclePawn::ApplyRollStabilization(bool bGrounded)
{
	if (!bRollStabilization || RollAssistAccel <= 0.f)
	{
		return;
	}
	const FVector Up = GetActorUpVector();
	const float TiltDeg = FMath::RadiansToDegrees(FMath::Acos(FMath::Clamp(static_cast<float>(Up.Z), -1.f, 1.f)));
	const float StartDeg = bGrounded ? RollAssistStartDegrees : RollAssistAirStartDegrees;
	if (TiltDeg <= StartDeg)
	{
		return;
	}
	// Eixo de giro que leva o teto do carro de volta para cima (mistura rolagem e arfagem).
	FVector Axis = FVector::CrossProduct(Up, FVector::UpVector);
	if (!Axis.Normalize())
	{
		Axis = GetActorForwardVector(); // de cabeça para baixo exato: rola em volta da frente
	}
	const float Alpha = FMath::Clamp((TiltDeg - StartDeg) / FMath::Max(90.f - StartDeg, 1.f), 0.f, 1.f);
	const float Strength = RollAssistAccel * Alpha * (bGrounded ? 1.f : RollAssistAirScale);
	// Amortece o giro em volta desse eixo (nos dois sentidos): segura a capotagem e não passa do ponto ao voltar.
	const float SpinAlongAxis = static_cast<float>(FVector::DotProduct(GetMesh()->GetPhysicsAngularVelocityInRadians(), Axis));
	const float Accel = FMath::Clamp(Strength - SpinAlongAxis * RollAssistDamping, -RollAssistAccel * 1.5f, RollAssistAccel * 1.5f);
	GetMesh()->AddTorqueInRadians(Axis * Accel, NAME_None, true);
}

void AJRVehiclePawn::TickAutoRecover(float DeltaSeconds)
{
	if (!bAutoRecover)
	{
		FlippedTime = 0.f;
		return;
	}
	const bool bFlipped = GetActorUpVector().Z < FlippedUpThreshold;
	const bool bSlow = GetMesh()->GetPhysicsLinearVelocity().Size() * 0.036 < AutoRecoverMaxKmh;
	if (!bFlipped || !bSlow)
	{
		FlippedTime = 0.f;
		return;
	}
	FlippedTime += DeltaSeconds;
	if (FlippedTime >= AutoRecoverDelay)
	{
		BeginRecover(false);
	}
}

bool AJRVehiclePawn::BeginRecover(bool bManual)
{
	UWorld* World = GetWorld();
	if (!World || bRecovering || bExploded || !bDriveEnabled || !GetMesh()->IsSimulatingPhysics())
	{
		return false;
	}
	const double Now = World->GetTimeSeconds();
	if (Now - LastRecoverTime < RecoverCooldown)
	{
		return false;
	}
	if (bManual && FMath::Abs(GetSpeedKmh()) > ManualRecoverMaxKmh)
	{
		if (Now - LastRecoverDeniedTime > 1.0)
		{
			LastRecoverDeniedTime = Now;
			AJRHUD::Toast(this, TEXT("Diminua a velocidade para desvirar o carro (R)."), FLinearColor(1.f, 0.8f, 0.2f));
		}
		return false;
	}
	// Direção (yaw) atual do carro no plano; se o nariz aponta para cima/baixo, usa a lateral.
	FVector Forward = GetActorForwardVector();
	Forward.Z = 0.0;
	if (!Forward.Normalize())
	{
		FVector Side = GetActorRightVector();
		Side.Z = 0.0;
		Forward = Side.Normalize() ? FVector::CrossProduct(Side, FVector::UpVector) : FVector::ForwardVector;
	}
	const FRotator UprightRotation(0.0, Forward.Rotation().Yaw, 0.0);

	// Chão embaixo do carro (ignora o próprio carro e os zumbis).
	const FVector Here = GetActorLocation();
	FCollisionQueryParams Params(SCENE_QUERY_STAT(JRVehicleRecover), false, this);
	FCollisionObjectQueryParams ObjectParams;
	ObjectParams.AddObjectTypesToQuery(ECC_WorldStatic);
	ObjectParams.AddObjectTypesToQuery(ECC_WorldDynamic);
	FHitResult Hit;
	double GroundZ = Here.Z;
	if (World->LineTraceSingleByObjectType(Hit, Here + FVector(0.0, 0.0, 300.0), Here - FVector(0.0, 0.0, 5000.0), ObjectParams, Params))
	{
		GroundZ = Hit.ImpactPoint.Z;
	}
	FVector TargetLocation(Here.X, Here.Y, GroundZ + RecoverHeight);
	// Se a carroceria ficaria dentro de uma pedra/pilar, sobe mais um pouco (até 3 tentativas).
	const FQuat UprightQuat = UprightRotation.Quaternion();
	const FCollisionShape BodyShape = FCollisionShape::MakeBox(BodyHalfExtent * 0.9);
	for (int32 Attempt = 0; Attempt < 3; ++Attempt)
	{
		const FVector BoxCenter = TargetLocation + UprightQuat.RotateVector(BodyCenter);
		if (!World->OverlapAnyTestByObjectType(BoxCenter, UprightQuat, ObjectParams, BodyShape, Params))
		{
			break;
		}
		TargetLocation.Z += 150.0;
	}
	RecoverStart = GetActorTransform();
	RecoverTarget = FTransform(UprightQuat, TargetLocation, RecoverStart.GetScale3D());
	RecoverElapsed = 0.f;
	FlippedTime = 0.f;
	LastRecoverTime = Now;
	bRecovering = true;
	UE_LOG(LogJR, Log, TEXT("%s: desvirando (%s), %.0f cm acima do chão"), *GetName(), bManual ? TEXT("tecla R") : TEXT("automático"),
		TargetLocation.Z - GroundZ);
	if (!bManual && IsPlayerControlled())
	{
		AJRHUD::Toast(this, TEXT("Carro desvirado."), FLinearColor(0.6f, 0.9f, 1.f));
	}
	return true;
}

void AJRVehiclePawn::TickRecover(float DeltaSeconds)
{
	RecoverElapsed += DeltaSeconds;
	const float Alpha = FMath::Clamp(RecoverElapsed / FMath::Max(RecoverDuration, 0.05f), 0.f, 1.f);
	const float Smooth = FMath::SmoothStep(0.f, 1.f, Alpha);
	const FVector NewLocation = FMath::Lerp(RecoverStart.GetLocation(), RecoverTarget.GetLocation(), static_cast<double>(Smooth));
	const FQuat NewRotation = FQuat::Slerp(RecoverStart.GetRotation(), RecoverTarget.GetRotation(), static_cast<double>(Smooth));
	if (Alpha >= 1.f)
	{
		bRecovering = false;
		MoveToTransform(RecoverTarget); // zera velocidades e reinicia a física já de pé
		GetMesh()->WakeAllRigidBodies();
		return;
	}
	// Teleporte físico a cada frame, parado (a gravidade não acumula durante o movimento).
	GetMesh()->SetPhysicsLinearVelocity(FVector::ZeroVector);
	GetMesh()->SetPhysicsAngularVelocityInDegrees(FVector::ZeroVector);
	SetActorLocationAndRotation(NewLocation, NewRotation, false, nullptr, ETeleportType::TeleportPhysics);
}

void AJRVehiclePawn::PossessedBy(AController* NewController)
{
	Super::PossessedBy(NewController);
	if (NewController && NewController->IsPlayerController())
	{
		RefreshDriver();
		if (GetWorldTimerManager().IsTimerActive(CarBombTimer))
		{
			// Voltou para o carro: desarma (continua pegando fogo).
			GetWorldTimerManager().ClearTimer(CarBombTimer);
			AJRHUD::Toast(this, TEXT("Bomba desarmada (o carro continua pegando fogo)."), FLinearColor(1.f, 0.8f, 0.2f));
		}
	}
}

void AJRVehiclePawn::SetDriverVisible(bool bVisible)
{
	DriverMesh->SetHiddenInGame(!bVisible);
	DriverMesh->SetComponentTickEnabled(bVisible);
	bDriverShown = bVisible;
}

void AJRVehiclePawn::RefreshDriver()
{
	UWorld* World = GetWorld();
	AJRGameMode* GameMode = World ? World->GetAuthGameMode<AJRGameMode>() : nullptr;
	USkeletalMesh* HeroMesh = nullptr;
	UAnimSequenceBase* DriveAnim = FallbackDrivingAnim;
	const AJRCharacter* HeroDefaults = nullptr;
	if (GameMode)
	{
		TSubclassOf<AJRCharacter> HeroClass = GameMode->ResolveCharacterClass();
		if (HeroClass)
		{
			HeroDefaults = GetDefault<AJRCharacter>(HeroClass);
		}
	}
	if (HeroDefaults)
	{
		if (HeroDefaults->GetDrivingAnim())
		{
			DriveAnim = HeroDefaults->GetDrivingAnim();
		}
		if (HeroDefaults->GetMesh())
		{
			HeroMesh = HeroDefaults->GetMesh()->GetSkeletalMeshAsset();
		}
	}
	const FJRSkinDefinition* Skin = GameMode ? GameMode->ResolveSelectedSkin() : nullptr;
	if (Skin)
	{
		if (USkeletalMesh* SkinMesh = Skin->Mesh.LoadSynchronous())
		{
			HeroMesh = SkinMesh;
		}
	}
	if (!HeroMesh || !DriveAnim)
	{
		UE_LOG(LogJR, Warning, TEXT("%s: motorista escondido (malha=%s, animação=%s). Rode tools/unreal/fix_vehicle_feel.py."),
			*GetName(), *GetNameSafe(HeroMesh), *GetNameSafe(DriveAnim));
		SetDriverVisible(false);
		return;
	}
	if (DriveAnim->GetSkeleton() != HeroMesh->GetSkeleton())
	{
		UE_LOG(LogJR, Warning, TEXT("%s: %s não é do esqueleto de %s; o motorista pode ficar em T."),
			*GetName(), *GetNameSafe(DriveAnim), *GetNameSafe(HeroMesh));
	}
	if (bDriverHeadHidden)
	{
		// Troca de malha: mostra a cabeça de novo (a primeira pessoa esconde outra vez se estiver ligada).
		SetDriverHeadHidden(false);
	}
	DriverMesh->SetSkeletalMeshAsset(HeroMesh);
	DriverMesh->EmptyOverrideMaterials();
	if (HeroDefaults && HeroDefaults->GetMesh())
	{
		const TArray<TObjectPtr<UMaterialInterface>>& HeroMaterials = HeroDefaults->GetMesh()->OverrideMaterials;
		for (int32 Slot = 0; Slot < HeroMaterials.Num(); ++Slot)
		{
			if (HeroMaterials[Slot])
			{
				DriverMesh->SetMaterial(Slot, HeroMaterials[Slot]);
			}
		}
	}
	if (Skin)
	{
		for (int32 Slot = 0; Slot < Skin->MaterialOverrides.Num(); ++Slot)
		{
			if (UMaterialInterface* Material = Skin->MaterialOverrides[Slot].LoadSynchronous())
			{
				DriverMesh->SetMaterial(Slot, Material);
			}
		}
	}
	// Canelas/pés atravessariam o assoalho: esconde (o tronco e as coxas ficam dentro da cabine).
	for (const FName& Bone : DriverHiddenBones)
	{
		if (DriverMesh->GetBoneIndex(Bone) != INDEX_NONE)
		{
			DriverMesh->HideBoneByName(Bone, EPhysBodyOp::PBO_None);
		}
	}
	DriverMesh->SetAnimationMode(EAnimationMode::AnimationSingleNode);
	DriverMesh->PlayAnimation(DriveAnim, true);
	SetDriverVisible(true);
}

void AJRVehiclePawn::HandleNitro(const FInputActionValue& Value)
{
	bNitroHeld = Value.Get<bool>();
}

void AJRVehiclePawn::TickNitro()
{
	bNitroActive = bNitroHeld && bDriveEnabled && !bRecovering && BrakeInputValue < 0.1f && NitroCharge > 0.f
		&& GetSpeedKmh() < NitroMaxSpeedKmh;
	if (!bNitroActive)
	{
		return;
	}
	const float Dt = 0.05f;
	NitroCharge = FMath::Max(0.f, NitroCharge - NitroDrainPerSecond * Dt);
	// A força do nitro é aplicada no Tick (a cada frame).
}

FTransform AJRVehiclePawn::GetExitTransform() const
{
	return ExitPoint->GetComponentTransform();
}

FTransform AJRVehiclePawn::GetSeatTransform() const
{
	return SeatPoint->GetComponentTransform();
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
	else
	{
		// Reserva: sem IA_Brake no BP o freio ainda funciona (S e seta para baixo).
		UE_LOG(LogJR, Warning, TEXT("%s: BrakeAction vazio no BP; usando S/seta para baixo direto. Rode tools/unreal/fix_vehicle_feel.py."), *GetName());
		static_cast<UInputComponent*>(Input)->BindKey(EKeys::S, IE_Pressed, this, &AJRVehiclePawn::HandleBrakeKeyPressed);
		static_cast<UInputComponent*>(Input)->BindKey(EKeys::S, IE_Released, this, &AJRVehiclePawn::HandleBrakeKeyReleased);
		static_cast<UInputComponent*>(Input)->BindKey(EKeys::Down, IE_Pressed, this, &AJRVehiclePawn::HandleBrakeKeyPressed);
		static_cast<UInputComponent*>(Input)->BindKey(EKeys::Down, IE_Released, this, &AJRVehiclePawn::HandleBrakeKeyReleased);
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
	else
	{
		static_cast<UInputComponent*>(Input)->BindKey(EKeys::SpaceBar, IE_Pressed, this, &AJRVehiclePawn::HandleHandbrakeKeyPressed);
		static_cast<UInputComponent*>(Input)->BindKey(EKeys::SpaceBar, IE_Released, this, &AJRVehiclePawn::HandleHandbrakeKeyReleased);
	}
	if (ResetAction)
	{
		Input->BindAction(ResetAction, ETriggerEvent::Started, this, &AJRVehiclePawn::HandleReset);
	}
	else
	{
		// Reserva: R desvira mesmo sem IA_Reset no BP.
		static_cast<UInputComponent*>(Input)->BindKey(EKeys::R, IE_Pressed, this, &AJRVehiclePawn::HandleResetKey);
	}
	// [A-078] descer do carro a qualquer hora (antes só um checkpoint tirava o herói do carro)
	static_cast<UInputComponent*>(Input)->BindKey(EKeys::E, IE_Pressed, this, &AJRVehiclePawn::HandleExitKey);
	static_cast<UInputComponent*>(Input)->BindKey(EKeys::Gamepad_FaceButton_Left, IE_Pressed, this, &AJRVehiclePawn::HandleExitKey);
	if (LookAction)
	{
		Input->BindAction(LookAction, ETriggerEvent::Triggered, this, &AJRVehiclePawn::HandleLook);
	}
	if (NitroAction)
	{
		Input->BindAction(NitroAction, ETriggerEvent::Started, this, &AJRVehiclePawn::HandleNitro);
		Input->BindAction(NitroAction, ETriggerEvent::Completed, this, &AJRVehiclePawn::HandleNitro);
	}
	if (MouseLookAction)
	{
		Input->BindAction(MouseLookAction, ETriggerEvent::Triggered, this, &AJRVehiclePawn::HandleLook);
	}
}

void AJRVehiclePawn::HandleThrottle(const FInputActionValue& Value)
{
	ApplyThrottleInput(Value.Get<float>());
}

void AJRVehiclePawn::HandleBrake(const FInputActionValue& Value)
{
	ApplyBrakeInput(Value.Get<float>());
}

void AJRVehiclePawn::ApplyThrottleInput(float Value)
{
	ThrottleInputValue = bDriveEnabled ? FMath::Clamp(Value, 0.f, 1.f) : 0.f;
	if (bDriveEnabled)
	{
		// [A-075] sem combustível o pedal não faz nada; engasgando, pulsa (TickFuel reaplica a cada frame)
		GetVehicleMovementComponent()->SetThrottleInput(EffectiveThrottle());
	}
}

// ---------------------------------------------------------------- [A-075] combustível

void AJRVehiclePawn::SetPendingRequiredItem(FName Item, const FString& Label)
{
	PendingRequiredItem = Item;
	PendingRequiredItemLabel = Label;
	if (Item == FName(TEXT("Fuel")))
	{
		// Roteiro: o carro chega ao posto com o tanque seco e só anda de novo com o galão.
		FuelLevel = 0.f;
		bEngineDead = true;
	}
}

void AJRVehiclePawn::ClearPendingRequiredItem()
{
	const bool bWasFuel = PendingRequiredItem == FName(TEXT("Fuel"));
	PendingRequiredItem = NAME_None;
	if (bWasFuel)
	{
		Refuel(1.f); // o galão enche o tanque
	}
}

void AJRVehiclePawn::Refuel(float Amount)
{
	FuelLevel = FMath::Clamp(FuelLevel + FMath::Max(0.f, Amount), 0.f, 1.f);
	if (FuelLevel > 0.f && PendingRequiredItem != FName(TEXT("Fuel")))
	{
		bEngineDead = false;
	}
}

float AJRVehiclePawn::EffectiveThrottle() const
{
	if (bEngineDead)
	{
		return 0.f;
	}
	if (IsFuelSputtering())
	{
		// Engasgo: força média FuelLimpThrottle, com falhas rápidas (o motor "tosse").
		const float Wave = 0.5f + 0.5f * FMath::Sin(FuelSputterPhase * 2.f * UE_PI);
		const float Cough = Wave > 0.8f ? 0.15f : 1.f;
		return ThrottleInputValue * FuelLimpThrottle * Cough * (0.7f + 0.6f * Wave);
	}
	return ThrottleInputValue;
}

void AJRVehiclePawn::TickFuel(float DeltaSeconds)
{
	if (bEngineDead || bExploded)
	{
		if (bEngineDead && ThrottleInputValue > 0.f)
		{
			GetVehicleMovementComponent()->SetThrottleInput(0.f);
		}
		return;
	}
	const float SpeedCmS = FMath::Abs(GetVehicleMovementComponent()->GetForwardSpeed());
	const float Km = SpeedCmS * DeltaSeconds / 100000.f;
	const float Use = 1.f + FuelThrottleExtra * ThrottleInputValue + (bNitroActive ? FuelNitroExtra : 0.f);
	const float Floor = PendingRequiredItem.IsNone() ? FuelLimpLevel : 0.f;
	FuelLevel = FMath::Max(Floor, FuelLevel - Km / FMath::Max(0.1f, FuelRangeKm) * Use);
	if (IsFuelSputtering())
	{
		FuelSputterPhase = FMath::Fmod(FuelSputterPhase + DeltaSeconds * FuelSputterHz * (0.8f + 0.4f * FMath::FRand()), 1000.f);
		if (ThrottleInputValue > 0.f)
		{
			GetVehicleMovementComponent()->SetThrottleInput(EffectiveThrottle());
		}
	}
}

// ---------------------------------------------------------------- [A-075] passageiro

void AJRVehiclePawn::SetPassenger(const USkeletalMeshComponent* Source, UAnimSequenceBase* Anim, bool bAnimIsSitting)
{
	USkeletalMesh* PassengerAsset = Source ? Source->GetSkeletalMeshAsset() : nullptr;
	if (!PassengerAsset)
	{
		ClearPassenger();
		return;
	}
	PassengerMesh->SetSkeletalMeshAsset(PassengerAsset);
	PassengerMesh->EmptyOverrideMaterials();
	for (int32 Slot = 0; Slot < Source->GetNumMaterials(); ++Slot)
	{
		if (UMaterialInterface* Material = Source->GetMaterial(Slot))
		{
			PassengerMesh->SetMaterial(Slot, Material);
		}
	}
	PassengerMesh->SetRelativeLocation(FVector(0.f, 0.f, -PassengerHipsHeight));
	for (const FName& Bone : (bAnimIsSitting ? PassengerHiddenBones : PassengerHiddenBonesStanding))
	{
		if (PassengerMesh->GetBoneIndex(Bone) != INDEX_NONE)
		{
			PassengerMesh->HideBoneByName(Bone, EPhysBodyOp::PBO_None);
		}
	}
	if (Anim)
	{
		if (Anim->GetSkeleton() != PassengerAsset->GetSkeleton())
		{
			UE_LOG(LogJR, Warning, TEXT("%s: animação do carona %s não é do esqueleto de %s (rode tools/unreal/setup_passenger.py)."),
				*GetName(), *GetNameSafe(Anim), *GetNameSafe(PassengerAsset));
		}
		PassengerMesh->SetAnimationMode(EAnimationMode::AnimationSingleNode);
		PassengerMesh->PlayAnimation(Anim, true);
	}
	PassengerMesh->SetHiddenInGame(false);
	PassengerMesh->SetComponentTickEnabled(true);
	bHasPassenger = true;
}

void AJRVehiclePawn::ClearPassenger()
{
	PassengerMesh->SetHiddenInGame(true);
	PassengerMesh->SetComponentTickEnabled(false);
	bHasPassenger = false;
}

void AJRVehiclePawn::ApplyBrakeInput(float Value)
{
	// Freio do Chaos (bReverseAsBrake): freia andando e engata a ré quando quase parado.
	BrakeInputValue = bDriveEnabled ? FMath::Clamp(Value, 0.f, 1.f) : 0.f;
	if (bDriveEnabled)
	{
		GetVehicleMovementComponent()->SetBrakeInput(BrakeInputValue);
	}
}

void AJRVehiclePawn::ApplyHandbrakeInput(bool bHeld)
{
	bHandbrakeHeld = bHeld;
	if (bDriveEnabled)
	{
		GetVehicleMovementComponent()->SetHandbrakeInput(bHeld);
	}
}

void AJRVehiclePawn::HandleReset(const FInputActionValue& Value)
{
	BeginRecover(true);
}

void AJRVehiclePawn::HandleSteer(const FInputActionValue& Value)
{
	LastSteerInput = Value.Get<float>();
	if (bDriveEnabled)
	{
		GetVehicleMovementComponent()->SetSteeringInput(ComputeSteering(LastSteerInput));
	}
}

void AJRVehiclePawn::HandleSteerReleased(const FInputActionValue& Value)
{
	LastSteerInput = 0.f;
	if (bDriveEnabled)
	{
		// Sem input o pneu furado (e o zumbi agarrado) continua puxando para o lado.
		GetVehicleMovementComponent()->SetSteeringInput(ComputeSteering(0.f));
	}
}

void AJRVehiclePawn::HandleHandbrake(const FInputActionValue& Value)
{
	ApplyHandbrakeInput(Value.Get<bool>());
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
	LastSteerInput = 0.f;
	ThrottleInputValue = 0.f;
	BrakeInputValue = 0.f;
	bHandbrakeHeld = false;
}

void AJRVehiclePawn::UnPossessed()
{
	// Requisito de teste: o veículo não continua acelerando quando o controle muda.
	ZeroInputs(true);
	// O herói de verdade assume no banco (animação de sair): o motorista visual some.
	SetDriverVisible(false);
	// Agarrados descem vivos e voltam a perseguir o jogador a pé.
	ReleaseAllGrabbers(false);
	// "Bomba": saiu do carro pegando fogo, explode daqui a pouco e leva os zumbis junto.
	if (bCarBombOnExitWhileBurning && bFireOn && !bExploded && !GetWorldTimerManager().IsTimerActive(CarBombTimer))
	{
		GetWorldTimerManager().SetTimer(CarBombTimer, this, &AJRVehiclePawn::Explode, FMath::Max(CarBombFuseTime, 0.1f), false);
		AJRHUD::Toast(this, FString::Printf(TEXT("Corra! O carro explode em %.0f s."), CarBombFuseTime), FLinearColor(1.f, 0.3f, 0.1f));
		UE_LOG(LogJR, Log, TEXT("%s: bomba armada (%.1f s)"), *GetName(), CarBombFuseTime);
	}
	Super::UnPossessed();
}

void AJRVehiclePawn::ParkAndDisable()
{
	bDriveEnabled = false;
	ZeroInputs(true);
	GetWorldTimerManager().SetTimer(SleepTimer, this, &AJRVehiclePawn::SleepPhysics, SleepDelayAfterPark, false);
}

void AJRVehiclePawn::StopThenExit(const FTransform& FallbackTransform)
{
	if (GetWorldTimerManager().IsTimerActive(StopExitTimer))
	{
		return;
	}
	bDriveEnabled = false;
	ZeroInputs(true);
	PendingExitFallback = FallbackTransform;
	StopExitElapsed = 0.f;
	GetWorldTimerManager().SetTimer(StopExitTimer, this, &AJRVehiclePawn::TickStopForExit, 0.1f, true);
}

void AJRVehiclePawn::HandleExitKey()
{
	if (bExploded || !IsPlayerControlled() || GetWorldTimerManager().IsTimerActive(StopExitTimer))
	{
		return;
	}
	// Acima disso o E só avisa para frear; abaixo o carro freia sozinho até parar e o herói desce.
	constexpr float ExitRequestMaxKmh = 25.f;
	if (FMath::Abs(GetSpeedKmh()) > ExitRequestMaxKmh)
	{
		AJRHUD::Toast(this, TEXT("Freie para descer do buggy."), FLinearColor(1.f, 0.85f, 0.3f));
		return;
	}
	StopThenExit(GetExitTransform()); // freia até parar e só então desce
}

void AJRVehiclePawn::TickStopForExit()
{
	StopExitElapsed += 0.1f;
	ZeroInputs(true);
	if (FMath::Abs(GetSpeedKmh()) > ExitMaxSpeedKmh && StopExitElapsed < ExitStopTimeout)
	{
		return;
	}
	GetWorldTimerManager().ClearTimer(StopExitTimer);
	// Parada total: o carro não pode seguir andando sozinho depois que o jogador desce.
	GetMesh()->SetPhysicsLinearVelocity(FVector::ZeroVector);
	GetMesh()->SetPhysicsAngularVelocityInDegrees(FVector::ZeroVector);
	if (AJRPlayerController* PC = Cast<AJRPlayerController>(GetController()))
	{
		PC->RequestExitVehicle(PendingExitFallback);
	}
}

void AJRVehiclePawn::SleepPhysics()
{
	GetMesh()->PutAllRigidBodiesToSleep();
}

void AJRVehiclePawn::HandleVehicleDisabled()
{
	// Integridade no fim: o carro explode (falha no estágio Driving; nos outros o jogador sai a pé).
	Explode();
}

// ---------------------------------------------------------------- Primeira pessoa (motorista)

void AJRVehiclePawn::SetFirstPersonView(bool bEnable, bool bInstant)
{
	if (bFirstPersonWanted && !bEnable)
	{
		// Volta para a câmera de trás olhando para onde a cabeça olhava.
		if (AController* ViewController = GetController())
		{
			ViewController->SetControlRotation(FRotator(-10.f, GetActorRotation().Yaw + FPLookYaw, 0.f));
		}
	}
	if (bEnable && !bFirstPersonWanted)
	{
		FPLookYaw = 0.f;
		FPLookPitch = 0.f;
		FPLookIdleTime = 0.f;
		bFPLookInit = false;
		bFPStableValid = false;
	}
	bFirstPersonWanted = bEnable;
	if (bInstant)
	{
		FPBlendAlpha = bEnable ? 1.f : 0.f;
	}
}

void AJRVehiclePawn::SetDriverHeadHidden(bool bHide)
{
	if (bHide == bDriverHeadHidden || !DriverMesh)
	{
		return;
	}
	bDriverHeadHidden = bHide;
	for (const FName& BoneToHide : FPHiddenBones)
	{
		if (BoneToHide.IsNone() || DriverMesh->GetBoneIndex(BoneToHide) == INDEX_NONE)
		{
			continue;
		}
		if (bHide)
		{
			DriverMesh->HideBoneByName(BoneToHide, EPhysBodyOp::PBO_None);
		}
		else
		{
			DriverMesh->UnHideBoneByName(BoneToHide);
		}
	}
}

void AJRVehiclePawn::CalcCamera(float DeltaTime, FMinimalViewInfo& OutResult)
{
	// Câmera de trás (SpringArm). A da cabeça do motorista é misturada por cima.
	Super::CalcCamera(DeltaTime, OutResult);
	// [A-073] sensação de velocidade/impacto (tempo real; só a câmera)
	UpdateDriveFeel(FMath::Min(DeltaTime / FMath::Max(0.0001f, UGameplayStatics::GetGlobalTimeDilation(this)), 0.05f));

	const bool bCanUseFP = bFirstPersonWanted && bDriverShown && DriverMesh && DriverMesh->GetSkeletalMeshAsset()
		&& DriverMesh->GetBoneIndex(FPHeadBone) != INDEX_NONE;
	const float TargetAlpha = bCanUseFP ? 1.f : 0.f;
	if (FPBlendTime <= KINDA_SMALL_NUMBER)
	{
		FPBlendAlpha = TargetAlpha;
	}
	else
	{
		FPBlendAlpha = FMath::FInterpConstantTo(FPBlendAlpha, TargetAlpha, DeltaTime, 1.f / FPBlendTime);
	}
	SetDriverHeadHidden(FPBlendAlpha > 0.5f);
	if (FPBlendAlpha <= 0.f)
	{
		bFPStableValid = false;
		bFPLookInit = false;
		ApplyDriveFeel(OutResult, 0.f); // [A-073] antes da conferência final (A-065)
		// [A-065] câmera de trás nunca dentro do chão (morro atrás do carro, câmera com atraso)
		if (SpringArm)
		{
			AJRCharacter::KeepCameraOutOfWorld(this, SpringArm->GetComponentLocation(), 25.f, OutResult.Location);
		}
		return;
	}

	// Olhar livre: soma quanto o mouse/analógico girou desde o último quadro (já com sensibilidade do jogo),
	// relativo à frente do carro: o carro faz a curva e a cabeça vai junto.
	const FRotator ControlNow = GetControlRotation();
	if (!bFPLookInit)
	{
		FPLastControlRotation = ControlNow;
		bFPLookInit = true;
	}
	const FRotator LookDelta = (ControlNow - FPLastControlRotation).GetNormalized();
	FPLastControlRotation = ControlNow;
	const float DeltaYaw = static_cast<float>(LookDelta.Yaw);
	const float DeltaPitch = static_cast<float>(LookDelta.Pitch);
	FPLookIdleTime = (FMath::Abs(DeltaYaw) + FMath::Abs(DeltaPitch) > 0.01f) ? 0.f : FPLookIdleTime + DeltaTime;
	FPLookYaw = FMath::Clamp(FPLookYaw + DeltaYaw, -FPMaxLookYaw, FPMaxLookYaw);
	FPLookPitch = FMath::Clamp(FPLookPitch + DeltaPitch, FPMinLookPitch, FPMaxLookPitch);
	if (FPLookIdleTime > FPRecenterDelay)
	{
		FPLookYaw = FMath::FInterpTo(FPLookYaw, 0.f, DeltaTime, FPRecenterSpeed);
		FPLookPitch = FMath::FInterpTo(FPLookPitch, 0.f, DeltaTime, FPRecenterSpeed);
	}

	const FTransform CarFrame(GetActorQuat(), GetActorLocation());
	const FRotator CarRot = GetActorRotation();
	const FQuat CarQuat = FRotator(CarRot.Pitch, CarRot.Yaw, CarRot.Roll * FPRollFollow).Quaternion();
	const FQuat ViewQuat = CarQuat * FRotator(FPLookPitch, FPLookYaw, 0.f).Quaternion();

	// Cabeça do motorista com um pouco de estabilização (buracos e solavancos balançam menos).
	const FVector HeadWorld = DriverMesh->GetBoneLocation(FPHeadBone);
	const FVector HeadLocal = CarFrame.InverseTransformPosition(HeadWorld);
	if (!bFPStableValid)
	{
		FPStableLocal = HeadLocal;
		bFPStableValid = true;
	}
	FPStableLocal = FMath::VInterpTo(FPStableLocal, HeadLocal, DeltaTime, FPStabilizeSpeed);
	const FVector EyeLocal = FMath::Lerp(HeadLocal, FPStableLocal, FMath::Clamp(FPStabilizeAlpha, 0.f, 1.f));
	const FVector EyeLocation = CarFrame.TransformPosition(EyeLocal) + CarQuat.RotateVector(FPEyeOffset);

	const float Smooth = FMath::SmoothStep(0.f, 1.f, FPBlendAlpha);
	OutResult.Location = FMath::Lerp(OutResult.Location, EyeLocation, Smooth);
	OutResult.Rotation = FQuat::Slerp(OutResult.Rotation.Quaternion(), ViewQuat, Smooth).Rotator();
	OutResult.FOV = FMath::Lerp(OutResult.FOV, FPFov, Smooth);
	ApplyDriveFeel(OutResult, Smooth); // [A-073]
}

void AJRVehiclePawn::UpdateDriveFeel(float RealDt)
{
	// [A-073] Liga o atropelo ao tremor uma vez (sem mexer no BeginPlay/NotifyZombieCarEvent do carro).
	if (!bDriveFeelBound)
	{
		OnZombieCarEvent.AddUniqueDynamic(this, &AJRVehiclePawn::HandleZombieCarFeel);
		bDriveFeelBound = true;
	}
	const FVector Vel = GetVelocity();
	const float Kmh = static_cast<float>(Vel.Size()) * 0.036f;
	if (!bDriveFeelVelValid || RealDt <= KINDA_SMALL_NUMBER)
	{
		DriveFeelLastVel = Vel;
		bDriveFeelVelValid = RealDt > KINDA_SMALL_NUMBER;
	}
	else
	{
		// Solavanco = perda brusca de velocidade (batida, atropelo) ou subida brusca do Z (aterrissou de um pulo).
		const float LostKmh = FMath::Max(0.f, static_cast<float>(DriveFeelLastVel.Size() - Vel.Size())) * 0.036f;
		const float UpKmh = FMath::Max(0.f, static_cast<float>(Vel.Z - DriveFeelLastVel.Z)) * 0.036f;
		const float JoltRate = FMath::Max(LostKmh, UpKmh * 0.7f) / RealDt;
		if (JoltRate > DriveJoltMinKmhPerSec)
		{
			DriveTrauma = FMath::Min(0.75f, DriveTrauma + (JoltRate - DriveJoltMinKmhPerSec) / 1500.f);
		}
		DriveFeelLastVel = Vel;
	}
	DriveTrauma = FMath::Max(0.f, DriveTrauma - 1.8f * RealDt);
	DriveShakeTime += RealDt;
	const float SpeedAlpha = FMath::Clamp((Kmh - DriveFOVStartKmh) / FMath::Max(1.f, DriveFOVFullKmh - DriveFOVStartKmh), 0.f, 1.f);
	// curva suave (ease-in-out): perto do início e do fim muda pouco
	const float Eased = SpeedAlpha * SpeedAlpha * (3.f - 2.f * SpeedAlpha);
	DriveFOVNow = FMath::FInterpTo(DriveFOVNow, DriveSpeedFOVBonus * Eased, RealDt, DriveFOVBlendSpeed);
	DriveRumbleNow = FMath::FInterpTo(DriveRumbleNow, Eased, RealDt, 3.f);
}

void AJRVehiclePawn::ApplyDriveFeel(FMinimalViewInfo& OutResult, float FirstPersonAlpha) const
{
	const float Motion = JRFeel::MotionScale();
	const float ShakeScale = JRFeel::ShakeScale();
	// Primeira pessoa enjoa mais: metade do FOV extra e da vibração.
	const float FPCut = FMath::Lerp(1.f, 0.5f, FMath::Clamp(FirstPersonAlpha, 0.f, 1.f));
	OutResult.FOV = FMath::Clamp(OutResult.FOV + DriveFOVNow * Motion * FPCut, 30.f, 130.f);
	const float Phase = DriveShakeTime;
	// Vibração do terreno: lenta e pequena (sem rolar a câmera).
	const float Rumble = DriveRumbleNow * DriveRumbleDegrees * ShakeScale * FPCut;
	// Solavanco: trauma ao quadrado (leve quase não mexe, batida forte sacode).
	const float Jolt = DriveTrauma * DriveTrauma * DriveShakeMaxAngle * ShakeScale;
	if (Rumble + Jolt > 0.0005f)
	{
		OutResult.Rotation.Pitch += FMath::PerlinNoise1D(Phase * 9.f + 3.1f) * Rumble + FMath::PerlinNoise1D(Phase * 24.f + 17.f) * Jolt;
		OutResult.Rotation.Yaw += FMath::PerlinNoise1D(Phase * 7.f + 41.f) * Rumble * 0.6f + FMath::PerlinNoise1D(Phase * 24.f + 59.f) * Jolt;
		OutResult.Rotation.Roll += FMath::PerlinNoise1D(Phase * 24.f + 83.f) * Jolt * 0.4f;
	}
}

void AJRVehiclePawn::HandleZombieCarFeel(EJRZombieCarEvent Event, AActor* Zombie, FVector Location, float Value)
{
	// [A-073] só a câmera de quem está dirigindo
	if (!IsPlayerControlled())
	{
		return;
	}
	switch (Event)
	{
	case EJRZombieCarEvent::RunOver:
		DriveTrauma = FMath::Min(0.8f, DriveTrauma + DriveRunOverShake * FMath::Clamp(Value / 60.f, 0.5f, 1.5f));
		break;
	case EJRZombieCarEvent::ZombieHitCar:
	case EJRZombieCarEvent::ZombiePushed:
		DriveTrauma = FMath::Min(0.8f, DriveTrauma + 0.12f);
		break;
	default:
		break;
	}
}

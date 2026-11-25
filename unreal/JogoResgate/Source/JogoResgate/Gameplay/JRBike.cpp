// Copyright utrazin. All Rights Reserved.

#include "Gameplay/JRBike.h"

#include "Animation/AnimInstance.h"
#include "Animation/AnimMontage.h"
#include "Animation/AnimSequenceBase.h"
#include "Animation/Skeleton.h"
#include "Camera/CameraComponent.h"
#include "Characters/JRCharacter.h"
#include "CollisionQueryParams.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/HitResult.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/Controller.h"
#include "GameFramework/SpringArmComponent.h"
#include "JogoResgate.h"
#include "Materials/MaterialInterface.h"
#include "PhysicalMaterials/PhysicalMaterial.h"

namespace
{
	constexpr float JRGravity = 980.f;

	UStaticMeshComponent* MakePart(AJRBike* Owner, const TCHAR* Name, USceneComponent* Parent)
	{
		UStaticMeshComponent* C = Owner->CreateDefaultSubobject<UStaticMeshComponent>(Name);
		C->SetupAttachment(Parent);
		C->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		C->SetCanEverAffectNavigation(false);
		return C;
	}

	USceneComponent* MakePivot(AJRBike* Owner, const TCHAR* Name, USceneComponent* Parent)
	{
		USceneComponent* C = Owner->CreateDefaultSubobject<USceneComponent>(Name);
		C->SetupAttachment(Parent);
		return C;
	}

	/** Mola amortecida (Euler semi-implícito): Damping = fração do amortecimento crítico. */
	void Spring(float& X, float& V, float Target, float Stiffness, float Damping, float Dt)
	{
		const float C = 2.f * FMath::Sqrt(FMath::Max(Stiffness, 0.f)) * Damping;
		V += (Stiffness * (Target - X) - C * V) * Dt;
		X += V * Dt;
	}

	bool HasKeyword(const FString& Name, const TArray<FString>& Keywords)
	{
		for (const FString& K : Keywords)
		{
			if (!K.IsEmpty() && Name.Contains(K, ESearchCase::IgnoreCase))
			{
				return true;
			}
		}
		return false;
	}
}

AJRBike::AJRBike()
{
	PrimaryActorTick.bCanEverTick = true;
	PrimaryActorTick.bStartWithTickEnabled = false;
	// Roda depois do controle (entrada do quadro) e antes do CharacterMovement do herói (prerequisitos ao montar).
	PrimaryActorTick.TickGroup = TG_PrePhysics;

	Root = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
	SetRootComponent(Root);
	LeanPivot = MakePivot(this, TEXT("LeanPivot"), Root);

	Frame = MakePart(this, TEXT("Frame"), LeanPivot);
	Frame->SetCollisionProfileName(TEXT("BlockAllDynamic"));
	Seat = MakePart(this, TEXT("Seat"), LeanPivot);

	SteerAxis = MakePivot(this, TEXT("SteerAxis"), LeanPivot);
	SteerYaw = MakePivot(this, TEXT("SteerYaw"), SteerAxis);
	SteerOffset = MakePivot(this, TEXT("SteerOffset"), SteerYaw);
	Handlebar = MakePart(this, TEXT("Handlebar"), SteerOffset);
	FrontPivot = MakePivot(this, TEXT("FrontPivot"), SteerOffset);
	FrontWheel = MakePart(this, TEXT("FrontWheel"), FrontPivot);

	RearPivot = MakePivot(this, TEXT("RearPivot"), LeanPivot);
	RearWheel = MakePart(this, TEXT("RearWheel"), RearPivot);

	CrankPivot = MakePivot(this, TEXT("CrankPivot"), LeanPivot);
	Crank = MakePart(this, TEXT("Crank"), CrankPivot);
	PedalRight = MakePart(this, TEXT("PedalRight"), CrankPivot);
	PedalLeft = MakePart(this, TEXT("PedalLeft"), CrankPivot);

	// [A-098] pedaladas geradas por tools/blender/gen_bike_rider.py e importadas por tools/unreal/setup_bike_anim.py
	for (const TCHAR* NN : {TEXT("01"), TEXT("02")})
	{
		FJRBikeRiderAnim Entry;
		Entry.Mesh = TSoftObjectPtr<USkeletalMesh>(FSoftObjectPath(FString::Printf(TEXT("/Game/Characters/Hero%s/Mesh/SK_Hero%s.SK_Hero%s"), NN, NN, NN)));
		Entry.PedalAnim = TSoftObjectPtr<UAnimSequenceBase>(FSoftObjectPath(FString::Printf(TEXT("/Game/Characters/Hero%s/Anims/Bike/A_Bike_Pedal_H%s.A_Bike_Pedal_H%s"), NN, NN, NN)));
		RiderAnims.Add(Entry);
	}
}

void AJRBike::OnConstruction(const FTransform& Transform)
{
	Super::OnConstruction(Transform);
	ApplyMeshes();
	LeanPivot->SetRelativeLocationAndRotation(FVector::ZeroVector, FRotator(0.f, 0.f, -ParkedLeanDegrees));
}

void AJRBike::BeginPlay()
{
	Super::BeginPlay();
	ApplyMeshes();
	SetParkedCollision(true);
	LeanPivot->SetRelativeLocationAndRotation(FVector::ZeroVector, FRotator(0.f, 0.f, -ParkedLeanDegrees));
}

void AJRBike::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
	if (AJRCharacter* Hero = Rider.Get())
	{
		RestoreRider(Hero);
	}
	Super::EndPlay(EndPlayReason);
}

void AJRBike::ApplyMeshes()
{
	UStaticMesh* FrameAsset = FrameMesh.LoadSynchronous();
	const bool bLegacy = FrameAsset == nullptr;
	if (bLegacy)
	{
		FrameAsset = LegacyFrameMesh.LoadSynchronous(); // quadro inteiro: pedivela, selim e guidão já vêm nele
	}
	UStaticMesh* WheelAsset = WheelMesh.LoadSynchronous();
	UStaticMesh* SeatAsset = bLegacy ? nullptr : SeatMesh.LoadSynchronous();
	UStaticMesh* BarAsset = bLegacy ? nullptr : HandlebarMesh.LoadSynchronous();
	UStaticMesh* CrankAsset = bLegacy ? nullptr : CrankMesh.LoadSynchronous();
	UStaticMesh* PedalAsset = bLegacy ? nullptr : PedalMesh.LoadSynchronous();
	bHasCrank = CrankAsset && PedalAsset;
	bHasSteer = BarAsset != nullptr;

	Frame->SetStaticMesh(FrameAsset);
	Seat->SetStaticMesh(SeatAsset);
	Handlebar->SetStaticMesh(BarAsset);
	Crank->SetStaticMesh(bHasCrank ? CrankAsset : nullptr);
	PedalRight->SetStaticMesh(bHasCrank ? PedalAsset : nullptr);
	PedalLeft->SetStaticMesh(bHasCrank ? PedalAsset : nullptr);
	FrontWheel->SetStaticMesh(WheelAsset);
	RearWheel->SetStaticMesh(WheelAsset);

	// Tudo embaixo do LeanPivot fica na escala da bicicleta (cm do modelo x BikeScale).
	LeanPivot->SetRelativeScale3D(FVector(FMath::Max(BikeScale, 0.1f)));
	Frame->SetRelativeLocation(FVector(0.f, 0.f, FrameGroundOffset));
	Seat->SetRelativeLocation(FVector(0.f, 0.f, FrameGroundOffset - SeatDrop));

	// Direção: SteerAxis no pé da caixa de direção com o Z local no eixo inclinado (pitch + = topo para trás);
	// SteerOffset desfaz isso, então guidão e roda da frente usam as coordenadas do quadro.
	const FTransform AxisXf(FRotator(SteerTiltDegrees, 0.f, 0.f), SteerPivotLocation);
	SteerAxis->SetRelativeTransform(AxisXf);
	SteerYaw->SetRelativeRotation(FRotator::ZeroRotator);
	SteerOffset->SetRelativeTransform(AxisXf.Inverse());
	Handlebar->SetRelativeLocation(FVector(0.f, 0.f, FrameGroundOffset));

	// Pivô no eixo da roda; a malha da roda tem origem embaixo, então desce um raio.
	FrontPivot->SetRelativeLocation(FVector(FrontWheelX, 0.f, WheelRadius));
	RearPivot->SetRelativeLocation(FVector(RearWheelX, 0.f, WheelRadius));
	FrontWheel->SetRelativeLocation(FVector(0.f, 0.f, -WheelRadius));
	RearWheel->SetRelativeLocation(FVector(0.f, 0.f, -WheelRadius));

	// Pedivela: fase 0 = braço direito (+Y) para a frente; os pedais ficam nas pontas.
	CrankPivot->SetRelativeLocation(CrankPivotLocation);
	PedalRight->SetRelativeLocation(FVector(CrankLength, PedalSpindleY, 0.f));
	PedalLeft->SetRelativeLocation(FVector(-CrankLength, -PedalSpindleY, 0.f));
	UpdateCrank();
}

void AJRBike::UpdateCrank()
{
	// Andar para a frente leva o pedal da frente para baixo (+X para -Z) = pitch negativo, como as rodas.
	CrankPivot->SetRelativeRotation(FRotator(-Phase, 0.f, 0.f));
	// Pedais sempre nivelados: desfazem o giro do pedivela (o esquerdo está virado 180 graus em yaw).
	PedalRight->SetRelativeRotation(FRotator(Phase, 0.f, 0.f));
	PedalLeft->SetRelativeRotation(FRotator(-Phase, 180.f, 0.f));
}

void AJRBike::SetParkedCollision(bool bParked)
{
	Frame->SetCollisionEnabled(bParked ? ECollisionEnabled::QueryAndPhysics : ECollisionEnabled::NoCollision);
}

bool AJRBike::CanInteract_Implementation(AActor* InstigatorActor) const
{
	const AJRCharacter* Hero = Cast<AJRCharacter>(InstigatorActor);
	return Hero && !IsMounted() && !Hero->IsRidingBike();
}

void AJRBike::Interact_Implementation(AActor* InstigatorActor)
{
	Mount(Cast<AJRCharacter>(InstigatorActor));
}

FText AJRBike::GetInteractionText_Implementation() const
{
	return NSLOCTEXT("JogoResgate", "BikeMount", "Subir na bicicleta");
}

UAnimSequenceBase* AJRBike::FindPedalAnim(const AJRCharacter* Hero) const
{
	if (RideAnimOverride)
	{
		return RideAnimOverride.Get();
	}
	const USkeletalMeshComponent* MeshComp = Hero ? Hero->GetMesh() : nullptr;
	const USkeletalMesh* HeroMesh = MeshComp ? MeshComp->GetSkeletalMeshAsset() : nullptr;
	if (!HeroMesh)
	{
		return nullptr;
	}
	const FSoftObjectPath HeroPath(HeroMesh);
	for (const FJRBikeRiderAnim& Entry : RiderAnims)
	{
		if (!Entry.Mesh.IsNull() && Entry.Mesh.ToSoftObjectPath() == HeroPath)
		{
			if (UAnimSequenceBase* Anim = Entry.PedalAnim.LoadSynchronous())
			{
				return Anim;
			}
		}
	}
	for (const FJRBikeRiderAnim& Entry : RiderAnims)
	{
		UAnimSequenceBase* Anim = Entry.PedalAnim.LoadSynchronous();
		if (Anim && Anim->GetSkeleton() && Anim->GetSkeleton() == HeroMesh->GetSkeleton())
		{
			return Anim;
		}
	}
	return nullptr;
}

bool AJRBike::Mount(AJRCharacter* Hero)
{
	if (!Hero || IsMounted() || Hero->IsRidingBike())
	{
		return false;
	}
	UCharacterMovementComponent* Move = Hero->GetCharacterMovement();
	UCapsuleComponent* Capsule = Hero->GetCapsuleComponent();
	if (!Move || !Capsule)
	{
		return false;
	}
	Hero->HolsterWeaponInstant();
	Rider = Hero;
	Hero->SetMountedBike(this);

	SavedMaxWalkSpeed = Move->MaxWalkSpeed;
	SavedMaxAcceleration = Move->MaxAcceleration;
	SavedBraking = Move->BrakingDecelerationWalking;
	SavedGroundFriction = Move->GroundFriction;
	SavedBrakingFrictionFactor = Move->BrakingFrictionFactor;
	SavedRotationRate = Move->RotationRate;
	bSavedOrientToMovement = Move->bOrientRotationToMovement;
	bSavedUseControllerDesiredRotation = Move->bUseControllerDesiredRotation;
	bSavedUseControllerYaw = Hero->bUseControllerRotationYaw;
	SavedMeshLocation = Hero->GetMesh()->GetRelativeLocation();
	SavedMeshRotation = Hero->GetMesh()->GetRelativeRotation();

	// Câmera do ombro (a que está no SpringArm): FOV e afastamento pela velocidade.
	RiderCamera.Reset();
	TInlineComponentArray<UCameraComponent*> Cameras(Hero);
	for (UCameraComponent* Cam : Cameras)
	{
		if (Cam && Cast<USpringArmComponent>(Cam->GetAttachParent()))
		{
			RiderCamera = Cam;
			break;
		}
	}
	if (UCameraComponent* Cam = RiderCamera.Get())
	{
		SavedFOV = Cam->FieldOfView;
		SavedCameraLocation = Cam->GetRelativeLocation();
		SavedCameraRotation = Cam->GetRelativeRotation();
	}

	// O herói vai para cima da bicicleta, olhando para onde ela aponta.
	const float BikeYaw = GetActorRotation().Yaw;
	const float HalfHeight = Capsule->GetScaledCapsuleHalfHeight();
	Hero->SetActorLocationAndRotation(GetActorLocation() + FVector(0.f, 0.f, HalfHeight + 2.f), FRotator(0.f, BikeYaw, 0.f),
		false, nullptr, ETeleportType::TeleportPhysics);
	if (AController* C = Hero->GetController())
	{
		C->SetControlRotation(FRotator(-12.f, BikeYaw, 0.f));
	}
	Move->StopMovementImmediately();

	SetParkedCollision(false);
	AttachToComponent(Capsule, FAttachmentTransformRules::SnapToTargetNotIncludingScale);
	// A pedalada foi feita com o chão da bicicleta = origem da malha do herói (pés no chão em pé).
	SetActorRelativeLocation(FVector(0.f, 0.f, SavedMeshLocation.Z));
	SetActorRelativeRotation(FRotator::ZeroRotator);
	LeanPivot->SetRelativeLocationAndRotation(FVector::ZeroVector, FRotator::ZeroRotator);

	Speed = 0.f;
	Heading = BikeYaw;
	Steer = 0.f;
	LateralVel = 0.f;
	Lean = LeanVel = 0.f;
	Heave = HeaveVel = 0.f;
	Pitch = PitchVel = 0.f;
	Roughness = 0.f;
	bPedaling = bSkidding = false;
	bWasFalling = false;
	LastActorZ = Hero->GetActorLocation().Z;
	CamSpeedAlpha = 0.f;

	// Ordem do quadro: controle (entrada) -> bicicleta -> CharacterMovement.
	InputTickSource = Hero->GetController();
	if (AActor* Src = InputTickSource.Get())
	{
		AddTickPrerequisiteActor(Src);
	}
	Move->AddTickPrerequisiteActor(this);

	UAnimSequenceBase* Pedal = FindPedalAnim(Hero);
	UAnimSequenceBase* Pose = Pedal ? Pedal : Hero->GetDrivingAnim();
	bPedalAnimSynced = Pedal != nullptr;
	ActiveMeshOffset = Pedal ? RiderMeshOffset : DrivingAnimMeshOffset;
	PedalAnimLength = Pose ? Pose->GetPlayLength() : 0.f;
	PedalMontage.Reset();
	UAnimInstance* AnimInst = Hero->GetMesh()->GetAnimInstance();
	if (AnimInst && Pose)
	{
		AnimInst->StopSlotAnimation(0.1f, Hero->GetUpperBodySlotName());
		UAnimMontage* M = AnimInst->PlaySlotAnimationAsDynamicMontage(Pose, Hero->GetFullBodySlotName(), 0.25f, 0.25f, 1.f, 100000);
		if (M && bPedalAnimSynced)
		{
			// A posição da montagem segue a fase do pedivela (UpdateRiderPose): sem deriva entre pernas e pedais.
			AnimInst->Montage_SetPlayRate(M, 0.f);
		}
		PedalMontage = M;
	}
	if (!Pedal)
	{
		UE_LOG(LogJR, Warning, TEXT("%s: sem pedalada para %s (rode tools/unreal/setup_bike_anim.py); usando DrivingAnim."),
			*GetName(), *GetNameSafe(Hero->GetMesh()->GetSkeletalMeshAsset()));
	}
	UpdateRiderPose(Hero);
	SetActorTickEnabled(true);
	return true;
}

void AJRBike::RestoreRider(AJRCharacter* Hero)
{
	if (UCharacterMovementComponent* Move = Hero->GetCharacterMovement())
	{
		Move->MaxWalkSpeed = SavedMaxWalkSpeed;
		Move->MaxAcceleration = SavedMaxAcceleration;
		Move->BrakingDecelerationWalking = SavedBraking;
		Move->GroundFriction = SavedGroundFriction;
		Move->BrakingFrictionFactor = SavedBrakingFrictionFactor;
		Move->RotationRate = SavedRotationRate;
		Move->bOrientRotationToMovement = bSavedOrientToMovement;
		Move->bUseControllerDesiredRotation = bSavedUseControllerDesiredRotation;
		Move->RemoveTickPrerequisiteActor(this);
		// Descendo andando: sai no máximo na velocidade de andar.
		Move->Velocity = Move->Velocity.GetClampedToMaxSize2D(SavedMaxWalkSpeed);
	}
	if (AActor* Src = InputTickSource.Get())
	{
		RemoveTickPrerequisiteActor(Src);
	}
	InputTickSource.Reset();
	Hero->bUseControllerRotationYaw = bSavedUseControllerYaw;
	Hero->GetMesh()->SetRelativeLocationAndRotation(SavedMeshLocation, SavedMeshRotation);
	if (UCameraComponent* Cam = RiderCamera.Get())
	{
		Cam->SetFieldOfView(SavedFOV);
		Cam->SetRelativeLocationAndRotation(SavedCameraLocation, SavedCameraRotation);
	}
	RiderCamera.Reset();
	if (UAnimInstance* AnimInst = Hero->GetMesh()->GetAnimInstance())
	{
		AnimInst->StopSlotAnimation(0.2f, Hero->GetFullBodySlotName());
	}
	PedalMontage.Reset();
	Hero->SetMountedBike(nullptr);
	Rider.Reset();
}

void AJRBike::Dismount()
{
	AJRCharacter* Hero = Rider.Get();
	if (!Hero)
	{
		return;
	}
	RestoreRider(Hero);
	SetActorTickEnabled(false);
	DetachFromActor(FDetachmentTransformRules::KeepWorldTransform);
	// Estaciona do lado do herói (direita; se tiver parede, esquerda; senão fica embaixo dele mesmo).
	const float HeroYaw = Hero->GetActorRotation().Yaw;
	const FVector Right = FRotator(0.f, HeroYaw, 0.f).RotateVector(FVector(0.f, 1.f, 0.f));
	const FVector HeroLoc = Hero->GetActorLocation();
	FVector Spot = HeroLoc;
	FCollisionQueryParams Params(SCENE_QUERY_STAT(JRBikePark), false, this);
	Params.AddIgnoredActor(Hero);
	const FCollisionShape Probe = FCollisionShape::MakeSphere(35.f);
	for (const float Side : {1.f, -1.f})
	{
		FHitResult Hit;
		const FVector Try = HeroLoc + Right * (Side * 80.f);
		if (!GetWorld()->SweepSingleByChannel(Hit, HeroLoc, Try, FQuat::Identity, ECC_WorldStatic, Probe, Params))
		{
			Spot = Try;
			break;
		}
	}
	PlaceParked(Spot, HeroYaw, Hero);
}

void AJRBike::PlaceParked(const FVector& Near, float Yaw, const AActor* Ignore)
{
	FCollisionQueryParams Params(SCENE_QUERY_STAT(JRBikeGround), false, this);
	if (Ignore)
	{
		Params.AddIgnoredActor(Ignore);
	}
	FVector Ground = Near - FVector(0.f, 0.f, 90.f);
	FHitResult Hit;
	if (GetWorld()->LineTraceSingleByChannel(Hit, Near + FVector(0.f, 0.f, 60.f), Near - FVector(0.f, 0.f, 600.f), ECC_Visibility, Params))
	{
		Ground = Hit.ImpactPoint;
	}
	SetActorLocationAndRotation(Ground, FRotator(0.f, Yaw, 0.f), false, nullptr, ETeleportType::TeleportPhysics);
	Speed = 0.f;
	Steer = 0.f;
	Lean = LeanVel = 0.f;
	Heave = HeaveVel = 0.f;
	Pitch = PitchVel = 0.f;
	SteerYaw->SetRelativeRotation(FRotator::ZeroRotator);
	LeanPivot->SetRelativeLocationAndRotation(FVector::ZeroVector, FRotator(0.f, 0.f, -ParkedLeanDegrees));
	SetParkedCollision(true);
}

float AJRBike::TraceWheelGround(const FVector& WheelGround, float& OutRoughness) const
{
	OutRoughness = 0.f;
	FCollisionQueryParams Params(SCENE_QUERY_STAT(JRBikeWheel), false, this);
	Params.bReturnPhysicalMaterial = true;
	if (const AJRCharacter* Hero = Rider.Get())
	{
		Params.AddIgnoredActor(Hero);
	}
	const FVector Up(0.f, 0.f, 1.f);
	FHitResult Hit;
	if (!GetWorld()->LineTraceSingleByChannel(Hit, WheelGround + Up * (SuspensionTravel + 40.f),
		WheelGround - Up * (SuspensionTravel + 60.f), ECC_Visibility, Params))
	{
		return -SuspensionTravel; // roda no ar: estica
	}
	const UPhysicalMaterial* PhysMat = Hit.PhysMaterial.Get();
	const UPrimitiveComponent* Comp = Hit.GetComponent();
	const UMaterialInterface* Mat = Comp ? Comp->GetMaterial(0) : nullptr;
	if ((PhysMat && HasKeyword(PhysMat->GetName(), RoughSurfaceKeywords)) || (Mat && HasKeyword(Mat->GetName(), RoughSurfaceKeywords)))
	{
		OutRoughness = 1.f;
	}
	else if (Comp && Comp->GetClass()->GetName().Contains(TEXT("Landscape")))
	{
		OutRoughness = LandscapeRoughness;
	}
	return FMath::Clamp(static_cast<float>(Hit.ImpactPoint.Z - WheelGround.Z), -SuspensionTravel, SuspensionTravel + 10.f);
}

void AJRBike::UpdateSuspension(AJRCharacter* Hero, float Dt)
{
	UCharacterMovementComponent* Move = Hero->GetCharacterMovement();
	const FTransform Base = Root->GetComponentTransform(); // chão da bicicleta, sem inclinação
	const float S = FMath::Max(BikeScale, 0.1f);
	const float WheelBase = FMath::Max((FrontWheelX - RearWheelX) * S, 10.f);
	float RoughF = 0.f;
	float RoughR = 0.f;
	const float HF = TraceWheelGround(Base.TransformPosition(FVector(FrontWheelX * S, 0.f, 0.f)), RoughF);
	const float HR = TraceWheelGround(Base.TransformPosition(FVector(RearWheelX * S, 0.f, 0.f)), RoughR);
	Roughness = FMath::FInterpTo(Roughness, FMath::Max(RoughF, RoughR), Dt, 4.f);

	// Meio-fio/degrau: o CharacterMovement sobe ou desce de uma vez; a bicicleta acompanha pela mola.
	const float Z = static_cast<float>(Hero->GetActorLocation().Z);
	const bool bFalling = Move && Move->IsFalling();
	if (!bFalling && !bWasFalling)
	{
		const float Dz = Z - LastActorZ;
		if (FMath::Abs(Dz) > 2.5f && FMath::Abs(Dz) < 60.f)
		{
			Heave -= Dz;
		}
	}
	if (bWasFalling && !bFalling)
	{
		HeaveVel -= FMath::Min(LastFallSpeed * LandingBounce, 320.f); // pancada da queda: comprime e quica
	}
	LastFallSpeed = bFalling && Move ? FMath::Max(0.f, static_cast<float>(-Move->Velocity.Z)) : 0.f;
	bWasFalling = bFalling;
	LastActorZ = Z;

	// Terra/grama: buraquinhos pela distância andada (cada roda o seu), mais fortes com velocidade.
	const float Bump = RoughBump * Roughness * FMath::Clamp(Speed / 700.f, 0.f, 1.f);
	const float TF = bFalling ? -SuspensionTravel * 0.3f : HF + Bump * FMath::PerlinNoise1D(Distance * 0.021f);
	const float TR = bFalling ? -SuspensionTravel * 0.3f : HR + Bump * FMath::PerlinNoise1D(Distance * 0.021f + 37.3f);
	const float HeaveTarget = 0.5f * (TF + TR);
	const float PitchTarget = FMath::RadiansToDegrees(FMath::Atan2(TF - TR, WheelBase)); // frente mais alta = nariz para cima
	Spring(Heave, HeaveVel, HeaveTarget, SuspensionStiffness, SuspensionDamping, Dt);
	Spring(Pitch, PitchVel, PitchTarget, SuspensionStiffness * 1.3f, SuspensionDamping * 1.2f, Dt);
	Heave = FMath::Clamp(Heave, -SuspensionTravel * 1.5f, SuspensionTravel * 1.5f);
	Pitch = FMath::Clamp(Pitch, -25.f, 25.f);
}

void AJRBike::UpdateRiderPose(AJRCharacter* Hero)
{
	// Bicicleta e herói inclinam/arfam juntos em volta do chão da bicicleta: mãos e pés não saem do lugar.
	const FQuat BodyRot = FRotator(Pitch, 0.f, Lean).Quaternion();
	LeanPivot->SetRelativeLocationAndRotation(FVector(0.f, 0.f, Heave), BodyRot);
	const FVector O = Root->GetRelativeLocation(); // chão da bicicleta no espaço da cápsula
	const FVector Local = SavedMeshLocation + ActiveMeshOffset - O;
	Hero->GetMesh()->SetRelativeLocationAndRotation(O + FVector(0.f, 0.f, Heave) + BodyRot.RotateVector(Local),
		BodyRot * SavedMeshRotation.Quaternion());

	UpdateCrank();
	USkeletalMeshComponent* MeshComp = Hero->GetMesh();
	UAnimInstance* AnimInst = MeshComp ? MeshComp->GetAnimInstance() : nullptr;
	if (!AnimInst || !bPedalAnimSynced || PedalAnimLength <= KINDA_SMALL_NUMBER)
	{
		return;
	}
	UAnimMontage* M = PedalMontage.Get();
	if (!M || !AnimInst->Montage_IsPlaying(M))
	{
		// Alguma reação de corpo inteiro tirou a pedalada: volta.
		UAnimSequenceBase* Pose = FindPedalAnim(Hero);
		M = Pose ? AnimInst->PlaySlotAnimationAsDynamicMontage(Pose, Hero->GetFullBodySlotName(), 0.2f, 0.25f, 1.f, 100000) : nullptr;
		if (M)
		{
			AnimInst->Montage_SetPlayRate(M, 0.f);
		}
		PedalMontage = M;
	}
	if (M)
	{
		const float Pos = FMath::Clamp(Phase / 360.f * PedalAnimLength, 0.f, PedalAnimLength - 1.e-3f);
		AnimInst->Montage_SetPosition(M, Pos);
	}
}

void AJRBike::UpdateCamera(float Dt)
{
	UCameraComponent* Cam = RiderCamera.Get();
	if (!Cam)
	{
		return;
	}
	const float SpeedAlpha = FMath::Clamp(Speed / FMath::Max(SprintRideSpeed, 1.f), 0.f, 1.f);
	CamSpeedAlpha = FMath::FInterpTo(CamSpeedAlpha, SpeedAlpha, Dt, 2.f);
	Cam->SetFieldOfView(SavedFOV + SpeedFOVBonus * CamSpeedAlpha);
	const float T = GetWorld()->GetTimeSeconds();
	const float Shake = RoughCameraShake * Roughness * FMath::Clamp(Speed / 600.f, 0.f, 1.f);
	const FVector Offset(-SpeedCameraPullBack * CamSpeedAlpha, 0.f, Shake * FMath::PerlinNoise1D(T * 13.f));
	const FRotator Wobble(Shake * 0.35f * FMath::PerlinNoise1D(T * 11.f + 5.f), 0.f, Shake * 0.25f * FMath::PerlinNoise1D(T * 9.f + 11.f));
	Cam->SetRelativeLocationAndRotation(SavedCameraLocation + Offset, SavedCameraRotation + Wobble);
}

void AJRBike::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	AJRCharacter* Hero = Rider.Get();
	if (!Hero)
	{
		SetActorTickEnabled(false);
		return;
	}
	UCharacterMovementComponent* Move = Hero->GetCharacterMovement();
	if (!Move)
	{
		return;
	}
	const float Dt = FMath::Clamp(DeltaSeconds, 1.e-3f, 0.05f);

	// A bicicleta manda na velocidade: o CharacterMovement só anda, colide, sobe degrau e cai.
	Move->MaxWalkSpeed = SprintRideSpeed * 2.f;
	Move->MaxAcceleration = 0.f;
	Move->BrakingDecelerationWalking = 0.f;
	Move->GroundFriction = 0.f;
	Move->BrakingFrictionFactor = 0.f;
	Move->bOrientRotationToMovement = false;
	Move->bUseControllerDesiredRotation = false;
	Hero->bUseControllerRotationYaw = false;

	// Entrada do quadro (mundo, relativa à câmera); consumida aqui para o CharacterMovement não acelerar sozinho.
	FVector In = Hero->GetPendingMovementInputVector();
	In.Z = 0.f;
	Hero->ConsumeMovementInputVector();
	const float InMag = FMath::Min(static_cast<float>(In.Size()), 1.f);

	const bool bGround = Move->IsMovingOnGround();
	const bool bSprint = Hero->IsSprintHeld();
	const float TopSpeed = bSprint ? SprintRideSpeed : RideSpeed;
	const FVector V = Move->Velocity;
	const FVector V2(V.X, V.Y, 0.f);

	// Bateu em algo: a velocidade de verdade (depois da colisão) manda.
	FVector Fwd = FRotator(0.f, Heading, 0.f).Vector();
	const float MeasuredFwd = static_cast<float>(FVector::DotProduct(V2, Fwd));
	if (bGround && MeasuredFwd < Speed - 30.f)
	{
		Speed = FMath::Max(0.f, MeasuredFwd);
	}

	float Throttle = 0.f;
	float BrakeIn = 0.f;
	float SteerTarget = 0.f;
	float StandingTurn = 0.f;
	if (InMag > 0.15f)
	{
		const float Delta = FMath::FindDeltaAngleDegrees(Heading, static_cast<float>(In.Rotation().Yaw));
		if (FMath::Abs(Delta) > 125.f && Speed > 20.f)
		{
			BrakeIn = InMag; // puxando para trás: freio
		}
		else if (FMath::Abs(Delta) <= 125.f)
		{
			Throttle = InMag * FMath::Clamp(1.3f - FMath::Abs(Delta) / 120.f, 0.35f, 1.f);
			SteerTarget = Delta * SteerResponse;
		}
		// Devagar/parada: dá para virar empurrando (sem isso a bicicleta parada não vira).
		const float Assist = 1.f - FMath::Clamp(Speed / 150.f, 0.f, 1.f);
		if (Assist > 0.f && BrakeIn <= 0.f)
		{
			StandingTurn = FMath::Clamp(Delta, -StandingTurnRate * Dt, StandingTurnRate * Dt) * Assist;
		}
	}
	const float MaxSteer = FMath::Lerp(MaxSteerLowSpeed, MaxSteerHighSpeed, FMath::Clamp(Speed / FMath::Max(SprintRideSpeed, 1.f), 0.f, 1.f));
	Steer = FMath::FInterpTo(Steer, FMath::Clamp(SteerTarget, -MaxSteer, MaxSteer), Dt, SteerSpeed);

	// Para a frente: pedalada em pulsos (2 por volta, pico com o pedivela na horizontal), roda livre, freio, ladeira.
	float Accel = 0.f;
	bPedaling = false;
	bSkidding = false;
	if (bGround)
	{
		if (Throttle > 0.f && Speed < TopSpeed * 1.04f)
		{
			bPedaling = true;
			const float Stroke = (1.f - PedalPulse) + PedalPulse * FMath::Abs(FMath::Cos(FMath::DegreesToRadians(Phase))) * (UE_PI * 0.5f);
			const float Ratio = Speed / FMath::Max(TopSpeed, 1.f);
			const float Ratio2 = Ratio * Ratio;
			Accel += (bSprint ? SprintPedalAcceleration : PedalAcceleration) * Throttle * Stroke * FMath::Max(0.f, 1.f - Ratio2 * Ratio2);
		}
		if (Speed > 1.f)
		{
			Accel -= RollingDecel + AirDrag * Speed * Speed;
		}
		if (BrakeIn > 0.f)
		{
			Accel -= BrakeDecel * BrakeIn;
			bSkidding = BrakeIn > 0.5f && Speed > SkidMinSpeed;
		}
		const FFindFloorResult& Floor = Move->CurrentFloor;
		if (Floor.IsWalkableFloor())
		{
			const float SlopeSin = static_cast<float>(-FVector::DotProduct(Floor.HitResult.ImpactNormal, Fwd)); // subindo > 0
			Accel -= JRGravity * SlopeGravityScale * SlopeSin;
		}
	}
	else
	{
		Accel -= AirDrag * Speed * Speed;
	}
	Speed = FMath::Max(0.f, Speed + Accel * Dt);
	if (Speed < 4.f && Throttle <= 0.f)
	{
		Speed = 0.f;
	}

	// Curva: modelo cinemático (taxa = v / entre-eixos x tan(esterço)); derrapando gira um pouco mais.
	const float WheelBase = FMath::Max((FrontWheelX - RearWheelX) * FMath::Max(BikeScale, 0.1f), 10.f);
	float YawRateDeg = bGround ? FMath::RadiansToDegrees(Speed / WheelBase * FMath::Tan(FMath::DegreesToRadians(Steer))) : 0.f;
	if (bSkidding)
	{
		YawRateDeg *= 1.2f;
	}
	YawRateDeg = FMath::Clamp(YawRateDeg, -TurnRateDegrees, TurnRateDegrees);
	Heading = FMath::UnwindDegrees(Heading + YawRateDeg * Dt + StandingTurn);
	Fwd = FRotator(0.f, Heading, 0.f).Vector();
	const FVector Right = FRotator(0.f, Heading + 90.f, 0.f).Vector();
	Hero->SetActorRotation(FRotator(0.f, Heading, 0.f));

	// De lado quase não escorrega: a bicicleta vai para onde a roda aponta (derrapando, solta mais).
	LateralVel = static_cast<float>(FVector::DotProduct(V2, Right));
	LateralVel = FMath::FInterpTo(LateralVel, 0.f, Dt, bSkidding ? SkidGrip : LateralGrip);
	Move->Velocity = Fwd * Speed + Right * LateralVel + FVector(0.f, 0.f, V.Z);
	Distance += Speed * Dt;

	// Rodas: ângulo = distância / raio (andar para +X gira o topo da roda para a frente = pitch negativo).
	const float WheelR = FMath::Max(WheelRadius * FMath::Max(BikeScale, 0.1f), 1.f);
	const float Spin = Speed * Dt / WheelR * (180.f / UE_PI);
	FrontWheelAngle = FMath::Fmod(FrontWheelAngle + Spin, 360.f);
	if (!bSkidding)
	{
		RearWheelAngle = FMath::Fmod(RearWheelAngle + Spin, 360.f); // freio forte trava a de trás
	}
	FrontPivot->SetRelativeRotation(FRotator(-FrontWheelAngle, 0.f, 0.f));
	RearPivot->SetRelativeRotation(FRotator(-RearWheelAngle, 0.f, 0.f));
	if (bHasSteer)
	{
		SteerYaw->SetRelativeRotation(FRotator(0.f, FMath::Clamp(Steer, -MaxVisualSteer, MaxVisualSteer), 0.f));
	}

	// Pedivela: cadência pela velocidade; sem pedalar vai para a horizontal e para (roda livre).
	if (bPedaling)
	{
		const float Cadence = FMath::Clamp(Speed / FMath::Max(DistancePerCrankTurn, 1.f), MinCadence, MaxCadence);
		Phase += Cadence * 360.f * Dt;
	}
	else
	{
		Phase = FMath::FInterpTo(Phase, FMath::RoundToFloat(Phase / 180.f) * 180.f, Dt, 3.f);
	}
	Phase = FMath::Fmod(Phase, 360.f);
	if (Phase < 0.f)
	{
		Phase += 360.f;
	}

	// Inclinação física na curva: atan(a_lateral / g), com mola (atraso e uma leve sobra).
	const float LateralAccel = Speed * FMath::DegreesToRadians(YawRateDeg);
	const float LeanTarget = bGround ? FMath::Clamp(FMath::RadiansToDegrees(FMath::Atan(LateralAccel / JRGravity)) * LeanScale, -MaxLeanDegrees, MaxLeanDegrees) : Lean;
	Spring(Lean, LeanVel, LeanTarget, LeanStiffness, LeanDamping, Dt);
	Lean = FMath::Clamp(Lean, -MaxLeanDegrees * 1.2f, MaxLeanDegrees * 1.2f);

	UpdateSuspension(Hero, Dt);
	UpdateRiderPose(Hero);
	UpdateCamera(Dt);
}

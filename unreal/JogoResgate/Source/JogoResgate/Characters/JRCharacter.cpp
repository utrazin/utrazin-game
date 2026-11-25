// Copyright utrazin. All Rights Reserved.

#include "Characters/JRCharacter.h"
#include "Gameplay/JRBike.h" // [A-097]
#include "Animation/AnimInstance.h"
#include "Animation/AnimMontage.h"
#include "Animation/AnimSequenceBase.h"
#include "Camera/CameraComponent.h"
#include "Camera/CameraTypes.h"
#include "Camera/PlayerCameraManager.h"
#include "Characters/JRCharacterDefinition.h"
#include "Combat/JRHealthComponent.h"
#include "Combat/JRWeaponComponent.h"
#include "Combat/JRWeaponDefinition.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Core/JRGameMode.h"
#include "Core/JRPlayerController.h"
#include "FX/JRDamageFXComponent.h"
#include "FX/JRInteractionCameraComponent.h"
#include "FX/JRFXSubsystem.h"   // [A-073]
#include "FX/JRGameFeel.h"      // [A-073]
#include "Gameplay/JRPickup.h"  // [A-073] só leitura: qual item está sendo pego
#include "EngineUtils.h"        // [A-073] TActorIterator
#include "Engine/Engine.h"      // [A-073] aviso na tela (diagnóstico do pegar)
#include "Sound/SoundBase.h"
#include "EnhancedInputComponent.h"
#include "EnhancedInputSubsystems.h"
#include "EnhancedPlayerInput.h"
#include "Engine/LocalPlayer.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/SpringArmComponent.h"
#include "InputActionValue.h"
#include "Interactions/JRInteractionComponent.h"
#include "Materials/MaterialInterface.h"
#include "Engine/OverlapResult.h"
#include "Engine/StaticMesh.h"
#include "InputCoreTypes.h"
#include "Kismet/GameplayStatics.h"
#include "TimerManager.h"
#include "UI/JRHUD.h"

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
	// [A-069] base plana no teste de chão: menos tremido na beira de malhas finas (estrada que flutua ~22 cm
	// sobre o terreno, pedras e blockouts com colisão pela malha). Degrau e rampa máximos ficam no padrão
	// (MaxStepHeight 45 cm, WalkableFloorAngle 44,76 graus): o degrau da estrada (22 cm) cabe neles.
	Move->bUseFlatBaseForFloorChecks = true;

	SpringArm = CreateDefaultSubobject<USpringArmComponent>(TEXT("SpringArm"));
	SpringArm->SetupAttachment(RootComponent);
	SpringArm->TargetArmLength = DefaultArmLength;
	SpringArm->SocketOffset = FVector(0.f, 45.f, 45.f);
	SpringArm->bUsePawnControlRotation = true;
	SpringArm->bEnableCameraLag = false; // lag + física causava tremido
	SpringArm->ProbeSize = 20.f;         // [A-065] era 12: perto do chão o plano de corte da câmera entrava no terreno

	Camera = CreateDefaultSubobject<UCameraComponent>(TEXT("Camera"));
	Camera->SetupAttachment(SpringArm, USpringArmComponent::SocketName);

	HealthComponent = CreateDefaultSubobject<UJRHealthComponent>(TEXT("HealthComponent"));
	WeaponComponent = CreateDefaultSubobject<UJRWeaponComponent>(TEXT("WeaponComponent"));
	InteractionComponent = CreateDefaultSubobject<UJRInteractionComponent>(TEXT("InteractionComponent"));
	InventoryComponent = CreateDefaultSubobject<UJRInventoryComponent>(TEXT("InventoryComponent"));
	DamageFXComponent = CreateDefaultSubobject<UJRDamageFXComponent>(TEXT("DamageFXComponent"));
	DamageFXComponent->SetBloodType(EJRBloodType::Human);
	InteractionCamera = CreateDefaultSubobject<UJRInteractionCameraComponent>(TEXT("InteractionCamera"));

	WeaponMesh = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("WeaponMesh"));
	WeaponMesh->SetupAttachment(GetMesh(), TEXT("hand_r"));
	WeaponMesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	WeaponMesh->SetGenerateOverlapEvents(false);
	WeaponMesh->SetVisibility(false);

	MeleeMesh = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("MeleeMesh"));
	MeleeMesh->SetupAttachment(GetMesh(), TEXT("hand_r"));
	MeleeMesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	MeleeMesh->SetGenerateOverlapEvents(false);
	MeleeMesh->SetVisibility(false);
}

void AJRCharacter::BeginPlay()
{
	Super::BeginPlay();
	GetCharacterMovement()->MaxWalkSpeed = WalkSpeed;
	// [A-073] peso ao andar: arranque e parada menos secos (0 = mantém o Blueprint)
	if (MoveMaxAcceleration > 0.f)
	{
		GetCharacterMovement()->MaxAcceleration = MoveMaxAcceleration;
	}
	if (MoveBrakingDeceleration > 0.f)
	{
		GetCharacterMovement()->BrakingDecelerationWalking = MoveBrakingDeceleration;
	}
	// Encaixes vindos do Blueprint (reserva quando Pistol/Shotgun/MeleeGripTransform estão vazios).
	WeaponMeshBaseRelative = WeaponMesh->GetRelativeTransform();
	MeleeMeshBaseRelative = MeleeMesh->GetRelativeTransform();
	MeleeMesh->SetRelativeTransform(GetGripFor(EJRWeaponSlot::Melee));
	WeaponComponent->SetMuzzleComponent(WeaponMesh);
	Camera->SetFieldOfView(BaseFOV);
	HealthComponent->OnDeath.AddDynamic(this, &AJRCharacter::HandleDeath);
	HealthComponent->OnHealthChanged.AddDynamic(this, &AJRCharacter::HandleHealthChanged);
	WeaponComponent->OnWeaponFired.AddDynamic(this, &AJRCharacter::HandleWeaponFired);
	WeaponComponent->OnReloadStateChanged.AddDynamic(this, &AJRCharacter::HandleReloadStateChanged);
	// Ergue/abaixa a pistola conforme mira e tiro (sem Tick).
	GetWorldTimerManager().SetTimer(UpperBodyTimer, this, &AJRCharacter::UpdateUpperBody, 0.05f, true, 0.2f);
	if (bStartWithWeaponEquipped)
	{
		bOwnPistol = true;
		CurrentSlot = EJRWeaponSlot::Pistol;
		bWeaponEquipped = true;
		WeaponComponent->SwitchDefinitionKeepAmmo(PistolDefinition.Get());
	}
	UpdateWeaponVisuals();
}

void AJRCharacter::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
	// Nunca deixa o mundo em câmera lenta se o herói sair de cena com a roda aberta.
	if (bItemWheelOpen)
	{
		bItemWheelOpen = false;
		if (GetWorld())
		{
			UGameplayStatics::SetGlobalTimeDilation(this, WheelSavedTimeDilation);
		}
	}
	GetWorldTimerManager().ClearTimer(HealApplyTimer);
	GetWorldTimerManager().ClearTimer(HealEndTimer);
	// [Sensação de combate] nunca deixa o jogo "congelado" do abate corpo a corpo.
	EndHitStop();
	Super::EndPlay(EndPlayReason);
}

bool AJRCharacter::OwnsWeapon(EJRWeaponSlot Slot) const
{
	switch (Slot)
	{
	case EJRWeaponSlot::None: return true;
	case EJRWeaponSlot::Melee: return bOwnMelee;
	case EJRWeaponSlot::Pistol: return bOwnPistol;
	case EJRWeaponSlot::Shotgun: return bOwnShotgun;
	case EJRWeaponSlot::Sniper: return bOwnSniper;
	default: return false;
	}
}

void AJRCharacter::SetWeaponEquipped(bool bEquip)
{
	if (!bEquip)
	{
		SelectWeaponSlot(EJRWeaponSlot::None);
		return;
	}
	const EJRWeaponSlot Best = bOwnShotgun ? EJRWeaponSlot::Shotgun : bOwnSniper ? EJRWeaponSlot::Sniper : bOwnPistol ? EJRWeaponSlot::Pistol
		: bOwnMelee ? EJRWeaponSlot::Melee : EJRWeaponSlot::None;
	SelectWeaponSlot(Best);
}

EJRWeaponSlot AJRCharacter::NextOwnedSlot() const
{
	const EJRWeaponSlot Order[] = { EJRWeaponSlot::None, EJRWeaponSlot::Melee, EJRWeaponSlot::Pistol, EJRWeaponSlot::Shotgun,
		EJRWeaponSlot::Sniper };
	const int32 NumOrder = static_cast<int32>(UE_ARRAY_COUNT(Order));
	int32 Index = 0;
	for (int32 i = 0; i < NumOrder; ++i)
	{
		if (Order[i] == CurrentSlot)
		{
			Index = i;
		}
	}
	for (int32 Step = 1; Step <= NumOrder; ++Step)
	{
		const EJRWeaponSlot Candidate = Order[(Index + Step) % NumOrder];
		if (OwnsWeapon(Candidate))
		{
			return Candidate;
		}
	}
	return EJRWeaponSlot::None;
}

void AJRCharacter::UpdateWeaponVisuals()
{
	const bool bRanged = IsFirearmSlot(CurrentSlot);
	if (bRanged)
	{
		UStaticMesh* Want = CurrentSlot == EJRWeaponSlot::Shotgun && ShotgunStaticMesh ? ShotgunStaticMesh.Get()
			: CurrentSlot == EJRWeaponSlot::Sniper && SniperStaticMesh ? SniperStaticMesh.Get()
			: (PistolStaticMesh ? PistolStaticMesh.Get() : static_cast<UStaticMesh*>(WeaponMesh->GetStaticMesh()));
		if (Want && WeaponMesh->GetStaticMesh() != Want)
		{
			WeaponMesh->SetStaticMesh(Want);
		}
		// Encaixe de cada arma (A-056/A-057); o tranco do tiro é somado por cima em ApplyWeaponKickTransform.
		WeaponMesh->SetRelativeTransform(GetGripFor(CurrentSlot));
		KickBackNow = 0.f;
		KickPitchNow = 0.f;
		bKickApplied = false;
	}
	if (CurrentSlot == EJRWeaponSlot::Melee)
	{
		MeleeMesh->SetRelativeTransform(GetGripFor(EJRWeaponSlot::Melee));
	}
	WeaponMesh->SetVisibility(bRanged);
	MeleeMesh->SetVisibility(CurrentSlot == EJRWeaponSlot::Melee);
}

void AJRCharacter::SelectWeaponSlot(EJRWeaponSlot NewSlot)
{
	if (bWeaponTransition || NewSlot == CurrentSlot || !OwnsWeapon(NewSlot) || HealthComponent->GetHealth() <= 0.f)
	{
		return;
	}
	// Trocar de arma no meio da cura interrompe a cura (o item só é gasto se a vida já subiu).
	CancelHeal(false);
	WeaponComponent->CancelAll();
	bFireHeld = false;
	const bool bWasArmed = CurrentSlot != EJRWeaponSlot::None;
	CurrentSlot = NewSlot;
	bWeaponEquipped = IsFirearmSlot(NewSlot);
	if (bWeaponEquipped)
	{
		WeaponComponent->SwitchDefinitionKeepAmmo(GetDefinitionFor(NewSlot));
	}
	const bool bEquip = NewSlot != EJRWeaponSlot::None;
	UAnimInstance* Anim = GetMesh()->GetAnimInstance();
	// Trocar de uma arma para outra também usa a animação de puxar (a nova aparece no meio dela).
	UAnimSequenceBase* Clip = bEquip ? GetActiveEquipAnim() : (bWasArmed ? UnequipAnim.Get() : nullptr);
	if (!Anim || !Clip)
	{
		UpdateWeaponVisuals();
		return;
	}
	bWeaponTransition = true;
	Anim->StopSlotAnimation(0.15f, UpperBodySlot);
	const float Start = bEquip ? 0.f : FMath::Clamp(UnequipStartTime, 0.f, Clip->GetPlayLength() - 0.1f);
	Anim->PlaySlotAnimationAsDynamicMontage(Clip, UpperBodySlot, 0.2f, 0.35f, 1.f, 1, -1.f, Start);

	FTimerManager& Timers = GetWorldTimerManager();
	Timers.SetTimer(WeaponVisibilityTimer, FTimerDelegate::CreateWeakLambda(this, [this]()
	{
		UpdateWeaponVisuals();
	}), FMath::Max(0.01f, bEquip ? EquipShowWeaponTime : UnequipHideWeaponTime), false);
	const float Remaining = Clip->GetPlayLength() - Start;
	Timers.SetTimer(WeaponTransitionTimer, FTimerDelegate::CreateWeakLambda(this, [this]()
	{
		bWeaponTransition = false;
	}), FMath::Max(0.1f, Remaining - 0.35f), false);
}

void AJRCharacter::HolsterWeaponInstant()
{
	FTimerManager& Timers = GetWorldTimerManager();
	Timers.ClearTimer(WeaponVisibilityTimer);
	Timers.ClearTimer(WeaponTransitionTimer);
	if (UAnimInstance* Anim = GetMesh() ? GetMesh()->GetAnimInstance() : nullptr)
	{
		Anim->StopSlotAnimation(0.f, UpperBodySlot);
	}
	CancelHeal(false);
	WeaponComponent->CancelAll();
	bFireHeld = false;
	bWeaponTransition = false;
	CurrentSlot = EJRWeaponSlot::None;
	bWeaponEquipped = false;
	UpdateWeaponVisuals();
}

void AJRCharacter::GrantWeapon(EJRWeaponSlot Slot, bool bEquipNow)
{
	switch (Slot)
	{
	case EJRWeaponSlot::Melee: bOwnMelee = true; break;
	case EJRWeaponSlot::Pistol: bOwnPistol = true; break;
	case EJRWeaponSlot::Sniper:
		bOwnSniper = true;
		WeaponComponent->AddReserveAmmo(10); // vem com algumas células
		break;
	case EJRWeaponSlot::Shotgun:
		bOwnShotgun = true;
		WeaponComponent->AddReserveAmmo(15); // vem com algumas células
		break;
	default: return;
	}
	if (bEquipNow)
	{
		bWeaponTransition = false;
		SelectWeaponSlot(Slot);
	}
}

void AJRCharacter::SetMoveSpeedMultiplier(float Multiplier)
{
	if (BaseWalkSpeed < 0.f)
	{
		BaseWalkSpeed = WalkSpeed;
		BaseSprintSpeed = SprintSpeed;
	}
	const float M = FMath::Clamp(Multiplier, 0.2f, 3.f);
	WalkSpeed = BaseWalkSpeed * M;
	SprintSpeed = BaseSprintSpeed * M;
	if (!bHealing && GetCharacterMovement())
	{
		GetCharacterMovement()->MaxWalkSpeed = bIsSprinting ? SprintSpeed : WalkSpeed;
	}
}

void AJRCharacter::JRArmas()
{
	GrantWeapon(EJRWeaponSlot::Melee, false);
	GrantWeapon(EJRWeaponSlot::Pistol, false);
	GrantWeapon(EJRWeaponSlot::Sniper, false);
	GrantWeapon(EJRWeaponSlot::Shotgun, true);
	WeaponComponent->AddReserveAmmo(120);
}

float AJRCharacter::PlayFullBodyAction(UAnimSequenceBase* InAnim, float PlayRate, float MaxDuration)
{
	UAnimInstance* Anim = GetMesh()->GetAnimInstance();
	if (!InAnim || !Anim)
	{
		return 0.f;
	}
	CancelHeal(false); // pegar do chão / abrir baú interrompe a cura
	WeaponComponent->CancelAll();
	bFireHeld = false;
	float Duration = InAnim->GetPlayLength() / FMath::Max(0.1f, PlayRate);
	if (MaxDuration > 0.f)
	{
		Duration = FMath::Min(Duration, MaxDuration);
	}
	Anim->StopSlotAnimation(0.1f, UpperBodySlot);
	Anim->PlaySlotAnimationAsDynamicMontage(InAnim, FullBodySlot, 0.2f, 0.3f, PlayRate, 1, Duration * PlayRate);
	GetCharacterMovement()->StopMovementImmediately();
	if (AController* C = GetController())
	{
		C->SetIgnoreMoveInput(true);
	}
	GetWorldTimerManager().SetTimer(ActionTimer, FTimerDelegate::CreateWeakLambda(this, [this]()
	{
		if (UAnimInstance* A = GetMesh()->GetAnimInstance())
		{
			A->StopSlotAnimation(0.3f, FullBodySlot);
		}
		if (AController* C2 = GetController())
		{
			C2->ResetIgnoreMoveInput();
		}
	}), FMath::Max(0.1f, Duration), false);
	return Duration;
}

void AJRCharacter::PickUpWeaponFromGround(EJRWeaponSlot Slot)
{
	// [A-073] (queixa: "a câmera troca, sem animação de pegar, ângulo ruim")
	// 1) o herói vira de frente para o item; 2) a câmera enquadra mão + item (3/4, lado livre de parede);
	// 3) o item some do chão e aparece na mão quando a mão chega nele (PickupGrabFraction), não no fim.
	AActor* Item = FindPickupBeingTaken();
	if (!PickupAnim)
	{
		UE_LOG(LogTemp, Warning, TEXT("[A-073] %s: PickupAnim vazio no Blueprint (rode setup_wave1.py): pegar sem animação"), *GetName());
	}
	if (Item)
	{
		FacePointSmooth(Item->GetActorLocation(), PickupTurnTime);
	}
	const float Duration = PlayFullBodyAction(PickupAnim, PickupPlayRate, PickupDuration);
	if (Duration <= 0.f)
	{
		GrantWeapon(Slot, true);
		PlayFeedback(0.12f, 0.f, -2.f);
		return;
	}
	InteractionCamera->PlayShot(EJRInteractionShot::PickupGround, Item, Duration); // [A-058][A-073] enquadra o item
#if !UE_BUILD_SHIPPING
	// [A-073] diagnóstico: se o AnimBlueprint não tem o nó Slot do corpo inteiro, a montage "toca" mas nada se mexe.
	FTimerHandle SlotCheckTimer;
	GetWorldTimerManager().SetTimer(SlotCheckTimer, FTimerDelegate::CreateWeakLambda(this, [this]()
	{
		const UAnimInstance* AnimNow = GetMesh()->GetAnimInstance();
		if (AnimNow && AnimNow->GetSlotNodeGlobalWeight(FullBodySlot) < 0.01f && GEngine)
		{
			const FString Msg = FString::Printf(TEXT("[A-073] O AnimBlueprint de %s não tem o Slot '%s': a animação de pegar não aparece."),
				*GetName(), *FullBodySlot.ToString());
			UE_LOG(LogTemp, Warning, TEXT("%s"), *Msg);
			GEngine->AddOnScreenDebugMessage(-1, 8.f, FColor::Orange, Msg);
		}
	}), 0.35f, false);
#endif
	const float GrabAt = FMath::Clamp(Duration * PickupGrabFraction, 0.25f, FMath::Max(0.25f, FMath::Min(PickupGrantTime, 0.85f)));
	TWeakObjectPtr<AActor> WeakItem(Item);
	GetWorldTimerManager().SetTimer(PickupTimer, FTimerDelegate::CreateWeakLambda(this, [this, Slot, WeakItem]()
	{
		// [A-073] a mão chegou: o item sai do chão e vai para a mão (o JRPickup se apaga sozinho logo depois)
		if (AActor* TakenItem = WeakItem.Get())
		{
			TakenItem->SetActorHiddenInGame(true);
		}
		PlayFeedback(0.12f, 0.f, -2.f); // tier pequeno: "peguei"
		// A arma já "está na mão" ao levantar: sem animação de puxar.
		switch (Slot)
		{
		case EJRWeaponSlot::Melee: bOwnMelee = true; break;
		case EJRWeaponSlot::Pistol: bOwnPistol = true; break;
		case EJRWeaponSlot::Shotgun: bOwnShotgun = true; WeaponComponent->AddReserveAmmo(15); break;
		case EJRWeaponSlot::Sniper: bOwnSniper = true; WeaponComponent->AddReserveAmmo(10); break;
		default: break;
		}
		CurrentSlot = Slot;
		bWeaponEquipped = IsFirearmSlot(Slot);
		if (bWeaponEquipped)
		{
			WeaponComponent->SwitchDefinitionKeepAmmo(GetDefinitionFor(Slot));
		}
		UpdateWeaponVisuals();
	}), GrabAt, false);
}

AActor* AJRCharacter::FindPickupBeingTaken() const
{
	// [A-073] o JRPickup marca bTaken ANTES de chamar PickUpWeaponFromGround: o pego mais perto é ele.
	AActor* Best = nullptr;
	double BestDistSq = FMath::Square(300.0);
	const FVector Here = GetActorLocation();
	for (TActorIterator<AJRPickup> It(GetWorld()); It; ++It)
	{
		AJRPickup* Candidate = *It;
		if (!Candidate || !Candidate->IsTaken() || Candidate->IsHidden())
		{
			continue;
		}
		const double DistSq = FVector::DistSquared(Here, Candidate->GetActorLocation());
		if (DistSq < BestDistSq)
		{
			BestDistSq = DistSq;
			Best = Candidate;
		}
	}
	return Best;
}

void AJRCharacter::FacePointSmooth(const FVector& Point, float Seconds)
{
	const FVector ToPoint = (Point - GetActorLocation()).GetSafeNormal2D();
	if (ToPoint.IsNearlyZero())
	{
		return;
	}
	FaceTargetYaw = static_cast<float>(ToPoint.Rotation().Yaw);
	if (Seconds <= 0.f)
	{
		SetActorRotation(FRotator(0.f, FaceTargetYaw, 0.f));
		return;
	}
	FaceTimeLeft = Seconds;
	const float FaceStep = 1.f / 60.f;
	GetWorldTimerManager().SetTimer(FaceTimer, FTimerDelegate::CreateWeakLambda(this, [this, FaceStep]()
	{
		FaceTimeLeft -= FaceStep;
		FRotator Now = GetActorRotation();
		const float Remaining = FMath::FindDeltaAngleDegrees(static_cast<float>(Now.Yaw), FaceTargetYaw);
		// fração do giro que falta, distribuída no tempo que sobra (chega exatamente no fim)
		const float Portion = FaceTimeLeft <= 0.f ? 1.f : FMath::Clamp(FaceStep / (FaceTimeLeft + FaceStep), 0.f, 1.f);
		Now.Yaw += Remaining * Portion;
		SetActorRotation(FRotator(0.f, Now.Yaw, 0.f));
		if (FaceTimeLeft <= 0.f)
		{
			GetWorldTimerManager().ClearTimer(FaceTimer);
		}
	}), FaceStep, true);
}

void AJRCharacter::MeleeAttack()
{
	UAnimInstance* Anim = GetMesh()->GetAnimInstance();
	if (bMeleeBusy || bWeaponTransition || !Anim)
	{
		return;
	}
	const double Now = GetWorld()->GetTimeSeconds();
	MeleeComboIndex = (Now - LastMeleeTime < 1.2 && MeleeAnims.Num() > 0) ? (MeleeComboIndex + 1) % MeleeAnims.Num() : 0;
	LastMeleeTime = Now;
	bMeleeBusy = true;
	// Golpeia para onde a câmera olha.
	if (Controller)
	{
		SetActorRotation(FRotator(0.f, Controller->GetControlRotation().Yaw, 0.f));
	}
	if (MeleeAnims.IsValidIndex(MeleeComboIndex) && MeleeAnims[MeleeComboIndex])
	{
		Anim->PlaySlotAnimationAsDynamicMontage(MeleeAnims[MeleeComboIndex], UpperBodySlot, 0.08f, 0.2f, MeleePlayRate);
	}
	GetWorldTimerManager().SetTimer(MeleeTimer, this, &AJRCharacter::DoMeleeHit, MeleeHitDelay, false);
}

void AJRCharacter::DoMeleeHit()
{
	const FVector Fwd = GetActorForwardVector();
	const FVector Center = GetActorLocation() + Fwd * (MeleeRange * 0.6f);
	TArray<FOverlapResult> Overlaps;
	FCollisionObjectQueryParams Objects;
	Objects.AddObjectTypesToQuery(ECC_Pawn);
	Objects.AddObjectTypesToQuery(ECC_PhysicsBody);
	Objects.AddObjectTypesToQuery(ECC_WorldDynamic);
	FCollisionQueryParams Params(SCENE_QUERY_STAT(JRMelee), false, this);
	GetWorld()->OverlapMultiByObjectType(Overlaps, Center, FQuat::Identity, Objects, FCollisionShape::MakeSphere(MeleeRadius), Params);
	TSet<AActor*> Done;
	bool bAnyKill = false;
	bool bAnyHit = false; // [A-073]
	for (const FOverlapResult& O : Overlaps)
	{
		AActor* Other = O.GetActor();
		if (!Other || Done.Contains(Other))
		{
			continue;
		}
		Done.Add(Other);
		FHitResult Hit;
		// [Sensação de combate] ponto do corpo virado para o herói: o sangue e a ferida saem ali.
		if (!UJRDamageFXComponent::FindBodyHit(Other, GetActorLocation(), -0.2f, 0.8f, Hit))
		{
			Hit.ImpactPoint = Other->GetActorLocation();
			Hit.Location = Hit.ImpactPoint;
		}
		const UJRHealthComponent* OtherHealth = Other->FindComponentByClass<UJRHealthComponent>();
		const bool bOtherAlive = OtherHealth && !OtherHealth->IsDead();
		const float Mult = (GetFuryRemaining() > 0.f ? FuryDamageMultiplier : 1.f)
			* (WeaponComponent ? WeaponComponent->GetUpgradeDamageMultiplier() : 1.f); // [Remap F1]
		UGameplayStatics::ApplyPointDamage(Other, MeleeDamage * Mult, Fwd, Hit, GetController(), this, nullptr);
		if (bOtherAlive)
		{
			const bool bKilled = OtherHealth->IsDead();
			WeaponComponent->NotifyHitConfirmed(bKilled);
			// [A-073] tiers: acerto = médio (0,3), abate = grande moderado (0,45). Era 0,2 / 0,35.
			AddCameraTrauma(bKilled ? 0.45f : 0.3f);
			bAnyKill |= bKilled;
			bAnyHit = true;
		}
		if (ACharacter* OtherChar = Cast<ACharacter>(Other))
		{
			OtherChar->LaunchCharacter(Fwd * MeleeKnockback + FVector(0.f, 0.f, 150.f), true, false);
		}
		if (UPrimitiveComponent* Comp = O.GetComponent())
		{
			if (Comp->IsSimulatingPhysics())
			{
				Comp->AddImpulse(Fwd * MeleeKnockback * Comp->GetMass());
			}
		}
	}
	GetWorldTimerManager().SetTimer(MeleeTimer, FTimerDelegate::CreateWeakLambda(this, [this]()
	{
		bMeleeBusy = false;
	}), FMath::Max(0.05f, MeleeCooldown - MeleeHitDelay), false);
	if (bAnyKill)
	{
		StartHitStop(); // "congelada" curtinha no abate: dá peso ao golpe
		FOVPulsePending -= 1.5f; // [A-073] "soco" de zoom curtinho no abate
	}
	else if (bAnyHit)
	{
		StartHitStopFor(MeleeHitStop); // [A-073] acerto sem matar também "pega" (antes: nada)
	}
}

void AJRCharacter::ActivateFury(float Seconds)
{
	WeaponComponent->SetBoost(FuryDamageMultiplier, FuryFireRateMultiplier);
	GetWorldTimerManager().SetTimer(FuryTimer, FTimerDelegate::CreateWeakLambda(this, [this]()
	{
		WeaponComponent->SetBoost(1.f, 1.f);
	}), FMath::Max(1.f, Seconds), false);
}

float AJRCharacter::GetFuryRemaining() const
{
	return GetWorldTimerManager().IsTimerActive(FuryTimer) ? GetWorldTimerManager().GetTimerRemaining(FuryTimer) : 0.f;
}

void AJRCharacter::HandleToggleWeapon(const FInputActionValue& Value)
{
	if (IsRidingBike()) // [A-097] de bicicleta: só anda, olha e desce (E)
	{
		return;
	}
	if (bItemWheelOpen)
	{
		// [A-059] Q com a roda aberta troca a aba (UpdateItemWheelInput); 1 / B continuam fechando sem trocar.
		const APlayerController* TogglePC = Cast<APlayerController>(GetController());
		if (!TogglePC || !TogglePC->IsInputKeyDown(EKeys::Q))
		{
			CancelItemWheel();
		}
		return;
	}
	SelectWeaponSlot(NextOwnedSlot());
}

bool AJRCharacter::WantsAimPose() const
{
	if (!bWeaponEquipped || bWeaponTransition || !GetActiveAimAnim() || bHealing)
	{
		return false;
	}
	return bAimHeld || bFireHeld || GetWorld()->GetTimeSeconds() - LastShotTime < AimLingerTime;
}

void AJRCharacter::PlayAimPose(float BlendIn)
{
	if (UAnimInstance* Anim = GetMesh()->GetAnimInstance())
	{
		AimMontage = Anim->PlaySlotAnimationAsDynamicMontage(GetActiveAimAnim(), UpperBodySlot, BlendIn, 0.3f, 1.f, 100000);
	}
}

void AJRCharacter::UpdateUpperBody()
{
	// Segurança: se o "soltar Tab" se perder (troca de contexto de input), a roda não fica presa em câmera lenta.
	if (bItemWheelOpen && ItemWheelAction)
	{
		const APlayerController* WheelPC = Cast<APlayerController>(GetController());
		const UEnhancedInputLocalPlayerSubsystem* InputSubsystem = WheelPC && WheelPC->GetLocalPlayer()
			? WheelPC->GetLocalPlayer()->GetSubsystem<UEnhancedInputLocalPlayerSubsystem>() : nullptr;
		const UEnhancedPlayerInput* PlayerInputObj = InputSubsystem ? InputSubsystem->GetPlayerInput() : nullptr;
		if (!WheelPC || (PlayerInputObj && !PlayerInputObj->GetActionValue(ItemWheelAction).Get<bool>()))
		{
			CloseItemWheel(false);
		}
	}
	UAnimInstance* Anim = GetMesh()->GetAnimInstance();
	if (!Anim)
	{
		return;
	}
	const bool bAlive = HealthComponent->GetHealth() > 0.f;
	if (!bAlive || Anim->IsSlotActive(FullBodySlot))
	{
		if (bAlive && Anim->IsSlotActive(UpperBodySlot))
		{
			Anim->StopSlotAnimation(0.2f, UpperBodySlot);
		}
		if (bAlive && IsFirstPersonActive())
		{
			// Primeira pessoa + corpo inteiro (pegar, baú): o corpo não gira junto com a câmera.
			bUseControllerRotationYaw = false;
			GetCharacterMovement()->bOrientRotationToMovement = false;
		}
		return;
	}
	const bool bWantAim = WantsAimPose();
	// Câmera sobre o ombro: o personagem fica de lado e a mira (centro da tela) livre.
	{
		const float Dt = 0.05f;
		const bool bCloseAim = bAimHeld && bWeaponEquipped;
		// [A-058] Curando: câmera chega sobre o ombro (sem travar o andar; a cura deixa andar devagar).
		const bool bCloseShoulder = bCloseAim || bHealing;
		float WantArm = bCloseAim ? AimArmLength : (bHealing ? HealArmLength : DefaultArmLength);
		for (const float ZoneArm : CameraZoneArms)
		{
			WantArm = FMath::Min(WantArm, ZoneArm); // [A-070] dentro de prédio a câmera fica perto
		}
		SpringArm->SocketOffset = FMath::VInterpTo(SpringArm->SocketOffset, bCloseShoulder ? AimShoulderOffset : ShoulderOffset, Dt, CameraBlendSpeed);
		SpringArm->TargetArmLength = FMath::FInterpTo(SpringArm->TargetArmLength, WantArm, Dt, CameraBlendSpeed);
	}
	// Mirando ou atirando, o personagem olha para onde a câmera aponta (o tiro sai para lá).
	// Em primeira pessoa o corpo sempre acompanha o yaw da câmera (menos saindo do carro).
	const bool bFaceCamera = bAimHeld || bWantAim || (IsFirstPersonActive() && !ExitingVehicle.IsValid());
	bUseControllerRotationYaw = bFaceCamera;
	GetCharacterMovement()->bOrientRotationToMovement = !bFaceCamera;

	if (bWeaponTransition || WeaponComponent->IsReloading())
	{
		return;
	}
	const bool bAimPlaying = AimMontage && Anim->Montage_IsPlaying(AimMontage);
	// Armado sem mirar: pose baixa com a mão fechada na arma (ArmedIdleAnim), se existir.
	const bool bIdlePlaying = IsArmedIdlePlaying();
	const bool bWantIdle = bWeaponEquipped && ArmedIdleAnim && !bWantAim && !bHealing;
	if (bWantAim && (!Anim->IsSlotActive(UpperBodySlot) || bIdlePlaying))
	{
		PlayAimPose(0.15f); // no mesmo slot: troca suave da pose baixa para a mira
	}
	else if (!bWantAim && bAimPlaying)
	{
		if (bWantIdle)
		{
			PlayArmedIdle(0.3f);
		}
		else
		{
			Anim->Montage_Stop(0.3f, AimMontage);
		}
		AimMontage = nullptr;
	}
	else if (bWantIdle && !Anim->IsSlotActive(UpperBodySlot))
	{
		PlayArmedIdle(0.25f);
	}
	else if (!bWantIdle && bIdlePlaying)
	{
		Anim->Montage_Stop(0.25f, ArmedIdleMontage);
		ArmedIdleMontage = nullptr;
	}
}

void AJRCharacter::HandleWeaponFired(const FVector& Start, const FVector& End)
{
	LastShotTime = GetWorld()->GetTimeSeconds();
	ApplyShotFeedback(); // coice da câmera e da arma, tremor (A-057)
	UAnimInstance* Anim = GetMesh()->GetAnimInstance();
	if (!Anim || !GetActiveAimAnim() || WeaponComponent->IsReloading())
	{
		return;
	}
	if (!(AimMontage && Anim->Montage_IsPlaying(AimMontage)) || !GetActiveFireAnim())
	{
		// Primeiro tiro com a arma abaixada: só ergue a arma (rápido).
		if (!Anim->IsSlotActive(UpperBodySlot) || IsArmedIdlePlaying())
		{
			PlayAimPose(0.08f);
		}
		return;
	}
	// O recuo começa e termina na pose de mira: ao acabar, a mira volta sem transição.
	UAnimMontage* Recoil = Anim->PlaySlotAnimationAsDynamicMontage(GetActiveFireAnim(), UpperBodySlot, 0.08f, 0.f);
	if (Recoil)
	{
		FOnMontageBlendingOutStarted Delegate;
		Delegate.BindUObject(this, &AJRCharacter::HandleRecoilBlendingOut);
		Anim->Montage_SetBlendingOutDelegate(Delegate, Recoil);
	}
}

void AJRCharacter::HandleRecoilBlendingOut(UAnimMontage* Montage, bool bInterrupted)
{
	if (!bInterrupted && WantsAimPose() && !WeaponComponent->IsReloading())
	{
		PlayAimPose(0.f);
	}
}

void AJRCharacter::HandleReloadStateChanged(bool bIsReloading)
{
	UAnimInstance* Anim = GetMesh()->GetAnimInstance();
	UAnimSequenceBase* ReloadClip = GetActiveReloadAnim();
	if (!bIsReloading || !ReloadClip || !Anim)
	{
		return; // a animação termina sozinha (morte/respawn param tudo)
	}
	Anim->StopSlotAnimation(0.1f, UpperBodySlot);
	float Rate = 1.f;
	const UJRWeaponDefinition* Def = WeaponComponent->GetDefinition();
	if (Def && Def->ReloadTime > 0.f && ReloadClip->GetPlayLength() > 0.f)
	{
		Rate = ReloadClip->GetPlayLength() / Def->ReloadTime;
	}
	Anim->PlaySlotAnimationAsDynamicMontage(ReloadClip, UpperBodySlot, 0.15f, 0.2f, Rate);
}

void AJRCharacter::HandleHealthChanged(UJRHealthComponent* Health, float NewHealth, float Delta)
{
	if (Delta < 0.f && NewHealth > 0.f)
	{
		// [Sensação de combate] tranco na câmera proporcional ao golpe.
		AddCameraTrauma(FMath::Clamp(-Delta / 40.f * DamageShake, 0.15f, 0.7f));
	}
	if (bHealing && Delta < 0.f && NewHealth > 0.f)
	{
		if (-Delta < HealInterruptDamage)
		{
			return; // arranhão: continua se curando (a reação de dano cortaria a animação)
		}
		CancelHeal(true); // golpe forte: interrompe e toca a reação normal
	}
	UAnimInstance* Anim = GetMesh()->GetAnimInstance();
	if (Delta >= 0.f || NewHealth <= 0.f || !HitReactAnim || !Anim || WeaponComponent->IsReloading() || bWeaponTransition)
	{
		return;
	}
	Anim->PlaySlotAnimationAsDynamicMontage(HitReactAnim, UpperBodySlot, 0.1f, 0.2f);
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
	if (MouseLookAction) { Input->BindAction(MouseLookAction, ETriggerEvent::Triggered, this, &AJRCharacter::HandleLook); }
	if (JumpAction)
	{
		Input->BindAction(JumpAction, ETriggerEvent::Started, this, &AJRCharacter::HandleJumpPressed); // [A-086] escalar ou pular
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
	if (ToggleWeaponAction) { Input->BindAction(ToggleWeaponAction, ETriggerEvent::Started, this, &AJRCharacter::HandleToggleWeapon); }
	if (ItemWheelAction)
	{
		Input->BindAction(ItemWheelAction, ETriggerEvent::Started, this, &AJRCharacter::HandleItemWheelPressed);
		Input->BindAction(ItemWheelAction, ETriggerEvent::Completed, this, &AJRCharacter::HandleItemWheelReleased);
	}
	if (HealAction) { Input->BindAction(HealAction, ETriggerEvent::Started, this, &AJRCharacter::HandleQuickHeal); }
	// Esc fecha a roda (no PIE o Esc também para o jogo; use o botão direito para cancelar no editor).
	FInputKeyBinding& EscBinding = static_cast<UInputComponent*>(Input)->BindKey(EKeys::Escape, IE_Pressed, this, &AJRCharacter::HandleEscapeKey);
	EscBinding.bConsumeInput = false;
	// [A-058] Roda do mouse: zoom da luneta do rifle (só age olhando pela luneta).
	FInputKeyBinding& ZoomInBinding = static_cast<UInputComponent*>(Input)->BindKey(EKeys::MouseScrollUp, IE_Pressed, this, &AJRCharacter::HandleScopeZoomIn);
	ZoomInBinding.bConsumeInput = false;
	FInputKeyBinding& ZoomOutBinding = static_cast<UInputComponent*>(Input)->BindKey(EKeys::MouseScrollDown, IE_Pressed, this, &AJRCharacter::HandleScopeZoomOut);
	ZoomOutBinding.bConsumeInput = false;
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
	FVector2D Axis = Value.Get<FVector2D>();
	if (ScopeAlpha > 0.f)
	{
		// [A-058] Luneta: o olhar fica mais lento na proporção do zoom (a mira não "voa").
		const float ScopeSens = FMath::Lerp(1.f, GetScopeFOV() / FMath::Max(1.f, BaseFOV) * ScopeLookScale, ScopeAlpha);
		Axis *= static_cast<double>(ScopeSens);
	}
	AddControllerYawInput(Axis.X);
	AddControllerPitchInput(Axis.Y);
	if (bItemWheelOpen)
	{
		FeedItemWheelCursor(); // a roda "rouba" o olhar: o cursor anda e a câmera fica parada
	}
}

void AJRCharacter::HandleSprint(const FInputActionValue& Value)
{
	bIsSprinting = Value.Get<bool>();
	if (bIsSprinting && bHealing)
	{
		CancelHeal(true); // correr interrompe a cura
	}
	GetCharacterMovement()->MaxWalkSpeed = bHealing ? WalkSpeed * HealMoveSpeedFactor : (bIsSprinting ? SprintSpeed : WalkSpeed);
}

void AJRCharacter::HandleAim(const FInputActionValue& Value)
{
	if (IsRidingBike()) // [A-097] de bicicleta: só anda, olha e desce (E)
	{
		return;
	}
	const bool bAim = Value.Get<bool>();
	if (bAim && bItemWheelOpen)
	{
		CancelItemWheel(); // botão direito / gatilho esquerdo cancela a roda (não mira)
		return;
	}
	bAimHeld = bAim;
	WeaponComponent->SetAiming(bAim);
	// Distância e ombro da câmera são suavizados em UpdateUpperBody.
}

void AJRCharacter::HandleFireStarted(const FInputActionValue& Value)
{
	if (IsRidingBike()) // [A-097] de bicicleta: só anda, olha e desce (E)
	{
		return;
	}
	if (bItemWheelOpen || bHealing || InteractionCamera->IsShotActive())
	{
		return; // roda aberta, mãos ocupadas com a bandagem ou cena de interação
	}
	if (CurrentSlot == EJRWeaponSlot::Melee && !bWeaponTransition)
	{
		MeleeAttack();
		return;
	}
	// Só atira com a arma na mão (e fora da animação de puxar/guardar).
	if (!bWeaponEquipped || bWeaponTransition)
	{
		return;
	}
	bFireHeld = true;
	WeaponComponent->StartFire();
}

void AJRCharacter::HandleFireStopped(const FInputActionValue& Value)
{
	bFireHeld = false;
	WeaponComponent->StopFire();
}

void AJRCharacter::HandleReload(const FInputActionValue& Value)
{
	if (IsRidingBike()) // [A-097] de bicicleta: só anda, olha e desce (E)
	{
		return;
	}
	if (bWeaponEquipped && !bWeaponTransition && !bHealing && !bItemWheelOpen)
	{
		WeaponComponent->StartReload();
	}
}

AJRBike* AJRCharacter::GetMountedBike() const
{
	return MountedBike.Get();
}

void AJRCharacter::SetMountedBike(AJRBike* Bike)
{
	MountedBike = Bike;
}

void AJRCharacter::HandleInteract(const FInputActionValue& Value)
{
	if (AJRBike* Bike = GetMountedBike()) // [A-097] E em cima da bicicleta = descer
	{
		Bike->Dismount();
		return;
	}
	if (bItemWheelOpen)
	{
		return;
	}
	if (InteractionComponent->TryInteract())
	{
		PlayFeedback(0.f, 0.f, -1.5f); // [A-073] resposta imediata ao E (pulso leve de zoom, sem tremor)
	}
}

void AJRCharacter::PlayExitVehicleSequence()
{
	PlayExitFromVehicle(nullptr, GetActorTransform());
}

void AJRCharacter::PlayExitFromVehicle(AActor* FromVehicle, const FTransform& SeatTransform)
{
	UAnimInstance* Anim = GetMesh()->GetAnimInstance();
	if (!ExitVehicleMontage || !Anim)
	{
		return;
	}
	if (FromVehicle)
	{
		// Coloca o personagem no banco (no chão, abaixo do banco), ignorando a colisão do carro
		// até a animação terminar de levá-lo para fora.
		const FVector Seat = SeatTransform.GetLocation();
		FCollisionQueryParams Params(SCENE_QUERY_STAT(JRSeatGround), false, FromVehicle);
		Params.AddIgnoredActor(this);
		FHitResult Hit;
		float GroundZ = Seat.Z - 60.f;
		if (GetWorld()->LineTraceSingleByChannel(Hit, Seat + FVector(0.f, 0.f, 50.f), Seat - FVector(0.f, 0.f, 500.f), ECC_Visibility, Params))
		{
			GroundZ = Hit.ImpactPoint.Z;
		}
		ExitingVehicle = FromVehicle;
		GetCapsuleComponent()->IgnoreActorWhenMoving(FromVehicle, true);
		// Sem isso o braço da câmera bate na carroceria e a câmera entra no carro.
		SpringArm->bDoCollisionTest = false;
		// O carro também precisa ignorar o personagem, senão a física "expulsa" o carro longe.
		if (UPrimitiveComponent* VehicleBody = Cast<UPrimitiveComponent>(FromVehicle->GetRootComponent()))
		{
			ExitVehiclePawnResponse = VehicleBody->GetCollisionResponseToChannel(ECC_Pawn);
			VehicleBody->SetCollisionResponseToChannel(ECC_Pawn, ECR_Ignore);
			VehicleBody->SetPhysicsLinearVelocity(FVector::ZeroVector);
			VehicleBody->SetPhysicsAngularVelocityInDegrees(FVector::ZeroVector);
		}
		const FRotator Yaw(0.f, SeatTransform.Rotator().Yaw, 0.f);
		SetActorLocationAndRotation(FVector(Seat.X, Seat.Y, GroundZ + GetCapsuleComponent()->GetScaledCapsuleHalfHeight()),
			Yaw, false, nullptr, ETeleportType::TeleportPhysics);
		bFPStableValid = false; // primeira pessoa: recomeça o ponto estável no banco
		if (AController* C = GetController())
		{
			C->SetControlRotation(Yaw);
		}
	}
	if (AController* C = GetController())
	{
		C->SetIgnoreMoveInput(true);
	}
	Anim->Montage_Play(ExitVehicleMontage);
	if (FromVehicle)
	{
		// [A-058] Sai do carro com um plano aberto de lado, partindo da câmera do carro.
		InteractionCamera->PlayShot(EJRInteractionShot::VehicleExit, nullptr, ExitVehicleMontage->GetPlayLength(), false, FromVehicle);
	}
	FOnMontageBlendingOutStarted BlendOutDelegate;
	BlendOutDelegate.BindUObject(this, &AJRCharacter::HandleExitBlendingOut);
	Anim->Montage_SetBlendingOutDelegate(BlendOutDelegate, ExitVehicleMontage);
	FOnMontageEnded EndDelegate;
	EndDelegate.BindUObject(this, &AJRCharacter::HandleMontageEnded);
	Anim->Montage_SetEndDelegate(EndDelegate, ExitVehicleMontage);
}

void AJRCharacter::HandleExitBlendingOut(UAnimMontage* Montage, bool bInterrupted)
{
	// A animação do Mixamo move o quadril para fora do carro; leva a cápsula até lá e corta a
	// montage na hora, para não haver "pulo" de volta ao banco.
	const FVector Pelvis = GetMesh()->GetBoneLocation(TEXT("pelvis"));
	const FVector Loc = GetActorLocation();
	SetActorLocation(FVector(Pelvis.X, Pelvis.Y, Loc.Z), false, nullptr, ETeleportType::TeleportPhysics);
	// A cápsula pulou para o quadril: o ponto estável da primeira pessoa recomeça (sem deslizar a câmera).
	bFPStableValid = false;
	if (UAnimInstance* Anim = GetMesh()->GetAnimInstance())
	{
		Anim->Montage_Stop(0.f, Montage);
	}
	SpringArm->bDoCollisionTest = true;
	if (AActor* Vehicle = ExitingVehicle.Get())
	{
		GetCapsuleComponent()->IgnoreActorWhenMoving(Vehicle, false);
		if (UPrimitiveComponent* VehicleBody = Cast<UPrimitiveComponent>(Vehicle->GetRootComponent()))
		{
			VehicleBody->SetCollisionResponseToChannel(ECC_Pawn, ExitVehiclePawnResponse);
		}
	}
	ExitingVehicle.Reset();
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
	// Troca de malha: mostra a cabeça antes (a primeira pessoa esconde de novo no próximo quadro).
	SetHeadHiddenForView(false);
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
	if (AJRBike* Bike = GetMountedBike()) // [A-097]
	{
		Bike->Dismount();
	}
	InteractionCamera->StopShot(true); // [A-058]
	CloseItemWheel(false);
	CancelHeal(false);
	WeaponComponent->CancelAll();
	if (UAnimInstance* Anim = GetMesh()->GetAnimInstance())
	{
		Anim->StopAllMontages(0.1f);
	}
	if (AController* C = GetController())
	{
		C->SetIgnoreMoveInput(true);
		C->SetIgnoreLookInput(true);
	}
	GetCharacterMovement()->DisableMovement();
	// Morto: a câmera volta para terceira pessoa (CalcCamera faz a transição) para ver o corpo.
	ApplyFirstPersonPitchLimits(false);
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
	CloseItemWheel(false);
	CancelHeal(false);
	HealthComponent->ResetHealth();
	if (UAnimInstance* Anim = GetMesh()->GetAnimInstance())
	{
		Anim->StopAllMontages(0.f);
	}
	bFPStableValid = false;
	ApplyFirstPersonPitchLimits(IsFirstPersonActive());
	GetCharacterMovement()->SetMovementMode(MOVE_Walking);
	if (AController* C = GetController())
	{
		C->ResetIgnoreInputFlags();
	}
}

// ---------------------------------------------------------------- Primeira pessoa

bool AJRCharacter::IsFirstPersonActive() const
{
	return bFirstPersonWanted && HealthComponent && HealthComponent->GetHealth() > 0.f;
}

void AJRCharacter::SetFirstPersonView(bool bEnable, bool bInstant)
{
	bFirstPersonWanted = bEnable;
	const bool bActiveNow = IsFirstPersonActive();
	if (bInstant)
	{
		FPBlendAlpha = bActiveNow ? 1.f : 0.f;
	}
	bFPStableValid = false;
	ApplyFirstPersonPitchLimits(bActiveNow);
	// Primeira pessoa: o corpo acompanha o yaw da câmera (pernas andam de lado/de costas).
	// Terceira pessoa: volta a virar para onde anda (UpdateUpperBody ajusta a mira a cada 0,05 s).
	const bool bFace = bActiveNow || bAimHeld;
	bUseControllerRotationYaw = bFace;
	GetCharacterMovement()->bOrientRotationToMovement = !bFace;
}

void AJRCharacter::ApplyFirstPersonPitchLimits(bool bFirstPerson)
{
	APlayerController* PC = Cast<APlayerController>(GetController());
	APlayerCameraManager* CamManager = nullptr;
	if (PC)
	{
		CamManager = PC->PlayerCameraManager;
	}
	if (!CamManager)
	{
		return;
	}
	if (!bSavedPitchLimits)
	{
		SavedPitchMin = CamManager->ViewPitchMin;
		SavedPitchMax = CamManager->ViewPitchMax;
		bSavedPitchLimits = true;
	}
	CamManager->ViewPitchMin = bFirstPerson ? FPPitchMin : SavedPitchMin;
	CamManager->ViewPitchMax = bFirstPerson ? FPPitchMax : SavedPitchMax;
}

void AJRCharacter::SetHeadHiddenForView(bool bHide)
{
	if (bHide == bHeadHidden)
	{
		return;
	}
	bHeadHidden = bHide;
	USkeletalMeshComponent* BodyMesh = GetMesh();
	if (!BodyMesh)
	{
		return;
	}
	for (const FName& BoneToHide : HiddenBones)
	{
		if (BoneToHide.IsNone() || BodyMesh->GetBoneIndex(BoneToHide) == INDEX_NONE)
		{
			continue;
		}
		if (bHide)
		{
			BodyMesh->HideBoneByName(BoneToHide, EPhysBodyOp::PBO_None);
		}
		else
		{
			BodyMesh->UnHideBoneByName(BoneToHide);
		}
	}
}

FVector AJRCharacter::ComputeFirstPersonEye(float DeltaTime, const FRotator& ViewRot)
{
	USkeletalMeshComponent* BodyMesh = GetMesh();
	// Referência do personagem (só yaw): a cabeça é medida nela para o ponto estável não depender de teleporte.
	const FTransform BodyFrame(FRotator(0.f, GetActorRotation().Yaw, 0.f), GetActorLocation());
	FVector HeadWorld = GetActorLocation() + FVector(0.f, 0.f, BaseEyeHeight);
	if (BodyMesh && BodyMesh->GetBoneIndex(FPHeadBone) != INDEX_NONE)
	{
		HeadWorld = BodyMesh->GetBoneLocation(FPHeadBone);
	}
	const FVector HeadLocal = BodyFrame.InverseTransformPosition(HeadWorld);
	if (!bFPStableValid)
	{
		FPStableLocal = HeadLocal;
		bFPStableValid = true;
	}
	// Ponto estável = cabeça suavizada: tira o balanço do passo, mas acompanha agachar/abaixar.
	FPStableLocal = FMath::VInterpTo(FPStableLocal, HeadLocal, DeltaTime, StabilizeSpeed);
	UAnimInstance* BodyAnim = BodyMesh ? BodyMesh->GetAnimInstance() : nullptr;
	const bool bBodyAction = ExitingVehicle.IsValid() || (BodyAnim && BodyAnim->IsSlotActive(FullBodySlot));
	const float StabAlpha = FMath::Clamp(bBodyAction ? FMath::Max(StabilizeAlpha, FullBodyStabilizeAlpha) : StabilizeAlpha, 0.f, 1.f);
	const FVector EyeLocal = FMath::Lerp(HeadLocal, FPStableLocal, StabAlpha);

	// Olhos à frente do rosto, no sentido do olhar; olhando para baixo vai um pouco mais à frente (vê os pés).
	const float ViewPitch = static_cast<float>(FRotator::NormalizeAxis(ViewRot.Pitch));
	const float LookDown = FMath::Clamp(-ViewPitch / 80.f, 0.f, 1.f);
	const FRotator ViewYawOnly(0.f, ViewRot.Yaw, 0.f);
	const FVector EyeShift = ViewYawOnly.RotateVector(EyeOffset + FVector(LookDownForwardOffset * LookDown, 0.f, 0.f));
	return BodyFrame.TransformPosition(EyeLocal) + EyeShift;
}

void AJRCharacter::CalcCamera(float DeltaTime, FMinimalViewInfo& OutResult)
{
	// Coice, tranco da arma, tremor e FOV andam aqui (uma vez por quadro, sem ligar o Tick do personagem).
	UpdateCombatFeel(DeltaTime);

	// Terceira pessoa: câmera do SpringArm (ombro). A primeira pessoa é misturada por cima dela.
	Super::CalcCamera(DeltaTime, OutResult);

	// [A-057] Terceira pessoa: batendo na parede a câmera chega perto na hora (nunca atravessa) e, ao sair,
	// volta suave (sem "estalo"); atraso vertical leve em pulos e degraus.
	if (SpringArm)
	{
		const FVector Pivot = SpringArm->GetComponentLocation();
		const FVector ArmVector = OutResult.Location - Pivot;
		const float ArmDist = static_cast<float>(ArmVector.Size());
		if (!bCamDistValid || ArmDist < SmoothedCamDist || CameraCollisionRecoverSpeed <= 0.f)
		{
			SmoothedCamDist = ArmDist;
			bCamDistValid = true;
		}
		else
		{
			SmoothedCamDist = FMath::FInterpTo(SmoothedCamDist, ArmDist, DeltaTime, CameraCollisionRecoverSpeed);
		}
		if (ArmDist > KINDA_SMALL_NUMBER)
		{
			OutResult.Location = Pivot + ArmVector * (SmoothedCamDist / ArmDist);
		}
		if (CameraVerticalLagSpeed > 0.f)
		{
			const double ActorZ = GetActorLocation().Z;
			if (!bCamZValid || FMath::Abs(SmoothedCamZ - ActorZ) > 150.0)
			{
				SmoothedCamZ = ActorZ; // teleporte/respawn: sem deslizar
				bCamZValid = true;
			}
			SmoothedCamZ = FMath::FInterpTo(SmoothedCamZ, ActorZ, static_cast<double>(DeltaTime), static_cast<double>(CameraVerticalLagSpeed));
			OutResult.Location.Z += FMath::Clamp(SmoothedCamZ - ActorZ, -30.0, 30.0);
		}
	}

	const float TargetAlpha = IsFirstPersonActive() ? 1.f : 0.f;
	if (FPBlendTime <= KINDA_SMALL_NUMBER)
	{
		FPBlendAlpha = TargetAlpha;
	}
	else
	{
		FPBlendAlpha = FMath::FInterpConstantTo(FPBlendAlpha, TargetAlpha, DeltaTime, 1.f / FPBlendTime);
	}
	// A cabeça some só quando a câmera já está chegando nela (metade da transição).
	// [A-086] cabeça e braços: visíveis de novo na luneta (a câmera usa a própria arma, que fica na mão) e nas
	// cenas de interação (outra câmera vê o corpo de fora)
	SetHeadHiddenForView(FPBlendAlpha > 0.5f && ScopeAlpha <= 0.f && !WantsScope()
		&& !(InteractionCamera && InteractionCamera->IsShotActive()));
	// [A-065] pivô da conferência final: o começo do braço da câmera (dentro da cápsula)
	const FVector SafetyPivot = SpringArm ? SpringArm->GetComponentLocation() : GetActorLocation();
	if (FPBlendAlpha <= 0.f)
	{
		bFPStableValid = false;
		ApplyViewFeel(OutResult);
		KeepCameraOutOfWorld(this, SafetyPivot, CameraSafetyRadius, OutResult.Location, ExitingVehicle.Get());
		UpdateFirstPersonViewmodel(DeltaTime, OutResult); // [A-068] terceira pessoa: devolve a arma à mão
		return;
	}
	const FRotator ViewRot = GetControlRotation();
	const FVector EyeLocation = ComputeFirstPersonEye(DeltaTime, ViewRot);
	const float Smooth = FMath::SmoothStep(0.f, 1.f, FPBlendAlpha);
	OutResult.Location = FMath::Lerp(OutResult.Location, EyeLocation, Smooth);
	// As duas câmeras usam a rotação do controle: o centro da tela é o mesmo ponto de onde sai o tiro.
	OutResult.Rotation = ViewRot;
	OutResult.FOV = FMath::Lerp(OutResult.FOV, FPFov, Smooth);
	ApplyViewFeel(OutResult);
	KeepCameraOutOfWorld(this, SafetyPivot, CameraSafetyRadius, OutResult.Location, ExitingVehicle.Get()); // [A-065]
	// [A-068] arma na frente da vista final (não mexe na câmera: só posiciona a arma)
	UpdateFirstPersonViewmodel(DeltaTime, OutResult);
}

// ---------------------------------------------------------------- Arma em primeira pessoa (A-068)

void AJRCharacter::RestoreViewmodelPose()
{
	bVMApplied = false;
	if (IsFirearmSlot(CurrentSlot))
	{
		const FTransform KickNow(FRotator(KickPitchNow, 0.f, 0.f), FVector(-KickBackNow, 0.f, 0.f));
		WeaponMesh->SetRelativeTransform(KickNow * GetGripFor(CurrentSlot));
	}
	MeleeMesh->SetRelativeTransform(GetGripFor(EJRWeaponSlot::Melee));
	WeaponMesh->SetCastShadow(true);
	MeleeMesh->SetCastShadow(true);
}

void AJRCharacter::UpdateFirstPersonViewmodel(float DeltaTime, const FMinimalViewInfo& View)
{
	const float Dt = FMath::Clamp(DeltaTime, 0.f, 0.05f);
	const bool bRanged = IsFirearmSlot(CurrentSlot);
	const bool bMelee = CurrentSlot == EJRWeaponSlot::Melee;
	UStaticMeshComponent* Held = bRanged ? WeaponMesh.Get() : (bMelee ? MeleeMesh.Get() : nullptr);
	// Luneta (a câmera vai para o olho da luneta pela própria arma) e cenas de interação (outra câmera):
	// a arma volta para a mão NA HORA, sem mistura.
	const bool bBlocked = !bFPViewmodel || !Held || !Held->IsVisible() || ScopeAlpha > 0.f || WantsScope()
		|| (InteractionCamera && InteractionCamera->IsShotActive());
	if (bBlocked)
	{
		VMActionWeight = 0.f;
	}
	else
	{
		// Durante o golpe o graveto segue a mão (a animação mostra o golpe).
		VMActionWeight = FMath::FInterpTo(VMActionWeight, (bMelee && bMeleeBusy) ? 0.f : 1.f, Dt, 12.f);
	}
	const float Weight = FMath::SmoothStep(0.f, 1.f, FPBlendAlpha) * VMActionWeight;
	if (Weight <= 0.001f || !Held)
	{
		if (bVMApplied)
		{
			RestoreViewmodelPose();
		}
		bVMLastViewValid = false;
		return;
	}

	// ---- estado: mira, corrida, abaixar, passos, respiração
	const float Speed = static_cast<float>(GetVelocity().Size2D());
	const UCharacterMovementComponent* MoveComp = GetCharacterMovement();
	const bool bGrounded = MoveComp && MoveComp->IsMovingOnGround();
	const float MoveAlpha = bGrounded ? FMath::Clamp(Speed / FMath::Max(1.f, WalkSpeed), 0.f, 1.f) : 0.f;
	const float SprintTarget = (bGrounded && bIsSprinting && !bAimHeld && Speed > WalkSpeed * 1.1f) ? 1.f : 0.f;
	VMSprintNow = FMath::FInterpTo(VMSprintNow, SprintTarget, Dt, 8.f);
	VMAimNow = FMath::FInterpTo(VMAimNow, (bRanged && bAimHeld && bWeaponEquipped) ? 1.f : 0.f, Dt, FPAimBlendSpeed);
	const bool bLowered = bWeaponTransition || bHealing || bItemWheelOpen || (WeaponComponent && WeaponComponent->IsReloading());
	VMDipNow = FMath::FInterpTo(VMDipNow, bLowered ? 1.f : 0.f, Dt, 10.f);
	if (MoveAlpha > 0.05f)
	{
		VMBobPhase += Dt * FMath::Lerp(FPBobWalkRate, FPBobSprintRate, VMSprintNow) * 2.f * UE_PI;
		if (VMBobPhase > 2.f * UE_PI)
		{
			VMBobPhase -= 2.f * UE_PI;
		}
	}
	VMBreathTime += Dt;

	// ---- sway: a arma atrasa um pouco quando a câmera gira e volta como mola
	const FRotator ViewRot = View.Rotation;
	if (!bVMLastViewValid)
	{
		VMLastViewRot = ViewRot;
		bVMLastViewValid = true;
	}
	const FRotator ViewDelta = (ViewRot - VMLastViewRot).GetNormalized();
	VMLastViewRot = ViewRot;
	const float InvDt = Dt > KINDA_SMALL_NUMBER ? 1.f / Dt : 0.f;
	const float SwayScale = FPSwayAmount * (1.f - 0.5f * VMAimNow) * InvDt;
	const FRotator SwayTarget(
		FMath::Clamp(-static_cast<float>(ViewDelta.Pitch) * SwayScale, -FPSwayMaxDegrees, FPSwayMaxDegrees),
		FMath::Clamp(-static_cast<float>(ViewDelta.Yaw) * SwayScale, -FPSwayMaxDegrees, FPSwayMaxDegrees), 0.f);
	VMSwayRot = FMath::RInterpTo(VMSwayRot, SwayTarget, Dt, FPSwaySpeed);
	const float SwayPitch = static_cast<float>(VMSwayRot.Pitch);
	const float SwayYaw = static_cast<float>(VMSwayRot.Yaw);

	// ---- posição na frente da câmera (X frente, Y direita, Z cima)
	const bool bLong = bRanged && UsesRifleAnims();
	const FVector HipOffset = bRanged ? (bLong ? FPRifleOffset : FPPistolOffset) : FPMeleeOffset;
	const FVector AimOffset = bRanged ? (bLong ? FPRifleAimOffset : FPPistolAimOffset) : FPMeleeOffset;
	FVector Local = FMath::Lerp(HipOffset, AimOffset, VMAimNow);
	const float BobAmp = MoveAlpha * (1.f - 0.85f * VMAimNow);
	const float Vert = BobAmp * FMath::Lerp(FPBobWalkCm, FPBobSprintCm, VMSprintNow);
	const float StepWave = FMath::Sin(VMBobPhase);
	const float StepDip = 0.5f * (1.f - FMath::Cos(2.f * VMBobPhase)); // desce a cada passo (2 por ciclo)
	const float Breath = FMath::Sin(VMBreathTime * FPBreathRate) * (1.f - 0.6f * VMAimNow);
	Local.Z += -StepDip * Vert + Breath * FPBreathCm;
	Local.Y += StepWave * Vert * 1.5f;
	Local += FVector(-2.f, 2.f, -3.f) * VMSprintNow;         // correndo: arma mais baixa e de lado
	Local += FVector(-4.f, 0.f, -14.f) * VMDipNow;           // recarga/troca/cura: arma desce
	Local.Y += SwayYaw * 0.35f;
	Local.Z += SwayPitch * 0.3f;

	FRotator LocalRot = bRanged ? FRotator::ZeroRotator : FPMeleeRotation;
	LocalRot.Yaw += FPWeaponYawIn * (1.f - VMAimNow) + SwayYaw + 8.f * VMSprintNow;
	LocalRot.Pitch += Breath * 0.35f - 30.f * VMDipNow - 8.f * VMSprintNow + SwayPitch;
	LocalRot.Roll += StepWave * BobAmp * FMath::Lerp(1.f, 3.f, VMSprintNow) + 6.f * VMSprintNow;

	// ---- mistura entre a mão (terceira pessoa) e a frente da câmera; o coice do A-057 vai por cima
	const FTransform Grip = GetGripFor(bRanged ? CurrentSlot : EJRWeaponSlot::Melee);
	const FTransform KickNow = bRanged ? FTransform(FRotator(KickPitchNow, 0.f, 0.f), FVector(-KickBackNow, 0.f, 0.f))
		: FTransform::Identity;
	const USceneComponent* HandParent = Held->GetAttachParent();
	const FTransform ParentWorld = HandParent ? HandParent->GetSocketTransform(Held->GetAttachSocketName()) : GetActorTransform();
	const FTransform HandWorld = KickNow * Grip * ParentWorld;
	const FQuat ViewQuat = ViewRot.Quaternion();
	// [A-086] escala própria (os braços do corpo ficam escondidos em 1a pessoa: a mão teria escala 0)
	const FVector ViewScale = Grip.GetScale3D() * (GetMesh() ? GetMesh()->GetComponentScale() : FVector::OneVector) * FPWeaponScale;
	const FTransform ViewWorld = KickNow * FTransform(ViewQuat * LocalRot.Quaternion(), View.Location + ViewQuat.RotateVector(Local),
		ViewScale);
	FTransform Final;
	Final.Blend(HandWorld, ViewWorld, Weight);
	Held->SetWorldTransform(Final, false, nullptr, ETeleportType::TeleportPhysics);
	// Na frente da câmera a sombra seria de uma arma flutuando ao lado do corpo: só a da mão projeta sombra.
	Held->SetCastShadow(Weight < 0.5f);
	bVMApplied = true;
}

void AJRCharacter::KeepCameraOutOfWorld(const AActor* ViewOwner, const FVector& Pivot, float Radius, FVector& InOutLocation,
	const AActor* ExtraIgnore)
{
	UWorld* World = ViewOwner ? ViewOwner->GetWorld() : nullptr;
	if (!World || Radius <= 0.f || FVector::DistSquared(Pivot, InOutLocation) < 1.0)
	{
		return;
	}
	FCollisionQueryParams Query(SCENE_QUERY_STAT(JRCameraSafety), false, ViewOwner);
	TArray<AActor*> Attached;
	ViewOwner->GetAttachedActors(Attached, true, true); // arma e outros presos ao dono não seguram a câmera
	Query.AddIgnoredActors(Attached);
	if (ExtraIgnore)
	{
		Query.AddIgnoredActor(ExtraIgnore); // carro do qual o herói está saindo
	}
	FHitResult Hit;
	if (World->SweepSingleByChannel(Hit, Pivot, InOutLocation, FQuat::Identity, ECC_Camera, FCollisionShape::MakeSphere(Radius), Query)
		&& !Hit.bStartPenetrating)
	{
		InOutLocation = Hit.Location;
	}
}

// ---------------------------------------------------------------- Bolsa e cura (A-055)

namespace
{
	const TCHAR* ConsumableLabel(EJRConsumable Item)
	{
		switch (Item)
		{
		case EJRConsumable::Bandage: return TEXT("bandagem");
		case EJRConsumable::Medkit: return TEXT("kit médico");
		default: return TEXT("Fúria");
		}
	}

	const FLinearColor HealToastColor(1.f, 0.45f, 0.4f);
	const FLinearColor WarnToastColor(1.f, 0.8f, 0.35f);
}

bool AJRCharacter::TryUseHealItem(EJRConsumable Item)
{
	if (Item == EJRConsumable::Fury)
	{
		return TryUseFuryCharge();
	}
	if (bHealing || bItemWheelOpen || HealthComponent->IsDead())
	{
		return false;
	}
	if (InventoryComponent->GetCount(Item) <= 0)
	{
		AJRHUD::Toast(this, FString::Printf(TEXT("Sem %s na bolsa"), ConsumableLabel(Item)), WarnToastColor);
		return false;
	}
	if (HealthComponent->GetHealthNormalized() >= 1.f)
	{
		AJRHUD::Toast(this, TEXT("Vida cheia"), WarnToastColor);
		return false;
	}
	UAnimInstance* Anim = GetMesh()->GetAnimInstance();
	// Pegando algo do chão, abrindo baú, saindo do carro ou trocando de arma: espera terminar.
	if (bWeaponTransition || ExitingVehicle.IsValid() || (Anim && Anim->IsSlotActive(FullBodySlot)))
	{
		return false;
	}
	WeaponComponent->CancelAll();
	bFireHeld = false;
	bHealing = true;
	bHealApplied = false;
	HealingItem = Item;
	HealStartTime = GetWorld()->GetTimeSeconds();
	// Anda devagar enquanto se cura (correr interrompe: HandleSprint).
	bIsSprinting = false;
	GetCharacterMovement()->MaxWalkSpeed = WalkSpeed * HealMoveSpeedFactor;
	// Mãos ocupadas: a arma some da mão até terminar (UpdateWeaponVisuals devolve).
	WeaponMesh->SetVisibility(false);
	MeleeMesh->SetVisibility(false);
	if (Anim && HealAnim)
	{
		Anim->StopSlotAnimation(0.1f, UpperBodySlot);
		AimMontage = nullptr;
		Anim->PlaySlotAnimationAsDynamicMontage(HealAnim, UpperBodySlot, 0.2f, 0.25f, 1.f, 1);
	}
	const float TotalTime = FMath::Max(0.1f, HealDuration);
	const float UseAt = FMath::Clamp(HealUseTime, 0.01f, TotalTime);
	FTimerManager& Timers = GetWorldTimerManager();
	Timers.SetTimer(HealApplyTimer, this, &AJRCharacter::ApplyHealNow, UseAt, false);
	Timers.SetTimer(HealEndTimer, this, &AJRCharacter::FinishHeal, TotalTime, false);
	return true;
}

void AJRCharacter::ApplyHealNow()
{
	if (!bHealing || bHealApplied || HealthComponent->IsDead())
	{
		return;
	}
	// Encheu a vida por outro meio no meio da animação: não gasta o item.
	if (HealthComponent->GetHealthNormalized() >= 1.f || !InventoryComponent->ConsumeItem(HealingItem))
	{
		CancelHeal(false);
		return;
	}
	bHealApplied = true;
	const float Healed = HealthComponent->Heal(InventoryComponent->GetHealAmount(HealingItem));
	PlayFeedback(0.f, 0.f, -2.5f); // [A-073] "respirou": pulso de zoom no instante em que a vida sobe
	AJRHUD::Toast(this, FString::Printf(TEXT("+%d de vida (%s)"), FMath::RoundToInt(Healed), ConsumableLabel(HealingItem)),
		HealToastColor);
}

void AJRCharacter::FinishHeal()
{
	if (!bHealing)
	{
		return;
	}
	if (!bHealApplied)
	{
		ApplyHealNow(); // HealUseTime maior que HealDuration: cura no fim
	}
	bHealing = false;
	GetWorldTimerManager().ClearTimer(HealApplyTimer);
	GetWorldTimerManager().ClearTimer(HealEndTimer);
	GetCharacterMovement()->MaxWalkSpeed = bIsSprinting ? SprintSpeed : WalkSpeed;
	if (UAnimInstance* Anim = GetMesh()->GetAnimInstance())
	{
		if (HealAnim && Anim->IsSlotActive(UpperBodySlot))
		{
			Anim->StopSlotAnimation(0.25f, UpperBodySlot);
		}
	}
	UpdateWeaponVisuals();
}

void AJRCharacter::CancelHeal(bool bShowToast)
{
	if (!bHealing)
	{
		return;
	}
	const bool bWasApplied = bHealApplied;
	bHealing = false;
	GetWorldTimerManager().ClearTimer(HealApplyTimer);
	GetWorldTimerManager().ClearTimer(HealEndTimer);
	if (UCharacterMovementComponent* MoveComp = GetCharacterMovement())
	{
		MoveComp->MaxWalkSpeed = bIsSprinting ? SprintSpeed : WalkSpeed;
	}
	if (UAnimInstance* Anim = GetMesh()->GetAnimInstance())
	{
		if (HealAnim)
		{
			Anim->StopSlotAnimation(0.15f, UpperBodySlot);
		}
	}
	UpdateWeaponVisuals();
	if (bShowToast && !bWasApplied)
	{
		AJRHUD::Toast(this, FString::Printf(TEXT("Cura interrompida (a %s não foi gasta)"), ConsumableLabel(HealingItem)),
			WarnToastColor);
	}
}

float AJRCharacter::GetHealProgress() const
{
	if (!bHealing || HealDuration <= 0.f)
	{
		return 0.f;
	}
	return FMath::Clamp(static_cast<float>(GetWorld()->GetTimeSeconds() - HealStartTime) / HealDuration, 0.f, 1.f);
}

bool AJRCharacter::TryUseFuryCharge()
{
	if (HealthComponent->IsDead())
	{
		return false;
	}
	if (InventoryComponent->GetCount(EJRConsumable::Fury) <= 0)
	{
		AJRHUD::Toast(this, TEXT("Nenhuma Fúria guardada"), WarnToastColor);
		return false;
	}
	if (GetFuryRemaining() > 0.f)
	{
		AJRHUD::Toast(this, TEXT("A Fúria já está ativa"), WarnToastColor);
		return false;
	}
	InventoryComponent->ConsumeItem(EJRConsumable::Fury);
	ActivateFury(InventoryComponent->GetFurySeconds());
	AJRHUD::Toast(this, TEXT("FÚRIA! Tiros mais fortes"), FLinearColor(0.8f, 0.3f, 1.f));
	return true;
}

void AJRCharacter::HandleQuickHeal(const FInputActionValue& Value)
{
	if (IsRidingBike()) // [A-097] de bicicleta: só anda, olha e desce (E)
	{
		return;
	}
	if (bItemWheelOpen || bHealing)
	{
		return;
	}
	if (InventoryComponent->GetCount(EJRConsumable::Bandage) > 0)
	{
		TryUseHealItem(EJRConsumable::Bandage);
	}
	else if (InventoryComponent->GetCount(EJRConsumable::Medkit) > 0)
	{
		TryUseHealItem(EJRConsumable::Medkit);
	}
	else
	{
		AJRHUD::Toast(this, TEXT("Sem bandagem nem kit médico"), WarnToastColor);
	}
}

void AJRCharacter::JRCura()
{
	InventoryComponent->AddItem(EJRConsumable::Bandage, 3);
	InventoryComponent->AddItem(EJRConsumable::Medkit, 2);
	InventoryComponent->AddItem(EJRConsumable::Fury, 1);
	const float Hurt = FMath::Min(50.f, HealthComponent->GetHealth() - 1.f);
	if (Hurt > 0.f)
	{
		HealthComponent->ApplyDamage(Hurt, nullptr);
	}
	AJRHUD::Toast(this, TEXT("Teste: bandagens, kits e Fúria na bolsa (H cura, Tab abre a roda)"), FLinearColor(0.6f, 0.9f, 1.f));
}

// ---------------------------------------------------------------- Roda de itens (A-055)

namespace
{
	EJRWheelEntry EntryForSlot(EJRWeaponSlot WeaponSlot)
	{
		switch (WeaponSlot)
		{
		case EJRWeaponSlot::Melee: return EJRWheelEntry::Melee;
		case EJRWeaponSlot::Pistol: return EJRWheelEntry::Pistol;
		case EJRWeaponSlot::Shotgun: return EJRWheelEntry::Shotgun;
		case EJRWeaponSlot::Sniper: return EJRWheelEntry::Sniper;
		default: return EJRWheelEntry::Unarmed;
		}
	}
}

void AJRCharacter::HandleItemWheelPressed(const FInputActionValue& Value)
{
	if (IsRidingBike()) // [A-097] de bicicleta: só anda, olha e desce (E)
	{
		return;
	}
	OpenItemWheel();
}

void AJRCharacter::HandleItemWheelReleased(const FInputActionValue& Value)
{
	CloseItemWheel(true);
}

void AJRCharacter::HandleEscapeKey()
{
	if (bItemWheelOpen)
	{
		CancelItemWheel();
	}
}

void AJRCharacter::CancelItemWheel()
{
	CloseItemWheel(false);
}

void AJRCharacter::OpenItemWheel()
{
	APlayerController* PC = Cast<APlayerController>(GetController());
	if (bItemWheelOpen || !PC || HealthComponent->IsDead())
	{
		return;
	}
	bItemWheelOpen = true;
	WheelCursor = FVector2D::ZeroVector;
	// [A-059] abre na última aba usada; na aba ARMAS o destaque começa no que está na mão
	WheelTab = FMath::Clamp(WheelTab, 0, JRItemWheel::NumTabs - 1);
	int32 HandTab = 0;
	int32 HandSector = 0;
	if (JRItemWheel::FindEntry(EntryForSlot(CurrentSlot), HandTab, HandSector) && HandTab == JRItemWheel::TabWeapons)
	{
		WheelTabHighlight[JRItemWheel::TabWeapons] = HandSector;
	}
	WheelHighlight = WheelTabHighlight[WheelTab];
	WheelTabChangeRealTime = -100.0;
	WheelOpenRealTime = GetWorld()->GetRealTimeSeconds();
	bFireHeld = false;
	WeaponComponent->StopFire();
	PC->RotationInput = FRotator::ZeroRotator;
	// Câmera lenta (estilo GTA). O HUD anima no tempo real; o olhar vira cursor (FeedItemWheelCursor).
	WheelSavedTimeDilation = UGameplayStatics::GetGlobalTimeDilation(this);
	UGameplayStatics::SetGlobalTimeDilation(this, FMath::Min(WheelSavedTimeDilation, ItemWheelTimeDilation));
}

void AJRCharacter::CloseItemWheel(bool bConfirm)
{
	if (!bItemWheelOpen)
	{
		return;
	}
	bItemWheelOpen = false;
	UGameplayStatics::SetGlobalTimeDilation(this, WheelSavedTimeDilation > 0.f ? WheelSavedTimeDilation : 1.f);
	if (bConfirm && !HealthComponent->IsDead())
	{
		WheelTabHighlight[FMath::Clamp(WheelTab, 0, JRItemWheel::NumTabs - 1)] = WheelHighlight;
		ApplyWheelEntry(JRItemWheel::EntryAt(WheelTab, WheelHighlight));
	}
}

void AJRCharacter::FeedItemWheelCursor()
{
	APlayerController* PC = Cast<APlayerController>(GetController());
	if (!PC)
	{
		return;
	}
	// O controller já aplicou sensibilidade, inversão e escala do olhar: Yaw + = direita, Pitch + = para cima.
	const FRotator LookDelta = PC->RotationInput;
	PC->RotationInput = FRotator::ZeroRotator;
	WheelCursor += FVector2D(LookDelta.Yaw, LookDelta.Pitch) * ItemWheelSensitivity;
	const double MaxLen = FMath::Max(1.f, ItemWheelCursorRadius);
	if (WheelCursor.Size() > MaxLen)
	{
		WheelCursor = WheelCursor.GetSafeNormal() * MaxLen;
	}
	const int32 Sector = JRItemWheel::SectorFromDirection(WheelCursor, ItemWheelCursorRadius * ItemWheelDeadZone);
	if (Sector >= 0)
	{
		WheelHighlight = Sector;
	}
}

FVector2D AJRCharacter::GetItemWheelCursor() const
{
	return WheelCursor / static_cast<double>(FMath::Max(1.f, ItemWheelCursorRadius));
}

void AJRCharacter::SetItemWheelTab(int32 NewTab)
{
	const int32 Wanted = FMath::Clamp(NewTab, 0, JRItemWheel::NumTabs - 1);
	if (!bItemWheelOpen || Wanted == WheelTab)
	{
		return;
	}
	WheelTabHighlight[WheelTab] = WheelHighlight;
	WheelTabDir = Wanted > WheelTab ? 1 : -1;
	WheelTab = Wanted;
	WheelHighlight = WheelTabHighlight[WheelTab];
	// Cursor já apontando para um setor: o destaque segue o cursor na aba nova.
	const int32 CursorSector = JRItemWheel::SectorFromDirection(WheelCursor, ItemWheelCursorRadius * ItemWheelDeadZone);
	if (CursorSector >= 0)
	{
		WheelHighlight = CursorSector;
	}
	WheelTabChangeRealTime = GetWorld() ? GetWorld()->GetRealTimeSeconds() : 0.0;
}

void AJRCharacter::CycleItemWheelTab(int32 Direction)
{
	const int32 Tabs = JRItemWheel::NumTabs;
	const int32 Next = ((WheelTab + (Direction >= 0 ? 1 : -1)) % Tabs + Tabs) % Tabs;
	SetItemWheelTab(Next);
	WheelTabDir = Direction >= 0 ? 1 : -1;
}

void AJRCharacter::UpdateItemWheelInput()
{
	if (!bItemWheelOpen)
	{
		return;
	}
	const APlayerController* WheelInputPC = Cast<APlayerController>(GetController());
	if (!WheelInputPC)
	{
		return;
	}
	if (WheelInputPC->WasInputKeyJustPressed(EKeys::Gamepad_FaceButton_Right))
	{
		CancelItemWheel();
		return;
	}
	int32 Step = 0;
	if (WheelInputPC->WasInputKeyJustPressed(EKeys::E) || WheelInputPC->WasInputKeyJustPressed(EKeys::MouseScrollDown)
		|| WheelInputPC->WasInputKeyJustPressed(EKeys::Gamepad_RightShoulder) || WheelInputPC->WasInputKeyJustPressed(EKeys::Gamepad_DPad_Right))
	{
		Step = 1;
	}
	else if (WheelInputPC->WasInputKeyJustPressed(EKeys::Q) || WheelInputPC->WasInputKeyJustPressed(EKeys::MouseScrollUp)
		|| WheelInputPC->WasInputKeyJustPressed(EKeys::Gamepad_DPad_Left))
	{
		Step = -1;
	}
	else if (WheelInputPC->WasInputKeyJustPressed(EKeys::LeftMouseButton))
	{
		Step = 1; // clique: alterna entre as duas abas (os cabeçalhos ficam em cima da roda)
	}
	if (Step != 0)
	{
		CycleItemWheelTab(Step);
	}
}

void AJRCharacter::ApplyWheelEntry(EJRWheelEntry Entry)
{
	switch (Entry)
	{
	case EJRWheelEntry::Unarmed:
		SelectWeaponSlot(EJRWeaponSlot::None);
		break;
	case EJRWheelEntry::Melee:
	case EJRWheelEntry::Pistol:
	case EJRWheelEntry::Shotgun:
	case EJRWheelEntry::Sniper:
	{
		const EJRWeaponSlot WantSlot = Entry == EJRWheelEntry::Melee ? EJRWeaponSlot::Melee
			: Entry == EJRWheelEntry::Pistol ? EJRWeaponSlot::Pistol
			: Entry == EJRWheelEntry::Sniper ? EJRWeaponSlot::Sniper : EJRWeaponSlot::Shotgun;
		if (OwnsWeapon(WantSlot))
		{
			SelectWeaponSlot(WantSlot);
		}
		else
		{
			AJRHUD::Toast(this, TEXT("Você ainda não encontrou essa arma"), WarnToastColor);
		}
		break;
	}
	case EJRWheelEntry::Bandage:
		TryUseHealItem(EJRConsumable::Bandage);
		break;
	case EJRWheelEntry::Medkit:
		TryUseHealItem(EJRConsumable::Medkit);
		break;
	case EJRWheelEntry::Fury:
		TryUseFuryCharge();
		break;
	case EJRWheelEntry::NoItem:
	case EJRWheelEntry::Empty:
	case EJRWheelEntry::Count:
		break; // "Nada" dos consumíveis e setores vazios: só fecha
	case EJRWheelEntry::CarKey:
	case EJRWheelEntry::Fuel:
	case EJRWheelEntry::Explosive:
		AJRHUD::Toast(this, TEXT("Item-chave: é usado sozinho no lugar certo (aperte E perto)"), WarnToastColor);
		break;
	default:
		AJRHUD::Toast(this, TEXT("Em breve"), WarnToastColor);
		break;
	}
}

FJRWheelEntryInfo AJRCharacter::GetWheelEntryInfo(int32 Index) const
{
	FJRWheelEntryInfo Info;
	// Índice = EJRWheelEntry como número (o rifle e os itens da A-059 ficam depois de Count).
	const int32 LastEntry = static_cast<int32>(EJRWheelEntry::Empty);
	const EJRWheelEntry Entry = (Index < 0 || Index > LastEntry || Index == static_cast<int32>(EJRWheelEntry::Count))
		? EJRWheelEntry::Empty : static_cast<EJRWheelEntry>(Index);
	const FJRAmmoState AmmoNow = WeaponComponent->GetAmmo();
	const int32 TotalAmmo = AmmoNow.Magazine + AmmoNow.Reserve;
	// Atributos 0..1 das barrinhas (A-059): dano por disparo até 120, espalhamento até 8 graus,
	// cadência até 8 tiros/s, alcance até 200 m (raiz quadrada para as diferenças pequenas aparecerem).
	auto FillStats = [&Info](const UJRWeaponDefinition* StatDef)
	{
		if (!StatDef)
		{
			return;
		}
		Info.bHasStats = true;
		const float ShotDamage = StatDef->Damage * static_cast<float>(FMath::Max(1, StatDef->PelletCount));
		const float WorstSpread = FMath::Max(StatDef->SpreadHalfAngleDegrees, StatDef->PelletSpreadDegrees);
		Info.StatDamage = JRItemWheel::StatFraction(ShotDamage, 120.f);
		Info.StatAccuracy = FMath::Clamp(1.f - WorstSpread / 8.f, 0.06f, 1.f);
		Info.StatFireRate = JRItemWheel::StatFraction(StatDef->FireRate, 8.f);
		Info.StatRange = JRItemWheel::StatFraction(StatDef->Range, 20000.f);
	};
	// Pistola, escopeta e rifle dividem as mesmas células: a que não está na mão mostra como ficaria ao trocar.
	auto FillFirearm = [&](EJRWeaponSlot GunSlot, const UJRWeaponDefinition* GunDef)
	{
		Info.Category = TEXT("ARMA DE FOGO");
		Info.bOwned = OwnsWeapon(GunSlot);
		Info.bCurrent = CurrentSlot == GunSlot;
		FillStats(GunDef);
		if (!Info.bOwned)
		{
			Info.Detail = TEXT("Ainda não encontrada");
			return;
		}
		if (Info.bCurrent)
		{
			Info.Loaded = AmmoNow.Magazine;
			Info.Reserve = AmmoNow.Reserve;
		}
		else
		{
			const int32 MagSize = GunDef ? FMath::Max(1, GunDef->MagazineSize) : FMath::Max(1, AmmoNow.MagazineSize);
			Info.Loaded = FMath::Min(MagSize, TotalAmmo);
			Info.Reserve = FMath::Max(0, TotalAmmo - Info.Loaded);
		}
		Info.Detail = TEXT("Células divididas entre as armas");
	};
	auto FillConsumable = [&](EJRConsumable BagItem, const FString& HealText)
	{
		Info.Category = TEXT("CURA");
		Info.Count = InventoryComponent->GetCount(BagItem);
		Info.MaxCount = InventoryComponent->GetMaxCount(BagItem);
		Info.bOwned = Info.Count > 0;
		Info.Detail = HealText;
	};
	const AJRPlayerController* KeyPC = Cast<AJRPlayerController>(GetController());
	auto FillKeyItem = [&](const TCHAR* KeyName, const TCHAR* Label, const TCHAR* IconName, const TCHAR* UseText)
	{
		Info.Name = Label;
		Info.Icon = IconName;
		Info.Category = TEXT("ITEM-CHAVE");
		Info.bKeyItem = true;
		Info.bOwned = KeyPC && KeyPC->HasKeyItem(FName(KeyName));
		Info.Detail = Info.bOwned ? FString(UseText) : FString(TEXT("Ainda não encontrado\n(ou já usado)"));
	};
	switch (Entry)
	{
	case EJRWheelEntry::Unarmed:
		Info.Name = TEXT("NADA");
		Info.Category = TEXT("SEM ARMA");
		Info.Icon = TEXT("Hand");
		Info.bOwned = true;
		Info.bCurrent = CurrentSlot == EJRWeaponSlot::None;
		Info.Detail = TEXT("Guarda a arma\nCorre e interage com as mãos livres");
		break;
	case EJRWheelEntry::NoItem:
		Info.Name = TEXT("NADA");
		Info.Category = TEXT("CONSUMÍVEIS");
		Info.Icon = TEXT("Hand");
		Info.bOwned = true;
		Info.Detail = TEXT("Fecha a roda sem usar nada");
		break;
	case EJRWheelEntry::Melee:
		Info.Name = TEXT("GRAVETO ALIEN");
		Info.Category = TEXT("CORPO A CORPO");
		Info.Icon = TEXT("Stick");
		Info.bOwned = bOwnMelee;
		Info.bCurrent = CurrentSlot == EJRWeaponSlot::Melee;
		Info.bHasStats = true;
		Info.StatDamage = JRItemWheel::StatFraction(MeleeDamage, 120.f);
		Info.StatAccuracy = 0.9f; // acerta onde mira (golpe curto)
		Info.StatFireRate = JRItemWheel::StatFraction(1.f / FMath::Max(0.1f, MeleeCooldown), 8.f);
		Info.StatRange = JRItemWheel::StatFraction(MeleeRange, 20000.f);
		Info.Detail = bOwnMelee ? FString::Printf(TEXT("Dano %d por golpe\nNão gasta células"), FMath::RoundToInt(MeleeDamage))
			: FString(TEXT("Ainda não encontrado"));
		break;
	case EJRWheelEntry::Pistol:
		Info.Name = TEXT("PISTOLA ALIEN");
		Info.Icon = TEXT("Pistol");
		FillFirearm(EJRWeaponSlot::Pistol, PistolDefinition.Get());
		break;
	case EJRWheelEntry::Shotgun:
		Info.Name = TEXT("ESCOPETA ALIEN");
		Info.Icon = TEXT("Shotgun");
		FillFirearm(EJRWeaponSlot::Shotgun, ShotgunDefinition.Get());
		break;
	case EJRWheelEntry::Sniper:
		Info.Name = TEXT("RIFLE ALIEN");
		Info.Icon = TEXT("Sniper");
		FillFirearm(EJRWeaponSlot::Sniper, SniperDefinition.Get());
		break;
	case EJRWheelEntry::Grenade:
		Info.Name = TEXT("GRANADA");
		Info.Category = TEXT("EM BREVE");
		Info.Icon = TEXT("Grenade");
		Info.bFuture = true;
		Info.Detail = TEXT("Ainda não existe nesta fase");
		break;
	case EJRWheelEntry::Fury:
	{
		Info.Name = TEXT("FÚRIA");
		Info.Category = TEXT("PODER");
		Info.Icon = TEXT("Fury");
		Info.Count = InventoryComponent->GetCount(EJRConsumable::Fury);
		Info.MaxCount = InventoryComponent->GetMaxCount(EJRConsumable::Fury);
		Info.bOwned = Info.Count > 0;
		const float FuryLeft = GetFuryRemaining();
		Info.Detail = FuryLeft > 0.f
			? FString::Printf(TEXT("Ativa: %d s restantes"), FMath::CeilToInt(FuryLeft))
			: FString::Printf(TEXT("Dano e cadência maiores\npor %d s"), FMath::RoundToInt(InventoryComponent->GetFurySeconds()));
		break;
	}
	case EJRWheelEntry::Medkit:
		Info.Name = TEXT("KIT MÉDICO");
		Info.Icon = TEXT("Medkit");
		FillConsumable(EJRConsumable::Medkit, FString::Printf(TEXT("Cura %d de vida"),
			FMath::RoundToInt(InventoryComponent->GetHealAmount(EJRConsumable::Medkit))));
		break;
	case EJRWheelEntry::Bandage:
		Info.Name = TEXT("BANDAGEM");
		Info.Icon = TEXT("Bandage");
		FillConsumable(EJRConsumable::Bandage, FString::Printf(TEXT("Cura %d de vida"),
			FMath::RoundToInt(InventoryComponent->GetHealAmount(EJRConsumable::Bandage))));
		break;
	case EJRWheelEntry::CarKey:
		FillKeyItem(TEXT("CarKey"), TEXT("CHAVE DO CARRO"), TEXT("CarKey"), TEXT("Liga o carro: chegue perto e aperte E"));
		break;
	case EJRWheelEntry::Fuel:
		FillKeyItem(TEXT("Fuel"), TEXT("GALÃO"), TEXT("Fuel"), TEXT("Abastece o carro sem gasolina"));
		break;
	case EJRWheelEntry::Explosive:
		FillKeyItem(TEXT("Explosive"), TEXT("EXPLOSIVO"), TEXT("Explosive"), TEXT("Derruba o portão bloqueado"));
		break;
	case EJRWheelEntry::Empty:
	case EJRWheelEntry::Count:
	default:
		Info.Name = TEXT("VAZIO");
		Info.bEmpty = true;
		break;
	}
	return Info;
}

// ---------------------------------------------------------------- Sensação de combate (A-057)

UAnimSequenceBase* AJRCharacter::GetActiveAimAnim() const
{
	return UsesRifleAnims() && ShotgunAimAnim ? ShotgunAimAnim.Get() : AimAnim.Get();
}

UAnimSequenceBase* AJRCharacter::GetActiveFireAnim() const
{
	return UsesRifleAnims() && ShotgunFireAnim ? ShotgunFireAnim.Get() : FireAnim.Get();
}

UAnimSequenceBase* AJRCharacter::GetActiveReloadAnim() const
{
	return UsesRifleAnims() && ShotgunReloadAnim ? ShotgunReloadAnim.Get() : ReloadAnim.Get();
}

UAnimSequenceBase* AJRCharacter::GetActiveEquipAnim() const
{
	return UsesRifleAnims() && ShotgunEquipAnim ? ShotgunEquipAnim.Get() : EquipAnim.Get();
}

bool AJRCharacter::IsArmedIdlePlaying() const
{
	const UAnimInstance* Anim = GetMesh() ? GetMesh()->GetAnimInstance() : nullptr;
	return Anim && ArmedIdleMontage && Anim->Montage_IsPlaying(ArmedIdleMontage);
}

void AJRCharacter::PlayArmedIdle(float BlendIn)
{
	if (UAnimInstance* Anim = GetMesh()->GetAnimInstance())
	{
		ArmedIdleMontage = Anim->PlaySlotAnimationAsDynamicMontage(ArmedIdleAnim, UpperBodySlot, BlendIn, 0.25f, 1.f, 100000);
	}
}

FTransform AJRCharacter::GetGripFor(EJRWeaponSlot Slot) const
{
	// Identidade = não preenchido pelo script: usa o encaixe que a malha tinha no Blueprint.
	auto IsSet = [](const FTransform& Grip) { return !Grip.Equals(FTransform::Identity, 1.e-3f); };
	if (Slot == EJRWeaponSlot::Melee)
	{
		return IsSet(MeleeGripTransform) ? MeleeGripTransform : MeleeMeshBaseRelative;
	}
	if (Slot == EJRWeaponSlot::Sniper)
	{
		// Sem encaixe próprio: o da escopeta (rifle de duas mãos) ou, sem ele, o da pistola.
		FTransform SniperGrip = IsSet(SniperGripTransform) ? SniperGripTransform
			: (IsSet(ShotgunGripTransform) ? ShotgunGripTransform : (IsSet(PistolGripTransform) ? PistolGripTransform : WeaponMeshBaseRelative));
		SniperGrip.SetScale3D((IsSet(SniperGripTransform) ? SniperGrip.GetScale3D() : FVector::OneVector) * SniperMeshScale);
		return SniperGrip;
	}
	if (Slot == EJRWeaponSlot::Shotgun)
	{
		FTransform ShotgunGrip = IsSet(ShotgunGripTransform) ? ShotgunGripTransform
			: (IsSet(PistolGripTransform) ? PistolGripTransform : WeaponMeshBaseRelative);
		ShotgunGrip.SetScale3D(ShotgunGrip.GetScale3D() * ShotgunMeshScale);
		return ShotgunGrip;
	}
	FTransform PistolGrip = IsSet(PistolGripTransform) ? PistolGripTransform : WeaponMeshBaseRelative;
	PistolGrip.SetScale3D(FVector::OneVector);
	return PistolGrip;
}

void AJRCharacter::AddCameraTrauma(float Amount)
{
	Trauma = FMath::Clamp(Trauma + Amount, 0.f, 1.f);
}

void AJRCharacter::ApplyShotFeedback()
{
	const UJRWeaponDefinition* Def = WeaponComponent->GetDefinition();
	if (!Def)
	{
		return;
	}
	// Mirando segura melhor a arma (coice menor).
	const float Steady = bAimHeld ? 0.7f : 1.f;
	const float KickUp = Def->RecoilPitch * Steady * FMath::FRandRange(0.85f, 1.15f);
	const float KickSide = FMath::FRandRange(-Def->RecoilYaw, Def->RecoilYaw) * Steady;
	const float Keep = FMath::Clamp(Def->RecoilKeepFraction, 0.f, 1.f);
	RecoilPending += FRotator(KickUp * (1.f - Keep), KickSide * (1.f - Keep), 0.f);
	RecoilKeepPending += FRotator(KickUp * Keep, KickSide * Keep, 0.f);
	RecoilRecoverySpeed = Def->RecoilRecovery;
	KickBackNow = FMath::Min(KickBackNow + Def->KickBack, Def->KickBack * 2.f);
	KickPitchNow = FMath::Min(KickPitchNow + Def->KickPitch, Def->KickPitch * 2.f);
	KickRecoverySpeed = Def->KickRecovery;
	AddCameraTrauma(Def->ShakeScale);
	if (CurrentSlot == EJRWeaponSlot::Sniper && RescopeDelay > 0.f)
	{
		// Rifle: sai da luneta para "puxar o ferrolho" e volta sozinho se ainda estiver mirando.
		ScopeBlockedUntil = GetWorld()->GetTimeSeconds() + RescopeDelay;
	}
	if (Def->FollowUpDelay > 0.f)
	{
		// Escopeta: "bombeia" a célula: a arma dá um tranco curto para trás e para baixo.
		const float PumpBack = Def->KickBack * 0.6f;
		const float PumpDip = Def->KickPitch * 0.35f;
		GetWorldTimerManager().SetTimer(PumpTimer, FTimerDelegate::CreateWeakLambda(this, [this, PumpBack, PumpDip]()
		{
			KickBackNow += PumpBack;
			KickPitchNow -= PumpDip;
		}), Def->FollowUpDelay, false);
	}
}

void AJRCharacter::UpdateCombatFeel(float DeltaTime)
{
	const float Dt = FMath::Min(DeltaTime, 0.05f);
	// Coice da vista: entra em ~40 ms (não é um estalo seco) e volta suave para o centro.
	const float Intake = FMath::Min(1.f, Dt * 30.f);
	const FRotator ViewStep = RecoilPending * Intake;
	RecoilPending -= ViewStep;
	RecoilOffset += ViewStep;
	const FRotator KeepStep = RecoilKeepPending * Intake;
	RecoilKeepPending -= KeepStep;
	if (Controller && !KeepStep.IsNearlyZero(1.e-4f) && HealthComponent->GetHealth() > 0.f && !bItemWheelOpen)
	{
		// A parte "que fica": a mira sobe de verdade (o jogador corrige puxando para baixo).
		Controller->SetControlRotation(Controller->GetControlRotation() + KeepStep);
	}
	RecoilOffset *= FMath::Exp(-RecoilRecoverySpeed * Dt);

	// Arma na mão: tranco para trás e cano para cima, volta como mola.
	const float KickDecay = FMath::Exp(-KickRecoverySpeed * Dt);
	KickBackNow *= KickDecay;
	KickPitchNow *= KickDecay;
	ApplyWeaponKickTransform();

	// [A-073] tremor, afundada e pulso andam em TEMPO REAL: na congelada (hit-stop) e na roda de itens
	// a câmera não fica parada fora do centro (skill game-feel, passo 5).
	const float Dilation = FMath::Max(0.0001f, UGameplayStatics::GetGlobalTimeDilation(this));
	const float RealDt = FMath::Min(DeltaTime / Dilation, 0.05f);
	Trauma = FMath::Max(0.f, Trauma - ShakeDecay * RealDt);
	ShakeTime += RealDt;
	const float Take = FMath::Min(1.f, RealDt * 25.f);
	const float DipStep = LandDipPending * Take;
	LandDipPending -= DipStep;
	LandDipNow = (LandDipNow + DipStep) * FMath::Exp(-7.f * RealDt);
	const float PulseStep = FOVPulsePending * Take;
	FOVPulsePending -= PulseStep;
	FOVPulseNow = (FOVPulseNow + PulseStep) * FMath::Exp(-6.f * RealDt);
	UpdateScope(Dt);

	// Zoom mirando e FOV um pouco maior correndo.
	const bool bSprintingNow = bIsSprinting && !bAimHeld && GetVelocity().Size2D() > WalkSpeed * 1.1f;
	const float FOVTarget = (bAimHeld && bWeaponEquipped ? AimFOV - BaseFOV : 0.f) + (bSprintingNow ? SprintFOVBonus : 0.f);
	FOVOffsetNow = FMath::FInterpTo(FOVOffsetNow, FOVTarget, Dt, FOVBlendSpeed);
}

void AJRCharacter::ApplyWeaponKickTransform()
{
	const bool bRanged = IsFirearmSlot(CurrentSlot);
	const bool bKicking = FMath::Abs(KickBackNow) > 0.01f || FMath::Abs(KickPitchNow) > 0.05f;
	if (!bRanged || !WeaponMesh->IsVisible())
	{
		KickBackNow = 0.f;
		KickPitchNow = 0.f;
		return;
	}
	if (!bKicking && !bKickApplied)
	{
		return;
	}
	// Tranco no espaço da arma (X = cano, Z = cima) e depois o encaixe na mão.
	const FTransform Kick(FRotator(KickPitchNow, 0.f, 0.f), FVector(-KickBackNow, 0.f, 0.f));
	WeaponMesh->SetRelativeTransform(Kick * GetGripFor(CurrentSlot));
	bKickApplied = bKicking;
	if (!bKicking)
	{
		KickBackNow = 0.f;
		KickPitchNow = 0.f;
	}
}

void AJRCharacter::ApplyViewFeel(FMinimalViewInfo& OutResult) const
{
	OutResult.Rotation += RecoilOffset;
	const float Shake = Trauma * Trauma * JRFeel::ShakeScale(); // [A-073] acessibilidade 0..1
	const float Motion = JRFeel::MotionScale();
	OutResult.Location.Z -= LandDipNow * Motion; // [A-073] afundada da aterrissagem
	if (Shake > 0.0001f)
	{
		const float Phase = ShakeTime * ShakeFrequency;
		const FRotator ShakeRot(FMath::PerlinNoise1D(Phase + 11.f), FMath::PerlinNoise1D(Phase + 37.f),
			FMath::PerlinNoise1D(Phase + 71.f) * 0.5f);
		OutResult.Rotation += ShakeRot * (ShakeMaxAngle * Shake);
		const FVector ShakeLocal(0.f, FMath::PerlinNoise1D(Phase + 101.f), FMath::PerlinNoise1D(Phase + 131.f));
		OutResult.Location += OutResult.Rotation.RotateVector(ShakeLocal) * (ShakeMaxOffset * Shake);
	}
	OutResult.FOV = FMath::Clamp(OutResult.FOV + FOVOffsetNow + FOVPulseNow * Motion, 30.f, 130.f); // [A-073] pulso

	// [A-058] Luneta do rifle: a câmera vai para o olho da luneta (mesmo em terceira pessoa) e fecha o zoom.
	if (ScopeAlpha > 0.f && WeaponMesh)
	{
		const float ScopeBlend = FMath::SmoothStep(0.f, 1.f, ScopeAlpha);
		const FVector ScopeEye = WeaponMesh->GetComponentTransform().TransformPosition(SniperScopeOffset);
		OutResult.Location = FMath::Lerp(OutResult.Location, ScopeEye, static_cast<double>(ScopeBlend));
		// Respiração: balanço lento; Shift prende o fôlego (quase parado); sem fôlego balança o dobro.
		const bool bHoldingBreath = bIsSprinting && !bBreathExhausted && BreathLeft > 0.f;
		const float SwayScale = bHoldingBreath ? 0.12f : (bBreathExhausted ? 2.f : 1.f);
		const float SwayPhase = ScopeTime * ScopeSwaySpeed;
		const FRotator Sway(FMath::PerlinNoise1D(SwayPhase + 5.3f), FMath::PerlinNoise1D(SwayPhase + 23.7f), 0.f);
		OutResult.Rotation += Sway * (ScopeSwayDegrees * SwayScale * ScopeBlend);
		OutResult.FOV = FMath::Lerp(OutResult.FOV, GetScopeFOV(), ScopeBlend);
	}
}

void AJRCharacter::StartHitStop()
{
	StartHitStopFor(HitStopDuration);
}

void AJRCharacter::StartHitStopFor(float Seconds)
{
	// [A-073] mesma lógica de antes, com a duração passada (e a opção jr.Feel.HitStop 0 desliga)
	if (!JRFeel::HitStopEnabled() || bItemWheelOpen || bHitStopActive || Seconds <= 0.f
		|| UGameplayStatics::GetGlobalTimeDilation(this) < 0.999f)
	{
		return; // roda de itens já mexe na velocidade do jogo
	}
	bHitStopActive = true;
	UGameplayStatics::SetGlobalTimeDilation(this, HitStopDilation);
	// Os timers andam no tempo do jogo (lento): converte a duração real.
	GetWorldTimerManager().SetTimer(HitStopTimer, this, &AJRCharacter::EndHitStop, FMath::Max(0.0005f, Seconds * HitStopDilation), false);
}

void AJRCharacter::PlayFeedback(float TraumaAmount, float HitStopSeconds, float FOVPulseDegrees)
{
	// [A-073] pacote por evento (tiers): cada canal é opcional
	if (TraumaAmount > 0.f)
	{
		AddCameraTrauma(TraumaAmount);
	}
	if (HitStopSeconds > 0.f)
	{
		StartHitStopFor(HitStopSeconds);
	}
	if (!FMath::IsNearlyZero(FOVPulseDegrees))
	{
		FOVPulsePending += FOVPulseDegrees;
	}
}

void AJRCharacter::Landed(const FHitResult& Hit)
{
	Super::Landed(Hit);
	// [A-073] aqui a velocidade ainda é a da queda (o movimento zera o Z logo depois). O som de aterrissar
	// continua no UJRAudioSubsystem; isto só põe câmera e poeira, e só em quedas de verdade (pulo normal: nada).
	const float FallSpeed = static_cast<float>(-GetVelocity().Z);
	if (FallSpeed < LandingMinSpeed || HealthComponent->IsDead())
	{
		return;
	}
	const float Heavy = FMath::GetMappedRangeValueClamped(FVector2f(LandingMinSpeed, FMath::Max(LandingMinSpeed + 1.f, LandingHeavySpeed)),
		FVector2f(0.f, 1.f), FallSpeed);
	LandDipPending += FMath::Lerp(LandingMaxDip * 0.35f, LandingMaxDip, Heavy);
	AddCameraTrauma(FMath::Lerp(0.12f, 0.35f, Heavy)); // pequeno -> médio
	if (Heavy > 0.3f)
	{
		if (UJRFXSubsystem* FX = UJRFXSubsystem::Get(this))
		{
			const float HalfHeight = GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
			const FVector Feet = Hit.bBlockingHit ? FVector(Hit.ImpactPoint) : GetActorLocation() - FVector(0.f, 0.f, HalfHeight);
			FX->SpawnDustPuff(Feet, LandingDustColor, FMath::RoundToInt(FMath::Lerp(6.f, 14.f, Heavy)), FMath::Lerp(180.f, 320.f, Heavy));
		}
	}
}

void AJRCharacter::EndHitStop()
{
	if (!bHitStopActive)
	{
		return;
	}
	bHitStopActive = false;
	GetWorldTimerManager().ClearTimer(HitStopTimer);
	if (GetWorld() && FMath::IsNearlyEqual(UGameplayStatics::GetGlobalTimeDilation(this), HitStopDilation, 0.001f))
	{
		UGameplayStatics::SetGlobalTimeDilation(this, 1.f);
	}
}

// ---------------------------------------------------------------- Rifle de precisão e luneta (A-058)

UJRWeaponDefinition* AJRCharacter::GetDefinitionFor(EJRWeaponSlot Slot) const
{
	switch (Slot)
	{
	case EJRWeaponSlot::Pistol: return PistolDefinition.Get();
	case EJRWeaponSlot::Shotgun: return ShotgunDefinition.Get();
	case EJRWeaponSlot::Sniper: return SniperDefinition ? SniperDefinition.Get() : PistolDefinition.Get();
	default: return nullptr;
	}
}

float AJRCharacter::GetScopeFOV() const
{
	return ScopeFOVs.IsValidIndex(ScopeZoomIndex) ? FMath::Clamp(ScopeFOVs[ScopeZoomIndex], 2.f, 90.f) : 20.f;
}

bool AJRCharacter::WantsScope() const
{
	return CurrentSlot == EJRWeaponSlot::Sniper && bWeaponEquipped && bAimHeld && !bWeaponTransition && !bHealing
		&& !bItemWheelOpen && !WeaponComponent->IsReloading() && HealthComponent->GetHealth() > 0.f
		&& !InteractionCamera->IsShotActive() && GetWorld()->GetTimeSeconds() >= ScopeBlockedUntil;
}

void AJRCharacter::UpdateScope(float DeltaTime)
{
	const bool bWantScope = WantsScope();
	const float Before = ScopeAlpha;
	ScopeAlpha = FMath::FInterpConstantTo(ScopeAlpha, bWantScope ? 1.f : 0.f, DeltaTime, 1.f / FMath::Max(0.01f, ScopeBlendTime));
	ScopeTime += DeltaTime;
	if (Before <= 0.f && ScopeAlpha > 0.f)
	{
		if (USoundBase* Zoom = ScopeZoomSound.LoadSynchronous())
		{
			UGameplayStatics::PlaySound2D(this, Zoom, 0.6f);
		}
	}
	// Dentro da luneta a câmera fica dentro do corpo/arma: some para o jogador (sombra continua).
	const bool bHideBody = ScopeAlpha > 0.6f;
	if (bHideBody != bScopeBodyHidden)
	{
		bScopeBodyHidden = bHideBody;
		GetMesh()->SetOwnerNoSee(bHideBody);
		WeaponMesh->SetOwnerNoSee(bHideBody);
	}
	// Fôlego: Shift segura a respiração até HoldBreathSeconds; recupera devagar soltando.
	if (bWantScope && bIsSprinting && !bBreathExhausted)
	{
		BreathLeft = FMath::Max(0.f, BreathLeft - DeltaTime);
		bBreathExhausted = BreathLeft <= 0.f;
	}
	else
	{
		BreathLeft = FMath::Min(HoldBreathSeconds, BreathLeft + DeltaTime * 0.6f);
		if (bBreathExhausted && !bIsSprinting && BreathLeft >= HoldBreathSeconds * 0.5f)
		{
			bBreathExhausted = false;
		}
	}
	// Na luneta anda devagar (e o Shift vira "prender a respiração", não corrida).
	const bool bSlow = ScopeAlpha > 0.5f;
	if (bSlow)
	{
		GetCharacterMovement()->MaxWalkSpeed = WalkSpeed * ScopeMoveSpeedFactor;
	}
	else if (bScopeSlowed)
	{
		GetCharacterMovement()->MaxWalkSpeed = bHealing ? WalkSpeed * HealMoveSpeedFactor : (bIsSprinting ? SprintSpeed : WalkSpeed);
	}
	bScopeSlowed = bSlow;
}

void AJRCharacter::HandleScopeZoomIn()
{
	if (ScopeAlpha > 0.5f && ScopeZoomIndex < ScopeFOVs.Num() - 1)
	{
		++ScopeZoomIndex;
		if (USoundBase* Zoom = ScopeZoomSound.LoadSynchronous())
		{
			UGameplayStatics::PlaySound2D(this, Zoom, 0.5f, 1.15f);
		}
	}
}

void AJRCharacter::HandleScopeZoomOut()
{
	if (ScopeAlpha > 0.5f && ScopeZoomIndex > 0)
	{
		--ScopeZoomIndex;
		if (USoundBase* Zoom = ScopeZoomSound.LoadSynchronous())
		{
			UGameplayStatics::PlaySound2D(this, Zoom, 0.5f, 0.9f);
		}
	}
}

// ---------------------------------------------------------------------------------------------------------------
// [A-086] Escalar (mantle): o que se vê é o que se sobe. Sem caixa invisível: tudo pela colisão das malhas.

void AJRCharacter::HandleJumpPressed()
{
	if (IsRidingBike()) // [A-097] de bicicleta: só anda, olha e desce (E)
	{
		return;
	}
	if (bMantling)
	{
		return;
	}
	if (!TryMantle())
	{
		Jump();
	}
}

bool AJRCharacter::TryMantle()
{
	UCharacterMovementComponent* Move = GetCharacterMovement();
	UWorld* World = GetWorld();
	UCapsuleComponent* Capsule = GetCapsuleComponent();
	if (!Move || !World || !Capsule || !(Move->IsMovingOnGround() || Move->IsFalling()))
	{
		return false;
	}
	const float Radius = Capsule->GetScaledCapsuleRadius();
	const float HalfHeight = Capsule->GetScaledCapsuleHalfHeight();
	const FVector Feet = GetActorLocation() - FVector(0.f, 0.f, HalfHeight);
	FVector Fwd = GetActorForwardVector().GetSafeNormal2D();
	const FVector Wish = Move->GetCurrentAcceleration().GetSafeNormal2D();
	if (!Wish.IsNearlyZero())
	{
		Fwd = Wish; // vai para onde o jogador está empurrando
	}
	FCollisionQueryParams Query(SCENE_QUERY_STAT(JRMantle), false, this);
	// 1) Tem algo na frente, na altura do peito?
	FHitResult Wall;
	const FVector Chest = Feet + FVector(0.f, 0.f, 110.f);
	if (!World->SweepSingleByChannel(Wall, Chest, Chest + Fwd * 90.f, FQuat::Identity, ECC_Pawn,
		FCollisionShape::MakeSphere(Radius * 0.6f), Query))
	{
		return false;
	}
	if (FVector::DotProduct(Wall.ImpactNormal.GetSafeNormal2D(), -Fwd) < 0.5f || Cast<APawn>(Wall.GetActor()))
	{
		return false; // parede muito de lado, ou é um personagem
	}
	// 2) Onde fica o topo? Desce de cima até achar chão firme, um pouco depois da borda.
	const FVector Over = Wall.ImpactPoint + Fwd * (Radius + 25.f);
	FHitResult Top;
	const float MaxClimb = 265.f;
	if (!World->LineTraceSingleByChannel(Top, FVector(Over.X, Over.Y, Feet.Z + MaxClimb + 40.f), FVector(Over.X, Over.Y, Feet.Z + 40.f),
		ECC_Pawn, Query))
	{
		return false;
	}
	const float Climb = static_cast<float>(Top.ImpactPoint.Z - Feet.Z);
	if (Climb < 55.f || Climb > MaxClimb || Top.ImpactNormal.Z < 0.7f || Top.bStartPenetrating)
	{
		return false;
	}
	// 3) O corpo cabe lá em cima?
	const FVector Target = Top.ImpactPoint + FVector(0.f, 0.f, HalfHeight + 3.f);
	if (World->OverlapBlockingTestByChannel(Target, FQuat::Identity, ECC_Pawn, FCollisionShape::MakeCapsule(Radius, HalfHeight), Query))
	{
		return false;
	}
	MantleFrom = GetActorLocation();
	MantleTo = Target;
	MantleStart = World->GetTimeSeconds();
	MantleDuration = FMath::GetMappedRangeValueClamped(FVector2D(55.f, MaxClimb), FVector2D(0.28f, 0.48f), Climb);
	bMantling = true;
	Move->StopMovementImmediately();
	Move->SetMovementMode(MOVE_Flying);
	World->GetTimerManager().SetTimer(MantleTimer, this, &AJRCharacter::TickMantle, 1.f / 120.f, true);
	return true;
}

void AJRCharacter::TickMantle()
{
	UWorld* World = GetWorld();
	if (!World)
	{
		return;
	}
	const float A = FMath::Clamp(static_cast<float>(World->GetTimeSeconds() - MantleStart) / FMath::Max(0.05f, MantleDuration), 0.f, 1.f);
	// Sobe primeiro (60% do tempo), depois avança por cima da borda: lê como "pegar e se puxar".
	const float Up = FMath::InterpEaseOut(0.f, 1.f, FMath::Min(1.f, A / 0.6f), 2.5f);
	const float Fwd = FMath::InterpEaseInOut(0.f, 1.f, FMath::Clamp((A - 0.35f) / 0.65f, 0.f, 1.f), 2.f);
	FVector P;
	P.X = FMath::Lerp(MantleFrom.X, MantleTo.X, Fwd);
	P.Y = FMath::Lerp(MantleFrom.Y, MantleTo.Y, Fwd);
	P.Z = FMath::Lerp(MantleFrom.Z, MantleTo.Z + 8.f, Up);
	SetActorLocation(P, false, nullptr, ETeleportType::None);
	if (A >= 1.f)
	{
		World->GetTimerManager().ClearTimer(MantleTimer);
		bMantling = false;
		if (UCharacterMovementComponent* Move = GetCharacterMovement())
		{
			Move->SetMovementMode(MOVE_Walking);
		}
	}
}

// Copyright utrazin. All Rights Reserved.

#include "FX/JRDamageFXComponent.h"
#include "FX/JRGameFeel.h"
#include "Camera/PlayerCameraManager.h"
#include "CoreGlobals.h"
#include "Combat/JRHealthComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/DecalComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "FX/JRFXSubsystem.h"
#include "GameFramework/Character.h"
#include "GameFramework/PlayerController.h"
#include "Kismet/GameplayStatics.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Sound/SoundBase.h"
#include "TimerManager.h"

namespace JRDamageFX
{
	const FName ColorParam(TEXT("Color"));
	const FName EmissiveParam(TEXT("Emissive"));
}

UJRDamageFXComponent::UJRDamageFXComponent()
{
	PrimaryComponentTick.bCanEverTick = false;
}

void UJRDamageFXComponent::SetBloodType(EJRBloodType NewType)
{
	BloodType = NewType;
	if (NewType == EJRBloodType::Zombie)
	{
		// Azul-ciano brilhante (sangue alienígena) e flash no corpo ao levar tiro.
		// [A-086] menos brilho: as manchas acesas no chão viravam "pontinhos azuis" espalhados que parecem lixo.
		BloodColor = FLinearColor(0.02f, 0.3f, 0.55f, 1.f);
		BloodEmissive = 0.35f;
		bHitFlash = true;
		MaxWounds = 5;
		LowHealthDripFraction = 0.f; // zumbi não deixa rastro por vida baixa (só logo depois do acerto)
	}
	else
	{
		BloodColor = FLinearColor(0.32f, 0.01f, 0.01f, 1.f);
		BloodEmissive = 0.f;
		bHitFlash = false;
		MaxWounds = 8;
		LowHealthDripFraction = 0.35f;
	}
}

void UJRDamageFXComponent::BeginPlay()
{
	Super::BeginPlay();
	Rand.GenerateNewSeed();
	if (AActor* Owner = GetOwner())
	{
		Owner->OnTakePointDamage.AddDynamic(this, &UJRDamageFXComponent::HandlePointDamage);
		Owner->OnTakeAnyDamage.AddDynamic(this, &UJRDamageFXComponent::HandleAnyDamage);
		if (UJRHealthComponent* Health = Owner->FindComponentByClass<UJRHealthComponent>())
		{
			OwnerHealth = Health;
			Health->OnHealthChanged.AddDynamic(this, &UJRDamageFXComponent::HandleHealthChanged);
		}
	}
}

void UJRDamageFXComponent::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
	if (UWorld* World = GetWorld())
	{
		World->GetTimerManager().ClearTimer(DripTimer);
		World->GetTimerManager().ClearTimer(WoundTimer);
		World->GetTimerManager().ClearTimer(FlashTimer);
	}
	Super::EndPlay(EndPlayReason);
}

USkeletalMeshComponent* UJRDamageFXComponent::GetBodyMesh() const
{
	const AActor* Owner = GetOwner();
	if (const ACharacter* Char = Cast<ACharacter>(Owner))
	{
		return Char->GetMesh();
	}
	return Owner ? Owner->FindComponentByClass<USkeletalMeshComponent>() : nullptr;
}

bool UJRDamageFXComponent::IsNearViewer(float MaxDistance) const
{
	const UWorld* World = GetWorld();
	const APlayerController* PC = World ? World->GetFirstPlayerController() : nullptr;
	if (!PC || !PC->PlayerCameraManager || !GetOwner())
	{
		return true;
	}
	return FVector::DistSquared(PC->PlayerCameraManager->GetCameraLocation(), GetOwner()->GetActorLocation()) < FMath::Square(MaxDistance);
}

bool UJRDamageFXComponent::FindBodyHit(AActor* Target, const FVector& From, float BandMin, float BandMax, FHitResult& OutHit)
{
	ACharacter* Char = Cast<ACharacter>(Target);
	USkeletalMeshComponent* BodyMesh = Char ? Char->GetMesh() : (Target ? Target->FindComponentByClass<USkeletalMeshComponent>() : nullptr);
	if (!Target || !BodyMesh)
	{
		return false;
	}
	FVector Center = BodyMesh->Bounds.Origin;
	float Half = static_cast<float>(BodyMesh->Bounds.BoxExtent.Z);
	if (Char && !BodyMesh->IsSimulatingPhysics() && Char->GetCapsuleComponent())
	{
		Center = Char->GetCapsuleComponent()->GetComponentLocation();
		Half = Char->GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
	}
	FVector Side = From - Center;
	Side.Z = 0.0;
	if (!Side.Normalize())
	{
		Side = Target->GetActorForwardVector();
	}
	const FVector Right = FVector::CrossProduct(FVector::UpVector, Side);
	const float Height = FMath::FRandRange(FMath::Min(BandMin, BandMax), FMath::Max(BandMin, BandMax)) * Half;
	const FVector Axis = Center + FVector(0.f, 0.f, Height) + Right * FMath::FRandRange(-12.f, 12.f);
	FCollisionQueryParams Query(SCENE_QUERY_STAT(JRBodyHit), true);
	// De fora (lado de quem bateu) até passar do eixo do corpo: acerta a pele (corpos do Physics Asset).
	if (BodyMesh->LineTraceComponent(OutHit, Axis + Side * 150.f, Axis - Side * 25.f, Query))
	{
		return true;
	}
	FVector BoneLocation = Axis;
	const FName Bone = BodyMesh->FindClosestBone(Axis, &BoneLocation);
	if (Bone.IsNone())
	{
		return false;
	}
	OutHit = FHitResult();
	OutHit.bBlockingHit = true;
	OutHit.ImpactPoint = BoneLocation + Side * 8.f;
	OutHit.Location = OutHit.ImpactPoint;
	OutHit.ImpactNormal = Side;
	OutHit.Normal = Side;
	OutHit.BoneName = Bone;
	OutHit.Component = BodyMesh;
	OutHit.HitObjectHandle = FActorInstanceHandle(Target);
	return true;
}

void UJRDamageFXComponent::HandlePointDamage(AActor* DamagedActor, float Damage, AController* InstigatedBy, FVector HitLocation,
	UPrimitiveComponent* FHitComponent, FName BoneName, FVector ShotFromDirection, const UDamageType* DamageType,
	AActor* DamageCauser)
{
	LastPointDamageFrame = GFrameCounter;
	PlayHit(HitLocation, ShotFromDirection, BoneName, FHitComponent, Damage, DamageCauser);
}

void UJRDamageFXComponent::HandleAnyDamage(AActor* DamagedActor, float Damage, const UDamageType* DamageType,
	AController* InstigatedBy, AActor* DamageCauser)
{
	// O dano pontual chega pelos dois eventos no mesmo quadro: o pontual já cuidou do efeito.
	if (GFrameCounter == LastPointDamageFrame || !DamageCauser || DamageCauser == GetOwner())
	{
		return; // abismo/ácido sem causador: sem sangue espirrando
	}
	const FVector From = DamageCauser->GetActorLocation();
	FHitResult Hit;
	if (FindBodyHit(GetOwner(), From, -0.6f, 0.7f, Hit))
	{
		PlayHit(Hit.ImpactPoint, (FVector(Hit.ImpactPoint) - From).GetSafeNormal(), Hit.BoneName, Hit.GetComponent(), Damage, DamageCauser);
	}
}

void UJRDamageFXComponent::HandleHealthChanged(UJRHealthComponent* Health, float NewHealth, float Delta)
{
	if (Delta > 0.f && Health)
	{
		// Curou: os ferimentos fecham (todos ao encher a vida; senão um a cada 20 de vida).
		if (NewHealth >= Health->GetMaxHealth() * 0.99f)
		{
			ClearWounds();
		}
		else
		{
			for (int32 Count = FMath::Max(1, FMath::FloorToInt(Delta / 20.f)); Count > 0 && Wounds.Num() > 0; --Count)
			{
				RemoveWound(0);
			}
		}
		return;
	}
	if (Delta < 0.f && NewHealth > 0.f && LowHealthDripFraction > 0.f && Health
		&& Health->GetHealthNormalized() < LowHealthDripFraction)
	{
		EnsureDripTimer();
	}
}

void UJRDamageFXComponent::PlayHit(const FVector& Point, const FVector& ShotDir, FName Bone, UPrimitiveComponent* HitComp,
	float Damage, AActor* Causer)
{
	AActor* Owner = GetOwner();
	UWorld* World = GetWorld();
	if (!Owner || !World)
	{
		return;
	}
	const double Now = World->GetTimeSeconds();
	LastHitTime = Now;

	// Direção do golpe (HUD do herói).
	if (Causer && Causer != Owner)
	{
		RecentHits.RemoveAll([Now](const FJRDamageIndicator& I) { return Now - I.Time > 2.0; });
		FJRDamageIndicator& Indicator = RecentHits.AddDefaulted_GetRef();
		Indicator.From = Causer->GetActorLocation();
		Indicator.Time = Now;
		Indicator.Amount = Damage;
		if (RecentHits.Num() > 6)
		{
			RecentHits.RemoveAt(0);
		}
	}

	FVector Dir = ShotDir.GetSafeNormal();
	if (Dir.IsNearlyZero())
	{
		Dir = Causer ? (Owner->GetActorLocation() - Causer->GetActorLocation()).GetSafeNormal() : -Owner->GetActorForwardVector();
	}
	USkeletalMeshComponent* BodyMesh = Cast<USkeletalMeshComponent>(HitComp);
	if (!BodyMesh || BodyMesh->GetOwner() != Owner)
	{
		BodyMesh = GetBodyMesh();
	}
	FVector Surface = Point;
	FVector Normal = -Dir;
	FName UseBone = Bone;
	if (BodyMesh)
	{
		// Traço curto contra o próprio corpo: ponto e normal exatos da pele (corpos do Physics Asset).
		FHitResult Exact;
		FCollisionQueryParams Query(SCENE_QUERY_STAT(JRWoundTrace), true);
		const bool bExact = BodyMesh->LineTraceComponent(Exact, Point - Dir * 40.f, Point + Dir * 15.f, Query);
		if (bExact)
		{
			Surface = Exact.ImpactPoint;
			Normal = Exact.ImpactNormal;
			if (!Exact.BoneName.IsNone())
			{
				UseBone = Exact.BoneName;
			}
		}
		if (UseBone.IsNone() || BodyMesh->GetBoneIndex(UseBone) == INDEX_NONE)
		{
			UseBone = BodyMesh->FindClosestBone(Point);
		}
		// [A-085] sem Physics Asset o traço na pele falha e o ponto fica na cápsula (sangue "flutuando"
		// ao lado do corpo). Puxa o ponto para junto do osso mais perto: a ferida e o jato saem do corpo.
		if (!bExact && !UseBone.IsNone() && BodyMesh->GetBoneIndex(UseBone) != INDEX_NONE)
		{
			const FVector BoneLoc = BodyMesh->GetBoneLocation(UseBone);
			const FVector Off = Point - BoneLoc;
			Surface = BoneLoc + Off.GetClampedToMaxSize(6.f); // [A-088] ferida mais colada no osso
			Normal = Off.IsNearlyZero() ? -Dir : Off.GetSafeNormal();
		}
	}

	const float DamageScale = FMath::Clamp(Damage / 25.f, 0.5f, 2.f);
	UJRFXSubsystem* FX = UJRFXSubsystem::Get(this);
	if (FX && IsNearViewer(6000.f))
	{
		FX->SpawnBloodSpray(Surface, Dir, Normal, BloodColor, BloodEmissive, FMath::RoundToInt(SprayCount * DamageScale), SpraySpeed);
		// Mancha atrás do acerto: parede (na direção do tiro) ou, sem parede, no chão.
		FCollisionObjectQueryParams Objects;
		Objects.AddObjectTypesToQuery(ECC_WorldStatic);
		Objects.AddObjectTypesToQuery(ECC_WorldDynamic);
		FCollisionQueryParams Query(SCENE_QUERY_STAT(JRSplatter), false, Owner);
		FHitResult Wall;
		const float Size = SplatterSize * Rand.FRandRange(0.7f, 1.2f) * FMath::Sqrt(DamageScale);
		if (World->LineTraceSingleByObjectType(Wall, Surface + Dir * 5.f, Surface + Dir * 250.f, Objects, Query))
		{
			FX->SpawnDecal(EJRDecalKind::Blood, Wall.ImpactPoint, Wall.ImpactNormal, Size, BloodColor, BloodEmissive, 30.f);
		}
		else
		{
			// [A-088] mancha de chão perto do corpo (antes até 1,4 m: parecia sangue solto em volta)
			const FVector Drop = Surface + FVector(Dir.X, Dir.Y, 0.0).GetSafeNormal() * Rand.FRandRange(20.f, 75.f);
			FHitResult Floor;
			if (World->LineTraceSingleByObjectType(Floor, Drop, Drop - FVector(0.f, 0.f, 400.f), Objects, Query))
			{
				FX->SpawnDecal(EJRDecalKind::Blood, Floor.ImpactPoint, Floor.ImpactNormal, Size * 0.8f, BloodColor, BloodEmissive, 30.f);
			}
		}
	}
	if (BodyMesh && MaxWounds > 0 && !NoWoundBones.Contains(UseBone))
	{
		AddWound(BodyMesh, UseBone, Surface, Normal);
	}
	EnsureDripTimer();
	if (bHitFlash)
	{
		StartHitFlash();
	}
	if (USoundBase* Sound = FleshHitSound.LoadSynchronous())
	{
		UGameplayStatics::PlaySoundAtLocation(this, Sound, Surface, 0.8f, Rand.FRandRange(0.9f, 1.1f));
	}
}

void UJRDamageFXComponent::AddWound(USkeletalMeshComponent* BodyMesh, FName Bone, const FVector& Point, const FVector& Normal)
{
	UJRFXSubsystem* FX = UJRFXSubsystem::Get(this);
	AActor* Owner = GetOwner();
	if (!FX || !Owner || !BodyMesh)
	{
		return;
	}
	while (Wounds.Num() >= MaxWounds && Wounds.Num() > 0)
	{
		RemoveWound(0);
	}
	const FVector N = Normal.IsNearlyZero() ? FVector::UpVector : Normal.GetSafeNormal();
	const float Size = WoundSize * Rand.FRandRange(0.8f, 1.25f);
	FJRWoundMark Mark;
	Mark.Time = GetWorld()->GetTimeSeconds();
	const FAttachmentTransformRules Attach = FAttachmentTransformRules::KeepWorldTransform;

	UMaterialInterface* DecalMat = FX->GetBloodDecalMaterial();
	if (bWoundDecal && DecalMat)
	{
		UDecalComponent* Decal = NewObject<UDecalComponent>(Owner);
		Decal->SetDecalMaterial(DecalMat);
		// Caixa rasa (4 cm para cada lado da pele) para não manchar o outro lado do membro.
		Decal->DecalSize = FVector(4.f, Size * 0.5f, Size * 0.5f);
		Decal->SetFadeScreenSize(0.001f);
		Decal->RegisterComponent();
		FRotator Rot = (-N).Rotation();
		Rot.Roll = Rand.FRandRange(0.f, 360.f);
		Decal->SetWorldLocationAndRotation(Point, Rot);
		Decal->AttachToComponent(BodyMesh, Attach, Bone);
		if (UMaterialInstanceDynamic* MID = Decal->CreateDynamicMaterialInstance())
		{
			MID->SetVectorParameterValue(JRDamageFX::ColorParam, BloodColor);
			MID->SetScalarParameterValue(JRDamageFX::EmissiveParam, BloodEmissive);
		}
		Decal->SetFadeOut(WoundLifetime, 2.f, false);
		Mark.Decal = Decal;
	}
	UMaterialInterface* BlobMat = FX->GetBloodMaterial();
	UStaticMesh* BlobMesh = FX->GetSphereMesh();
	if (bWoundBlob && BlobMat && BlobMesh)
	{
		UStaticMeshComponent* Blob = NewObject<UStaticMeshComponent>(Owner);
		Blob->SetMobility(EComponentMobility::Movable);
		Blob->SetStaticMesh(BlobMesh);
		Blob->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		Blob->SetGenerateOverlapEvents(false);
		Blob->SetCastShadow(false);
		Blob->bReceivesDecals = false;
		Blob->SetCanEverAffectNavigation(false);
		Blob->RegisterComponent();
		const float BlobSize = Size * 0.45f;
		// Esfera achatada deitada na pele (Z = normal), um tico para fora.
		Blob->SetWorldTransform(FTransform(FRotationMatrix::MakeFromZ(N).Rotator(), Point + N * 0.3f,
			FVector(BlobSize, BlobSize * 0.8f, BlobSize * 0.22f) / 100.f));
		Blob->AttachToComponent(BodyMesh, Attach, Bone);
		UMaterialInstanceDynamic* MID = UMaterialInstanceDynamic::Create(BlobMat, Blob);
		MID->SetVectorParameterValue(JRDamageFX::ColorParam, BloodColor * 0.8f);
		MID->SetScalarParameterValue(JRDamageFX::EmissiveParam, BloodEmissive);
		Blob->SetMaterial(0, MID);
		Mark.Blob = Blob;
	}
	if (!Mark.Blob && !Mark.Decal)
	{
		return;
	}
	Wounds.Add(Mark);
	FTimerManager& Timers = GetWorld()->GetTimerManager();
	if (!Timers.IsTimerActive(WoundTimer))
	{
		Timers.SetTimer(WoundTimer, this, &UJRDamageFXComponent::UpdateWounds, 1.f, true);
	}
}

void UJRDamageFXComponent::RemoveWound(int32 Index)
{
	if (!Wounds.IsValidIndex(Index))
	{
		return;
	}
	FJRWoundMark& Mark = Wounds[Index];
	if (IsValid(Mark.Blob))
	{
		Mark.Blob->DestroyComponent();
	}
	if (IsValid(Mark.Decal))
	{
		Mark.Decal->DestroyComponent();
	}
	Wounds.RemoveAt(Index);
}

void UJRDamageFXComponent::ClearWounds()
{
	while (Wounds.Num() > 0)
	{
		RemoveWound(Wounds.Num() - 1);
	}
}

void UJRDamageFXComponent::UpdateWounds()
{
	const double Now = GetWorld()->GetTimeSeconds();
	for (int32 i = Wounds.Num() - 1; i >= 0; --i)
	{
		// O decal some sozinho (fade); a bolha sai 1 s depois do início do fade.
		if (Now - Wounds[i].Time > WoundLifetime + 1.0 || (!IsValid(Wounds[i].Blob) && !IsValid(Wounds[i].Decal)))
		{
			RemoveWound(i);
		}
	}
	if (Wounds.Num() == 0)
	{
		GetWorld()->GetTimerManager().ClearTimer(WoundTimer);
	}
}

void UJRDamageFXComponent::EnsureDripTimer()
{
	FTimerManager& Timers = GetWorld()->GetTimerManager();
	if (!Timers.IsTimerActive(DripTimer))
	{
		Timers.SetTimer(DripTimer, this, &UJRDamageFXComponent::Drip, DripInterval, true, DripInterval * Rand.FRandRange(0.3f, 1.f));
	}
}

void UJRDamageFXComponent::Drip()
{
	const double Now = GetWorld()->GetTimeSeconds();
	const UJRHealthComponent* Health = OwnerHealth.Get();
	const bool bRecent = Now - LastHitTime < DripAfterHit;
	const bool bLow = Health && !Health->IsDead() && LowHealthDripFraction > 0.f
		&& Health->GetHealthNormalized() < LowHealthDripFraction;
	if (!bRecent && !bLow)
	{
		GetWorld()->GetTimerManager().ClearTimer(DripTimer);
		return;
	}
	UJRFXSubsystem* FX = UJRFXSubsystem::Get(this);
	if (!FX || !IsNearViewer(DripMaxDistance))
	{
		return;
	}
	// Pinga de uma ferida qualquer (sem ferida: da cintura).
	FVector From = GetOwner()->GetActorLocation();
	if (Wounds.Num() > 0)
	{
		const FJRWoundMark& Mark = Wounds[Rand.RandRange(0, Wounds.Num() - 1)];
		if (IsValid(Mark.Blob))
		{
			From = Mark.Blob->GetComponentLocation();
		}
		else if (IsValid(Mark.Decal))
		{
			From = Mark.Decal->GetComponentLocation();
		}
	}
	FX->SpawnBloodDrop(From + FVector(Rand.FRandRange(-2.f, 2.f), Rand.FRandRange(-2.f, 2.f), -1.f), BloodColor, BloodEmissive,
		DripDecalSize, GetOwner());
}

void UJRDamageFXComponent::StartHitFlash()
{
	USkeletalMeshComponent* BodyMesh = GetBodyMesh();
	UJRFXSubsystem* FX = UJRFXSubsystem::Get(this);
	UMaterialInterface* FlashMat = FX ? FX->GetHitFlashMaterial() : nullptr;
	if (!BodyMesh || !FlashMat)
	{
		return;
	}
	if (!FlashMID)
	{
		FlashMID = UMaterialInstanceDynamic::Create(FlashMat, this);
	}
	// [A-073] acessibilidade (jr.Feel.ReduceFlash 1): cor mais escura e metade do tempo
	const bool bReduce = JRFeel::ReduceFlash();
	FlashMID->SetVectorParameterValue(JRDamageFX::ColorParam, bReduce
		? FLinearColor(HitFlashColor.R * 0.35f, HitFlashColor.G * 0.35f, HitFlashColor.B * 0.35f, HitFlashColor.A) : HitFlashColor);
	if (!bFlashing)
	{
		SavedOverlay = BodyMesh->GetOverlayMaterial();
	}
	BodyMesh->SetOverlayMaterial(FlashMID);
	bFlashing = true;
	GetWorld()->GetTimerManager().SetTimer(FlashTimer, this, &UJRDamageFXComponent::EndHitFlash,
		FMath::Max(0.02f, HitFlashTime * (bReduce ? 0.5f : 1.f)), false);
}

void UJRDamageFXComponent::EndHitFlash()
{
	if (USkeletalMeshComponent* BodyMesh = GetBodyMesh())
	{
		BodyMesh->SetOverlayMaterial(SavedOverlay);
	}
	SavedOverlay = nullptr;
	bFlashing = false;
}

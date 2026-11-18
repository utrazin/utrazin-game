// Copyright utrazin. All Rights Reserved.

#include "Combat/JRWeaponComponent.h"
#include "AI/JRAimPrediction.h"
#include "Combat/JRWeaponDefinition.h"
#include "Combat/JRHealthComponent.h"
#include "Characters/JRCharacter.h" // [A-073] sensação do abate a distância
#include "Components/PrimitiveComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "FX/JRFXSubsystem.h"
#include "HAL/IConsoleManager.h"
#include "Sound/SoundAttenuation.h"
#include "Sound/SoundBase.h"
#include "GameFramework/Controller.h"
#include "GameFramework/Pawn.h"
#include "JogoResgate.h"
#include "Kismet/GameplayStatics.h"
#include "DrawDebugHelpers.h"
#include "TimerManager.h"

namespace
{
	// Linhas de depuração do tiro (desligadas no jogo; "jr.Weapon.Debug 1" no console liga).
	TAutoConsoleVariable<int32> CVarJRWeaponDebug(TEXT("jr.Weapon.Debug"), 0,
		TEXT("1 = desenha as linhas de depuração dos tiros (traço da câmera e acertos)."), ECVF_Cheat);
}

UJRWeaponComponent::UJRWeaponComponent()
{
	PrimaryComponentTick.bCanEverTick = false;
}

void UJRWeaponComponent::BeginPlay()
{
	Super::BeginPlay();
	SpreadStream.GenerateNewSeed();
	EquipDefinition(Definition);
}

void UJRWeaponComponent::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
	CancelAll();
	Super::EndPlay(EndPlayReason);
}

void UJRWeaponComponent::EquipDefinition(UJRWeaponDefinition* NewDefinition)
{
	CancelAll();
	Definition = NewDefinition;
	if (Definition)
	{
		Ammo.Initialize(Definition->MagazineSize, Definition->StartingReserve);
		OnAmmoChanged.Broadcast(Ammo.Magazine, Ammo.Reserve);
	}
}

void UJRWeaponComponent::SwitchDefinitionKeepAmmo(UJRWeaponDefinition* NewDefinition)
{
	if (!NewDefinition || NewDefinition == Definition)
	{
		return;
	}
	CancelAll();
	const int32 Total = Ammo.Magazine + Ammo.Reserve;
	Definition = NewDefinition;
	Ammo.MagazineSize = FMath::Max(1, Definition->MagazineSize);
	Ammo.Magazine = FMath::Min(Ammo.MagazineSize, Total);
	Ammo.Reserve = FMath::Max(0, Total - Ammo.Magazine);
	OnAmmoChanged.Broadcast(Ammo.Magazine, Ammo.Reserve);
}

void UJRWeaponComponent::SetBoost(float InDamageMultiplier, float InFireRateMultiplier)
{
	DamageMultiplier = FMath::Max(0.1f, InDamageMultiplier);
	FireRateMultiplier = FMath::Max(0.1f, InFireRateMultiplier);
	if (bWantsToFire)
	{
		StartFire(); // reinicia o timer com a nova cadência
	}
}

void UJRWeaponComponent::StartFire()
{
	if (!Definition || bReloading)
	{
		return;
	}
	bWantsToFire = true;
	UWorld* World = GetWorld();
	const float Interval = 1.f / (Definition->FireRate * FireRateMultiplier);
	const double Elapsed = World->GetTimeSeconds() - LastFireTime;
	const float FirstDelay = FMath::Max(0.f, Interval - static_cast<float>(Elapsed));
	World->GetTimerManager().SetTimer(FireTimer, this, &UJRWeaponComponent::FireOnce, Interval, true, FirstDelay);
}

void UJRWeaponComponent::StopFire()
{
	bWantsToFire = false;
	if (UWorld* World = GetWorld())
	{
		World->GetTimerManager().ClearTimer(FireTimer);
	}
}

bool UJRWeaponComponent::StartReload()
{
	if (!Definition || bReloading || !Ammo.CanReload())
	{
		return false;
	}
	StopFire();
	bReloading = true;
	OnReloadStateChanged.Broadcast(true);
	if (Definition->ReloadSound && GetOwner())
	{
		PlayWeaponSound(Definition->ReloadSound, GetOwner()->GetActorLocation(), 0.8f, false);
	}
	GetWorld()->GetTimerManager().SetTimer(ReloadTimer, this, &UJRWeaponComponent::FinishReload, Definition->ReloadTime, false);
	return true;
}

void UJRWeaponComponent::FinishReload()
{
	bReloading = false;
	Ammo.Reload();
	OnReloadStateChanged.Broadcast(false);
	OnAmmoChanged.Broadcast(Ammo.Magazine, Ammo.Reserve);
}

void UJRWeaponComponent::AddReserveAmmo(int32 Amount)
{
	Ammo.AddReserve(Amount);
	OnAmmoChanged.Broadcast(Ammo.Magazine, Ammo.Reserve);
}

void UJRWeaponComponent::CancelAll()
{
	StopFire();
	if (bReloading)
	{
		bReloading = false;
		if (UWorld* World = GetWorld())
		{
			World->GetTimerManager().ClearTimer(ReloadTimer);
		}
		OnReloadStateChanged.Broadcast(false);
	}
}

bool UJRWeaponComponent::GetAimViewPoint(FVector& OutLocation, FRotator& OutRotation) const
{
	const APawn* Pawn = Cast<APawn>(GetOwner());
	if (!Pawn)
	{
		return false;
	}
	if (const AController* Controller = Pawn->GetController())
	{
		Controller->GetPlayerViewPoint(OutLocation, OutRotation);
		return true;
	}
	Pawn->GetActorEyesViewPoint(OutLocation, OutRotation);
	return true;
}

bool UJRWeaponComponent::IsLocalPlayerOwner() const
{
	const APawn* Pawn = Cast<APawn>(GetOwner());
	return Pawn && Pawn->IsLocallyControlled() && Pawn->IsPlayerControlled();
}

void UJRWeaponComponent::PlayWeaponSound(USoundBase* Sound, const FVector& Location, float Volume, bool bPitchVariation) const
{
	if (!Sound || !Definition)
	{
		return;
	}
	const float Variance = bPitchVariation ? Definition->PitchVariance : 0.f;
	const float Pitch = 1.f + FMath::FRandRange(-Variance, Variance);
	if (IsLocalPlayerOwner())
	{
		// Jogador: camada 2D "na mão" + a 3D mais baixa (posição e distância para o mundo).
		UGameplayStatics::PlaySound2D(this, Sound, Volume * Player2DVolume, Pitch);
		UGameplayStatics::PlaySoundAtLocation(this, Sound, Location, Volume * 0.5f, Pitch, 0.f, Definition->SoundAttenuation);
		return;
	}
	UGameplayStatics::PlaySoundAtLocation(this, Sound, Location, Volume, Pitch, 0.f, Definition->SoundAttenuation);
}

FVector UJRWeaponComponent::GetMuzzleLocation(const FVector& FallbackDir) const
{
	static const FName MuzzleSocket(TEXT("Muzzle"));
	if (const USceneComponent* Muzzle = MuzzleComponent.Get())
	{
		if (Muzzle->IsVisible())
		{
			if (Muzzle->DoesSocketExist(MuzzleSocket))
			{
				return Muzzle->GetSocketLocation(MuzzleSocket);
			}
			const UStaticMeshComponent* GunMesh = Cast<UStaticMeshComponent>(Muzzle);
			if (GunMesh && GunMesh->GetStaticMesh())
			{
				// Ponta do cano: frente (+X) da caixa da malha, um pouco acima do centro.
				const FBox Box = GunMesh->GetStaticMesh()->GetBoundingBox();
				const FVector Center = Box.GetCenter();
				FVector Local(Box.Max.X, Center.Y, Center.Z + (Box.Max.Z - Center.Z) * 0.25);
				if (Definition)
				{
					Local += Definition->MuzzleOffset;
				}
				return GunMesh->GetComponentTransform().TransformPosition(Local);
			}
			return Muzzle->GetComponentLocation();
		}
	}
	const AActor* Owner = GetOwner();
	return Owner ? Owner->GetActorLocation() + FVector(0.f, 0.f, 50.f) + FallbackDir * 40.f : FVector::ZeroVector;
}

float UJRWeaponComponent::GetCrosshairBloom() const
{
	const UWorld* World = GetWorld();
	if (!World || BloomValue <= 0.f)
	{
		return 0.f;
	}
	const float Since = static_cast<float>(World->GetTimeSeconds() - BloomTime);
	return BloomValue * FMath::Exp(-Since * BloomDecay);
}

void UJRWeaponComponent::NotifyHitConfirmed(bool bKill)
{
	const UWorld* World = GetWorld();
	if (!World)
	{
		return;
	}
	// Abate tem prioridade: um acerto comum logo depois não apaga o "X" vermelho.
	const bool bKeepKill = bLastHitKill && World->GetTimeSeconds() - LastHitConfirmTime < 0.3;
	LastHitConfirmTime = World->GetTimeSeconds();
	bLastHitKill = bKill || bKeepKill;
	if (IsLocalPlayerOwner())
	{
		if (USoundBase* Sound = (bKill ? KillMarkerSound : HitMarkerSound).LoadSynchronous())
		{
			UGameplayStatics::PlaySound2D(this, Sound, bKill ? 0.8f : 0.45f);
		}
	}
}

void UJRWeaponComponent::ApplyPelletHit(const FHitResult& Hit, const FVector& Dir, float Amount, bool bImpactSound)
{
	AActor* Owner = GetOwner();
	AActor* HitActor = Hit.GetActor();
	if (!Owner || !Definition)
	{
		return;
	}
	const UJRHealthComponent* TargetHealth = HitActor ? HitActor->FindComponentByClass<UJRHealthComponent>() : nullptr;
	const bool bWasAlive = TargetHealth && !TargetHealth->IsDead();
	if (HitActor)
	{
		UGameplayStatics::ApplyPointDamage(HitActor, Amount, Dir, Hit, Owner->GetInstigatorController(), Owner, nullptr);
		UPrimitiveComponent* HitComp = Hit.GetComponent();
		if (HitComp && HitComp->IsSimulatingPhysics())
		{
			// Velocidade direta (independe da massa): cone e caixa reagem de forma visível.
			HitComp->AddImpulseAtLocation(Dir * HitImpulse * HitComp->GetMass(), Hit.ImpactPoint, Hit.BoneName);
		}
	}
	// Estouro do plasma: menor em corpos (o sangue aparece), com queimado só em superfícies.
	const bool bBody = HitActor && HitActor->IsA<APawn>();
	if (UJRFXSubsystem* FX = UJRFXSubsystem::Get(this))
	{
		FX->SpawnPlasmaImpact(Hit.ImpactPoint, Hit.ImpactNormal, Definition->PlasmaColor, Definition->PlasmaIntensity,
			Definition->ImpactScale * (bBody ? 0.6f : 1.f), !bBody);
	}
	if (bImpactSound && Definition->ImpactSound)
	{
		UGameplayStatics::PlaySoundAtLocation(this, Definition->ImpactSound, Hit.ImpactPoint, 0.8f,
			FMath::FRandRange(0.9f, 1.1f), 0.f, Definition->SoundAttenuation);
	}
	if (TargetHealth && bWasAlive)
	{
		NotifyHitConfirmed(TargetHealth->IsDead());
		// [A-073] abate a distância: tremorzinho e zoom curto; armas pesadas (escopeta/rifle) congelam 0,04 s.
		// Pistola: só o tremor pequeno (tiro rápido não pode ficar "travando").
		if (TargetHealth->IsDead() && IsLocalPlayerOwner())
		{
			if (AJRCharacter* Hero = Cast<AJRCharacter>(Owner))
			{
				const bool bHeavyGun = Definition->ShakeScale >= 0.4f;
				Hero->PlayFeedback(bHeavyGun ? 0.25f : 0.15f, bHeavyGun ? 0.04f : 0.f, -1.f);
			}
		}
	}
}

void UJRWeaponComponent::FireOnce()
{
	if (!Definition || !bWantsToFire)
	{
		StopFire();
		return;
	}
	if (!Ammo.ConsumeShot())
	{
		StopFire();
		if (!StartReload() && Definition->DryFireSound && GetOwner())
		{
			// Sem célula nenhuma: clique seco.
			PlayWeaponSound(Definition->DryFireSound, GetOwner()->GetActorLocation(), 0.8f, false);
		}
		return;
	}
	UWorld* World = GetWorld();
	LastFireTime = World->GetTimeSeconds();

	FVector ViewLocation;
	FRotator ViewRotation;
	if (!GetAimViewPoint(ViewLocation, ViewRotation))
	{
		return;
	}
	const float Spread = bAiming ? Definition->SpreadHalfAngleDegrees * 0.5f : Definition->SpreadHalfAngleDegrees;
	const FVector Direction = FJRAimPrediction::ApplySpread(ViewRotation.Vector(), Spread, SpreadStream);
	const FVector Muzzle = GetMuzzleLocation(ViewRotation.Vector());
	const bool bDebug = CVarJRWeaponDebug.GetValueOnGameThread() > 0;
	UJRFXSubsystem* FX = UJRFXSubsystem::Get(this);

	FCollisionQueryParams Params(SCENE_QUERY_STAT(JRWeaponTrace), true, GetOwner());
	FHitResult Hit;
	bool bHit = false;
	FVector End = ViewLocation + Direction * Definition->Range;
	const int32 Pellets = FMath::Max(1, Definition->PelletCount);
	const float Amount = Definition->Damage * DamageMultiplier;
	const float BoltSpeed = FMath::Max(1000.f, Definition->BoltSpeed);
	for (int32 Pellet = 0; Pellet < Pellets; ++Pellet)
	{
		const FVector PelletDir = Pellets > 1
			? FJRAimPrediction::ApplySpread(ViewRotation.Vector(), FMath::Max(Spread, Definition->PelletSpreadDegrees), SpreadStream)
			: Direction;
		const FVector PelletEnd = ViewLocation + PelletDir * Definition->Range;
		FHitResult PelletHit;
		bool bPelletHit = World->LineTraceSingleByChannel(PelletHit, ViewLocation, PelletEnd, TraceChannel, Params);
		if (Pellet == 0)
		{
			Hit = PelletHit;
			bHit = bPelletHit;
			End = PelletEnd;
		}
		// Rifle (MaxPierce): atravessa corpos; cada um leva o dano quando o plasma passa por ele. Parede para.
		FCollisionQueryParams PierceParams = Params;
		for (int32 PierceLeft = Definition->MaxPierce; bPelletHit && PierceLeft > 0; --PierceLeft)
		{
			AActor* Pierced = PelletHit.GetActor();
			if (!Pierced || !Pierced->IsA<APawn>())
			{
				break;
			}
			const FHitResult PiercedHit = PelletHit;
			const FVector PiercedDir = PelletDir;
			const float PierceDelay = static_cast<float>(FVector::Dist(Muzzle, FVector(PiercedHit.ImpactPoint))) / BoltSpeed;
			FTimerHandle PierceTimer;
			World->GetTimerManager().SetTimer(PierceTimer, FTimerDelegate::CreateWeakLambda(this, [this, PiercedHit, PiercedDir, Amount]()
			{
				ApplyPelletHit(PiercedHit, PiercedDir, Amount, false);
			}), FMath::Max(0.001f, PierceDelay), false);
			PierceParams.AddIgnoredActor(Pierced);
			bPelletHit = World->LineTraceSingleByChannel(PelletHit, FVector(PiercedHit.ImpactPoint), PelletEnd, TraceChannel, PierceParams);
		}
		const FVector Impact = bPelletHit ? FVector(PelletHit.ImpactPoint) : PelletEnd;
		// Plasma visível do cano até o impacto (o rastro sempre sai da arma, não da câmera).
		if (FX)
		{
			const FVector VisualEnd = bPelletHit ? Impact : Muzzle + (Impact - Muzzle).GetClampedToMaxSize(8000.f);
			FX->SpawnPlasmaBolt(Muzzle, VisualEnd, Definition->PlasmaColor, Definition->PlasmaIntensity, BoltSpeed,
				Definition->BoltLength, Definition->BoltWidth, Definition->TrailLength, Pellet == 0);
		}
		if (bPelletHit)
		{
			// O dano chega junto com o plasma (tempo de voo visual); perto demais é na hora.
			const float Delay = static_cast<float>(FVector::Dist(Muzzle, Impact)) / BoltSpeed;
			const FVector HitDir = PelletDir;
			const bool bSound = Pellet == 0;
			if (Delay < 0.02f)
			{
				ApplyPelletHit(PelletHit, HitDir, Amount, bSound);
			}
			else
			{
				FTimerHandle PelletTimer;
				World->GetTimerManager().SetTimer(PelletTimer, FTimerDelegate::CreateWeakLambda(this, [this, PelletHit, HitDir, Amount, bSound]()
				{
					ApplyPelletHit(PelletHit, HitDir, Amount, bSound);
				}), Delay, false);
			}
		}
		if (bDebug)
		{
			DrawDebugLine(World, ViewLocation, Impact, Pellet == 0 ? FColor::Cyan : FColor::Purple, false, 0.5f, 0, 1.f);
			if (bPelletHit)
			{
				DrawDebugSphere(World, Impact, 8.f, 8, FColor::Red, false, 0.5f);
			}
		}
	}

	// Clarão do cano, som e abertura da mira.
	if (FX)
	{
		const float Flash = Definition->MuzzleFlashScale;
		FX->SpawnFlash(Muzzle, Definition->PlasmaColor, Definition->PlasmaIntensity, 6.f * Flash, 26.f * Flash, 0.06f,
			14000.f * Flash, 450.f * Flash);
		FX->SpawnFlash(Muzzle, FLinearColor::White, Definition->PlasmaIntensity * 0.5f, 3.f * Flash, 12.f * Flash, 0.04f, 0.f, 0.f);
	}
	PlayWeaponSound(Definition->FireSound, Muzzle, Definition->FireVolume, true);
	if (Definition->FollowUpSound && Definition->FollowUpDelay > 0.f)
	{
		FTimerHandle FollowUpTimer;
		World->GetTimerManager().SetTimer(FollowUpTimer, FTimerDelegate::CreateWeakLambda(this, [this]()
		{
			if (Definition && Definition->FollowUpSound && GetOwner())
			{
				PlayWeaponSound(Definition->FollowUpSound, GetOwner()->GetActorLocation(), 0.7f, false);
			}
		}), Definition->FollowUpDelay, false);
	}
	BloomValue = FMath::Min(1.f, GetCrosshairBloom() + Definition->CrosshairBloom);
	BloomTime = World->GetTimeSeconds();

	OnWeaponFired.Broadcast(ViewLocation, bHit ? Hit.ImpactPoint : End);
	OnAmmoChanged.Broadcast(Ammo.Magazine, Ammo.Reserve);
}

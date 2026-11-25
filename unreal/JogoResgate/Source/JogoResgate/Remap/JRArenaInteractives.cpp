// Copyright utrazin. All Rights Reserved.

#include "Remap/JRArenaInteractives.h"
#include "Audio/JRAudio.h"
#include "Combat/JRHealthComponent.h"
#include "Components/BoxComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/PointLightComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/CollisionProfile.h"
#include "Engine/GameInstance.h"
#include "Engine/StaticMesh.h"
#include "FX/JRFXSubsystem.h"
#include "Remap/JRRunSubsystem.h"
#include "UI/JRHUD.h"
#include "UObject/ConstructorHelpers.h"

// ============================================================================ baú

AJRArenaChest::AJRArenaChest()
{
	WeaponInside = EJRWeaponSlot::None;
	AmmoInside = 40;
	HealthInside = 25.f;
	BandagesInside = 1;
	MedkitsInside = 0;

	// Malha do baú do usuário (mesma montagem do build_l01.py): base no chão, dobradiça atrás.
	static ConstructorHelpers::FObjectFinder<UStaticMesh> BaseFinder(TEXT("/Game/Environment/User/Props/SM_PRP_Bau_Base.SM_PRP_Bau_Base"));
	static ConstructorHelpers::FObjectFinder<UStaticMesh> LidFinder(TEXT("/Game/Environment/User/Props/SM_PRP_Bau_Tampa.SM_PRP_Bau_Tampa"));
	if (BaseFinder.Succeeded() && LidFinder.Succeeded())
	{
		Base->SetStaticMesh(BaseFinder.Object);
		Base->SetRelativeLocation(FVector::ZeroVector);
		Base->SetRelativeScale3D(FVector::OneVector);
		LidPivot->SetRelativeLocation(FVector(0.f, -36.1f, 32.9f));
		Lid->SetStaticMesh(LidFinder.Object);
		Lid->SetRelativeLocation(FVector::ZeroVector);
		Lid->SetRelativeScale3D(FVector::OneVector);
	}
}

void AJRArenaChest::Interact_Implementation(AActor* InstigatorActor)
{
	const bool bWasOpened = IsOpened();
	Super::Interact_Implementation(InstigatorActor);
	if (bWasOpened || !IsOpened())
	{
		return;
	}
	const UGameInstance* GI = GetGameInstance();
	UJRRunSubsystem* Run = GI ? GI->GetSubsystem<UJRRunSubsystem>() : nullptr;
	if (Run && Run->IsRunActive() && CreditsPerLevel > 0)
	{
		const int64 Gain = static_cast<int64>(CreditsPerLevel) * FMath::Max(1, Run->GetSectorLevel());
		Run->AddBonusCredits(Gain);
		AJRHUD::Toast(this, FString::Printf(TEXT("Baú: +%lld créditos"), Gain), FLinearColor(1.f, 0.85f, 0.2f));
	}
}

// ============================================================================ ninho

AJRArenaNest::AJRArenaNest()
{
	PrimaryActorTick.bCanEverTick = false;
	// [A-088] Em cima do ninho o zumbi não alcançava (print 8). Cápsula: topo redondo, superfície "não andável" e sem
	// degrau: quem pula em cima escorrega para fora.
	Collision = CreateDefaultSubobject<UCapsuleComponent>(TEXT("Colisao"));
	Collision->InitCapsuleSize(80.f, 95.f);
	Collision->SetCollisionProfileName(UCollisionProfile::BlockAll_ProfileName);
	Collision->SetWalkableSlopeOverride(FWalkableSlopeOverride(EWalkableSlopeBehavior::WalkableSlope_Unwalkable, 0.f));
	Collision->CanCharacterStepUpOn = ECB_No;
	Collision->SetCanEverAffectNavigation(true);
	Collision->SetHiddenInGame(true);
	RootComponent = Collision;

	NestMesh = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Malha"));
	NestMesh->SetupAttachment(Collision);
	NestMesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	NestMesh->SetCanEverAffectNavigation(false);
	static ConstructorHelpers::FObjectFinder<UStaticMesh> SphereFinder(TEXT("/Engine/BasicShapes/Sphere.Sphere"));
	if (SphereFinder.Succeeded())
	{
		NestMesh->SetStaticMesh(SphereFinder.Object); // plano B se o saco de ovos não carregar
	}

	Glow = CreateDefaultSubobject<UPointLightComponent>(TEXT("Brilho"));
	Glow->SetupAttachment(Collision);
	Glow->SetRelativeLocation(FVector(0.f, 0.f, 120.f));
	Glow->SetIntensity(3500.f);
	Glow->SetAttenuationRadius(700.f);
	Glow->SetLightColor(FLinearColor(0.55f, 1.f, 0.35f));
	Glow->SetCastShadows(false);

	HealthComponent = CreateDefaultSubobject<UJRHealthComponent>(TEXT("Vida"));
	// [A-093] ninho novo (Noct Forge 3D + polimento no Blender: monte orgânico com 8 ovos brilhando)
	NestMeshAsset = TSoftObjectPtr<UStaticMesh>(FSoftObjectPath(TEXT("/Game/Environment/User/Arena/SM_ARN_Ninho.SM_ARN_Ninho")));
}

void AJRArenaNest::BeginPlay()
{
	Super::BeginPlay();
	if (UStaticMesh* Loaded = NestMeshAsset.LoadSynchronous())
	{
		NestMesh->SetStaticMesh(Loaded);
	}
	// Ajusta a malha para TargetHeight, apoiada no chão (a raiz é a caixa, centrada a meia altura).
	if (UStaticMesh* Current = NestMesh->GetStaticMesh())
	{
		const FBox LocalBox = Current->GetBoundingBox();
		const FVector Ext = LocalBox.GetSize();
		if (Ext.Z > 1.0)
		{
			const double FitScale = TargetHeight / Ext.Z;
			const FVector Half = Ext * FitScale * 0.5;
			const float CapRadius = static_cast<float>(FMath::Max(40.0, FMath::Max(Half.X, Half.Y)));
			Collision->SetCapsuleSize(CapRadius, static_cast<float>(FMath::Max(Half.Z, static_cast<double>(CapRadius))), true);
			NestMesh->SetRelativeScale3D(FVector(FitScale));
			const FVector LocalCenter = LocalBox.GetCenter() * FitScale;
			NestMesh->SetRelativeLocation(FVector(-LocalCenter.X, -LocalCenter.Y, -Half.Z - LocalBox.Min.Z * FitScale));
			// a raiz fica a meia altura: sobe o ator para a base encostar no chão
			SetActorLocation(GetActorLocation() + FVector(0.f, 0.f, Half.Z));
		}
	}
	HealthComponent->OnDeath.AddDynamic(this, &AJRArenaNest::HandleNestDeath);
}

void AJRArenaNest::SetupNest(float InMaxHealth)
{
	HealthComponent->SetMaxHealth(InMaxHealth, true);
}

void AJRArenaNest::HandleNestDeath(UJRHealthComponent* DeadHealth, AActor* Killer)
{
	if (bNestDestroyed)
	{
		return;
	}
	bNestDestroyed = true;
	const FVector Where = GetActorLocation();
	if (UJRFXSubsystem* FX = UJRFXSubsystem::Get(this))
	{
		FX->SpawnFlash(Where, FLinearColor(0.55f, 1.f, 0.35f), 6.f, 60.f, 420.f, 0.45f, 9000.f, 1200.f);
		FX->SpawnDustPuff(Where, FLinearColor(0.2f, 0.35f, 0.12f), 24, 600.f);
	}
	UJRAudio::PlayAt(this, TEXT("World.Barrel.Explode"), Where);
	Glow->SetVisibility(false);
	NestMesh->SetVisibility(false);
	Collision->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	SetLifeSpan(1.f);
}

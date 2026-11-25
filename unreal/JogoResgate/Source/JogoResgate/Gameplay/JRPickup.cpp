// Copyright utrazin. All Rights Reserved.

#include "Gameplay/JRPickup.h"
#include "Audio/JRAudio.h" // [Áudio/A-061]
#include "Characters/JRCharacter.h"
#include "Combat/JRHealthComponent.h"
#include "Combat/JRInventoryComponent.h"
#include "Combat/JRWeaponComponent.h"
#include "Components/PointLightComponent.h"
#include "Components/SphereComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "FX/JRFXSubsystem.h"
#include "GameFramework/Pawn.h"
#include "GameFramework/RotatingMovementComponent.h"
#include "Kismet/GameplayStatics.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "UObject/ConstructorHelpers.h"
#include "Materials/MaterialInterface.h"
#include "UI/JRHUD.h"
#include "Vehicles/JRVehicleDamageComponent.h"
#include "Vehicles/JRVehiclePawn.h"

namespace
{
	const TCHAR* MeshFor(EJRPickupType T)
	{
		switch (T)
		{
		case EJRPickupType::Health: return TEXT("/Engine/BasicShapes/Sphere.Sphere");
		case EJRPickupType::Nitro: return TEXT("/Engine/BasicShapes/Cylinder.Cylinder");
		case EJRPickupType::Fury: return TEXT("/Engine/BasicShapes/Cone.Cone");
		case EJRPickupType::Repair: return TEXT("/Engine/BasicShapes/Cube.Cube");
		case EJRPickupType::WeaponMelee:
		case EJRPickupType::WeaponPistol:
		case EJRPickupType::WeaponShotgun:
		case EJRPickupType::WeaponSniper: return TEXT("/Engine/BasicShapes/Cone.Cone");
		case EJRPickupType::Bandage: return TEXT("/Engine/BasicShapes/Cylinder.Cylinder");
		case EJRPickupType::Medkit: return TEXT("/Engine/BasicShapes/Cube.Cube");
		default: return TEXT("/Engine/BasicShapes/Cube.Cube");
		}
	}

	/** Modelo do usuário do kit médico (import_user_assets.py). Nulo se ainda não foi importado. */
	UStaticMesh* DefaultMedkitMesh()
	{
		return LoadObject<UStaticMesh>(nullptr, TEXT("/Game/Environment/User/Itens/SM_ITM_KitMedico.SM_ITM_KitMedico"), nullptr,
			LOAD_NoWarn | LOAD_Quiet);
	}

	/** [A-082] Carrega a malha padrão sem aviso no log (ainda não importada = nulo, cai no visual antigo). */
	UStaticMesh* LoadSoftMesh(const TSoftObjectPtr<UStaticMesh>& Soft)
	{
		if (Soft.IsNull())
		{
			return nullptr;
		}
		if (UStaticMesh* Loaded = Soft.Get())
		{
			return Loaded;
		}
		return LoadObject<UStaticMesh>(nullptr, *Soft.ToSoftObjectPath().ToString(), nullptr, LOAD_NoWarn | LOAD_Quiet);
	}

	TSoftObjectPtr<UStaticMesh> SoftMesh(const TCHAR* Path)
	{
		return TSoftObjectPtr<UStaticMesh>(FSoftObjectPath(Path));
	}

	FLinearColor ColorFor(EJRPickupType T)
	{
		switch (T)
		{
		case EJRPickupType::Health: return FLinearColor(1.f, 0.12f, 0.15f);
		case EJRPickupType::Nitro: return FLinearColor(0.1f, 0.55f, 1.f);
		case EJRPickupType::Fury: return FLinearColor(0.75f, 0.2f, 1.f);
		case EJRPickupType::Repair: return FLinearColor(0.2f, 1.f, 0.35f);
		case EJRPickupType::WeaponMelee:
		case EJRPickupType::WeaponPistol:
		case EJRPickupType::WeaponShotgun:
		case EJRPickupType::WeaponSniper: return FLinearColor(0.2f, 1.f, 0.9f);
		case EJRPickupType::Bandage: return FLinearColor(0.95f, 0.9f, 0.77f); // creme
		case EJRPickupType::Medkit: return FLinearColor(0.9f, 0.25f, 0.16f);
		default: return FLinearColor(1.f, 0.8f, 0.1f);
		}
	}

	// [A-082] 2*pi em float (UE_TWO_PI é double e misturaria tipos no FRandRange/Sin)
	constexpr float JRPickupTwoPi = 6.2831853f;

	// [A-082] cores dos núcleos (iguais ao setup_pickups_3d.py e às cores do plasma das armas)
	const FLinearColor JRPistolPlasma(0.55f, 0.12f, 1.f);
	const FLinearColor JRShotgunPlasma(1.f, 0.35f, 0.04f);
	const FLinearColor JRSniperPlasma(0.1f, 0.85f, 1.f);

	/** Arma na mão do herói (munição do chão vai para a reserva dela, então o item mostra a célula dela). */
	EJRWeaponSlot HeroWeaponSlot(const UObject* WorldContext)
	{
		if (const AJRCharacter* Hero = Cast<AJRCharacter>(UGameplayStatics::GetPlayerPawn(WorldContext, 0)))
		{
			return Hero->GetCurrentWeaponSlot();
		}
		return EJRWeaponSlot::None;
	}

	/** [A-082] Sequência de itens pegos em seguida: o som sobe um pouquinho de tom (pega-pega gostoso). */
	struct FJRPickupStreak
	{
		TWeakObjectPtr<const UWorld> StreakWorld;
		double LastTime = -100.0;
		int32 Count = 0;
	};
	FJRPickupStreak GPickupStreak;

	float NextStreakPitch(const UWorld* InWorld)
	{
		const double Clock = InWorld ? InWorld->GetTimeSeconds() : 0.0;
		if (GPickupStreak.StreakWorld.Get() != InWorld || Clock - GPickupStreak.LastTime > 1.2 || Clock < GPickupStreak.LastTime)
		{
			GPickupStreak.Count = 0;
		}
		GPickupStreak.StreakWorld = InWorld;
		GPickupStreak.LastTime = Clock;
		const float Pitch = 1.f + 0.05f * static_cast<float>(FMath::Min(GPickupStreak.Count, 6)) + FMath::FRandRange(-0.02f, 0.02f);
		++GPickupStreak.Count;
		return Pitch;
	}
}

AJRPickup::AJRPickup()
{
	// [A-082] Tick para a animação (ver comentário da classe)
	PrimaryActorTick.bCanEverTick = true;
	PrimaryActorTick.bStartWithTickEnabled = true;

	Trigger = CreateDefaultSubobject<USphereComponent>(TEXT("Trigger"));
	Trigger->InitSphereRadius(140.f);
	Trigger->SetCollisionProfileName(TEXT("OverlapAllDynamic"));
	RootComponent = Trigger;

	Mesh = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Mesh"));
	Mesh->SetupAttachment(Trigger);
	Mesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Mesh->SetGenerateOverlapEvents(false);
	Mesh->SetRelativeLocation(FVector(0.f, 0.f, 40.f));
	Mesh->SetRelativeScale3D(FVector(0.45f));

	// [A-063] brilho leve em candelas: o sol do entardecer tem ~5 lux, então 6 cd dão ~6 lux a 1 m
	// (antes eram 2500, em torno de 2500 lux: o item ficava branco estourado).
	Glow = CreateDefaultSubobject<UPointLightComponent>(TEXT("Glow"));
	Glow->SetupAttachment(Mesh);
	Glow->IntensityUnits = ELightUnits::Candelas;
	Glow->SetIntensity(6.f);
	Glow->SetAttenuationRadius(250.f);
	Glow->SetCastShadows(false);

	// [A-082] o giro agora é do Tick; o componente fica desligado (compatibilidade com o que já foi salvo)
	Rotator = CreateDefaultSubobject<URotatingMovementComponent>(TEXT("Rotator"));
	Rotator->RotationRate = FRotator::ZeroRotator;
	Rotator->bAutoActivate = false;
	Rotator->SetUpdatedComponent(Mesh);

	// [A-082] anel de brilho no chão
	Beam = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Beam"));
	Beam->SetupAttachment(Trigger);
	Beam->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Beam->SetGenerateOverlapEvents(false);
	Beam->SetCastShadow(false);
	Beam->bReceivesDecals = false;
	Beam->SetVisibility(false);
	{
		static ConstructorHelpers::FObjectFinder<UStaticMesh> CylinderFinder(TEXT("/Engine/BasicShapes/Cylinder.Cylinder"));
		if (CylinderFinder.Succeeded())
		{
			Beam->SetStaticMesh(CylinderFinder.Object);
		}
	}
	BeamMaterial = TSoftObjectPtr<UMaterialInterface>(FSoftObjectPath(TEXT("/Game/Materials/Remap/M_Pickup_Beam.M_Pickup_Beam")));

	Ring = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Ring"));
	Ring->SetupAttachment(Trigger);
	Ring->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Ring->SetGenerateOverlapEvents(false);
	Ring->SetCastShadow(false);
	Ring->bReceivesDecals = false;
	Ring->SetRelativeLocation(FVector(0.f, 0.f, 1.5f));

	// [A-082] malhas padrão (tools/unreal/setup_pickups_3d.py); ausentes = visual antigo
	MeshAmmoPistol = SoftMesh(TEXT("/Game/Props/Pickups/SM_Pickup_CellPistol.SM_Pickup_CellPistol"));
	MeshAmmoShotgun = SoftMesh(TEXT("/Game/Props/Pickups/SM_Pickup_ShellShotgun.SM_Pickup_ShellShotgun"));
	MeshAmmoSniper = SoftMesh(TEXT("/Game/Props/Pickups/SM_Pickup_CellRifle.SM_Pickup_CellRifle"));
	MeshHealth = SoftMesh(TEXT("/Game/Props/Pickups/SM_Pickup_HealthGel.SM_Pickup_HealthGel"));
	MeshBandage = SoftMesh(TEXT("/Game/Props/Pickups/SM_Pickup_Bandage.SM_Pickup_Bandage"));
	MeshMedkit = SoftMesh(TEXT("/Game/Props/Pickups/SM_Pickup_Medkit.SM_Pickup_Medkit"));
	MeshFury = SoftMesh(TEXT("/Game/Props/Pickups/SM_Pickup_FuryCrystal.SM_Pickup_FuryCrystal"));
	MeshNitro = SoftMesh(TEXT("/Game/Props/Pickups/SM_Pickup_Nitro.SM_Pickup_Nitro"));
	MeshRepair = SoftMesh(TEXT("/Game/Props/Pickups/SM_Pickup_Repair.SM_Pickup_Repair"));
	MeshWeaponMelee = SoftMesh(TEXT("/Game/Environment/User/Armas/SM_ARM_Graveto.SM_ARM_Graveto"));
	MeshWeaponPistol = SoftMesh(TEXT("/Game/Weapons/SM_AlienPistol.SM_AlienPistol"));
	MeshWeaponShotgun = SoftMesh(TEXT("/Game/Environment/User/Armas/SM_ARM_Escopeta.SM_ARM_Escopeta"));
	MeshWeaponSniper = SoftMesh(TEXT("/Game/Environment/User/Armas/SM_ARM_Sniper.SM_ARM_Sniper"));
	RingMesh = SoftMesh(TEXT("/Game/Props/Pickups/SM_Pickup_Ring.SM_Pickup_Ring"));
}

void AJRPickup::OnConstruction(const FTransform& Transform)
{
	Super::OnConstruction(Transform);
	ApplyVisual();
}

void AJRPickup::BeginPlay()
{
	Super::BeginPlay();
	PhaseSeed = FMath::FRand();
	SpinYaw = FMath::FRandRange(0.f, 360.f);
	ApplyVisual();
	if (bSnapToGround)
	{
		SnapToGround();
	}
	Trigger->OnComponentBeginOverlap.AddDynamic(this, &AJRPickup::HandleOverlap);
}

void AJRPickup::Setup(EJRPickupType InType, float InAmount)
{
	Type = InType;
	Amount = InAmount;
	ApplyVisual();
}

UStaticMesh* AJRPickup::ResolveDefaultMesh(FLinearColor& OutCoreColor, float& OutScale) const
{
	OutScale = 1.f;
	OutCoreColor = ColorFor(Type);
	switch (Type)
	{
	case EJRPickupType::Ammo:
	{
		const EJRWeaponSlot Slot = HeroWeaponSlot(this);
		if (Slot == EJRWeaponSlot::Shotgun)
		{
			OutCoreColor = JRShotgunPlasma;
			OutScale = 1.7f;
			return LoadSoftMesh(MeshAmmoShotgun);
		}
		if (Slot == EJRWeaponSlot::Sniper)
		{
			OutCoreColor = JRSniperPlasma;
			OutScale = 1.7f;
			return LoadSoftMesh(MeshAmmoSniper);
		}
		OutCoreColor = JRPistolPlasma;
		OutScale = 1.8f;
		return LoadSoftMesh(MeshAmmoPistol);
	}
	case EJRPickupType::Health:
		OutCoreColor = FLinearColor(1.f, 0.12f, 0.2f);
		OutScale = 1.8f;
		return LoadSoftMesh(MeshHealth);
	case EJRPickupType::Bandage:
		OutCoreColor = FLinearColor(1.f, 0.25f, 0.25f);
		OutScale = 1.6f;
		return LoadSoftMesh(MeshBandage);
	case EJRPickupType::Medkit:
		OutCoreColor = FLinearColor(1.f, 0.2f, 0.15f);
		OutScale = 1.5f;
		return LoadSoftMesh(MeshMedkit);
	case EJRPickupType::Fury:
		OutCoreColor = FLinearColor(0.75f, 0.2f, 1.f);
		OutScale = 1.6f;
		return LoadSoftMesh(MeshFury);
	case EJRPickupType::Nitro:
		OutCoreColor = FLinearColor(0.1f, 0.55f, 1.f);
		OutScale = 2.4f; // o carro passa por cima: maior para ler de longe
		return LoadSoftMesh(MeshNitro);
	case EJRPickupType::Repair:
		OutCoreColor = FLinearColor(0.2f, 1.f, 0.35f);
		OutScale = 2.2f;
		return LoadSoftMesh(MeshRepair);
	case EJRPickupType::WeaponMelee:
		OutScale = 1.3f;
		return LoadSoftMesh(MeshWeaponMelee);
	case EJRPickupType::WeaponPistol:
		OutCoreColor = JRPistolPlasma;
		OutScale = 1.3f;
		return LoadSoftMesh(MeshWeaponPistol);
	case EJRPickupType::WeaponShotgun:
		OutCoreColor = JRShotgunPlasma;
		OutScale = 1.3f;
		return LoadSoftMesh(MeshWeaponShotgun);
	case EJRPickupType::WeaponSniper:
		OutCoreColor = JRSniperPlasma;
		OutScale = 1.3f;
		return LoadSoftMesh(MeshWeaponSniper);
	default:
		return nullptr;
	}
}

void AJRPickup::ApplyVisual()
{
	CoreMID = nullptr;
	RingMID = nullptr;
	Mesh->EmptyOverrideMaterials();
	GlowColor = ColorFor(Type);
	CoreColor = GlowColor;
	bFloats = !IsWeapon();
	Rotator->RotationRate = FRotator::ZeroRotator;
	Mesh->SetRelativeRotation(FRotator::ZeroRotator);
	Glow->SetRelativeLocation(FVector::ZeroVector);
	float RingSize = 0.5f;

	FLinearColor DefaultCore = GlowColor;
	float DefaultScale = 1.f;
	UStaticMesh* const Default3D = DisplayMesh ? nullptr : ResolveDefaultMesh(DefaultCore, DefaultScale);
	bool bUseShape = false;

	// Arma: a própria malha, deitada no chão; pode ser alvo do traço de interação.
	if (IsWeapon())
	{
		Mesh->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
		Mesh->SetCollisionResponseToAllChannels(ECR_Ignore);
		Mesh->SetCollisionResponseToChannel(ECC_Visibility, ECR_Block);
		RingSize = 1.1f;
		if (UStaticMesh* WeaponMesh = DisplayMesh ? DisplayMesh.Get() : Default3D)
		{
			Mesh->SetStaticMesh(WeaponMesh);
			Mesh->SetRelativeScale3D(FVector(DisplayMesh ? DisplayScale : DefaultScale));
			Mesh->SetRelativeLocation(FVector(0.f, 0.f, 8.f)); // [A-063] deitada, quase encostando no chão
			GlowColor = DefaultCore;
		}
		else
		{
			bUseShape = true;
		}
	}
	// Item com malha própria escolhida no nível (modelo do usuário em tamanho real, origem no pé):
	// usa a malha com o material dela, com o pé no chão (origem do ator = ponto de apoio).
	else if (DisplayMesh)
	{
		bFloats = false; // [A-082] modelo grande do usuário fica apoiado (só brilho, anel, ímã e pop)
		Mesh->SetStaticMesh(DisplayMesh);
		Mesh->SetRelativeScale3D(FVector(DisplayScale));
		Mesh->SetRelativeLocation(FVector::ZeroVector);
	}
	// [A-082] malha 3D padrão do tipo (pivô na base, núcleo "Core" que brilha e pulsa)
	else if (Default3D)
	{
		Mesh->SetStaticMesh(Default3D);
		Mesh->SetRelativeScale3D(FVector(DefaultScale));
		Mesh->SetRelativeLocation(FVector::ZeroVector);
		Glow->SetRelativeLocation(FVector(0.f, 0.f, 5.f));
		CoreColor = DefaultCore;
		GlowColor = DefaultCore;
		const int32 CoreIndex = Mesh->GetMaterialIndex(TEXT("Core"));
		if (CoreIndex != INDEX_NONE)
		{
			CoreMID = Mesh->CreateDynamicMaterialInstance(CoreIndex);
			if (CoreMID)
			{
				CoreMID->SetVectorParameterValue(TEXT("Color"), CoreColor);
				CoreMID->SetScalarParameterValue(TEXT("Intensity"), CoreGlowIntensity);
			}
		}
		if (Type == EJRPickupType::Nitro || Type == EJRPickupType::Repair)
		{
			RingSize = 1.0f;
		}
	}
	// Kit médico do usuário (antes do A-082 era o padrão do kit)
	else if (UStaticMesh* UserMedkit = Type == EJRPickupType::Medkit ? DefaultMedkitMesh() : nullptr)
	{
		bFloats = false;
		Mesh->SetStaticMesh(UserMedkit);
		Mesh->SetRelativeScale3D(FVector(DisplayScale));
		Mesh->SetRelativeLocation(FVector::ZeroVector);
	}
	else
	{
		bUseShape = true;
	}

	if (bUseShape)
	{
		if (UStaticMesh* Shape = LoadObject<UStaticMesh>(nullptr, MeshFor(Type)))
		{
			Mesh->SetStaticMesh(Shape);
		}
		// Forma básica: rolinho achatado para a bandagem, tamanho padrão para o resto. As formas da engine têm
		// 100 cm com a origem no centro: sobe meia altura para a base encostar no chão.
		const FVector ShapeScale = Type == EJRPickupType::Bandage ? FVector(0.3f, 0.3f, 0.22f) : FVector(0.45f);
		Mesh->SetRelativeScale3D(ShapeScale);
		Mesh->SetRelativeLocation(FVector(0.f, 0.f, 50.f * ShapeScale.Z));
		if (UMaterialInterface* Base = LoadObject<UMaterialInterface>(nullptr, TEXT("/Engine/BasicShapes/BasicShapeMaterial.BasicShapeMaterial")))
		{
			if (UMaterialInstanceDynamic* MID = Mesh->CreateDynamicMaterialInstance(0, Base))
			{
				MID->SetVectorParameterValue(TEXT("Color"), GlowColor);
			}
		}
	}

	Glow->SetLightColor(GlowColor);
	Glow->SetIntensity(GlowCandelas);

	// [A-082] anel de brilho do chão
	UStaticMesh* const RingAsset = LoadSoftMesh(RingMesh);
	Ring->SetStaticMesh(RingAsset);
	RingBaseScale = FVector(RingSize, RingSize, 1.f);
	Ring->SetRelativeScale3D(RingBaseScale);
	Ring->SetVisibility(RingAsset != nullptr && !bTaken && Phase == EJRPickupPhase::Idle);
	if (RingAsset)
	{
		RingMID = Ring->CreateDynamicMaterialInstance(0);
		if (RingMID)
		{
			RingMID->SetVectorParameterValue(TEXT("Color"), GlowColor);
			RingMID->SetScalarParameterValue(TEXT("Intensity"), RingGlowIntensity);
		}
	}

	// [A-086] maior e com feixe de luz: dá para ler o que caiu e onde, de longe
	if (!IsWeapon() && VisualScaleBoost != 1.f)
	{
		Mesh->SetRelativeScale3D(Mesh->GetRelativeScale3D() * VisualScaleBoost);
		Mesh->SetRelativeLocation(Mesh->GetRelativeLocation() * VisualScaleBoost);
	}
	UMaterialInterface* const BeamMat = BeamMaterial.IsNull() ? nullptr : BeamMaterial.LoadSynchronous();
	bBeamReady = Beam && BeamMat && Beam->GetStaticMesh();
	if (bBeamReady)
	{
		Beam->SetMaterial(0, BeamMat);
		BeamMID = Beam->CreateDynamicMaterialInstance(0, BeamMat);
		if (BeamMID)
		{
			BeamMID->SetVectorParameterValue(TEXT("Color"), GlowColor);
			// [A-088] feixe era coluna sólida e grossa (print 12): bem menos forte (aditivo estourava em branco)
			BeamBaseIntensity = IsWeapon() ? 1.1f : 0.75f;
			BeamMID->SetScalarParameterValue(TEXT("Intensity"), BeamBaseIntensity);
		}
		const float Width = IsWeapon() ? 0.11f : 0.07f; // cilindro da engine: 100 cm, origem no centro (antes 0.32/0.22)
		Beam->SetRelativeScale3D(FVector(Width, Width, BeamHeight / 100.f));
		Beam->SetRelativeLocation(FVector(0.f, 0.f, BeamHeight * 0.5f));
		Beam->SetVisibility(!bTaken && Phase == EJRPickupPhase::Idle);
	}
	else if (Beam)
	{
		Beam->SetVisibility(false);
	}

	VisualBaseLocation = Mesh->GetRelativeLocation();
	VisualBaseRotation = Mesh->GetRelativeRotation();
	VisualBaseScale = Mesh->GetRelativeScale3D();
}

FString AJRPickup::GetLabelText() const
{
	const int32 N = FMath::Max(1, FMath::RoundToInt(Amount));
	switch (Type)
	{
	case EJRPickupType::Ammo: return FString::Printf(TEXT("Munição +%d"), N);
	case EJRPickupType::Health: return FString::Printf(TEXT("Vida +%d"), N);
	case EJRPickupType::Nitro: return TEXT("Nitro");
	case EJRPickupType::Fury: return TEXT("Fúria");
	case EJRPickupType::Repair: return TEXT("Conserto");
	case EJRPickupType::WeaponMelee: return TEXT("Graveto alien  [E]");
	case EJRPickupType::WeaponPistol: return TEXT("Pistola alien  [E]");
	case EJRPickupType::WeaponShotgun: return TEXT("Escopeta alien  [E]");
	case EJRPickupType::WeaponSniper: return TEXT("Rifle alien  [E]");
	case EJRPickupType::Bandage: return N > 1 ? FString::Printf(TEXT("Bandagem x%d"), N) : FString(TEXT("Bandagem"));
	case EJRPickupType::Medkit: return N > 1 ? FString::Printf(TEXT("Kit médico x%d"), N) : FString(TEXT("Kit médico"));
	default: return TEXT("Item");
	}
}

bool AJRPickup::FindGroundBelow(const FVector& From, float MaxDrop, FVector& OutPoint) const
{
	UWorld* const PickWorld = GetWorld();
	if (!PickWorld)
	{
		return false;
	}
	const FVector End = From - FVector(0.f, 0.f, MaxDrop);
	FCollisionQueryParams Params(SCENE_QUERY_STAT(JRPickupSnap), true, this);
	FCollisionObjectQueryParams Objects;
	Objects.AddObjectTypesToQuery(ECC_WorldStatic);
	Objects.AddObjectTypesToQuery(ECC_WorldDynamic);
	Objects.AddObjectTypesToQuery(ECC_PhysicsBody);
	TArray<FHitResult> Hits;
	PickWorld->LineTraceMultiByObjectType(Hits, From, End, Objects, Params);
	for (const FHitResult& Hit : Hits)
	{
		const AActor* HitActor = Hit.GetActor();
		const UPrimitiveComponent* HitComp = Hit.GetComponent();
		// pula o que começa dentro do traço, personagens, carros, outros itens e gatilhos (caixas de história,
		// zonas): apoia só no que segura o personagem (chão, mesa, caixa)
		if (Hit.bStartPenetrating || !HitComp || (HitActor && (HitActor->IsA<APawn>() || HitActor->IsA<AJRPickup>()))
			|| HitComp->GetCollisionResponseToChannel(ECC_Pawn) != ECR_Block)
		{
			continue;
		}
		OutPoint = Hit.ImpactPoint;
		return true;
	}
	return false;
}

void AJRPickup::SnapToGround()
{
	FVector Ground;
	if (FindGroundBelow(GetActorLocation() + FVector(0.f, 0.f, 60.f), SnapMaxDrop + 60.f, Ground))
	{
		SetActorLocation(Ground);
	}
}

AJRPickup* AJRPickup::SpawnPickup(UWorld* World, EJRPickupType InType, float InAmount, const FVector& Location, float LifeSeconds)
{
	if (!World)
	{
		return nullptr;
	}
	FActorSpawnParameters Params;
	Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
	AJRPickup* Pickup = World->SpawnActor<AJRPickup>(AJRPickup::StaticClass(), Location, FRotator::ZeroRotator, Params);
	if (Pickup)
	{
		Pickup->Setup(InType, InAmount);
		if (LifeSeconds > 0.f)
		{
			Pickup->SetLifeSpan(LifeSeconds);
		}
		// [A-082] sai do corpo num arco curto (o BeginPlay já achou o chão embaixo do ponto de spawn)
		if (Pickup->HasActorBegunPlay())
		{
			Pickup->StartDropToss(Location);
		}
	}
	return Pickup;
}

void AJRPickup::StartDropToss(const FVector& From)
{
	UWorld* const PickWorld = GetWorld();
	if (!PickWorld)
	{
		return;
	}
	// chão de reserva: onde o BeginPlay apoiou (embaixo do zumbi)
	FVector Landing = GetActorLocation();
	const float Angle = FMath::FRandRange(0.f, JRPickupTwoPi);
	const float Reach = FMath::FRandRange(45.f, 95.f);
	const FVector Offset(FMath::Cos(Angle) * Reach, FMath::Sin(Angle) * Reach, 0.f);
	FVector Probe;
	if (FindGroundBelow(From + Offset + FVector(0.f, 0.f, 40.f), SnapMaxDrop + 140.f, Probe))
	{
		// não atravessa parede: só aceita o ponto ao lado se nada estático estiver no caminho
		FCollisionQueryParams Params(SCENE_QUERY_STAT(JRPickupToss), false, this);
		const bool bBlocked = PickWorld->LineTraceTestByObjectType(From + FVector(0.f, 0.f, 20.f), Probe + FVector(0.f, 0.f, 20.f),
			FCollisionObjectQueryParams(ECC_WorldStatic), Params);
		if (!bBlocked)
		{
			Landing = Probe;
		}
	}
	TossFrom = From + FVector(0.f, 0.f, 25.f);
	TossFrom.Z = FMath::Max(TossFrom.Z, Landing.Z + 20.f);
	TossTo = Landing;
	TossTime = 0.f;
	TossDuration = 0.42f;
	TossHeight = 55.f;
	TossBounces = 1;
	SpinBoost = 720.f;
	Phase = EJRPickupPhase::Toss;
	SetActorEnableCollision(false);
	Ring->SetVisibility(false);
	if (Beam) { Beam->SetVisibility(false); }
	SetActorLocation(TossFrom);
}

void AJRPickup::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	const float Dt = FMath::Min(DeltaSeconds, 0.05f);
	AnimTime += Dt;
	const UWorld* const PickWorld = GetWorld();
	const float Now = PickWorld ? static_cast<float>(PickWorld->GetTimeSeconds()) : AnimTime;
	switch (Phase)
	{
	case EJRPickupPhase::Toss:
		TickToss(Dt);
		break;
	case EJRPickupPhase::Magnet:
		TickMagnet(Dt);
		break;
	case EJRPickupPhase::Pop:
		TickPop(Dt);
		return;
	default:
		TryStartMagnet(Now);
		break;
	}
	if (Phase != EJRPickupPhase::Pop && !IsActorBeingDestroyed())
	{
		UpdateVisual(Dt);
	}
}

void AJRPickup::UpdateVisual(float Dt)
{
	KickTime += Dt;
	SpinBoost = FMath::FInterpTo(SpinBoost, 0.f, Dt, 3.f);
	// longe da câmera e parado: não mexe em nada (só a checagem do ímã, no Tick)
	if (Phase == EJRPickupPhase::Idle && KickTime > 1.f && !Mesh->WasRecentlyRendered(0.3f))
	{
		return;
	}
	if (bFloats || Phase == EJRPickupPhase::Toss)
	{
		const float SpinRate = (bFloats ? SpinDegreesPerSecond : 0.f) + SpinBoost;
		SpinYaw = FMath::Fmod(SpinYaw + SpinRate * Dt, 360.f);
	}
	const float Wave = FMath::Sin((AnimTime * BobFrequency + PhaseSeed) * JRPickupTwoPi);
	const float Lift = bFloats ? HoverHeight + BobAmplitude * Wave : 0.f;

	// mola do quique / do "não cabe": achata e estica rapidinho
	const float Spring = KickStrength * FMath::Exp(-KickTime * 9.f) * FMath::Cos(KickTime * 38.f);
	const FVector Squash(1.f + 0.22f * Spring, 1.f + 0.22f * Spring, 1.f - 0.3f * Spring);

	float MagnetShrink = 1.f;
	if (Phase == EJRPickupPhase::Magnet)
	{
		if (const APawn* Puller = MagnetPawn.Get())
		{
			const float Left = static_cast<float>(FVector::Dist(GetActorLocation(), MagnetTargetFor(Puller)));
			MagnetShrink = FMath::Lerp(0.7f, 1.f, FMath::Clamp(Left / 90.f, 0.f, 1.f));
		}
	}
	Mesh->SetRelativeLocationAndRotation(VisualBaseLocation + FVector(0.f, 0.f, Lift), VisualBaseRotation + FRotator(0.f, SpinYaw, 0.f));
	Mesh->SetRelativeScale3D(VisualBaseScale * Squash * MagnetShrink);

	// pulso suave do brilho (luz, núcleo e anel juntos)
	const float Pulse = 0.5f + 0.5f * FMath::Sin((AnimTime * PulseFrequency + PhaseSeed * 0.37f) * JRPickupTwoPi);
	Glow->SetIntensity(GlowCandelas * (0.7f + 0.6f * Pulse));
	if (BeamMID)
	{
		BeamMID->SetScalarParameterValue(TEXT("Intensity"), BeamBaseIntensity * (0.65f + 0.45f * Pulse));
	}
	if (CoreMID)
	{
		CoreMID->SetScalarParameterValue(TEXT("Intensity"), CoreGlowIntensity * (0.75f + 0.5f * Pulse));
	}
	if (RingMID)
	{
		RingMID->SetScalarParameterValue(TEXT("Intensity"), RingGlowIntensity * (0.6f + 0.8f * Pulse));
		Ring->SetRelativeScale3D(RingBaseScale * (0.94f + 0.12f * Pulse));
	}

	// drop com tempo: pisca cada vez mais rápido nos últimos segundos
	const float LifeLeft = GetLifeSpan();
	if (LifeLeft > 0.f && LifeLeft < BlinkBeforeExpire && BlinkBeforeExpire > 0.f && Phase == EJRPickupPhase::Idle)
	{
		const float Rate = FMath::Lerp(4.f, 10.f, 1.f - LifeLeft / BlinkBeforeExpire);
		const bool bOn = FMath::Fmod(AnimTime * Rate, 1.f) < 0.6f;
		Mesh->SetVisibility(bOn);
		Ring->SetVisibility(bOn && Ring->GetStaticMesh() != nullptr && !bTaken);
		if (Beam) { Beam->SetVisibility(bOn && bBeamReady && !bTaken); }
	}
}

void AJRPickup::TickToss(float Dt)
{
	TossTime += Dt;
	const float A = FMath::Clamp(TossTime / FMath::Max(TossDuration, 0.01f), 0.f, 1.f);
	const FVector Flat = FMath::Lerp(TossFrom, TossTo, A);
	SetActorLocation(Flat + FVector(0.f, 0.f, 4.f * TossHeight * A * (1.f - A)));
	if (A < 1.f)
	{
		return;
	}
	if (TossBounces > 0)
	{
		// primeira batida no chão: poeirinha e um quique pequeno
		--TossBounces;
		Kick(1.f);
		if (UJRFXSubsystem* FX = UJRFXSubsystem::Get(this))
		{
			FX->SpawnDustPuff(TossTo, FLinearColor(0.32f, 0.27f, 0.24f), 5, 110.f);
		}
		TossFrom = TossTo;
		TossHeight *= 0.22f;
		TossDuration *= 0.5f;
		TossTime = 0.f;
		return;
	}
	Kick(0.6f);
	Phase = EJRPickupPhase::Idle;
	SetActorEnableCollision(true);
	Ring->SetVisibility(Ring->GetStaticMesh() != nullptr && !bTaken);
	if (Beam) { Beam->SetVisibility(bBeamReady && !bTaken); }
}

FVector AJRPickup::MagnetTargetFor(const APawn* Hero) const
{
	// cintura do herói (a malha fica HoverHeight acima da origem do item)
	return Hero->GetActorLocation() - FVector(0.f, 0.f, 35.f + (bFloats ? HoverHeight : 0.f));
}

void AJRPickup::TryStartMagnet(float Now)
{
	if (bTaken || IsWeapon() || Now < NextMagnetTime)
	{
		return;
	}
	AJRCharacter* Hero = Cast<AJRCharacter>(UGameplayStatics::GetPlayerPawn(this, 0));
	if (!Hero)
	{
		return;
	}
	const FVector Here = GetActorLocation();
	const FVector HeroAt = Hero->GetActorLocation();
	const double HeightDiff = HeroAt.Z - Here.Z;
	if (FVector::DistSquared2D(Here, HeroAt) > FMath::Square(static_cast<double>(MagnetRadius)) || HeightDiff < -60.0 || HeightDiff > 220.0)
	{
		return;
	}
	if (CanBeCollectedBy(Hero))
	{
		StartMagnet(Hero);
	}
	else
	{
		NotifyBlocked(Now);
	}
}

void AJRPickup::StartMagnet(APawn* Hero)
{
	Phase = EJRPickupPhase::Magnet;
	MagnetPawn = Hero;
	MagnetTime = 0.f;
	MagnetSpeed = 250.f;
	MagnetVelocity = FVector(0.f, 0.f, 260.f); // pulinho antes de voar para o herói
	SpinBoost = 540.f;
	SetActorEnableCollision(false);
	Ring->SetVisibility(false);
	if (Beam) { Beam->SetVisibility(false); }
	Mesh->SetVisibility(true);
}

void AJRPickup::CancelMagnet(float Now)
{
	Phase = EJRPickupPhase::Idle;
	MagnetPawn = nullptr;
	NextMagnetTime = Now + 1.f;
	SetActorEnableCollision(true);
	SnapToGround();
	Ring->SetVisibility(Ring->GetStaticMesh() != nullptr && !bTaken);
	if (Beam) { Beam->SetVisibility(bBeamReady && !bTaken); }
	Kick(1.f);
}

void AJRPickup::TickMagnet(float Dt)
{
	APawn* Hero = MagnetPawn.Get();
	const AJRCharacter* HeroChar = Cast<AJRCharacter>(Hero);
	const UWorld* const PickWorld = GetWorld();
	const float Now = PickWorld ? static_cast<float>(PickWorld->GetTimeSeconds()) : AnimTime;
	// herói sumiu, morreu, entrou no carro ou a bolsa encheu no caminho: o item volta para o chão (não gruda)
	if (!HeroChar || !CanBeCollectedBy(HeroChar))
	{
		CancelMagnet(Now);
		return;
	}
	const FVector PullTarget = MagnetTargetFor(Hero);
	const FVector Here = GetActorLocation();
	const FVector ToTarget = PullTarget - Here;
	const double Dist = ToTarget.Size();
	if (Dist > static_cast<double>(MagnetRadius) * 2.5)
	{
		CancelMagnet(Now);
		return;
	}
	MagnetTime += Dt;
	MagnetSpeed = FMath::Min(MagnetSpeed + 6000.f * Dt, MagnetMaxSpeed);
	MagnetVelocity = FMath::VInterpTo(MagnetVelocity, ToTarget.GetSafeNormal() * MagnetSpeed, Dt, 12.f);
	const FVector Step = MagnetVelocity * Dt;
	if (Dist <= FMath::Max(35.0, Step.Size()) || MagnetTime > 0.8f)
	{
		SetActorLocation(PullTarget);
		Collect(Hero, Hero);
		return;
	}
	SetActorLocation(Here + Step);
}

void AJRPickup::Collect(AActor* Collector, APawn* FollowPawn)
{
	if (bTaken)
	{
		return;
	}
	if (!TryApply(Collector))
	{
		if (Phase == EJRPickupPhase::Magnet)
		{
			const UWorld* const PickWorld = GetWorld();
			CancelMagnet(PickWorld ? static_cast<float>(PickWorld->GetTimeSeconds()) : AnimTime);
		}
		return;
	}
	bTaken = true;
	// [Áudio/A-061] som de pegar por tipo (munição, cura, resto); em sequência o tom sobe um pouco
	const FName SoundId = Type == EJRPickupType::Ammo ? FName(TEXT("World.Pickup.Ammo"))
		: (Type == EJRPickupType::Health || Type == EJRPickupType::Bandage || Type == EJRPickupType::Medkit) ? FName(TEXT("Hero.Pickup"))
		: FName(TEXT("World.Pickup"));
	UJRAudio::Play2D(this, SoundId, 1.f, NextStreakPitch(GetWorld()));
	if (UJRFXSubsystem* FX = UJRFXSubsystem::Get(this))
	{
		FX->SpawnFlash(Mesh->GetComponentLocation(), GlowColor, 12.f, 5.f, 40.f, 0.18f, 0.f, 0.f);
	}
	Phase = EJRPickupPhase::Pop;
	PopTime = 0.f;
	PopFollow = FollowPawn;
	SetActorEnableCollision(false);
	Ring->SetVisibility(false);
	if (Beam) { Beam->SetVisibility(false); }
	Mesh->SetVisibility(true);
}

void AJRPickup::TickPop(float Dt)
{
	PopTime += Dt;
	const float PopDuration = 0.18f;
	const float A = FMath::Clamp(PopTime / PopDuration, 0.f, 1.f);
	// cresce rápido (1 -> 1,35) e some encolhendo
	const float PopScale = A < 0.3f ? FMath::Lerp(1.f, 1.35f, A / 0.3f) : FMath::Lerp(1.35f, 0.f, (A - 0.3f) / 0.7f);
	if (const APawn* Follow = PopFollow.Get())
	{
		SetActorLocation(FMath::VInterpTo(GetActorLocation(), MagnetTargetFor(Follow), Dt, 25.f));
	}
	SpinYaw = FMath::Fmod(SpinYaw + 900.f * Dt, 360.f);
	Mesh->SetRelativeLocationAndRotation(VisualBaseLocation + FVector(0.f, 0.f, bFloats ? HoverHeight : 0.f),
		VisualBaseRotation + FRotator(0.f, SpinYaw, 0.f));
	Mesh->SetRelativeScale3D(VisualBaseScale * FMath::Max(PopScale, 0.01f));
	Glow->SetIntensity(GlowCandelas * (1.f + 4.f * (1.f - A)));
	if (CoreMID)
	{
		CoreMID->SetScalarParameterValue(TEXT("Intensity"), CoreGlowIntensity * (1.f + 3.f * (1.f - A)));
	}
	if (A >= 1.f)
	{
		Destroy();
	}
}

void AJRPickup::Kick(float Strength)
{
	KickTime = 0.f;
	KickStrength = Strength;
}

void AJRPickup::NotifyBlocked(float Now)
{
	if (Now < NextBlockedToastTime)
	{
		return;
	}
	NextBlockedToastTime = Now + 3.5f;
	Kick(1.f); // pulinho de "não cabe"
	const TCHAR* Message = nullptr;
	switch (Type)
	{
	case EJRPickupType::Health: Message = TEXT("Vida cheia e bolsa cheia de bandagens"); break;
	case EJRPickupType::Bandage: Message = TEXT("Bolsa cheia de bandagens"); break;
	case EJRPickupType::Medkit: Message = TEXT("Bolsa cheia de kits médicos"); break;
	default: break;
	}
	if (Message)
	{
		AJRHUD::Toast(this, Message, FLinearColor(1.f, 0.8f, 0.35f));
	}
}

bool AJRPickup::CanBeCollectedBy(const AJRCharacter* Hero) const
{
	if (!Hero || bTaken || IsWeapon())
	{
		return false;
	}
	const UJRHealthComponent* Health = Hero->GetHealthComponent();
	if (Health && Health->IsDead())
	{
		return false;
	}
	const UJRInventoryComponent* Bag = Hero->GetInventoryComponent();
	switch (Type)
	{
	case EJRPickupType::Ammo:
		return Hero->GetWeaponComponent() != nullptr;
	case EJRPickupType::Health:
		// vida cheia vira bandagem na bolsa (TryApply); só não pega com vida cheia E bolsa cheia
		return !Health || Health->GetHealthNormalized() < 1.f || (Bag && !Bag->IsFull(EJRConsumable::Bandage));
	case EJRPickupType::Fury:
		return true; // ativa na hora ou guarda (se a bolsa encher, renova a Fúria)
	case EJRPickupType::Bandage:
		return Bag && !Bag->IsFull(EJRConsumable::Bandage);
	case EJRPickupType::Medkit:
		return Bag && !Bag->IsFull(EJRConsumable::Medkit);
	default:
		return false; // nitro e conserto são do carro
	}
}

void AJRPickup::HandleOverlap(UPrimitiveComponent* OverlappedComponent, AActor* OtherActor, UPrimitiveComponent* OtherComp,
	int32 OtherBodyIndex, bool bFromSweep, const FHitResult& SweepResult)
{
	if (bTaken || IsWeapon() || Phase != EJRPickupPhase::Idle)
	{
		return;
	}
	APawn* OtherPawn = Cast<APawn>(OtherActor);
	if (!OtherPawn || !OtherPawn->IsPlayerControlled())
	{
		return;
	}
	// A pé: o ímã cuida (também chamado pelo Tick); aqui só adianta quando o herói entra na esfera.
	if (AJRCharacter* Hero = Cast<AJRCharacter>(OtherPawn))
	{
		const UWorld* const PickWorld = GetWorld();
		const float Now = PickWorld ? static_cast<float>(PickWorld->GetTimeSeconds()) : AnimTime;
		if (Now >= NextMagnetTime && CanBeCollectedBy(Hero))
		{
			StartMagnet(Hero);
		}
		return;
	}
	// De carro (nitro, conserto): pega na hora ao passar por cima, com o mesmo "pop".
	Collect(OtherPawn, nullptr);
}

bool AJRPickup::CanInteract_Implementation(AActor* InstigatorActor) const
{
	return IsWeapon() && !bTaken && Cast<AJRCharacter>(InstigatorActor) != nullptr;
}

FText AJRPickup::GetInteractionText_Implementation() const
{
	switch (Type)
	{
	case EJRPickupType::WeaponMelee: return NSLOCTEXT("JogoResgate", "PickStick", "Pegar o graveto alien");
	case EJRPickupType::WeaponPistol: return NSLOCTEXT("JogoResgate", "PickPistol", "Pegar a pistola");
	case EJRPickupType::WeaponShotgun: return NSLOCTEXT("JogoResgate", "PickShotgun", "Pegar a escopeta alien");
	case EJRPickupType::WeaponSniper: return NSLOCTEXT("JogoResgate", "PickSniper", "Pegar o rifle de precisão alien");
	default: return FText::GetEmpty();
	}
}

void AJRPickup::Interact_Implementation(AActor* InstigatorActor)
{
	AJRCharacter* Hero = Cast<AJRCharacter>(InstigatorActor);
	if (!Hero || bTaken)
	{
		return;
	}
	bTaken = true;
	UJRAudio::Play2D(this, TEXT("World.Pickup.Weapon")); // [Áudio/A-061]
	const EJRWeaponSlot Slot = Type == EJRPickupType::WeaponMelee ? EJRWeaponSlot::Melee
		: Type == EJRPickupType::WeaponPistol ? EJRWeaponSlot::Pistol
		: Type == EJRPickupType::WeaponSniper ? EJRWeaponSlot::Sniper : EJRWeaponSlot::Shotgun; // [A-058]
	Hero->PickUpWeaponFromGround(Slot);
	AJRHUD::Toast(this, FString::Printf(TEXT("Você pegou: %s"), *GetInteractionText_Implementation().ToString().Replace(TEXT("Pegar "), TEXT(""))),
		FLinearColor(0.2f, 1.f, 0.8f));
	SetLifeSpan(0.9f); // some quando a mão chega no chão
	Glow->SetVisibility(false);
	Ring->SetVisibility(false);
	if (Beam) { Beam->SetVisibility(false); }
}

bool AJRPickup::TryApply(AActor* Collector)
{
	if (AJRCharacter* Hero = Cast<AJRCharacter>(Collector))
	{
		switch (Type)
		{
		case EJRPickupType::Ammo:
			Hero->GetWeaponComponent()->AddReserveAmmo(FMath::RoundToInt(Amount));
			AJRHUD::Toast(this, FString::Printf(TEXT("+%d células"), FMath::RoundToInt(Amount)), FLinearColor(1.f, 0.85f, 0.2f));
			return true;
		case EJRPickupType::Health:
			if (Hero->GetHealthComponent()->GetHealthNormalized() >= 1.f)
			{
				// Vida cheia: vira uma bandagem na bolsa (A-055); bolsa cheia = deixa o item para depois.
				if (Hero->GetInventoryComponent()->AddItem(EJRConsumable::Bandage, 1) > 0)
				{
					AJRHUD::Toast(this, TEXT("Vida cheia: guardou uma bandagem"), FLinearColor(0.95f, 0.9f, 0.77f));
					return true;
				}
				return false;
			}
			Hero->GetHealthComponent()->Heal(Amount);
			AJRHUD::Toast(this, FString::Printf(TEXT("+%d de vida"), FMath::RoundToInt(Amount)), FLinearColor(1.f, 0.35f, 0.35f));
			return true;
		case EJRPickupType::Fury:
			// Já com Fúria ativa: guarda a carga para usar depois pela roda (A-055).
			if (Hero->GetFuryRemaining() > 0.f && Hero->GetInventoryComponent()->AddItem(EJRConsumable::Fury, 1) > 0)
			{
				AJRHUD::Toast(this, TEXT("Fúria guardada (use pela roda: TAB)"), FLinearColor(0.8f, 0.3f, 1.f));
				return true;
			}
			Hero->ActivateFury(Amount);
			AJRHUD::Toast(this, TEXT("FÚRIA! Tiros mais fortes"), FLinearColor(0.8f, 0.3f, 1.f));
			return true;
		case EJRPickupType::Bandage:
		case EJRPickupType::Medkit:
		{
			const bool bIsMedkit = Type == EJRPickupType::Medkit;
			const int32 Got = Hero->GetInventoryComponent()->AddItem(bIsMedkit ? EJRConsumable::Medkit : EJRConsumable::Bandage,
				FMath::Max(1, FMath::RoundToInt(Amount)));
			if (Got <= 0)
			{
				AJRHUD::Toast(this, bIsMedkit ? TEXT("Bolsa cheia de kits médicos") : TEXT("Bolsa cheia de bandagens"),
					FLinearColor(1.f, 0.8f, 0.35f));
				return false; // fica no chão
			}
			AJRHUD::Toast(this, FString::Printf(TEXT("+%d %s"), Got, bIsMedkit ? (Got > 1 ? TEXT("kits médicos") : TEXT("kit médico"))
				: (Got > 1 ? TEXT("bandagens") : TEXT("bandagem"))), FLinearColor(1.f, 0.45f, 0.4f));
			return true;
		}
		default:
			return false;
		}
	}
	if (AJRVehiclePawn* Vehicle = Cast<AJRVehiclePawn>(Collector))
	{
		switch (Type)
		{
		case EJRPickupType::Nitro:
			Vehicle->AddNitro(Amount);
			AJRHUD::Toast(this, TEXT("+ Nitro"), FLinearColor(0.3f, 0.7f, 1.f));
			return true;
		case EJRPickupType::Repair:
			if (UJRVehicleDamageComponent* Damage = Vehicle->GetDamageComponent())
			{
				Damage->RepairAll();
			}
			AJRHUD::Toast(this, TEXT("Carro consertado!"), FLinearColor(0.3f, 1.f, 0.5f));
			return true;
		default:
			return false;
		}
	}
	return false;
}

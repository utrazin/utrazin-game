// Copyright utrazin. All Rights Reserved.

#include "Gameplay/JRPickup.h"
#include "Audio/JRAudio.h" // [Áudio/A-061]
#include "Characters/JRCharacter.h"
#include "Combat/JRHealthComponent.h"
#include "Combat/JRWeaponComponent.h"
#include "Components/PointLightComponent.h"
#include "Components/SphereComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "GameFramework/Pawn.h"
#include "GameFramework/RotatingMovementComponent.h"
#include "Materials/MaterialInstanceDynamic.h"
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
}

AJRPickup::AJRPickup()
{
	PrimaryActorTick.bCanEverTick = false;
	Trigger = CreateDefaultSubobject<USphereComponent>(TEXT("Trigger"));
	Trigger->InitSphereRadius(140.f);
	Trigger->SetCollisionProfileName(TEXT("OverlapAllDynamic"));
	RootComponent = Trigger;

	Mesh = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Mesh"));
	Mesh->SetupAttachment(Trigger);
	Mesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
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

	// [A-063] parado: o componente fica, mas sem girar (o marcador do item mostra onde ele está)
	Rotator = CreateDefaultSubobject<URotatingMovementComponent>(TEXT("Rotator"));
	Rotator->RotationRate = FRotator::ZeroRotator;
	Rotator->SetUpdatedComponent(Mesh);
}

void AJRPickup::OnConstruction(const FTransform& Transform)
{
	Super::OnConstruction(Transform);
	ApplyVisual();
}

void AJRPickup::BeginPlay()
{
	Super::BeginPlay();
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

void AJRPickup::ApplyVisual()
{
	const FLinearColor Color = ColorFor(Type);
	Glow->SetLightColor(Color);
	Rotator->RotationRate = FRotator::ZeroRotator; // [A-063] nada gira
	// Arma: a própria malha, deitada no chão; pode ser alvo do traço de interação.
	if (IsWeapon())
	{
		Mesh->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
		Mesh->SetCollisionResponseToAllChannels(ECR_Ignore);
		Mesh->SetCollisionResponseToChannel(ECC_Visibility, ECR_Block);
		if (DisplayMesh)
		{
			Mesh->SetStaticMesh(DisplayMesh);
			Mesh->SetRelativeScale3D(FVector(DisplayScale));
			Mesh->SetRelativeLocation(FVector(0.f, 0.f, 8.f)); // [A-063] deitada, quase encostando no chão
			return;
		}
	}
	// Item com malha própria (kit médico, munição... modelos do usuário em tamanho real, origem no pé):
	// usa a malha com o material dela, com o pé no chão (origem do ator = ponto de apoio).
	else if (UStaticMesh* OwnMesh = DisplayMesh ? DisplayMesh.Get() : (Type == EJRPickupType::Medkit ? DefaultMedkitMesh() : nullptr))
	{
		Mesh->SetStaticMesh(OwnMesh);
		Mesh->SetRelativeScale3D(FVector(DisplayScale));
		Mesh->SetRelativeLocation(FVector::ZeroVector);
		Mesh->EmptyOverrideMaterials();
		return;
	}
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
			MID->SetVectorParameterValue(TEXT("Color"), Color);
		}
	}
	Glow->SetLightColor(Color);
}

void AJRPickup::SnapToGround()
{
	UWorld* World = GetWorld();
	if (!World)
	{
		return;
	}
	const FVector Start = GetActorLocation() + FVector(0.f, 0.f, 60.f);
	const FVector End = GetActorLocation() - FVector(0.f, 0.f, SnapMaxDrop);
	FCollisionQueryParams Params(SCENE_QUERY_STAT(JRPickupSnap), true, this);
	FCollisionObjectQueryParams Objects;
	Objects.AddObjectTypesToQuery(ECC_WorldStatic);
	Objects.AddObjectTypesToQuery(ECC_WorldDynamic);
	Objects.AddObjectTypesToQuery(ECC_PhysicsBody);
	TArray<FHitResult> Hits;
	World->LineTraceMultiByObjectType(Hits, Start, End, Objects, Params);
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
		SetActorLocation(Hit.ImpactPoint);
		return;
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
	}
	return Pickup;
}

void AJRPickup::HandleOverlap(UPrimitiveComponent* OverlappedComponent, AActor* OtherActor, UPrimitiveComponent* OtherComp,
	int32 OtherBodyIndex, bool bFromSweep, const FHitResult& SweepResult)
{
	const APawn* Pawn = Cast<APawn>(OtherActor);
	if (!IsWeapon() && !bTaken && Pawn && Pawn->IsPlayerControlled() && TryApply(OtherActor))
	{
		bTaken = true;
		// [Áudio/A-061] som de pegar por tipo (munição, cura, resto)
		UJRAudio::Play2D(this, Type == EJRPickupType::Ammo ? FName(TEXT("World.Pickup.Ammo"))
			: (Type == EJRPickupType::Health || Type == EJRPickupType::Bandage || Type == EJRPickupType::Medkit) ? FName(TEXT("Hero.Pickup"))
			: FName(TEXT("World.Pickup")));
		Destroy();
	}
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

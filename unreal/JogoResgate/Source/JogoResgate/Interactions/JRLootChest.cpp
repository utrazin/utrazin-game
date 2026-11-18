// Copyright utrazin. All Rights Reserved.

#include "Interactions/JRLootChest.h"
#include "Audio/JRAudio.h" // [Áudio/A-061]
#include "AI/JRAIDirector.h"
#include "Core/JRPlayerController.h"
#include "Combat/JRHealthComponent.h"
#include "Combat/JRWeaponComponent.h"
#include "Components/PointLightComponent.h"
#include "Components/StaticMeshComponent.h"
#include "FX/JRInteractionCameraComponent.h"
#include "Engine/StaticMesh.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Materials/MaterialInterface.h"
#include "TimerManager.h"
#include "UI/JRHUD.h"
#include "UObject/ConstructorHelpers.h"

AJRLootChest::AJRLootChest()
{
	PrimaryActorTick.bCanEverTick = false;
	RootComponent = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
	// Cubo da engine tem 1 m e pivô no centro: baú de 1 x 0,6 x 0,5 m apoiado no chão.
	Base = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Base"));
	Base->SetupAttachment(RootComponent);
	Base->SetRelativeLocation(FVector(0.f, 0.f, 25.f));
	Base->SetRelativeScale3D(FVector(1.0f, 0.6f, 0.5f));
	LidPivot = CreateDefaultSubobject<USceneComponent>(TEXT("LidPivot"));
	LidPivot->SetupAttachment(RootComponent);
	LidPivot->SetRelativeLocation(FVector(0.f, -30.f, 50.f)); // dobradiça: borda de trás, no topo
	Lid = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Lid"));
	Lid->SetupAttachment(LidPivot);
	Lid->SetRelativeLocation(FVector(0.f, 30.f, 5.f));
	Lid->SetRelativeScale3D(FVector(1.04f, 0.62f, 0.1f));
	Glow = CreateDefaultSubobject<UPointLightComponent>(TEXT("Glow"));
	Glow->SetupAttachment(RootComponent);
	Glow->SetRelativeLocation(FVector(0.f, 0.f, 90.f));
	Glow->SetIntensity(1800.f);
	Glow->SetAttenuationRadius(400.f);
	Glow->SetLightColor(FLinearColor(1.f, 0.75f, 0.2f));
	Glow->SetCastShadows(false);
	static ConstructorHelpers::FObjectFinder<UStaticMesh> Cube(TEXT("/Engine/BasicShapes/Cube.Cube"));
	if (Cube.Succeeded())
	{
		Base->SetStaticMesh(Cube.Object);
		Lid->SetStaticMesh(Cube.Object);
	}
	Base->SetCollisionProfileName(TEXT("BlockAllDynamic"));
	Lid->SetCollisionProfileName(TEXT("NoCollision"));
}

bool AJRLootChest::CanInteract_Implementation(AActor* InstigatorActor) const
{
	return !bOpened && Cast<AJRCharacter>(InstigatorActor) != nullptr;
}

FText AJRLootChest::GetInteractionText_Implementation() const
{
	return NSLOCTEXT("JogoResgate", "OpenChest", "Abrir o baú");
}

void AJRLootChest::Interact_Implementation(AActor* InstigatorActor)
{
	AJRCharacter* Hero = Cast<AJRCharacter>(InstigatorActor);
	if (!Hero || bOpened)
	{
		return;
	}
	bOpened = true;
	Opener = Hero;
	// Encara o baú antes de abrir.
	const FVector ToChest = (GetActorLocation() - Hero->GetActorLocation()).GetSafeNormal2D();
	Hero->SetActorRotation(ToChest.Rotation());
	// [Animações/A-057] bomba de gasolina (item Fuel): animação de interagir em pé, se o herói tiver.
	const bool bFuelPump = KeyItemInside == FName(TEXT("Fuel")) && Hero->GetInteractAnim() != nullptr;
	const float Duration = bFuelPump ? Hero->PlayFullBodyAction(Hero->GetInteractAnim(), 1.f, OpenDuration)
		: Hero->PlayFullBodyAction(Hero->GetOpenChestAnim(), OpenPlayRate, OpenDuration);
	// [A-058] câmera cinematográfica enquanto abre (pula se houver zumbi a menos de 5 m).
	if (UJRInteractionCameraComponent* ShotCam = Hero->GetInteractionCamera())
	{
		ShotCam->PlayShot(bFuelPump ? EJRInteractionShot::FuelPump : EJRInteractionShot::Chest, this, Duration);
	}
	GetWorldTimerManager().SetTimer(OpenTimer, this, &AJRLootChest::OpenAndGive, FMath::Max(0.2f, Duration * 0.55f), false);
}

void AJRLootChest::OpenAndGive()
{
	UJRAudio::Play2D(this, TEXT("World.Chest.Open")); // [Áudio/A-061] tampa abrindo (2D: o herói está colado no baú)
	LidPivot->SetRelativeRotation(FRotator(0.f, 0.f, -110.f));
	Glow->SetIntensity(5000.f);
	AJRCharacter* Hero = Opener.Get();
	if (!Hero)
	{
		return;
	}
	if (AmmoInside > 0)
	{
		Hero->GetWeaponComponent()->AddReserveAmmo(AmmoInside);
		AJRHUD::Toast(this, FString::Printf(TEXT("+%d células"), AmmoInside), FLinearColor(1.f, 0.85f, 0.2f));
	}
	if (WeaponInside == EJRWeaponSlot::Pistol)
	{
		AJRHUD::Toast(this, TEXT("Você achou: PISTOLA ALIEN!"), FLinearColor(0.2f, 1.f, 0.8f));
	}
	else if (WeaponInside == EJRWeaponSlot::Shotgun)
	{
		AJRHUD::Toast(this, TEXT("Você achou: ESCOPETA ALIEN!"), FLinearColor(0.2f, 1.f, 0.8f));
	}
	else if (WeaponInside == EJRWeaponSlot::Sniper) // [A-058]
	{
		AJRHUD::Toast(this, TEXT("Você achou: RIFLE ALIEN! Mire (botão direito) para usar a luneta."), FLinearColor(0.2f, 1.f, 0.8f));
	}
	if (HealthInside > 0.f)
	{
		Hero->GetHealthComponent()->Heal(HealthInside);
	}
	if (BandagesInside > 0)
	{
		const int32 GotBandages = Hero->GetInventoryComponent()->AddItem(EJRConsumable::Bandage, BandagesInside);
		AJRHUD::Toast(this, GotBandages > 0 ? FString::Printf(TEXT("+%d bandagem(ns)"), GotBandages) : FString(TEXT("Bolsa cheia de bandagens")),
			FLinearColor(1.f, 0.45f, 0.4f));
	}
	if (MedkitsInside > 0)
	{
		const int32 GotMedkits = Hero->GetInventoryComponent()->AddItem(EJRConsumable::Medkit, MedkitsInside);
		AJRHUD::Toast(this, GotMedkits > 0 ? FString::Printf(TEXT("+%d kit(s) médico(s)"), GotMedkits) : FString(TEXT("Bolsa cheia de kits médicos")),
			FLinearColor(1.f, 0.45f, 0.4f));
	}
	if (!KeyItemInside.IsNone())
	{
		if (AJRPlayerController* PC = Cast<AJRPlayerController>(Hero->GetController()))
		{
			PC->GiveKeyItem(KeyItemInside);
		}
		AJRHUD::Toast(this, FString::Printf(TEXT("Você achou: %s!"), KeyItemLabel.IsEmpty() ? *KeyItemInside.ToString() : *KeyItemLabel),
			FLinearColor(0.2f, 1.f, 0.8f));
	}
	if (bTriggerHordeOnOpen)
	{
		if (AJRAIDirector* Director = AJRAIDirector::Find(this))
		{
			Director->TriggerHordeAt(TEXT("Bau"), GetActorLocation(), HordeDuration, HordeSize);
			AJRHUD::Toast(this, TEXT("O barulho atraiu a horda! Aguente firme."), FLinearColor(1.f, 0.35f, 0.2f));
		}
	}
	if (WeaponInside != EJRWeaponSlot::None)
	{
		// Deixa a animação de abrir terminar e então puxa a arma nova.
		FTimerHandle EquipTimer;
		const EJRWeaponSlot Slot = WeaponInside;
		GetWorldTimerManager().SetTimer(EquipTimer, FTimerDelegate::CreateWeakLambda(Hero, [Hero, Slot]()
		{
			Hero->GrantWeapon(Slot, true);
		}), FMath::Max(0.2f, OpenDuration * 0.5f), false);
	}
}

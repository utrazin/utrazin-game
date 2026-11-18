// Copyright utrazin. All Rights Reserved.

#include "Remap/JRExtractionShip.h"
#include "Components/PointLightComponent.h"
#include "Components/SphereComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "GameFramework/Pawn.h"
#include "Remap/JRArenaDirector.h"
#include "TimerManager.h"
#include "UObject/ConstructorHelpers.h"

AJRExtractionShip::AJRExtractionShip()
{
	PrimaryActorTick.bCanEverTick = false;

	Trigger = CreateDefaultSubobject<USphereComponent>(TEXT("Trigger"));
	Trigger->InitSphereRadius(350.f);
	Trigger->SetCollisionProfileName(TEXT("Trigger"));
	RootComponent = Trigger;

	static ConstructorHelpers::FObjectFinder<UStaticMesh> CylinderMesh(TEXT("/Engine/BasicShapes/Cylinder.Cylinder"));

	Pad = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Pad"));
	Pad->SetupAttachment(Trigger);
	Pad->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Pad->SetRelativeScale3D(FVector(7.f, 7.f, 0.1f)); // disco de 7 m
	Pad->SetRelativeLocation(FVector(0.f, 0.f, -340.f));

	Beam = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Beam"));
	Beam->SetupAttachment(Trigger);
	Beam->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Beam->SetCastShadow(false);
	Beam->SetRelativeScale3D(FVector(0.6f, 0.6f, 60.f)); // feixe de 60 m (achar de longe)
	Beam->SetRelativeLocation(FVector(0.f, 0.f, 2600.f));

	if (CylinderMesh.Succeeded())
	{
		Pad->SetStaticMesh(CylinderMesh.Object);
		Beam->SetStaticMesh(CylinderMesh.Object);
	}

	Light = CreateDefaultSubobject<UPointLightComponent>(TEXT("Light"));
	Light->SetupAttachment(Trigger);
	Light->SetRelativeLocation(FVector(0.f, 0.f, 200.f));
	Light->SetIntensity(80000.f);
	Light->SetAttenuationRadius(1600.f);
	Light->SetLightColor(FLinearColor(0.25f, 0.9f, 1.f));
}

void AJRExtractionShip::Activate(AJRArenaDirector* InDirector, float Seconds, float InMultiplier)
{
	Director = InDirector;
	Multiplier = InMultiplier;
	ExpireTime = GetWorld()->GetTimeSeconds() + Seconds;
	Trigger->OnComponentBeginOverlap.AddUniqueDynamic(this, &AJRExtractionShip::HandleOverlap);
	GetWorldTimerManager().SetTimer(LeaveTimer, this, &AJRExtractionShip::Leave, FMath::Max(1.f, Seconds), false);
	// Já tem alguém dentro (nasceu em cima do herói)?
	TArray<AActor*> Inside;
	Trigger->GetOverlappingActors(Inside, APawn::StaticClass());
	for (AActor* A : Inside)
	{
		HandleOverlap(Trigger, A, nullptr, 0, false, FHitResult());
	}
}

float AJRExtractionShip::GetSecondsLeft() const
{
	return FMath::Max(0.f, static_cast<float>(ExpireTime - GetWorld()->GetTimeSeconds()));
}

void AJRExtractionShip::HandleOverlap(UPrimitiveComponent* OverlappedComponent, AActor* OtherActor, UPrimitiveComponent* OtherComp,
	int32 OtherBodyIndex, bool bFromSweep, const FHitResult& SweepResult)
{
	const APawn* Pawn = Cast<APawn>(OtherActor);
	if (bUsed || !Pawn || !Pawn->IsPlayerControlled())
	{
		return;
	}
	bUsed = true;
	GetWorldTimerManager().ClearTimer(LeaveTimer);
	if (AJRArenaDirector* D = Director.Get())
	{
		D->Extract(Multiplier);
	}
}

void AJRExtractionShip::Leave()
{
	if (bUsed)
	{
		return;
	}
	if (AJRArenaDirector* D = Director.Get())
	{
		D->HandleShipLeft(this);
	}
	Destroy();
}

// Copyright utrazin. All Rights Reserved.

#include "Gameplay/JRCameraZone.h"
#include "Characters/JRCharacter.h"
#include "Components/BoxComponent.h"

AJRCameraZone::AJRCameraZone()
{
	PrimaryActorTick.bCanEverTick = false;
	Box = CreateDefaultSubobject<UBoxComponent>(TEXT("Box"));
	Box->SetBoxExtent(FVector(400.f, 400.f, 150.f));
	Box->SetCollisionProfileName(TEXT("OverlapAllDynamic"));
	Box->SetGenerateOverlapEvents(true);
	Box->SetCanEverAffectNavigation(false);
	RootComponent = Box;
}

void AJRCameraZone::BeginPlay()
{
	Super::BeginPlay();
	Box->OnComponentBeginOverlap.AddDynamic(this, &AJRCameraZone::HandleBeginOverlap);
	Box->OnComponentEndOverlap.AddDynamic(this, &AJRCameraZone::HandleEndOverlap);
}

void AJRCameraZone::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
	for (const TWeakObjectPtr<AJRCharacter>& Hero : HeroesInside)
	{
		if (AJRCharacter* Ptr = Hero.Get())
		{
			Ptr->ExitCameraZone(ArmLength);
		}
	}
	HeroesInside.Reset();
	Super::EndPlay(EndPlayReason);
}

void AJRCameraZone::HandleBeginOverlap(UPrimitiveComponent* OverlappedComponent, AActor* OtherActor, UPrimitiveComponent* OtherComp,
	int32 OtherBodyIndex, bool bFromSweep, const FHitResult& SweepResult)
{
	AJRCharacter* Hero = Cast<AJRCharacter>(OtherActor);
	// só a cápsula conta (a malha e a arma também geram sobreposição)
	if (!Hero || OtherComp != Hero->GetRootComponent() || HeroesInside.Contains(Hero))
	{
		return;
	}
	HeroesInside.Add(Hero);
	Hero->EnterCameraZone(ArmLength);
}

void AJRCameraZone::HandleEndOverlap(UPrimitiveComponent* OverlappedComponent, AActor* OtherActor, UPrimitiveComponent* OtherComp,
	int32 OtherBodyIndex)
{
	AJRCharacter* Hero = Cast<AJRCharacter>(OtherActor);
	if (!Hero || OtherComp != Hero->GetRootComponent() || !HeroesInside.Contains(Hero))
	{
		return;
	}
	HeroesInside.Remove(Hero);
	Hero->ExitCameraZone(ArmLength);
}

// Copyright utrazin. All Rights Reserved.

#include "Remap/JRShopkeeper.h"
#include "Animation/AnimationAsset.h"
#include "Animation/AnimSequenceBase.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/TextRenderComponent.h"
#include "Engine/StaticMesh.h"
#include "GameFramework/Pawn.h"
#include "GameFramework/PlayerController.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Remap/JRRemapHUD.h"
#include "TimerManager.h"
#include "UObject/ConstructorHelpers.h"

#define LOCTEXT_NAMESPACE "JRRemap"

AJRShopkeeper::AJRShopkeeper()
{
	PrimaryActorTick.bCanEverTick = false;

	Capsule = CreateDefaultSubobject<UCapsuleComponent>(TEXT("Capsule"));
	Capsule->InitCapsuleSize(60.f, 110.f);
	Capsule->SetCollisionProfileName(TEXT("BlockAllDynamic")); // bloqueia o herói e é achado pelo traço de interação
	RootComponent = Capsule;

	Mesh = CreateDefaultSubobject<USkeletalMeshComponent>(TEXT("Mesh"));
	Mesh->SetupAttachment(Capsule);
	Mesh->SetRelativeLocation(FVector(0.f, 0.f, -110.f));
	Mesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);

	static ConstructorHelpers::FObjectFinder<UStaticMesh> CapsuleMesh(TEXT("/Engine/BasicShapes/Cylinder.Cylinder"));
	Placeholder = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Placeholder"));
	Placeholder->SetupAttachment(Capsule);
	Placeholder->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Placeholder->SetRelativeScale3D(FVector(1.2f, 1.2f, 2.2f));
	if (CapsuleMesh.Succeeded())
	{
		Placeholder->SetStaticMesh(CapsuleMesh.Object);
	}

	NameTag = CreateDefaultSubobject<UTextRenderComponent>(TEXT("NameTag"));
	NameTag->SetupAttachment(Capsule);
	NameTag->SetRelativeLocation(FVector(0.f, 0.f, 170.f));
	NameTag->SetHorizontalAlignment(EHTA_Center);
	NameTag->SetWorldSize(32.f);
	NameTag->SetTextRenderColor(FColor(255, 220, 120));
	NameTag->SetHiddenInGame(true); // [A-083] no jogo o nome é desenhado pela AJRRemapHUD (plaquinha v2 quando perto); no editor continua visível

	DisplayName = LOCTEXT("ShopDefault", "Vendedor");
}

void AJRShopkeeper::OnConstruction(const FTransform& Transform)
{
	Super::OnConstruction(Transform);
	RefreshVisual();
}

void AJRShopkeeper::RefreshVisual()
{
	const bool bHasModel = Mesh && Mesh->GetSkeletalMeshAsset() != nullptr;
	Placeholder->SetVisibility(!bHasModel);
	NameTag->SetText(DisplayName);
	if (!bHasModel)
	{
		if (UMaterialInstanceDynamic* MID = Placeholder->CreateAndSetMaterialInstanceDynamic(0))
		{
			MID->SetVectorParameterValue(TEXT("Color"), PlaceholderColor);
			MID->SetVectorParameterValue(TEXT("BaseColor"), PlaceholderColor);
		}
	}
	else
	{
		// Pés no chão: a cápsula acompanha a altura da malha.
		const FBoxSphereBounds B = Mesh->GetSkeletalMeshAsset()->GetBounds();
		const float Half = FMath::Max(60.f, B.BoxExtent.Z);
		Capsule->SetCapsuleSize(FMath::Max(40.f, FMath::Min(B.BoxExtent.X, B.BoxExtent.Y) * 0.8f), Half);
		Mesh->SetRelativeLocation(FVector(0.f, 0.f, -Half));
		Mesh->SetRelativeRotation(FRotator(0.f, MeshYawOffset, 0.f));
		NameTag->SetRelativeLocation(FVector(0.f, 0.f, Half + 40.f));
	}
}

void AJRShopkeeper::BeginPlay()
{
	Super::BeginPlay();
	RefreshVisual();
	if (NameTag)
	{
		NameTag->SetHiddenInGame(true); // [A-083] vale também para vendedores já salvos no mapa
	}
	BackToIdle();
}

void AJRShopkeeper::BackToIdle()
{
	if (Mesh && Mesh->GetSkeletalMeshAsset() && IdleAnim)
	{
		Mesh->PlayAnimation(IdleAnim, true);
	}
}

void AJRShopkeeper::PlayTalk()
{
	if (!Mesh || !Mesh->GetSkeletalMeshAsset() || !TalkAnim)
	{
		return;
	}
	Mesh->PlayAnimation(TalkAnim, false);
	float Len = 2.5f;
	if (const UAnimSequenceBase* Seq = Cast<UAnimSequenceBase>(TalkAnim))
	{
		Len = FMath::Max(0.5f, Seq->GetPlayLength());
	}
	GetWorldTimerManager().SetTimer(TalkTimer, this, &AJRShopkeeper::BackToIdle, Len, false);
}

FString AJRShopkeeper::PickGreeting() const
{
	if (Greetings.Num() == 0)
	{
		return FString();
	}
	return Greetings[FMath::RandRange(0, Greetings.Num() - 1)];
}

bool AJRShopkeeper::CanInteract_Implementation(AActor* InstigatorActor) const
{
	return Cast<APawn>(InstigatorActor) != nullptr;
}

void AJRShopkeeper::Interact_Implementation(AActor* InstigatorActor)
{
	const APawn* Pawn = Cast<APawn>(InstigatorActor);
	const APlayerController* PC = Pawn ? Cast<APlayerController>(Pawn->GetController()) : nullptr;
	if (AJRRemapHUD* HUD = PC ? Cast<AJRRemapHUD>(PC->GetHUD()) : nullptr)
	{
		HUD->OpenShop(this);
		PlayTalk();
	}
}

FText AJRShopkeeper::GetInteractionText_Implementation() const
{
	return FText::Format(LOCTEXT("ShopTalk", "Falar com {0}"), DisplayName);
}

#undef LOCTEXT_NAMESPACE

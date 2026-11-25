// Copyright utrazin. All Rights Reserved.

#include "Remap/JRTreeShrine.h"

#include "Components/CapsuleComponent.h"
#include "Components/PointLightComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/GameInstance.h"
#include "Remap/JREconomySubsystem.h"
#include "Remap/JRRemapTypes.h"

AJRTreeShrine::AJRTreeShrine()
{
	PrimaryActorTick.bCanEverTick = true;
	PrimaryActorTick.TickInterval = 1.f / 30.f;
	ShopType = EJRShopType::Arvore;
	DisplayName = NSLOCTEXT("JRRemap", "TreeShrine", "Árvore-Mãe");
	Greetings = { TEXT("A Árvore-Mãe pulsa. Traga cristais da arena e ela cresce com você.") };
	PlaceholderColor = FLinearColor(0.4f, 1.f, 0.8f);
	Capsule->SetCapsuleSize(90.f, 120.f);
	Glow = CreateDefaultSubobject<UPointLightComponent>(TEXT("Glow"));
	Glow->SetupAttachment(Capsule);
	Glow->SetRelativeLocation(FVector(60.f, 0.f, 120.f));
	Glow->SetIntensityUnits(ELightUnits::Candelas);
	Glow->SetIntensity(GlowCandelas);
	Glow->SetAttenuationRadius(1800.f);
	Glow->SetLightColor(FLinearColor(0.45f, 1.f, 0.85f));
	Glow->SetCastShadows(false);
}

void AJRTreeShrine::HideBody()
{
	if (Placeholder)
	{
		Placeholder->SetVisibility(false);
	}
}

void AJRTreeShrine::OnConstruction(const FTransform& Transform)
{
	Super::OnConstruction(Transform);
	HideBody();
}

void AJRTreeShrine::BeginPlay()
{
	Super::BeginPlay();
	HideBody();
}

void AJRTreeShrine::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	CheckAccum += DeltaSeconds;
	if (CheckAccum > 1.f)
	{
		CheckAccum = 0.f;
		bCanBuy = false;
		if (const UJREconomySubsystem* Economy = GetGameInstance() ? GetGameInstance()->GetSubsystem<UJREconomySubsystem>() : nullptr)
		{
			for (const FJRTreeNodeDef& Node : FJRSkillTree::Nodes())
			{
				if (Economy->IsTreeNodeOpen(Node.Id) && Economy->GetCrystals() >= FJRSkillTree::Cost(Node, Economy->GetTreeRank(Node.Id)))
				{
					bCanBuy = true;
					break;
				}
			}
		}
	}
	// pulsa devagar; quando dá para comprar, pulsa mais forte e mais rápido (chama o jogador)
	const float Time = GetWorld() ? GetWorld()->GetTimeSeconds() : 0.f;
	const float Speed = bCanBuy ? 3.2f : 1.2f;
	const float Amp = bCanBuy ? 0.8f : 0.3f;
	Glow->SetIntensity(GlowCandelas * (1.f + Amp * FMath::Sin(Time * Speed)));
}

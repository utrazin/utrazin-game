// Copyright utrazin. All Rights Reserved.

#include "Gameplay/JRDistrictGate.h"

#include "Characters/JRCharacter.h"
#include "Components/BoxComponent.h"
#include "Components/PointLightComponent.h"
#include "Components/PrimitiveComponent.h"
#include "Components/TextRenderComponent.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/PlayerController.h"
#include "JogoResgate.h"
#include "Kismet/GameplayStatics.h"
#include "Remap/JREconomySubsystem.h"
#include "Remap/JRRemapHUD.h"
#include "Remap/JRRemapTypes.h"
#include "TimerManager.h"

AJRDistrictGate::AJRDistrictGate()
{
	PrimaryActorTick.bCanEverTick = false;
	Root = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
	SetRootComponent(Root);

	// Área do E: só consulta (a barricada de verdade são as malhas do mapa).
	Box = CreateDefaultSubobject<UBoxComponent>(TEXT("Box"));
	Box->SetupAttachment(Root);
	Box->SetBoxExtent(FVector(150.f, 300.f, 150.f));
	Box->SetRelativeLocation(FVector(0.f, 0.f, 150.f));
	Box->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
	Box->SetCollisionObjectType(ECC_WorldDynamic);
	Box->SetCollisionResponseToAllChannels(ECR_Overlap);
	Box->SetCollisionResponseToChannel(ECC_Camera, ECR_Ignore);
	Box->SetCollisionResponseToChannel(ECC_Visibility, ECR_Ignore);
	Box->SetCanEverAffectNavigation(false);

	Sign = CreateDefaultSubobject<UTextRenderComponent>(TEXT("Sign"));
	Sign->SetupAttachment(Root);
	Sign->SetRelativeLocation(FVector(-20.f, 0.f, 430.f)); // acima das barricadas, virada para quem chega (+X)
	Sign->SetHorizontalAlignment(EHTA_Center);
	Sign->SetVerticalAlignment(EVRTA_TextCenter);
	Sign->SetWorldSize(70.f);
	Sign->SetCollisionEnabled(ECollisionEnabled::NoCollision);

	Lamp = CreateDefaultSubobject<UPointLightComponent>(TEXT("Lamp"));
	Lamp->SetupAttachment(Root);
	Lamp->SetRelativeLocation(FVector(80.f, 0.f, 380.f));
	Lamp->SetIntensityUnits(ELightUnits::Candelas);
	Lamp->SetIntensity(30.f);
	Lamp->SetAttenuationRadius(1400.f);
	Lamp->SetCastShadows(false);
}

void AJRDistrictGate::OnConstruction(const FTransform& Transform)
{
	Super::OnConstruction(Transform);
	RefreshLook();
}

bool AJRDistrictGate::IsUnlocked() const
{
	const UGameInstance* GI = GetGameInstance();
	const UJREconomySubsystem* Economy = GI ? GI->GetSubsystem<UJREconomySubsystem>() : nullptr;
	return Economy && Economy->GetUnlockedArenaLevel() >= RequiredArenaLevel;
}

namespace
{
	// A fonte padrão do texto 3D não tem acento: a placa sai sem (o nome na faixa da HUD continua com).
	FString NoAccents(FString S)
	{
		const TCHAR* From[] = { TEXT("Á"), TEXT("À"), TEXT("Â"), TEXT("Ã"), TEXT("É"), TEXT("Ê"), TEXT("Í"), TEXT("Ó"), TEXT("Ô"), TEXT("Õ"), TEXT("Ú"), TEXT("Ç") };
		const TCHAR* To[] = { TEXT("A"), TEXT("A"), TEXT("A"), TEXT("A"), TEXT("E"), TEXT("E"), TEXT("I"), TEXT("O"), TEXT("O"), TEXT("O"), TEXT("U"), TEXT("C") };
		for (int32 i = 0; i < UE_ARRAY_COUNT(From); ++i)
		{
			S.ReplaceInline(From[i], To[i], ESearchCase::CaseSensitive);
		}
		return S;
	}
}

void AJRDistrictGate::RefreshLook()
{
	const bool bOpen = GetWorld() && GetWorld()->IsGameWorld() && (bOpened || IsUnlocked());
	Sign->SetText(FText::FromString(NoAccents(bOpen ? DistrictName.ToUpper()
		: FString::Printf(TEXT("%s\nFECHADO ATE A ARENA %d"), *DistrictName.ToUpper(), RequiredArenaLevel))));
	const FColor Col = bOpen ? FColor(120, 255, 190) : FColor(255, 120, 90);
	Sign->SetTextRenderColor(Col);
	Lamp->SetLightColor(FLinearColor(Col));
}

void AJRDistrictGate::BeginPlay()
{
	Super::BeginPlay();
	const FName Tag = BarrierTag.IsNone() ? DistrictId : BarrierTag;
	for (TActorIterator<AActor> It(GetWorld()); It; ++It)
	{
		if (*It != this && It->ActorHasTag(Tag))
		{
			FPiece P;
			P.Actor = *It;
			P.Start = It->GetActorLocation();
			P.StartRot = It->GetActorRotation();
			// quem está mais perto do posto cai primeiro (efeito dominó a partir do portão)
			P.Delay = FMath::Clamp(static_cast<float>(FVector::Dist2D(P.Start, GetActorLocation())) / 6000.f, 0.f, 0.9f);
			P.Tilt = FMath::FRandRange(-18.f, 18.f);
			Pieces.Add(P);
		}
	}
	RefreshLook();
	if (!IsUnlocked())
	{
		UE_LOG(LogJR, Log, TEXT("[bairros] %s fechado (arena %d), %d barricadas"), *DistrictId.ToString(), RequiredArenaLevel, Pieces.Num());
		return;
	}
	const UJREconomySubsystem* Economy = GetGameInstance()->GetSubsystem<UJREconomySubsystem>();
	if (Economy && Economy->IsDistrictSeen(DistrictId))
	{
		bOpened = true;
		SetPiecesHidden();
		return;
	}
	// liberado e ainda não visto: espera o herói chegar perto para ele ver cair
	GetWorldTimerManager().SetTimer(PollTimer, this, &AJRDistrictGate::Poll, 0.25f, true, 0.5f);
}

void AJRDistrictGate::Poll()
{
	const APawn* Hero = UGameplayStatics::GetPlayerPawn(this, 0);
	if (Hero && FVector::Dist(Hero->GetActorLocation(), GetActorLocation()) < RevealDistance)
	{
		GetWorldTimerManager().ClearTimer(PollTimer);
		StartCollapse();
	}
}

void AJRDistrictGate::ForceOpen()
{
	GetWorldTimerManager().ClearTimer(PollTimer);
	if (!bOpened)
	{
		StartCollapse();
	}
}

void AJRDistrictGate::StartCollapse()
{
	bOpened = true;
	RefreshLook();
	if (UJREconomySubsystem* Economy = GetGameInstance()->GetSubsystem<UJREconomySubsystem>())
	{
		Economy->MarkDistrictSeen(DistrictId);
	}
	APlayerController* PC = UGameplayStatics::GetPlayerController(this, 0);
	if (AJRRemapHUD* HUD = PC ? Cast<AJRRemapHUD>(PC->GetHUD()) : nullptr)
	{
		HUD->ShowCityBanner(TEXT("BAIRRO LIBERADO"), DistrictName, TEXT("R_Flag"));
	}
	if (AJRCharacter* Hero = PC ? Cast<AJRCharacter>(PC->GetPawn()) : nullptr)
	{
		Hero->PlayFeedback(0.35f, 0.f, 0.f);
	}
	for (FPiece& P : Pieces)
	{
		if (AActor* A = P.Actor.Get())
		{
			A->SetActorEnableCollision(false); // passagem livre na hora, a animação é só visual
		}
	}
	UE_LOG(LogJR, Log, TEXT("[bairros] %s liberado: %d barricadas caindo"), *DistrictId.ToString(), Pieces.Num());
	CollapseStart = GetWorld()->GetTimeSeconds();
	GetWorldTimerManager().SetTimer(CollapseTimer, this, &AJRDistrictGate::TickCollapse, 1.f / 60.f, true);
}

void AJRDistrictGate::TickCollapse()
{
	const float T = static_cast<float>(GetWorld()->GetTimeSeconds() - CollapseStart);
	bool bAllDone = true;
	for (FPiece& P : Pieces)
	{
		AActor* A = P.Actor.Get();
		if (!A)
		{
			continue;
		}
		const float A01 = FMath::Clamp((T - P.Delay) / CollapseSeconds, 0.f, 1.f);
		if (A01 < 1.f)
		{
			bAllDone = false;
		}
		// treme um pouco, depois afunda e tomba (some no chão como se fosse recolhida)
		const float Shake = A01 < 0.25f ? FMath::Sin(T * 60.f + P.Tilt) * 4.f * (A01 > 0.f ? 1.f : 0.f) : 0.f;
		const float Sink = FMath::InterpEaseIn(0.f, 520.f, FMath::Clamp((A01 - 0.2f) / 0.8f, 0.f, 1.f), 2.2f);
		A->SetActorLocationAndRotation(P.Start + FVector(Shake, Shake * 0.5f, -Sink),
			P.StartRot + FRotator(P.Tilt * FMath::Clamp((A01 - 0.2f) / 0.8f, 0.f, 1.f), 0.f, 0.f), false, nullptr, ETeleportType::TeleportPhysics);
	}
	if (bAllDone)
	{
		GetWorldTimerManager().ClearTimer(CollapseTimer);
		SetPiecesHidden();
	}
}

void AJRDistrictGate::SetPiecesHidden()
{
	for (FPiece& P : Pieces)
	{
		if (AActor* A = P.Actor.Get())
		{
			A->SetActorEnableCollision(false);
			A->SetActorHiddenInGame(true);
		}
	}
	// o posto continua como marco do bairro (placa verde), mas sem o E
	Box->SetCollisionEnabled(ECollisionEnabled::NoCollision);
}

bool AJRDistrictGate::CanInteract_Implementation(AActor* InstigatorActor) const
{
	return !bOpened && Cast<APawn>(InstigatorActor) != nullptr;
}

FText AJRDistrictGate::GetInteractionText_Implementation() const
{
	return FText::FromString(FString::Printf(TEXT("%s (fechado)"), *DistrictName));
}

void AJRDistrictGate::Interact_Implementation(AActor* InstigatorActor)
{
	const UJREconomySubsystem* Economy = GetGameInstance()->GetSubsystem<UJREconomySubsystem>();
	const int32 NeedWave = (RequiredArenaLevel - 1) * 6;
	const int32 Best = Economy ? Economy->GetBestWave() : 0;
	APlayerController* PC = UGameplayStatics::GetPlayerController(this, 0);
	if (AJRRemapHUD* HUD = PC ? Cast<AJRRemapHUD>(PC->GetHUD()) : nullptr)
	{
		HUD->ShowCityBanner(DistrictName.ToUpper(),
			FString::Printf(TEXT("Abre com a arena nível %d: chegue à onda %d numa corrida (recorde: %d)"), RequiredArenaLevel, NeedWave, Best),
			TEXT("Icon_Lock"));
	}
}

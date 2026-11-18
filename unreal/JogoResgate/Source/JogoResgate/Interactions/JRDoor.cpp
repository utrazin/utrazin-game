// Copyright utrazin. All Rights Reserved.

#include "Interactions/JRDoor.h"
#include "Audio/JRAudio.h"
#include "Characters/JRCharacter.h"
#include "Components/BoxComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "GameFramework/Controller.h"
#include "GameFramework/Pawn.h"

namespace JRDoorTuning
{
	/** Folga do batente: a dobradiça fica 7 cm para dentro do vão (o batente tem 8 cm). */
	constexpr float FrameInset = 7.f;
	/** Largura e altura da malha da folha (SM_INT_Porta*). */
	constexpr float MeshWidth = 100.f;
	constexpr float MeshHeight = 220.f;
	/** Profundidade da caixa que detecta zumbis, de cada lado da parede. */
	constexpr float DetectDepth = 160.f;
}

AJRDoor::AJRDoor()
{
	PrimaryActorTick.bCanEverTick = true;
	PrimaryActorTick.bStartWithTickEnabled = false; // só liga durante a animação

	Root = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
	RootComponent = Root;
	Root->SetMobility(EComponentMobility::Movable);

	HingeA = CreateDefaultSubobject<USceneComponent>(TEXT("HingeA"));
	HingeA->SetupAttachment(Root);
	LeafA = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("LeafA"));
	LeafA->SetupAttachment(HingeA);

	HingeB = CreateDefaultSubobject<USceneComponent>(TEXT("HingeB"));
	HingeB->SetupAttachment(Root);
	LeafB = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("LeafB"));
	LeafB->SetupAttachment(HingeB);

	for (UStaticMeshComponent* Leaf : { LeafA.Get(), LeafB.Get() })
	{
		Leaf->SetCollisionProfileName(TEXT("BlockAllDynamic"));
		Leaf->SetCollisionResponseToChannel(ECC_Camera, ECR_Ignore); // a câmera não "pula" ao passar pela porta
		Leaf->SetCanEverAffectNavigation(false);                     // a navmesh atravessa: zumbis chegam e abrem
		Leaf->SetMobility(EComponentMobility::Movable);
	}

	Detect = CreateDefaultSubobject<UBoxComponent>(TEXT("Detect"));
	Detect->SetupAttachment(Root);
	Detect->SetCollisionProfileName(TEXT("OverlapAllDynamic"));
	Detect->SetGenerateOverlapEvents(true);
	Detect->SetCanEverAffectNavigation(false);
}

void AJRDoor::OnConstruction(const FTransform& Transform)
{
	Super::OnConstruction(Transform);
	ApplyLayout();
	SetLeafYaw(bStartOpen ? -OpenAngle : 0.f); // portão já aberto fica virado para fora (+X): o interior fica livre
}

void AJRDoor::ApplyLayout()
{
	using namespace JRDoorTuning;
	const float Half = OpeningWidth * 0.5f;
	const float LeafWidth = FMath::Max(20.f, (bDouble ? Half : OpeningWidth) - FrameInset * (bDouble ? 1.5f : 2.f));
	const float LeafHeight = FMath::Max(100.f, OpeningHeight - 3.f);
	const FVector LeafScale(1.f, LeafWidth / MeshWidth, LeafHeight / MeshHeight);

	// Folha A: dobradiça no lado -Y, abre em direção a +Y. Folha B (dupla): dobradiça em +Y, espelhada.
	HingeA->SetRelativeLocation(FVector(0.f, -Half + FrameInset, 1.f));
	LeafA->SetRelativeScale3D(LeafScale);
	LeafA->SetStaticMesh(LeafMesh);

	HingeB->SetRelativeLocation(FVector(0.f, Half - FrameInset, 1.f));
	LeafB->SetRelativeRotation(FRotator(0.f, 180.f, 0.f));
	LeafB->SetRelativeScale3D(LeafScale);
	LeafB->SetStaticMesh(bDouble ? LeafMesh.Get() : nullptr);
	LeafB->SetVisibility(bDouble);
	LeafB->SetCollisionEnabled(bDouble ? ECollisionEnabled::QueryAndPhysics : ECollisionEnabled::NoCollision);

	Detect->SetRelativeLocation(FVector(0.f, 0.f, OpeningHeight * 0.5f));
	Detect->SetBoxExtent(FVector(DetectDepth, Half, OpeningHeight * 0.5f));
}

void AJRDoor::BeginPlay()
{
	Super::BeginPlay();
	ApplyLayout();
	bOpen = bStartOpen;
	CurrentYaw = bStartOpen ? -OpenAngle : 0.f;
	SetLeafYaw(CurrentYaw);
	if (bAutoOpenForAI)
	{
		Detect->OnComponentBeginOverlap.AddDynamic(this, &AJRDoor::HandleDetectOverlap);
	}
}

void AJRDoor::SetLeafYaw(float Yaw)
{
	CurrentYaw = Yaw;
	HingeA->SetRelativeRotation(FRotator(0.f, Yaw, 0.f));
	// A folha B é espelhada: o mesmo "abrir para longe" é o giro contrário.
	HingeB->SetRelativeRotation(FRotator(0.f, -Yaw, 0.f));
}

void AJRDoor::SetLeavesBlockPawns(bool bBlock)
{
	const ECollisionResponse Response = bBlock ? ECR_Block : ECR_Ignore;
	LeafA->SetCollisionResponseToChannel(ECC_Pawn, Response);
	if (bDouble)
	{
		LeafB->SetCollisionResponseToChannel(ECC_Pawn, Response);
	}
}

bool AJRDoor::CanInteract_Implementation(AActor* InstigatorActor) const
{
	if (bAnimating || Cast<AJRCharacter>(InstigatorActor) == nullptr)
	{
		return false;
	}
	if (!bOpen)
	{
		return true;
	}
	if (!bAllowClose)
	{
		return false;
	}
	// Fechar só olhando para a porta e perto dela: a porta aberta não "rouba" o E de um item ao lado.
	const APawn* Pawn = Cast<APawn>(InstigatorActor);
	const AController* Controller = Pawn ? Pawn->GetController() : nullptr;
	if (!Controller)
	{
		return false;
	}
	const FVector ToDoor = GetActorLocation() + FVector(0.f, 0.f, OpeningHeight * 0.5f) - Pawn->GetPawnViewLocation();
	if (ToDoor.SizeSquared() > FMath::Square(250.f))
	{
		return false;
	}
	return FVector::DotProduct(ToDoor.GetSafeNormal(), Controller->GetControlRotation().Vector()) > 0.75f;
}

FText AJRDoor::GetInteractionText_Implementation() const
{
	return bOpen ? NSLOCTEXT("JogoResgate", "CloseDoor", "Fechar a porta") : NSLOCTEXT("JogoResgate", "OpenDoor", "Abrir a porta");
}

void AJRDoor::Interact_Implementation(AActor* InstigatorActor)
{
	if (!InstigatorActor || bAnimating)
	{
		return;
	}
	if (bOpen)
	{
		if (bAllowClose)
		{
			Close();
		}
		return;
	}
	OpenAwayFrom(InstigatorActor->GetActorLocation());
}

void AJRDoor::OpenAwayFrom(const FVector& FromLocation)
{
	if (bOpen || bAnimating)
	{
		return;
	}
	// Quem está do lado +X (frente) empurra a porta para -X: com a dobradiça em -Y, giro positivo leva a folha
	// (que aponta para +Y) em direção a -X.
	const float Side = static_cast<float>(FVector::DotProduct(FromLocation - GetActorLocation(), GetActorForwardVector()));
	FromYaw = CurrentYaw;
	TargetYaw = Side >= 0.f ? OpenAngle : -OpenAngle;
	AnimTime = 0.f;
	AnimDuration = OpenTime;
	bOpen = true;
	bAnimating = true;
	SetLeavesBlockPawns(false); // não empurra o herói nem prende o zumbi enquanto gira
	SetActorTickEnabled(true);
	if (!UJRAudio::PlayAt(this, TEXT("World.Door.Open"), GetActorLocation()))
	{
		UJRAudio::PlayAt(this, TEXT("World.Gate.Open"), GetActorLocation(), 0.45f, 1.5f); // som provisório
	}
}

void AJRDoor::Close()
{
	if (!bOpen || bAnimating)
	{
		return;
	}
	FromYaw = CurrentYaw;
	TargetYaw = 0.f;
	AnimTime = 0.f;
	AnimDuration = CloseTime;
	bOpen = false;
	bAnimating = true;
	SetLeavesBlockPawns(false);
	SetActorTickEnabled(true);
	if (!UJRAudio::PlayAt(this, TEXT("World.Door.Close"), GetActorLocation()))
	{
		UJRAudio::PlayAt(this, TEXT("World.Gate.Open"), GetActorLocation(), 0.4f, 1.8f);
	}
}

void AJRDoor::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	if (!bAnimating)
	{
		SetActorTickEnabled(false);
		return;
	}
	AnimTime += DeltaSeconds;
	const float T = FMath::Clamp(AnimTime / FMath::Max(0.05f, AnimDuration), 0.f, 1.f);
	// "back out": sai rápido, passa um pouco do ponto e volta (peso de porta de verdade).
	const float S = Overshoot * 20.f;
	const float U = T - 1.f;
	const float Eased = 1.f + (S + 1.f) * U * U * U + S * U * U;
	SetLeafYaw(FMath::Lerp(FromYaw, TargetYaw, Eased));
	if (T >= 1.f)
	{
		SetLeafYaw(TargetYaw);
		bAnimating = false;
		SetLeavesBlockPawns(true);
		SetActorTickEnabled(false);
	}
}

void AJRDoor::HandleDetectOverlap(UPrimitiveComponent* OverlappedComponent, AActor* OtherActor, UPrimitiveComponent* OtherComp,
	int32 OtherBodyIndex, bool bFromSweep, const FHitResult& SweepResult)
{
	const APawn* Pawn = Cast<APawn>(OtherActor);
	if (!Pawn || Pawn->IsPlayerControlled() || bOpen || bAnimating)
	{
		return;
	}
	// Só a cápsula (raiz) conta: armas e malhas presas no zumbi não disparam a porta.
	if (OtherComp != Pawn->GetRootComponent())
	{
		return;
	}
	OpenAwayFrom(Pawn->GetActorLocation());
}

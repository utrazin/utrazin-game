// Copyright utrazin. All Rights Reserved.

#include "Interactions/JRInteractionComponent.h"
#include "Engine/OverlapResult.h"
#include "Engine/World.h"
#include "GameFramework/Controller.h"
#include "GameFramework/Pawn.h"
#include "Interactions/JRInteractable.h"

UJRInteractionComponent::UJRInteractionComponent()
{
	PrimaryComponentTick.bCanEverTick = false;
}

AActor* UJRInteractionComponent::FindInteractable() const
{
	const APawn* Pawn = Cast<APawn>(GetOwner());
	if (!Pawn || !Pawn->GetController())
	{
		return nullptr;
	}
	FVector ViewLocation;
	FRotator ViewRotation;
	Pawn->GetController()->GetPlayerViewPoint(ViewLocation, ViewRotation);

	// Começa no pawn (não na câmera afastada) para não pegar objetos atrás do personagem.
	const FVector Start = Pawn->GetPawnViewLocation();
	const FVector End = Start + ViewRotation.Vector() * InteractionDistance;
	FCollisionQueryParams Params(SCENE_QUERY_STAT(JRInteractionTrace), false, Pawn);
	FHitResult Hit;
	if (GetWorld()->SweepSingleByChannel(Hit, Start, End, FQuat::Identity, ECC_Visibility,
		FCollisionShape::MakeSphere(TraceRadius), Params))
	{
		AActor* HitActor = Hit.GetActor();
		if (HitActor && HitActor->Implements<UJRInteractable>()
			&& IJRInteractable::Execute_CanInteract(HitActor, GetOwner()))
		{
			return HitActor;
		}
	}
	// Sem mira exata: o interagível mais próximo em volta (itens no chão, baús).
	TArray<FOverlapResult> Overlaps;
	FCollisionObjectQueryParams Objects;
	Objects.AddObjectTypesToQuery(ECC_WorldDynamic);
	Objects.AddObjectTypesToQuery(ECC_WorldStatic);
	Objects.AddObjectTypesToQuery(ECC_Vehicle);     // buggy (entrar com E)
	Objects.AddObjectTypesToQuery(ECC_PhysicsBody);
	GetWorld()->OverlapMultiByObjectType(Overlaps, Pawn->GetActorLocation(), FQuat::Identity, Objects,
		FCollisionShape::MakeSphere(ProximityRadius), Params);
	AActor* Best = nullptr;
	float BestDist = TNumericLimits<float>::Max();
	for (const FOverlapResult& O : Overlaps)
	{
		AActor* Candidate = O.GetActor();
		if (Candidate && Candidate->Implements<UJRInteractable>() && IJRInteractable::Execute_CanInteract(Candidate, GetOwner()))
		{
			const float D = FVector::DistSquared(Candidate->GetActorLocation(), Pawn->GetActorLocation());
			if (D < BestDist)
			{
				BestDist = D;
				Best = Candidate;
			}
		}
	}
	return Best;
}

bool UJRInteractionComponent::TryInteract()
{
	if (AActor* Target = FindInteractable())
	{
		IJRInteractable::Execute_Interact(Target, GetOwner());
		return true;
	}
	return false;
}

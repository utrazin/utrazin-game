// Copyright utrazin. All Rights Reserved.

#include "Interactions/JRInteractable.h"

bool IJRInteractable::CanInteract_Implementation(AActor* InstigatorActor) const
{
	return true;
}

void IJRInteractable::Interact_Implementation(AActor* InstigatorActor)
{
}

FText IJRInteractable::GetInteractionText_Implementation() const
{
	return FText::GetEmpty();
}

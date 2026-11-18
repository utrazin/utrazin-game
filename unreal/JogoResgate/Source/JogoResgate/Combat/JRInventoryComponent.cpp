// Copyright utrazin. All Rights Reserved.

#include "Combat/JRInventoryComponent.h"

UJRInventoryComponent::UJRInventoryComponent()
{
	PrimaryComponentTick.bCanEverTick = false;
}

void UJRInventoryComponent::BeginPlay()
{
	Super::BeginPlay();
	Bandages = FMath::Clamp(StartBandages, 0, MaxBandages);
	Medkits = FMath::Clamp(StartMedkits, 0, MaxMedkits);
	FuryCharges = 0;
}

int32* UJRInventoryComponent::CountPtr(EJRConsumable Item)
{
	switch (Item)
	{
	case EJRConsumable::Bandage: return &Bandages;
	case EJRConsumable::Medkit: return &Medkits;
	case EJRConsumable::Fury: return &FuryCharges;
	default: return nullptr;
	}
}

int32 UJRInventoryComponent::GetCount(EJRConsumable Item) const
{
	switch (Item)
	{
	case EJRConsumable::Bandage: return Bandages;
	case EJRConsumable::Medkit: return Medkits;
	case EJRConsumable::Fury: return FuryCharges;
	default: return 0;
	}
}

int32 UJRInventoryComponent::GetMaxCount(EJRConsumable Item) const
{
	switch (Item)
	{
	case EJRConsumable::Bandage: return MaxBandages;
	case EJRConsumable::Medkit: return MaxMedkits;
	case EJRConsumable::Fury: return MaxFuryCharges;
	default: return 0;
	}
}

float UJRInventoryComponent::GetHealAmount(EJRConsumable Item) const
{
	switch (Item)
	{
	case EJRConsumable::Bandage: return BandageHeal;
	case EJRConsumable::Medkit: return MedkitHeal;
	default: return 0.f;
	}
}

int32 UJRInventoryComponent::AddItem(EJRConsumable Item, int32 Count)
{
	int32* Value = CountPtr(Item);
	if (!Value || Count <= 0)
	{
		return 0;
	}
	const int32 Added = FMath::Clamp(GetMaxCount(Item) - *Value, 0, Count);
	if (Added > 0)
	{
		*Value += Added;
		OnInventoryChanged.Broadcast(Item, *Value);
	}
	return Added;
}

bool UJRInventoryComponent::ConsumeItem(EJRConsumable Item)
{
	int32* Value = CountPtr(Item);
	if (!Value || *Value <= 0)
	{
		return false;
	}
	--(*Value);
	OnInventoryChanged.Broadcast(Item, *Value);
	return true;
}

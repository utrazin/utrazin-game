// Copyright utrazin. All Rights Reserved.

#pragma once

#include "NativeGameplayTags.h"

/** Gameplay Tags nativas do projeto. Estados e eventos relevantes passam por aqui (ver ADR-001). */
namespace JRGameplayTags
{
	JOGORESGATE_API UE_DECLARE_GAMEPLAY_TAG_EXTERN(State_Dead);
	JOGORESGATE_API UE_DECLARE_GAMEPLAY_TAG_EXTERN(State_Reloading);
	JOGORESGATE_API UE_DECLARE_GAMEPLAY_TAG_EXTERN(State_InVehicle);
	JOGORESGATE_API UE_DECLARE_GAMEPLAY_TAG_EXTERN(State_Vehicle_Disabled);

	JOGORESGATE_API UE_DECLARE_GAMEPLAY_TAG_EXTERN(Event_Damage_Received);
	JOGORESGATE_API UE_DECLARE_GAMEPLAY_TAG_EXTERN(Event_Checkpoint_Reached);
	JOGORESGATE_API UE_DECLARE_GAMEPLAY_TAG_EXTERN(Event_Vehicle_TireFlat);
	JOGORESGATE_API UE_DECLARE_GAMEPLAY_TAG_EXTERN(Event_Rescue_Completed);

	JOGORESGATE_API UE_DECLARE_GAMEPLAY_TAG_EXTERN(Faction_Player);
	JOGORESGATE_API UE_DECLARE_GAMEPLAY_TAG_EXTERN(Faction_Enemy);
}

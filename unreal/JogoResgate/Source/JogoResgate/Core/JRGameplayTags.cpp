// Copyright utrazin. All Rights Reserved.

#include "Core/JRGameplayTags.h"

namespace JRGameplayTags
{
	UE_DEFINE_GAMEPLAY_TAG_COMMENT(State_Dead, "State.Dead", "Ator morto.");
	UE_DEFINE_GAMEPLAY_TAG_COMMENT(State_Reloading, "State.Reloading", "Arma recarregando.");
	UE_DEFINE_GAMEPLAY_TAG_COMMENT(State_InVehicle, "State.InVehicle", "Jogador controlando o veículo.");
	UE_DEFINE_GAMEPLAY_TAG_COMMENT(State_Vehicle_Disabled, "State.Vehicle.Disabled", "Veículo inutilizado.");

	UE_DEFINE_GAMEPLAY_TAG_COMMENT(Event_Damage_Received, "Event.Damage.Received", "Dano recebido.");
	UE_DEFINE_GAMEPLAY_TAG_COMMENT(Event_Checkpoint_Reached, "Event.Checkpoint.Reached", "Checkpoint alcançado.");
	UE_DEFINE_GAMEPLAY_TAG_COMMENT(Event_Vehicle_TireFlat, "Event.Vehicle.TireFlat", "Pneu furado.");
	UE_DEFINE_GAMEPLAY_TAG_COMMENT(Event_Rescue_Completed, "Event.Rescue.Completed", "Resgate concluído.");

	UE_DEFINE_GAMEPLAY_TAG_COMMENT(Faction_Player, "Faction.Player", "Lado do jogador.");
	UE_DEFINE_GAMEPLAY_TAG_COMMENT(Faction_Enemy, "Faction.Enemy", "Inimigos.");
}

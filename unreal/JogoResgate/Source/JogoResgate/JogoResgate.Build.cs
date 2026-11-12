// Copyright utrazin. All Rights Reserved.

using UnrealBuildTool;

public class JogoResgate : ModuleRules
{
	public JogoResgate(ReadOnlyTargetRules Target) : base(Target)
	{
		PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;

		// Permite includes relativos à raiz do módulo, ex.: #include "Combat/JRHealthComponent.h"
		PublicIncludePaths.Add(ModuleDirectory);

		PublicDependencyModuleNames.AddRange(new string[]
		{
			"Core",
			"CoreUObject",
			"Engine",
			"InputCore",
			"EnhancedInput",
			"GameplayTags",
			"ChaosVehicles",
			"PhysicsCore",
			"AIModule",
			"NavigationSystem",
			"StateTreeModule",
			"GameplayStateTreeModule",
			"Niagara"
		});

		PrivateDependencyModuleNames.AddRange(new string[]
		{
			"UMG",
			"Slate",
			"SlateCore"
		});
	}
}

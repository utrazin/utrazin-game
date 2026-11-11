// Copyright utrazin. All Rights Reserved.

using UnrealBuildTool;

public class JogoResgateTarget : TargetRules
{
	public JogoResgateTarget(TargetInfo Target) : base(Target)
	{
		Type = TargetType.Game;
		DefaultBuildSettings = BuildSettingsVersion.Latest;
		IncludeOrderVersion = EngineIncludeOrderVersion.Latest;
		ExtraModuleNames.Add("JogoResgate");
	}
}

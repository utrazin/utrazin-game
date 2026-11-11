// Copyright utrazin. All Rights Reserved.

using UnrealBuildTool;

public class JogoResgateEditorTarget : TargetRules
{
	public JogoResgateEditorTarget(TargetInfo Target) : base(Target)
	{
		Type = TargetType.Editor;
		DefaultBuildSettings = BuildSettingsVersion.Latest;
		IncludeOrderVersion = EngineIncludeOrderVersion.Latest;
		ExtraModuleNames.Add("JogoResgate");
	}
}

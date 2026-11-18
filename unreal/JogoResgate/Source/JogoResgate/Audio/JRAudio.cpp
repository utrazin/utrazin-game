// Copyright utrazin. All Rights Reserved.

#include "Audio/JRAudio.h"

#include "Audio/JRAudioSubsystem.h"
#include "Components/AudioComponent.h"

bool UJRAudio::Play2D(const UObject* WorldContextObject, FName Id, float VolumeMultiplier, float PitchMultiplier)
{
	UJRAudioSubsystem* Audio = UJRAudioSubsystem::Get(WorldContextObject);
	return Audio && Audio->Play2D(Id, VolumeMultiplier, PitchMultiplier);
}

bool UJRAudio::PlayAt(const UObject* WorldContextObject, FName Id, FVector Location, float VolumeMultiplier, float PitchMultiplier)
{
	UJRAudioSubsystem* Audio = UJRAudioSubsystem::Get(WorldContextObject);
	return Audio && Audio->PlayAt(Id, Location, VolumeMultiplier, PitchMultiplier);
}

UAudioComponent* UJRAudio::PlayAttached(const UObject* WorldContextObject, FName Id, USceneComponent* AttachTo, FName Socket,
	float VolumeMultiplier)
{
	UJRAudioSubsystem* Audio = UJRAudioSubsystem::Get(WorldContextObject);
	return Audio ? Audio->PlayAttached(Id, AttachTo, Socket, VolumeMultiplier) : nullptr;
}

void UJRAudio::PlayMusic(const UObject* WorldContextObject, FName Id, float FadeSeconds)
{
	if (UJRAudioSubsystem* Audio = UJRAudioSubsystem::Get(WorldContextObject))
	{
		Audio->PlayMusic(Id, FadeSeconds);
	}
}

void UJRAudio::NotifyToast(const UObject* WorldContextObject)
{
	if (UJRAudioSubsystem* Audio = UJRAudioSubsystem::Get(WorldContextObject))
	{
		Audio->NotifyToast();
	}
}

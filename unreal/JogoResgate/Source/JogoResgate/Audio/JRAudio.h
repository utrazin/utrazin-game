// Copyright utrazin. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "JRAudio.generated.h"

class UAudioComponent;
class USceneComponent;

/**
 * Atalhos estáticos para tocar sons do banco por id (A-061), de C++ ou Blueprint:
 *   UJRAudio::Play2D(this, TEXT("UI.Radio"));
 *   UJRAudio::PlayAt(this, TEXT("World.Spikes"), GetActorLocation());
 * Sem banco (setup_audio.py não rodado) ou id desconhecido: não faz nada e devolve false/nulo.
 */
UCLASS()
class JOGORESGATE_API UJRAudio : public UBlueprintFunctionLibrary
{
	GENERATED_BODY()

public:
	UFUNCTION(BlueprintCallable, Category = "Audio", meta = (WorldContext = "WorldContextObject"))
	static bool Play2D(const UObject* WorldContextObject, FName Id, float VolumeMultiplier = 1.f, float PitchMultiplier = 1.f);

	UFUNCTION(BlueprintCallable, Category = "Audio", meta = (WorldContext = "WorldContextObject"))
	static bool PlayAt(const UObject* WorldContextObject, FName Id, FVector Location, float VolumeMultiplier = 1.f, float PitchMultiplier = 1.f);

	UFUNCTION(BlueprintCallable, Category = "Audio", meta = (WorldContext = "WorldContextObject"))
	static UAudioComponent* PlayAttached(const UObject* WorldContextObject, FName Id, USceneComponent* AttachTo, FName Socket = NAME_None,
		float VolumeMultiplier = 1.f);

	/** Troca a música de fundo (o subsistema volta a decidir sozinho na próxima mudança do diretor). */
	UFUNCTION(BlueprintCallable, Category = "Audio", meta = (WorldContext = "WorldContextObject"))
	static void PlayMusic(const UObject* WorldContextObject, FName Id, float FadeSeconds = 2.f);

	/** Bipe do toast (chamado pelo AJRHUD::ShowToast). */
	static void NotifyToast(const UObject* WorldContextObject);
};

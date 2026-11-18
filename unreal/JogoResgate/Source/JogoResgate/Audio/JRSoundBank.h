// Copyright utrazin. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"
#include "Engine/DataAsset.h"
#include "JRSoundBank.generated.h"

class USoundAttenuation;
class USoundBase;

/** Um som do banco: id lógico (ex.: "Car.Engine") e as variações sorteadas a cada toque (A-061). */
USTRUCT(BlueprintType)
struct FJRSoundEntry
{
	GENERATED_BODY()

	/** Id usado no código (UJRAudio::Play2D(this, "Zombie.Growl")). Prefixo dá a categoria: Music., Amb., UI. ou SFX (resto). */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Sound")
	FName Id;

	/** Sorteia uma por toque (sem repetir a anterior quando há mais de uma). */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Sound")
	TArray<TSoftObjectPtr<USoundBase>> Variations;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Sound", meta = (ClampMin = "0"))
	float Volume = 1.f;

	/** Tom sorteado entre PitchMin e PitchMax a cada toque (variação natural). */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Sound", meta = (ClampMin = "0.1"))
	float PitchMin = 1.f;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Sound", meta = (ClampMin = "0.1"))
	float PitchMax = 1.f;

	/** Atenuação 3D (PlayAt/PlayAttached). Vazio = DefaultAttenuation do banco. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Sound")
	TSoftObjectPtr<USoundAttenuation> Attenuation;

	/** Só informativo: o loop vem da própria SoundWave (setup_audio.py liga "Looping" nos *_Loop). */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Sound")
	bool bLoop = false;

	/** Intervalo mínimo entre dois toques do mesmo id (s, tempo real): evita "metralhadora" de som. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Sound", meta = (ClampMin = "0", Units = "s"))
	float MinInterval = 0.f;

	/** Conta no limite de vocalizações de zumbi ao mesmo tempo (Audio Bible: máx. 6). */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Sound")
	bool bZombieVoice = false;
};

/** Zona de ambiente: perto do centro os loops LoopIds tocam no volume LoopVolumes (some até Radius x ZoneFadeFactor). */
USTRUCT(BlueprintType)
struct FJRAmbienceZone
{
	GENERATED_BODY()

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Ambience")
	FName Name;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Ambience")
	FVector Center = FVector::ZeroVector;

	/** Só neste mapa (nome curto, ex.: L01_ZombieValley). Vazio = todos os mapas. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Ambience")
	FName MapName;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Ambience", meta = (Units = "cm"))
	float Radius = 10000.f;

	/** Ids de loops de ambiente (Amb.*) e o volume de cada um (mesmo índice; faltando = 1). */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Ambience")
	TArray<FName> LoopIds;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Ambience")
	TArray<float> LoopVolumes;

	/** Piso dos passos quando o traço não acha material conhecido: Dirt, Grass, Sand, Stone, Metal, Wood. Vazio = não muda. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Ambience")
	FName FootSurface;

	/** Som extra junto com alguns passos (ex.: ponte rangendo) e a chance por passo. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Ambience")
	FName FootExtraId;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Ambience", meta = (ClampMin = "0", ClampMax = "1"))
	float FootExtraChance = 0.f;

	/** Soma no volume dos trovões distantes (0 = só o valor base). */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Ambience", meta = (ClampMin = "0"))
	float ThunderWeight = 0.f;
};

/** Loop 3D fixo no mapa (lago tóxico borbulhando, nave caída zumbindo, árvore pulsando). */
USTRUCT(BlueprintType)
struct FJRAudioEmitter
{
	GENERATED_BODY()

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Emitter")
	FName Name;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Emitter")
	FVector Location = FVector::ZeroVector;

	/** Só neste mapa (nome curto). Vazio = todos os mapas. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Emitter")
	FName MapName;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Emitter")
	FName LoopId;

	/** Some de vez nesta distância (cheio até 25% dela). */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Emitter", meta = (Units = "cm"))
	float Radius = 5000.f;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Emitter", meta = (ClampMin = "0"))
	float Volume = 1.f;
};

/**
 * Banco de sons do jogo (A-061): /Game/Audio/DA_SoundBank, preenchido por tools/unreal/setup_audio.py.
 * O UJRAudioSubsystem carrega este asset pelo caminho no começo da fase e pré-carrega todos os sons
 * (são poucos e curtos; evita travadinha no primeiro toque).
 */
UCLASS(BlueprintType)
class JOGORESGATE_API UJRSoundBank : public UPrimaryDataAsset
{
	GENERATED_BODY()

public:
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Sounds")
	TArray<FJRSoundEntry> Sounds;

	/** Atenuação 3D padrão (ATT_JR_Default). */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Sounds")
	TSoftObjectPtr<USoundAttenuation> DefaultAttenuation;

	// ---- Volumes por categoria (multiplicam o Volume de cada som)

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Mix", meta = (ClampMin = "0"))
	float MasterVolume = 1.f;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Mix", meta = (ClampMin = "0"))
	float MusicVolume = 0.5f;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Mix", meta = (ClampMin = "0"))
	float SFXVolume = 1.f;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Mix", meta = (ClampMin = "0"))
	float AmbienceVolume = 0.7f;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Mix", meta = (ClampMin = "0"))
	float UIVolume = 0.8f;

	// ---- Ambiente

	/** Loops que tocam no mapa todo (vento baixo) e o volume de cada um. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Ambience")
	TArray<FName> BaseAmbienceIds = { TEXT("Amb.Wind") };

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Ambience")
	TArray<float> BaseAmbienceVolumes = { 0.35f };

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Ambience")
	TArray<FJRAmbienceZone> AmbienceZones;

	/** A zona some linearmente de Radius até Radius x este fator. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Ambience", meta = (ClampMin = "1.01"))
	float ZoneFadeFactor = 1.5f;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Ambience")
	TArray<FJRAudioEmitter> Emitters;

	/** Trovão distante: volume base e intervalo sorteado entre os dois valores. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Ambience", meta = (ClampMin = "0"))
	float ThunderBaseVolume = 0.35f;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Ambience", meta = (Units = "s"))
	float ThunderMinInterval = 25.f;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Ambience", meta = (Units = "s"))
	float ThunderMaxInterval = 60.f;

	// ---- Zumbis

	/** Arquétipos que rugem (elite) em vez de rosnar. Também vale MaxHealth >= EliteMinHealth. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Zombies")
	TArray<FName> EliteArchetypeIds = { TEXT("ENM-010") };

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Zombies", meta = (ClampMin = "1"))
	float EliteMinHealth = 300.f;

	/** Vocalizações de zumbi ao mesmo tempo (janela de 2 s). */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Zombies", meta = (ClampMin = "1"))
	int32 MaxZombieVoices = 6;

	/** Zumbis mais longe que isto não vocalizam nem pisam (economia de vozes). */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Zombies", meta = (Units = "cm"))
	float ZombieVoiceRadius = 5000.f;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Zombies", meta = (Units = "cm"))
	float ZombieStepRadius = 1500.f;

	// ---- Herói e música

	/** Abaixo desta fração de vida toca o coração/respiração. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Hero", meta = (ClampMin = "0", ClampMax = "1"))
	float LowHealthFraction = 0.3f;

	/** Na Subida do diretor, com intensidade acima disto, a música vira "tensão". */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Music", meta = (ClampMin = "0", ClampMax = "1"))
	float TensionIntensity = 0.35f;

	/** Zumbis em combate perto (20 m) que também levam a música para "tensão". */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Music", meta = (ClampMin = "1"))
	int32 TensionEngagedCount = 3;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Music", meta = (Units = "s"))
	float MusicCrossfadeSeconds = 3.f;

	/** Tempo mínimo numa música antes de trocar (menos para entrar na horda, que é na hora). */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Music", meta = (Units = "s"))
	float MusicMinHoldSeconds = 10.f;
};

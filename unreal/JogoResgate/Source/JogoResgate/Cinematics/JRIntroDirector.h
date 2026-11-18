// Copyright utrazin. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "JRIntroDirector.generated.h"

class AJRCharacter;
class AStaticMeshActor;
class APlayerController;
class UAudioComponent;
class UCameraComponent;
class UNiagaraComponent;
class UNiagaraSystem;
class UPointLightComponent;
class UStaticMesh;

/** Em que parte da abertura estamos (A-074). */
UENUM(BlueprintType)
enum class EJRIntroPhase : uint8
{
	Off,
	Menu,           // Ato 0: tela de start
	FadeToIntro,    // escurece depois do "Jogar"
	Cabin,          // Ato 1: nave, alarme, luz vermelha
	LoseControl,    // Ato 2: perda de controle e queda
	Impact,         // Ato 3: impacto
	Aftermath,      // Ato 4: nave caída e herói ao lado
	Handoff,        // Ato 5: blend para a câmera do jogo
	SkipFade,       // pulou: tela preta, tudo no lugar, volta
	Done
};

/** O que o AJRIntroHUD desenha por cima da imagem (lido a cada quadro). Só C++. */
struct FJRIntroOverlay
{
	bool bVisible = false;
	bool bMenu = false;
	/** Esconde o HUD do jogo (barras, minimapa, objetivo) durante a abertura. */
	bool bHideGameHud = false;
	TArray<FString> MenuItems;
	int32 MenuIndex = 0;
	/** 0..1: tela preta, clarão branco, faixas de cinema. */
	float Black = 0.f;
	float White = 0.f;
	float Letterbox = 0.f;
	FString Subtitle;
	float SubtitleAlpha = 0.f;
	bool bSkipHint = false;
	float SkipProgress = 0.f;
};

/**
 * Abertura do jogo (A-074) sem Level Sequence: um ator no mapa da fase 1 (posto por tools/unreal/setup_intro.py,
 * no ponto onde o herói aparece ao lado da nave caída) dirige tudo em C++:
 *   Ato 0 tela de start (Jogar / Ver abertura / Sair) com a câmera girando devagar sobre o vale;
 *   Ato 1 nave voando com alarme e luz vermelha piscando, tremor leve (7 s);
 *   Ato 2 explosão no motor, a nave desce desgovernada até o ponto da queda (10 s: plano do chão e plano de perseguição);
 *   Ato 3 corte no impacto, clarão branco, tremor forte, faíscas e fogo, silêncio (3 s);
 *   Ato 4 plano aberto da nave caída pegando fogo e corte para o herói ao lado, que dá os primeiros passos (9 s);
 *   Ato 5 blend de 1 s para a câmera do jogo; o gatilho Historia_Z0_Queda dispara (fala + tarefa "Pegue o graveto").
 * Segurar Espaço / Enter / A (controle) pula: tela preta, tudo no estado final e a mesma entrega do controle.
 * IntroSeen fica no save: depois da primeira vez, "Jogar" já pula (e "Ver abertura" mostra de novo).
 *
 * O AJRGameMode decide se a abertura roda (início da fase, sem estar renascendo) e então faz o herói nascer neste ator.
 * Tick: só durante a abertura (câmeras e curvas precisam ser suaves a cada quadro); desligado ao terminar.
 */
UCLASS()
class JOGORESGATE_API AJRIntroDirector : public AActor
{
	GENERATED_BODY()

public:
	AJRIntroDirector();

	virtual void BeginPlay() override;
	virtual void Tick(float DeltaSeconds) override;
	virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;

	/** O primeiro diretor de abertura do mundo (ou nulo). */
	static AJRIntroDirector* FindInWorld(UWorld* World);

	/** A abertura completa pode rodar neste mapa (ligada, e no editor só se bPlayInEditor). */
	bool CanPlayIntro() const;

	/** Abertura ou tela de start em andamento (o HUD esconde o jogo). */
	bool IsRunning() const { return Phase != EJRIntroPhase::Off && Phase != EJRIntroPhase::Done; }

	EJRIntroPhase GetPhase() const { return Phase; }

	const FJRIntroOverlay& GetOverlay() const { return Overlay; }

	/** Flag IntroSeen do save (false sem save). */
	static bool IsIntroSeen(const UObject* WorldContext);
	static void SetIntroSeen(const UObject* WorldContext, bool bSeen);

protected:
	UPROPERTY(VisibleAnywhere, Category = "Abertura")
	TObjectPtr<USceneComponent> Root;

	/** Câmera da abertura (movida a cada quadro). */
	UPROPERTY(VisibleAnywhere, Category = "Abertura")
	TObjectPtr<UCameraComponent> CineCamera;

	/** Luz vermelha do alarme (presa na nave em voo). */
	UPROPERTY(VisibleAnywhere, Category = "Abertura")
	TObjectPtr<UPointLightComponent> AlarmLight;

	// ---------------------------------------------------------------- liga / desliga

	UPROPERTY(EditAnywhere, Category = "Abertura")
	bool bEnabled = true;

	/** No editor (Play), mostrar a tela de start e a abertura. Desligue se atrapalhar os testes. */
	UPROPERTY(EditAnywhere, Category = "Abertura")
	bool bPlayInEditor = true;

	/** Ao abrir o jogo com um checkpoint salvo no meio da fase: mostra a tela de start (só "Continuar" e "Sair"). */
	UPROPERTY(EditAnywhere, Category = "Abertura")
	bool bStartScreenOnContinue = true;

	// ---------------------------------------------------------------- cena (setup_intro.py preenche; vazio = procura sozinho)

	/** A nave caída do mapa (MRC_NaveResgate). Vazio: procura uma malha com ShipMeshHint no nome. */
	UPROPERTY(EditInstanceOnly, Category = "Abertura|Cena")
	TObjectPtr<AActor> CrashedShip;

	UPROPERTY(EditAnywhere, Category = "Abertura|Cena")
	FString ShipMeshHint = TEXT("NaveResgate");

	/** Luzes de fogo da nave (Fogo_Nave_1..3): apagadas até o impacto. Vazio: luzes laranja perto da nave. */
	UPROPERTY(EditInstanceOnly, Category = "Abertura|Cena")
	TArray<TObjectPtr<AActor>> FireLights;

	/** Gatilho da primeira fala/tarefa (Historia_Z0_Queda). Vazio: o AJRStoryTrigger mais perto do início. */
	UPROPERTY(EditInstanceOnly, Category = "Abertura|Cena")
	TObjectPtr<AActor> FirstStoryTrigger;

	/** Malha da nave em voo. Vazio: a mesma da nave caída. */
	UPROPERTY(EditAnywhere, Category = "Abertura|Cena")
	TSoftObjectPtr<UStaticMesh> FlightShipMesh;

	/** Giro (yaw) que aponta o nariz da malha para +X. MRC_NaveResgate tem o comprimento em Y: -90 ou 90. */
	UPROPERTY(EditAnywhere, Category = "Abertura|Cena", meta = (Units = "Degrees"))
	float ShipModelYawOffset = -90.f;

	/** Gira a direção de chegada da nave (0 = ela chega pela traseira da nave caída, deslizando para a frente). */
	UPROPERTY(EditAnywhere, Category = "Abertura|Cena", meta = (Units = "Degrees"))
	float ApproachYawExtra = 0.f;

	/** Escala da nave em voo (0 = a mesma da nave caída). */
	UPROPERTY(EditAnywhere, Category = "Abertura|Cena", meta = (ClampMin = "0"))
	float FlightShipScale = 0.f;

	/** Altura do voo nivelado acima do ponto da queda (sobe sozinha se um morro estiver no caminho). */
	UPROPERTY(EditAnywhere, Category = "Abertura|Cena", meta = (Units = "cm", ClampMin = "1000"))
	float CruiseAltitude = 9000.f;

	/** Distância do voo nivelado (Ato 1) e da descida (Ato 2). */
	UPROPERTY(EditAnywhere, Category = "Abertura|Cena", meta = (Units = "cm", ClampMin = "1000"))
	float CruiseDistance = 26000.f;

	UPROPERTY(EditAnywhere, Category = "Abertura|Cena", meta = (Units = "cm", ClampMin = "1000"))
	float DiveDistance = 30000.f;

	/** Fumaça/fogo opcionais (Niagara). Sem eles: faíscas e clarões do UJRFXSubsystem. */
	UPROPERTY(EditAnywhere, Category = "Abertura|Cena")
	TObjectPtr<UNiagaraSystem> SmokeSystem;

	UPROPERTY(EditAnywhere, Category = "Abertura|Cena")
	TObjectPtr<UNiagaraSystem> FireSystem;

	UPROPERTY(EditAnywhere, Category = "Abertura|Cena", meta = (ClampMin = "0"))
	float AlarmLightCandelas = 80.f;

	// ---------------------------------------------------------------- tempos (total ~31 s; regra: <= 60 s)

	UPROPERTY(EditAnywhere, Category = "Abertura|Tempo", meta = (Units = "s", ClampMin = "0.1"))
	float FadeSeconds = 0.8f;

	UPROPERTY(EditAnywhere, Category = "Abertura|Tempo", meta = (Units = "s", ClampMin = "2"))
	float CabinSeconds = 7.f;

	UPROPERTY(EditAnywhere, Category = "Abertura|Tempo", meta = (Units = "s", ClampMin = "4"))
	float LoseControlSeconds = 10.f;

	UPROPERTY(EditAnywhere, Category = "Abertura|Tempo", meta = (Units = "s", ClampMin = "1.5"))
	float ImpactSeconds = 3.f;

	UPROPERTY(EditAnywhere, Category = "Abertura|Tempo", meta = (Units = "s", ClampMin = "5"))
	float AftermathSeconds = 9.f;

	UPROPERTY(EditAnywhere, Category = "Abertura|Tempo", meta = (Units = "s", ClampMin = "0.2"))
	float HandoffBlendSeconds = 1.f;

	/** Quanto tempo segurar o botão para pular. */
	UPROPERTY(EditAnywhere, Category = "Abertura|Tempo", meta = (Units = "s", ClampMin = "0.2"))
	float SkipHoldSeconds = 1.f;

	// ---------------------------------------------------------------- sons (ids do DA_SoundBank; id que não existe = silêncio)

	UPROPERTY(EditAnywhere, Category = "Abertura|Som")
	FName MenuMusicId = TEXT("Music.Explore");

	UPROPERTY(EditAnywhere, Category = "Abertura|Som")
	FName TensionMusicId = TEXT("Music.Tension");

	UPROPERTY(EditAnywhere, Category = "Abertura|Som")
	FName GameMusicId = TEXT("Music.Explore");

	UPROPERTY(EditAnywhere, Category = "Abertura|Som")
	FName AlarmSoundId = TEXT("UI.LowFuel");

	UPROPERTY(EditAnywhere, Category = "Abertura|Som")
	FName EngineLoopId = TEXT("Car.Engine");

	UPROPERTY(EditAnywhere, Category = "Abertura|Som")
	FName WindLoopId = TEXT("Amb.Wind");

	UPROPERTY(EditAnywhere, Category = "Abertura|Som")
	FName EngineBangId = TEXT("Car.Explosion");

	UPROPERTY(EditAnywhere, Category = "Abertura|Som")
	TArray<FName> ImpactSoundIds = { TEXT("Car.Impact.Heavy"), TEXT("Car.Explosion") };

	UPROPERTY(EditAnywhere, Category = "Abertura|Som")
	FName FireLoopId = TEXT("Car.Fire");

	UPROPERTY(EditAnywhere, Category = "Abertura|Som")
	FName MenuMoveSoundId = TEXT("UI.Wheel.Hover");

	UPROPERTY(EditAnywhere, Category = "Abertura|Som")
	FName MenuSelectSoundId = TEXT("UI.Wheel.Open");

private:
	enum class EMode : uint8 { None, Full, MenuOnly };
	enum class EMenuAction : uint8 { Play, PlayFull, Continue, Quit };

	// fluxo
	bool AcquirePlayer();
	void ResolveScene();
	void BuildPath();
	void LockPlayer();
	void UnlockPlayer();
	void FreezeEnemies(bool bFreeze);
	void SetPhase(EJRIntroPhase NewPhase);
	void OpenMenu();
	void TickMenu(float DeltaSeconds);
	void RunMenuAction(EMenuAction Action);
	void StartCinematic();
	void StartSkip();
	void Finish();
	void UpdateSkip(float DeltaSeconds);

	// atos
	void TickCabin(float T);
	void TickLoseControl(float T);
	void TickImpact(float T);
	void TickAftermath(float T);
	void TickMenuCamera(float T);

	// cena
	void SpawnFlightShip();
	void DestroyFlightShip();
	void ShowCrashSite(bool bWithEffects);
	void HideCrashSite();
	void ShowHero();
	void StartFireLoop();
	FVector ShipForward(float T) const;
	void FireStoryTrigger();
	AActor* FindStoryTrigger() const;

	// matemática
	FVector PathPosition(float T) const;
	FQuat ShipRotation(float T) const;
	void SetCamera(const FVector& Location, const FVector& LookAt, float Fov, float ShakeDeg, float ShakeCm);
	void SetCameraRot(const FVector& Location, const FQuat& Rotation, float Fov, float ShakeDeg, float ShakeCm);
	float GroundZAt(const FVector& Where, float Fallback) const;
	FVector HeroPivot() const;

	// som
	void Play2D(FName Id, float Volume = 1.f, float Pitch = 1.f) const;
	void PlayAt(FName Id, const FVector& Where, float Volume = 1.f) const;
	void StopLoop(TObjectPtr<UAudioComponent>& Slot, float FadeOut);

	EMode Mode = EMode::None;
	EJRIntroPhase Phase = EJRIntroPhase::Off;
	float PhaseTime = 0.f;
	float RealTime = 0.f;

	TWeakObjectPtr<APlayerController> PlayerPC;
	TWeakObjectPtr<APawn> PlayerPawn;
	bool bPlayerLocked = false;
	bool bPawnWasDamageable = true;
	bool bHeroShown = false;
	bool bCrashShown = false;
	bool bTriggerFired = false;

	// menu
	bool bMenuOpened = false;
	FVector2D LastMouse = FVector2D(-1.f, -1.f);
	TArray<EMenuAction> MenuActions;
	int32 MenuIndex = 0;
	bool bMenuNeedsRelease = true;

	// pular
	float SkipHold = 0.f;
	bool bSkipArmed = false;
	bool bSkipApplied = false;
	float SkipBlackStart = 0.f;
	float SkipLetterboxStart = 0.f;

	// cena calculada
	FVector CrashPoint = FVector::ZeroVector;
	FVector ApproachDir = FVector::ForwardVector;  // direção em que a nave anda (XY)
	FVector CampPoint = FVector::ZeroVector;        // checkpoint do início (plano do chão)
	FVector HeroMark = FVector::ZeroVector;         // onde o herói aparece (este ator)
	FVector HeroFacing = FVector::ForwardVector;
	FQuat CrashedShipQuat = FQuat::Identity;
	FVector CrashedShipScale = FVector::OneVector;
	float ShipRadius = 1000.f;
	float PathAltitude = 9000.f;
	FVector PathA = FVector::ZeroVector;
	FVector PathB = FVector::ZeroVector;
	FVector PathC1 = FVector::ZeroVector;
	FVector PathC2 = FVector::ZeroVector;
	FVector ImpactCamDir = FVector::ForwardVector;
	FVector MenuOrbitCenter = FVector::ZeroVector;

	UPROPERTY(Transient)
	TObjectPtr<AStaticMeshActor> FlightShip;

	UPROPERTY(Transient)
	TObjectPtr<UAudioComponent> EngineLoop;

	UPROPERTY(Transient)
	TObjectPtr<UAudioComponent> WindLoop;

	UPROPERTY(Transient)
	TObjectPtr<UAudioComponent> FireLoop;

	UPROPERTY(Transient)
	TObjectPtr<UNiagaraComponent> SmokeFX;

	TMap<TWeakObjectPtr<AActor>, float> FrozenEnemies;
	float NextFreezeScan = 0.f;
	float NextAlarm = 0.f;
	float NextSpark = 0.f;
	bool bEngineBang = false;
	bool bImpactSoundsDone = false;
	bool bFireLoopStarted = false;
	bool bHandoffStarted = false;
	bool bHeroStepDone = false;
	FQuat HandoffStartQuat = FQuat::Identity;
	FVector HandoffStartLoc = FVector::ZeroVector;

	FJRIntroOverlay Overlay;
};

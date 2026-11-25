// Copyright utrazin. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Character.h"
#include "Characters/JRItemWheel.h"
#include "Combat/JRInventoryComponent.h"
#include "JRCharacter.generated.h"

class UAnimMontage;
class UAnimSequenceBase;
class UCameraComponent;
class UInputAction;
class UJRDamageFXComponent;
class UJRHealthComponent;
class UJRInteractionCameraComponent;
class UJRInteractionComponent;
class UJRWeaponComponent;
class UJRWeaponDefinition;
class UStaticMesh;
class UStaticMeshComponent;
class USoundBase;
class USpringArmComponent;
struct FInputActionValue;
struct FJRSkinDefinition;
struct FMinimalViewInfo;

/** Armas que o herói pode carregar (começa sem nenhuma; acha pelo caminho). */
UENUM(BlueprintType)
enum class EJRWeaponSlot : uint8
{
	None,
	Melee,    // graveto alien (corpo a corpo)
	Pistol,
	Shotgun,
	Sniper    // [A-058] rifle de precisão alien (no fim: valores antigos não mudam)
};

/** Personagem jogável a pé (GDD 7). Componentes fazem o trabalho; a classe só compõe e roteia input. */
UCLASS()
class JOGORESGATE_API AJRCharacter : public ACharacter
{
	GENERATED_BODY()

public:
	AJRCharacter();

	/** Toca a montage de saída do carro bloqueando o movimento até terminar. */
	UFUNCTION(BlueprintCallable, Category = "Character")
	void PlayExitVehicleSequence();

	/** Começa sentado no banco do veículo e a animação leva o personagem para fora. */
	void PlayExitFromVehicle(AActor* FromVehicle, const FTransform& SeatTransform);

	/** Abraço do resgate. Retorna a duração (0 se não houver montage). */
	UFUNCTION(BlueprintCallable, Category = "Character")
	float PlayRescueHug();

	void ApplySkin(const FJRSkinDefinition& Skin);

	UFUNCTION(BlueprintPure, Category = "Character")
	UJRHealthComponent* GetHealthComponent() const { return HealthComponent; }

	UFUNCTION(BlueprintPure, Category = "Character")
	UJRWeaponComponent* GetWeaponComponent() const { return WeaponComponent; }

	UFUNCTION(BlueprintPure, Category = "Character")
	UJRDamageFXComponent* GetDamageFXComponent() const { return DamageFXComponent; }

	/** Câmera cinematográfica das interações (baú, pegar arma, explosivo, sair do carro, resgate; A-058). */
	UFUNCTION(BlueprintPure, Category = "Character")
	UJRInteractionCameraComponent* GetInteractionCamera() const { return InteractionCamera; }

	/** Pistola, escopeta ou rifle (armas de fogo que usam o WeaponComponent). */
	static bool IsFirearmSlot(EJRWeaponSlot Slot)
	{
		return Slot == EJRWeaponSlot::Pistol || Slot == EJRWeaponSlot::Shotgun || Slot == EJRWeaponSlot::Sniper;
	}

	/** 0 = câmera normal, 1 = olhando pela luneta do rifle (transição de ScopeBlendTime). */
	UFUNCTION(BlueprintPure, Category = "Weapon|Scope")
	float GetScopeAlpha() const { return ScopeAlpha; }

	/** Campo de visão da luneta no zoom atual. */
	UFUNCTION(BlueprintPure, Category = "Weapon|Scope")
	float GetScopeFOV() const;

	/** Fôlego para segurar a respiração na luneta (0..1). */
	UFUNCTION(BlueprintPure, Category = "Weapon|Scope")
	float GetBreathFraction() const { return HoldBreathSeconds > 0.f ? BreathLeft / HoldBreathSeconds : 0.f; }

	/** Puxa (true: melhor arma que tiver) ou guarda (false) a arma, com animação. */
	UFUNCTION(BlueprintCallable, Category = "Weapon")
	void SetWeaponEquipped(bool bEquip);

	/** Arma de fogo na mão (pistola ou escopeta). */
	UFUNCTION(BlueprintPure, Category = "Weapon")
	bool IsWeaponEquipped() const { return bWeaponEquipped; }

	UFUNCTION(BlueprintCallable, Category = "Weapon")
	void SelectWeaponSlot(EJRWeaponSlot NewSlot);

	/**
	 * [A-090] Guarda a arma na hora, sem animação, mesmo no meio de uma troca. Usado ao nascer na cidade: o
	 * GrantWeapon(.., true) já tinha começado a puxar a arma e o SetWeaponEquipped(false) era ignorado (troca em
	 * andamento), então o herói aparecia com a pistola na mão.
	 */
	void HolsterWeaponInstant();

	UFUNCTION(BlueprintPure, Category = "Weapon")
	EJRWeaponSlot GetCurrentWeaponSlot() const { return CurrentSlot; }

	UFUNCTION(BlueprintPure, Category = "Weapon")
	bool OwnsWeapon(EJRWeaponSlot Slot) const;

	/** Ganha a arma (e, se pedir, já puxa). */
	UFUNCTION(BlueprintCallable, Category = "Weapon")
	void GrantWeapon(EJRWeaponSlot Slot, bool bEquipNow);

	/** Abaixa, pega a arma do chão (animação) e já fica com ela na mão. */
	UFUNCTION(BlueprintCallable, Category = "Weapon")
	void PickUpWeaponFromGround(EJRWeaponSlot Slot);

	/** Animação de corpo inteiro travando o movimento (pegar, abrir baú). Retorna a duração. */
	UFUNCTION(BlueprintCallable, Category = "Character")
	float PlayFullBodyAction(UAnimSequenceBase* Anim, float PlayRate = 1.f, float MaxDuration = 0.f);

	UFUNCTION(BlueprintPure, Category = "Character")
	UAnimSequenceBase* GetOpenChestAnim() const { return OpenChestAnim; }

	/** Interagir em pé (abastecer, ligar, abrir portão). Usado por portões e pela bomba de gasolina. */
	UFUNCTION(BlueprintPure, Category = "Character")
	UAnimSequenceBase* GetInteractAnim() const { return InteractAnim; }

	/** Ajoelhar e armar o explosivo. Usado pelo AJRBlockingGate. */
	UFUNCTION(BlueprintPure, Category = "Character")
	UAnimSequenceBase* GetPlantAnim() const { return PlantAnim; }

	/** Tremor de câmera (soma 0..1; decai sozinho). Tiro, dano, golpe. */
	UFUNCTION(BlueprintCallable, Category = "Camera")
	void AddCameraTrauma(float Amount);

	/**
	 * [A-073] Um "pacote" de sensação num evento (tiers da skill game-feel): tremor (trauma 0..1), congelada curta
	 * (segundos reais; 0 = sem) e pulso de FOV (graus; negativo = fecha um pouco, "foco"). Respeita jr.Feel.*.
	 * Pequeno: 0,10-0,20 / 0 / -1..-2.  Médio: 0,30-0,45 / 0,04-0,06.  Grande: 0,45-0,6 / 0,08-0,12 (com moderação).
	 */
	UFUNCTION(BlueprintCallable, Category = "Camera|Feel")
	void PlayFeedback(float TraumaAmount, float HitStopSeconds = 0.f, float FOVPulseDegrees = 0.f);

	/** [A-073] Aterrissagem: tremor, "afundada" da câmera e terra levantada conforme a velocidade da queda. */
	virtual void Landed(const FHitResult& Hit) override;

	/** Loop de dirigir (sentado, mãos no volante) usado pelo motorista visual do carro. */
	UFUNCTION(BlueprintPure, Category = "Character")
	UAnimSequenceBase* GetDrivingAnim() const { return DrivingAnim; }

	/**
	 * [A-097] Bicicleta da cidade (AJRBike): enquanto monta, o herói não mira, não atira, não troca de arma, não pula
	 * e não cura; E desce. A bicicleta cuida da velocidade, da curva e da pose (DrivingAnim no slot de corpo inteiro).
	 */
	bool IsRidingBike() const { return MountedBike.IsValid(); }
	class AJRBike* GetMountedBike() const;
	void SetMountedBike(class AJRBike* Bike);
	bool IsSprintHeld() const { return bIsSprinting; }
	FName GetFullBodySlotName() const { return FullBodySlot; }
	FName GetUpperBodySlotName() const { return UpperBodySlot; }

	/** Console (teste): dá todas as armas. */
	UFUNCTION(Exec)
	void JRArmas();

	/** [Remap F1] Cartas de velocidade: escala andar e correr a partir dos valores originais. */
	void SetMoveSpeedMultiplier(float Multiplier);

	/** [Remap F1] Vida máxima antes das cartas (-1 = ainda não guardada). */
	float RemapBaseMaxHealth = -1.f;

	UFUNCTION(BlueprintPure, Category = "Weapon")
	bool IsAimHeld() const { return bAimHeld; }

	/** Poder "Fúria": dano e cadência maiores por alguns segundos. */
	UFUNCTION(BlueprintCallable, Category = "Weapon")
	void ActivateFury(float Seconds);

	/** Segundos restantes de Fúria (0 = inativa). */
	UFUNCTION(BlueprintPure, Category = "Weapon")
	float GetFuryRemaining() const;

	/** Restaura vida e estado para respawn em checkpoint. */
	void ResetForRespawn();

	/**
	 * Liga/desliga a visão em primeira pessoa (tecla V / clique do analógico direito, via AJRPlayerController).
	 * bInstant = sem transição (ex.: ao sair do carro). Morto, a câmera volta para terceira pessoa sozinha.
	 */
	UFUNCTION(BlueprintCallable, Category = "Camera|FirstPerson")
	void SetFirstPersonView(bool bEnable, bool bInstant = false);

	/** Primeira pessoa escolhida pelo jogador. */
	UFUNCTION(BlueprintPure, Category = "Camera|FirstPerson")
	bool IsFirstPersonView() const { return bFirstPersonWanted; }

	/** Primeira pessoa valendo agora (escolhida e vivo). */
	UFUNCTION(BlueprintPure, Category = "Camera|FirstPerson")
	bool IsFirstPersonActive() const;

	/** Câmera final: terceira pessoa (SpringArm) misturada com a câmera nos olhos em primeira pessoa. */
	virtual void CalcCamera(float DeltaTime, FMinimalViewInfo& OutResult) override;

	/**
	 * [A-065] Última conferência da câmera (vale para o herói e o carro): uma esfera de Radius sai do Pivot
	 * (dentro do personagem/carro) até a posição final; se bater em chão, parede ou pedra (canal Camera),
	 * a câmera para antes. Roda DEPOIS do atraso vertical, do tremor e do coice, que mexem na câmera depois
	 * do teste de colisão do SpringArm (era por isso que dava para ver por baixo do terreno).
	 */
	/** [A-070] Zona de câmera de interior (AJRCameraZone): enquanto houver uma, o braço não passa de ArmCm. */
	void EnterCameraZone(float ArmCm) { CameraZoneArms.Add(ArmCm); }
	void ExitCameraZone(float ArmCm) { CameraZoneArms.RemoveSingle(ArmCm); }

	static void KeepCameraOutOfWorld(const AActor* ViewOwner, const FVector& Pivot, float Radius, FVector& InOutLocation,
		const AActor* ExtraIgnore = nullptr);

	// ------------------------------------------------------------ Bolsa, cura e roda de itens (A-055)

	UFUNCTION(BlueprintPure, Category = "Inventory")
	UJRInventoryComponent* GetInventoryComponent() const { return InventoryComponent; }

	/**
	 * Usa bandagem ou kit médico: toca HealAnim (parte de cima do corpo, anda a 40%), cura em HealUseTime
	 * e gasta o item nessa hora. Falha (com aviso) se a vida estiver cheia, sem o item ou já curando.
	 */
	UFUNCTION(BlueprintCallable, Category = "Inventory")
	bool TryUseHealItem(EJRConsumable Item);

	/** Interrompe a cura em andamento (o item não é gasto se a cura ainda não aconteceu). */
	UFUNCTION(BlueprintCallable, Category = "Inventory")
	void CancelHeal(bool bShowToast);

	UFUNCTION(BlueprintPure, Category = "Inventory")
	bool IsHealing() const { return bHealing; }

	/** 0..1 da animação de cura (para o anel no HUD). */
	UFUNCTION(BlueprintPure, Category = "Inventory")
	float GetHealProgress() const;

	UFUNCTION(BlueprintPure, Category = "Inventory")
	EJRConsumable GetHealingItem() const { return HealingItem; }

	/** Usa uma carga de Fúria guardada (roda de itens). */
	UFUNCTION(BlueprintCallable, Category = "Inventory")
	bool TryUseFuryCharge();

	/** Console (teste): bolsa com bandagens, kits e Fúria, e tira metade da vida para testar a cura. */
	UFUNCTION(Exec)
	void JRCura();

	/** Roda de itens aberta (Tab segurado). */
	UFUNCTION(BlueprintPure, Category = "ItemWheel")
	bool IsItemWheelOpen() const { return bItemWheelOpen; }

	/** Setor destacado (EJRWheelEntry como número). */
	int32 GetItemWheelHighlight() const { return WheelHighlight; }

	/** Direção do cursor da roda (X direita, Y cima), 0..1 do raio. */
	FVector2D GetItemWheelCursor() const;

	/** Tempo real (sem câmera lenta) em que a roda abriu: animação de entrada no HUD. */
	double GetItemWheelOpenRealTime() const { return WheelOpenRealTime; }

	/** O que o setor mostra (nome, ícone, quantidade, munição, bloqueado). */
	FJRWheelEntryInfo GetWheelEntryInfo(int32 Index) const;

	/** Fecha a roda sem usar nada (Esc, botão direito, B). */
	UFUNCTION(BlueprintCallable, Category = "ItemWheel")
	void CancelItemWheel();

	/** [A-059] Aba aberta na roda (JRItemWheel::TabWeapons = ARMAS, TabConsumables = CONSUMÍVEIS). */
	int32 GetItemWheelTab() const { return WheelTab; }

	/** Tempo real da última troca de aba e direção (+1 / -1): o HUD anima o deslizar dos ícones. */
	double GetItemWheelTabChangeRealTime() const { return WheelTabChangeRealTime; }
	int32 GetItemWheelTabDirection() const { return WheelTabDir; }

	/** Item no setor da aba aberta. */
	EJRWheelEntry GetItemWheelEntry(int32 Sector) const { return JRItemWheel::EntryAt(WheelTab, Sector); }

	/** Troca a aba da roda aberta (Q/E, roda do mouse, RB, direcional, clique). */
	void SetItemWheelTab(int32 NewTab);
	void CycleItemWheelTab(int32 Direction);

	/**
	 * Lê as teclas da roda aberta (trocar aba, B cancela). Chamado pelo HUD a cada quadro enquanto a roda
	 * está aberta: o personagem não tem Tick e essas teclas não têm Input Action própria.
	 */
	void UpdateItemWheelInput();

protected:
	virtual void BeginPlay() override;
	virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;
	virtual void SetupPlayerInputComponent(UInputComponent* PlayerInputComponent) override;

	void HandleMove(const FInputActionValue& Value);
	void HandleLook(const FInputActionValue& Value);
	void HandleSprint(const FInputActionValue& Value);
	void HandleAim(const FInputActionValue& Value);
	void HandleFireStarted(const FInputActionValue& Value);
	void HandleFireStopped(const FInputActionValue& Value);
	void HandleReload(const FInputActionValue& Value);
	void HandleInteract(const FInputActionValue& Value);
	void HandleToggleWeapon(const FInputActionValue& Value);
	/** Tab/LB apertado (Started) e solto (Completed). */
	void HandleItemWheelPressed(const FInputActionValue& Value);
	void HandleItemWheelReleased(const FInputActionValue& Value);
	/** H / direcional para baixo: bandagem primeiro, senão kit médico. */
	void HandleQuickHeal(const FInputActionValue& Value);
	/** Esc com a roda aberta (BindKey sem consumir: o menu de pausa futuro continua recebendo). */
	void HandleEscapeKey();
	void OpenItemWheel();
	/** bConfirm: usa/equipa o setor destacado. */
	void CloseItemWheel(bool bConfirm);
	/** Move o cursor da roda com o "olhar" deste quadro (lido do controller e zerado: a câmera não gira). */
	void FeedItemWheelCursor();
	void ApplyWheelEntry(EJRWheelEntry Entry);
	void FinishHeal();
	void ApplyHealNow();
	void MeleeAttack();
	void DoMeleeHit();
	void UpdateWeaponVisuals();
	EJRWeaponSlot NextOwnedSlot() const;

	/** Roda do mouse na luneta (2 zooms). */
	void HandleScopeZoomIn();
	void HandleScopeZoomOut();

	UFUNCTION()
	void HandleDeath(UJRHealthComponent* Health, AActor* Killer);

	UFUNCTION()
	void HandleMontageEnded(UAnimMontage* Montage, bool bInterrupted);

	UFUNCTION()
	void HandleExitBlendingOut(UAnimMontage* Montage, bool bInterrupted);

	UFUNCTION()
	void HandleWeaponFired(const FVector& Start, const FVector& End);

	UFUNCTION()
	void HandleReloadStateChanged(bool bIsReloading);

	UFUNCTION()
	void HandleHealthChanged(UJRHealthComponent* Health, float NewHealth, float Delta);

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Character")
	TObjectPtr<USpringArmComponent> SpringArm;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Character")
	TObjectPtr<UCameraComponent> Camera;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Character")
	TObjectPtr<UJRHealthComponent> HealthComponent;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Character")
	TObjectPtr<UJRWeaponComponent> WeaponComponent;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Character")
	TObjectPtr<UJRInteractionComponent> InteractionComponent;

	/** Bolsa: bandagens, kits médicos e cargas de Fúria (A-055). */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Character")
	TObjectPtr<UJRInventoryComponent> InventoryComponent;

	/** Sangue vermelho, ferimentos no corpo, gotejar e direção do dano (A-057). */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Character")
	TObjectPtr<UJRDamageFXComponent> DamageFXComponent;

	/** Câmera das interações (A-058). */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Character")
	TObjectPtr<UJRInteractionCameraComponent> InteractionCamera;

	/** Pistola/escopeta visível na mão direita (só aparece com arma de fogo na mão). */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Weapon")
	TObjectPtr<UStaticMeshComponent> WeaponMesh;

	/** Graveto alien na mão direita (corpo a corpo). */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Weapon")
	TObjectPtr<UStaticMeshComponent> MeleeMesh;

	UPROPERTY(EditDefaultsOnly, Category = "Weapon")
	TObjectPtr<UJRWeaponDefinition> PistolDefinition;

	UPROPERTY(EditDefaultsOnly, Category = "Weapon")
	TObjectPtr<UJRWeaponDefinition> ShotgunDefinition;

	UPROPERTY(EditDefaultsOnly, Category = "Weapon")
	TObjectPtr<UStaticMesh> PistolStaticMesh;

	UPROPERTY(EditDefaultsOnly, Category = "Weapon")
	TObjectPtr<UStaticMesh> ShotgunStaticMesh;

	/** Escala da malha da escopeta em relação ao encaixe da pistola. */
	UPROPERTY(EditDefaultsOnly, Category = "Weapon")
	float ShotgunMeshScale = 1.35f;

	/**
	 * Encaixe de cada arma no osso hand_r (relativo; preenchido pelo tools/unreal/fix_weapon_grips.py).
	 * Identidade = não preenchido: usa o encaixe que a WeaponMesh/MeleeMesh tem no Blueprint.
	 */
	UPROPERTY(EditDefaultsOnly, Category = "Weapon|Grip")
	FTransform PistolGripTransform = FTransform::Identity;

	/** Identidade = usa o da pistola (com ShotgunMeshScale). */
	UPROPERTY(EditDefaultsOnly, Category = "Weapon|Grip")
	FTransform ShotgunGripTransform = FTransform::Identity;

	UPROPERTY(EditDefaultsOnly, Category = "Weapon|Grip")
	FTransform MeleeGripTransform = FTransform::Identity;

	// ---- Rifle de precisão (A-058)

	UPROPERTY(EditDefaultsOnly, Category = "Weapon|Sniper")
	TObjectPtr<UJRWeaponDefinition> SniperDefinition;

	/** Malha do rifle (SM_ARM_Sniper; setup_sniper.py preenche). */
	UPROPERTY(EditDefaultsOnly, Category = "Weapon|Sniper")
	TObjectPtr<UStaticMesh> SniperStaticMesh;

	UPROPERTY(EditDefaultsOnly, Category = "Weapon|Sniper")
	float SniperMeshScale = 1.f;

	/** Identidade = usa o da escopeta (ou da pistola) com SniperMeshScale. */
	UPROPERTY(EditDefaultsOnly, Category = "Weapon|Grip")
	FTransform SniperGripTransform = FTransform::Identity;

	/** Olho na luneta, no espaço da malha do rifle (cm; X = cano, Z = cima). setup_sniper.py mede no modelo. */
	UPROPERTY(EditDefaultsOnly, Category = "Weapon|Sniper")
	FVector SniperScopeOffset = FVector(-6.f, 0.f, 27.f);

	/** Zooms da luneta (roda do mouse troca). */
	UPROPERTY(EditDefaultsOnly, Category = "Weapon|Sniper")
	TArray<float> ScopeFOVs = { 20.f, 10.f };

	/** Tempo da transição para dentro/fora da luneta. */
	UPROPERTY(EditDefaultsOnly, Category = "Weapon|Sniper", meta = (Units = "s", ClampMin = "0.01"))
	float ScopeBlendTime = 0.25f;

	/** Multiplicador extra da sensibilidade na luneta (já cai na proporção do zoom). */
	UPROPERTY(EditDefaultsOnly, Category = "Weapon|Sniper", meta = (ClampMin = "0.05"))
	float ScopeLookScale = 1.f;

	/** Balanço da respiração na luneta (graus) e rapidez. */
	UPROPERTY(EditDefaultsOnly, Category = "Weapon|Sniper", meta = (Units = "Degrees", ClampMin = "0"))
	float ScopeSwayDegrees = 0.45f;

	UPROPERTY(EditDefaultsOnly, Category = "Weapon|Sniper", meta = (ClampMin = "0"))
	float ScopeSwaySpeed = 0.35f;

	/** Segurar Shift na luneta prende a respiração (mira firme) por até estes segundos. */
	UPROPERTY(EditDefaultsOnly, Category = "Weapon|Sniper", meta = (Units = "s", ClampMin = "0"))
	float HoldBreathSeconds = 3.f;

	/** Depois do tiro a luneta sai por este tempo (ferrolho) e volta se ainda estiver mirando. 0 = não sai. */
	UPROPERTY(EditDefaultsOnly, Category = "Weapon|Sniper", meta = (Units = "s", ClampMin = "0"))
	float RescopeDelay = 0.7f;

	/** Andar mirando pela luneta (fração do WalkSpeed). */
	UPROPERTY(EditDefaultsOnly, Category = "Weapon|Sniper", meta = (ClampMin = "0", ClampMax = "1"))
	float ScopeMoveSpeedFactor = 0.5f;

	UPROPERTY(EditDefaultsOnly, Category = "Weapon|Sniper")
	TSoftObjectPtr<USoundBase> ScopeZoomSound = TSoftObjectPtr<USoundBase>(FSoftObjectPath(TEXT("/Game/Audio/SFX/Weapons/SFX_Scope_Zoom.SFX_Scope_Zoom")));

	/** Distância da câmera curando (sobre o ombro, mais perto; A-058). */
	UPROPERTY(EditDefaultsOnly, Category = "Camera", meta = (Units = "cm"))
	float HealArmLength = 200.f;

	/** Golpes do graveto (alternados em combo, slot UpperBody). */
	UPROPERTY(EditDefaultsOnly, Category = "Weapon|Melee")
	TArray<TObjectPtr<UAnimSequenceBase>> MeleeAnims;

	UPROPERTY(EditDefaultsOnly, Category = "Weapon|Melee")
	float MeleeDamage = 40.f;

	UPROPERTY(EditDefaultsOnly, Category = "Weapon|Melee", meta = (Units = "cm"))
	float MeleeRange = 170.f;

	UPROPERTY(EditDefaultsOnly, Category = "Weapon|Melee", meta = (Units = "cm"))
	float MeleeRadius = 110.f;

	UPROPERTY(EditDefaultsOnly, Category = "Weapon|Melee", meta = (Units = "s"))
	float MeleeHitDelay = 0.3f;

	UPROPERTY(EditDefaultsOnly, Category = "Weapon|Melee", meta = (Units = "s"))
	float MeleeCooldown = 0.55f;

	UPROPERTY(EditDefaultsOnly, Category = "Weapon|Melee")
	float MeleePlayRate = 1.4f;

	/** Empurrão do golpe (cm/s) em zumbis e objetos. */
	UPROPERTY(EditDefaultsOnly, Category = "Weapon|Melee")
	float MeleeKnockback = 650.f;

	/** Pegar do chão (corpo inteiro). */
	UPROPERTY(EditDefaultsOnly, Category = "Animation")
	TObjectPtr<UAnimSequenceBase> PickupAnim;

	UPROPERTY(EditDefaultsOnly, Category = "Animation", meta = (Units = "s"))
	float PickupGrantTime = 0.9f;

	UPROPERTY(EditDefaultsOnly, Category = "Animation", meta = (Units = "s"))
	float PickupDuration = 1.6f;

	/** [A-073] Velocidade da animação de pegar do chão (era fixa 1,3 no código). */
	UPROPERTY(EditDefaultsOnly, Category = "Animation", meta = (ClampMin = "0.5", ClampMax = "2"))
	float PickupPlayRate = 1.25f;

	/**
	 * [A-073] Em que fração da animação a mão chega no item (ali o item some do chão e aparece na mão).
	 * "Grab Torch From Floor" (Mixamo) toca o chão perto de 40%. O teto é PickupGrantTime e 0,85 s
	 * (o JRPickup se apaga 0,9 s depois de pego).
	 */
	UPROPERTY(EditDefaultsOnly, Category = "Animation", meta = (ClampMin = "0.1", ClampMax = "0.9"))
	float PickupGrabFraction = 0.42f;

	/** [A-073] Tempo para o herói virar de frente para o item antes de abaixar. */
	UPROPERTY(EditDefaultsOnly, Category = "Animation", meta = (Units = "s", ClampMin = "0"))
	float PickupTurnTime = 0.2f;

	/** Abrir baú (corpo inteiro). */
	UPROPERTY(EditDefaultsOnly, Category = "Animation")
	TObjectPtr<UAnimSequenceBase> OpenChestAnim;

	UPROPERTY(EditDefaultsOnly, Category = "Input")
	TObjectPtr<UInputAction> MoveAction;

	UPROPERTY(EditDefaultsOnly, Category = "Input")
	TObjectPtr<UInputAction> LookAction;

	/** Olhar com o mouse (separado do analógico, como no template da Epic). */
	UPROPERTY(EditDefaultsOnly, Category = "Input")
	TObjectPtr<UInputAction> MouseLookAction;

	UPROPERTY(EditDefaultsOnly, Category = "Input")
	TObjectPtr<UInputAction> JumpAction;

	UPROPERTY(EditDefaultsOnly, Category = "Input")
	TObjectPtr<UInputAction> SprintAction;

	UPROPERTY(EditDefaultsOnly, Category = "Input")
	TObjectPtr<UInputAction> AimAction;

	UPROPERTY(EditDefaultsOnly, Category = "Input")
	TObjectPtr<UInputAction> FireAction;

	UPROPERTY(EditDefaultsOnly, Category = "Input")
	TObjectPtr<UInputAction> ReloadAction;

	UPROPERTY(EditDefaultsOnly, Category = "Input")
	TObjectPtr<UInputAction> InteractAction;

	/** Equipar/guardar a pistola. */
	UPROPERTY(EditDefaultsOnly, Category = "Input")
	TObjectPtr<UInputAction> ToggleWeaponAction;

	/** Roda de itens: segurar Tab / LB (IA_ItemWheel no IMC_JR_Combat; só a pé). */
	UPROPERTY(EditDefaultsOnly, Category = "Input")
	TObjectPtr<UInputAction> ItemWheelAction;

	/** Cura rápida: H / direcional para baixo (IA_Heal no IMC_JR_Combat). */
	UPROPERTY(EditDefaultsOnly, Category = "Input")
	TObjectPtr<UInputAction> HealAction;

	/** Velocidade do jogo com a roda aberta (o HUD continua no tempo real). */
	UPROPERTY(EditDefaultsOnly, Category = "ItemWheel", meta = (ClampMin = "0.05", ClampMax = "1"))
	float ItemWheelTimeDilation = 0.25f;

	/** Sensibilidade do cursor da roda (mouse e analógico; maior = escolhe com menos movimento). */
	UPROPERTY(EditDefaultsOnly, Category = "ItemWheel", meta = (ClampMin = "0.05"))
	float ItemWheelSensitivity = 1.f;

	/** Tamanho do "raio" do cursor, em graus de olhar acumulados (menor = mais sensível). */
	UPROPERTY(EditDefaultsOnly, Category = "ItemWheel", meta = (ClampMin = "1"))
	float ItemWheelCursorRadius = 10.f;

	/** Fração do raio sem escolha (o destaque anterior fica). */
	UPROPERTY(EditDefaultsOnly, Category = "ItemWheel", meta = (ClampMin = "0", ClampMax = "0.9"))
	float ItemWheelDeadZone = 0.35f;

	/** Animação de usar bandagem/kit (slot UpperBody; o agente de animações preenche nos BPs dos heróis). */
	UPROPERTY(EditDefaultsOnly, Category = "Animation|Heal")
	TObjectPtr<UAnimSequenceBase> HealAnim;

	/** Segundo da animação em que a vida sobe e o item é gasto. */
	UPROPERTY(EditDefaultsOnly, Category = "Animation|Heal", meta = (Units = "s", ClampMin = "0"))
	float HealUseTime = 1.4f;

	/** Duração total da ação de curar (a animação é cortada aqui se for mais longa). */
	UPROPERTY(EditDefaultsOnly, Category = "Animation|Heal", meta = (Units = "s", ClampMin = "0.1"))
	float HealDuration = 2.2f;

	/** Velocidade de andar durante a cura (fração do WalkSpeed). */
	UPROPERTY(EditDefaultsOnly, Category = "Animation|Heal", meta = (ClampMin = "0", ClampMax = "1"))
	float HealMoveSpeedFactor = 0.4f;

	/** Dano de um golpe só que interrompe a cura (golpes menores não interrompem). */
	UPROPERTY(EditDefaultsOnly, Category = "Animation|Heal", meta = (ClampMin = "0"))
	float HealInterruptDamage = 20.f;

	UPROPERTY(EditDefaultsOnly, Category = "Movement", meta = (Units = "cm/s"))
	float WalkSpeed = 350.f;

	UPROPERTY(EditDefaultsOnly, Category = "Movement", meta = (Units = "cm/s"))
	float SprintSpeed = 600.f;

	/** [Remap F1] WalkSpeed/SprintSpeed antes das cartas (-1 = ainda não guardado). */
	float BaseWalkSpeed = -1.f;
	float BaseSprintSpeed = -1.f;

	/** Distância da câmera (era 400: herói ~15% da altura da tela; 300 = ~20%, A-057). */
	UPROPERTY(EditDefaultsOnly, Category = "Camera", meta = (Units = "cm"))
	float DefaultArmLength = 300.f;

	UPROPERTY(EditDefaultsOnly, Category = "Camera", meta = (Units = "cm"))
	float AimArmLength = 170.f;

	/** Câmera sobre o ombro direito (andando / mirando). Y = lado, Z = altura. */
	UPROPERTY(EditDefaultsOnly, Category = "Camera")
	FVector ShoulderOffset = FVector(0.f, 45.f, 45.f);

	UPROPERTY(EditDefaultsOnly, Category = "Camera")
	FVector AimShoulderOffset = FVector(0.f, 70.f, 55.f);

	UPROPERTY(EditDefaultsOnly, Category = "Camera")
	float CameraBlendSpeed = 10.f;

	// ---- Sensação de combate (A-057)

	/** Campo de visão normal (terceira pessoa). */
	UPROPERTY(EditDefaultsOnly, Category = "Camera|Feel", meta = (Units = "Degrees", ClampMin = "60", ClampMax = "120"))
	float BaseFOV = 90.f;

	/** Campo de visão mirando (zoom). */
	UPROPERTY(EditDefaultsOnly, Category = "Camera|Feel", meta = (Units = "Degrees", ClampMin = "30", ClampMax = "120"))
	float AimFOV = 70.f;

	/** Graus a mais correndo (sensação de velocidade). */
	UPROPERTY(EditDefaultsOnly, Category = "Camera|Feel", meta = (Units = "Degrees", ClampMin = "0"))
	float SprintFOVBonus = 5.f;

	UPROPERTY(EditDefaultsOnly, Category = "Camera|Feel", meta = (ClampMin = "0.5"))
	float FOVBlendSpeed = 8.f;

	/** Batendo em parede a câmera chega perto na hora; ao sair volta suave com esta rapidez (0 = na hora). */
	UPROPERTY(EditDefaultsOnly, Category = "Camera|Feel", meta = (ClampMin = "0"))
	float CameraCollisionRecoverSpeed = 6.f;

	/** Atraso vertical suave da câmera (pulos, degraus). 0 = sem. */
	UPROPERTY(EditDefaultsOnly, Category = "Camera|Feel", meta = (ClampMin = "0"))
	float CameraVerticalLagSpeed = 12.f;

	/** [A-065] Folga mínima entre a câmera e o mundo (chão, parede) na conferência final. 0 = desliga. */
	UPROPERTY(EditDefaultsOnly, Category = "Camera|Feel", meta = (Units = "cm", ClampMin = "0"))
	float CameraSafetyRadius = 20.f;

	/** Tremor máximo (graus) com trauma 1. */
	UPROPERTY(EditDefaultsOnly, Category = "Camera|Feel", meta = (Units = "Degrees", ClampMin = "0"))
	float ShakeMaxAngle = 2.5f;

	/** Deslocamento máximo do tremor (cm). */
	UPROPERTY(EditDefaultsOnly, Category = "Camera|Feel", meta = (Units = "cm", ClampMin = "0"))
	float ShakeMaxOffset = 4.f;

	/** Quanto trauma some por segundo. */
	UPROPERTY(EditDefaultsOnly, Category = "Camera|Feel", meta = (ClampMin = "0.1"))
	float ShakeDecay = 2.2f;

	UPROPERTY(EditDefaultsOnly, Category = "Camera|Feel", meta = (ClampMin = "1"))
	float ShakeFrequency = 22.f;

	/** Trauma ao levar 40 de dano (proporcional; mínimo 0,15). */
	UPROPERTY(EditDefaultsOnly, Category = "Camera|Feel", meta = (ClampMin = "0", ClampMax = "1"))
	float DamageShake = 0.45f;

	/** "Congelada" no abate corpo a corpo: velocidade do jogo e duração em tempo real. */
	UPROPERTY(EditDefaultsOnly, Category = "Camera|Feel", meta = (ClampMin = "0.01", ClampMax = "1"))
	float HitStopDilation = 0.05f;

	/** Congelada do ABATE corpo a corpo (tier grande). [A-073] era 0,06. */
	UPROPERTY(EditDefaultsOnly, Category = "Camera|Feel", meta = (Units = "s", ClampMin = "0"))
	float HitStopDuration = 0.085f;

	/** [A-073] Congelada de um golpe corpo a corpo que acerta sem matar (tier médio). 0 = sem. */
	UPROPERTY(EditDefaultsOnly, Category = "Camera|Feel", meta = (Units = "s", ClampMin = "0"))
	float MeleeHitStop = 0.045f;

	/** [A-073] Queda mais lenta que isto não tem efeito (pulo normal cai a ~450). ~2,2 m de altura. */
	UPROPERTY(EditDefaultsOnly, Category = "Camera|Feel", meta = (Units = "cm/s", ClampMin = "0"))
	float LandingMinSpeed = 650.f;

	/** [A-073] Queda a partir desta velocidade = efeito máximo (~6 m de altura). */
	UPROPERTY(EditDefaultsOnly, Category = "Camera|Feel", meta = (Units = "cm/s", ClampMin = "1"))
	float LandingHeavySpeed = 1100.f;

	/** [A-073] "Afundada" pedida na aterrissagem mais forte (entra rápido e volta como mola: o pico fica ~60% disto). */
	UPROPERTY(EditDefaultsOnly, Category = "Camera|Feel", meta = (Units = "cm", ClampMin = "0"))
	float LandingMaxDip = 12.f;

	/** [A-073] Cor da terra levantada na aterrissagem forte. */
	UPROPERTY(EditDefaultsOnly, Category = "Camera|Feel")
	FLinearColor LandingDustColor = FLinearColor(0.16f, 0.12f, 0.09f, 1.f);

	/**
	 * [A-073] Peso ao andar: aceleração e frenagem do CharacterMovement aplicadas no BeginPlay
	 * (0 = mantém o que estiver no Blueprint). Padrão da engine: 2048 e 2048 (arranque e parada secos).
	 */
	UPROPERTY(EditDefaultsOnly, Category = "Movement|Feel", meta = (ClampMin = "0"))
	float MoveMaxAcceleration = 1500.f;

	UPROPERTY(EditDefaultsOnly, Category = "Movement|Feel", meta = (ClampMin = "0"))
	float MoveBrakingDeceleration = 1500.f;

	/** Osso da cabeça seguido pela câmera em primeira pessoa (esqueleto do herói: "head"). */
	UPROPERTY(EditDefaultsOnly, Category = "Camera|FirstPerson")
	FName FPHeadBone = TEXT("head");

	/**
	 * Olhos em relação ao osso da cabeça (cm), no sentido para onde a câmera olha: X = frente, Y = lado, Z = cima.
	 * Um pouco à frente do rosto para não ver o crânio por dentro.
	 */
	UPROPERTY(EditDefaultsOnly, Category = "Camera|FirstPerson")
	FVector EyeOffset = FVector(10.f, 0.f, 8.f);

	/** Frente extra quando olha todo para baixo: vê pernas e pés sem ver o peito por dentro. */
	UPROPERTY(EditDefaultsOnly, Category = "Camera|FirstPerson", meta = (Units = "cm"))
	float LookDownForwardOffset = 12.f;

	/** 0 = câmera presa na cabeça (balança a cada passo); 1 = ponto estável (suavizado). Padrão 0,7. */
	UPROPERTY(EditDefaultsOnly, Category = "Camera|FirstPerson", meta = (ClampMin = "0", ClampMax = "1"))
	float StabilizeAlpha = 0.7f;

	/** Estabilização durante animações de corpo inteiro (pegar do chão, abrir baú, sair do carro). */
	UPROPERTY(EditDefaultsOnly, Category = "Camera|FirstPerson", meta = (ClampMin = "0", ClampMax = "1"))
	float FullBodyStabilizeAlpha = 0.85f;

	/** Rapidez com que o ponto estável acompanha a cabeça (maior = segue mais rápido, balança mais). */
	UPROPERTY(EditDefaultsOnly, Category = "Camera|FirstPerson", meta = (ClampMin = "0.1"))
	float StabilizeSpeed = 5.f;

	/** Campo de visão em primeira pessoa. */
	UPROPERTY(EditDefaultsOnly, Category = "Camera|FirstPerson", meta = (Units = "Degrees", ClampMin = "60", ClampMax = "120"))
	float FPFov = 90.f;

	/** Duração da transição entre terceira e primeira pessoa. */
	UPROPERTY(EditDefaultsOnly, Category = "Camera|FirstPerson", meta = (Units = "s"))
	float FPBlendTime = 0.25f;

	/** Limites de olhar para baixo/cima em primeira pessoa. */
	UPROPERTY(EditDefaultsOnly, Category = "Camera|FirstPerson", meta = (Units = "Degrees"))
	float FPPitchMin = -80.f;

	UPROPERTY(EditDefaultsOnly, Category = "Camera|FirstPerson", meta = (Units = "Degrees"))
	float FPPitchMax = 80.f;

	// ---- [A-068] Arma em primeira pessoa (viewmodel): a arma sai da mão do corpo inteiro (que fica no quadril,
	// fora do quadro) e vai para a frente da câmera, com respiração, balanço ao andar/correr, atraso ao girar
	// (sway), mira no centro e o coice do A-057 somado. As mãos do corpo NÃO acompanham (limitação: um modelo
	// de braços só para a primeira pessoa fica como melhoria futura).

	/** Liga a arma na frente da câmera em primeira pessoa. */
	UPROPERTY(EditDefaultsOnly, Category = "Camera|FirstPerson|Weapon")
	bool bFPViewmodel = true;

	/** [A-086] Tamanho da arma na frente da câmera (a pistola tampava ~30% da tela). */
	UPROPERTY(EditDefaultsOnly, Category = "Camera|FirstPerson|Weapon", meta = (ClampMin = "0.3", ClampMax = "1.5"))
	float FPWeaponScale = 0.72f;

	/** Pistola: posição do punho em relação à câmera (cm; X frente, Y direita, Z cima). */
	UPROPERTY(EditDefaultsOnly, Category = "Camera|FirstPerson|Weapon")
	FVector FPPistolOffset = FVector(36.f, 15.f, -16.f);

	/** Pistola mirando: alça de mira no centro da tela (cm). */
	UPROPERTY(EditDefaultsOnly, Category = "Camera|FirstPerson|Weapon")
	FVector FPPistolAimOffset = FVector(30.f, 0.f, -10.5f);

	/** Escopeta e rifle (armas longas) fora da mira (cm). O rifle mirando usa a luneta (A-058). */
	UPROPERTY(EditDefaultsOnly, Category = "Camera|FirstPerson|Weapon")
	FVector FPRifleOffset = FVector(26.f, 14.f, -17.f);

	UPROPERTY(EditDefaultsOnly, Category = "Camera|FirstPerson|Weapon")
	FVector FPRifleAimOffset = FVector(20.f, 0.f, -11.f);

	/** Graveto (corpo a corpo) parado na frente; durante o golpe volta para a mão (a animação mostra o golpe). */
	UPROPERTY(EditDefaultsOnly, Category = "Camera|FirstPerson|Weapon")
	FVector FPMeleeOffset = FVector(34.f, 20.f, -24.f);

	/** Inclinação do graveto na frente da câmera (o comprido da malha é o X dela). */
	UPROPERTY(EditDefaultsOnly, Category = "Camera|FirstPerson|Weapon")
	FRotator FPMeleeRotation = FRotator(35.f, -15.f, -20.f);

	/** Arma fora da mira apontando um pouco para o centro (graus; negativo = para a esquerda). */
	UPROPERTY(EditDefaultsOnly, Category = "Camera|FirstPerson|Weapon", meta = (Units = "Degrees"))
	float FPWeaponYawIn = -2.5f;

	/** Balanço vertical ao andar e correndo (cm). O lateral é 1,5 vez isso. */
	UPROPERTY(EditDefaultsOnly, Category = "Camera|FirstPerson|Weapon", meta = (Units = "cm", ClampMin = "0"))
	float FPBobWalkCm = 0.7f;

	UPROPERTY(EditDefaultsOnly, Category = "Camera|FirstPerson|Weapon", meta = (Units = "cm", ClampMin = "0"))
	float FPBobSprintCm = 1.8f;

	/** Ciclos de balanço por segundo (1 ciclo = 2 passos) andando e correndo. */
	UPROPERTY(EditDefaultsOnly, Category = "Camera|FirstPerson|Weapon", meta = (ClampMin = "0"))
	float FPBobWalkRate = 0.95f;

	UPROPERTY(EditDefaultsOnly, Category = "Camera|FirstPerson|Weapon", meta = (ClampMin = "0"))
	float FPBobSprintRate = 1.45f;

	/** Respiração parado: altura (cm) e rapidez (radianos por segundo; 1,6 = um ciclo a cada ~4 s). */
	UPROPERTY(EditDefaultsOnly, Category = "Camera|FirstPerson|Weapon", meta = (Units = "cm", ClampMin = "0"))
	float FPBreathCm = 0.25f;

	UPROPERTY(EditDefaultsOnly, Category = "Camera|FirstPerson|Weapon", meta = (ClampMin = "0"))
	float FPBreathRate = 1.6f;

	/** Atraso ao girar a câmera: graus de inclinação da arma por grau/s de giro, limite e volta (mola). */
	UPROPERTY(EditDefaultsOnly, Category = "Camera|FirstPerson|Weapon", meta = (ClampMin = "0"))
	float FPSwayAmount = 0.012f;

	UPROPERTY(EditDefaultsOnly, Category = "Camera|FirstPerson|Weapon", meta = (Units = "Degrees", ClampMin = "0"))
	float FPSwayMaxDegrees = 4.f;

	UPROPERTY(EditDefaultsOnly, Category = "Camera|FirstPerson|Weapon", meta = (ClampMin = "0.1"))
	float FPSwaySpeed = 9.f;

	/** Rapidez de levar a arma à mira (e de volta). */
	UPROPERTY(EditDefaultsOnly, Category = "Camera|FirstPerson|Weapon", meta = (ClampMin = "0.1"))
	float FPAimBlendSpeed = 12.f;

	/**
	 * Ossos escondidos em primeira pessoa (a câmera fica dentro da cabeça). Os filhos somem junto
	 * (cabelo/capuz presos na cabeça). Se o pescoço aparecer ao olhar para baixo, adicione "neck_02".
	 */
	UPROPERTY(EditDefaultsOnly, Category = "Camera|FirstPerson")
	TArray<FName> HiddenBones = { TEXT("head"), TEXT("upperarm_l"), TEXT("upperarm_r") }; // [A-086] braços do corpo inteiro somem em 1a pessoa (apareciam mãos soltas)

	UPROPERTY(EditDefaultsOnly, Category = "Weapon")
	float FuryDamageMultiplier = 2.f;

	UPROPERTY(EditDefaultsOnly, Category = "Weapon")
	float FuryFireRateMultiplier = 1.75f;

	UPROPERTY(EditDefaultsOnly, Category = "Animation")
	TObjectPtr<UAnimMontage> ExitVehicleMontage;

	/** Loop sentado dirigindo (do mesmo esqueleto do herói). O carro lê isto do Blueprint do herói. */
	UPROPERTY(EditDefaultsOnly, Category = "Animation")
	TObjectPtr<UAnimSequenceBase> DrivingAnim;

	UPROPERTY(EditDefaultsOnly, Category = "Animation")
	TObjectPtr<UAnimMontage> RescueHugMontage;

	UPROPERTY(EditDefaultsOnly, Category = "Animation")
	TObjectPtr<UAnimMontage> DeathMontage;

	/** Pose de mira com a pistola (loop no UpperBody só ao mirar ou atirar). */
	UPROPERTY(EditDefaultsOnly, Category = "Animation")
	TObjectPtr<UAnimSequenceBase> AimAnim;

	/** Recuo de um tiro (curto; começa e termina na pose de mira). Cada herói tem o seu. */
	UPROPERTY(EditDefaultsOnly, Category = "Animation")
	TObjectPtr<UAnimSequenceBase> FireAnim;

	/** Puxar a pistola. */
	UPROPERTY(EditDefaultsOnly, Category = "Animation")
	TObjectPtr<UAnimSequenceBase> EquipAnim;

	/** Guardar a pistola (o arquivo começa mirando; pulamos para UnequipStartTime). */
	UPROPERTY(EditDefaultsOnly, Category = "Animation")
	TObjectPtr<UAnimSequenceBase> UnequipAnim;

	UPROPERTY(EditDefaultsOnly, Category = "Animation", meta = (Units = "s"))
	float UnequipStartTime = 3.2f;

	/** Momento do "puxar" em que a arma aparece na mão. */
	UPROPERTY(EditDefaultsOnly, Category = "Animation", meta = (Units = "s"))
	float EquipShowWeaponTime = 0.55f;

	/** Momento do "guardar" em que a arma some (já atrás das costas). */
	UPROPERTY(EditDefaultsOnly, Category = "Animation", meta = (Units = "s"))
	float UnequipHideWeaponTime = 0.65f;

	/** Quanto tempo a arma continua erguida depois do último tiro. */
	UPROPERTY(EditDefaultsOnly, Category = "Animation", meta = (Units = "s"))
	float AimLingerTime = 0.8f;

	UPROPERTY(EditDefaultsOnly, Category = "Weapon")
	bool bStartWithWeaponEquipped = false;

	/** Recarga (slot UpperBody). A velocidade é ajustada para durar o ReloadTime da arma. */
	UPROPERTY(EditDefaultsOnly, Category = "Animation")
	TObjectPtr<UAnimSequenceBase> ReloadAnim;

	/** Escopeta: mirar/atirar/recarregar/sacar (vazio = usa a da pistola). setup_anims_wave2.py preenche com o rifle. */
	UPROPERTY(EditDefaultsOnly, Category = "Animation|Shotgun")
	TObjectPtr<UAnimSequenceBase> ShotgunAimAnim;

	UPROPERTY(EditDefaultsOnly, Category = "Animation|Shotgun")
	TObjectPtr<UAnimSequenceBase> ShotgunFireAnim;

	UPROPERTY(EditDefaultsOnly, Category = "Animation|Shotgun")
	TObjectPtr<UAnimSequenceBase> ShotgunReloadAnim;

	UPROPERTY(EditDefaultsOnly, Category = "Animation|Shotgun")
	TObjectPtr<UAnimSequenceBase> ShotgunEquipAnim;

	/**
	 * Arma de fogo na mão SEM mirar (parado/andando): loop no UpperBody com a mão fechada na arma, cano baixo.
	 * Vazio = como antes (anima desarmado).
	 */
	UPROPERTY(EditDefaultsOnly, Category = "Animation")
	TObjectPtr<UAnimSequenceBase> ArmedIdleAnim;

	/** Interagir (corpo inteiro): abastecer, ligar gerador, abrir portão. */
	UPROPERTY(EditDefaultsOnly, Category = "Animation")
	TObjectPtr<UAnimSequenceBase> InteractAnim;

	/** Armar o explosivo (corpo inteiro, ajoelhado). */
	UPROPERTY(EditDefaultsOnly, Category = "Animation")
	TObjectPtr<UAnimSequenceBase> PlantAnim;

	/** Reação ao levar dano (slot UpperBody; não interrompe tiro/recarga). */
	UPROPERTY(EditDefaultsOnly, Category = "Animation")
	TObjectPtr<UAnimSequenceBase> HitReactAnim;

	/** Slot do AnimBP usado pelas animações de parte de cima do corpo. */
	UPROPERTY(EditDefaultsOnly, Category = "Animation")
	FName UpperBodySlot = TEXT("UpperBody");

	/** Slot de corpo inteiro (morte, sair do carro, resgate): enquanto ativo, a pose da arma sai. */
	UPROPERTY(EditDefaultsOnly, Category = "Animation")
	FName FullBodySlot = TEXT("DefaultSlot");

	/** Atraso entre a morte e o reinício no checkpoint. */
	UPROPERTY(EditDefaultsOnly, Category = "Character", meta = (Units = "s"))
	float FailureDelay = 2.5f;

private:
	void NotifyFailure();

	/** Esconde/mostra os HiddenBones (só age quando muda). */
	void SetHeadHiddenForView(bool bHide);

	/** Limita o olhar para cima/baixo em primeira pessoa; em terceira volta ao padrão da câmera. */
	void ApplyFirstPersonPitchLimits(bool bFirstPerson);

	/** Posição dos olhos: cabeça misturada com um ponto estável (menos balanço) + EyeOffset. */
	FVector ComputeFirstPersonEye(float DeltaTime, const FRotator& ViewRot);

	/** [A-068] Arma na frente da câmera em primeira pessoa (chamado no fim de CalcCamera, com a vista final). */
	void UpdateFirstPersonViewmodel(float DeltaTime, const FMinimalViewInfo& View);
	/** [A-068] Devolve pistola/graveto ao encaixe na mão (terceira pessoa, luneta, cena de interação). */
	void RestoreViewmodelPose();

	bool bFirstPersonWanted = false;
	bool bHeadHidden = false;
	bool bFPStableValid = false;
	bool bSavedPitchLimits = false;
	/** 0 = terceira pessoa, 1 = primeira pessoa (transição). */
	float FPBlendAlpha = 0.f;
	float SavedPitchMin = -89.9f;
	float SavedPitchMax = 89.9f;
	/** Cabeça suavizada no espaço do personagem (ponto estável). */
	FVector FPStableLocal = FVector::ZeroVector;

	// [A-068] estado da arma em primeira pessoa (por quadro)
	float VMActionWeight = 0.f;   // 1 = arma na frente; 0 = na mão (luneta, golpe, cena de interação)
	float VMBobPhase = 0.f;
	float VMBreathTime = 0.f;
	float VMAimNow = 0.f;
	float VMSprintNow = 0.f;
	float VMDipNow = 0.f;         // abaixa na recarga, troca de arma, cura e roda de itens
	FRotator VMSwayRot = FRotator::ZeroRotator;
	FRotator VMLastViewRot = FRotator::ZeroRotator;
	bool bVMLastViewValid = false;
	bool bVMApplied = false;

	FTimerHandle FailureTimer;

	void UpdateUpperBody();
	void PlayAimPose(float BlendIn);

	// ---- Sensação de combate (A-057)
	/** Coice, tranco da arma, tremor e FOV por quadro (chamado de CalcCamera: sem Tick). */
	void UpdateCombatFeel(float DeltaTime);
	/** Aplica o coice do tiro atual (câmera, arma na mão, tremor). */
	void ApplyShotFeedback();
	/** Encaixe base da arma atual (sem o tranco). */
	FTransform GetGripFor(EJRWeaponSlot Slot) const;
	void ApplyWeaponKickTransform();
	/** Luneta: alvo, transição, esconder o corpo, respiração e velocidade de andar (por quadro). */
	void UpdateScope(float DeltaTime);
	bool WantsScope() const;
	/** Pistola/escopeta/rifle -> definição. */
	UJRWeaponDefinition* GetDefinitionFor(EJRWeaponSlot Slot) const;
	/** Rifle e escopeta usam as animações de rifle (Shotgun*Anim) quando existem. */
	bool UsesRifleAnims() const { return CurrentSlot == EJRWeaponSlot::Shotgun || CurrentSlot == EJRWeaponSlot::Sniper; }
	/** Coice da vista, tremor e FOV no resultado final da câmera. */
	void ApplyViewFeel(FMinimalViewInfo& OutResult) const;
	void StartHitStop();
	/** [A-073] congelada com duração própria (segundos reais); respeita jr.Feel.HitStop. */
	void StartHitStopFor(float Seconds);
	void EndHitStop();
	/** [A-073] o JRPickup que acabou de ser pego (marcado como pego, mais perto, até 3 m). */
	AActor* FindPickupBeingTaken() const;
	/** [A-073] vira o corpo suavemente para um ponto (parado, durante a ação). */
	void FacePointSmooth(const FVector& Point, float Seconds);
	UAnimSequenceBase* GetActiveAimAnim() const;
	UAnimSequenceBase* GetActiveFireAnim() const;
	UAnimSequenceBase* GetActiveReloadAnim() const;
	UAnimSequenceBase* GetActiveEquipAnim() const;
	bool IsArmedIdlePlaying() const;
	void PlayArmedIdle(float BlendIn);
	void HandleRecoilBlendingOut(UAnimMontage* Montage, bool bInterrupted);
	bool WantsAimPose() const;

	UPROPERTY(Transient)
	TObjectPtr<UAnimMontage> AimMontage;

	UPROPERTY(Transient)
	TObjectPtr<UAnimMontage> ArmedIdleMontage;

	// Sensação de combate (estado por quadro)
	FRotator RecoilOffset = FRotator::ZeroRotator;   // coice só da vista (volta sozinho)
	FRotator RecoilPending = FRotator::ZeroRotator;  // coice entrando (rápido, não instantâneo)
	FRotator RecoilKeepPending = FRotator::ZeroRotator; // parte que vai para a mira de verdade
	float RecoilRecoverySpeed = 9.f;
	float KickBackNow = 0.f;
	float KickPitchNow = 0.f;
	float KickRecoverySpeed = 14.f;
	bool bKickApplied = false;
	float Trauma = 0.f;
	float ShakeTime = 0.f;
	float FOVOffsetNow = 0.f;
	float SmoothedCamDist = 0.f;
	/** [A-070] Braços pedidos pelas zonas de câmera em que o herói está (o menor vale). */
	TArray<float> CameraZoneArms;
	bool bCamDistValid = false;
	double SmoothedCamZ = 0.0;
	bool bCamZValid = false;
	FTransform WeaponMeshBaseRelative = FTransform::Identity;
	FTransform MeleeMeshBaseRelative = FTransform::Identity;
	FTimerHandle HitStopTimer;
	FTimerHandle PumpTimer;
	bool bHitStopActive = false;
	// [A-073] aterrissagem e pulso de FOV (entram rápido, voltam como mola; tempo real)
	float LandDipNow = 0.f;
	float LandDipPending = 0.f;
	float FOVPulseNow = 0.f;
	float FOVPulsePending = 0.f;
	FTimerHandle FaceTimer;
	float FaceTargetYaw = 0.f;
	float FaceTimeLeft = 0.f;

	FTimerHandle UpperBodyTimer;
	FTimerHandle FuryTimer;
	FTimerHandle MeleeTimer;
	FTimerHandle ActionTimer;
	FTimerHandle PickupTimer;
	EJRWeaponSlot CurrentSlot = EJRWeaponSlot::None;
	bool bOwnMelee = false;
	bool bOwnPistol = false;
	bool bOwnShotgun = false;
	bool bOwnSniper = false;
	// Luneta (A-058)
	float ScopeAlpha = 0.f;
	float ScopeTime = 0.f;
	float BreathLeft = 3.f;
	int32 ScopeZoomIndex = 0;
	double ScopeBlockedUntil = 0.0;
	bool bBreathExhausted = false;
	bool bScopeBodyHidden = false;
	bool bScopeSlowed = false;
	bool bMeleeBusy = false;
	int32 MeleeComboIndex = 0;
	double LastMeleeTime = -100.0;
	FTimerHandle WeaponVisibilityTimer;
	FTimerHandle WeaponTransitionTimer;
	double LastShotTime = -1000.0;
	bool bWeaponEquipped = false;
	bool bWeaponTransition = false;
	bool bAimHeld = false;
	bool bFireHeld = false;

	TWeakObjectPtr<AActor> ExitingVehicle;
	TEnumAsByte<ECollisionResponse> ExitVehiclePawnResponse = ECR_Block;
	bool bIsSprinting = false;

	/** [A-097] Bicicleta montada (nula a pé). */
	TWeakObjectPtr<class AJRBike> MountedBike;

	// Cura
	FTimerHandle HealApplyTimer;
	FTimerHandle HealEndTimer;
	bool bHealing = false;
	bool bHealApplied = false;
	EJRConsumable HealingItem = EJRConsumable::Bandage;
	double HealStartTime = 0.0;

	// Roda de itens
	bool bItemWheelOpen = false;
	int32 WheelHighlight = 0;
	FVector2D WheelCursor = FVector2D::ZeroVector;
	double WheelOpenRealTime = 0.0;
	float WheelSavedTimeDilation = 1.f;
	// [A-059] abas da roda
	int32 WheelTab = 0;
	int32 WheelTabDir = 1;
	double WheelTabChangeRealTime = -100.0;
	int32 WheelTabHighlight[2] = { 0, 1 };

	// [A-086] Escalar: pulo de frente para carro/contêiner/mureta (até ~2,6 m) sobe em cima com um movimento suave.
	void HandleJumpPressed();
	bool TryMantle();
	void TickMantle();
	FTimerHandle MantleTimer;
	FVector MantleFrom = FVector::ZeroVector;
	FVector MantleTo = FVector::ZeroVector;
	double MantleStart = 0.0;
	float MantleDuration = 0.4f;
	bool bMantling = false;
};

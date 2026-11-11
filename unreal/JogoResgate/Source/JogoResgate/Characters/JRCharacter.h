// Copyright utrazin. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Character.h"
#include "JRCharacter.generated.h"

class UAnimMontage;
class UCameraComponent;
class UInputAction;
class UJRHealthComponent;
class UJRInteractionComponent;
class UJRWeaponComponent;
class USpringArmComponent;
struct FInputActionValue;
struct FJRSkinDefinition;

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

	/** Abraço do resgate. Retorna a duração (0 se não houver montage). */
	UFUNCTION(BlueprintCallable, Category = "Character")
	float PlayRescueHug();

	void ApplySkin(const FJRSkinDefinition& Skin);

	UFUNCTION(BlueprintPure, Category = "Character")
	UJRHealthComponent* GetHealthComponent() const { return HealthComponent; }

	UFUNCTION(BlueprintPure, Category = "Character")
	UJRWeaponComponent* GetWeaponComponent() const { return WeaponComponent; }

	/** Restaura vida e estado para respawn em checkpoint. */
	void ResetForRespawn();

protected:
	virtual void BeginPlay() override;
	virtual void SetupPlayerInputComponent(UInputComponent* PlayerInputComponent) override;

	void HandleMove(const FInputActionValue& Value);
	void HandleLook(const FInputActionValue& Value);
	void HandleSprint(const FInputActionValue& Value);
	void HandleAim(const FInputActionValue& Value);
	void HandleFireStarted(const FInputActionValue& Value);
	void HandleFireStopped(const FInputActionValue& Value);
	void HandleReload(const FInputActionValue& Value);
	void HandleInteract(const FInputActionValue& Value);

	UFUNCTION()
	void HandleDeath(UJRHealthComponent* Health, AActor* Killer);

	UFUNCTION()
	void HandleMontageEnded(UAnimMontage* Montage, bool bInterrupted);

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

	UPROPERTY(EditDefaultsOnly, Category = "Input")
	TObjectPtr<UInputAction> MoveAction;

	UPROPERTY(EditDefaultsOnly, Category = "Input")
	TObjectPtr<UInputAction> LookAction;

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

	UPROPERTY(EditDefaultsOnly, Category = "Movement", meta = (Units = "cm/s"))
	float WalkSpeed = 350.f;

	UPROPERTY(EditDefaultsOnly, Category = "Movement", meta = (Units = "cm/s"))
	float SprintSpeed = 600.f;

	UPROPERTY(EditDefaultsOnly, Category = "Camera", meta = (Units = "cm"))
	float DefaultArmLength = 300.f;

	UPROPERTY(EditDefaultsOnly, Category = "Camera", meta = (Units = "cm"))
	float AimArmLength = 150.f;

	UPROPERTY(EditDefaultsOnly, Category = "Animation")
	TObjectPtr<UAnimMontage> ExitVehicleMontage;

	UPROPERTY(EditDefaultsOnly, Category = "Animation")
	TObjectPtr<UAnimMontage> RescueHugMontage;

	UPROPERTY(EditDefaultsOnly, Category = "Animation")
	TObjectPtr<UAnimMontage> DeathMontage;

	/** Atraso entre a morte e o reinício no checkpoint. */
	UPROPERTY(EditDefaultsOnly, Category = "Character", meta = (Units = "s"))
	float FailureDelay = 2.5f;

private:
	void NotifyFailure();

	FTimerHandle FailureTimer;
	bool bIsSprinting = false;
};

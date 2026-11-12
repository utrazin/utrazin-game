// Copyright utrazin. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"
#include "WheeledVehiclePawn.h"
#include "JRVehiclePawn.generated.h"

class UCameraComponent;
class UInputAction;
class UJRVehicleDamageComponent;
class USpringArmComponent;
class UStaticMeshComponent;
struct FInputActionValue;

/**
 * SUV jogável (A-008) sobre Chaos Vehicles. Tuning de rodas/motor fica no Blueprint
 * derivado (BP_Vehicle_SUV) e em docs/gameplay/VEHICLE.md.
 */
UCLASS()
class JOGORESGATE_API AJRVehiclePawn : public AWheeledVehiclePawn
{
	GENERATED_BODY()

public:
	AJRVehiclePawn();

	/** Zera inputs, freia e desativa o veículo após a saída do jogador (A-015). */
	UFUNCTION(BlueprintCallable, Category = "Vehicle")
	void ParkAndDisable();

	UFUNCTION(BlueprintPure, Category = "Vehicle")
	UJRVehicleDamageComponent* GetDamageComponent() const { return DamageComponent; }

	UFUNCTION(BlueprintPure, Category = "Vehicle")
	FTransform GetExitTransform() const;

	UFUNCTION(BlueprintPure, Category = "Vehicle")
	float GetSpeedKmh() const;

protected:
	virtual void BeginPlay() override;
	virtual void SetupPlayerInputComponent(UInputComponent* PlayerInputComponent) override;
	virtual void UnPossessed() override;

	void HandleThrottle(const FInputActionValue& Value);
	void HandleBrake(const FInputActionValue& Value);
	void HandleSteer(const FInputActionValue& Value);
	void HandleSteerReleased(const FInputActionValue& Value);
	void HandleHandbrake(const FInputActionValue& Value);
	void HandleLook(const FInputActionValue& Value);
	void ZeroInputs(bool bApplyHandbrake);

	UFUNCTION()
	void HandleVehicleDisabled();

	void SleepPhysics();

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Vehicle")
	TObjectPtr<USpringArmComponent> SpringArm;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Vehicle")
	TObjectPtr<UCameraComponent> Camera;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Vehicle")
	TObjectPtr<UJRVehicleDamageComponent> DamageComponent;

	/** Carroceria visual (estática), presa ao esqueleto da suspensão. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Vehicle|Visual")
	TObjectPtr<UStaticMeshComponent> ChassisMesh;

	/** Pneus visuais nos sockets VisWheel_* (FL, FR, BL, BR). */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Vehicle|Visual")
	TObjectPtr<UStaticMeshComponent> TireFL;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Vehicle|Visual")
	TObjectPtr<UStaticMeshComponent> TireFR;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Vehicle|Visual")
	TObjectPtr<UStaticMeshComponent> TireBL;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Vehicle|Visual")
	TObjectPtr<UStaticMeshComponent> TireBR;

	/** Onde o personagem aparece ao sair do carro (lado do motorista). */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Vehicle")
	TObjectPtr<USceneComponent> ExitPoint;

	UPROPERTY(EditDefaultsOnly, Category = "Input")
	TObjectPtr<UInputAction> ThrottleAction;

	UPROPERTY(EditDefaultsOnly, Category = "Input")
	TObjectPtr<UInputAction> BrakeAction;

	UPROPERTY(EditDefaultsOnly, Category = "Input")
	TObjectPtr<UInputAction> SteerAction;

	UPROPERTY(EditDefaultsOnly, Category = "Input")
	TObjectPtr<UInputAction> HandbrakeAction;

	UPROPERTY(EditDefaultsOnly, Category = "Input")
	TObjectPtr<UInputAction> LookAction;

	UPROPERTY(EditDefaultsOnly, Category = "Input")
	TObjectPtr<UInputAction> MouseLookAction;

	UPROPERTY(EditDefaultsOnly, Category = "Vehicle", meta = (Units = "s"))
	float SleepDelayAfterPark = 2.f;

private:
	bool bDriveEnabled = true;
	FTimerHandle SleepTimer;
};

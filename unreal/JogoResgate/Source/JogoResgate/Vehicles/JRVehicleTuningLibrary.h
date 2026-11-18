// Copyright utrazin. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "JRVehicleTuningLibrary.generated.h"

class UPhysicsAsset;

/**
 * Funções para scripts Python do Editor (tools/unreal/fix_vehicle_feel.py) mexerem no que o Python não alcança:
 * curvas FRuntimeFloatCurve (torque, volante, aderência lateral) e CCD por corpo do Physics Asset.
 * Curvas: cada chave é FVector2D(X = tempo/RPM/velocidade, Y = valor).
 */
UCLASS()
class JOGORESGATE_API UJRVehicleTuningLibrary : public UBlueprintFunctionLibrary
{
	GENERATED_BODY()

public:
	/** Curva de torque do motor (X = RPM, Y = torque relativo 0..1). Movement = UChaosWheeledVehicleMovementComponent. */
	UFUNCTION(BlueprintCallable, Category = "JR|Vehicle Tuning")
	static bool SetTorqueCurve(UObject* Movement, const TArray<FVector2D>& Keys);

	UFUNCTION(BlueprintCallable, Category = "JR|Vehicle Tuning")
	static TArray<FVector2D> GetTorqueCurve(UObject* Movement);

	/** Curva do volante (X = velocidade, Y = fração do ângulo máximo). */
	UFUNCTION(BlueprintCallable, Category = "JR|Vehicle Tuning")
	static bool SetSteeringCurve(UObject* Movement, const TArray<FVector2D>& Keys);

	UFUNCTION(BlueprintCallable, Category = "JR|Vehicle Tuning")
	static TArray<FVector2D> GetSteeringCurve(UObject* Movement);

	/** Curva de aderência lateral de uma roda (use o objeto padrão/CDO da classe da roda). */
	UFUNCTION(BlueprintCallable, Category = "JR|Vehicle Tuning")
	static bool SetLateralSlipGraph(UObject* Wheel, const TArray<FVector2D>& Keys);

	UFUNCTION(BlueprintCallable, Category = "JR|Vehicle Tuning")
	static TArray<FVector2D> GetLateralSlipGraph(UObject* Wheel);

	/** Liga/desliga CCD em todos os corpos do Physics Asset. Retorna quantos corpos mudou. */
	UFUNCTION(BlueprintCallable, Category = "JR|Vehicle Tuning")
	static int32 SetPhysicsAssetCCD(UPhysicsAsset* PhysicsAsset, bool bUseCCD);
};

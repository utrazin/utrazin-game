// Copyright utrazin. All Rights Reserved.

#include "Vehicles/JRVehicleTuningLibrary.h"
#include "ChaosVehicleWheel.h"
#include "ChaosWheeledVehicleMovementComponent.h"
#include "Curves/CurveFloat.h"
#include "Curves/RichCurve.h"
#include "PhysicsEngine/PhysicsAsset.h"
#include "PhysicsEngine/SkeletalBodySetup.h"

namespace JRVehicleTuning
{
	void WriteCurve(UObject* Owner, FRuntimeFloatCurve& Curve, const TArray<FVector2D>& Keys)
	{
		Owner->Modify();
		// Sem curva externa: as chaves passam a morar no próprio objeto.
		Curve.ExternalCurve = nullptr;
		FRichCurve* Rich = Curve.GetRichCurve();
		Rich->Reset();
		for (const FVector2D& Key : Keys)
		{
			const FKeyHandle Handle = Rich->AddKey(static_cast<float>(Key.X), static_cast<float>(Key.Y));
			Rich->SetKeyInterpMode(Handle, RCIM_Cubic);
		}
		Rich->AutoSetTangents();
		Owner->MarkPackageDirty();
	}

	TArray<FVector2D> ReadCurve(const FRuntimeFloatCurve& Curve)
	{
		TArray<FVector2D> Out;
		if (const FRichCurve* Rich = Curve.GetRichCurveConst())
		{
			for (const FRichCurveKey& Key : Rich->GetConstRefOfKeys())
			{
				Out.Emplace(Key.Time, Key.Value);
			}
		}
		return Out;
	}
}

bool UJRVehicleTuningLibrary::SetTorqueCurve(UObject* Movement, const TArray<FVector2D>& Keys)
{
	UChaosWheeledVehicleMovementComponent* Comp = Cast<UChaosWheeledVehicleMovementComponent>(Movement);
	if (!Comp || Keys.Num() == 0)
	{
		return false;
	}
	JRVehicleTuning::WriteCurve(Comp, Comp->EngineSetup.TorqueCurve, Keys);
	return true;
}

TArray<FVector2D> UJRVehicleTuningLibrary::GetTorqueCurve(UObject* Movement)
{
	const UChaosWheeledVehicleMovementComponent* Comp = Cast<UChaosWheeledVehicleMovementComponent>(Movement);
	return Comp ? JRVehicleTuning::ReadCurve(Comp->EngineSetup.TorqueCurve) : TArray<FVector2D>();
}

bool UJRVehicleTuningLibrary::SetSteeringCurve(UObject* Movement, const TArray<FVector2D>& Keys)
{
	UChaosWheeledVehicleMovementComponent* Comp = Cast<UChaosWheeledVehicleMovementComponent>(Movement);
	if (!Comp || Keys.Num() == 0)
	{
		return false;
	}
	JRVehicleTuning::WriteCurve(Comp, Comp->SteeringSetup.SteeringCurve, Keys);
	return true;
}

TArray<FVector2D> UJRVehicleTuningLibrary::GetSteeringCurve(UObject* Movement)
{
	const UChaosWheeledVehicleMovementComponent* Comp = Cast<UChaosWheeledVehicleMovementComponent>(Movement);
	return Comp ? JRVehicleTuning::ReadCurve(Comp->SteeringSetup.SteeringCurve) : TArray<FVector2D>();
}

bool UJRVehicleTuningLibrary::SetLateralSlipGraph(UObject* Wheel, const TArray<FVector2D>& Keys)
{
	UChaosVehicleWheel* WheelObj = Cast<UChaosVehicleWheel>(Wheel);
	if (!WheelObj || Keys.Num() == 0)
	{
		return false;
	}
	JRVehicleTuning::WriteCurve(WheelObj, WheelObj->LateralSlipGraph, Keys);
	return true;
}

TArray<FVector2D> UJRVehicleTuningLibrary::GetLateralSlipGraph(UObject* Wheel)
{
	const UChaosVehicleWheel* WheelObj = Cast<UChaosVehicleWheel>(Wheel);
	return WheelObj ? JRVehicleTuning::ReadCurve(WheelObj->LateralSlipGraph) : TArray<FVector2D>();
}

int32 UJRVehicleTuningLibrary::SetPhysicsAssetCCD(UPhysicsAsset* PhysicsAsset, bool bUseCCD)
{
	if (!PhysicsAsset)
	{
		return 0;
	}
	PhysicsAsset->Modify();
	int32 Changed = 0;
	for (USkeletalBodySetup* Body : PhysicsAsset->SkeletalBodySetups)
	{
		if (Body)
		{
			Body->Modify();
			Body->DefaultInstance.bUseCCD = bUseCCD;
			++Changed;
		}
	}
	PhysicsAsset->MarkPackageDirty();
	return Changed;
}

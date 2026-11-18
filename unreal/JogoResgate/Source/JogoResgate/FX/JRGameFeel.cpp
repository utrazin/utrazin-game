// Copyright utrazin. All Rights Reserved.

#include "FX/JRGameFeel.h"
#include "HAL/IConsoleManager.h"

namespace
{
	TAutoConsoleVariable<float> CVarJRFeelShakeScale(TEXT("jr.Feel.ShakeScale"), 1.f,
		TEXT("Intensidade do tremor de câmera, 0 a 1 (0 = sem tremor)."), ECVF_Default);
	TAutoConsoleVariable<float> CVarJRFeelMotionScale(TEXT("jr.Feel.MotionScale"), 1.f,
		TEXT("Movimentos extras da câmera (FOV de velocidade, aterrissagem, pulso), 0 a 1."), ECVF_Default);
	TAutoConsoleVariable<int32> CVarJRFeelReduceFlash(TEXT("jr.Feel.ReduceFlash"), 0,
		TEXT("1 = clarões de acerto mais fracos e curtos."), ECVF_Default);
	TAutoConsoleVariable<int32> CVarJRFeelHitStop(TEXT("jr.Feel.HitStop"), 1,
		TEXT("0 = desliga a congelada curtinha dos golpes."), ECVF_Default);
}

namespace JRFeel
{
	float ShakeScale()
	{
		return FMath::Clamp(CVarJRFeelShakeScale.GetValueOnGameThread(), 0.f, 1.f);
	}

	float MotionScale()
	{
		return FMath::Clamp(CVarJRFeelMotionScale.GetValueOnGameThread(), 0.f, 1.f);
	}

	bool ReduceFlash()
	{
		return CVarJRFeelReduceFlash.GetValueOnGameThread() != 0;
	}

	bool HitStopEnabled()
	{
		return CVarJRFeelHitStop.GetValueOnGameThread() != 0;
	}
}

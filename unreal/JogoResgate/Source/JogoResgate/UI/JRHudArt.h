// Copyright utrazin. All Rights Reserved.
// GERADO por tools/pipeline/make_hud_v2.py: não edite à mão (rode o script de novo).
// Números em pixels das imagens de referência (assets/raw/ui_refs). O HUD converte com a escala da tela.

#pragma once

#include "CoreMinimal.h"

namespace JRHudArt
{
	struct FRect { float X; float Y; float W; float H; };
	struct FPanel { float W; float H; };
	struct FBarSegments { int32 Num; FRect Seg[10]; };
	struct FPill { float TexW; float TexH; float CapL; float Mid; float CapR; };

	constexpr FPanel ObjHeroSize = { 454.0f, 247.0f };
	constexpr FRect ObjHeroTitle = { 114.0f, 18.0f, 230.0f, 48.0f };
	constexpr FRect ObjHeroBody = { 104.0f, 92.0f, 284.0f, 76.0f };
	constexpr FRect ObjHeroMarker = { 44.0f, 96.0f, 48.0f, 48.0f };

	constexpr FPanel ObjCarSize = { 487.0f, 228.0f };
	constexpr FRect ObjCarTitle = { 125.0f, 12.0f, 265.0f, 56.0f };
	constexpr FRect ObjCarBody = { 65.0f, 94.0f, 350.0f, 98.0f };
	constexpr FRect ObjCarMarker = { 23.0f, 150.0f, 46.0f, 46.0f };

	constexpr FPanel MapHeroSize = { 345.0f, 336.0f };
	constexpr FRect MapHeroTitle = { 114.0f, 10.0f, 186.0f, 54.0f };
	constexpr FRect MapHeroEllipse = { 168.8f, 186.5f, 115.0f, 115.0f }; // centro X, Y, raio X, raio Y

	constexpr FPanel MapCarSize = { 387.0f, 350.0f };
	constexpr FRect MapCarTitle = { 98.0f, 3.0f, 195.0f, 56.0f };
	constexpr FRect MapCarEllipse = { 199.0f, 189.0f, 173.0f, 129.0f }; // centro X, Y, raio X, raio Y

	constexpr FPanel BotHeroSize = { 655.0f, 258.0f };
	constexpr FRect BotHeroRing = { 97.1f, 140.5f, 66.0f, 0.f }; // centro X, Y, raio
	constexpr FRect BotHeroBarA = { 252.0f, 93.0f, 356.0f, 52.0f };
	constexpr FRect BotHeroBarALabel = { 256.0f, 61.0f, 98.0f, 38.0f };
	constexpr FRect BotHeroBarAValue = { 464.0f, 59.0f, 130.0f, 38.0f };
	constexpr FRect BotHeroBarAIcon = { 194.0f, 53.0f, 50.0f, 54.0f };
	constexpr FBarSegments BotHeroBarASegments = { 8, { { 260.0f, 104.0f, 40.0f, 28.0f }, { 304.0f, 108.0f, 39.0f, 26.0f }, { 347.0f, 106.0f, 40.0f, 29.0f }, { 389.0f, 102.0f, 41.0f, 30.0f }, { 432.0f, 99.0f, 41.0f, 29.0f }, { 477.0f, 98.0f, 39.0f, 27.0f }, { 519.0f, 99.0f, 39.0f, 28.0f }, { 559.0f, 105.0f, 38.0f, 32.0f } } };
	constexpr FRect BotHeroBarB = { 254.0f, 175.0f, 340.0f, 60.0f };
	constexpr FRect BotHeroBarBLabel = { 256.0f, 151.0f, 138.0f, 38.0f };
	constexpr FRect BotHeroBarBValue = { 434.0f, 137.0f, 150.0f, 38.0f };
	constexpr FRect BotHeroBarBIcon = { 194.0f, 140.0f, 50.0f, 55.0f };
	constexpr FBarSegments BotHeroBarBSegments = { 8, { { 260.0f, 197.0f, 40.0f, 28.0f }, { 303.0f, 199.0f, 40.0f, 27.0f }, { 347.0f, 197.0f, 37.0f, 29.0f }, { 388.0f, 190.0f, 37.0f, 31.0f }, { 429.0f, 184.0f, 35.0f, 31.0f }, { 468.0f, 181.0f, 36.0f, 28.0f }, { 507.0f, 181.0f, 37.0f, 25.0f }, { 545.0f, 182.0f, 37.0f, 29.0f } } };

	constexpr FPanel BotCarSize = { 701.0f, 302.0f };
	constexpr FRect BotCarRing = { 102.9f, 176.7f, 66.0f, 0.f };
	constexpr FRect BotCarSpeed = { 634.0f, 126.0f, 60.0f, 120.0f };
	constexpr FRect BotCarBarA = { 252.0f, 90.0f, 358.0f, 48.0f };
	constexpr FRect BotCarBarALabel = { 250.0f, 56.0f, 184.0f, 38.0f };
	constexpr FRect BotCarBarAValue = { 464.0f, 52.0f, 140.0f, 36.0f };
	constexpr float BotCarBarASpan[2] = { 254.0f, 604.0f }; // x inicial e final da barra
	constexpr FRect BotCarBarB = { 276.0f, 161.0f, 320.0f, 50.0f };
	constexpr FRect BotCarBarBLabel = { 277.0f, 138.0f, 137.0f, 36.0f };
	constexpr FRect BotCarBarBValue = { 454.0f, 128.0f, 140.0f, 36.0f };
	constexpr float BotCarBarBSpan[2] = { 279.0f, 589.0f }; // x inicial e final da barra
	constexpr FRect BotCarBarC = { 256.0f, 228.0f, 316.0f, 52.0f };
	constexpr FRect BotCarBarCLabel = { 270.0f, 216.0f, 104.0f, 38.0f };
	constexpr FRect BotCarBarCValue = { 424.0f, 206.0f, 140.0f, 36.0f };
	constexpr float BotCarBarCSpan[2] = { 264.0f, 563.0f }; // x inicial e final da barra

	constexpr FPanel WeaponSize = { 655.0f, 258.0f };
	constexpr FRect WeaponRing = { 557.9f, 140.5f, 66.0f, 0.f };
	constexpr FRect WeaponBody = { 61.0f, 53.0f, 350.0f, 177.0f };

	constexpr FPanel WheelSize = { 1254.0f, 1254.0f };
	constexpr float WheelCenter[2] = { 627.0f, 602.0f };
	constexpr float WheelDiscRadius = 236.0f;
	constexpr FRect WheelCellRect[8] = { { 418.0f, 59.0f, 418.0f, 302.0f }, { 720.0f, 101.0f, 422.0f, 411.0f }, { 870.0f, 394.0f, 339.0f, 412.0f }, { 725.0f, 690.0f, 433.0f, 426.0f }, { 390.0f, 846.0f, 464.0f, 334.0f }, { 97.0f, 690.0f, 422.0f, 431.0f }, { 46.0f, 394.0f, 339.0f, 412.0f }, { 113.0f, 108.0f, 418.0f, 404.0f } };
	constexpr FRect WheelCellCenter[8] = { { 626.0f, 198.9f, 0.f, 0.f }, { 920.9f, 316.9f, 0.f, 0.f }, { 1055.1f, 598.9f, 0.f, 0.f }, { 932.1f, 892.6f, 0.f, 0.f }, { 624.3f, 1024.2f, 0.f, 0.f }, { 310.2f, 897.5f, 0.f, 0.f }, { 198.9f, 598.9f, 0.f, 0.f }, { 328.8f, 316.1f, 0.f, 0.f } }; // X, Y do centro de massa

	constexpr FPill PillTeal = { 102.0f, 76.0f, 48.0f, 4.0f, 50.0f };
	constexpr FPill PillLavender = { 102.0f, 76.0f, 48.0f, 4.0f, 50.0f };
	constexpr FPill PillNavy = { 92.0f, 72.0f, 44.0f, 4.0f, 44.0f };
}

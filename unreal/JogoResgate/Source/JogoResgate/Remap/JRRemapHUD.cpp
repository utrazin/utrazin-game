// Copyright utrazin. All Rights Reserved.

#include "Remap/JRRemapHUD.h"
#include "AI/JREnemyCharacter.h"
#include "Audio/JRAudio.h"
#include "Characters/JRCharacter.h"
#include "Combat/JRWeaponComponent.h"
#include "Engine/Canvas.h"
#include "Engine/Texture2D.h"
#include "EngineUtils.h"
#include "GameFramework/PlayerController.h"
#include "HAL/PlatformTime.h"
#include "InputCoreTypes.h"
#include "Kismet/GameplayStatics.h"
#include "Remap/JRArenaDirector.h"
#include "Remap/JREconomySubsystem.h"
#include "Remap/JRExtractionShip.h"
#include "Remap/JRRemapTypes.h"
#include "Remap/JRRunSubsystem.h"
#include "Remap/JRShopkeeper.h"
#include "Gameplay/JRPickup.h"
#include "Gameplay/JRDistrictGate.h"
#include "Kismet/KismetSystemLibrary.h"
#include "UI/JRHudArt.h"

// ======================================================================
// [A-083] HUD do Remap no estilo v2. Ícones novos: assets/work/ui/remap/T_HUD2_R_*.png
// (assets/work/ui/remap/_make_remap_hud.py), importados em /Game/UI/HUD/V2 por tools/unreal/setup_remap_hud.py.
// Sem as texturas tudo continua aparecendo (painéis arredondados lisos, sem ícone).
// ======================================================================

namespace JRRHS
{
	// Paleta da HUD v2 (mesma do AJRHUD)
	const FLinearColor Ink = FLinearColor(FColor(12, 13, 32));
	const FLinearColor Navy = FLinearColor(FColor(24, 30, 62));
	const FLinearColor White = FLinearColor(FColor(250, 250, 255));
	const FLinearColor Soft = FLinearColor(FColor(196, 206, 236));
	const FLinearColor Cyan = FLinearColor(FColor(90, 240, 246));
	const FLinearColor Lilac = FLinearColor(FColor(186, 162, 240));
	const FLinearColor Purple = FLinearColor(FColor(186, 96, 255));
	const FLinearColor Gold = FLinearColor(FColor(255, 210, 80));
	const FLinearColor Red = FLinearColor(FColor(255, 96, 84));
	const FLinearColor Green = FLinearColor(FColor(120, 240, 150));
	const FLinearColor Locked = FLinearColor(FColor(150, 140, 180));

	FLinearColor Fade(FLinearColor In, float Alpha)
	{
		In.A *= Alpha;
		return In;
	}

	float Ease(float T)
	{
		const float V = FMath::Clamp(T, 0.f, 1.f);
		return 1.f - (1.f - V) * (1.f - V) * (1.f - V);
	}

	/** Passa um pouco do ponto e volta (entrada com "mola"). */
	float EaseBack(float T)
	{
		const float V = FMath::Clamp(T, 0.f, 1.f) - 1.f;
		const float C1 = 1.70158f;
		return 1.f + (C1 + 1.f) * V * V * V + C1 * V * V;
	}

	float Pulse(double Now, float Speed)
	{
		return 0.5f + 0.5f * FMath::Sin(static_cast<float>(Now) * Speed);
	}
}

// ====================================================================== início

void AJRRemapHUD::BeginPlay()
{
	Super::BeginPlay();
	RNow = FPlatformTime::Seconds();
	// Tarefa no painel OBJETIVO (no lugar do texto do L01).
	if (AJRArenaDirector::FindInWorld(this))
	{
		LastObjectiveLine = TEXT("Sobreviva às ondas. A nave de extração chega a cada 3 ondas");
		SetCurrentTask(LastObjectiveLine, nullptr, 0.f);
	}
	else
	{
		for (TActorIterator<AJRShopkeeper> It(GetWorld()); It; ++It)
		{
			if (It->GetShopType() == EJRShopType::Portao)
			{
				SetCurrentTask(TEXT("Fale com Kaar no portão para ir à arena"), *It, 300.f);
				break;
			}
		}
	}
	UJRRunSubsystem* Run = GetGameInstance() ? GetGameInstance()->GetSubsystem<UJRRunSubsystem>() : nullptr;
	const UJREconomySubsystem* Economy = GetGameInstance() ? GetGameInstance()->GetSubsystem<UJREconomySubsystem>() : nullptr;
	if (Run && Run->HasReport() && !AJRArenaDirector::FindInWorld(this))
	{
		bReportOpen = true;
		ReportOpenedAt = RNow;
		ReportRowsShown = 0;
		if (Economy)
		{
			// A carteira começa sem o que a corrida rendeu e sobe junto com a última linha do relatório.
			bWalletHeld = true;
			WalletHeldValue = FMath::Max<int64>(0, Economy->GetCredits() - Run->GetReport().CreditsKept);
			TweenSnap(TEXT("Wallet"), WalletHeldValue);
		}
	}
}

// ====================================================================== peças do estilo

void AJRRemapHUD::NineSlice(UTexture2D* Tex, float X, float Y, float W, float H, float Corner, const FLinearColor& Tint)
{
	if (!Tex || W <= 1.f || H <= 1.f)
	{
		return;
	}
	const float Cn = FMath::Min3(Corner, W * 0.5f, H * 0.5f);
	const float UC = 80.f / 256.f;
	const float Xs[4] = { X, X + Cn, X + W - Cn, X + W };
	const float Ys[4] = { Y, Y + Cn, Y + H - Cn, Y + H };
	const float Us[4] = { 0.f, UC, 1.f - UC, 1.f };
	for (int32 Row = 0; Row < 3; ++Row)
	{
		for (int32 Col = 0; Col < 3; ++Col)
		{
			DrawTex(Tex, Xs[Col], Ys[Row], Xs[Col + 1] - Xs[Col], Ys[Row + 1] - Ys[Row], Tint,
				FVector2D(Us[Col], Us[Row]), FVector2D(Us[Col + 1], Us[Row + 1]));
		}
	}
}

void AJRRemapHUD::PanelBox(float X, float Y, float W, float H, const FLinearColor& RimTint, float Alpha, float GlowAlpha,
	const FLinearColor& GlowTint)
{
	if (Alpha <= 0.01f)
	{
		return;
	}
	const float Corner = FMath::Min(44.f * RU, FMath::Min(W, H) * 0.5f);
	if (GlowAlpha > 0.01f)
	{
		const float G = 28.f * RU; // a textura R_PanelGlow tem o brilho a ~31 px (de 256) da borda
		if (UTexture2D* GlowTex = HudTex(TEXT("R_PanelGlow")))
		{
			NineSlice(GlowTex, X - G, Y - G, W + 2.f * G, H + 2.f * G, Corner + G, JRRHS::Fade(GlowTint, GlowAlpha * Alpha));
		}
		else
		{
			DrawRounded(X - G * 0.5f, Y - G * 0.5f, W + G, H + G, Corner, JRRHS::Fade(GlowTint, 0.35f * GlowAlpha * Alpha));
		}
	}
	UTexture2D* FillTex = HudTex(TEXT("R_PanelFill"));
	UTexture2D* RimTex = HudTex(TEXT("R_PanelRim"));
	if (FillTex && RimTex)
	{
		NineSlice(FillTex, X, Y, W, H, Corner, JRRHS::Fade(FLinearColor::White, Alpha));
		NineSlice(RimTex, X, Y, W, H, Corner, JRRHS::Fade(RimTint, Alpha));
	}
	else
	{
		DrawRounded(X - 3.f * RU, Y - 3.f * RU, W + 6.f * RU, H + 6.f * RU, Corner, JRRHS::Fade(JRRHS::Ink, 0.95f * Alpha));
		DrawRounded(X, Y, W, H, Corner, JRRHS::Fade(RimTint, Alpha));
		DrawRounded(X + 7.f * RU, Y + 7.f * RU, W - 14.f * RU, H - 14.f * RU, Corner * 0.8f, JRRHS::Fade(JRRHS::Navy, 0.97f * Alpha));
	}
	// luzinhas ciano no aro de baixo (como nos painéis do herói)
	if (UTexture2D* LightTex = HudTex(TEXT("R_Light")))
	{
		const float LW = 22.f * RU;
		const float LH = 12.f * RU;
		for (int32 Dot = 0; Dot < 3; ++Dot)
		{
			const float LX = X + W - Corner * 0.6f - (LW + 4.f * RU) * static_cast<float>(3 - Dot);
			DrawTex(LightTex, LX, Y + H - LH * 0.75f, LW, LH, JRRHS::Fade(FLinearColor::White, Alpha));
		}
	}
}

void AJRRemapHUD::DrawNine(UTexture2D* Tex, float X, float Y, float W, float H, float CapU, float CapV, float CapX, float CapY,
	const FLinearColor& Color)
{
	if (!Tex || W <= 1.f || H <= 1.f)
	{
		return;
	}
	CapX = FMath::Min(CapX, W * 0.5f);
	CapY = FMath::Min(CapY, H * 0.5f);
	const float Xs[4] = { X, X + CapX, X + W - CapX, X + W };
	const float Ys[4] = { Y, Y + CapY, Y + H - CapY, Y + H };
	const float Us[4] = { 0.f, CapU, 1.f - CapU, 1.f };
	const float Vs[4] = { 0.f, CapV, 1.f - CapV, 1.f };
	for (int32 Row = 0; Row < 3; ++Row)
	{
		for (int32 Col = 0; Col < 3; ++Col)
		{
			DrawTex(Tex, Xs[Col], Ys[Row], Xs[Col + 1] - Xs[Col], Ys[Row + 1] - Ys[Row], Color,
				FVector2D(Us[Col], Vs[Row]), FVector2D(Us[Col + 1], Vs[Row + 1]));
		}
	}
}

void AJRRemapHUD::IconAt(const FString& Name, float CX, float CY, float SizePx, float Alpha, float AngleDeg)
{
	if (Name.IsEmpty())
	{
		return;
	}
	UTexture2D* Tex = HudTex(Name);
	if (!Tex)
	{
		// sem a textura: bolinha lilás no lugar (o layout não quebra)
		const float Dot = SizePx * 0.5f;
		DrawRounded(CX - Dot * 0.5f, CY - Dot * 0.5f, Dot, Dot, Dot * 0.5f, JRRHS::Fade(JRRHS::Lilac, 0.8f * Alpha));
		return;
	}
	if (FMath::Abs(AngleDeg) > 0.1f)
	{
		DrawRotatedTex(Tex, FVector2D(CX, CY), SizePx, AngleDeg, JRRHS::Fade(FLinearColor::White, Alpha));
	}
	else
	{
		DrawTex(Tex, CX - SizePx * 0.5f, CY - SizePx * 0.5f, SizePx, SizePx, JRRHS::Fade(FLinearColor::White, Alpha));
	}
}

void AJRRemapHUD::IconBadge(const FString& Name, float CX, float CY, float SizePx, float Alpha, const FLinearColor& RingTint)
{
	if (UTexture2D* BadgeTex = HudTex(TEXT("Badge")))
	{
		DrawTex(BadgeTex, CX - SizePx * 0.5f, CY - SizePx * 0.5f, SizePx, SizePx, JRRHS::Fade(RingTint, Alpha));
	}
	else
	{
		DrawRounded(CX - SizePx * 0.5f, CY - SizePx * 0.5f, SizePx, SizePx, SizePx * 0.5f, JRRHS::Fade(JRRHS::Navy, Alpha));
	}
	IconAt(Name, CX, CY, SizePx * 0.66f, Alpha);
}

float AJRRemapHUD::TextMid(const FString& Str, float X, float CY, float Px, const FLinearColor& Color, int32 Align, bool bBold)
{
	if (Str.IsEmpty())
	{
		return 0.f;
	}
	const float LineH = MeasureText(Str, bBold, Px).Y;
	return DrawHudText(Str, X, CY - LineH * 0.5f, Px, Color, Align, bBold);
}

void AJRRemapHUD::BarAt(float X, float Y, float W, float H, float Frac, const FLinearColor& FillColor, float Alpha, float Flash)
{
	const float Edge = 2.5f * RU;
	DrawRounded(X - Edge, Y - Edge, W + 2.f * Edge, H + 2.f * Edge, (H + 2.f * Edge) * 0.5f, JRRHS::Fade(JRRHS::Ink, 0.95f * Alpha));
	DrawRounded(X, Y, W, H, H * 0.5f, JRRHS::Fade(JRRHS::Navy, Alpha));
	const float Clamped = FMath::Clamp(Frac, 0.f, 1.f);
	if (Clamped <= 0.001f)
	{
		return;
	}
	const float FillW = FMath::Max(H, W * Clamped);
	FLinearColor Fill = FMath::Lerp(FillColor, FLinearColor::White, FMath::Clamp(Flash, 0.f, 1.f) * 0.7f);
	Fill.A = Alpha;
	DrawRounded(X, Y, FillW, H, H * 0.5f, Fill);
	// brilho de vidro em cima
	DrawRounded(X + H * 0.35f, Y + H * 0.14f, FMath::Max(0.f, FillW - H * 0.7f), H * 0.3f, H * 0.15f,
		FLinearColor(1.f, 1.f, 1.f, 0.28f * Alpha));
}

float AJRRemapHUD::IconPill(const FString& PillTex, const FString& Icon, const FString& Str, float CX, float Y, float PillH, float Px,
	const FLinearColor& LabelColor, float Alpha, float Scale)
{
	const float Hs = PillH * Scale;
	const float Pxs = Px * Scale;
	const float IconSize = Icon.IsEmpty() ? 0.f : Hs * 0.82f;
	const float Gap = Icon.IsEmpty() ? 0.f : 8.f * RU * Scale;
	const float TextW = MeasureText(Str, true, Pxs).X;
	const float ContentW = IconSize + Gap + TextW;
	const float PillW = PillWidthFor(PillTex, Hs, ContentW);
	const float PY = Y + (PillH - Hs) * 0.5f;
	DrawPill(PillTex, CX - PillW * 0.5f, PY, PillW, Hs, JRRHS::Fade(FLinearColor::White, Alpha));
	const float StartX = CX - ContentW * 0.5f;
	if (!Icon.IsEmpty())
	{
		IconAt(Icon, StartX + IconSize * 0.5f, PY + Hs * 0.46f, IconSize, Alpha);
	}
	TextMid(Str, StartX + IconSize + Gap, PY + Hs * 0.46f, Pxs, JRRHS::Fade(LabelColor, Alpha), 0, true);
	return PillW;
}

// ====================================================================== efeitos

int64 AJRRemapHUD::TweenNumber(FName Key, int64 Target, float Speed)
{
	double* Shown = TweenShown.Find(Key);
	if (!Shown)
	{
		TweenShown.Add(Key, static_cast<double>(Target));
		TweenGoal.Add(Key, Target);
		return Target;
	}
	int64& Goal = TweenGoal.FindOrAdd(Key);
	if (Goal != Target)
	{
		Goal = Target;
		TweenPopAt.Add(Key, RNow);
	}
	const double Diff = static_cast<double>(Target) - *Shown;
	if (FMath::Abs(Diff) < 0.5)
	{
		*Shown = static_cast<double>(Target);
	}
	else
	{
		// exponencial (números grandes correm) com passo mínimo (números pequenos terminam)
		double StepSize = Diff * FMath::Min(1.0, static_cast<double>(RDelta * Speed));
		const double MinStep = FMath::Min(FMath::Abs(Diff), static_cast<double>(RDelta) * 40.0);
		if (FMath::Abs(StepSize) < MinStep)
		{
			StepSize = Diff > 0.0 ? MinStep : -MinStep;
		}
		*Shown += StepSize;
	}
	return FMath::FloorToInt64(*Shown + 0.5);
}

void AJRRemapHUD::TweenSnap(FName Key, int64 Value)
{
	TweenShown.Add(Key, static_cast<double>(Value));
	TweenGoal.Add(Key, Value);
}

float AJRRemapHUD::PopOf(FName Key, float Dur) const
{
	const double* At = TweenPopAt.Find(Key);
	if (!At || Dur <= 0.f)
	{
		return 0.f;
	}
	const float Age = static_cast<float>(RNow - *At) / Dur;
	return Age < 1.f ? 1.f - Age : 0.f;
}

void AJRRemapHUD::SpawnFloater(const FString& Label, const FString& Icon, const FLinearColor& Tint, const FVector2D& ScreenPos, float SizePx, float Life)
{
	FFloater& New = Floaters.AddDefaulted_GetRef();
	New.Label = Label;
	New.Icon = Icon;
	New.Tint = Tint;
	New.ScreenPos = ScreenPos;
	New.bInWorld = false;
	New.Born = RNow;
	New.Life = Life;
	New.SizePx = SizePx;
	if (Floaters.Num() > 24)
	{
		Floaters.RemoveAt(0);
	}
}

void AJRRemapHUD::SpawnWorldFloater(const FString& Label, const FString& Icon, const FLinearColor& Tint, const FVector& WorldPos, float SizePx)
{
	FFloater& New = Floaters.AddDefaulted_GetRef();
	New.Label = Label;
	New.Icon = Icon;
	New.Tint = Tint;
	New.WorldPos = WorldPos;
	New.bInWorld = true;
	New.Born = RNow;
	New.Life = 1.15f;
	New.SizePx = SizePx;
	if (Floaters.Num() > 24)
	{
		Floaters.RemoveAt(0);
	}
}

void AJRRemapHUD::SpawnCoins(const FVector2D& From, const FVector2D& To, int32 Count)
{
	for (int32 Coin = 0; Coin < Count; ++Coin)
	{
		FFlyCoin& New = FlyCoins.AddDefaulted_GetRef();
		New.From = From + FVector2D(FMath::FRandRange(-18.f, 18.f), FMath::FRandRange(-12.f, 12.f)) * RU;
		New.To = To;
		New.Born = RNow + 0.07 * Coin;
		New.Dur = 0.55f + 0.05f * static_cast<float>(Coin);
	}
	if (FlyCoins.Num() > 30)
	{
		FlyCoins.RemoveAt(0, FlyCoins.Num() - 30);
	}
}

void AJRRemapHUD::ShowBanner(const FString& Title, const FString& Sub, const FString& Icon, float Duration)
{
	BannerTitle = Title;
	BannerSub = Sub;
	BannerIcon = Icon;
	BannerAt = RNow;
	BannerDur = Duration;
}

void AJRRemapHUD::DrawFloaters()
{
	// textos subindo
	for (int32 Index = Floaters.Num() - 1; Index >= 0; --Index)
	{
		const FFloater& Fl = Floaters[Index];
		const float Age = Since(Fl.Born);
		if (Age > Fl.Life)
		{
			Floaters.RemoveAt(Index);
			continue;
		}
		FVector2D Pos = Fl.ScreenPos;
		if (Fl.bInWorld)
		{
			const FVector Projected = Project(Fl.WorldPos, false);
			if (Projected.Z <= 0.f)
			{
				continue;
			}
			Pos = FVector2D(Projected.X, Projected.Y);
		}
		const float T = Age / Fl.Life;
		const float Rise = JRRHS::Ease(T) * 70.f * RU;
		const float Grow = Age < 0.18f ? JRRHS::EaseBack(Age / 0.18f) : 1.f;
		const float Alpha = T < 0.65f ? 1.f : FMath::Max(0.f, 1.f - (T - 0.65f) / 0.35f);
		const float Px = Fl.SizePx * RU * (0.6f + 0.4f * Grow);
		const float IconSize = Fl.Icon.IsEmpty() ? 0.f : Px * 1.25f;
		const float TextW = MeasureText(Fl.Label, true, Px).X;
		const float TotalW = IconSize + (IconSize > 0.f ? 6.f * RU : 0.f) + TextW;
		const float LeftX = Pos.X - TotalW * 0.5f;
		const float MidY = Pos.Y - Rise;
		if (!Fl.Icon.IsEmpty())
		{
			IconAt(Fl.Icon, LeftX + IconSize * 0.5f, MidY, IconSize, Alpha, 8.f * FMath::Sin(Age * 12.f));
		}
		TextMid(Fl.Label, LeftX + IconSize + (IconSize > 0.f ? 6.f * RU : 0.f), MidY, Px, JRRHS::Fade(Fl.Tint, Alpha));
	}
	// moedas voando até o painel (curva para cima, giro e encolhe na chegada)
	for (int32 Index = FlyCoins.Num() - 1; Index >= 0; --Index)
	{
		const FFlyCoin& Fc = FlyCoins[Index];
		const float Age = Since(Fc.Born);
		if (Age < 0.f)
		{
			continue;
		}
		if (Age > Fc.Dur)
		{
			FlyCoins.RemoveAt(Index);
			continue;
		}
		const float T = Age / Fc.Dur;
		const float Tin = T * T; // acelera até o painel
		const FVector2D Mid = (Fc.From + Fc.To) * 0.5f + FVector2D(0.f, -120.f * RU);
		const float WA = (1.f - Tin) * (1.f - Tin);
		const float WB = 2.f * (1.f - Tin) * Tin;
		const float WC = Tin * Tin;
		const FVector2D Pos = Fc.From * WA + Mid * WB + Fc.To * WC;
		const float CoinSize = 30.f * RU * (T < 0.15f ? JRRHS::EaseBack(T / 0.15f) : (1.f - 0.4f * T));
		IconAt(TEXT("R_Coin"), Pos.X, Pos.Y, CoinSize, 1.f, 360.f * T);
	}
}

void AJRRemapHUD::DrawCenterBanner()
{
	const float Age = Since(BannerAt);
	if (BannerTitle.IsEmpty() || Age > BannerDur || Age < 0.f)
	{
		return;
	}
	const float In = JRRHS::EaseBack(Age / 0.3f);
	const float Alpha = Age > BannerDur - 0.35f ? FMath::Max(0.f, (BannerDur - Age) / 0.35f) : FMath::Min(1.f, Age / 0.12f);
	const float CX = Canvas->ClipX * 0.5f;
	const float Y = Canvas->ClipY * 0.27f;
	// [A-087] faixa pintada: azul nas ondas comuns, vermelha com garras a cada 5 (horda) e na nave
	const bool bHorde = BannerIcon == TEXT("R_Wave") && SeenWave > 0 && SeenWave % 5 == 0;
	if (UTexture2D* Band = HudTex(bHorde ? TEXT("V3_BannerHorde") : TEXT("V3_BannerWave")))
	{
		// entra da esquerda com passada do ponto e tranco
		const float Slide = (1.f - FMath::Min(1.f, JRRHS::EaseBack(Age / 0.28f))) * -Canvas->ClipX * 0.6f;
		const float Shake = Age < 0.35f ? FMath::Sin(Age * 90.f) * (0.35f - Age) * 30.f * RU : 0.f;
		const float BW = 860.f * RU;
		const float BH = BW * static_cast<float>(Band->GetSizeY()) / static_cast<float>(FMath::Max(1, Band->GetSizeX()));
		const float BX = CX - BW * 0.5f + Slide + Shake;
		const float BY = Y - BH * 0.35f;
		DrawTex(Band, BX, BY, BW, BH, JRRHS::Fade(FLinearColor::White, Alpha));
		// texto à direita da caveira (a caveira ocupa ~22% da esquerda)
		const float TextCX = BX + BW * 0.58f;
		TextMid(BannerTitle, TextCX, BY + BH * (BannerSub.IsEmpty() ? 0.5f : 0.42f), 64.f * RU, JRRHS::Fade(FLinearColor::White, Alpha), 1, true);
		if (!BannerSub.IsEmpty())
		{
			TextMid(BannerSub, TextCX, BY + BH * 0.66f, 26.f * RU, JRRHS::Fade(bHorde ? FLinearColor(1.f, 0.75f, 0.75f) : JRRHS::Gold, Alpha), 1, false);
		}
		return;
	}
	if (UTexture2D* GlowTex = HudTex(TEXT("Glow")))
	{
		const float G = 340.f * RU * In;
		DrawTex(GlowTex, CX - G, Y + 50.f * RU - G * 0.45f, 2.f * G, G * 0.9f, JRRHS::Fade(JRRHS::Cyan, 0.35f * Alpha), FVector2D(0.f, 0.f),
			FVector2D(1.f, 1.f), true);
	}
	IconPill(TEXT("PillTeal"), BannerIcon, BannerTitle, CX, Y, 96.f * RU, 56.f * RU, JRRHS::White, Alpha, FMath::Max(0.2f, In));
	if (!BannerSub.IsEmpty())
	{
		IconPill(TEXT("PillNavy"), FString(), BannerSub, CX, Y + 104.f * RU, 50.f * RU, 26.f * RU, JRRHS::Gold, Alpha);
	}
}

void AJRRemapHUD::PlayUi(const TCHAR* SoundId, float Volume, float Pitch)
{
	UJRAudio::Play2D(this, FName(SoundId), Volume, Pitch);
}

// ====================================================================== textos e ícones

FString AJRRemapHUD::Fmt(int64 Value)
{
	FString Digits = FString::Printf(TEXT("%lld"), FMath::Abs(Value));
	FString Out;
	for (int32 Index = 0; Index < Digits.Len(); ++Index)
	{
		if (Index > 0 && (Digits.Len() - Index) % 3 == 0)
		{
			Out.AppendChar(TEXT('.'));
		}
		Out.AppendChar(Digits[Index]);
	}
	return Value < 0 ? TEXT("-") + Out : Out;
}

FString AJRRemapHUD::CardIcon(EJRRunCard Card)
{
	// [A-087] ícones pintados pelo usuário (T_HUD2_V3_Card_*, já com o aro redondo)
	switch (Card)
	{
	case EJRRunCard::Damage: return TEXT("V3_Card_Damage");
	case EJRRunCard::FireRate: return TEXT("V3_Card_FireRate");
	case EJRRunCard::MoveSpeed: return TEXT("V3_Card_MoveSpeed");
	case EJRRunCard::MaxHealth: return TEXT("V3_Card_MaxHealth");
	case EJRRunCard::LifeOnKill: return TEXT("V3_Card_LifeOnKill");
	case EJRRunCard::Credits: return TEXT("V3_Card_Credits");
	case EJRRunCard::HealNow: return TEXT("V3_Card_HealNow");
	case EJRRunCard::Energy: return TEXT("V3_Card_Energy");
	case EJRRunCard::Armor: return TEXT("V3_Card_Armor");
	default: return TEXT("R_Star");
	}
}

FString AJRRemapHUD::ShopIconFor(const AJRShopkeeper* Keeper)
{
	if (!Keeper)
	{
		return FString();
	}
	switch (Keeper->GetShopType())
	{
	case EJRShopType::Armeiro: return TEXT("Icon_Shotgun");
	case EJRShopType::Bancada: return TEXT("R_Bench");
	case EJRShopType::Portao: return TEXT("R_Portal");
	case EJRShopType::Arvore: return TEXT("R_Tree"); // [A-098] ícone pedido ao usuário (sem ele: bolinha lilás)
	default: return FString();
	}
}

FLinearColor AJRRemapHUD::RarityColor(int32 Rarity)
{
	switch (FMath::Clamp(Rarity, 0, 2))
	{
	case 1: return FLinearColor(FColor(90, 180, 255));   // rara: azul
	case 2: return FLinearColor(FColor(205, 110, 255));  // épica: roxo
	default: return FLinearColor(FColor(200, 210, 230)); // comum: pedra clara
	}
}

// ====================================================================== entrada

bool AJRRemapHUD::Pressed(const FKey& Key) const
{
	return PlayerOwner && PlayerOwner->WasInputKeyJustPressed(Key);
}

bool AJRRemapHUD::PressedClose() const
{
	return Pressed(EKeys::Q) || Pressed(EKeys::BackSpace) || Pressed(EKeys::Tab) || Pressed(EKeys::Gamepad_FaceButton_Right)
		|| ((FPlatformTime::Seconds() - ShopOpenedAt) > 0.3 && Pressed(EKeys::E));
}

int32 AJRRemapHUD::PollChoice(int32 NumOptions, int32& InOutSelected)
{
	if (NumOptions <= 0)
	{
		return INDEX_NONE;
	}
	static const FKey Digits[] = { EKeys::One, EKeys::Two, EKeys::Three, EKeys::Four, EKeys::Five };
	static const FKey Pad[] = { EKeys::NumPadOne, EKeys::NumPadTwo, EKeys::NumPadThree, EKeys::NumPadFour, EKeys::NumPadFive };
	for (int32 Index = 0; Index < FMath::Min(NumOptions, 5); ++Index)
	{
		if (Pressed(Digits[Index]) || Pressed(Pad[Index]))
		{
			InOutSelected = Index;
			return Index;
		}
	}
	const int32 Before = InOutSelected;
	if (Pressed(EKeys::Up) || Pressed(EKeys::Left) || Pressed(EKeys::Gamepad_DPad_Up) || Pressed(EKeys::Gamepad_DPad_Left))
	{
		InOutSelected = (InOutSelected + NumOptions - 1) % NumOptions;
	}
	if (Pressed(EKeys::Down) || Pressed(EKeys::Right) || Pressed(EKeys::Gamepad_DPad_Down) || Pressed(EKeys::Gamepad_DPad_Right))
	{
		InOutSelected = (InOutSelected + 1) % NumOptions;
	}
	InOutSelected = FMath::Clamp(InOutSelected, 0, NumOptions - 1);
	if (InOutSelected != Before)
	{
		PlayUi(TEXT("UI.Wheel.Hover"));
		CardMovedAt = RNow;
	}
	if (Pressed(EKeys::Enter) || Pressed(EKeys::SpaceBar) || Pressed(EKeys::Gamepad_FaceButton_Bottom))
	{
		return InOutSelected;
	}
	return INDEX_NONE;
}

void AJRRemapHUD::SetPawnInput(bool bEnable)
{
	APawn* Pawn = PlayerOwner ? PlayerOwner->GetPawn() : nullptr;
	if (!Pawn)
	{
		return;
	}
	if (bEnable)
	{
		Pawn->EnableInput(PlayerOwner);
	}
	else
	{
		if (AJRCharacter* Hero = Cast<AJRCharacter>(Pawn))
		{
			if (UJRWeaponComponent* Weapon = Hero->GetWeaponComponent())
			{
				Weapon->StopFire();
			}
		}
		Pawn->DisableInput(PlayerOwner);
	}
}

bool AJRRemapHUD::IsHudModalOpen() const
{
	if (bReportOpen || ShopKeeper.IsValid())
	{
		return true;
	}
	const UGameInstance* GI = GetGameInstance();
	const UJRRunSubsystem* Run = GI ? GI->GetSubsystem<UJRRunSubsystem>() : nullptr;
	return Run && Run->IsChoosingCard();
}

void AJRRemapHUD::CollectRadarBlips(TArray<FJRHudBlip>& OutBlips) const
{
	if (const AJRArenaDirector* Director = AJRArenaDirector::FindInWorld(this))
	{
		if (const AJRExtractionShip* Ship = Director->GetActiveShip())
		{
			FJRHudBlip& Blip = OutBlips.AddDefaulted_GetRef();
			Blip.World = Ship->GetActorLocation();
			Blip.Icon = TEXT("R_Ship");
			Blip.Tint = JRRHS::Cyan;
		}
		return;
	}
	// Cidade: um pino por vendedor, com o ícone da função (REMAP 9.3: "minimapa com o ícone de cada prédio").
	for (TActorIterator<AJRShopkeeper> It(GetWorld()); It; ++It)
	{
		FJRHudBlip& Blip = OutBlips.AddDefaulted_GetRef();
		Blip.World = It->GetActorLocation();
		Blip.Icon = ShopIconFor(*It);
		Blip.Tint = It->GetShopType() == EJRShopType::Portao ? JRRHS::Gold : JRRHS::Lilac;
	}
}

FString AJRRemapHUD::MarkerIconFor(const AActor* Target) const
{
	if (const AJRShopkeeper* Keeper = Cast<AJRShopkeeper>(Target))
	{
		return ShopIconFor(Keeper);
	}
	if (Target && Target->IsA<AJRExtractionShip>())
	{
		return TEXT("R_Ship");
	}
	return Super::MarkerIconFor(Target);
}

// ====================================================================== loja

void AJRRemapHUD::OpenShop(AJRShopkeeper* Shopkeeper)
{
	if (!Shopkeeper || bReportOpen)
	{
		return;
	}
	ShopKeeper = Shopkeeper;
	ShopSelected = 0;
	ShopFlashRow = -1;
	ShopDenyRow = -1;
	ShopLine = Shopkeeper->PickGreeting();
	if (ShopLine.IsEmpty())
	{
		switch (Shopkeeper->GetShopType())
		{
		case EJRShopType::Armeiro: ShopLine = TEXT("Armas boas, preço justo. Olhe à vontade."); break;
		case EJRShopType::Bancada: ShopLine = TEXT("Traga créditos e eu deixo suas armas mais fortes."); break;
		case EJRShopType::Portao: ShopLine = TEXT("Pronto para sair? Escolha a arena."); break;
		case EJRShopType::Arvore: ShopLine = TEXT("A Árvore-Mãe pulsa. Traga cristais da arena e ela cresce com você."); break;
		}
	}
	if (Shopkeeper->GetShopType() == EJRShopType::Arvore) // [A-098] sempre mostra o saldo de cristais
	{
		if (const UJREconomySubsystem* Eco = GetGameInstance() ? GetGameInstance()->GetSubsystem<UJREconomySubsystem>() : nullptr)
		{
			ShopLine += FString::Printf(TEXT(" (Você tem %lld cristais.)"), Eco->GetCrystals());
		}
	}
	RNow = FPlatformTime::Seconds();
	ShopLineAt = RNow;
	ShopOpenedAt = RNow;
	PlayUi(TEXT("UI.Wheel.Open"));
	SetPawnInput(false);
}

void AJRRemapHUD::CloseShop()
{
	if (ShopKeeper.IsValid())
	{
		ShopKeeper.Reset();
		SetPawnInput(true);
		PlayUi(TEXT("UI.Wheel.Close"));
	}
}

void AJRRemapHUD::BuildShopEntries(TArray<FShopEntry>& Out) const
{
	const AJRShopkeeper* Keeper = ShopKeeper.Get();
	UGameInstance* GI = GetGameInstance();
	UJREconomySubsystem* Economy = GI ? GI->GetSubsystem<UJREconomySubsystem>() : nullptr;
	UJRRunSubsystem* Run = GI ? GI->GetSubsystem<UJRRunSubsystem>() : nullptr;
	if (!Keeper || !Economy)
	{
		return;
	}
	APlayerController* PC = PlayerOwner;
	switch (Keeper->GetShopType())
	{
	case EJRShopType::Armeiro:
	{
		struct FW { EJRWeaponSlot Slot; const TCHAR* Name; const TCHAR* Detail; const TCHAR* Icon; };
		const FW Weapons[] = {
			{ EJRWeaponSlot::Shotgun, TEXT("Escopeta alienígena"), TEXT("Estrago de perto. A melhor para segurar ondas."), TEXT("Icon_Shotgun") },
			{ EJRWeaponSlot::Sniper, TEXT("Rifle de precisão"), TEXT("Um tiro, um zumbi. Lento, para elites."), TEXT("Icon_Sniper") },
		};
		for (const FW& Weapon : Weapons)
		{
			FShopEntry Entry;
			Entry.Label = Weapon.Name;
			Entry.Detail = Weapon.Detail;
			Entry.Icon = Weapon.Icon;
			Entry.Price = FJRRemapRules::WeaponPrice(Weapon.Slot);
			Entry.bOwned = Economy->OwnsWeapon(Weapon.Slot);
			Entry.bAvailable = !Entry.bOwned;
			const EJRWeaponSlot Slot = Weapon.Slot;
			Entry.Buy = [Economy, PC, Slot]()
			{
				if (!Economy->BuyWeapon(Slot))
				{
					return false;
				}
				if (AJRCharacter* Hero = PC ? Cast<AJRCharacter>(PC->GetPawn()) : nullptr)
				{
					Hero->GrantWeapon(Slot, true);
				}
				return true;
			};
			Out.Add(MoveTemp(Entry));
		}
		break;
	}
	case EJRShopType::Bancada:
	{
		const int32 Bench = Economy->GetBenchLevel();
		FShopEntry Entry;
		Entry.Label = FString::Printf(TEXT("Calibrar armas: nível %d -> %d"), Bench, Bench + 1);
		Entry.Detail = FString::Printf(TEXT("Dano de todas as armas: +%d%% -> +%d%%"), Bench * 10, (Bench + 1) * 10);
		Entry.Icon = TEXT("R_Bench");
		Entry.Price = Economy->GetNextBenchCost();
		Entry.Buy = [Economy, PC]()
		{
			if (!Economy->BuyBenchLevel())
			{
				return false;
			}
			if (AJRCharacter* Hero = PC ? Cast<AJRCharacter>(PC->GetPawn()) : nullptr)
			{
				if (UJRWeaponComponent* Weapon = Hero->GetWeaponComponent())
				{
					Weapon->SetUpgradeMultipliers(Economy->GetPermanentDamageMultiplier(), 1.f);
				}
			}
			return true;
		};
		Out.Add(MoveTemp(Entry));
		break;
	}
	case EJRShopType::Arvore: // [A-098] Árvore-Mãe: um item por nó, agrupado por galho
	{
		for (const FJRTreeNodeDef& Node : FJRSkillTree::Nodes())
		{
			const FName Id = Node.Id;
			const int32 Rank = Economy->GetTreeRank(Id);
			const bool bMax = Rank >= Node.MaxRank;
			FString Why;
			const bool bOpen = Economy->IsTreeNodeOpen(Id, &Why);
			// galho fechado e sem nenhum nível: só mostra o primeiro nó trancado de cada galho (o resto aparece depois)
			if (!bOpen && !bMax && Rank == 0 && Node.Depth > 1)
			{
				const FJRTreeNodeDef* Parent = FJRSkillTree::Find(Node.Requires);
				if (Parent && Economy->GetTreeRank(Parent->Id) == 0)
				{
					continue;
				}
			}
			FShopEntry Entry;
			Entry.Label = FString::Printf(TEXT("%s  %s  %d/%d"), *FJRSkillTree::BranchName(Node.Branch), Node.Label, Rank, Node.MaxRank);
			const FString Now = Rank > 0 ? FJRSkillTree::EffectText(Node, Rank) : FString(TEXT("nada ainda"));
			const FString Next = bMax ? FString(TEXT("máximo")) : FJRSkillTree::EffectText(Node, Rank + 1);
			Entry.Detail = bOpen || bMax ? FString::Printf(TEXT("Agora: %s. Próximo: %s"), *Now, *Next) : Why;
			Entry.Icon = Node.Icon;
			Entry.bCrystals = true;
			Entry.bOwned = bMax;
			Entry.bAvailable = bOpen;
			Entry.DenyLine = bMax ? TEXT("Esse galho já deu tudo o que tinha.") : Why;
			Entry.Price = bMax ? 0 : FJRSkillTree::Cost(Node, Rank);
			Entry.Buy = [Economy, PC, Id]()
			{
				if (!Economy->BuyTreeNode(Id))
				{
					return false;
				}
				if (AJRCharacter* Hero = PC ? Cast<AJRCharacter>(PC->GetPawn()) : nullptr)
				{
					if (UGameInstance* G = PC->GetGameInstance())
					{
						if (UJRRunSubsystem* R = G->GetSubsystem<UJRRunSubsystem>())
						{
							R->ApplyStatsToHero(Hero, false); // efeito já na cidade (vida, velocidade)
						}
					}
				}
				return true;
			};
			Out.Add(MoveTemp(Entry));
		}
		break;
	}
	case EJRShopType::Portao:
	{
		const int32 MaxArena = Economy->GetUnlockedArenaLevel(); // [A-098] nível novo a cada 6 ondas de recorde (abre bairro também)
		for (int32 ArenaLv = 1; ArenaLv <= MaxArena; ++ArenaLv)
		{
			FShopEntry Entry;
			Entry.Label = FString::Printf(TEXT("Arena nível %d"), ArenaLv);
			Entry.Detail = FString::Printf(TEXT("Zumbis com %.0f%% de vida, pagam %.0f%%"),
				FJRRemapRules::EnemyHealthScale(ArenaLv) * 100.f, FJRRemapRules::CreditsPerCost(ArenaLv) / 6.f * 100.f);
			Entry.Icon = TEXT("R_Portal");
			Entry.Price = 0;
			Entry.Buy = [Run, PC, ArenaLv]()
			{
				if (!Run)
				{
					return false;
				}
				Run->StartRun(ArenaLv);
				UGameplayStatics::OpenLevel(PC, FName(FJRRemapRules::ArenaMap));
				return true;
			};
			Out.Add(MoveTemp(Entry));
		}
		if (MaxArena < 5)
		{
			FShopEntry LockedEntry;
			LockedEntry.Label = FString::Printf(TEXT("Arena nível %d"), MaxArena + 1);
			LockedEntry.Detail = FString::Printf(TEXT("Chegue à onda %d numa corrida para liberar"), MaxArena * 6);
			LockedEntry.Icon = TEXT("Icon_Lock");
			LockedEntry.bAvailable = false;
			Out.Add(MoveTemp(LockedEntry));
		}
		break;
	}
	}
}

void AJRRemapHUD::DrawShopBubble(AJRShopkeeper* Keeper)
{
	const float Open = JRRHS::EaseBack(Since(ShopOpenedAt) / 0.3f);
	const float Alpha = FMath::Min(1.f, Since(ShopOpenedAt) / 0.15f);
	const float BW = 560.f * RU;
	const float BX = Canvas->ClipX * 0.05f;
	const float BY = Canvas->ClipY * 0.40f + (1.f - Open) * 40.f * RU;
	const float TextPx = 26.f * RU;

	// fala com efeito de digitação
	const int32 Shown = FMath::Clamp(FMath::FloorToInt(Since(ShopLineAt) * TypewriterSpeed), 0, ShopLine.Len());
	TArray<FString> Lines = WrapText(ShopLine, false, TextPx, BW - 64.f * RU); // quebra pela frase inteira (não pula de linha ao digitar)
	const float LineH = MeasureText(TEXT("Ág"), false, TextPx).Y * 0.98f;
	const float BH = FMath::Max(3, Lines.Num()) * LineH + 56.f * RU;

	// rabinho do balão apontando para a cabeça do vendedor
	FVector Origin;
	FVector Extent;
	Keeper->GetActorBounds(true, Origin, Extent);
	const FVector Head = Keeper->GetActorLocation() + FVector(0.f, 0.f, FMath::Clamp(static_cast<float>(Extent.Z), 60.f, 200.f) * 0.75f);
	const FVector HeadScreen = Project(Head, false);
	FVector2D TailTip(BX + BW * 0.8f, BY - 70.f * RU);
	if (HeadScreen.Z > 0.f)
	{
		TailTip = FVector2D(HeadScreen.X, HeadScreen.Y);
	}
	const float BaseX = FMath::Clamp(TailTip.X, BX + 70.f * RU, BX + BW - 70.f * RU);
	FVector2D Dir = TailTip - FVector2D(BaseX, BY);
	const float TailLen = FMath::Clamp(static_cast<float>(Dir.Size()), 30.f * RU, 90.f * RU);
	Dir = Dir.GetSafeNormal();
	if (Dir.Y > -0.2f)
	{
		Dir = FVector2D(Dir.X, -0.6f).GetSafeNormal(); // sempre sai por cima do balão
	}
	const FVector2D Tip = FVector2D(BaseX, BY + 6.f * RU) + Dir * TailLen;
	DrawSolidTri(FVector2D(BaseX - 30.f * RU, BY + 14.f * RU), FVector2D(BaseX + 30.f * RU, BY + 14.f * RU), Tip + Dir * 4.f * RU,
		JRRHS::Fade(JRRHS::Ink, 0.95f * Alpha));
	DrawSolidTri(FVector2D(BaseX - 22.f * RU, BY + 16.f * RU), FVector2D(BaseX + 22.f * RU, BY + 16.f * RU), Tip, JRRHS::Fade(JRRHS::Lilac, Alpha));

	PanelBox(BX, BY, BW, BH, JRRHS::Lilac, Alpha);
	// texto digitado (mantém a quebra da frase inteira)
	int32 Left = Shown;
	float LineY = BY + 30.f * RU;
	for (const FString& Line : Lines)
	{
		if (Left <= 0)
		{
			break;
		}
		const FString Part = Line.Left(Left);
		Left -= Line.Len() + 1;
		DrawHudText(Part, BX + 32.f * RU, LineY, TextPx, JRRHS::Fade(JRRHS::White, Alpha), 0, false);
		LineY += LineH;
	}
	if (Shown >= ShopLine.Len() && JRRHS::Pulse(RNow, 6.f) > 0.5f)
	{
		DrawSolidTri(FVector2D(BX + BW - 46.f * RU, BY + BH - 34.f * RU), FVector2D(BX + BW - 26.f * RU, BY + BH - 34.f * RU),
			FVector2D(BX + BW - 36.f * RU, BY + BH - 22.f * RU), JRRHS::Fade(JRRHS::Cyan, Alpha));
	}

	// plaquinha com o nome e o ícone da função, por cima do canto do balão
	const FString Name = Keeper->GetDisplayName().ToString();
	IconPill(TEXT("PillLavender"), ShopIconFor(Keeper), Name, BX + 40.f * RU + MeasureText(Name, true, 30.f * RU).X * 0.5f + 40.f * RU,
		BY - 34.f * RU, 62.f * RU, 30.f * RU, JRRHS::White, Alpha);
}

void AJRRemapHUD::DrawShop()
{
	AJRShopkeeper* Keeper = ShopKeeper.Get();
	if (!Keeper)
	{
		return;
	}
	if (PressedClose())
	{
		CloseShop();
		return;
	}
	TArray<FShopEntry> Entries;
	BuildShopEntries(Entries);
	const UJREconomySubsystem* Economy = GetGameInstance()->GetSubsystem<UJREconomySubsystem>();
	const bool bCrystalShop = Keeper->GetShopType() == EJRShopType::Arvore; // [A-098]
	const int64 Credits = Economy ? (bCrystalShop ? Economy->GetCrystals() : Economy->GetCredits()) : 0;

	const int32 Choice = PollChoice(Entries.Num(), ShopSelected);
	if (Choice != INDEX_NONE && Entries.IsValidIndex(Choice))
	{
		FShopEntry& Picked = Entries[Choice];
		if (!Picked.bAvailable || !Picked.Buy)
		{
			ShopDenyRow = Choice;
			ShopDenyAt = RNow;
			ShopLine = !Picked.DenyLine.IsEmpty() ? Picked.DenyLine
				: Picked.bOwned ? TEXT("Essa você já tem. Quer outra coisa?") : TEXT("Ainda não. Volte quando for mais longe na arena.");
			ShopLineAt = RNow;
			PlayUi(TEXT("UI.Wheel.Close"), 0.8f, 0.8f);
		}
		else if (Picked.Price > Credits)
		{
			ShopDenyRow = Choice;
			ShopDenyAt = RNow;
			ShopLine = FString::Printf(TEXT("Faltam %s %s. Volte depois de uma boa corrida."), *Fmt(Picked.Price - Credits),
				Picked.bCrystals ? TEXT("cristais") : TEXT("créditos"));
			ShopLineAt = RNow;
			PlayUi(TEXT("UI.LowFuel"), 0.7f, 1.15f);
		}
		else
		{
			const int64 Paid = Picked.Price;
			const FString What = Picked.Label;
			if (Picked.Buy())
			{
				ShopFlashRow = Choice;
				ShopFlashAt = RNow;
				switch (Keeper->GetShopType())
				{
				case EJRShopType::Armeiro: ShopLine = FString::Printf(TEXT("%s é sua. Cuide bem dela."), *What); break;
				case EJRShopType::Bancada: ShopLine = TEXT("Pronto! Sente a diferença no gatilho?"); break;
				case EJRShopType::Portao: ShopLine = TEXT("Boa sorte lá fora."); break;
				case EJRShopType::Arvore: ShopLine = TEXT("Um galho novo brota. Você sente a seiva correndo."); break;
				}
				ShopLineAt = RNow;
				Keeper->PlayTalk();
				PlayUi(TEXT("UI.Objective"));
				if (Paid > 0 && bCrystalShop)
				{
					SpawnFloater(FString::Printf(TEXT("-%s"), *Fmt(Paid)), TEXT("R_Crystal"), JRRHS::Lilac,
						WalletCoinPos + FVector2D(0.f, 30.f * RU), 30.f);
				}
				else if (Paid > 0)
				{
					const float CoinsToY = Canvas->ClipY * 0.5f;
					SpawnFloater(FString::Printf(TEXT("-%s"), *Fmt(Paid)), TEXT("R_Coin"), JRRHS::Red,
						WalletCoinPos + FVector2D(0.f, 30.f * RU), 30.f);
					SpawnCoins(WalletCoinPos, FVector2D(Canvas->ClipX - 120.f * RU, CoinsToY), 4);
				}
				if (AJRCharacter* Hero = PlayerOwner ? Cast<AJRCharacter>(PlayerOwner->GetPawn()) : nullptr)
				{
					Hero->PlayFeedback(0.25f, 0.f, 2.f);
				}
			}
		}
		Entries.Reset();
		BuildShopEntries(Entries); // preço/estado novos
		if (!ShopKeeper.IsValid())
		{
			return; // o portão troca de mapa
		}
	}

	DrawShopBubble(Keeper);

	// ---- lista à direita
	const float Open = JRRHS::Ease(Since(ShopOpenedAt) / 0.3f);
	const float LW = 620.f * RU;
	const bool bCompact = Entries.Num() > 6; // [A-098] a Árvore-Mãe pode ter 12 linhas
	const float RowH = (bCompact ? 74.f : 96.f) * RU;
	const float RowGap = (bCompact ? 6.f : 12.f) * RU;
	const float HeadH = 110.f * RU;
	const float FootH = 64.f * RU;
	const float LH = HeadH + Entries.Num() * (RowH + RowGap) + FootH;
	const float LX = Canvas->ClipX - LW - 48.f * RU + (1.f - Open) * 160.f * RU;
	const float LY = FMath::Max(40.f * RU, Canvas->ClipY * 0.47f - LH * 0.5f);
	if (UTexture2D* Window = HudTex(TEXT("V3_Window")))
	{
		// [A-087] janela pintada (9 fatias: os cristais dos cantos não esticam).
		// [A-088] a moldura pintada é grossa (~12% de cada lado): a janela cresce em volta da lista para as linhas e o
		// número dos créditos ficarem dentro da área útil (print 3: passavam da borda).
		const float PadX = LW * 0.12f / 0.76f;
		const float PadY = FMath::Max(64.f * RU, LH * 0.09f);
		DrawNine(Window, LX - PadX, LY - PadY, LW + 2.f * PadX, LH + 2.f * PadY, 0.16f, 0.26f, 150.f * RU, 140.f * RU,
			JRRHS::Fade(FLinearColor::White, Open));
	}
	else
	{
		PanelBox(LX, LY, LW, LH, JRRHS::Lilac, Open);
	}

	// título e carteira
	FString Title = TEXT("LOJA");
	switch (Keeper->GetShopType())
	{
	case EJRShopType::Armeiro: Title = TEXT("ARMEIRO"); break;
	case EJRShopType::Bancada: Title = TEXT("BANCADA"); break;
	case EJRShopType::Portao: Title = TEXT("PORTÃO"); break;
	case EJRShopType::Arvore: Title = TEXT("ÁRVORE-MÃE"); break;
	}
	IconPill(TEXT("PillTeal"), ShopIconFor(Keeper), Title, LX + 150.f * RU, LY - 26.f * RU, 66.f * RU, 32.f * RU, JRRHS::White, Open);
	const int64 WalletShown = TweenNumber(bCrystalShop ? TEXT("Crystals") : TEXT("Wallet"), Credits, 5.f);
	const float WalletPop = PopOf(TEXT("Wallet"), 0.4f);
	const float DenyAge = Since(ShopDenyAt);
	const float Shake = DenyAge < 0.45f ? FMath::Sin(DenyAge * 70.f) * 10.f * RU * (1.f - DenyAge / 0.45f) : 0.f;
	const FLinearColor WalletColor = DenyAge < 0.6f ? FMath::Lerp(JRRHS::Gold, JRRHS::Red, 1.f - DenyAge / 0.6f) : JRRHS::Gold;
	const float WalletPx = 36.f * RU * (1.f + 0.18f * WalletPop);
	const FString WalletStr = Fmt(WalletShown);
	const float WalletW = MeasureText(WalletStr, true, WalletPx).X;
	const float WalletRight = LX + LW - 36.f * RU + Shake;
	const float WalletMid = LY + 62.f * RU;
	WalletCoinPos = FVector2D(WalletRight - WalletW - 30.f * RU, WalletMid);
	IconAt(bCrystalShop ? TEXT("R_Crystal") : TEXT("R_Coin"), WalletCoinPos.X, WalletMid, 46.f * RU * (1.f + 0.25f * WalletPop), Open, 20.f * WalletPop);
	TextMid(WalletStr, WalletRight, WalletMid, WalletPx, JRRHS::Fade(WalletColor, Open), 2);
	TextMid(TEXT("seus créditos"), WalletCoinPos.X - 30.f * RU, WalletMid, 19.f * RU, JRRHS::Fade(JRRHS::Soft, Open), 2, false);

	// linhas
	float RowY = LY + HeadH;
	for (int32 Index = 0; Index < Entries.Num(); ++Index)
	{
		const FShopEntry& Entry = Entries[Index];
		const bool bSel = Index == ShopSelected;
		const bool bAfford = Entry.Price <= Credits;
		const float RowIn = JRRHS::EaseBack((Since(ShopOpenedAt) - 0.08f - 0.06f * Index) / 0.3f);
		if (RowIn <= 0.01f)
		{
			RowY += RowH + RowGap;
			continue;
		}
		const float Slide = Smooth(FName(*FString::Printf(TEXT("RemapShopRow%d"), Index)), bSel ? 1.f : 0.f, 14.f, RDelta);
		const float FlashAge = Index == ShopFlashRow ? Since(ShopFlashAt) : 99.f;
		const float RowDeny = Index == ShopDenyRow ? Since(ShopDenyAt) : 99.f;
		const float RowShake = RowDeny < 0.45f ? FMath::Sin(RowDeny * 70.f) * 12.f * RU * (1.f - RowDeny / 0.45f) : 0.f;
		const float FlashPop = FlashAge < 0.35f ? 1.f - FlashAge / 0.35f : 0.f;
		const float RX = LX + 24.f * RU + Slide * 14.f * RU + RowShake + (1.f - RowIn) * 80.f * RU;
		const float RW = LW - 48.f * RU;
		const FLinearColor Rim = RowDeny < 0.5f ? JRRHS::Red : (bSel ? JRRHS::Cyan : JRRHS::Fade(JRRHS::Lilac, 0.8f));
		const float Glow = bSel ? 0.45f + 0.35f * JRRHS::Pulse(RNow, 5.f) : 0.f;
		const bool bRowLocked = !Entry.bAvailable && !Entry.bOwned;
		UTexture2D* RowTex = HudTex(bRowLocked ? TEXT("V3_RowLocked") : (bSel ? TEXT("V3_RowSelected") : TEXT("V3_RowNormal")));
		if (RowTex)
		{
			// [A-087] botão pintado em 3 estados; a negação pinta de vermelho e o selecionado pulsa
			const float Pulse = bSel ? 0.9f + 0.1f * JRRHS::Pulse(RNow, 5.f) : 1.f;
			FLinearColor Tint = RowDeny < 0.5f ? FLinearColor(1.f, 0.55f, 0.55f) : FLinearColor(Pulse, Pulse, Pulse);
			Tint = FMath::Lerp(Tint, JRRHS::Gold, FlashPop * 0.6f);
			// [A-088] linha torta (print 3): esticar a arte na vertical entortava as bordas pintadas. Agora só 3 fatias
			// na horizontal (altura inteira, sem esticar em pé) e a ponta proporcional à textura.
			const float RowDrawH = RowH + FlashPop * 8.f * RU;
			const float TexAspect = static_cast<float>(RowTex->GetSizeX()) / static_cast<float>(FMath::Max(1, RowTex->GetSizeY()));
			const float RowCapX = FMath::Min(RW * 0.45f, RowDrawH * TexAspect * 0.14f);
			DrawNine(RowTex, RX, RowY - FlashPop * 4.f * RU, RW, RowDrawH, 0.14f, 0.5f, RowCapX, RowDrawH * 0.5f,
				JRRHS::Fade(Tint, FMath::Min(1.f, RowIn) * Open));
			(void)Glow;
			(void)Rim;
		}
		else
		{
			PanelBox(RX, RowY - FlashPop * 4.f * RU, RW, RowH + FlashPop * 8.f * RU, Rim, FMath::Min(1.f, RowIn) * Open,
				FMath::Max(Glow, FlashPop), FlashPop > 0.f ? JRRHS::Gold : JRRHS::Cyan);
		}
		if (FlashPop > 0.f)
		{
			DrawRounded(RX + 8.f * RU, RowY + 8.f * RU, RW - 16.f * RU, RowH - 16.f * RU, 30.f * RU, FLinearColor(1.f, 1.f, 1.f, 0.35f * FlashPop));
		}
		const float MidY = RowY + RowH * 0.5f;
		const bool bLocked = bRowLocked;
		if (!(bLocked && RowTex)) // a linha bloqueada pintada já tem o cadeado no lugar do selo
		IconBadge(Entry.Icon, RX + 54.f * RU, MidY, 76.f * RU * (1.f + 0.15f * FlashPop + (bSel ? 0.05f * JRRHS::Pulse(RNow, 5.f) : 0.f)),
			Entry.bAvailable || Entry.bOwned ? 1.f : 0.6f, bSel ? FLinearColor::White : FLinearColor(0.85f, 0.85f, 0.95f));
		if (bLocked && !RowTex && Entry.Icon != TEXT("Icon_Lock"))
		{
			IconAt(TEXT("Icon_Lock"), RX + 76.f * RU, MidY + 20.f * RU, 34.f * RU);
		}
		// tecla no canto do selo
		DrawKeyCap(FString::Printf(TEXT("%d"), Index + 1), RX + 8.f * RU, RowY + 4.f * RU, 26.f * RU);
		// preço / estado
		FString PriceStr;
		FString PricePill = TEXT("PillNavy");
		FString PriceIcon;
		FLinearColor PriceColor = JRRHS::Gold;
		if (Entry.bOwned)
		{
			PriceStr = Entry.bCrystals ? TEXT("MÁXIMO") : TEXT("COMPRADO");
			PriceColor = JRRHS::Green;
		}
		else if (bLocked)
		{
			PriceStr = TEXT("BLOQUEADA");
			PriceColor = JRRHS::Locked;
			PriceIcon = TEXT("Icon_Lock");
		}
		else if (Entry.Price <= 0)
		{
			PriceStr = TEXT("IR");
			PricePill = TEXT("PillTeal");
			PriceColor = JRRHS::White;
		}
		else
		{
			PriceStr = Fmt(Entry.Price);
			PriceIcon = Entry.bCrystals ? TEXT("R_Crystal") : TEXT("R_Coin"); // [A-098]
			PriceColor = bAfford ? JRRHS::Gold : JRRHS::Red;
			if (RowDeny < 0.6f)
			{
				PriceColor = FMath::Lerp(JRRHS::Red, FLinearColor::White, 0.5f + 0.5f * FMath::Sin(RowDeny * 40.f));
			}
		}
		const float PricePx = 24.f * RU;
		const float PriceW = PillWidthFor(PricePill, 50.f * RU, MeasureText(PriceStr, true, PricePx).X + (PriceIcon.IsEmpty() ? 0.f : 46.f * RU));
		const float PriceCX = RX + RW - 22.f * RU - PriceW * 0.5f;
		IconPill(PricePill, PriceIcon, PriceStr, PriceCX, MidY - 25.f * RU, 50.f * RU, PricePx, PriceColor, RowIn > 1.f ? 1.f : RowIn,
			1.f + 0.12f * FlashPop);
		// nome e detalhe
		const float TextX = RX + 104.f * RU;
		const float TextMaxW = PriceCX - PriceW * 0.5f - TextX - 14.f * RU;
		const FLinearColor LabelColor = (Entry.bAvailable || Entry.bOwned) ? JRRHS::White : JRRHS::Locked;
		DrawHudTextFit(Entry.Label, TextX, RowY + 16.f * RU, 26.f * RU, TextMaxW, LabelColor, 0, true);
		DrawHudTextFit(Entry.Detail, TextX, RowY + 56.f * RU, 18.f * RU, TextMaxW, JRRHS::Soft, 0, false);
		RowY += RowH + RowGap;
	}

	// rodapé com as teclas
	const float FootY = LY + LH - FootH * 0.5f - 6.f * RU;
	float KX = LX + 36.f * RU;
	auto Hint = [this, &KX, FootY](const TCHAR* HintKey, const TCHAR* HintText)
	{
		KX += DrawKeyCap(HintKey, KX, FootY - 15.f * RU, 30.f * RU) + 8.f * RU;
		KX += TextMid(HintText, KX, FootY, 19.f * RU, JRRHS::Soft, 0, false) + 22.f * RU;
	};
	Hint(TEXT("1-4"), TEXT("escolher"));
	Hint(TEXT("ENTER"), Keeper->GetShopType() == EJRShopType::Portao ? TEXT("ir") : TEXT("comprar"));
	Hint(TEXT("Q"), TEXT("sair"));
}

// ====================================================================== carteira (cidade)

void AJRRemapHUD::DrawWallet()
{
	const UJREconomySubsystem* Economy = GetGameInstance()->GetSubsystem<UJREconomySubsystem>();
	if (!Economy)
	{
		return;
	}
	const int64 RealCredits = Economy->GetCredits();
	const int64 Target = bWalletHeld ? WalletHeldValue : RealCredits;
	const int64 Before = TweenGoal.Contains(TEXT("Wallet")) ? TweenGoal[TEXT("Wallet")] : Target;
	const int64 Shown = TweenNumber(TEXT("Wallet"), Target, 3.5f);
	const float Pop = PopOf(TEXT("Wallet"), 0.45f);

	const float PW = 330.f * RK;
	const float PH = 168.f * RK;
	const float M = SafeMargin * RU;
	const float PX = Canvas->ClipX - M - PW - 10.f * RK;
	const float PY = M + (JRHudArt::MapHeroSize.H + 56.f) * RK;
	PanelBox(PX, PY, PW, PH, JRRHS::Lilac, 1.f, Pop * 0.9f, JRRHS::Gold);

	// créditos (linha grande)
	const float Row1 = PY + 46.f * RK;
	WalletCoinPos = FVector2D(PX + 46.f * RK, Row1);
	if (Target > Before)
	{
		SpawnFloater(FString::Printf(TEXT("+%s"), *Fmt(Target - Before)), FString(), JRRHS::Green, WalletCoinPos + FVector2D(120.f * RK, 40.f * RK), 30.f);
	}
	IconAt(TEXT("R_Coin"), WalletCoinPos.X, Row1, 58.f * RK * (1.f + 0.3f * Pop), 1.f, 25.f * Pop);
	TextMid(Fmt(Shown), PX + 86.f * RK, Row1, 40.f * RK * (1.f + 0.15f * Pop), FMath::Lerp(JRRHS::Gold, FLinearColor::White, Pop * 0.6f));
	TextMid(TEXT("CRÉDITOS"), PX + PW - 26.f * RK, Row1 - 22.f * RK, 15.f * RK, JRRHS::Soft, 2, false);
	// bancada e recorde
	const float Row2 = PY + 98.f * RK;
	const float Row3 = PY + 136.f * RK;
	IconAt(TEXT("R_Bench"), PX + 46.f * RK, Row2, 38.f * RK);
	// [A-086] o bônus vem logo depois do nível (antes ficava alinhado à direita e encavalava no texto)
	const float BenchW = TextMid(FString::Printf(TEXT("Bancada nv %d"), Economy->GetBenchLevel()), PX + 76.f * RK, Row2, 22.f * RK, JRRHS::White);
	// [A-088] "+80% dano" passava da borda direita: mede e diminui a letra até caber dentro do painel
	const FString BonusStr = FString::Printf(TEXT("+%d%% dano"), Economy->GetBenchLevel() * 10);
	const float BonusX = PX + 76.f * RK + BenchW + 10.f * RK;
	const float BonusRoom = PX + PW - 24.f * RK - BonusX;
	float BonusPx = 18.f * RK;
	const float BonusW = MeasureText(BonusStr, false, BonusPx).X;
	if (BonusW > BonusRoom && BonusW > 1.f)
	{
		BonusPx = FMath::Max(11.f * RK, BonusPx * BonusRoom / BonusW);
	}
	TextMid(BonusStr, BonusX, Row2, BonusPx, JRRHS::Cyan, 0, false);
	IconAt(TEXT("R_Trophy"), PX + 46.f * RK, Row3, 38.f * RK);
	TextMid(FString::Printf(TEXT("Recorde: onda %d"), Economy->GetBestWave()), PX + 76.f * RK, Row3, 22.f * RK, JRRHS::White);
}

// ====================================================================== nome dos vendedores (cidade)

void AJRRemapHUD::DrawNpcNames()
{
	const APawn* Pawn = PlayerOwner ? PlayerOwner->GetPawn() : nullptr;
	if (!Pawn || IsHudModalOpen())
	{
		return;
	}
	for (TActorIterator<AJRShopkeeper> It(GetWorld()); It; ++It)
	{
		const AJRShopkeeper* Keeper = *It;
		const float DistM = static_cast<float>(FVector::Dist(Pawn->GetActorLocation(), Keeper->GetActorLocation())) / 100.f;
		if (DistM > NpcNameRange)
		{
			continue;
		}
		FVector Origin;
		FVector Extent;
		Keeper->GetActorBounds(true, Origin, Extent);
		const double TopZ = Extent.Z > 1.0 && Extent.Z < 600.0 ? Origin.Z + Extent.Z : Keeper->GetActorLocation().Z + 120.0;
		const FVector Screen = Project(FVector(Keeper->GetActorLocation().X, Keeper->GetActorLocation().Y, TopZ + 15.0), false); // embaixo do pino do objetivo (que fica a +70)
		if (Screen.Z <= 0.f || Screen.X < 0.f || Screen.X > Canvas->ClipX || Screen.Y < 0.f || Screen.Y > Canvas->ClipY)
		{
			continue;
		}
		const float Alpha = FMath::Clamp((NpcNameRange - DistM) / 4.f, 0.f, 1.f);
		const float Bob = 3.f * RU * FMath::Sin(static_cast<float>(RNow) * 2.2f + static_cast<float>(Keeper->GetUniqueID() % 7));
		const float Near = FMath::Clamp(1.2f - DistM / NpcNameRange, 0.75f, 1.f);
		// [A-086] a placa ficava cortada na borda da tela: o centro é puxado para dentro (meia largura estimada)
		const FString NpcName = Keeper->GetDisplayName().ToString();
		const float HalfW = (MeasureText(NpcName, true, 24.f * RU * Near).X + 90.f * RU) * 0.5f;
		const float SafeX = FMath::Clamp(Screen.X, HalfW + 12.f * RU, Canvas->ClipX - HalfW - 12.f * RU);
		IconPill(TEXT("PillLavender"), ShopIconFor(Keeper), NpcName, SafeX, Screen.Y - 24.f * RU + Bob,
			48.f * RU, 24.f * RU, JRRHS::White, Alpha, Near);
	}
}

void AJRRemapHUD::DrawPickupLabels()
{
	const APawn* Pawn = PlayerOwner ? PlayerOwner->GetPawn() : nullptr;
	if (!Pawn || IsHudModalOpen())
	{
		return;
	}
	const float Range = 900.f;
	struct FNear
	{
		const AJRPickup* Item;
		float Dist;
	};
	TArray<FNear, TInlineAllocator<16>> Near;
	for (TActorIterator<AJRPickup> It(GetWorld()); It; ++It)
	{
		const AJRPickup* Item = *It;
		if (!Item || Item->IsTaken())
		{
			continue;
		}
		const float D = static_cast<float>(FVector::Dist(Pawn->GetActorLocation(), Item->GetActorLocation()));
		if (D <= Range)
		{
			Near.Add({ Item, D });
		}
	}
	Near.Sort([](const FNear& A, const FNear& B) { return A.Dist < B.Dist; });
	// [A-088] etiquetas se sobrepunham quando caíam vários itens juntos (print 12): cada uma que bateria numa já
	// desenhada sobe para cima dela (pilha), com um ponto marcando o item. Mais de 4: a última vira "+N itens".
	struct FPlacedLabel
	{
		float X;
		float Y;
		float HalfW;
		float HalfH;
	};
	TArray<FPlacedLabel, TInlineAllocator<8>> Placed;
	const int32 MaxLabels = 4;
	for (int32 i = 0; i < FMath::Min(Near.Num(), MaxLabels); ++i)
	{
		const AJRPickup* Item = Near[i].Item;
		const FVector Screen = Project(Item->GetActorLocation() + FVector(0.f, 0.f, 75.f), false);
		if (Screen.Z <= 0.f || Screen.X < 0.f || Screen.X > Canvas->ClipX || Screen.Y < 0.f || Screen.Y > Canvas->ClipY)
		{
			continue;
		}
		// some de leve no fim do alcance; o mais perto fica um pouco maior
		const float Alpha = FMath::Clamp((Range - Near[i].Dist) / 250.f, 0.f, 1.f);
		const float Size = i == 0 ? 1.f : 0.85f;
		const float Bob = 2.f * RU * FMath::Sin(static_cast<float>(RNow) * 3.f + static_cast<float>(Item->GetUniqueID() % 11));
		FLinearColor Tint = Item->GetLabelColor();
		Tint = FLinearColor::LerpUsingHSV(Tint, FLinearColor::White, 0.35f);
		FString LabelStr = Item->GetLabelText();
		if (i == MaxLabels - 1 && Near.Num() > MaxLabels)
		{
			LabelStr = FString::Printf(TEXT("+%d itens"), Near.Num() - (MaxLabels - 1));
		}
		const float HalfW = (MeasureText(LabelStr, true, 21.f * RU * Size).X + 70.f * RU * Size) * 0.5f;
		const float HalfH = 23.f * RU * Size;
		float LabelY = static_cast<float>(Screen.Y) + Bob;
		for (int32 Guard = 0; Guard < 8; ++Guard)
		{
			bool bHit = false;
			for (const FPlacedLabel& Other : Placed)
			{
				if (FMath::Abs(static_cast<float>(Screen.X) - Other.X) < HalfW + Other.HalfW && FMath::Abs(LabelY - Other.Y) < HalfH + Other.HalfH)
				{
					LabelY = Other.Y - (HalfH + Other.HalfH) - 4.f * RU;
					bHit = true;
				}
			}
			if (!bHit)
			{
				break;
			}
		}
		Placed.Add({ static_cast<float>(Screen.X), LabelY, HalfW, HalfH });
		if (LabelY < static_cast<float>(Screen.Y) - 12.f * RU)
		{
			// subiu na pilha: ponto no item para saber de quem é a etiqueta
			const float DotR = 5.f * RU;
			DrawRounded(static_cast<float>(Screen.X) - DotR, static_cast<float>(Screen.Y) + 30.f * RU - DotR, 2.f * DotR, 2.f * DotR, DotR,
				JRRHS::Fade(Tint, 0.8f * Alpha));
		}
		IconPill(TEXT("PillNavy"), Item->GetLabelIcon(), LabelStr, Screen.X, LabelY, 44.f * RU, 21.f * RU, Tint, Alpha, Size);
	}
}

// ====================================================================== tela de título (cidade)

bool AJRRemapHUD::DrawTitleScreen()
{
	UJRRunSubsystem* Run = GetGameInstance() ? GetGameInstance()->GetSubsystem<UJRRunSubsystem>() : nullptr;
	UTexture2D* Back = HudTex(TEXT("V3_MenuBackground"));
	if (!Run || !Back || !PlayerOwner)
	{
		return false;
	}
	if (!Run->bTitleShown)
	{
		Run->bTitleShown = true;
		bTitleActive = true;
		TitleOpenedAt = RNow;
		TitleClosingAt = -100.0;
		TitleSelected = 0;
		SetPawnInput(false);
		PlayerOwner->bShowMouseCursor = true;
	}
	if (!bTitleActive)
	{
		return false;
	}
	const float W = Canvas->ClipX;
	const float H = Canvas->ClipY;
	const float Age = Since(TitleOpenedAt);
	const float CloseAge = TitleClosingAt > 0.0 ? Since(TitleClosingAt) : -1.f;
	if (CloseAge > 0.55f)
	{
		bTitleActive = false;
		SetPawnInput(true);
		PlayerOwner->bShowMouseCursor = false;
		return false;
	}
	const float Out = CloseAge >= 0.f ? FMath::Clamp(CloseAge / 0.55f, 0.f, 1.f) : 0.f;
	const float Alpha = 1.f - JRRHS::Ease(Out);

	// fundo: zoom lento e leve paralaxe com o mouse
	float MX = W * 0.5f;
	float MY = H * 0.5f;
	PlayerOwner->GetMousePosition(MX, MY);
	const float Zoom = 1.06f + 0.04f * FMath::Min(1.f, Age / 25.f) + 0.08f * JRRHS::Ease(Out);
	const float BW = W * Zoom;
	const float BH = FMath::Max(H * Zoom, BW * static_cast<float>(Back->GetSizeY()) / static_cast<float>(FMath::Max(1, Back->GetSizeX())));
	const float Par = 18.f * RU;
	const float BX = (W - BW) * 0.5f - (MX / W - 0.5f) * Par;
	const float BY = (H - BH) * 0.5f - (MY / H - 0.5f) * Par;
	DrawTex(Back, BX, BY, BW, BH, JRRHS::Fade(FLinearColor::White, Alpha));
	// entra do preto
	if (Age < 0.8f)
	{
		DrawRounded(0.f, 0.f, W, H, 0.f, FLinearColor(0.f, 0.f, 0.f, 1.f - JRRHS::Ease(Age / 0.8f)));
	}

	// título: letras caem uma a uma com mola
	const FString Title = TEXT("VILLA STAR");
	const float TitlePx = 118.f * RU;
	float LX = W * 0.07f;
	const float TitleY = H * 0.20f;
	for (int32 i = 0; i < Title.Len(); ++i)
	{
		const FString Ch = Title.Mid(i, 1);
		const float T = (Age - 0.35f - 0.06f * i) / 0.4f;
		const float ChW = MeasureText(Ch, true, TitlePx).X;
		if (T > 0.f)
		{
			const float Drop = (1.f - FMath::Min(1.f, JRRHS::EaseBack(T))) * -60.f * RU;
			const float Bob = 3.f * RU * FMath::Sin(static_cast<float>(RNow) * 1.8f + i * 0.6f);
			const FLinearColor Glow = FMath::Lerp(JRRHS::Cyan, FLinearColor::White, 0.35f);
			TextMid(Ch, LX + 3.f * RU, TitleY + Drop + Bob + 5.f * RU, TitlePx, JRRHS::Fade(JRRHS::Ink, 0.85f * Alpha * FMath::Min(1.f, T)), 0, true);
			TextMid(Ch, LX, TitleY + Drop + Bob, TitlePx, JRRHS::Fade(Glow, Alpha * FMath::Min(1.f, T)), 0, true);
		}
		LX += ChW;
	}
	TextMid(TEXT("Sobreviva, junte créditos, restaure a vila"), W * 0.07f + 6.f * RU, TitleY + TitlePx * 0.85f, 28.f * RU,
		JRRHS::Fade(JRRHS::Soft, Alpha * FMath::Clamp((Age - 1.f) / 0.4f, 0.f, 1.f)), 0, false);

	// botões
	static const TCHAR* Labels[] = { TEXT("JOGAR"), TEXT("SAIR") };
	const int32 Num = 2;
	const float BtnW = 470.f * RU;
	const float BtnH = BtnW * 252.f / 1024.f;
	const float BtnX = W * 0.07f;
	const float BtnY0 = H * 0.48f;
	const float Gap = 18.f * RU;
	int32 Hover = INDEX_NONE;
	for (int32 i = 0; i < Num; ++i)
	{
		const float Y = BtnY0 + i * (BtnH + Gap);
		if (MX >= BtnX && MX <= BtnX + BtnW && MY >= Y && MY <= Y + BtnH)
		{
			Hover = i;
		}
	}
	if (CloseAge < 0.f)
	{
		if (Hover != INDEX_NONE && Hover != TitleSelected && FVector2D::Distance(FVector2D(MX, MY), TitleLastMouse) > 1.f)
		{
			TitleSelected = Hover;
			PlayUi(TEXT("UI.Wheel.Hover"));
		}
		if (Pressed(EKeys::Up) || Pressed(EKeys::W) || Pressed(EKeys::Gamepad_DPad_Up))
		{
			TitleSelected = (TitleSelected + Num - 1) % Num;
			PlayUi(TEXT("UI.Wheel.Hover"));
		}
		if (Pressed(EKeys::Down) || Pressed(EKeys::S) || Pressed(EKeys::Gamepad_DPad_Down))
		{
			TitleSelected = (TitleSelected + 1) % Num;
			PlayUi(TEXT("UI.Wheel.Hover"));
		}
		const bool bClick = Hover != INDEX_NONE && Pressed(EKeys::LeftMouseButton);
		if (Age > 0.9f && TitlePressedIndex == INDEX_NONE
			&& (bClick || Pressed(EKeys::Enter) || Pressed(EKeys::SpaceBar) || Pressed(EKeys::Gamepad_FaceButton_Bottom)))
		{
			TitlePressedIndex = bClick ? Hover : TitleSelected;
			TitlePressedAt = RNow;
			PlayUi(TEXT("UI.Objective"), 1.f, 1.1f);
		}
		// ação depois do "afundar" do botão (0,15 s)
		if (TitlePressedIndex != INDEX_NONE && Since(TitlePressedAt) > 0.15f)
		{
			if (TitlePressedIndex == 0)
			{
				TitleClosingAt = RNow;
			}
			else
			{
				UKismetSystemLibrary::QuitGame(this, PlayerOwner, EQuitPreference::Quit, false);
			}
			TitlePressedIndex = INDEX_NONE;
		}
	}
	TitleLastMouse = FVector2D(MX, MY);
	for (int32 i = 0; i < Num; ++i)
	{
		const float T = (Age - 0.9f - 0.1f * i) / 0.35f;
		if (T <= 0.f)
		{
			continue;
		}
		const bool bSel = i == TitleSelected;
		const bool bDown = i == TitlePressedIndex;
		const float Slide = (1.f - FMath::Min(1.f, JRRHS::EaseBack(T))) * -BtnW;
		const float Push = Smooth(FName(*FString::Printf(TEXT("TitleBtn%d"), i)), bSel ? 1.f : 0.f, 12.f, RDelta);
		const float Sc = (bDown ? 0.96f : 1.f) * (1.f + 0.04f * Push);
		const float BWi = BtnW * Sc;
		const float BHi = BtnH * Sc;
		const float X = BtnX + Slide + Push * 22.f * RU;
		const float Y = BtnY0 + i * (BtnH + Gap) + (BtnH - BHi) * 0.5f;
		UTexture2D* Tex = HudTex(bDown ? TEXT("V3_MenuBtnPressed") : (bSel ? TEXT("V3_MenuBtnHover") : TEXT("V3_MenuBtnNormal")));
		const float A = Alpha * FMath::Min(1.f, T * 2.f);
		if (Tex)
		{
			DrawTex(Tex, X, Y, BWi, BHi, JRRHS::Fade(FLinearColor::White, A));
		}
		TextMid(Labels[i], X + BWi * 0.5f, Y + BHi * 0.5f, 44.f * RU * Sc, JRRHS::Fade(bSel ? FLinearColor::White : JRRHS::Soft, A), 1, true);
	}
	TextMid(TEXT("W/S ou setas  ·  Enter ou clique"), W * 0.07f + 6.f * RU, H - 56.f * RU, 20.f * RU, JRRHS::Fade(JRRHS::Soft, 0.8f * Alpha), 0, false);
	return true;
}

// ====================================================================== corrida (arena)

void AJRRemapHUD::WatchRun()
{
	const UJRRunSubsystem* Run = GetGameInstance()->GetSubsystem<UJRRunSubsystem>();
	const AJRArenaDirector* Director = AJRArenaDirector::FindInWorld(this);
	if (!Run || !Director)
	{
		return;
	}
	// ---- abate: "+N" saindo do zumbi e moedas voando até o painel
	const int32 KillsNow = Run->GetKills();
	const int64 CreditsNow = Run->GetRunCredits();
	if (SeenKills < 0)
	{
		SeenKills = KillsNow;
		SeenRunCredits = CreditsNow;
	}
	else if (KillsNow != SeenKills || CreditsNow != SeenRunCredits)
	{
		const int64 Gain = CreditsNow - SeenRunCredits;
		bool bHasSpot = false;
		FVector Spot = FVector::ZeroVector;
		if (KillsNow > SeenKills)
		{
			const FVector Me = PlayerOwner && PlayerOwner->GetPawn() ? PlayerOwner->GetPawn()->GetActorLocation() : FVector::ZeroVector;
			double BestD = TNumericLimits<double>::Max();
			for (TActorIterator<AJREnemyCharacter> It(GetWorld()); It; ++It)
			{
				if (!It->IsDead())
				{
					continue;
				}
				const TWeakObjectPtr<AJREnemyCharacter> Weak(*It);
				if (CountedDead.Contains(Weak))
				{
					continue;
				}
				CountedDead.Add(Weak);
				const double D = FVector::DistSquared(Me, It->GetActorLocation());
				if (D < BestD)
				{
					BestD = D;
					Spot = It->GetActorLocation() + FVector(0.f, 0.f, 110.f);
					bHasSpot = true;
				}
			}
			for (auto SetIt = CountedDead.CreateIterator(); SetIt; ++SetIt)
			{
				if (!SetIt->IsValid())
				{
					SetIt.RemoveCurrent();
				}
			}
		}
		if (Gain > 0)
		{
			FVector2D From(Canvas->ClipX * 0.5f + 70.f * RU, Canvas->ClipY * 0.5f - 40.f * RU);
			if (bHasSpot)
			{
				SpawnWorldFloater(FString::Printf(TEXT("+%s"), *Fmt(Gain)), TEXT("R_Coin"), JRRHS::Gold, Spot, 30.f);
				const FVector SpotScreen = Project(Spot, false);
				if (SpotScreen.Z > 0.f)
				{
					From = FVector2D(SpotScreen.X, SpotScreen.Y);
				}
			}
			else
			{
				SpawnFloater(FString::Printf(TEXT("+%s"), *Fmt(Gain)), TEXT("R_Coin"), JRRHS::Gold, From, 30.f);
			}
			SpawnCoins(From, RunCoinPos, FMath::Clamp(static_cast<int32>(Gain / 8) + 1, 1, 4));
			PlayUi(TEXT("UI.Toast"), 0.35f, 1.2f + FMath::FRandRange(0.f, 0.15f));
		}
		SeenKills = KillsNow;
		SeenRunCredits = CreditsNow;
	}
	// ---- energia e nível
	const float Frac = FMath::Clamp(Run->GetEnergy() / FMath::Max(1.f, Run->GetEnergyNeeded()), 0.f, 1.f);
	const int32 LevelNow = Run->GetRunLevel();
	if (SeenRunLevel < 0)
	{
		SeenRunLevel = LevelNow;
		EnergyShown = Frac;
	}
	else if (LevelNow > SeenRunLevel)
	{
		SeenRunLevel = LevelNow;
		LevelUpAt = RNow;
		EnergyShown = 0.f;
		PlayUi(TEXT("UI.Objective"), 1.f, 1.1f);
		SpawnFloater(FString::Printf(TEXT("NÍVEL %d!"), LevelNow), TEXT("R_Energy"), JRRHS::Gold,
			FVector2D(Canvas->ClipX * 0.5f, 200.f * RU), 34.f, 1.3f);
	}
	if (SeenEnergyFrac >= 0.f && Frac > SeenEnergyFrac + 0.0005f)
	{
		EnergyGainAt = RNow;
	}
	SeenEnergyFrac = Frac;
	EnergyShown = FMath::FInterpTo(EnergyShown, Frac, RDelta, 8.f);
	// ---- onda nova
	const int32 WaveNow = Run->GetWave();
	if (WaveNow != SeenWave)
	{
		if (SeenWave >= 0 && WaveNow > 0)
		{
			WaveStartAt = RNow;
			ShowBanner(FString::Printf(TEXT("ONDA %d"), WaveNow), FString::Printf(TEXT("%d zumbis"), FJRRemapRules::WaveEnemyCount(WaveNow)),
				TEXT("R_Wave"), 1.8f);
			PlayUi(TEXT("UI.Wheel.Tab"), 1.f, 0.9f);
		}
		SeenWave = WaveNow;
	}
	// ---- nave chegou
	AJRExtractionShip* Ship = Director->GetActiveShip();
	if (Ship && SeenShip.Get() != Ship)
	{
		SeenShip = Ship;
		ShipTotalSeconds = FMath::Max(1.f, Ship->GetSecondsLeft());
		ShowBanner(TEXT("A NAVE CHEGOU!"), FString::Printf(TEXT("Corra até ela: créditos x%.2f"), Ship->GetMultiplier()), TEXT("R_Ship"), 2.2f);
		PlayUi(TEXT("UI.Objective"));
	}
	else if (!Ship)
	{
		SeenShip.Reset();
	}
	// ---- objetivo do diretor (contrato F2): texto no painel OBJETIVO
	FString Line = Director->GetObjectiveLine();
	if (Line.IsEmpty())
	{
		Line = TEXT("Sobreviva às ondas. A nave de extração chega a cada 3 ondas");
	}
	if (Line != LastObjectiveLine)
	{
		LastObjectiveLine = Line;
		ObjectiveChangedAt = RNow;
		ObjectiveShown = 0.f;
		SetCurrentTask(Line, nullptr, 0.f);
		PlayUi(TEXT("UI.Objective"), 0.8f);
	}
}

void AJRRemapHUD::DrawObjectiveProgress(const AJRArenaDirector* Director)
{
	const float Progress = Director->GetObjectiveProgress();
	if (Progress < 0.f || IsHudModalOpen())
	{
		return;
	}
	ObjectiveShown = FMath::FInterpTo(ObjectiveShown, FMath::Clamp(Progress, 0.f, 1.f), RDelta, 6.f);
	// fica no lugar da "dica" do painel OBJETIVO (embaixo dele)
	const float M = SafeMargin * RU;
	const float PillH = 46.f * RK;
	const float PillW = 400.f * RK;
	const float PX = M + 24.f * RK;
	const float PY = M + JRHudArt::ObjHeroSize.H * RK + 2.f * RK;
	const float Flash = Since(ObjectiveChangedAt) < 0.6f ? 1.f - Since(ObjectiveChangedAt) / 0.6f : 0.f;
	DrawPill(TEXT("PillNavy"), PX, PY, PillW, PillH, FLinearColor::White);
	IconAt(TEXT("R_Flag"), PX + 34.f * RK, PY + PillH * 0.46f, 36.f * RK, 1.f, -6.f + 12.f * JRRHS::Pulse(RNow, 3.f) * Flash);
	const FString Pct = FString::Printf(TEXT("%d%%"), FMath::RoundToInt(ObjectiveShown * 100.f));
	const float PctW = MeasureText(Pct, true, 20.f * RK).X;
	const float BarX = PX + 62.f * RK;
	const float BarW = PillW - 62.f * RK - PctW - 44.f * RK;
	BarAt(BarX, PY + PillH * 0.46f - 7.f * RK, BarW, 14.f * RK, ObjectiveShown, JRRHS::Gold, 1.f, Flash);
	TextMid(Pct, PX + PillW - 28.f * RK, PY + PillH * 0.46f, 20.f * RK, Progress >= 1.f ? JRRHS::Green : JRRHS::Gold, 2);
}

void AJRRemapHUD::DrawWaveAndEnergy(const UJRRunSubsystem* Run, const AJRArenaDirector* Director)
{
	const float CX = Canvas->ClipX * 0.5f;
	const float TopY = 16.f * RU;

	// ---- ONDA (pílula ciano) com pulo quando começa
	const float WavePop = Since(WaveStartAt) < 0.5f ? 1.f - Since(WaveStartAt) / 0.5f : 0.f;
	const FString WaveTitle = Run->GetWave() > 0 ? FString::Printf(TEXT("ONDA %d"), Run->GetWave()) : FString(TEXT("PREPARE-SE"));
	IconPill(TEXT("PillTeal"), TEXT("R_Wave"), WaveTitle, CX, TopY, 64.f * RU, 34.f * RU, JRRHS::White, 1.f, 1.f + 0.2f * WavePop);

	// ---- linha de baixo: restam N / próxima onda em N s
	FString SubIcon = TEXT("R_Skull");
	FString Sub;
	FLinearColor SubColor = JRRHS::Soft;
	if (Director->IsEnded())
	{
		Sub = TEXT("fim da corrida");
	}
	else if (Director->IsInBreak())
	{
		const int32 SecsLeft = FMath::CeilToInt(Director->GetBreakSecondsLeft());
		Sub = FString::Printf(TEXT("próxima onda em %d s"), SecsLeft);
		SubIcon = TEXT("R_Clock");
		SubColor = SecsLeft <= 3 ? JRRHS::Gold : JRRHS::Soft;
	}
	else
	{
		Sub = FString::Printf(TEXT("restam %d"), Director->GetEnemiesLeftInWave());
	}
	IconPill(TEXT("PillNavy"), SubIcon, Sub, CX, TopY + 66.f * RU, 42.f * RU, 21.f * RU, SubColor);

	// ---- barra de energia (nível da corrida)
	const float BW = 440.f * RU;
	const float BH = 22.f * RU;
	const float BX = CX - BW * 0.5f + 20.f * RU;
	const float BY = TopY + 128.f * RU;
	const float LevelAge = Since(LevelUpAt);
	const float GainAge = Since(EnergyGainAt);
	const bool bLevelFlash = LevelAge < 0.4f;
	const float ShownFrac = bLevelFlash ? 1.f : EnergyShown;
	const float GainFlash = GainAge < 0.3f ? 1.f - GainAge / 0.3f : 0.f;
	const float LevelFlash = LevelAge < 0.8f ? 1.f - LevelAge / 0.8f : 0.f;
	const bool bNearFull = ShownFrac > 0.85f;
	if (UTexture2D* GlowTex = HudTex(TEXT("Glow")))
	{
		const float GlowA = FMath::Max3(GainFlash * 0.5f, LevelFlash, bNearFull ? 0.25f + 0.25f * JRRHS::Pulse(RNow, 8.f) : 0.f);
		if (GlowA > 0.01f)
		{
			DrawTex(GlowTex, BX - 40.f * RU, BY - 40.f * RU, BW + 80.f * RU, BH + 80.f * RU, JRRHS::Fade(JRRHS::Purple, GlowA), FVector2D(0.f, 0.f),
				FVector2D(1.f, 1.f), true);
		}
	}
	BarAt(BX, BY, BW, BH, ShownFrac, JRRHS::Purple, 1.f, FMath::Max(GainFlash * 0.6f, LevelFlash));
	if (bNearFull)
	{
		// brilho correndo pela barra quase cheia
		const float Run01 = FMath::Fmod(static_cast<float>(RNow) * 0.9f, 1.f);
		const float GX = BX + BW * ShownFrac * Run01;
		DrawRounded(GX - 12.f * RU, BY + 2.f * RU, 24.f * RU, BH - 4.f * RU, 10.f * RU, FLinearColor(1.f, 1.f, 1.f, 0.35f));
	}
	// selo do nível
	const float LvPop = LevelAge < 0.6f ? JRRHS::EaseBack(LevelAge / 0.6f) : 1.f;
	const float LvSize = 64.f * RU * (LevelAge < 0.6f ? 0.7f + 0.5f * LvPop - 0.2f * (LevelAge / 0.6f) : 1.f);
	const float LvX = BX - 30.f * RU;
	const float LvY = BY + BH * 0.5f;
	IconBadge(FString(), LvX, LvY, LvSize, 1.f, FLinearColor(0.85f, 0.65f, 1.f));
	TextMid(FString::Printf(TEXT("%d"), Run->GetRunLevel()), LvX, LvY + 1.f * RU, 28.f * RU, JRRHS::White, 1);
	TextMid(TEXT("NV"), LvX, LvY - LvSize * 0.52f, 14.f * RU, JRRHS::Lilac, 1);
	IconAt(TEXT("R_Energy"), BX + BW + 20.f * RU, BY + BH * 0.5f, 40.f * RU, 1.f, GainFlash * 12.f);
	// escolhas de carta guardadas
	const int32 Pending = Run->GetPendingChoices() - (Run->IsChoosingCard() ? 1 : 0);
	if (Pending > 0)
	{
		const FString CardsLabel = Pending > 1 ? FString::Printf(TEXT("+%d cartas"), Pending) : FString(TEXT("+1 carta"));
		IconPill(TEXT("PillLavender"), TEXT("R_Star"), CardsLabel, BX + BW + 110.f * RU, BY - 12.f * RU, 46.f * RU, 20.f * RU, JRRHS::Gold, 1.f,
			1.f + 0.06f * JRRHS::Pulse(RNow, 6.f));
	}
}

void AJRRemapHUD::DrawRunPanel()
{
	const UJRRunSubsystem* Run = GetGameInstance()->GetSubsystem<UJRRunSubsystem>();
	const AJRArenaDirector* Director = AJRArenaDirector::FindInWorld(this);
	if (!Run || !Director)
	{
		return;
	}
	const bool bModal = IsHudModalOpen();
	if (!bModal)
	{
		DrawWaveAndEnergy(Run, Director);
	}
	DrawObjectiveProgress(Director);

	// ---- painel da corrida à esquerda (créditos, contrato de morte, abates, multiplicador)
	const float M = SafeMargin * RU;
	const float PW = 340.f * RK;
	const float PH = 176.f * RK;
	const float PX = M + 6.f * RK;
	const float PY = Canvas->ClipY * 0.33f;
	const int64 Shown = TweenNumber(TEXT("RunCredits"), Run->GetRunCredits(), 6.f);
	const float Pop = PopOf(TEXT("RunCredits"), 0.35f);
	PanelBox(PX, PY, PW, PH, JRRHS::Lilac, 1.f, Pop * 0.8f, JRRHS::Gold);
	IconPill(TEXT("PillTeal"), FString(), TEXT("CORRIDA"), PX + PW * 0.5f, PY - 22.f * RK, 46.f * RK, 22.f * RK, JRRHS::White);

	const float Row1 = PY + 54.f * RK;
	RunCoinPos = FVector2D(PX + 48.f * RK, Row1);
	IconAt(TEXT("R_Coin"), RunCoinPos.X, Row1, 56.f * RK * (1.f + 0.3f * Pop), 1.f, 20.f * Pop);
	TextMid(Fmt(Shown), PX + 86.f * RK, Row1, 40.f * RK * (1.f + 0.15f * Pop), FMath::Lerp(JRRHS::Gold, FLinearColor::White, 0.5f * Pop));

	// contrato de morte (sempre visível, REMAP 7.5)
	const float Row2 = PY + 104.f * RK;
	IconAt(TEXT("R_Skull"), PX + 48.f * RK, Row2, 36.f * RK, 0.9f);
	TextMid(TEXT("se morrer, fica com"), PX + 76.f * RK, Row2, 18.f * RK, JRRHS::Soft, 0, false);
	TextMid(Fmt(Run->GetCreditsIfDie()), PX + PW - 26.f * RK, Row2, 22.f * RK, JRRHS::Red, 2);

	// abates e multiplicador da próxima nave
	const float Row3 = PY + 144.f * RK;
	const float KillPop = PopOf(TEXT("RunKills"), 0.3f);
	TweenNumber(TEXT("RunKills"), Run->GetKills(), 20.f);
	IconAt(TEXT("R_Skull"), PX + 48.f * RK, Row3, 34.f * RK * (1.f + 0.3f * KillPop));
	TextMid(FString::Printf(TEXT("%d"), Run->GetKills()), PX + 76.f * RK, Row3, 24.f * RK, JRRHS::White);
	const float Mult = FJRRemapRules::ExtractionMultiplier(FMath::Max(3, (Run->GetWavesCleared() / 3 + 1) * 3));
	IconAt(TEXT("R_Star"), PX + PW * 0.55f, Row3, 34.f * RK);
	TextMid(FString::Printf(TEXT("nave x%.2f"), Mult), PX + PW * 0.55f + 24.f * RK, Row3, 22.f * RK, JRRHS::Cyan);
}

void AJRRemapHUD::DrawShipMarker()
{
	const AJRArenaDirector* Director = AJRArenaDirector::FindInWorld(this);
	const AJRExtractionShip* Ship = Director ? Director->GetActiveShip() : nullptr;
	if (!Ship || !PlayerOwner || IsHudModalOpen())
	{
		return;
	}
	const float SecsLeft = Ship->GetSecondsLeft();
	const float TimeFrac = FMath::Clamp(SecsLeft / FMath::Max(1.f, ShipTotalSeconds), 0.f, 1.f);
	const bool bHurry = SecsLeft < 8.f;
	const FLinearColor Tint = bHurry ? FMath::Lerp(JRRHS::Cyan, JRRHS::Red, JRRHS::Pulse(RNow, 10.f)) : JRRHS::Cyan;

	// ---- aviso fixo embaixo da barra de energia
	IconPill(TEXT("PillTeal"), TEXT("R_Ship"), FString::Printf(TEXT("NAVE  %d s  x%.2f"), FMath::CeilToInt(SecsLeft), Ship->GetMultiplier()),
		Canvas->ClipX * 0.5f, 196.f * RU, 54.f * RU, 26.f * RU, bHurry ? JRRHS::Gold : JRRHS::White, 1.f,
		1.f + (bHurry ? 0.06f : 0.03f) * JRRHS::Pulse(RNow, bHurry ? 10.f : 4.f));

	// ---- pino no mundo (fora da tela fica na borda com seta)
	FVector Screen = Project(Ship->GetActorLocation() + FVector(0.f, 0.f, 300.f), false);
	const float Edge = 80.f * RU;
	bool bOff = false;
	if (Screen.Z <= 0.f)
	{
		Screen.X = Canvas->ClipX - Screen.X;
		Screen.Y = Canvas->ClipY - Edge;
		bOff = true;
	}
	if (Screen.X < Edge || Screen.X > Canvas->ClipX - Edge || Screen.Y < Edge || Screen.Y > Canvas->ClipY - Edge)
	{
		bOff = true;
	}
	const FVector2D Raw(Screen.X, Screen.Y);
	const FVector2D Tip(FMath::Clamp(Screen.X, Edge, Canvas->ClipX - Edge), FMath::Clamp(Screen.Y, Edge + 240.f * RU, Canvas->ClipY - Edge - 240.f * RU));
	const float PinSize = (bOff ? 44.f : 54.f) * RU;
	DrawMarkerPin(Tip, PinSize, TEXT("R_Ship"), Tint, 1.f, true);
	// anel do tempo em volta do pino (esvazia até a nave ir embora)
	const FVector2D Disc = Tip - FVector2D(0.f, PinSize * 0.95f);
	const float RingR = PinSize * 0.5f + 7.f * RU;
	DrawArc(Disc, RingR, RingR + 6.f * RU, 0.f, 360.f, JRRHS::Fade(JRRHS::Ink, 0.85f), 40);
	DrawArc(Disc, RingR + 1.f * RU, RingR + 5.f * RU, 0.f, 360.f * TimeFrac, Tint, 40);
	if (bOff)
	{
		const FVector2D Mid(Canvas->ClipX * 0.5f, Canvas->ClipY * 0.5f);
		const FVector2D Dir = (Raw - Mid).GetSafeNormal();
		const float Yaw = FMath::RadiansToDegrees(FMath::Atan2(Dir.Y, Dir.X));
		const float Bob = 5.f * RU * FMath::Sin(static_cast<float>(RNow) * 7.f);
		DrawArrow(Disc + Dir * (RingR + 22.f * RU + Bob), Yaw, 12.f * RU, Tint);
	}
	const APawn* Pawn = PlayerOwner->GetPawn();
	const float DistM = Pawn ? static_cast<float>(FVector::Dist(Pawn->GetActorLocation(), Ship->GetActorLocation())) / 100.f : 0.f;
	IconPill(TEXT("PillNavy"), FString(), FString::Printf(TEXT("%d m"), FMath::RoundToInt(DistM)), Tip.X, Tip.Y + 8.f * RU, 36.f * RU, 19.f * RU,
		JRRHS::Cyan, 0.95f);
}

// ====================================================================== cartas

void AJRRemapHUD::DrawCardFace(EJRRunCard Card, float CX, float CY, float CardW, float CardH, float Alpha, bool bSelected, int32 KeyIndex)
{
	const int32 Rarity = FJRRemapRules::CardRarity(Card);
	const FLinearColor RC = RarityColor(Rarity);
	// [A-087] moldura pintada por raridade (comum ciano, rara magenta, épica dourada)
	if (UTexture2D* Frame = HudTex(Rarity == 2 ? TEXT("V3_CardEpic") : (Rarity == 1 ? TEXT("V3_CardRare") : TEXT("V3_CardCommon"))))
	{
		const float TexW = static_cast<float>(FMath::Max(1, Frame->GetSizeX()));
		const float TexH = static_cast<float>(FMath::Max(1, Frame->GetSizeY()));
		float FW = CardW;
		float FH = FW * TexH / TexW;
		if (FH > CardH)
		{
			FH = CardH;
			FW = FH * TexW / TexH;
		}
		const float FX = CX - FW * 0.5f;
		const float FY = CY - FH * 0.5f;
		const float U = FW / 515.f;
		// selecionada: halo na cor da raridade seguindo o contorno da própria moldura, pulsando
		if (bSelected)
		{
			const float Pulse = 0.55f + 0.45f * JRRHS::Pulse(RNow, 4.f);
			const float H = 14.f * U;
			DrawTex(Frame, FX - H, FY - H, FW + 2.f * H, FH + 2.f * H, JRRHS::Fade(RC, 0.55f * Pulse * Alpha));
		}
		DrawTex(Frame, FX, FY, FW, FH, JRRHS::Fade(FLinearColor::White, Alpha));
		// ícone no aro de cima (balança quando selecionada)
		const float Wobble = bSelected ? 6.f * FMath::Sin(static_cast<float>(RNow) * 4.f) : 0.f;
		const float Bounce = bSelected ? 4.f * U * FMath::Sin(static_cast<float>(RNow) * 6.f) : 0.f;
		IconAt(CardIcon(Card), CX, FY + FH * 0.149f + Bounce, FW * 0.40f * (bSelected ? 1.06f : 1.f), Alpha, Wobble);
		// nome e descrição no painel do meio
		DrawHudTextFit(FJRRemapRules::CardTitle(Card).ToString(), CX, FY + FH * 0.335f, 34.f * U, FW * 0.74f, JRRHS::Fade(JRRHS::White, Alpha), 1, true);
		const float DescPx = 23.f * U;
		const TArray<FString> DescLines = WrapText(FJRRemapRules::CardDescription(Card).ToString(), false, DescPx, FW * 0.7f);
		float DescY = FY + FH * 0.43f;
		const float DescH = MeasureText(TEXT("Ág"), false, DescPx).Y;
		for (int32 LineIndex = 0; LineIndex < DescLines.Num() && LineIndex < 5; ++LineIndex)
		{
			DrawHudText(DescLines[LineIndex], CX, DescY, DescPx, JRRHS::Fade(JRRHS::Soft, Alpha), 1, false);
			DescY += DescH;
		}
		// raridade na placa de baixo
		const TCHAR* RarityLabel = Rarity == 2 ? TEXT("ÉPICA") : (Rarity == 1 ? TEXT("RARA") : TEXT("COMUM"));
		TextMid(RarityLabel, CX, FY + FH * 0.78f, 26.f * U, JRRHS::Fade(RC, Alpha), 1, true);
		if (KeyIndex >= 0)
		{
			const float KeyH = 44.f * U;
			DrawKeyCap(FString::Printf(TEXT("%d"), KeyIndex + 1), CX - KeyH * 0.5f, FY + FH - KeyH * 0.75f, KeyH);
		}
		return;
	}
	const float X = CX - CardW * 0.5f;
	const float Y = CY - CardH * 0.5f;
	const float Glow = bSelected ? 0.7f + 0.3f * JRRHS::Pulse(RNow, 5.f) : (Rarity == 2 ? 0.35f : 0.f);
	PanelBox(X, Y, CardW, CardH, bSelected ? FMath::Lerp(RC, FLinearColor::White, 0.35f) : RC, Alpha, Glow, RC);
	const float U = CardW / 300.f; // escala interna da carta

	// raridade
	const TCHAR* RarityName = Rarity == 2 ? TEXT("ÉPICA") : (Rarity == 1 ? TEXT("RARA") : TEXT("COMUM"));
	IconPill(TEXT("PillNavy"), FString(), RarityName, CX, Y - 18.f * U, 40.f * U, 18.f * U, RC, Alpha);

	// ícone grande no anel (balança quando selecionado)
	const float IconCY = Y + 128.f * U;
	if (UTexture2D* GlowTex = HudTex(TEXT("Glow")))
	{
		const float G = 120.f * U * (bSelected ? 1.15f : 0.9f);
		DrawTex(GlowTex, CX - G, IconCY - G, 2.f * G, 2.f * G, JRRHS::Fade(RC, (bSelected ? 0.55f : 0.3f) * Alpha), FVector2D(0.f, 0.f),
			FVector2D(1.f, 1.f), true);
	}
	if (UTexture2D* RingTex = HudTex(TEXT("Ring")))
	{
		const float RS = 150.f * U;
		DrawTex(RingTex, CX - RS * 0.5f, IconCY - RS * 0.5f, RS, RS, JRRHS::Fade(RC, Alpha));
	}
	const float Wobble = bSelected ? 7.f * FMath::Sin(static_cast<float>(RNow) * 4.f) : 0.f;
	const float Bounce = bSelected ? 4.f * U * FMath::Sin(static_cast<float>(RNow) * 6.f) : 0.f;
	IconAt(CardIcon(Card), CX, IconCY + Bounce, 116.f * U * (bSelected ? 1.08f : 1.f), Alpha, Wobble);

	// nome e descrição
	DrawHudTextFit(FJRRemapRules::CardTitle(Card).ToString(), CX, Y + 222.f * U, 30.f * U, CardW - 30.f * U, JRRHS::Fade(JRRHS::White, Alpha), 1, true);
	const float DescPx = 20.f * U;
	const TArray<FString> Lines = WrapText(FJRRemapRules::CardDescription(Card).ToString(), false, DescPx, CardW - 44.f * U);
	float LineY = Y + 270.f * U;
	const float LineH = MeasureText(TEXT("Ág"), false, DescPx).Y;
	for (int32 LineIndex = 0; LineIndex < Lines.Num() && LineIndex < 4; ++LineIndex)
	{
		DrawHudText(Lines[LineIndex], CX, LineY, DescPx, JRRHS::Fade(JRRHS::Soft, Alpha), 1, false);
		LineY += LineH;
	}
	// tecla
	if (KeyIndex >= 0)
	{
		const FString KeyLabel = FString::Printf(TEXT("%d"), KeyIndex + 1);
		const float KeyH = 40.f * U;
		DrawKeyCap(KeyLabel, CX - KeyH * 0.5f, Y + CardH - KeyH * 0.5f, KeyH);
	}
}

void AJRRemapHUD::DrawCards()
{
	UJRRunSubsystem* Run = GetGameInstance()->GetSubsystem<UJRRunSubsystem>();
	AJRArenaDirector* Director = AJRArenaDirector::FindInWorld(this);
	if (!Run || !Director)
	{
		return;
	}
	const float CardW = 300.f * RU;
	const float CardH = 466.f * RU; // [A-087] proporção da moldura pintada (515 x 800)

	// carta escolhida subindo e sumindo (depois de confirmar)
	const float PickAge = Since(CardPickedAt);
	if (CardPicked != EJRRunCard::Count && PickAge < 0.7f && !Run->IsChoosingCard())
	{
		const float T = PickAge / 0.7f;
		const float Flash = FMath::Max(0.f, 1.f - PickAge / 0.25f);
		if (Flash > 0.f)
		{
			DrawRounded(0.f, 0.f, Canvas->ClipX, Canvas->ClipY, 0.f, FLinearColor(1.f, 1.f, 1.f, 0.25f * Flash));
		}
		const float Grow = 1.f + 0.25f * JRRHS::Ease(T);
		DrawCardFace(CardPicked, CardPickedPos.X, CardPickedPos.Y - 160.f * RU * JRRHS::Ease(T), CardW * Grow, CardH * Grow, 1.f - T, true, -1);
	}
	if (!Run->IsChoosingCard())
	{
		if (bCardsWereOpen && PlayerOwner)
		{
			PlayerOwner->bShowMouseCursor = false; // [A-087]
		}
		bCardsWereOpen = false;
		return;
	}
	if (!bCardsWereOpen)
	{
		bCardsWereOpen = true;
		CardsOpenedAt = RNow;
		CardSelected = 1;
		PlayUi(TEXT("UI.Wheel.Open"));
	}
	const TArray<EJRRunCard>& Cards = Run->GetOfferedCards();
	const float OpenAge = Since(CardsOpenedAt);
	int32 Choice = OpenAge > 0.35f ? PollChoice(Cards.Num(), CardSelected) : INDEX_NONE; // sem escolher sem querer na entrada
	const float Gap = 46.f * RU;
	const float Total = Cards.Num() * CardW + FMath::Max(0, Cards.Num() - 1) * Gap;
	const float FirstCX = Canvas->ClipX * 0.5f - Total * 0.5f + CardW * 0.5f;
	const float BaseCY = Canvas->ClipY * 0.56f;
	// [A-087] mouse: passar por cima seleciona, clicar escolhe (o cursor aparece só nesta tela)
	if (PlayerOwner)
	{
		PlayerOwner->bShowMouseCursor = true;
		float MX = 0.f;
		float MY = 0.f;
		if (PlayerOwner->GetMousePosition(MX, MY))
		{
			for (int32 Index = 0; Index < Cards.Num() && Index < 3; ++Index)
			{
				const float CX = FirstCX + Index * (CardW + Gap);
				if (FMath::Abs(MX - CX) <= CardW * 0.5f && FMath::Abs(MY - BaseCY) <= CardH * 0.5f)
				{
					if (CardSelected != Index && FVector2D::Distance(FVector2D(MX, MY), LastCardMouse) > 1.f)
					{
						CardSelected = Index;
						CardMovedAt = RNow;
						PlayUi(TEXT("UI.Wheel.Hover"));
					}
					if (Choice == INDEX_NONE && OpenAge > 0.35f && Pressed(EKeys::LeftMouseButton))
					{
						Choice = Index;
					}
				}
			}
			LastCardMouse = FVector2D(MX, MY);
		}
	}
	if (Choice != INDEX_NONE && Cards.IsValidIndex(Choice))
	{
		CardPicked = Cards[Choice];
		CardPickedAt = RNow;
		CardPickedPos = FVector2D(FirstCX + Choice * (CardW + Gap), BaseCY - 24.f * RU);
		bCardsWereOpen = false; // a próxima escolha guardada entra deslizando de novo
		if (PlayerOwner)
		{
			PlayerOwner->bShowMouseCursor = false;
		}
		PlayUi(TEXT("UI.Objective"), 1.f, 1.15f);
		const FString PickedTitle = FJRRemapRules::CardTitle(CardPicked).ToString();
		Director->ConfirmCard(Choice);
		ShowToast(FString::Printf(TEXT("Carta: %s"), *PickedTitle), RarityColor(FJRRemapRules::CardRarity(CardPicked)));
		return;
	}

	// fundo escuro com brilho roxo no meio
	const float FadeIn = FMath::Min(1.f, OpenAge / 0.25f);
	DrawRounded(0.f, 0.f, Canvas->ClipX, Canvas->ClipY, 0.f, JRRHS::Fade(JRRHS::Ink, 0.62f * FadeIn));
	// [A-085] o brilho roxo era um quadrado duro (textura sem borda suave) no meio da tela: removido.
	// título
	const float TitleIn = JRRHS::EaseBack(OpenAge / 0.35f);
	if (UTexture2D* Plate = HudTex(TEXT("V3_PlateLevel")))
	{
		// [A-087] placa pintada com o cristal; entra crescendo com mola
		const float PW = 560.f * RU * FMath::Max(0.2f, TitleIn);
		const float PH = PW * static_cast<float>(Plate->GetSizeY()) / static_cast<float>(FMath::Max(1, Plate->GetSizeX()));
		const float PX = Canvas->ClipX * 0.5f - PW * 0.5f;
		const float PY = Canvas->ClipY * 0.02f;
		DrawTex(Plate, PX, PY, PW, PH, JRRHS::Fade(FLinearColor::White, FadeIn));
		TextMid(FString::Printf(TEXT("NÍVEL %d!"), Run->GetRunLevel()), Canvas->ClipX * 0.5f, PY + PH * 0.66f, 58.f * RU * FMath::Max(0.2f, TitleIn),
			JRRHS::Fade(JRRHS::White, FadeIn), 1, true);
	}
	else
	{
		IconPill(TEXT("PillTeal"), TEXT("R_Energy"), FString::Printf(TEXT("NÍVEL %d!"), Run->GetRunLevel()), Canvas->ClipX * 0.5f, Canvas->ClipY * 0.09f,
			92.f * RU, 52.f * RU, JRRHS::White, FadeIn, FMath::Max(0.2f, TitleIn));
	}
	const int32 Waiting = Run->GetPendingChoices() - 1;
	const FString SubTitle = Waiting > 0 ? FString::Printf(TEXT("Escolha uma carta  (mais %d guardada%s)"), Waiting, Waiting > 1 ? TEXT("s") : TEXT(""))
		: FString(TEXT("Escolha uma carta"));
	IconPill(TEXT("PillNavy"), FString(), SubTitle, Canvas->ClipX * 0.5f, Canvas->ClipY * 0.02f + 300.f * RU, 48.f * RU, 24.f * RU, JRRHS::Gold, FadeIn);

	// cartas entrando de baixo, uma depois da outra, com mola
	for (int32 Index = 0; Index < Cards.Num() && Index < 3; ++Index)
	{
		const float T = (OpenAge - 0.1f - 0.09f * Index) / 0.45f;
		if (T <= 0.f)
		{
			continue;
		}
		const float In = JRRHS::EaseBack(T);
		const bool bSel = Index == CardSelected;
		CardScales[Index] = FMath::FInterpTo(CardScales[Index], bSel ? 1.07f : 0.95f, RDelta, 12.f);
		const float Hop = bSel && Since(CardMovedAt) < 0.25f ? FMath::Sin(Since(CardMovedAt) / 0.25f * UE_PI) * 14.f * RU : 0.f;
		const float CX = FirstCX + Index * (CardW + Gap);
		const float CY = BaseCY + (1.f - In) * Canvas->ClipY * 0.6f - (bSel ? 24.f * RU : 0.f) - Hop;
		const float Sc = CardScales[Index];
		DrawCardFace(Cards[Index], CX, CY, CardW * Sc, CardH * Sc, FMath::Min(1.f, T * 3.f) * (bSel ? 1.f : 0.88f), bSel, Index);
	}
	// dicas
	const float HintY = BaseCY + CardH * 0.5f + 60.f * RU;
	float HX = Canvas->ClipX * 0.5f - 220.f * RU;
	HX += DrawKeyCap(TEXT("1"), HX, HintY, 32.f * RU) + 6.f * RU;
	HX += DrawKeyCap(TEXT("2"), HX, HintY, 32.f * RU) + 6.f * RU;
	HX += DrawKeyCap(TEXT("3"), HX, HintY, 32.f * RU) + 12.f * RU;
	HX += TextMid(TEXT("ou setas +"), HX, HintY + 16.f * RU, 20.f * RU, JRRHS::Fade(JRRHS::Soft, FadeIn), 0, false) + 10.f * RU;
	HX += DrawKeyCap(TEXT("ENTER"), HX, HintY, 32.f * RU) + 10.f * RU;
	TextMid(TEXT("escolher"), HX, HintY + 16.f * RU, 20.f * RU, JRRHS::Fade(JRRHS::Soft, FadeIn), 0, false);
}

// ====================================================================== relatório (cidade)

void AJRRemapHUD::DrawReport()
{
	UJRRunSubsystem* Run = GetGameInstance()->GetSubsystem<UJRRunSubsystem>();
	if (!Run || !Run->HasReport())
	{
		bReportOpen = false;
		bWalletHeld = false;
		return;
	}
	const FJRRunReport& R = Run->GetReport();
	struct FRow
	{
		FString Icon;
		FString Label;
		int64 Value = 0;
		FString Prefix;
		FString Suffix;
		FLinearColor Color = FLinearColor::White;
		bool bFloat = false; // multiplicador
		float FloatValue = 1.f;
	};
	TArray<FRow> Rows;
	auto AddRow = [&Rows](const TCHAR* Icon, const TCHAR* Label, int64 Value, const FLinearColor& Color)
	{
		FRow& New = Rows.AddDefaulted_GetRef();
		New.Icon = Icon;
		New.Label = Label;
		New.Value = Value;
		New.Color = Color;
		return Rows.Num() - 1;
	};
	AddRow(TEXT("R_Portal"), TEXT("Arena"), R.SectorLevel, JRRHS::White);
	Rows.Last().Prefix = TEXT("nível ");
	AddRow(TEXT("R_Wave"), TEXT("Ondas vencidas"), R.Waves, R.bNewRecord ? JRRHS::Gold : JRRHS::White);
	AddRow(TEXT("R_Skull"), TEXT("Abates"), R.Kills, JRRHS::White);
	AddRow(TEXT("R_Flag"), TEXT("Objetivos cumpridos"), R.ObjectivesCompleted, JRRHS::White);
	AddRow(TEXT("R_Flame"), TEXT("Maior combo"), R.MaxCombo, JRRHS::White);
	Rows.Last().Prefix = TEXT("x");
	AddRow(TEXT("R_Energy"), TEXT("Nível da corrida"), R.RunLevel, JRRHS::White);
	AddRow(TEXT("R_Coin"), TEXT("Créditos na corrida"), R.CreditsEarned, JRRHS::Gold);
	AddRow(R.bExtracted ? TEXT("R_Star") : TEXT("R_Skull"), R.bExtracted ? TEXT("Multiplicador da nave") : TEXT("Contrato de morte"), 0,
		R.bExtracted ? JRRHS::Green : JRRHS::Red);
	Rows.Last().bFloat = true;
	Rows.Last().FloatValue = R.Multiplier;
	const int32 NumRows = Rows.Num();

	// tempo de cada linha (a última, "FICOU COM", vem depois de todas)
	const float FirstAt = 0.45f;
	const float Step = 0.22f;
	const float FinalAt = FirstAt + Step * NumRows + 0.15f;
	const float Age = Since(ReportOpenedAt);
	const bool bAllShown = Age > FinalAt + 0.5f;
	const bool bConfirm = Pressed(EKeys::Enter) || Pressed(EKeys::SpaceBar) || Pressed(EKeys::E) || Pressed(EKeys::Gamepad_FaceButton_Bottom);
	if (bConfirm && !bAllShown && Age > 0.3f)
	{
		ReportOpenedAt = RNow - (FinalAt + 0.6f); // pula a animação
	}
	else if (bConfirm && bAllShown)
	{
		Run->ConsumeReport();
		bReportOpen = false;
		bWalletHeld = false;
		SetPawnInput(true);
		PlayUi(TEXT("UI.Wheel.Close"));
		return;
	}
	SetPawnInput(false);
	const float AgeNow = Since(ReportOpenedAt);

	// fundo
	const float In = JRRHS::EaseBack(AgeNow / 0.35f);
	DrawRounded(0.f, 0.f, Canvas->ClipX, Canvas->ClipY, 0.f, JRRHS::Fade(JRRHS::Ink, 0.5f * FMath::Min(1.f, AgeNow / 0.25f)));
	const float PW = 660.f * RU;
	const float RowH = 46.f * RU;
	const float PH = 130.f * RU + RowH * NumRows + 120.f * RU;
	const float PX = Canvas->ClipX * 0.5f - PW * 0.5f;
	const float PY = Canvas->ClipY * 0.5f - PH * 0.5f + (1.f - In) * 60.f * RU;
	const FLinearColor Rim = R.bExtracted ? JRRHS::Cyan : JRRHS::Red;
	PanelBox(PX, PY, PW, PH, Rim, FMath::Min(1.f, AgeNow / 0.2f), 0.4f, Rim);
	IconPill(R.bExtracted ? TEXT("PillTeal") : TEXT("PillLavender"), R.bExtracted ? TEXT("R_Ship") : TEXT("R_Skull"),
		R.bExtracted ? TEXT("EXTRAÇÃO CONCLUÍDA") : TEXT("VOCÊ CAIU"), Canvas->ClipX * 0.5f, PY - 40.f * RU, 84.f * RU, 42.f * RU,
		R.bExtracted ? JRRHS::White : JRRHS::Red, 1.f, FMath::Max(0.2f, In));

	// linhas, uma a uma, contando
	float RowY = PY + 76.f * RU;
	for (int32 Index = 0; Index < NumRows; ++Index)
	{
		const FRow& Row = Rows[Index];
		const float RowAge = AgeNow - (FirstAt + Step * Index);
		if (RowAge < 0.f)
		{
			break;
		}
		if (Index >= ReportRowsShown)
		{
			ReportRowsShown = Index + 1;
			PlayUi(TEXT("UI.Wheel.Hover"), 0.8f, 0.9f + 0.05f * Index);
		}
		const float RowIn = JRRHS::EaseBack(RowAge / 0.3f);
		const float Alpha = FMath::Min(1.f, RowAge / 0.15f);
		const float Slide = (1.f - RowIn) * -60.f * RU;
		const float Count = JRRHS::Ease(RowAge / 0.5f);
		const float MidY = RowY + RowH * 0.5f;
		if (Index % 2 == 0)
		{
			DrawRounded(PX + 24.f * RU, RowY + 3.f * RU, PW - 48.f * RU, RowH - 6.f * RU, 18.f * RU, FLinearColor(1.f, 1.f, 1.f, 0.04f * Alpha));
		}
		IconAt(Row.Icon, PX + 58.f * RU + Slide, MidY, 38.f * RU * (RowAge < 0.2f ? 0.6f + 0.4f * RowIn : 1.f), Alpha);
		TextMid(Row.Label, PX + 90.f * RU + Slide, MidY, 23.f * RU, JRRHS::Fade(JRRHS::Soft, Alpha), 0, false);
		FString ValueStr;
		if (Row.bFloat)
		{
			ValueStr = FString::Printf(TEXT("x%.2f"), FMath::Lerp(0.f, Row.FloatValue, Count));
		}
		else
		{
			ValueStr = Row.Prefix + Fmt(FMath::FloorToInt64(static_cast<double>(Row.Value) * Count + 0.5)) + Row.Suffix;
		}
		const float ValueRight = PX + PW - 40.f * RU;
		const float VW = TextMid(ValueStr, ValueRight, MidY, 26.f * RU * (RowAge < 0.25f ? 1.f + 0.2f * (1.f - RowAge / 0.25f) : 1.f),
			JRRHS::Fade(Row.Color, Alpha), 2);
		if (Index == 1 && R.bNewRecord && RowAge > 0.4f)
		{
			IconPill(TEXT("PillLavender"), TEXT("R_Trophy"), TEXT("RECORDE!"), ValueRight - VW - 90.f * RU, RowY + 2.f * RU, 40.f * RU, 18.f * RU, JRRHS::Gold,
				Alpha, 1.f + 0.08f * JRRHS::Pulse(RNow, 7.f));
		}
		RowY += RowH;
	}

	// FICOU COM (grande, dourado) e a carteira sobe junto
	const float FinalAge = AgeNow - FinalAt;
	if (FinalAge >= 0.f)
	{
		if (bWalletHeld)
		{
			bWalletHeld = false; // a carteira começa a contar
			PlayUi(TEXT("UI.Objective"));
			SpawnCoins(FVector2D(Canvas->ClipX * 0.5f, RowY + 50.f * RU), WalletCoinPos, 6);
		}
		const float FinalIn = JRRHS::EaseBack(FinalAge / 0.35f);
		const float Count = JRRHS::Ease(FinalAge / 0.7f);
		const float MidY = RowY + 52.f * RU;
		if (UTexture2D* GlowTex = HudTex(TEXT("Glow")))
		{
			const float G = 260.f * RU;
			DrawTex(GlowTex, Canvas->ClipX * 0.5f - G, MidY - G * 0.3f, 2.f * G, G * 0.6f,
				JRRHS::Fade(JRRHS::Gold, (0.35f + 0.15f * JRRHS::Pulse(RNow, 4.f)) * FMath::Min(1.f, FinalAge / 0.2f)), FVector2D(0.f, 0.f),
				FVector2D(1.f, 1.f), true);
		}
		const FString KeptStr = FString::Printf(TEXT("FICOU COM  +%s"), *Fmt(FMath::FloorToInt64(static_cast<double>(R.CreditsKept) * Count + 0.5)));
		IconPill(TEXT("PillNavy"), TEXT("R_Coins"), KeptStr, Canvas->ClipX * 0.5f, MidY - 34.f * RU, 68.f * RU, 34.f * RU, JRRHS::Gold, 1.f,
			FMath::Max(0.2f, FinalIn));
	}
	if (AgeNow > FinalAt + 0.5f)
	{
		const float HintY = PY + PH - 30.f * RU;
		float HX = Canvas->ClipX * 0.5f - 90.f * RU;
		HX += DrawKeyCap(TEXT("ENTER"), HX, HintY - 15.f * RU, 30.f * RU) + 10.f * RU;
		TextMid(TEXT("continuar"), HX, HintY, 20.f * RU, JRRHS::Fade(JRRHS::Soft, 0.6f + 0.4f * JRRHS::Pulse(RNow, 3.f)), 0, false);
	}
}

// ====================================================================== principal

void AJRRemapHUD::DrawHUD()
{
	Super::DrawHUD();
	if (!Canvas || !PlayerOwner)
	{
		return;
	}
	// relógio real: nas cartas o jogo fica com dilatação 0,0001
	RNow = FPlatformTime::Seconds();
	RDelta = RLast < 0.0 ? 0.f : FMath::Clamp(static_cast<float>(RNow - RLast), 0.f, 0.1f);
	RLast = RNow;
	RU = Canvas->ClipY / 1080.f;
	RK = RU * HudScale;

	const bool bArena = AJRArenaDirector::FindInWorld(this) != nullptr;
	if (bArena)
	{
		WatchRun();
		DrawRunPanel();
		DrawShipMarker();
		DrawPickupLabels();
		DrawFloaters();
		DrawCenterBanner();
		DrawCards();
	}
	else if (DrawTitleScreen())
	{
		return;
	}
	else
	{
		DrawNpcNames();
		if (!ShopKeeper.IsValid())
		{
			DrawWallet();
		}
		if (bReportOpen)
		{
			DrawReport();
		}
		else if (ShopKeeper.IsValid())
		{
			DrawShop();
		}
		DrawFloaters();
		DrawCenterBanner();
	}
}

// ====================================================================== console

void AJRRemapHUD::JRCreditos(int32 Amount)
{
	if (UJREconomySubsystem* Economy = GetGameInstance()->GetSubsystem<UJREconomySubsystem>())
	{
		Economy->AddCredits(Amount);
	}
}

void AJRRemapHUD::JRArena(int32 InLevel)
{
	if (UJRRunSubsystem* Run = GetGameInstance()->GetSubsystem<UJRRunSubsystem>())
	{
		Run->StartRun(FMath::Max(1, InLevel));
		UGameplayStatics::OpenLevel(this, FName(FJRRemapRules::ArenaMap));
	}
}

void AJRRemapHUD::JRCristais(int32 Amount)
{
	if (UJREconomySubsystem* Economy = GetGameInstance()->GetSubsystem<UJREconomySubsystem>())
	{
		Economy->AddCrystals(Amount);
	}
}

void AJRRemapHUD::JRRecorde(int32 Waves)
{
	UJREconomySubsystem* Economy = GetGameInstance()->GetSubsystem<UJREconomySubsystem>();
	if (!Economy)
	{
		return;
	}
	Economy->RecordRun(Waves);
	Economy->Save();
	for (TActorIterator<AJRDistrictGate> It(GetWorld()); It; ++It)
	{
		if (It->IsUnlocked())
		{
			It->ForceOpen();
		}
	}
}

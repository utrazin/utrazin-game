// Copyright utrazin. All Rights Reserved.

#include "UI/JRIntroHUD.h"
#include "CanvasItem.h"
#include "Cinematics/JRIntroDirector.h"
#include "Engine/Canvas.h"
#include "Engine/Engine.h"
#include "Engine/Font.h"
#include "Engine/FontFace.h"
#include "Engine/Texture2D.h"
#include "Engine/World.h"
#include "Kismet/GameplayStatics.h"
#include "UI/JRHudArt.h"

namespace
{
	// Mesmos arquivos e cores do HUD v2 (JRHUD.cpp / setup_hud_v2.py).
	const TCHAR* const IntroFontBoldPath = TEXT("/Game/UI/HUD/V2/Fonts/FF_HUD2_FredokaBold.FF_HUD2_FredokaBold");
	const TCHAR* const IntroFontSemiBoldPath = TEXT("/Game/UI/HUD/V2/Fonts/FF_HUD2_FredokaSemiBold.FF_HUD2_FredokaSemiBold");
	const FLinearColor IntroInk = FLinearColor(FColor(12, 13, 32));
	const FLinearColor IntroNavy = FLinearColor(FColor(24, 30, 62));
	const FLinearColor IntroText1 = FLinearColor(FColor(250, 250, 255));
	const FLinearColor IntroSoft = FLinearColor(FColor(196, 206, 236));
	const FLinearColor IntroCyan = FLinearColor(FColor(90, 240, 246));
	const FLinearColor IntroYellow = FLinearColor(FColor(255, 214, 92));

	FLinearColor WithAlpha(FLinearColor In, float Alpha)
	{
		In.A *= Alpha;
		return In;
	}

	float EaseInOut(float T)
	{
		const float C = FMath::Clamp(T, 0.f, 1.f);
		return C * C * (3.f - 2.f * C);
	}
}

void AJRIntroHUD::DrawHUD()
{
	if (!CachedDirector.IsValid() && !bSearchedDirector)
	{
		bSearchedDirector = true;
		CachedDirector = AJRIntroDirector::FindInWorld(GetWorld());
	}
	const AJRIntroDirector* Director = CachedDirector.Get();
	const bool bIntro = Director && Director->IsRunning();
	if (!bIntro || !Director->GetOverlay().bHideGameHud)
	{
		Super::DrawHUD();
	}
	if (bIntro && Canvas)
	{
		DrawIntroOverlay(Director->GetOverlay());
	}
	else
	{
		MenuRects.Reset();
	}
}

int32 AJRIntroHUD::HitTestMenu(const FVector2D& ScreenPos) const
{
	for (int32 Index = 0; Index < MenuRects.Num(); ++Index)
	{
		if (MenuRects[Index].IsInside(ScreenPos))
		{
			return Index;
		}
	}
	return INDEX_NONE;
}

void AJRIntroHUD::JRAbertura()
{
	AJRIntroDirector::SetIntroSeen(this, false);
	UGameplayStatics::OpenLevel(this, FName(*UGameplayStatics::GetCurrentLevelName(this)));
}

// ====================================================================== desenho

void AJRIntroHUD::DrawIntroOverlay(const FJRIntroOverlay& Ov)
{
	const float ScreenW = Canvas->ClipX;
	const float ScreenH = Canvas->ClipY;
	const float Ui = ScreenH / 1080.f;

	// Faixas de cinema.
	if (Ov.Letterbox > 0.f)
	{
		const float Bar = ScreenH * 0.11f * EaseInOut(Ov.Letterbox);
		IntroRect(0.f, 0.f, ScreenW, Bar, FLinearColor::Black);
		IntroRect(0.f, ScreenH - Bar, ScreenW, Bar, FLinearColor::Black);
	}

	if (Ov.bMenu)
	{
		DrawStartMenu(Ov, Ui);
	}
	else
	{
		MenuRects.Reset();
	}

	// Legenda (rádio da nave).
	if (Ov.SubtitleAlpha > 0.f && !Ov.Subtitle.IsEmpty())
	{
		const float Size = 34.f * Ui;
		const FVector2D TextSize = IntroMeasure(Ov.Subtitle, Size, true);
		const float PillH = Size * 1.7f;
		const float PillW = TextSize.X + 90.f * Ui;
		const float PillY = ScreenH * 0.76f;
		IntroPill(false, (ScreenW - PillW) * 0.5f, PillY, PillW, PillH, WithAlpha(FLinearColor::White, Ov.SubtitleAlpha * 0.95f));
		IntroText(Ov.Subtitle, ScreenW * 0.5f, PillY + (PillH - TextSize.Y) * 0.5f, Size, WithAlpha(IntroYellow, Ov.SubtitleAlpha), true, 0.5f);
	}

	// Segure para pular.
	if (Ov.bSkipHint)
	{
		const float Size = 22.f * Ui;
		const FString Hint = TEXT("Segure ESPAÇO ou A para pular");
		const FVector2D TextSize = IntroMeasure(Hint, Size, false);
		const float Right = ScreenW - 40.f * Ui;
		const float Y = ScreenH - 40.f * Ui - TextSize.Y - 12.f * Ui;
		const float Alpha = 0.55f + 0.45f * Ov.SkipProgress;
		IntroText(Hint, Right, Y, Size, WithAlpha(IntroSoft, Alpha), false, 1.f);
		const float BarW = TextSize.X;
		const float BarY = Y + TextSize.Y + 6.f * Ui;
		IntroRect(Right - BarW, BarY, BarW, 5.f * Ui, WithAlpha(IntroNavy, 0.8f));
		if (Ov.SkipProgress > 0.f)
		{
			IntroRect(Right - BarW, BarY, BarW * Ov.SkipProgress, 5.f * Ui, IntroCyan);
		}
	}

	// Clarão branco do impacto e tela preta das transições (por cima de tudo).
	if (Ov.White > 0.f)
	{
		IntroRect(0.f, 0.f, ScreenW, ScreenH, FLinearColor(1.f, 1.f, 1.f, Ov.White));
	}
	if (Ov.Black > 0.f)
	{
		IntroRect(0.f, 0.f, ScreenW, ScreenH, FLinearColor(0.f, 0.f, 0.f, Ov.Black));
	}
}

void AJRIntroHUD::DrawStartMenu(const FJRIntroOverlay& Ov, float Ui)
{
	const float ScreenW = Canvas->ClipX;
	const float ScreenH = Canvas->ClipY;
	// Véu azul-escuro para o texto ler bem sobre o céu.
	IntroRect(0.f, 0.f, ScreenW, ScreenH, WithAlpha(IntroInk, 0.35f));
	IntroRect(0.f, ScreenH * 0.62f, ScreenW, ScreenH * 0.38f, WithAlpha(IntroInk, 0.25f));

	const float TitleSize = 112.f * Ui;
	IntroText(TEXT("JOGO DE RESGATE"), ScreenW * 0.5f, ScreenH * 0.20f, TitleSize, IntroYellow, true, 0.5f);
	IntroText(TEXT("Fase 1: Vale dos Zumbis"), ScreenW * 0.5f, ScreenH * 0.20f + TitleSize * 1.15f, 32.f * Ui, IntroSoft, false, 0.5f);

	MenuRects.Reset();
	const float ItemW = 430.f * Ui;
	const float ItemH = 78.f * Ui;
	const float Gap = 22.f * Ui;
	const float StartY = ScreenH * 0.50f;
	for (int32 Index = 0; Index < Ov.MenuItems.Num(); ++Index)
	{
		const bool bSelected = Index == Ov.MenuIndex;
		const float Grow = bSelected ? 1.06f : 1.f;
		const float W = ItemW * Grow;
		const float H = ItemH * Grow;
		const float X = (ScreenW - W) * 0.5f;
		const float Y = StartY + Index * (ItemH + Gap) - (H - ItemH) * 0.5f;
		IntroPill(bSelected, X, Y, W, H, FLinearColor::White);
		const float Size = 40.f * Ui * Grow;
		const FVector2D TextSize = IntroMeasure(Ov.MenuItems[Index], Size, true);
		IntroText(Ov.MenuItems[Index], ScreenW * 0.5f, Y + (H - TextSize.Y) * 0.5f, Size, bSelected ? IntroInk : IntroText1, true, 0.5f);
		MenuRects.Add(FBox2D(FVector2D(X, Y), FVector2D(X + W, Y + H)));
	}
	IntroText(TEXT("W/S ou setas: escolher     Enter, Espaço ou A: confirmar     Mouse: clique"), ScreenW * 0.5f,
		ScreenH - 70.f * Ui, 22.f * Ui, WithAlpha(IntroSoft, 0.85f), false, 0.5f);
}

// ====================================================================== peças

void AJRIntroHUD::IntroRect(float X, float Y, float W, float H, const FLinearColor& Color)
{
	if (W <= 0.f || H <= 0.f)
	{
		return;
	}
	FCanvasTileItem Tile(FVector2D(X, Y), FVector2D(W, H), Color);
	Tile.BlendMode = SE_BLEND_Translucent;
	Canvas->DrawItem(Tile);
}

UTexture2D* AJRIntroHUD::IntroTex(const TCHAR* Name)
{
	const FString Key(Name);
	if (const TObjectPtr<UTexture2D>* Found = IntroTextures.Find(Key))
	{
		return Found->Get();
	}
	const FString Path = FString::Printf(TEXT("/Game/UI/HUD/V2/%s.%s"), Name, Name);
	UTexture2D* Tex = LoadObject<UTexture2D>(nullptr, *Path, nullptr, LOAD_NoWarn | LOAD_Quiet);
	IntroTextures.Add(Key, Tex);
	return Tex;
}

void AJRIntroHUD::IntroPill(bool bTeal, float X, float Y, float W, float H, const FLinearColor& Color)
{
	// Pílula em 3 partes (pontas + meio esticado), como o DrawPill do HUD v2.
	const JRHudArt::FPill& Art = bTeal ? JRHudArt::PillTeal : JRHudArt::PillNavy;
	UTexture2D* Tex = IntroTex(bTeal ? TEXT("T_HUD2_PillTeal") : TEXT("T_HUD2_PillNavy"));
	if (!Tex || !Tex->GetResource())
	{
		IntroRect(X, Y, W, H, WithAlpha(bTeal ? IntroCyan : IntroNavy, Color.A * 0.92f));
		return;
	}
	const float K = H / Art.TexH;
	const float CapL = Art.CapL * K;
	const float CapR = Art.CapR * K;
	const float MidW = FMath::Max(0.f, W - CapL - CapR);
	const float U1 = Art.CapL / Art.TexW;
	const float U2 = (Art.CapL + Art.Mid) / Art.TexW;
	auto Part = [this, Tex, &Color, Y, H](float PartX, float PartW, float UA, float UB)
	{
		FCanvasTileItem Tile(FVector2D(PartX, Y), Tex->GetResource(), FVector2D(PartW, H), FVector2D(UA, 0.f), FVector2D(UB, 1.f), Color);
		Tile.BlendMode = SE_BLEND_Translucent;
		Canvas->DrawItem(Tile);
	};
	Part(X, CapL, 0.f, U1);
	Part(X + CapL, MidW, U1 + 0.2f / Art.TexW, U2 - 0.2f / Art.TexW);
	Part(X + CapL + MidW, CapR, U2, 1.f);
}

UFont* AJRIntroHUD::IntroFont(bool bBold, float PixelSize, float& OutScale)
{
	OutScale = 1.f;
	if (!bSearchedIntroFonts)
	{
		bSearchedIntroFonts = true;
		auto FaceFrom = [](const TCHAR* FacePath) -> UFontFace*
		{
			if (UFontFace* Found = LoadObject<UFontFace>(nullptr, FacePath, nullptr, LOAD_NoWarn | LOAD_Quiet))
			{
				return Found;
			}
			if (const UFont* AsFont = LoadObject<UFont>(nullptr, FacePath, nullptr, LOAD_NoWarn | LOAD_Quiet))
			{
				for (const FTypefaceEntry& Typeface : AsFont->CompositeFont.DefaultTypeface.Fonts)
				{
					if (const UFontFace* Inner = Cast<const UFontFace>(Typeface.Font.GetFontFaceAsset()))
					{
						return const_cast<UFontFace*>(Inner);
					}
				}
			}
			return nullptr;
		};
		IntroFaceBold = FaceFrom(IntroFontBoldPath);
		IntroFaceSemiBold = FaceFrom(IntroFontSemiBoldPath);
	}
	UFontFace* Face = bBold ? IntroFaceBold.Get() : (IntroFaceSemiBold ? IntroFaceSemiBold.Get() : IntroFaceBold.Get());
	if (!Face)
	{
		// sem o setup_hud_v2.py: fonte da Unreal, aumentada
		UFont* Fallback = GEngine ? GEngine->GetLargeFont() : nullptr;
		OutScale = PixelSize / 24.f;
		return Fallback;
	}
	const int32 Points = FMath::Clamp(FMath::RoundToInt(PixelSize * 0.75f), 6, 220);
	const int32 CacheKey = Points * 2 + (bBold ? 1 : 0);
	if (const TObjectPtr<UFont>* Found = IntroFonts.Find(CacheKey))
	{
		return Found->Get();
	}
	UFont* NewFont = NewObject<UFont>(this);
	NewFont->FontCacheType = EFontCacheType::Runtime;
	NewFont->LegacyFontSize = static_cast<decltype(NewFont->LegacyFontSize)>(Points);
	FTypefaceEntry& Typeface = NewFont->CompositeFont.DefaultTypeface.Fonts.AddDefaulted_GetRef();
	Typeface.Name = TEXT("Regular");
	Typeface.Font = FFontData(Face);
	IntroFonts.Add(CacheKey, NewFont);
	return NewFont;
}

FVector2D AJRIntroHUD::IntroMeasure(const FString& Text, float PixelSize, bool bBold)
{
	float FontScale = 1.f;
	UFont* Font = IntroFont(bBold, PixelSize, FontScale);
	if (!Font || !Canvas || Text.IsEmpty())
	{
		return FVector2D::ZeroVector;
	}
	float XL = 0.f;
	float YL = 0.f;
	Canvas->TextSize(Font, Text, XL, YL, FontScale, FontScale);
	return FVector2D(XL, YL);
}

void AJRIntroHUD::IntroText(const FString& Text, float X, float Y, float PixelSize, const FLinearColor& Color, bool bBold, float AlignX)
{
	float FontScale = 1.f;
	UFont* Font = IntroFont(bBold, PixelSize, FontScale);
	if (!Font || Text.IsEmpty() || Color.A <= 0.f)
	{
		return;
	}
	const FVector2D TextSize = IntroMeasure(Text, PixelSize, bBold);
	FCanvasTextItem Item(FVector2D(X - TextSize.X * AlignX, Y), FText::FromString(Text), Font, Color);
	Item.Scale = FVector2D(FontScale, FontScale);
	Item.EnableShadow(FLinearColor(0.f, 0.f, 0.02f, 0.65f * Color.A), FVector2D(2.f, 2.f));
	Item.BlendMode = SE_BLEND_Translucent;
	Canvas->DrawItem(Item);
}

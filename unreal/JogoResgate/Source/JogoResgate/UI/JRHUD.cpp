// Copyright utrazin. All Rights Reserved.

#include "UI/JRHUD.h"
#include "Audio/JRAudio.h" // [Áudio/A-061]
#include "AI/JREnemyCharacter.h"
#include "AI/JRHordeDirector.h"
#include "Camera/PlayerCameraManager.h"
#include "CanvasItem.h"
#include "Characters/JRCharacter.h"
#include "Characters/JRItemWheel.h"
#include "Combat/JRHealthComponent.h"
#include "Combat/JRInventoryComponent.h"
#include "Combat/JRWeaponComponent.h"
#include "Engine/Canvas.h"
#include "Engine/Engine.h"
#include "Engine/Font.h"
#include "Engine/FontFace.h"
#include "Engine/Texture2D.h"
#include "EngineUtils.h"
#include "Fonts/CompositeFont.h"
#include "FX/JRDamageFXComponent.h"
#include "FX/JRGameFeel.h" // [A-073] jr.Feel.ReduceFlash
#include "GameFramework/PlayerController.h"
#include "Gameplay/JRBlockingGate.h"
#include "Gameplay/JRPickup.h"
#include "Interactions/JRInteractable.h"
#include "Interactions/JRInteractionComponent.h"
#include "Interactions/JRLootChest.h"
#include "Interactions/JRRescueTarget.h"
#include "Levels/JRCheckpoint.h"
#include "Levels/JRLevelDefinition.h"
#include "UI/JRHudArt.h"
#include "Vehicles/JRVehicleDamageComponent.h"
#include "Vehicles/JRVehiclePawn.h"

// ======================================================================
// HUD v2 (A-059): peças recortadas das referências do usuário (tools/pipeline/make_hud_v2.py),
// importadas em /Game/UI/HUD/V2 por tools/unreal/setup_hud_v2.py.
// Medidas em "pixels da referência" (JRHudArt.h) vezes K = escala da tela (altura / 1080) x HudScale.
// ======================================================================

namespace
{
	const TCHAR* const HudTexFolder = TEXT("/Game/UI/HUD/V2/");
	const TCHAR* const FontBoldPath = TEXT("/Game/UI/HUD/V2/Fonts/FF_HUD2_FredokaBold.FF_HUD2_FredokaBold");
	const TCHAR* const FontSemiBoldPath = TEXT("/Game/UI/HUD/V2/Fonts/FF_HUD2_FredokaSemiBold.FF_HUD2_FredokaSemiBold");

	// Paleta das referências (sRGB -> linear pelo construtor de FColor).
	const FLinearColor InkColor = FLinearColor(FColor(12, 13, 32));
	const FLinearColor NavyColor = FLinearColor(FColor(24, 30, 62));
	const FLinearColor TextColor = FLinearColor(FColor(250, 250, 255));
	const FLinearColor SoftTextColor = FLinearColor(FColor(196, 206, 236));
	const FLinearColor CyanText = FLinearColor(FColor(90, 240, 246));
	const FLinearColor LockedText = FLinearColor(FColor(150, 140, 180));
	const FLinearColor YellowText = FLinearColor(FColor(255, 214, 92));
	const FLinearColor FuryColor = FLinearColor(FColor(190, 90, 255));

	FLinearColor Faded(FLinearColor In, float Alpha)
	{
		In.A *= Alpha;
		return In;
	}

	/** Ponto de um painel (pixels da referência) na tela. */
	FVector2D PanelPoint(const FVector2D& Origin, float K, float RefX, float RefY)
	{
		return Origin + FVector2D(RefX, RefY) * K;
	}

	float EaseOut(float T)
	{
		const float C = FMath::Clamp(T, 0.f, 1.f);
		return 1.f - (1.f - C) * (1.f - C) * (1.f - C);
	}
}

// ====================================================================== quadro

void AJRHUD::DrawHUD()
{
	Super::DrawHUD();
	if (!Canvas || !PlayerOwner)
	{
		return;
	}
	S = Canvas->ClipY / 1080.f;
	const double RealNow = GetWorld()->GetRealTimeSeconds();
	const float RealDelta = LastHudRealTime < 0.0 ? 0.f : FMath::Clamp(static_cast<float>(RealNow - LastHudRealTime), 0.f, 0.1f);
	LastHudRealTime = RealNow;
	APawn* Pawn = PlayerOwner->GetPawn();

	const UJRObjectiveSubsystem* Objective = GetWorld()->GetSubsystem<UJRObjectiveSubsystem>();
	const EJRLevelStage Stage = Objective ? Objective->GetStage() : EJRLevelStage::NotStarted;
	const bool bDriving = Pawn && Pawn->IsA<AJRVehiclePawn>();

	AJRCharacter* Hero = Cast<AJRCharacter>(Pawn);
	const bool bModalOpen = IsHudModalOpen(); // [A-083] loja/cartas/relatório da AJRRemapHUD
	if (Hero)
	{
		LastIntegrity = -1.f;
		DrawHeroHud(Hero);
		if (!bModalOpen)
		{
			DrawWeaponCard(Hero, RealDelta); // [A-083] a lista da loja ocupa o lado direito
			DrawInteractionPrompt(Hero);
		}
	}
	else if (AJRVehiclePawn* Vehicle = Cast<AJRVehiclePawn>(Pawn))
	{
		LastHealth = -1.f;
		DrawVehicleHud(Vehicle);
	}
	DrawToasts();

	UpdateTasks(Pawn, Stage); // [A-064]
	if (!bModalOpen)
	{
		DrawObjective(Stage, bDriving);
	}

	// ---- Guia: marcador no mundo, minimapa e mapa grande
	if (Pawn && !bModalOpen)
	{
		AActor* Target = GuideTarget(Stage); // [A-064] tarefa atual primeiro
		if (bBigMap && UseLevelMinimapImage()) // [A-083] radar não tem mapa grande
		{
			DrawBigMapView(Pawn, Target);
		}
		else
		{
			DrawWorldMarker(Target, Pawn);
			DrawMinimap(Pawn, bDriving, Target);
		}
	}

	// ---- Roda de itens (Tab) por cima de tudo
	if (Hero && Hero->IsItemWheelOpen())
	{
		Hero->UpdateItemWheelInput(); // Q/E, roda do mouse, RB: troca de aba (A-059)
		if (Hero->IsItemWheelOpen())
		{
			DrawItemWheel(Hero);
		}
	}

	// ---- Flash de dano
	const double Since = GetWorld()->GetTimeSeconds() - DamageFlashStart;
	if (Since < DamageFlashDuration)
	{
		// [A-073] acessibilidade: jr.Feel.ReduceFlash 1 deixa o clarão vermelho bem mais fraco
		const float A = (JRFeel::ReduceFlash() ? 0.1f : 0.30f) * (1.f - static_cast<float>(Since) / DamageFlashDuration);
		FCanvasTileItem Flash(FVector2D::ZeroVector, FVector2D(Canvas->ClipX, Canvas->ClipY), FLinearColor(0.8f, 0.f, 0.f, A));
		Flash.BlendMode = SE_BLEND_Translucent;
		Canvas->DrawItem(Flash);
	}

	// ---- Telas de fim
	if (Stage == EJRLevelStage::Completed)
	{
		DrawBigBanner(TEXT("RESGATE CONCLUÍDO!"), TEXT("Fase concluída"), AccentColor);
	}
	else if (Stage == EJRLevelStage::Failed)
	{
		DrawBigBanner(TEXT("VOCÊ CAIU"), TEXT("Voltando ao checkpoint..."), HealthColor);
	}
}

// ====================================================================== peças básicas

UTexture2D* AJRHUD::HudTex(const FString& Name)
{
	if (TObjectPtr<UTexture2D>* Found = HudTextures.Find(Name))
	{
		return Found->Get();
	}
	const FString Asset = FString(TEXT("T_HUD2_")) + Name;
	const FString Path = FString(HudTexFolder) + Asset + TEXT(".") + Asset;
	UTexture2D* Tex = LoadObject<UTexture2D>(nullptr, *Path, nullptr, LOAD_NoWarn | LOAD_Quiet);
	HudTextures.Add(Name, Tex);
	return Tex;
}

void AJRHUD::DrawTex(UTexture2D* Tex, float X, float Y, float W, float H, const FLinearColor& Color, const FVector2D& UV0,
	const FVector2D& UV1, bool bAdditive)
{
	if (!Tex || !Tex->GetResource() || W <= 0.f || H <= 0.f || Color.A <= 0.001f)
	{
		return;
	}
	// [A-086] O "aditivo" da Canvas soma o RGB e ignora o alfa: as texturas de brilho são brancas com a forma no
	// alfa, e viravam QUADRADOS brancos/roxos (cartas, ícones). Agora: mistura pelo alfa, com a cor um pouco mais
	// forte para continuar parecendo luz.
	FLinearColor TileColor = Color;
	if (bAdditive)
	{
		TileColor = FLinearColor(FMath::Min(Color.R * 1.25f, 1.f), FMath::Min(Color.G * 1.25f, 1.f), FMath::Min(Color.B * 1.25f, 1.f), Color.A);
	}
	FCanvasTileItem Tile(FVector2D(X, Y), Tex->GetResource(), FVector2D(W, H), UV0, UV1, TileColor);
	Tile.BlendMode = SE_BLEND_Translucent;
	Canvas->DrawItem(Tile);
}

float AJRHUD::PillWidthFor(const FString& TexName, float H, float TextW) const
{
	const JRHudArt::FPill& P = TexName == TEXT("PillTeal") ? JRHudArt::PillTeal
		: (TexName == TEXT("PillLavender") ? JRHudArt::PillLavender : JRHudArt::PillNavy);
	const float Unit = H / P.TexH;
	return TextW + (P.CapL + P.CapR) * Unit * 0.62f;
}

void AJRHUD::DrawPill(const FString& TexName, float X, float Y, float W, float H, const FLinearColor& Color)
{
	UTexture2D* Tex = HudTex(TexName);
	const JRHudArt::FPill& P = TexName == TEXT("PillTeal") ? JRHudArt::PillTeal
		: (TexName == TEXT("PillLavender") ? JRHudArt::PillLavender : JRHudArt::PillNavy);
	if (!Tex)
	{
		DrawRounded(X, Y, W, H, H * 0.5f, Faded(NavyColor, Color.A * 0.9f));
		return;
	}
	const float Unit = H / P.TexH;
	float CapL = P.CapL * Unit;
	float CapR = P.CapR * Unit;
	if (CapL + CapR > W)
	{
		const float Shrink = W / (CapL + CapR);
		CapL *= Shrink;
		CapR *= Shrink;
	}
	const float MidW = FMath::Max(0.f, W - CapL - CapR);
	const float U1 = P.CapL / P.TexW;
	const float U2 = (P.CapL + P.Mid) / P.TexW;
	DrawTex(Tex, X, Y, CapL, H, Color, FVector2D(0.f, 0.f), FVector2D(U1, 1.f));
	DrawTex(Tex, X + CapL, Y, MidW, H, Color, FVector2D(U1 + 0.2f / P.TexW, 0.f), FVector2D(U2 - 0.2f / P.TexW, 1.f));
	DrawTex(Tex, X + CapL + MidW, Y, CapR, H, Color, FVector2D(U2, 0.f), FVector2D(1.f, 1.f));
}

UFont* AJRHUD::HudFont(bool bBold, float PixelSize)
{
	if (!bSearchedFonts)
	{
		bSearchedFonts = true;
		auto FaceFrom = [](const TCHAR* FacePath) -> UFontFace*
		{
			if (UFontFace* Found = LoadObject<UFontFace>(nullptr, FacePath, nullptr, LOAD_NoWarn | LOAD_Quiet))
			{
				return Found;
			}
			// A importação pode ter criado uma UFont com a Font Face dentro: usa a face dela.
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
		FaceBold = FaceFrom(FontBoldPath);
		FaceSemiBold = FaceFrom(FontSemiBoldPath);
	}
	UFontFace* Face = bBold ? FaceBold.Get() : (FaceSemiBold ? FaceSemiBold.Get() : FaceBold.Get());
	if (!Face)
	{
		return GEngine ? GEngine->GetMediumFont() : nullptr; // sem o setup_hud_v2.py: fonte padrão
	}
	// Fonte "Runtime": a Unreal rasteriza no tamanho pedido (nítida em qualquer resolução).
	const int32 Points = FMath::Clamp(FMath::RoundToInt(PixelSize * 0.75f), 6, 220);
	const int32 CacheKey = Points * 2 + (bBold ? 1 : 0);
	if (TObjectPtr<UFont>* Found = FontCache.Find(CacheKey))
	{
		return Found->Get();
	}
	UFont* NewFont = NewObject<UFont>(this);
	NewFont->FontCacheType = EFontCacheType::Runtime;
	NewFont->LegacyFontSize = static_cast<decltype(NewFont->LegacyFontSize)>(Points);
	FTypefaceEntry& Typeface = NewFont->CompositeFont.DefaultTypeface.Fonts.AddDefaulted_GetRef();
	Typeface.Name = TEXT("Regular");
	Typeface.Font = FFontData(Face);
	FontCache.Add(CacheKey, NewFont);
	return NewFont;
}

FVector2D AJRHUD::MeasureText(const FString& Text, bool bBold, float PixelSize)
{
	UFont* Font = HudFont(bBold, PixelSize);
	if (!Font || !Canvas || Text.IsEmpty())
	{
		return FVector2D::ZeroVector;
	}
	const float FontScale = Font->FontCacheType == EFontCacheType::Runtime ? 1.f : PixelSize / 22.f;
	float TextW = 0.f;
	float TextH = 0.f;
	Canvas->TextSize(Font, Text, TextW, TextH, FontScale, FontScale);
	return FVector2D(TextW, TextH);
}

float AJRHUD::DrawHudText(const FString& Text, float X, float Y, float PixelSize, const FLinearColor& Color, int32 Align, bool bBold,
	float Outline)
{
	UFont* Font = HudFont(bBold, PixelSize);
	if (!Font || !Canvas || Text.IsEmpty() || Color.A <= 0.01f)
	{
		return 0.f;
	}
	const float FontScale = Font->FontCacheType == EFontCacheType::Runtime ? 1.f : PixelSize / 22.f;
	float TextW = 0.f;
	float TextH = 0.f;
	Canvas->TextSize(Font, Text, TextW, TextH, FontScale, FontScale);
	const float DrawX = Align == 1 ? X - TextW * 0.5f : (Align == 2 ? X - TextW : X);
	const float Thick = Outline >= 0.f ? Outline : FMath::Max(1.f, PixelSize * 0.085f);
	FCanvasTextItem Item(FVector2D(DrawX, Y), FText::FromString(Text), Font, Faded(InkColor, Color.A * 0.55f));
	Item.Scale = FVector2D(FontScale, FontScale);
	Item.BlendMode = SE_BLEND_Translucent;
	if (Thick > 0.f)
	{
		// Sombra embaixo e contorno escuro em volta (o "relevo" dos textos das referências).
		Item.Position = FVector2D(DrawX, Y + Thick * 1.7f);
		Canvas->DrawItem(Item);
		Item.SetColor(Faded(InkColor, Color.A * 0.95f));
		const int32 Steps = Thick > 2.5f ? 12 : 8;
		for (int32 Step = 0; Step < Steps; ++Step)
		{
			const float Ang = 2.f * UE_PI * static_cast<float>(Step) / static_cast<float>(Steps);
			Item.Position = FVector2D(DrawX + FMath::Cos(Ang) * Thick, Y + FMath::Sin(Ang) * Thick);
			Canvas->DrawItem(Item);
		}
	}
	Item.SetColor(Color);
	Item.Position = FVector2D(DrawX, Y);
	Canvas->DrawItem(Item);
	return TextW;
}

float AJRHUD::DrawHudTextFit(const FString& Text, float X, float Y, float PixelSize, float MaxW, const FLinearColor& Color, int32 Align,
	bool bBold)
{
	float Size = PixelSize;
	const float Width = MeasureText(Text, bBold, Size).X;
	if (MaxW > 0.f && Width > MaxW)
	{
		Size = FMath::Max(8.f, Size * MaxW / Width);
	}
	// Mantém a linha centrada na mesma altura ao encolher.
	DrawHudText(Text, X, Y + (PixelSize - Size) * 0.45f, Size, Color, Align, bBold);
	return Size;
}

TArray<FString> AJRHUD::WrapText(const FString& Text, bool bBold, float PixelSize, float MaxW)
{
	TArray<FString> Lines;
	TArray<FString> Paragraphs;
	Text.ParseIntoArray(Paragraphs, TEXT("\n"), false);
	for (const FString& Paragraph : Paragraphs)
	{
		TArray<FString> Words;
		Paragraph.ParseIntoArrayWS(Words);
		FString Line;
		for (const FString& Word : Words)
		{
			const FString Try = Line.IsEmpty() ? Word : Line + TEXT(" ") + Word;
			if (!Line.IsEmpty() && MeasureText(Try, bBold, PixelSize).X > MaxW)
			{
				Lines.Add(Line);
				Line = Word;
			}
			else
			{
				Line = Try;
			}
		}
		Lines.Add(Line);
	}
	return Lines;
}

float AJRHUD::DrawKeyCap(const FString& Key, float X, float Y, float H)
{
	const float TextSize = H * (Key.Len() > 1 ? 0.46f : 0.56f);
	const float TextW = MeasureText(Key, true, TextSize).X;
	const float W = FMath::Max(H, TextW + H * 0.55f);
	UTexture2D* Tex = HudTex(TEXT("Key"));
	if (Tex)
	{
		// 3 fatias na horizontal para teclas largas (TAB, SHIFT).
		const float Cap = H * 0.36f;
		DrawTex(Tex, X, Y, Cap, H, FLinearColor::White, FVector2D(0.f, 0.f), FVector2D(0.36f, 1.f));
		DrawTex(Tex, X + Cap, Y, W - 2.f * Cap, H, FLinearColor::White, FVector2D(0.36f, 0.f), FVector2D(0.64f, 1.f));
		DrawTex(Tex, X + W - Cap, Y, Cap, H, FLinearColor::White, FVector2D(0.64f, 0.f), FVector2D(1.f, 1.f));
	}
	else
	{
		DrawRounded(X, Y, W, H, H * 0.25f, FLinearColor(0.9f, 1.f, 1.f, 1.f));
	}
	const float TextH = MeasureText(Key, true, TextSize).Y;
	DrawHudText(Key, X + W * 0.5f, Y + H * 0.40f - TextH * 0.5f, TextSize, InkColor, 1, true, 0.f);
	return W;
}

float AJRHUD::Smooth(FName Key, float Target, float Speed, float DeltaTime)
{
	float& Value = SmoothValues.FindOrAdd(Key, Target);
	Value = FMath::FInterpTo(Value, Target, DeltaTime, Speed);
	return Value;
}

void AJRHUD::DrawRounded(float X, float Y, float W, float H, float R, const FLinearColor& Color)
{
	R = FMath::Min3(R, W * 0.5f, H * 0.5f);
	UTexture2D* Circle = HudTex(TEXT("Circle"));
	auto Rect = [&](float RX, float RY, float RW, float RH)
	{
		if (RW <= 0.f || RH <= 0.f)
		{
			return;
		}
		FCanvasTileItem T(FVector2D(RX, RY), FVector2D(RW, RH), Color);
		T.BlendMode = SE_BLEND_Translucent;
		Canvas->DrawItem(T);
	};
	if (!Circle || !Circle->GetResource() || R < 1.f)
	{
		Rect(X, Y, W, H);
		return;
	}
	Rect(X + R, Y, W - 2.f * R, H);
	Rect(X, Y + R, R, H - 2.f * R);
	Rect(X + W - R, Y + R, R, H - 2.f * R);
	auto Corner = [&](float CX, float CY, float U0, float V0)
	{
		FCanvasTileItem T(FVector2D(CX, CY), Circle->GetResource(), FVector2D(R, R), FVector2D(U0, V0), FVector2D(U0 + 0.5f, V0 + 0.5f), Color);
		T.BlendMode = SE_BLEND_Translucent;
		Canvas->DrawItem(T);
	};
	Corner(X, Y, 0.f, 0.f);
	Corner(X + W - R, Y, 0.5f, 0.f);
	Corner(X, Y + H - R, 0.f, 0.5f);
	Corner(X + W - R, Y + H - R, 0.5f, 0.5f);
}

void AJRHUD::DrawLabel(const FString& Text, float X, float Y, float Scale, const FLinearColor& Color, bool bCenterX)
{
	DrawHudText(Text, X, Y, 18.f * Scale * S, Color, bCenterX ? 1 : 0, true);
}

// ====================================================================== barras dos painéis

void AJRHUD::DrawSegmentBar(const FString& FillTex, const FVector2D& Origin, float K, int32 Which, float Pct, float TrailPct,
	const FLinearColor& Tint)
{
	UTexture2D* Tex = HudTex(FillTex);
	if (!Tex)
	{
		return;
	}
	const JRHudArt::FRect& Bar = Which == 0 ? JRHudArt::BotHeroBarA : JRHudArt::BotHeroBarB;
	const JRHudArt::FBarSegments& Segs = Which == 0 ? JRHudArt::BotHeroBarASegments : JRHudArt::BotHeroBarBSegments;
	const int32 Count = FMath::Max(1, Segs.Num);
	for (int32 SegIndex = 0; SegIndex < Count; ++SegIndex)
	{
		const JRHudArt::FRect& Seg = Segs.Seg[SegIndex];
		const float F0 = static_cast<float>(SegIndex) / static_cast<float>(Count);
		const float F1 = static_cast<float>(SegIndex + 1) / static_cast<float>(Count);
		const float Lit = FMath::Clamp((Pct - F0) / (F1 - F0), 0.f, 1.f);
		const float Ghost = FMath::Clamp((TrailPct - F0) / (F1 - F0), 0.f, 1.f);
		const float Pad = 2.f;
		const float X0 = FMath::Max(Bar.X, Seg.X - Pad);
		const float Y0 = FMath::Max(Bar.Y, Seg.Y - Pad);
		const float X1 = FMath::Min(Bar.X + Bar.W, Seg.X + Seg.W + Pad);
		const float Y1 = FMath::Min(Bar.Y + Bar.H, Seg.Y + Seg.H + Pad);
		const FVector2D UV0((X0 - Bar.X) / Bar.W, (Y0 - Bar.Y) / Bar.H);
		const FVector2D UV1((X1 - Bar.X) / Bar.W, (Y1 - Bar.Y) / Bar.H);
		const FVector2D P0 = PanelPoint(Origin, K, X0, Y0);
		const float W = (X1 - X0) * K;
		const float H = (Y1 - Y0) * K;
		if (Ghost > Lit)
		{
			// rastro do dano: o pedaço perdido pisca claro e some
			DrawTex(Tex, P0.X, P0.Y, W, H, FLinearColor(1.f, 1.f, 1.f, (Ghost - Lit) * 0.85f), UV0, UV1, true);
		}
		if (Lit > 0.f)
		{
			DrawTex(Tex, P0.X, P0.Y, W, H, Faded(Tint, Lit), UV0, UV1);
		}
	}
}

void AJRHUD::DrawContinuousBar(const FString& FillTex, const FVector2D& Origin, float K, int32 Which, float Pct, float TrailPct,
	const FLinearColor& Tint)
{
	UTexture2D* Tex = HudTex(FillTex);
	if (!Tex)
	{
		return;
	}
	const JRHudArt::FRect& Bar = Which == 0 ? JRHudArt::BotCarBarA : (Which == 1 ? JRHudArt::BotCarBarB : JRHudArt::BotCarBarC);
	const float* Span = Which == 0 ? JRHudArt::BotCarBarASpan : (Which == 1 ? JRHudArt::BotCarBarBSpan : JRHudArt::BotCarBarCSpan);
	auto DrawPart = [&](float RefX0, float RefX1, const FLinearColor& Color, bool bAdd)
	{
		const float A = FMath::Clamp(RefX0, Bar.X, Bar.X + Bar.W);
		const float B = FMath::Clamp(RefX1, Bar.X, Bar.X + Bar.W);
		if (B - A < 0.5f)
		{
			return;
		}
		const FVector2D P0 = PanelPoint(Origin, K, A, Bar.Y);
		DrawTex(Tex, P0.X, P0.Y, (B - A) * K, Bar.H * K, Color, FVector2D((A - Bar.X) / Bar.W, 0.f), FVector2D((B - Bar.X) / Bar.W, 1.f), bAdd);
	};
	const float Len = Span[1] - Span[0];
	const float XEnd = Pct >= 0.999f ? Bar.X + Bar.W : Span[0] + Len * FMath::Clamp(Pct, 0.f, 1.f);
	const float XTrail = Span[0] + Len * FMath::Clamp(TrailPct, 0.f, 1.f);
	if (XTrail > XEnd)
	{
		DrawPart(XEnd, XTrail, FLinearColor(1.f, 1.f, 1.f, 0.8f), true);
	}
	if (Pct > 0.001f)
	{
		DrawPart(Bar.X, XEnd, Tint, false);
	}
}

// ====================================================================== objetivo

AJRHordeDirector* AJRHUD::FindHorde()
{
	if (!CachedHorde.IsValid() && !bSearchedHorde)
	{
		bSearchedHorde = true;
		for (TActorIterator<AJRHordeDirector> It(GetWorld()); It; ++It)
		{
			CachedHorde = *It;
			break;
		}
	}
	return CachedHorde.Get();
}

FString AJRHUD::ObjectiveFor(EJRLevelStage Stage) const
{
	switch (Stage)
	{
	// [A-064] texto geral (só aparece sem tarefa): o jogo começa NA nave caída, então nada de "até a nave"
	case EJRLevelStage::Driving: return TEXT("Siga com o buggy pela estrada do vale");
	case EJRLevelStage::OnFoot: return TEXT("Explore a pé e siga as pistas");
	case EJRLevelStage::FinalHorde: return TEXT("Segure a horda na arena!");
	case EJRLevelStage::Rescue: return TEXT("Liberte a sobrevivente da cela");
	case EJRLevelStage::Completed: return TEXT("Fase concluída");
	default: return FString();
	}
}

void AJRHUD::DrawObjective(EJRLevelStage Stage, bool bDriving)
{
	if (Stage != LastStage)
	{
		// Novo estágio: a dica antiga não vale mais.
		LastStage = Stage;
		ObjectiveHint.Reset();
	}
	// [A-064] a tarefa atual manda no texto; o geral do estágio só aparece sem tarefa
	FString Text = CurrentTask.Text.IsEmpty() ? ObjectiveFor(Stage) : CurrentTask.Text;
	if (Text.IsEmpty())
	{
		return;
	}
	FString Wave;
	if (Stage == EJRLevelStage::FinalHorde)
	{
		if (const AJRHordeDirector* Horde = FindHorde())
		{
			if (Horde->GetCurrentWave() >= 0)
			{
				Wave = FString::Printf(TEXT("ONDA %d"), Horde->GetCurrentWave() + 1);
			}
		}
	}
	const float K = S * HudScale;
	const float M = SafeMargin * S;
	const FVector2D Origin(M, M);
	const JRHudArt::FPanel Size = bDriving ? JRHudArt::ObjCarSize : JRHudArt::ObjHeroSize;
	const JRHudArt::FRect Title = bDriving ? JRHudArt::ObjCarTitle : JRHudArt::ObjHeroTitle;
	const JRHudArt::FRect Body = bDriving ? JRHudArt::ObjCarBody : JRHudArt::ObjHeroBody;
	DrawTex(HudTex(bDriving ? TEXT("ObjCar") : TEXT("ObjHero")), Origin.X, Origin.Y, Size.W * K, Size.H * K, FLinearColor::White);

	// Título na pílula
	const float TitleSize = 34.f * K;
	const FVector2D TitleC = PanelPoint(Origin, K, Title.X + Title.W * 0.5f, Title.Y + Title.H * 0.5f);
	const float TitleH = MeasureText(TEXT("OBJETIVO"), true, TitleSize).Y;
	DrawHudText(TEXT("OBJETIVO"), TitleC.X, TitleC.Y - TitleH * 0.5f, TitleSize, TextColor, 1);
	if (!Wave.IsEmpty())
	{
		const FVector2D WaveP = PanelPoint(Origin, K, Title.X + Title.W + 8.f, Title.Y + Title.H * 0.5f);
		const float WaveH = MeasureText(Wave, true, 22.f * K).Y;
		DrawHudText(Wave, WaveP.X, WaveP.Y - WaveH * 0.5f, 22.f * K, YellowText, 0);
	}

	// Texto do objetivo: até 2 linhas, encolhe se precisar
	const float BodyW = Body.W * K;
	float BodySize = 25.f * K;
	TArray<FString> Lines = WrapText(Text, false, BodySize, BodyW);
	while (Lines.Num() > 2 && BodySize > 14.f * K)
	{
		BodySize *= 0.92f;
		Lines = WrapText(Text, false, BodySize, BodyW);
	}
	const float LineH = MeasureText(TEXT("Ág"), false, BodySize).Y * 0.92f;
	const FVector2D BodyP = PanelPoint(Origin, K, Body.X, Body.Y + Body.H * 0.5f);
	float LineY = BodyP.Y - LineH * static_cast<float>(Lines.Num()) * 0.5f;
	for (const FString& Line : Lines)
	{
		DrawHudText(Line, BodyP.X, LineY, BodySize, TextColor, 0, false);
		LineY += LineH;
	}

	// Dica (embaixo do painel, numa pílula escura)
	if (!ObjectiveHint.IsEmpty())
	{
		const float HintSize = 20.f * K;
		const float PillH = 44.f * K;
		const float HintW = MeasureText(ObjectiveHint, false, HintSize).X;
		const float PillW = FMath::Min(PillWidthFor(TEXT("PillNavy"), PillH, HintW), Canvas->ClipX * 0.45f);
		const float PX = Origin.X + 24.f * K;
		const float PY = Origin.Y + Size.H * K + 2.f * K;
		DrawPill(TEXT("PillNavy"), PX, PY, PillW, PillH, FLinearColor::White);
		const float HintH = MeasureText(ObjectiveHint, false, HintSize).Y;
		DrawHudTextFit(ObjectiveHint, PX + PillW * 0.5f, PY + PillH * 0.45f - HintH * 0.5f, HintSize, PillW - 40.f * K, YellowText, 1, false);
	}
}

void AJRHUD::DrawBigBanner(const FString& Title, const FString& Sub, const FLinearColor& Color)
{
	const float CX = Canvas->ClipX * 0.5f;
	const float CY = Canvas->ClipY * 0.5f;
	FCanvasTileItem Band(FVector2D(0.f, CY - 150.f * S), FVector2D(Canvas->ClipX, 300.f * S), Faded(InkColor, 0.55f));
	Band.BlendMode = SE_BLEND_Translucent;
	Canvas->DrawItem(Band);
	const float TitleSize = 64.f * S;
	const float TitleW = MeasureText(Title, true, TitleSize).X;
	const float PillH = 104.f * S;
	const float PillW = PillWidthFor(TEXT("PillTeal"), PillH, TitleW) + 40.f * S;
	DrawPill(TEXT("PillTeal"), CX - PillW * 0.5f, CY - 90.f * S, PillW, PillH, FLinearColor::White);
	const float TitleH = MeasureText(Title, true, TitleSize).Y;
	DrawHudText(Title, CX, CY - 90.f * S + PillH * 0.45f - TitleH * 0.5f, TitleSize, TextColor, 1);
	const float SubSize = 28.f * S;
	const float SubW = MeasureText(Sub, false, SubSize).X;
	const float SubPillH = 54.f * S;
	const float SubPillW = PillWidthFor(TEXT("PillNavy"), SubPillH, SubW) + 20.f * S;
	DrawPill(TEXT("PillNavy"), CX - SubPillW * 0.5f, CY + 30.f * S, SubPillW, SubPillH, FLinearColor::White);
	const float SubH = MeasureText(Sub, false, SubSize).Y;
	DrawHudText(Sub, CX, CY + 30.f * S + SubPillH * 0.45f - SubH * 0.5f, SubSize, Color, 1, false);
}

// ====================================================================== guia (minimapa / mapa / marcador)

AActor* AJRHUD::FindObjectiveTarget(EJRLevelStage Stage)
{
	if (!bSearchedTargets)
	{
		bSearchedTargets = true;
		for (TActorIterator<AJRCheckpoint> It(GetWorld()); It; ++It)
		{
			if (It->IsVehicleTransition())
			{
				CachedTransition = *It;
				break;
			}
		}
		for (TActorIterator<AJRRescueTarget> It(GetWorld()); It; ++It)
		{
			CachedRescue = *It;
			break;
		}
	}
	switch (Stage)
	{
	case EJRLevelStage::Driving:
		return CachedTransition.Get();
	case EJRLevelStage::OnFoot:
	case EJRLevelStage::FinalHorde:
		if (AJRHordeDirector* Horde = FindHorde())
		{
			return Horde;
		}
		return CachedRescue.Get();
	case EJRLevelStage::Rescue:
		return CachedRescue.Get();
	default:
		return nullptr;
	}
}

// ====================================================================== tarefa atual (A-064)

void AJRHUD::SetCurrentTask(const FString& Text, AActor* Target, float ReachRadius)
{
	FJRTask Task;
	Task.Text = Text;
	Task.Target = Target;
	Task.bHasTarget = Target != nullptr;
	Task.Reach = FMath::Max(100.f, ReachRadius);
	// Tarefa sem alvo nunca termina sozinha: a próxima a substitui na hora em vez de esperar na fila.
	if (CurrentTask.Text.IsEmpty() || !CurrentTask.bHasTarget || IsTaskDone(CurrentTask, PlayerOwner ? PlayerOwner->GetPawn() : nullptr))
	{
		CurrentTask = Task;
	}
	else
	{
		PendingTasks.Add(Task);
	}
}

bool AJRHUD::IsTaskDone(const FJRTask& Task, const APawn* Pawn) const
{
	if (!Task.bHasTarget)
	{
		return false;
	}
	const AActor* Target = Task.Target.Get();
	if (!Target)
	{
		return true; // item pego e destruído, ator removido
	}
	if (const AJRPickup* Pickup = Cast<AJRPickup>(Target))
	{
		return Pickup->IsTaken();
	}
	if (const AJRLootChest* Chest = Cast<AJRLootChest>(Target))
	{
		return Chest->IsOpened();
	}
	if (const AJRBlockingGate* Gate = Cast<AJRBlockingGate>(Target))
	{
		return Gate->IsOpen();
	}
	if (const AJRRescueTarget* Rescue = Cast<AJRRescueTarget>(Target))
	{
		return Rescue->IsRescued();
	}
	if (const APawn* TargetPawn = Cast<APawn>(Target))
	{
		return TargetPawn->IsPlayerControlled(); // "entre no buggy"
	}
	return Pawn && FVector::Dist2D(Pawn->GetActorLocation(), Target->GetActorLocation()) < Task.Reach;
}

void AJRHUD::UpdateTasks(const APawn* Pawn, EJRLevelStage Stage)
{
	if (Stage == EJRLevelStage::Completed)
	{
		CurrentTask = FJRTask();
		PendingTasks.Reset();
		return;
	}
	while (!CurrentTask.Text.IsEmpty() && IsTaskDone(CurrentTask, Pawn))
	{
		if (PendingTasks.Num() > 0)
		{
			CurrentTask = PendingTasks[0];
			PendingTasks.RemoveAt(0);
		}
		else
		{
			CurrentTask = FJRTask();
		}
	}
}

AActor* AJRHUD::GuideTarget(EJRLevelStage Stage)
{
	if (CurrentTask.bHasTarget)
	{
		if (AActor* Target = CurrentTask.Target.Get())
		{
			return Target;
		}
	}
	return FindObjectiveTarget(Stage);
}

UTexture2D* AJRHUD::GetMinimapTexture()
{
	if (!bSearchedMinimap)
	{
		bSearchedMinimap = true;
		if (const UJRObjectiveSubsystem* Objective = GetWorld()->GetSubsystem<UJRObjectiveSubsystem>())
		{
			if (const UJRLevelDefinition* Def = Objective->GetLevelDefinition())
			{
				CachedMinimap = Def->MinimapTexture.LoadSynchronous();
				CachedBigMap = Def->BigMapTexture.LoadSynchronous(); // [A-067]
				MapMin = Def->MinimapWorldMin;
				MapMax = Def->MinimapWorldMax;
			}
		}
	}
	return CachedMinimap.Get();
}

UTexture2D* AJRHUD::GetBigMapTexture()
{
	UTexture2D* Mini = GetMinimapTexture();
	return CachedBigMap.IsValid() ? CachedBigMap.Get() : Mini;
}

FVector2D AJRHUD::WorldToUV(const FVector& L) const
{
	// Norte para cima: topo da imagem = Y mínimo do mundo.
	return FVector2D((L.X - MapMin.X) / FMath::Max(1.f, MapMax.X - MapMin.X),
		(L.Y - MapMin.Y) / FMath::Max(1.f, MapMax.Y - MapMin.Y));
}

void AJRHUD::DrawDiamond(const FVector2D& C, float R, const FLinearColor& Color)
{
	TArray<FCanvasUVTri> Tris;
	auto Tri = [&](const FVector2D& A, const FVector2D& B, const FVector2D& D, const FLinearColor& Col)
	{
		FCanvasUVTri T;
		T.V0_Pos = A; T.V1_Pos = B; T.V2_Pos = D;
		T.V0_Color = Col; T.V1_Color = Col; T.V2_Color = Col;
		Tris.Add(T);
	};
	const float O = R + 2.5f * S;
	const FLinearColor Dark = Faded(InkColor, 0.95f * Color.A);
	Tri(C + FVector2D(0, -O), C + FVector2D(O, 0), C + FVector2D(0, O), Dark);
	Tri(C + FVector2D(0, -O), C + FVector2D(-O, 0), C + FVector2D(0, O), Dark);
	Tri(C + FVector2D(0, -R), C + FVector2D(R, 0), C + FVector2D(0, R), Color);
	Tri(C + FVector2D(0, -R), C + FVector2D(-R, 0), C + FVector2D(0, R), Color);
	// brilho em cima (efeito de "pedra")
	const FLinearColor Shine(1.f, 1.f, 1.f, 0.45f * Color.A);
	Tri(C + FVector2D(0, -R * 0.8f), C + FVector2D(R * 0.45f, -R * 0.3f), C + FVector2D(-R * 0.45f, -R * 0.3f), Shine);
	FCanvasTriangleItem Item(FVector2D::ZeroVector, FVector2D::ZeroVector, FVector2D::ZeroVector, nullptr);
	Item.TriangleList = MoveTemp(Tris);
	Item.BlendMode = SE_BLEND_Translucent;
	if (UTexture2D* White = HudTex(TEXT("Circle")))
	{
		Item.Texture = White->GetResource();
		for (FCanvasUVTri& T : Item.TriangleList)
		{
			T.V0_UV = FVector2D(0.5f, 0.5f); T.V1_UV = FVector2D(0.5f, 0.5f); T.V2_UV = FVector2D(0.5f, 0.5f);
		}
		Canvas->DrawItem(Item);
	}
	else
	{
		Canvas->K2_DrawTriangle(nullptr, Item.TriangleList);
	}
}

void AJRHUD::DrawArrow(const FVector2D& C, float Yaw, float R, const FLinearColor& Color)
{
	const float A = FMath::DegreesToRadians(Yaw);
	auto Dir = [&](float Off) { return FVector2D(FMath::Cos(A + Off), FMath::Sin(A + Off)); };
	TArray<FCanvasUVTri> Tris;
	auto Tri = [&](float Scale, const FLinearColor& Col)
	{
		FCanvasUVTri T;
		T.V0_Pos = C + Dir(0.f) * R * Scale;
		T.V1_Pos = C + Dir(2.45f) * R * 0.8f * Scale;
		T.V2_Pos = C + Dir(-2.45f) * R * 0.8f * Scale;
		T.V0_Color = Col; T.V1_Color = Col; T.V2_Color = Col;
		Tris.Add(T);
	};
	Tri(1.45f, Faded(InkColor, 0.95f * Color.A));
	Tri(1.f, Color);
	FCanvasTriangleItem Item(FVector2D::ZeroVector, FVector2D::ZeroVector, FVector2D::ZeroVector, nullptr);
	Item.TriangleList = MoveTemp(Tris);
	Item.BlendMode = SE_BLEND_Translucent;
	if (UTexture2D* White = HudTex(TEXT("Circle")))
	{
		Item.Texture = White->GetResource();
		for (FCanvasUVTri& T : Item.TriangleList)
		{
			T.V0_UV = FVector2D(0.5f, 0.5f); T.V1_UV = FVector2D(0.5f, 0.5f); T.V2_UV = FVector2D(0.5f, 0.5f);
		}
		Canvas->DrawItem(Item);
	}
	else
	{
		Canvas->K2_DrawTriangle(nullptr, Item.TriangleList);
	}
}

void AJRHUD::DrawMapEllipse(UTexture2D* Tex, const FVector2D& Center, float RX, float RY, const FVector2D& UVCenter, const FVector2D& UVHalf,
	const FLinearColor& Color)
{
	UTexture2D* Use = Tex ? Tex : HudTex(TEXT("Circle"));
	if (!Use || !Use->GetResource())
	{
		return;
	}
	const int32 Segments = 72;
	FCanvasTriangleItem Item(FVector2D::ZeroVector, FVector2D::ZeroVector, FVector2D::ZeroVector, Use->GetResource());
	Item.TriangleList.Reset();
	Item.TriangleList.Reserve(Segments);
	auto UVAt = [&](float LX, float LY)
	{
		// LX, LY de -1 a 1 dentro da elipse
		return Tex ? FVector2D(UVCenter.X + LX * UVHalf.X, UVCenter.Y + LY * UVHalf.Y) : FVector2D(0.5f, 0.5f);
	};
	for (int32 Seg = 0; Seg < Segments; ++Seg)
	{
		const float A0 = 2.f * UE_PI * static_cast<float>(Seg) / static_cast<float>(Segments);
		const float A1 = 2.f * UE_PI * static_cast<float>(Seg + 1) / static_cast<float>(Segments);
		FCanvasUVTri T;
		T.V0_Pos = Center;
		T.V0_UV = UVAt(0.f, 0.f);
		T.V1_Pos = Center + FVector2D(FMath::Cos(A0) * RX, FMath::Sin(A0) * RY);
		T.V1_UV = UVAt(FMath::Cos(A0), FMath::Sin(A0));
		T.V2_Pos = Center + FVector2D(FMath::Cos(A1) * RX, FMath::Sin(A1) * RY);
		T.V2_UV = UVAt(FMath::Cos(A1), FMath::Sin(A1));
		T.V0_Color = Color; T.V1_Color = Color; T.V2_Color = Color;
		Item.TriangleList.Add(T);
	}
	Item.BlendMode = SE_BLEND_Translucent;
	Canvas->DrawItem(Item);
}

void AJRHUD::DrawMinimap(const APawn* Pawn, bool bDriving, const AActor* Target)
{
	const float K = S * HudScale;
	const float M = SafeMargin * S;
	const JRHudArt::FPanel Size = bDriving ? JRHudArt::MapCarSize : JRHudArt::MapHeroSize;
	const JRHudArt::FRect Ell = bDriving ? JRHudArt::MapCarEllipse : JRHudArt::MapHeroEllipse;
	const JRHudArt::FRect Title = bDriving ? JRHudArt::MapCarTitle : JRHudArt::MapHeroTitle;
	const FVector2D Origin(Canvas->ClipX - M - Size.W * K, M);
	const FVector2D C = PanelPoint(Origin, K, Ell.X, Ell.Y);
	const float RX = Ell.W * K;
	const float RY = Ell.H * K;

	// ---- fundo e imagem do mapa (recortados na elipse; a moldura cobre a borda)
	DrawMapEllipse(nullptr, C, RX, RY, FVector2D::ZeroVector, FVector2D::ZeroVector, NavyColor);
	// [A-083] Radar: sem imagem (a do L01 não vale na cidade/arena); escala linear em volta do jogador.
	const bool bRadar = !UseLevelMinimapImage();
	if (bRadar)
	{
		MapMin = FVector2D(-2000000.f, -2000000.f);
		MapMax = FVector2D(2000000.f, 2000000.f);
	}
	UTexture2D* MapTex = bRadar ? nullptr : GetMinimapTexture();
	const float SpanCm = (bDriving ? MinimapSpanDriving : MinimapSpanOnFoot) * 100.f;
	const float CmPerPx = SpanCm / FMath::Max(1.f, 2.f * RX);
	const FVector2D UVHalf(RX * CmPerPx / FMath::Max(1.f, MapMax.X - MapMin.X), RY * CmPerPx / FMath::Max(1.f, MapMax.Y - MapMin.Y));
	const FVector2D PawnUV = WorldToUV(Pawn->GetActorLocation());
	// Perto da borda do mapa a janela para de andar (a imagem não se repete).
	const FVector2D UVCenter(UVHalf.X < 0.5f ? FMath::Clamp(PawnUV.X, UVHalf.X, 1.f - UVHalf.X) : 0.5f,
		UVHalf.Y < 0.5f ? FMath::Clamp(PawnUV.Y, UVHalf.Y, 1.f - UVHalf.Y) : 0.5f);
	if (MapTex && MapTex->GetResource())
	{
		DrawMapEllipse(MapTex, C, RX, RY, UVCenter, UVHalf, FLinearColor::White);
		if (MinimapTint > 0.f)
		{
			DrawMapEllipse(nullptr, C, RX, RY, FVector2D::ZeroVector, FVector2D::ZeroVector, Faded(NavyColor, MinimapTint));
		}
	}
	auto ToScreen = [&](const FVector& L)
	{
		const FVector2D UV = WorldToUV(L);
		return C + FVector2D((UV.X - UVCenter.X) / FMath::Max(1e-6f, UVHalf.X) * RX, (UV.Y - UVCenter.Y) / FMath::Max(1e-6f, UVHalf.Y) * RY);
	};
	auto EllipseQ = [&](const FVector2D& P)
	{
		const FVector2D D = P - C;
		return static_cast<float>(FMath::Square(D.X / RX) + FMath::Square(D.Y / RY));
	};
	if (bRadar)
	{
		// [A-083] anéis de distância e varredura girando (radar vivo)
		const float RadarR = FMath::Min(RX, RY);
		DrawArc(C, RadarR * 0.33f - 1.2f * K, RadarR * 0.33f + 1.2f * K, 0.f, 360.f, Faded(AccentColor, 0.22f), 32);
		DrawArc(C, RadarR * 0.66f - 1.2f * K, RadarR * 0.66f + 1.2f * K, 0.f, 360.f, Faded(AccentColor, 0.18f), 48);
		const float Sweep = FMath::Fmod(static_cast<float>(GetWorld()->GetRealTimeSeconds()) * 120.f, 360.f);
		for (int32 Slice = 0; Slice < 8; ++Slice)
		{
			const float SliceAlpha = 0.20f * (1.f - static_cast<float>(Slice) / 8.f);
			DrawArc(C, 0.f, RadarR * 0.96f, Sweep - 6.f * static_cast<float>(Slice + 1), Sweep - 6.f * static_cast<float>(Slice), Faded(AccentColor, SliceAlpha), 3);
		}
	}

	// ---- zumbis (pontos vermelhos)
	for (TActorIterator<AJREnemyCharacter> It(GetWorld()); It; ++It)
	{
		if (It->IsDead())
		{
			continue;
		}
		const FVector2D P = ToScreen(It->GetActorLocation());
		if (EllipseQ(P) < 0.86f)
		{
			DrawRounded(P.X - 5.f * K, P.Y - 5.f * K, 10.f * K, 10.f * K, 5.f * K, Faded(InkColor, 0.9f));
			DrawRounded(P.X - 3.5f * K, P.Y - 3.5f * K, 7.f * K, 7.f * K, 3.5f * K, HealthColor);
		}
	}
	// ---- [A-067] itens e baús que ainda servem (pontinho ciano com contorno)
	{
		TArray<AActor*> Nearby;
		CollectNearbyInteractables(Pawn, SpanCm * 0.5f, 12, Target, Nearby);
		for (const AActor* Item : Nearby)
		{
			const FVector2D P = ToScreen(Item->GetActorLocation());
			if (EllipseQ(P) < 0.82f)
			{
				DrawRounded(P.X - 6.f * K, P.Y - 6.f * K, 12.f * K, 12.f * K, 6.f * K, Faded(InkColor, 0.9f));
				DrawRounded(P.X - 4.f * K, P.Y - 4.f * K, 8.f * K, 8.f * K, 4.f * K, AccentColor);
			}
		}
	}
	// ---- [A-083] pinos extras da subclasse (nave de extração, vendedores)
	{
		TArray<FJRHudBlip> Blips;
		CollectRadarBlips(Blips);
		for (const FJRHudBlip& Blip : Blips)
		{
			FVector2D BlipPos = ToScreen(Blip.World);
			const float BlipQ = EllipseQ(BlipPos);
			const bool bBlipOut = BlipQ > 0.62f;
			if (bBlipOut)
			{
				BlipPos = C + (BlipPos - C) * (0.79f / FMath::Sqrt(BlipQ));
			}
			DrawMarkerPin(BlipPos, (bBlipOut ? 24.f : 28.f) * K, Blip.Icon, Blip.Tint, 1.f, false);
		}
	}
	// ---- tarefa atual: pino com ícone; fora da área fica preso na borda, no rumo dela
	if (Target)
	{
		FVector2D P = ToScreen(Target->GetActorLocation());
		const float Q = EllipseQ(P);
		const bool bOutside = Q > 0.62f;
		if (bOutside)
		{
			P = C + (P - C) * (0.79f / FMath::Sqrt(Q));
		}
		DrawMarkerPin(P, (bOutside ? 26.f : 30.f) * K, MarkerIconFor(Target), ObjectiveColor, 1.f, true);
	}
	// ---- jogador (seta no centro)
	const FVector2D PawnP = ToScreen(Pawn->GetActorLocation());
	float ViewYaw = static_cast<float>(Pawn->GetActorRotation().Yaw);
	if (PlayerOwner && PlayerOwner->PlayerCameraManager && !bDriving)
	{
		ViewYaw = static_cast<float>(PlayerOwner->PlayerCameraManager->GetCameraRotation().Yaw);
	}
	DrawArrow(PawnP, ViewYaw, 13.f * K, CyanText); // [A-067] um pouco maior

	// ---- moldura por cima e título
	DrawTex(HudTex(bDriving ? TEXT("MapCar") : TEXT("MapHero")), Origin.X, Origin.Y, Size.W * K, Size.H * K, FLinearColor::White);
	const float TitleSize = 32.f * K;
	const FVector2D TitleC = PanelPoint(Origin, K, Title.X + Title.W * 0.5f, Title.Y + Title.H * 0.5f);
	const TCHAR* const MapTitle = bRadar ? TEXT("RADAR") : TEXT("MINIMAPA"); // [A-083]
	const float TitleH = MeasureText(MapTitle, true, TitleSize).Y;
	DrawHudText(MapTitle, TitleC.X, TitleC.Y - TitleH * 0.5f, TitleSize, TextColor, 1);
	if (!bDriving)
	{
		// [A-067] bússola: N em destaque e L, S, O menores na borda (norte sempre para cima)
		const TCHAR* const Letters[] = { TEXT("N"), TEXT("L"), TEXT("S"), TEXT("O") };
		const FVector2D Dirs[] = { FVector2D(0.f, -1.f), FVector2D(1.f, 0.f), FVector2D(0.f, 1.f), FVector2D(-1.f, 0.f) };
		for (int32 Index = 0; Index < 4; ++Index)
		{
			const float LetterSize = (Index == 0 ? 22.f : 16.f) * K;
			const FVector2D LetterPos = C + FVector2D(Dirs[Index].X * (RX - 13.f * K), Dirs[Index].Y * (RY - 13.f * K));
			const float LH = MeasureText(Letters[Index], true, LetterSize).Y;
			DrawHudText(Letters[Index], LetterPos.X, LetterPos.Y - LH * 0.5f, LetterSize,
				Index == 0 ? YellowText : Faded(TextColor, 0.7f), 1);
		}
	}

	// ---- distância e atalho do mapa (pílula embaixo da moldura)
	if (bRadar && !Target)
	{
		return; // [A-083] radar sem alvo: sem mapa grande, sem pílula
	}
	const float RowY = Origin.Y + Size.H * K + 4.f * K;
	const float PillH = 40.f * K;
	FString DistText = TEXT("MAPA");
	if (Target)
	{
		const float Dist = FVector::Dist2D(Pawn->GetActorLocation(), Target->GetActorLocation()) / 100.f;
		DistText = FString::Printf(TEXT("%s  %d m"), CurrentTask.Text.IsEmpty() ? TEXT("OBJETIVO") : TEXT("TAREFA"), FMath::RoundToInt(Dist));
	}
	const float TextSize = 19.f * K;
	const float TextW = MeasureText(DistText, true, TextSize).X;
	const float KeyW = 34.f * K;
	const float PillW = PillWidthFor(TEXT("PillNavy"), PillH, TextW + KeyW + 10.f * K);
	const float PX = C.X - PillW * 0.5f;
	DrawPill(TEXT("PillNavy"), PX, RowY, PillW, PillH, FLinearColor::White);
	const float Inner = PX + (PillW - (TextW + KeyW + 10.f * K)) * 0.5f;
	DrawKeyCap(TEXT("M"), Inner, RowY + PillH * 0.5f - 15.f * K, 30.f * K);
	const float TextH = MeasureText(DistText, true, TextSize).Y;
	DrawHudText(DistText, Inner + KeyW + 10.f * K, RowY + PillH * 0.45f - TextH * 0.5f, TextSize, Target ? YellowText : TextColor, 0);
}

void AJRHUD::DrawBigMapView(const APawn* Pawn, const AActor* Target)
{
	UTexture2D* Tex = GetBigMapTexture(); // [A-067] versão com nomes dos lugares
	FCanvasTileItem Dim(FVector2D::ZeroVector, FVector2D(Canvas->ClipX, Canvas->ClipY), Faded(InkColor, 0.72f));
	Dim.BlendMode = SE_BLEND_Translucent;
	Canvas->DrawItem(Dim);
	if (!Tex || !Tex->GetResource())
	{
		DrawHudText(TEXT("Mapa indisponível nesta fase"), Canvas->ClipX * 0.5f, Canvas->ClipY * 0.5f, 30.f * S, TextColor, 1);
		return;
	}
	const float MapSize = Canvas->ClipY * 0.74f;
	const FVector2D Pos((Canvas->ClipX - MapSize) * 0.5f, (Canvas->ClipY - MapSize) * 0.5f + 16.f * S);
	auto ToScreen = [&](const FVector& L) { return Pos + WorldToUV(L) * MapSize; };
	// moldura de "pedra" lilás em camadas (mesmas cores da roda)
	const float B = 16.f * S;
	DrawRounded(Pos.X - B - 4.f * S, Pos.Y - B + 2.f * S, MapSize + 2.f * B + 8.f * S, MapSize + 2.f * B + 8.f * S, 34.f * S, Faded(InkColor, 0.9f));
	DrawRounded(Pos.X - B, Pos.Y - B, MapSize + 2.f * B, MapSize + 2.f * B, 30.f * S, FLinearColor(FColor(118, 96, 178)));
	DrawRounded(Pos.X - B + 3.f * S, Pos.Y - B + 2.f * S, MapSize + 2.f * B - 6.f * S, 10.f * S, 5.f * S, FLinearColor(FColor(170, 150, 225, 160)));
	DrawRounded(Pos.X - 5.f * S, Pos.Y - 5.f * S, MapSize + 10.f * S, MapSize + 10.f * S, 14.f * S, InkColor);
	FCanvasTileItem Map(Pos, Tex->GetResource(), FVector2D(MapSize, MapSize), FLinearColor::White);
	Map.BlendMode = SE_BLEND_Translucent;
	Canvas->DrawItem(Map);
	// luzes ciano nas laterais
	for (int32 Side = 0; Side < 2; ++Side)
	{
		const float LX = Side == 0 ? Pos.X - B - 2.f * S : Pos.X + MapSize + B - 10.f * S;
		DrawRounded(LX, Pos.Y + MapSize * 0.4f, 12.f * S, MapSize * 0.2f, 6.f * S, AccentColor);
	}
	for (TActorIterator<AJREnemyCharacter> It(GetWorld()); It; ++It)
	{
		if (!It->IsDead())
		{
			const FVector2D P = ToScreen(It->GetActorLocation());
			DrawRounded(P.X - 4.f * S, P.Y - 4.f * S, 8.f * S, 8.f * S, 4.f * S, Faded(InkColor, 0.9f));
			DrawRounded(P.X - 3.f * S, P.Y - 3.f * S, 6.f * S, 6.f * S, 3.f * S, HealthColor);
		}
	}
	if (Target)
	{
		DrawMarkerPin(ToScreen(Target->GetActorLocation()), 40.f * S, MarkerIconFor(Target), ObjectiveColor, 1.f, true); // [A-067]
	}
	DrawArrow(ToScreen(Pawn->GetActorLocation()), static_cast<float>(Pawn->GetActorRotation().Yaw), 13.f * S, CyanText);
	// título e legenda
	const float TitleH = 64.f * S;
	const float TitleW = PillWidthFor(TEXT("PillTeal"), TitleH, MeasureText(TEXT("MAPA"), true, 40.f * S).X) + 30.f * S;
	DrawPill(TEXT("PillTeal"), Canvas->ClipX * 0.5f - TitleW * 0.5f, Pos.Y - B - TitleH * 0.75f, TitleW, TitleH, FLinearColor::White);
	const float TH = MeasureText(TEXT("MAPA"), true, 40.f * S).Y;
	DrawHudText(TEXT("MAPA"), Canvas->ClipX * 0.5f, Pos.Y - B - TitleH * 0.75f + TitleH * 0.45f - TH * 0.5f, 40.f * S, TextColor, 1);
	const FString Legend = TEXT("seta = você      pino = tarefa      pontos vermelhos = zumbis");
	const float LegendSize = 19.f * S;
	const float LegendW = MeasureText(Legend, false, LegendSize).X;
	const float LegendPillH = 44.f * S;
	const float KeyW = 40.f * S;
	const float LegendPillW = PillWidthFor(TEXT("PillNavy"), LegendPillH, LegendW + KeyW + 80.f * S);
	const float LX0 = Canvas->ClipX * 0.5f - LegendPillW * 0.5f;
	const float LY0 = Pos.Y + MapSize + B + 10.f * S;
	DrawPill(TEXT("PillNavy"), LX0, LY0, LegendPillW, LegendPillH, FLinearColor::White);
	float CursorX = LX0 + (LegendPillW - (LegendW + KeyW + 80.f * S)) * 0.5f;
	CursorX += DrawKeyCap(TEXT("M"), CursorX, LY0 + LegendPillH * 0.5f - 15.f * S, 30.f * S) + 6.f * S;
	const float LH = MeasureText(Legend, false, LegendSize).Y;
	CursorX += DrawHudText(TEXT("fechar"), CursorX, LY0 + LegendPillH * 0.45f - LH * 0.5f, LegendSize, SoftTextColor, 0, false) + 30.f * S;
	DrawHudText(Legend, CursorX, LY0 + LegendPillH * 0.45f - LH * 0.5f, LegendSize, TextColor, 0, false);
}

void AJRHUD::DrawWorldMarker(const AActor* Target, const APawn* Pawn)
{
	const float Now = static_cast<float>(GetWorld()->GetRealTimeSeconds());
	// [A-083] Sem pinos flutuando em cima de itens e baús no chão (pedido do usuário): o mundo só marca
	// o objetivo (e a nave de extração, desenhada pela AJRRemapHUD). Os pontos ciano no minimapa continuam.
	if (Target && (Target->IsA<AJRPickup>() || Target->IsA<AJRLootChest>()))
	{
		return;
	}
	if (!Target)
	{
		return;
	}
	// Pino dourado da tarefa atual; fora da tela fica na borda com uma seta apontando para ele.
	FVector Screen = Project(MarkerAnchor(Target), false);
	const float Edge = 70.f * S;
	bool bOff = false;
	if (Screen.Z <= 0.f)
	{
		// atrás da câmera: espelha para a borda de baixo
		Screen.X = Canvas->ClipX - Screen.X;
		Screen.Y = Canvas->ClipY - Edge;
		bOff = true;
	}
	if (Screen.X < Edge || Screen.X > Canvas->ClipX - Edge || Screen.Y < Edge || Screen.Y > Canvas->ClipY - Edge)
	{
		bOff = true;
	}
	const FVector2D Raw(Screen.X, Screen.Y);
	Screen.X = FMath::Clamp(Screen.X, Edge, Canvas->ClipX - Edge);
	Screen.Y = FMath::Clamp(Screen.Y, Edge + 260.f * S, Canvas->ClipY - Edge - 240.f * S);
	const float Dist = static_cast<float>(FVector::Dist(Pawn->GetActorLocation(), Target->GetActorLocation())) / 100.f;
	if (!bOff && Dist < 4.f)
	{
		return; // já chegou: o aviso "E" assume
	}
	const FVector2D Tip(Screen.X, Screen.Y);
	DrawMarkerPin(Tip, (bOff ? 36.f : 44.f) * S, MarkerIconFor(Target), ObjectiveColor, 1.f, true);
	if (bOff)
	{
		const FVector2D Mid(Canvas->ClipX * 0.5f, Canvas->ClipY * 0.5f);
		const FVector2D Dir = (Raw - Mid).GetSafeNormal();
		const float Yaw = FMath::RadiansToDegrees(FMath::Atan2(Dir.Y, Dir.X));
		const float Bob = 4.f * S * FMath::Sin(Now * 6.f);
		DrawArrow(Tip - FVector2D(0.f, 22.f * S) + Dir * (40.f * S + Bob), Yaw, 11.f * S, ObjectiveColor);
	}
	const FString DistText = FString::Printf(TEXT("%d m"), FMath::RoundToInt(Dist));
	const float TextSize = 19.f * S;
	const float PillH = 34.f * S;
	const float PillW = PillWidthFor(TEXT("PillNavy"), PillH, MeasureText(DistText, true, TextSize).X);
	DrawPill(TEXT("PillNavy"), Tip.X - PillW * 0.5f, Tip.Y + 8.f * S, PillW, PillH, FLinearColor(1.f, 1.f, 1.f, 0.92f));
	const float TH = MeasureText(DistText, true, TextSize).Y;
	DrawHudText(DistText, Tip.X, Tip.Y + 8.f * S + PillH * 0.45f - TH * 0.5f, TextSize, YellowText, 1);
}

// ====================================================================== marcadores (A-067)

FVector AJRHUD::MarkerAnchor(const AActor* Target)
{
	FVector Origin;
	FVector Extent;
	Target->GetActorBounds(true, Origin, Extent);
	const double Top = Extent.Z > 1.0 && Extent.Z < 1500.0 ? Origin.Z + Extent.Z : Target->GetActorLocation().Z + 60.0;
	return FVector(Target->GetActorLocation().X, Target->GetActorLocation().Y, FMath::Max(Top, Target->GetActorLocation().Z) + 70.0);
}

FString AJRHUD::MarkerIconFor(const AActor* Target) const
{
	if (const AJRPickup* Pickup = Cast<AJRPickup>(Target))
	{
		switch (Pickup->GetPickupType())
		{
		case EJRPickupType::WeaponMelee: return TEXT("Icon_Stick");
		case EJRPickupType::WeaponPistol: return TEXT("Icon_Pistol");
		case EJRPickupType::WeaponShotgun: return TEXT("Icon_Shotgun");
		case EJRPickupType::WeaponSniper: return TEXT("Icon_Sniper");
		case EJRPickupType::Health:
		case EJRPickupType::Medkit: return TEXT("Icon_Medkit");
		case EJRPickupType::Bandage: return TEXT("Icon_Bandage");
		case EJRPickupType::Ammo: return TEXT("Stat_Ammo");
		case EJRPickupType::Fury: return TEXT("Icon_Fury");
		case EJRPickupType::Nitro: return TEXT("Icon_Fuel");
		default: return FString();
		}
	}
	if (const AJRLootChest* Chest = Cast<AJRLootChest>(Target))
	{
		const FString Key = Chest->GetKeyItemInside().ToString();
		if (Key.Contains(TEXT("Key")))
		{
			return TEXT("Icon_CarKey");
		}
		if (Key.Contains(TEXT("Fuel")))
		{
			return TEXT("Icon_Fuel");
		}
		if (Key.Contains(TEXT("Explosive")))
		{
			return TEXT("Icon_Explosive");
		}
		switch (Chest->GetWeaponInside())
		{
		case EJRWeaponSlot::Melee: return TEXT("Icon_Stick");
		case EJRWeaponSlot::Pistol: return TEXT("Icon_Pistol");
		case EJRWeaponSlot::Shotgun: return TEXT("Icon_Shotgun");
		case EJRWeaponSlot::Sniper: return TEXT("Icon_Sniper");
		default: return TEXT("Stat_Ammo");
		}
	}
	if (Target && Target->IsA<AJRVehiclePawn>())
	{
		return TEXT("Icon_CarKey");
	}
	if (Target && Target->IsA<AJRRescueTarget>())
	{
		return TEXT("Icon_Hand");
	}
	return FString();
}

void AJRHUD::DrawSolidTri(const FVector2D& A, const FVector2D& B, const FVector2D& C, const FLinearColor& Color)
{
	FCanvasUVTri T;
	T.V0_Pos = A; T.V1_Pos = B; T.V2_Pos = C;
	T.V0_Color = Color; T.V1_Color = Color; T.V2_Color = Color;
	T.V0_UV = FVector2D(0.5f, 0.5f); T.V1_UV = FVector2D(0.5f, 0.5f); T.V2_UV = FVector2D(0.5f, 0.5f);
	UTexture2D* White = HudTex(TEXT("Circle"));
	FCanvasTriangleItem Item(FVector2D::ZeroVector, FVector2D::ZeroVector, FVector2D::ZeroVector, White ? White->GetResource() : nullptr);
	Item.TriangleList.Reset();
	Item.TriangleList.Add(T);
	Item.BlendMode = SE_BLEND_Translucent;
	Canvas->DrawItem(Item);
}

void AJRHUD::DrawMarkerPin(const FVector2D& Tip, float Size, const FString& Icon, const FLinearColor& RingColor, float Alpha, bool bPulse)
{
	if (Alpha <= 0.01f)
	{
		return;
	}
	const float Now = static_cast<float>(GetWorld()->GetRealTimeSeconds());
	const float Pulse = bPulse ? 0.5f + 0.5f * FMath::Sin(Now * 4.f) : 0.f;
	const float R = Size * 0.5f;
	const FVector2D C = Tip - FVector2D(0.f, Size * 0.95f);
	// halo (respira na tarefa atual)
	if (UTexture2D* GlowTex = HudTex(TEXT("Glow")))
	{
		const float G = Size * (1.5f + 0.25f * Pulse);
		DrawTex(GlowTex, C.X - G, C.Y - G, 2.f * G, 2.f * G, Faded(RingColor, (0.35f + 0.25f * Pulse) * Alpha));
	}
	// ponta para baixo (contorno escuro + cor)
	DrawSolidTri(C + FVector2D(-R * 0.62f, R * 0.55f), C + FVector2D(R * 0.62f, R * 0.55f), Tip + FVector2D(0.f, 3.f * S), Faded(InkColor, 0.95f * Alpha));
	DrawSolidTri(C + FVector2D(-R * 0.45f, R * 0.55f), C + FVector2D(R * 0.45f, R * 0.55f), Tip, Faded(RingColor, Alpha));
	// disco: contorno escuro, anel colorido, miolo azul-marinho
	const float RO = R + 3.f * S;
	DrawRounded(C.X - RO, C.Y - RO, 2.f * RO, 2.f * RO, RO, Faded(InkColor, 0.95f * Alpha));
	DrawRounded(C.X - R, C.Y - R, 2.f * R, 2.f * R, R, Faded(RingColor, Alpha));
	const float RI = R * 0.78f;
	DrawRounded(C.X - RI, C.Y - RI, 2.f * RI, 2.f * RI, RI, Faded(NavyColor, Alpha));
	// brilho em cima (efeito de vidro, como os painéis)
	DrawRounded(C.X - RI * 0.6f, C.Y - RI * 0.82f, RI * 1.2f, RI * 0.38f, RI * 0.19f, FLinearColor(1.f, 1.f, 1.f, 0.16f * Alpha));
	UTexture2D* IconTex = Icon.IsEmpty() ? nullptr : HudTex(Icon);
	if (IconTex)
	{
		const float IS = RI * 1.45f;
		DrawTex(IconTex, C.X - IS * 0.5f, C.Y - IS * 0.5f, IS, IS, Faded(FLinearColor::White, Alpha));
	}
	else
	{
		DrawDiamond(C, RI * 0.55f, Faded(RingColor, Alpha)); // ponto sem ícone (lugar)
	}
}

void AJRHUD::CollectNearbyInteractables(const APawn* Pawn, float RadiusCm, int32 MaxCount, const AActor* Skip, TArray<AActor*>& Out) const
{
	Out.Reset();
	if (!Pawn || MaxCount <= 0)
	{
		return;
	}
	const FVector Me = Pawn->GetActorLocation();
	const double R2 = static_cast<double>(RadiusCm) * static_cast<double>(RadiusCm);
	TArray<TPair<double, AActor*>> Found;
	for (TActorIterator<AJRPickup> It(GetWorld()); It; ++It)
	{
		if (*It != Skip && !It->IsTaken() && FVector::DistSquared(Me, It->GetActorLocation()) < R2)
		{
			Found.Emplace(FVector::DistSquared(Me, It->GetActorLocation()), *It);
		}
	}
	for (TActorIterator<AJRLootChest> It(GetWorld()); It; ++It)
	{
		if (*It != Skip && !It->IsOpened() && FVector::DistSquared(Me, It->GetActorLocation()) < R2)
		{
			Found.Emplace(FVector::DistSquared(Me, It->GetActorLocation()), *It);
		}
	}
	Found.Sort([](const TPair<double, AActor*>& A, const TPair<double, AActor*>& B) { return A.Key < B.Key; });
	for (int32 Index = 0; Index < Found.Num() && Index < MaxCount; ++Index)
	{
		Out.Add(Found[Index].Value);
	}
}

// ====================================================================== HUD do herói / carro / avisos

void AJRHUD::DrawHeroHud(AJRCharacter* Hero)
{
	// [A-058] luneta primeiro: o resto do HUD fica por cima dela.
	const float HeroScope = Hero->GetScopeAlpha();
	if (HeroScope > 0.01f)
	{
		DrawSniperScope(Hero, HeroScope);
	}
	const float K = S * HudScale;
	const float M = SafeMargin * S;
	const double RealNow = GetWorld()->GetRealTimeSeconds();
	const float Now = static_cast<float>(RealNow);
	const float Delta = FMath::Clamp(static_cast<float>(GetWorld()->GetDeltaSeconds()), 0.f, 0.1f);
	const float RealDelta = FMath::Max(Delta, 1.f / 120.f);

	// ---- Vida
	const UJRHealthComponent* Health = Hero->GetHealthComponent();
	const float Hp = Health->GetHealth();
	if (LastHealth >= 0.f && Hp < LastHealth)
	{
		DamageFlashStart = GetWorld()->GetTimeSeconds();
		TrailHold.Add(TEXT("Hp"), RealNow + 0.35);
	}
	LastHealth = Hp;
	const float HpPct = Health->GetHealthNormalized();
	const float HpShown = Smooth(TEXT("HpShown"), HpPct, 12.f, RealDelta);
	// rastro do dano: segura 0,35 s e depois desce devagar (cópia local: o TMap pode realocar)
	float HpTrail = SmoothValues.FindOrAdd(TEXT("HpTrail"), HpPct);
	if (HpTrail < HpShown)
	{
		HpTrail = HpShown;
	}
	else if (RealNow > TrailHold.FindRef(TEXT("Hp")))
	{
		HpTrail = FMath::FInterpConstantTo(HpTrail, HpShown, RealDelta, 0.9f);
	}
	SmoothValues.Add(TEXT("HpTrail"), HpTrail);

	const FVector2D Origin(M, Canvas->ClipY - M - JRHudArt::BotHeroSize.H * K);
	DrawTex(HudTex(TEXT("BotHero")), Origin.X, Origin.Y, JRHudArt::BotHeroSize.W * K, JRHudArt::BotHeroSize.H * K, FLinearColor::White);
	const bool bLow = HpPct < 0.3f;
	const float LowPulse = bLow ? 0.5f + 0.5f * FMath::Sin(Now * 7.f) : 0.f;
	FLinearColor HpTint = FLinearColor::White;
	if (bLow)
	{
		HpTint = FLinearColor(1.f, 0.85f + 0.15f * LowPulse, 0.85f + 0.15f * LowPulse, 1.f);
	}
	DrawSegmentBar(TEXT("BotHero_FillA"), Origin, K, 0, HpShown, HpTrail, HpTint);
	if (bLow)
	{
		// coração pulsando em vermelho
		const JRHudArt::FRect& Icon = JRHudArt::BotHeroBarAIcon;
		const FVector2D IC = PanelPoint(Origin, K, Icon.X + Icon.W * 0.5f, Icon.Y + Icon.H * 0.5f);
		const float GS = 110.f * K * (1.f + 0.15f * LowPulse);
		DrawTex(HudTex(TEXT("Glow")), IC.X - GS * 0.5f, IC.Y - GS * 0.5f, GS, GS, FLinearColor(1.f, 0.1f, 0.05f, 0.35f + 0.35f * LowPulse), FVector2D(0.f, 0.f), FVector2D(1.f, 1.f), true);
	}

	// ---- Fúria (barra verde do painel; na referência era STAMINA)
	UJRInventoryComponent* Bag = Hero->GetInventoryComponent();
	const float FuryLeft = Hero->GetFuryRemaining();
	const float FurySeconds = Bag ? FMath::Max(1.f, Bag->GetFurySeconds()) : 10.f;
	const float FuryPct = FuryLeft > 0.f ? FMath::Clamp(FuryLeft / FurySeconds, 0.f, 1.f) : 0.f;
	const float FuryShown = Smooth(TEXT("FuryShown"), FuryPct, 10.f, RealDelta);
	const FLinearColor FuryTint = FuryLeft > 0.f ? FLinearColor(1.f, 1.f, 1.f, 0.85f + 0.15f * FMath::Sin(Now * 10.f)) : FLinearColor::White;
	DrawSegmentBar(TEXT("BotHero_FillB"), Origin, K, 1, FuryShown, FuryShown, FuryTint);

	// ---- textos das barras
	const float LabelSize = 30.f * K;
	const float ValueSize = 22.f * K;
	auto LabelAt = [&](const JRHudArt::FRect& R, const FString& Label)
	{
		const FVector2D P = PanelPoint(Origin, K, R.X, R.Y + R.H * 0.5f);
		const float LH = MeasureText(Label, true, LabelSize).Y;
		DrawHudText(Label, P.X, P.Y - LH * 0.5f, LabelSize, TextColor, 0);
	};
	auto ValueAt = [&](const JRHudArt::FRect& R, const FString& Value, const FLinearColor& Color)
	{
		const FVector2D P = PanelPoint(Origin, K, R.X + R.W, R.Y + R.H * 0.5f);
		const float VH = MeasureText(Value, true, ValueSize).Y;
		DrawHudText(Value, P.X, P.Y - VH * 0.5f, ValueSize, Color, 2);
	};
	LabelAt(JRHudArt::BotHeroBarALabel, TEXT("VIDA"));
	ValueAt(JRHudArt::BotHeroBarAValue, FString::Printf(TEXT("%d / %d"), FMath::CeilToInt(Hp), FMath::CeilToInt(Health->GetMaxHealth())),
		bLow ? FLinearColor(1.f, 0.55f + 0.3f * LowPulse, 0.5f, 1.f) : SoftTextColor);
	LabelAt(JRHudArt::BotHeroBarBLabel, TEXT("FÚRIA"));
	const int32 FuryCharges = Bag ? Bag->GetCount(EJRConsumable::Fury) : 0;
	if (FuryLeft > 0.f)
	{
		ValueAt(JRHudArt::BotHeroBarBValue, FString::Printf(TEXT("ATIVA %ds"), FMath::CeilToInt(FuryLeft)), FLinearColor(0.85f, 1.f, 0.4f, 1.f));
	}
	else
	{
		ValueAt(JRHudArt::BotHeroBarBValue, FuryCharges > 0 ? FString::Printf(TEXT("GUARDADAS x%d"), FuryCharges) : FString(TEXT("VAZIA")), SoftTextColor);
	}
	if (FuryLeft > 0.f)
	{
		// borda roxa pulsando na tela
		const float A = 0.10f + 0.06f * FMath::Sin(Now * 6.f);
		for (int32 Side = 0; Side < 2; ++Side)
		{
			FCanvasTileItem EdgeTile(FVector2D(Side == 0 ? 0.f : Canvas->ClipX - 40.f * S, 0.f), FVector2D(40.f * S, Canvas->ClipY), Faded(FuryColor, A));
			EdgeTile.BlendMode = SE_BLEND_Translucent;
			Canvas->DrawItem(EdgeTile);
		}
	}

	DrawHealItems(Hero, Origin.X + 200.f * K, Origin.Y - 2.f * K, K);
	DrawHealProgress(Hero);
	DrawDamageIndicators(Hero);
}

void AJRHUD::DrawWeaponCard(AJRCharacter* Hero, float DeltaTime)
{
	const float K = S * HudScale;
	const float M = SafeMargin * S;
	const UJRWeaponComponent* Weapon = Hero->GetWeaponComponent();
	const FVector2D Origin(Canvas->ClipX - M - JRHudArt::WeaponSize.W * K, Canvas->ClipY - M - JRHudArt::WeaponSize.H * K);
	DrawTex(HudTex(TEXT("Weapon")), Origin.X, Origin.Y, JRHudArt::WeaponSize.W * K, JRHudArt::WeaponSize.H * K, FLinearColor::White);

	const EJRWeaponSlot Current = Hero->GetCurrentWeaponSlot();
	const TCHAR* Name = Current == EJRWeaponSlot::Melee ? TEXT("GRAVETO ALIEN") : Current == EJRWeaponSlot::Pistol ? TEXT("PISTOLA ALIEN")
		: Current == EJRWeaponSlot::Shotgun ? TEXT("ESCOPETA ALIEN") : Current == EJRWeaponSlot::Sniper ? TEXT("RIFLE ALIEN") : TEXT("DESARMADO");
	const TCHAR* Icon = Current == EJRWeaponSlot::Melee ? TEXT("Icon_Stick") : Current == EJRWeaponSlot::Pistol ? TEXT("Icon_Pistol")
		: Current == EJRWeaponSlot::Shotgun ? TEXT("Icon_Shotgun") : Current == EJRWeaponSlot::Sniper ? TEXT("Icon_Sniper") : TEXT("Icon_Hand");

	// ---- ícone da arma no anel (com uma "batida" ao trocar)
	const float LastSlotF = SmoothValues.FindOrAdd(TEXT("WeaponSlot"), static_cast<float>(Current));
	float Bump = SmoothValues.FindOrAdd(TEXT("WeaponBump"), 0.f);
	if (FMath::RoundToInt(LastSlotF) != static_cast<int32>(Current))
	{
		SmoothValues.Add(TEXT("WeaponSlot"), static_cast<float>(Current));
		Bump = 1.f;
	}
	Bump = FMath::Max(0.f, Bump - DeltaTime * 4.f);
	SmoothValues.Add(TEXT("WeaponBump"), Bump);
	const FVector2D Ring = PanelPoint(Origin, K, JRHudArt::WeaponRing.X, JRHudArt::WeaponRing.Y);
	const float IconSize = JRHudArt::WeaponRing.W * 2.05f * K * (1.f + 0.12f * Bump);
	DrawTex(HudTex(Icon), Ring.X - IconSize * 0.5f, Ring.Y - IconSize * 0.5f, IconSize, IconSize, FLinearColor::White);

	// ---- nome numa pílula verde-água no topo do miolo
	const JRHudArt::FRect& Body = JRHudArt::WeaponBody;
	const float NameSize = 26.f * K;
	const float NameW = MeasureText(Name, true, NameSize).X;
	const float PillH = 50.f * K;
	const float PillW = FMath::Min(PillWidthFor(TEXT("PillTeal"), PillH, NameW), Body.W * K);
	const FVector2D BodyP = PanelPoint(Origin, K, Body.X, Body.Y);
	const float PillX = BodyP.X + (Body.W * K - PillW) * 0.5f;
	DrawPill(TEXT("PillTeal"), PillX, BodyP.Y + 4.f * K, PillW, PillH, FLinearColor::White);
	const float NH = MeasureText(Name, true, NameSize).Y;
	DrawHudTextFit(Name, PillX + PillW * 0.5f, BodyP.Y + 4.f * K + PillH * 0.42f - NH * 0.5f, NameSize, PillW - 50.f * K, TextColor, 1);

	CrosshairBloomNow = Weapon->GetCrosshairBloom();
	const float RightX = BodyP.X + Body.W * K;
	const float RowY = BodyP.Y + 66.f * K;
	if (Hero->IsWeaponEquipped())
	{
		const FJRAmmoState Ammo = Weapon->GetAmmo();
		const FLinearColor MagColor = Ammo.Magazine == 0 ? HealthColor : TextColor;
		// munição grande: "12 / 48" alinhado à direita
		const FString ReserveText = FString::Printf(TEXT("/ %d"), Ammo.Reserve);
		const float BigSize = 60.f * K;
		const float SmallSize = 30.f * K;
		const float ReserveW = MeasureText(ReserveText, true, SmallSize).X;
		const float BigH = MeasureText(TEXT("0"), true, BigSize).Y;
		const float SmallH = MeasureText(TEXT("0"), true, SmallSize).Y;
		DrawHudText(ReserveText, RightX, RowY + BigH * 0.62f - SmallH * 0.62f, SmallSize, CyanText, 2);
		DrawHudText(FString::FromInt(Ammo.Magazine), RightX - ReserveW - 8.f * K, RowY, BigSize, MagColor, 2);
		DrawTex(HudTex(TEXT("Stat_Ammo")), BodyP.X + 4.f * K, RowY + 6.f * K, 46.f * K, 46.f * K, FLinearColor::White);
		DrawHudText(TEXT("MUNIÇÃO"), BodyP.X + 50.f * K, RowY + 14.f * K, 22.f * K, SoftTextColor, 0);

		// pente: pontinhos ciano (até 30) ou barra contínua
		const int32 MagSize = FMath::Max(1, Ammo.MagazineSize);
		const float PipY = RowY + BigH + 2.f * K;
		const float PipAreaW = Body.W * K - 8.f * K;
		const float Shown = Smooth(TEXT("MagShown"), static_cast<float>(Ammo.Magazine), 18.f, DeltaTime > 0.f ? DeltaTime : 1.f / 60.f);
		if (MagSize <= 30)
		{
			const float Gap = 4.f * K;
			const float PipW = FMath::Min(26.f * K, (PipAreaW - Gap * (MagSize - 1)) / static_cast<float>(MagSize));
			const float PipH = 14.f * K;
			const float StartX = RightX - (PipW * MagSize + Gap * (MagSize - 1));
			for (int32 Pip = 0; Pip < MagSize; ++Pip)
			{
				const float PX = StartX + Pip * (PipW + Gap);
				const float Fill = FMath::Clamp(Shown - static_cast<float>(Pip), 0.f, 1.f);
				DrawRounded(PX - 1.5f * K, PipY - 1.5f * K, PipW + 3.f * K, PipH + 3.f * K, 5.f * K, Faded(InkColor, 0.95f));
				DrawRounded(PX, PipY, PipW, PipH, 4.f * K, FLinearColor(FColor(52, 50, 92)));
				if (Fill > 0.f)
				{
					DrawRounded(PX, PipY, PipW, PipH, 4.f * K, Faded(AccentColor, Fill));
					DrawRounded(PX + 2.f * K, PipY + 2.f * K, PipW - 4.f * K, PipH * 0.35f, 2.f * K, FLinearColor(1.f, 1.f, 1.f, 0.35f * Fill));
				}
			}
		}
		else
		{
			const float BarH = 14.f * K;
			DrawRounded(RightX - PipAreaW, PipY, PipAreaW, BarH, BarH * 0.5f, FLinearColor(FColor(52, 50, 92)));
			DrawRounded(RightX - PipAreaW, PipY, PipAreaW * FMath::Clamp(Shown / MagSize, 0.f, 1.f), BarH, BarH * 0.5f, AccentColor);
		}
		// estado: recarregando / sem munição
		const float StateY = PipY + 22.f * K;
		if (Weapon->IsReloading())
		{
			const float Blink = 0.6f + 0.4f * FMath::Sin(static_cast<float>(GetWorld()->GetRealTimeSeconds()) * 9.f);
			DrawHudText(TEXT("RECARREGANDO..."), RightX, StateY, 22.f * K, Faded(CyanText, Blink), 2);
		}
		else if (Ammo.Magazine == 0)
		{
			if (Ammo.Reserve > 0)
			{
				const float KW = DrawKeyCap(TEXT("R"), RightX - 150.f * K, StateY - 2.f * K, 30.f * K);
				DrawHudText(TEXT("RECARREGAR"), RightX - 150.f * K + KW + 8.f * K, StateY, 22.f * K, HealthColor, 0);
			}
			else
			{
				DrawHudText(TEXT("SEM CÉLULAS"), RightX, StateY, 22.f * K, HealthColor, 2);
			}
		}
		if (Current == EJRWeaponSlot::Shotgun)
		{
			DrawShotgunCrosshair(Hero->IsAimHeld());
		}
		else if (Hero->GetScopeAlpha() > 0.5f)
		{
			// a retícula da luneta substitui a mira
		}
		else
		{
			DrawCrosshair(Hero->IsAimHeld(), Weapon->IsReloading());
		}
	}
	else
	{
		const FString Info = Current == EJRWeaponSlot::Melee ? TEXT("CORPO A CORPO") : TEXT("MÃOS LIVRES");
		DrawHudText(Info, RightX, RowY + 14.f * K, 32.f * K, SoftTextColor, 2);
		if (Current == EJRWeaponSlot::Melee)
		{
			// ponto discreto no centro para orientar o golpe
			DrawRounded(Canvas->ClipX * 0.5f - 4.f * S, Canvas->ClipY * 0.5f - 4.f * S, 8.f * S, 8.f * S, 4.f * S, Faded(InkColor, 0.7f));
			DrawRounded(Canvas->ClipX * 0.5f - 3.f * S, Canvas->ClipY * 0.5f - 3.f * S, 6.f * S, 6.f * S, 3.f * S, FLinearColor(1.f, 1.f, 1.f, 0.85f));
		}
	}
	DrawHitMarker(Weapon);

	// ---- atalhos em cima do cartão: [Q] trocar  [TAB] roda
	const float HintY = Origin.Y + 6.f * K;
	float HX = Origin.X + 230.f * K;
	HX += DrawKeyCap(TEXT("Q"), HX, HintY, 28.f * K) + 6.f * K;
	HX += DrawHudText(TEXT("trocar"), HX, HintY + 2.f * K, 19.f * K, SoftTextColor, 0, false) + 16.f * K;
	HX += DrawKeyCap(TEXT("TAB"), HX, HintY, 28.f * K) + 6.f * K;
	DrawHudText(TEXT("roda"), HX, HintY + 2.f * K, 19.f * K, SoftTextColor, 0, false);
}

void AJRHUD::DrawInteractionPrompt(AJRCharacter* Hero)
{
	const UJRInteractionComponent* Interaction = Hero->FindComponentByClass<UJRInteractionComponent>();
	AActor* Target = Interaction ? Interaction->FindInteractable() : nullptr;
	if (!Target || Hero->IsItemWheelOpen())
	{
		return;
	}
	const FString Text = IJRInteractable::Execute_GetInteractionText(Target).ToString();
	const FString Line = Text.IsEmpty() ? FString(TEXT("Interagir")) : Text;
	const float TextSize = 26.f * S;
	const float PillH = 58.f * S;
	const float KeyH = 40.f * S;
	const float TextW = MeasureText(Line, true, TextSize).X;
	const float PillW = PillWidthFor(TEXT("PillNavy"), PillH, TextW + KeyH + 14.f * S);
	const float BX = Canvas->ClipX * 0.5f - PillW * 0.5f;
	const float BY = Canvas->ClipY * 0.66f;
	DrawPill(TEXT("PillNavy"), BX, BY, PillW, PillH, FLinearColor::White);
	const float InnerX = BX + (PillW - (TextW + KeyH + 14.f * S)) * 0.5f;
	DrawKeyCap(TEXT("E"), InnerX, BY + PillH * 0.45f - KeyH * 0.5f, KeyH);
	const float TH = MeasureText(Line, true, TextSize).Y;
	DrawHudText(Line, InnerX + KeyH + 14.f * S, BY + PillH * 0.44f - TH * 0.5f, TextSize, TextColor, 0);
}

void AJRHUD::DrawVehicleHud(AJRVehiclePawn* Vehicle)
{
	const float K = S * HudScale;
	const float M = SafeMargin * S;
	const double RealNow = GetWorld()->GetRealTimeSeconds();
	const float Now = static_cast<float>(RealNow);
	const float Delta = FMath::Max(FMath::Clamp(static_cast<float>(GetWorld()->GetDeltaSeconds()), 0.f, 0.1f), 1.f / 120.f);
	const UJRVehicleDamageComponent* Damage = Vehicle->GetDamageComponent();
	const float Integrity = Damage ? Damage->GetIntegrity() : 1.f;
	if (LastIntegrity >= 0.f && Integrity < LastIntegrity - 0.001f)
	{
		TrailHold.Add(TEXT("Car"), RealNow + 0.35);
	}
	LastIntegrity = Integrity;
	const float CarShown = Smooth(TEXT("CarShown"), Integrity, 10.f, Delta);
	float CarTrail = SmoothValues.FindOrAdd(TEXT("CarTrail"), Integrity);
	if (CarTrail < CarShown)
	{
		CarTrail = CarShown;
	}
	else if (RealNow > TrailHold.FindRef(TEXT("Car")))
	{
		CarTrail = FMath::FInterpConstantTo(CarTrail, CarShown, Delta, 0.6f);
	}
	SmoothValues.Add(TEXT("CarTrail"), CarTrail);
	// [A-075] gasolina de verdade (tanque 0..1 do carro): reserva pisca, seco = VAZIO
	const bool bFuelMissing = Vehicle->IsEngineDead() || Vehicle->GetPendingRequiredItem() == FName(TEXT("Fuel"));
	const bool bFuelReserve = !bFuelMissing && Vehicle->IsFuelReserve();
	const float Fuel = Smooth(TEXT("FuelShown"), bFuelMissing ? 0.f : Vehicle->GetFuel(), 4.f, Delta);
	const float FuelPulse = (bFuelReserve || bFuelMissing) ? 0.5f + 0.5f * FMath::Sin(Now * (Vehicle->IsFuelSputtering() ? 11.f : 5.f)) : 0.f;
	const float Nitro = Smooth(TEXT("NitroShown"), Vehicle->GetNitro(), 14.f, Delta);

	const FVector2D Origin(M, Canvas->ClipY - M - JRHudArt::BotCarSize.H * K);
	DrawTex(HudTex(TEXT("BotCar")), Origin.X, Origin.Y, JRHudArt::BotCarSize.W * K, JRHudArt::BotCarSize.H * K, FLinearColor::White);
	const bool bLow = Integrity < 0.3f;
	const float LowPulse = bLow ? 0.5f + 0.5f * FMath::Sin(Now * 7.f) : 0.f;
	DrawContinuousBar(TEXT("BotCar_FillA"), Origin, K, 0, CarShown, CarTrail, bLow ? FLinearColor(1.f, 0.8f + 0.2f * LowPulse, 0.8f + 0.2f * LowPulse, 1.f) : FLinearColor::White);
	DrawContinuousBar(TEXT("BotCar_FillB"), Origin, K, 1, Fuel, Fuel,
		bFuelReserve ? FLinearColor(1.f, 0.55f + 0.45f * FuelPulse, 0.35f + 0.5f * FuelPulse, 1.f) : FLinearColor::White);
	const bool bNitroOn = Vehicle->IsNitroActive();
	DrawContinuousBar(TEXT("BotCar_FillC"), Origin, K, 2, Nitro, Nitro,
		bNitroOn ? FLinearColor(1.f, 1.f, 1.f, 0.8f + 0.2f * FMath::Sin(Now * 20.f)) : FLinearColor::White);
	if (bNitroOn)
	{
		const float* Span = JRHudArt::BotCarBarCSpan;
		const float GX = Span[0] + (Span[1] - Span[0]) * Nitro;
		const FVector2D GP = PanelPoint(Origin, K, GX, JRHudArt::BotCarBarC.Y + JRHudArt::BotCarBarC.H * 0.5f);
		const float GS = 90.f * K;
		DrawTex(HudTex(TEXT("Glow")), GP.X - GS * 0.5f, GP.Y - GS * 0.5f, GS, GS, FLinearColor(0.7f, 0.3f, 1.f, 0.7f), FVector2D(0.f, 0.f), FVector2D(1.f, 1.f), true);
	}

	const float LabelSize = 26.f * K;
	const float ValueSize = 21.f * K;
	auto LabelAt = [&](const JRHudArt::FRect& R, const FString& Label)
	{
		const FVector2D P = PanelPoint(Origin, K, R.X, R.Y + R.H * 0.5f);
		const float LH = MeasureText(Label, true, LabelSize).Y;
		DrawHudText(Label, P.X, P.Y - LH * 0.5f, LabelSize, TextColor, 0);
	};
	auto ValueAt = [&](const JRHudArt::FRect& R, const FString& Value, const FLinearColor& Color)
	{
		const FVector2D P = PanelPoint(Origin, K, R.X + R.W, R.Y + R.H * 0.5f);
		const float VH = MeasureText(Value, true, ValueSize).Y;
		DrawHudText(Value, P.X, P.Y - VH * 0.5f, ValueSize, Color, 2);
	};
	LabelAt(JRHudArt::BotCarBarALabel, TEXT("VIDA DO CARRO"));
	ValueAt(JRHudArt::BotCarBarAValue, FString::Printf(TEXT("%d%%"), FMath::RoundToInt(Integrity * 100.f)),
		bLow ? FLinearColor(1.f, 0.5f + 0.3f * LowPulse, 0.45f, 1.f) : SoftTextColor);
	LabelAt(JRHudArt::BotCarBarBLabel, TEXT("GASOLINA"));
	{
		FString FuelText = FString::Printf(TEXT("%d%%"), FMath::RoundToInt(Vehicle->GetFuel() * 100.f));
		if (bFuelMissing)
		{
			FuelText = TEXT("VAZIO");
		}
		else if (Vehicle->IsFuelSputtering())
		{
			FuelText = TEXT("SECANDO!");
		}
		else if (bFuelReserve)
		{
			FuelText = FString::Printf(TEXT("RESERVA %d%%"), FMath::RoundToInt(Vehicle->GetFuel() * 100.f));
		}
		ValueAt(JRHudArt::BotCarBarBValue, FuelText, (bFuelMissing || bFuelReserve)
			? FLinearColor(1.f, 0.45f + 0.35f * FuelPulse, 0.35f, 1.f) : SoftTextColor);
	}
	LabelAt(JRHudArt::BotCarBarCLabel, TEXT("NITRO"));
	ValueAt(JRHudArt::BotCarBarCValue, bNitroOn ? FString(TEXT("ATIVO!")) : FString::Printf(TEXT("%d%%"), FMath::RoundToInt(Vehicle->GetNitro() * 100.f)),
		bNitroOn ? FLinearColor(0.85f, 0.6f, 1.f, 1.f) : SoftTextColor);

	// ---- velocímetro: selo redondo no canto inferior direito, arco ciano pela velocidade
	const float Kmh = FMath::Abs(Vehicle->GetSpeedKmh());
	const float SpeedShown = Smooth(TEXT("SpeedShown"), Kmh, 8.f, Delta);
	const float BadgeSize = 230.f * K;
	const FVector2D BC(Canvas->ClipX - M - BadgeSize * 0.5f, Canvas->ClipY - M - BadgeSize * 0.5f);
	DrawTex(HudTex(TEXT("Badge")), BC.X - BadgeSize * 0.5f, BC.Y - BadgeSize * 0.5f, BadgeSize, BadgeSize, FLinearColor::White);
	const float ArcPct = FMath::Clamp(SpeedShown / FMath::Max(10.f, SpeedometerMaxKmh), 0.f, 1.f);
	const float ArcR = BadgeSize * 0.5f * (66.f / 92.f);
	DrawArc(BC, ArcR - 15.f * K, ArcR - 5.f * K, -135.f, 135.f, Faded(InkColor, 0.7f), 48);
	if (ArcPct > 0.f)
	{
		DrawArc(BC, ArcR - 14.f * K, ArcR - 6.f * K, -135.f, -135.f + 270.f * ArcPct,
			bNitroOn ? FLinearColor(0.75f, 0.35f, 1.f, 1.f) : FLinearColor(FColor(236, 252, 255)), 48);
	}
	const FString SpeedText = FString::FromInt(FMath::RoundToInt(SpeedShown));
	const float SH = MeasureText(SpeedText, true, 56.f * K).Y;
	DrawHudText(SpeedText, BC.X, BC.Y - SH * 0.62f, 56.f * K, TextColor, 1);
	DrawHudText(TEXT("km/h"), BC.X, BC.Y + 14.f * K, 22.f * K, SoftTextColor, 1);
	// [A-075] marcador de gasolina colado no velocímetro (lado esquerdo): ícone + barra vertical E..F
	{
		const float GW = 16.f * K;
		const float GH = BadgeSize * 0.62f;
		const float GX = BC.X - BadgeSize * 0.5f - GW - 14.f * K;
		const float GY = BC.Y - GH * 0.5f + 12.f * K;
		DrawRounded(GX - 3.f * K, GY - 3.f * K, GW + 6.f * K, GH + 6.f * K, 8.f * K, Faded(InkColor, 0.75f));
		const float FillH = GH * FMath::Clamp(Fuel, 0.f, 1.f);
		const FLinearColor FillColor = bFuelMissing ? HealthColor
			: (bFuelReserve ? FLinearColor(1.f, 0.5f + 0.4f * FuelPulse, 0.25f, 1.f) : FLinearColor(FColor(255, 214, 92)));
		if (FillH > 1.f)
		{
			DrawRounded(GX, GY + GH - FillH, GW, FillH, FMath::Min(6.f * K, FillH * 0.5f), FillColor);
		}
		// marca da reserva
		const float RY = GY + GH * (1.f - Vehicle->GetFuelReserveMark());
		DrawRounded(GX - 4.f * K, RY - 1.5f * K, GW + 8.f * K, 3.f * K, 1.5f * K, Faded(TextColor, 0.7f));
		DrawHudText(TEXT("F"), GX + GW * 0.5f, GY - 26.f * K, 18.f * K, SoftTextColor, 1);
		DrawHudText(TEXT("E"), GX + GW * 0.5f, GY + GH + 6.f * K, 18.f * K, (bFuelMissing || bFuelReserve) ? FillColor : SoftTextColor, 1);
		if (UTexture2D* FuelIcon = HudTex(TEXT("Icon_Fuel")))
		{
			const float IS = 34.f * K;
			const float IA = (bFuelMissing || bFuelReserve) ? 0.55f + 0.45f * FuelPulse : 0.9f;
			DrawTex(FuelIcon, GX + GW * 0.5f - IS * 0.5f, GY + GH + 28.f * K, IS, IS, FLinearColor(1.f, 1.f, 1.f, IA));
		}
	}
	// atalho do nitro
	const float KeyH = 30.f * K;
	const float KW = MeasureText(TEXT("SHIFT"), true, KeyH * 0.5f).X + KeyH * 0.55f;
	DrawKeyCap(TEXT("SHIFT"), BC.X - KW * 0.5f, BC.Y + BadgeSize * 0.5f - KeyH * 1.25f, KeyH);
}

void AJRHUD::DrawCrosshair(bool bAiming, bool bReloading)
{
	const float CX = Canvas->ClipX * 0.5f;
	const float CY = Canvas->ClipY * 0.5f;
	const float Gap = (bAiming ? 6.f : 14.f) * S + CrosshairBloomNow * 18.f * S; // abre com os tiros
	const float Len = 12.f * S;
	const float T = FMath::Max(2.f, 3.f * S);
	const FLinearColor C = bReloading ? FLinearColor(1.f, 1.f, 1.f, 0.35f) : FLinearColor::White;
	auto DrawTick = [&](float X, float Y, float W, float H)
	{
		DrawRounded(X - 1.5f, Y - 1.5f, W + 3.f, H + 3.f, FMath::Min(W, H) * 0.5f + 1.5f, Faded(InkColor, 0.75f * C.A));
		DrawRounded(X, Y, W, H, FMath::Min(W, H) * 0.5f, C);
	};
	DrawTick(CX - Gap - Len, CY - T * 0.5f, Len, T);
	DrawTick(CX + Gap, CY - T * 0.5f, Len, T);
	DrawTick(CX - T * 0.5f, CY - Gap - Len, T, Len);
	DrawTick(CX - T * 0.5f, CY + Gap, T, Len);
	DrawTick(CX - T * 0.5f, CY - T * 0.5f, T, T);
}

void AJRHUD::DrawShotgunCrosshair(bool bAiming)
{
	const float Size = (bAiming ? 70.f : 100.f) * S + CrosshairBloomNow * 45.f * S; // abre com os tiros
	DrawTex(HudTex(TEXT("Ring")), Canvas->ClipX * 0.5f - Size * 0.5f, Canvas->ClipY * 0.5f - Size * 0.5f, Size, Size, FLinearColor(1.f, 1.f, 1.f, 0.85f));
	DrawRounded(Canvas->ClipX * 0.5f - 4.f * S, Canvas->ClipY * 0.5f - 4.f * S, 8.f * S, 8.f * S, 4.f * S, Faded(InkColor, 0.7f));
	DrawRounded(Canvas->ClipX * 0.5f - 3.f * S, Canvas->ClipY * 0.5f - 3.f * S, 6.f * S, 6.f * S, 3.f * S, FLinearColor::White);
}

void AJRHUD::ShowToast(const FString& Text, FLinearColor Color)
{
	FToast T;
	T.Text = Text;
	T.Color = Color;
	T.Start = GetWorld() ? GetWorld()->GetRealTimeSeconds() : 0.0;
	Toasts.Add(T);
	UJRAudio::NotifyToast(this); // [Áudio/A-061] bipe (pula se outro som de interface acabou de tocar)
	if (Toasts.Num() > 4)
	{
		Toasts.RemoveAt(0);
	}
}

void AJRHUD::Toast(const UObject* WorldContext, const FString& Text, FLinearColor Color)
{
	const UWorld* World = WorldContext ? WorldContext->GetWorld() : nullptr;
	const APlayerController* PC = World ? World->GetFirstPlayerController() : nullptr;
	if (AJRHUD* Hud = PC ? Cast<AJRHUD>(PC->GetHUD()) : nullptr)
	{
		Hud->ShowToast(Text, Color);
	}
}

void AJRHUD::DrawToasts()
{
	const double Now = GetWorld()->GetRealTimeSeconds();
	Toasts.RemoveAll([Now](const FToast& T) { return Now - T.Start > 3.2; });
	const float TextSize = 23.f * S;
	const float PillH = 50.f * S;
	float Y = Canvas->ClipY * 0.73f;
	for (const FToast& T : Toasts)
	{
		const float Age = static_cast<float>(Now - T.Start);
		const float A = Age < 0.18f ? Age / 0.18f : (Age > 2.6f ? FMath::Max(0.f, (3.2f - Age) / 0.6f) : 1.f);
		const float Slide = (1.f - EaseOut(Age / 0.25f)) * 24.f * S;
		const float TextW = MeasureText(T.Text, true, TextSize).X;
		const float PillW = FMath::Min(PillWidthFor(TEXT("PillNavy"), PillH, TextW), Canvas->ClipX * 0.7f);
		const float PX = Canvas->ClipX * 0.5f - PillW * 0.5f;
		DrawPill(TEXT("PillNavy"), PX, Y + Slide, PillW, PillH, FLinearColor(1.f, 1.f, 1.f, A));
		FLinearColor C = T.Color;
		C.A = A;
		const float TH = MeasureText(T.Text, true, TextSize).Y;
		DrawHudTextFit(T.Text, Canvas->ClipX * 0.5f, Y + Slide + PillH * 0.44f - TH * 0.5f, TextSize, PillW - 46.f * S, C, 1);
		Y += PillH + 6.f * S;
	}
}

// ====================================================================== roda de itens e cura (A-055 / A-059)

void AJRHUD::DrawRotatedTex(UTexture2D* Tex, const FVector2D& Center, float Size, float AngleDeg, const FLinearColor& Color)
{
	if (!Tex || !Tex->GetResource())
	{
		return;
	}
	// Gira os 4 cantos na mão (tela: X direita, Y para baixo; ângulo positivo = sentido horário).
	const float Rad = FMath::DegreesToRadians(AngleDeg);
	const float CosA = FMath::Cos(Rad);
	const float SinA = FMath::Sin(Rad);
	const float Half = Size * 0.5f;
	auto RotCorner = [&](float LX, float LY)
	{
		return Center + FVector2D(LX * CosA - LY * SinA, LX * SinA + LY * CosA);
	};
	const FVector2D P00 = RotCorner(-Half, -Half);
	const FVector2D P10 = RotCorner(Half, -Half);
	const FVector2D P11 = RotCorner(Half, Half);
	const FVector2D P01 = RotCorner(-Half, Half);
	FCanvasTriangleItem Quad(P00, P10, P11, Tex->GetResource());
	Quad.TriangleList.Reset();
	FCanvasUVTri First;
	First.V0_Pos = P00; First.V0_UV = FVector2D(0.f, 0.f); First.V0_Color = Color;
	First.V1_Pos = P10; First.V1_UV = FVector2D(1.f, 0.f); First.V1_Color = Color;
	First.V2_Pos = P11; First.V2_UV = FVector2D(1.f, 1.f); First.V2_Color = Color;
	FCanvasUVTri Second;
	Second.V0_Pos = P00; Second.V0_UV = FVector2D(0.f, 0.f); Second.V0_Color = Color;
	Second.V1_Pos = P11; Second.V1_UV = FVector2D(1.f, 1.f); Second.V1_Color = Color;
	Second.V2_Pos = P01; Second.V2_UV = FVector2D(0.f, 1.f); Second.V2_Color = Color;
	Quad.TriangleList.Add(First);
	Quad.TriangleList.Add(Second);
	Quad.BlendMode = SE_BLEND_Translucent;
	Canvas->DrawItem(Quad);
}

void AJRHUD::DrawArc(const FVector2D& Center, float RIn, float ROut, float Deg0, float Deg1, const FLinearColor& Color, int32 Segments)
{
	if (ROut <= RIn || Deg1 <= Deg0)
	{
		return;
	}
	const int32 Steps = FMath::Max(1, Segments);
	auto PointAt = [&](float Deg, float Radius)
	{
		const float Rad = FMath::DegreesToRadians(Deg);
		return Center + FVector2D(FMath::Sin(Rad), -FMath::Cos(Rad)) * Radius;
	};
	TArray<FCanvasUVTri> Tris;
	Tris.Reserve(Steps * 2);
	for (int32 Step = 0; Step < Steps; ++Step)
	{
		const float A0 = Deg0 + (Deg1 - Deg0) * static_cast<float>(Step) / static_cast<float>(Steps);
		const float A1 = Deg0 + (Deg1 - Deg0) * static_cast<float>(Step + 1) / static_cast<float>(Steps);
		const FVector2D In0 = PointAt(A0, RIn);
		const FVector2D Out0 = PointAt(A0, ROut);
		const FVector2D In1 = PointAt(A1, RIn);
		const FVector2D Out1 = PointAt(A1, ROut);
		FCanvasUVTri Tri;
		Tri.V0_Color = Color; Tri.V1_Color = Color; Tri.V2_Color = Color;
		Tri.V0_UV = FVector2D(0.5f, 0.5f); Tri.V1_UV = FVector2D(0.5f, 0.5f); Tri.V2_UV = FVector2D(0.5f, 0.5f);
		Tri.V0_Pos = In0; Tri.V1_Pos = Out0; Tri.V2_Pos = Out1;
		Tris.Add(Tri);
		Tri.V0_Pos = In0; Tri.V1_Pos = Out1; Tri.V2_Pos = In1;
		Tris.Add(Tri);
	}
	UTexture2D* White = HudTex(TEXT("Circle"));
	if (White && White->GetResource())
	{
		// textura branca (centro do círculo) para poder usar mistura translúcida
		FCanvasTriangleItem Item(FVector2D::ZeroVector, FVector2D::ZeroVector, FVector2D::ZeroVector, White->GetResource());
		Item.TriangleList = MoveTemp(Tris);
		Item.BlendMode = SE_BLEND_Translucent;
		Canvas->DrawItem(Item);
	}
	else
	{
		Canvas->K2_DrawTriangle(nullptr, Tris);
	}
}

void AJRHUD::DrawItemWheel(AJRCharacter* Hero)
{
	// Tempo real: o jogo está em câmera lenta, a roda não.
	const double RealNow = GetWorld()->GetRealTimeSeconds();
	const float Appear = FMath::Clamp(static_cast<float>(RealNow - Hero->GetItemWheelOpenRealTime()) / 0.16f, 0.f, 1.f);
	const float Ease = EaseOut(Appear);
	const float TabT = FMath::Clamp(static_cast<float>(RealNow - Hero->GetItemWheelTabChangeRealTime()) / 0.2f, 0.f, 1.f);
	const float TabEase = EaseOut(TabT);
	const int32 Tab = Hero->GetItemWheelTab();
	const int32 Highlight = Hero->GetItemWheelHighlight();

	// ---- fundo escurecido
	FCanvasTileItem Dim(FVector2D::ZeroVector, FVector2D(Canvas->ClipX, Canvas->ClipY), Faded(InkColor, 0.55f * Ease));
	Dim.BlendMode = SE_BLEND_Translucent;
	Canvas->DrawItem(Dim);

	// ---- geometria: a textura tem 1254 px; a roda ocupa WheelScreenFraction da altura
	const float K = Canvas->ClipY * WheelScreenFraction / JRHudArt::WheelSize.H * (0.86f + 0.14f * Ease);
	const FVector2D Mid(Canvas->ClipX * 0.5f, Canvas->ClipY * 0.51f);
	const FVector2D TexCenter(JRHudArt::WheelCenter[0], JRHudArt::WheelCenter[1]);
	const FVector2D Origin = Mid - TexCenter * K;
	auto WheelPoint = [&](float RefX, float RefY) { return PanelPoint(Origin, K, RefX, RefY); };
	const FLinearColor Fade(1.f, 1.f, 1.f, Ease);
	DrawTex(HudTex(TEXT("Wheel")), Origin.X, Origin.Y, JRHudArt::WheelSize.W * K, JRHudArt::WheelSize.H * K, Fade);

	// ---- abas (cabeçalhos em cima da roda; Q / E / roda do mouse / RB / clique trocam)
	const TCHAR* TabNames[2] = { TEXT("ARMAS"), TEXT("CONSUMÍVEIS") };
	const float TabH = 80.f * K;
	const float TabTextSize = 38.f * K;
	const float TabY = WheelPoint(0.f, 0.f).Y + 2.f * K;
	float TabWs[2];
	for (int32 TabIndex = 0; TabIndex < 2; ++TabIndex)
	{
		TabWs[TabIndex] = FMath::Max(300.f * K, PillWidthFor(TEXT("PillTeal"), TabH, MeasureText(TabNames[TabIndex], true, TabTextSize).X));
	}
	const float TabGap = 14.f * K;
	const float TabsW = TabWs[0] + TabWs[1] + TabGap;
	float TabX = Mid.X - TabsW * 0.5f;
	const float TabTop = TabY - TabH - 22.f * K;
	for (int32 TabIndex = 0; TabIndex < 2; ++TabIndex)
	{
		const bool bActive = TabIndex == Tab;
		const float Lift = bActive ? 4.f * K : 0.f;
		DrawPill(bActive ? TEXT("PillTeal") : TEXT("PillLavender"), TabX, TabTop - Lift, TabWs[TabIndex], TabH, Faded(FLinearColor::White, Ease * (bActive ? 1.f : 0.85f)));
		const float TH = MeasureText(TabNames[TabIndex], true, TabTextSize).Y;
		DrawHudText(TabNames[TabIndex], TabX + TabWs[TabIndex] * 0.5f, TabTop - Lift + TabH * 0.42f - TH * 0.5f, TabTextSize,
			Faded(bActive ? TextColor : SoftTextColor, Ease), 1);
		TabX += TabWs[TabIndex] + TabGap;
	}
	const float KeyH = 52.f * K;
	DrawKeyCap(TEXT("Q"), Mid.X - TabsW * 0.5f - KeyH - 14.f * K, TabTop + TabH * 0.45f - KeyH * 0.5f, KeyH);
	DrawKeyCap(TEXT("E"), Mid.X + TabsW * 0.5f + 14.f * K, TabTop + TabH * 0.45f - KeyH * 0.5f, KeyH);

	// ---- setores
	FJRWheelEntryInfo Selected;
	UTexture2D* LockTex = HudTex(TEXT("Icon_Lock"));
	const float Pulse = 0.88f + 0.12f * FMath::Sin(static_cast<float>(RealNow) * 6.f);
	for (int32 Sector = 0; Sector < JRItemWheel::NumSectors; ++Sector)
	{
		const EJRWheelEntry Entry = Hero->GetItemWheelEntry(Sector);
		const FJRWheelEntryInfo Info = Hero->GetWheelEntryInfo(static_cast<int32>(Entry));
		const bool bSel = Sector == Highlight;
		if (bSel)
		{
			Selected = Info;
		}
		const bool bLocked = !Info.bEmpty && (!Info.bOwned || Info.bFuture);
		const JRHudArt::FRect& Cell = JRHudArt::WheelCellRect[Sector];
		const FVector2D CellP = WheelPoint(Cell.X, Cell.Y);
		const FString CellName = FString::Printf(TEXT("WheelCell%d_"), Sector);
		if (bSel)
		{
			DrawTex(HudTex(CellName + TEXT("Glow")), CellP.X, CellP.Y, Cell.W * K, Cell.H * K, Faded(FLinearColor::White, Ease * Pulse));
		}
		else if (Info.bEmpty || bLocked)
		{
			DrawTex(HudTex(CellName + TEXT("Mask")), CellP.X, CellP.Y, Cell.W * K, Cell.H * K, Faded(InkColor, Ease * (Info.bEmpty ? 0.45f : 0.3f)));
		}
		if (Info.bEmpty)
		{
			continue;
		}
		// ícone: no centro de massa do setor; ao trocar de aba entra deslizando de lado
		const JRHudArt::FRect& CC = JRHudArt::WheelCellCenter[Sector];
		const FVector2D Dir = (FVector2D(CC.X, CC.Y) - TexCenter).GetSafeNormal();
		const FVector2D Tangent(-Dir.Y, Dir.X);
		const FVector2D Slide = Tangent * (1.f - TabEase) * 60.f * K * static_cast<float>(Hero->GetItemWheelTabDirection());
		const FVector2D IconC = WheelPoint(CC.X, CC.Y) - Dir * 6.f * K + Slide;
		const float IconSize = 262.f * K * (bSel ? 1.1f : 1.f);
		const float IconAlpha = Ease * TabEase;
		FLinearColor IconTint = FLinearColor::White;
		if (bLocked)
		{
			IconTint = FLinearColor(0.32f, 0.3f, 0.42f, 0.75f); // "apagado": escuro e frio
		}
		DrawTex(HudTex(TEXT("Icon_") + Info.Icon.ToString()), IconC.X - IconSize * 0.5f, IconC.Y - IconSize * 0.5f, IconSize, IconSize, Faded(IconTint, IconAlpha));
		if (bLocked && LockTex)
		{
			const float LS = IconSize * 0.42f;
			DrawTex(LockTex, IconC.X + IconSize * 0.18f - LS * 0.5f, IconC.Y + IconSize * 0.16f - LS * 0.5f, LS, LS, Faded(FLinearColor::White, IconAlpha));
		}
		// quantidade (consumíveis) ou munição (armas de fogo)
		FString Amount;
		if (!bLocked && Info.Loaded >= 0)
		{
			Amount = FString::Printf(TEXT("%d/%d"), Info.Loaded, Info.Reserve);
		}
		else if (Info.Count >= 0)
		{
			Amount = FString::Printf(TEXT("x%d"), Info.Count);
		}
		if (!Amount.IsEmpty())
		{
			DrawHudText(Amount, IconC.X + IconSize * 0.36f, IconC.Y + IconSize * 0.22f, 30.f * K, Faded(bLocked ? LockedText : TextColor, IconAlpha), 2);
		}
		if (Info.bCurrent)
		{
			// na mão agora: luz ciano perto da borda de fora
			const FVector2D DotP = IconC + FVector2D(-IconSize * 0.36f, -IconSize * 0.3f);
			const float DS = 40.f * K;
			DrawTex(HudTex(TEXT("Glow")), DotP.X - DS, DotP.Y - DS, DS * 2.f, DS * 2.f, Faded(AccentColor, IconAlpha * 0.7f), FVector2D(0.f, 0.f), FVector2D(1.f, 1.f), true);
			DrawRounded(DotP.X - 14.f * K, DotP.Y - 14.f * K, 28.f * K, 28.f * K, 14.f * K, Faded(InkColor, IconAlpha));
			DrawRounded(DotP.X - 11.f * K, DotP.Y - 11.f * K, 22.f * K, 22.f * K, 11.f * K, Faded(TextColor, IconAlpha));
			DrawRounded(DotP.X - 7.f * K, DotP.Y - 7.f * K, 14.f * K, 14.f * K, 7.f * K, Faded(AccentColor, IconAlpha));
		}
	}

	// ---- ponteiro na borda do disco, apontando para o setor destacado
	const float HiDeg = JRItemWheel::SectorCenterDeg(Highlight);
	const FVector2D HiDir(FMath::Sin(FMath::DegreesToRadians(HiDeg)), -FMath::Cos(FMath::DegreesToRadians(HiDeg)));
	const float PointerR = (JRHudArt::WheelDiscRadius + 34.f) * K;
	DrawRotatedTex(HudTex(TEXT("Pointer")), Mid + HiDir * PointerR, 62.f * K, HiDeg - 90.f, Faded(FLinearColor::White, Ease));

	// ---- centro
	DrawWheelCenter(Selected, Mid, K, Ease * TabEase);

	// ---- dicas embaixo
	const float HintSize = 19.f * S;
	const float HintPillH = 44.f * S;
	const FString HintA = TEXT("mouse / analógico: escolher");
	const FString HintB = TEXT("soltar: usar");
	const FString HintC = TEXT("botão direito / B: cancelar");
	const float WA = MeasureText(HintA, false, HintSize).X;
	const float WB = MeasureText(HintB, false, HintSize).X;
	const float WC = MeasureText(HintC, false, HintSize).X;
	const float KeyCapW = 64.f * S;
	const float Inner = WA + WB + WC + KeyCapW + 70.f * S;
	const float HintPillW = PillWidthFor(TEXT("PillNavy"), HintPillH, Inner);
	const float HintY = FMath::Min(Canvas->ClipY - HintPillH - 8.f * S, WheelPoint(0.f, JRHudArt::WheelSize.H).Y + 4.f * S);
	const float HintX = Mid.X - HintPillW * 0.5f;
	DrawPill(TEXT("PillNavy"), HintX, HintY, HintPillW, HintPillH, Fade);
	float CursorX = HintX + (HintPillW - Inner) * 0.5f;
	const float TY = HintY + HintPillH * 0.44f - MeasureText(HintA, false, HintSize).Y * 0.5f;
	CursorX += DrawHudText(HintA, CursorX, TY, HintSize, Faded(SoftTextColor, Ease), 0, false) + 24.f * S;
	CursorX += DrawKeyCap(TEXT("TAB"), CursorX, HintY + HintPillH * 0.5f - 15.f * S, 30.f * S) + 6.f * S;
	CursorX += DrawHudText(HintB, CursorX, TY, HintSize, Faded(TextColor, Ease), 0, false) + 24.f * S;
	DrawHudText(HintC, CursorX, TY, HintSize, Faded(SoftTextColor, Ease), 0, false);
}

void AJRHUD::DrawWheelCenter(const FJRWheelEntryInfo& Info, const FVector2D& Mid, float K, float Alpha)
{
	if (Info.Name.IsEmpty())
	{
		return;
	}
	const float R = JRHudArt::WheelDiscRadius * K;
	const bool bLocked = !Info.bEmpty && (!Info.bOwned || Info.bFuture);
	// altura total do bloco (centralizado no disco)
	const float PanelW = R * 1.66f;
	const bool bHasAmount = Info.Loaded >= 0 || Info.Count >= 0 || Info.bKeyItem;
	const TArray<FString> DetailLines = Info.bHasStats ? TArray<FString>() : WrapText(Info.Detail, false, 25.f * K, PanelW - 44.f * K);
	const float ContentH = (bHasAmount ? 52.f * K : 0.f) + (Info.bHasStats ? 4.f * 44.f * K : DetailLines.Num() * 33.f * K) + 18.f * K;
	const float BlockH = 38.f * K + 76.f * K + 12.f * K + ContentH + 14.f * K + 30.f * K;
	// categoria
	float Y = Mid.Y - BlockH * 0.5f;
	if (!Info.Category.IsEmpty())
	{
		DrawHudText(Info.Category, Mid.X, Y, 27.f * K, Faded(CyanText, Alpha), 1);
	}
	Y += 38.f * K;
	// nome numa pílula verde-água
	const float NameSize = 46.f * K;
	const float PillH = 76.f * K;
	const float NameW = MeasureText(Info.Name, true, NameSize).X;
	const float PillW = FMath::Min(PillWidthFor(TEXT("PillTeal"), PillH, NameW), R * 1.78f);
	DrawPill(bLocked ? TEXT("PillLavender") : TEXT("PillTeal"), Mid.X - PillW * 0.5f, Y, PillW, PillH, Faded(FLinearColor::White, Alpha));
	const float NH = MeasureText(Info.Name, true, NameSize).Y;
	DrawHudTextFit(Info.Name, Mid.X, Y + PillH * 0.42f - NH * 0.5f, NameSize, PillW - 60.f * K, Faded(TextColor, Alpha), 1);
	Y += PillH + 12.f * K;

	const float PanelX = Mid.X - PanelW * 0.5f;
	const float RowX = PanelX + 22.f * K;
	const float RowRight = PanelX + PanelW - 20.f * K;
	float RowY = Y + 12.f * K;
	const float RowSize = 27.f * K;
	const float IconS = 42.f * K;
	// painel interno mais escuro (como na referência), na altura do conteúdo
	const float PanelTop = Y;
	DrawRounded(PanelX, Y, PanelW, ContentH, 22.f * K, Faded(InkColor, 0.35f * Alpha));

	// linha de quantidade: munição / na bolsa / status
	FString AmountLabel;
	FString AmountValue;
	if (Info.Loaded >= 0)
	{
		AmountLabel = TEXT("MUNIÇÃO:");
		AmountValue = FString::Printf(TEXT("%d / %d"), Info.Loaded, Info.Reserve);
	}
	else if (Info.Count >= 0)
	{
		AmountLabel = Info.Icon == FName(TEXT("Fury")) ? TEXT("CARGAS:") : TEXT("NA BOLSA:");
		AmountValue = Info.MaxCount > 0 ? FString::Printf(TEXT("%d / %d"), Info.Count, Info.MaxCount) : FString::FromInt(Info.Count);
	}
	else if (Info.bKeyItem)
	{
		AmountLabel = TEXT("STATUS:");
		AmountValue = Info.bOwned ? TEXT("NA MOCHILA") : TEXT("FALTA");
	}
	if (!AmountLabel.IsEmpty())
	{
		// munição: bala; consumíveis e itens-chave: o próprio ícone pequeno
		const FString RowIcon = Info.Loaded >= 0 ? FString(TEXT("Stat_Ammo")) : TEXT("Icon_") + Info.Icon.ToString();
		DrawTex(HudTex(RowIcon), RowX - 4.f * K, RowY - 4.f * K, IconS, IconS, Faded(FLinearColor::White, Alpha));
		DrawHudText(AmountLabel, RowX + IconS + 4.f * K, RowY + 2.f * K, RowSize, Faded(TextColor, Alpha), 0);
		DrawHudText(AmountValue, RowRight, RowY - 2.f * K, 34.f * K, Faded(Info.bOwned ? CyanText : LockedText, Alpha), 2);
		RowY += 52.f * K;
	}

	if (Info.bHasStats)
	{
		struct FStatRow { const TCHAR* Label; const TCHAR* IconName; float Value; };
		const FStatRow Rows[4] = {
			{ TEXT("DANO"), TEXT("Stat_Damage"), Info.StatDamage },
			{ TEXT("PRECISÃO"), TEXT("Stat_Accuracy"), Info.StatAccuracy },
			{ TEXT("CADÊNCIA"), TEXT("Stat_FireRate"), Info.StatFireRate },
			{ TEXT("ALCANCE"), TEXT("Stat_Range"), Info.StatRange } };
		const int32 NumSegs = 5;
		const float BarW = 160.f * K;
		const float SegGap = 4.f * K;
		const float SegW = (BarW - SegGap * (NumSegs - 1)) / static_cast<float>(NumSegs);
		const float SegH = 18.f * K;
		const float Skew = 6.f * K;
		for (const FStatRow& Row : Rows)
		{
			DrawTex(HudTex(Row.IconName), RowX - 4.f * K, RowY - 4.f * K, IconS, IconS, Faded(FLinearColor::White, Alpha));
			DrawHudText(Row.Label, RowX + IconS + 4.f * K, RowY, 24.f * K, Faded(TextColor, Alpha), 0, true);
			// barra de 5 segmentos inclinados (como na referência)
			const float BX = RowRight - BarW;
			const float BY = RowY + 6.f * K;
			DrawRounded(BX - 6.f * K, BY - 4.f * K, BarW + 12.f * K, SegH + 8.f * K, (SegH + 8.f * K) * 0.5f, Faded(InkColor, 0.85f * Alpha));
			const float Lit = Row.Value * static_cast<float>(NumSegs);
			TArray<FCanvasUVTri> Tris;
			for (int32 Seg = 0; Seg < NumSegs; ++Seg)
			{
				const float SX = BX + Seg * (SegW + SegGap);
				const float Fill = FMath::Clamp(Lit - static_cast<float>(Seg), 0.f, 1.f);
				const FLinearColor Off = FLinearColor(FColor(92, 84, 140));
				const FLinearColor TopC = FMath::Lerp(Off, FLinearColor(FColor(150, 255, 252)), Fill);
				const FLinearColor BotC = FMath::Lerp(Off * 0.75f, FLinearColor(FColor(30, 200, 214)), Fill);
				FCanvasUVTri T;
				T.V0_UV = FVector2D(0.5f, 0.5f); T.V1_UV = FVector2D(0.5f, 0.5f); T.V2_UV = FVector2D(0.5f, 0.5f);
				const FVector2D A(SX + Skew, BY);
				const FVector2D B(SX + SegW + Skew, BY);
				const FVector2D C2(SX + SegW - Skew, BY + SegH);
				const FVector2D D(SX - Skew, BY + SegH);
				T.V0_Pos = A; T.V1_Pos = B; T.V2_Pos = C2;
				T.V0_Color = Faded(TopC, Alpha); T.V1_Color = Faded(TopC, Alpha); T.V2_Color = Faded(BotC, Alpha);
				Tris.Add(T);
				T.V0_Pos = A; T.V1_Pos = C2; T.V2_Pos = D;
				T.V0_Color = Faded(TopC, Alpha); T.V1_Color = Faded(BotC, Alpha); T.V2_Color = Faded(BotC, Alpha);
				Tris.Add(T);
			}
			if (UTexture2D* White = HudTex(TEXT("Circle")))
			{
				FCanvasTriangleItem Item(FVector2D::ZeroVector, FVector2D::ZeroVector, FVector2D::ZeroVector, White->GetResource());
				Item.TriangleList = MoveTemp(Tris);
				Item.BlendMode = SE_BLEND_Translucent;
				Canvas->DrawItem(Item);
			}
			RowY += 44.f * K;
		}
	}
	else
	{
		// consumíveis, itens-chave e "Nada": descrição
		for (const FString& Line : DetailLines)
		{
			DrawHudText(Line, Mid.X, RowY, 25.f * K, Faded(SoftTextColor, Alpha), 1, false);
			RowY += 33.f * K;
		}
	}

	// ação (embaixo do disco)
	FString Action;
	FLinearColor ActionColor = YellowText;
	if (Info.bFuture)
	{
		Action = TEXT("EM BREVE");
		ActionColor = LockedText;
	}
	else if (Info.bKeyItem)
	{
		Action = Info.bOwned ? TEXT("USADO SOZINHO") : TEXT("BLOQUEADO");
		ActionColor = Info.bOwned ? SoftTextColor : LockedText;
	}
	else if (!Info.bOwned)
	{
		Action = TEXT("BLOQUEADO");
		ActionColor = LockedText;
	}
	else if (Info.bCurrent)
	{
		Action = TEXT("NA MÃO");
		ActionColor = CyanText;
	}
	else if (Info.Count >= 0)
	{
		Action = TEXT("SOLTE PARA USAR");
	}
	else
	{
		Action = TEXT("SOLTE PARA EQUIPAR");
	}
	DrawHudText(Action, Mid.X, PanelTop + ContentH + 12.f * K, 26.f * K, Faded(ActionColor, Alpha), 1);
}

void AJRHUD::DrawHealItems(AJRCharacter* Hero, float X, float Y, float K)
{
	const UJRInventoryComponent* Bag = Hero->GetInventoryComponent();
	if (!Bag)
	{
		return;
	}
	struct FChip
	{
		EJRConsumable Item;
		const TCHAR* Icon;
	};
	const FChip Chips[] = { { EJRConsumable::Bandage, TEXT("Icon_Bandage") }, { EJRConsumable::Medkit, TEXT("Icon_Medkit") } };
	const float ChipSize = 84.f * K;
	float CX = X;
	for (const FChip& Chip : Chips)
	{
		const int32 ItemCount = Bag->GetCount(Chip.Item);
		const float Alpha = ItemCount > 0 ? 1.f : 0.5f;
		DrawTex(HudTex(TEXT("Badge")), CX, Y - ChipSize, ChipSize, ChipSize, Faded(FLinearColor::White, ItemCount > 0 ? 1.f : 0.75f));
		const float IS = ChipSize * 0.78f;
		DrawTex(HudTex(Chip.Icon), CX + (ChipSize - IS) * 0.5f, Y - ChipSize + (ChipSize - IS) * 0.5f, IS, IS,
			ItemCount > 0 ? FLinearColor::White : FLinearColor(0.35f, 0.33f, 0.45f, 0.8f));
		DrawHudText(FString::Printf(TEXT("x%d"), ItemCount), CX + ChipSize * 0.98f, Y - ChipSize * 0.42f, 24.f * K, Faded(TextColor, Alpha), 2);
		CX += ChipSize + 8.f * K;
	}
	DrawKeyCap(TEXT("H"), CX + 4.f * K, Y - ChipSize * 0.5f - 15.f * K, 30.f * K);
	DrawHudText(TEXT("curar"), CX + 40.f * K, Y - ChipSize * 0.5f - 12.f * K, 19.f * K, SoftTextColor, 0, false);
}

void AJRHUD::DrawHealProgress(AJRCharacter* Hero)
{
	if (!Hero->IsHealing())
	{
		return;
	}
	const float Progress = Hero->GetHealProgress();
	const FVector2D Mid(Canvas->ClipX * 0.5f, Canvas->ClipY * 0.5f + 130.f * S);
	const float BadgeSize = 120.f * S;
	DrawTex(HudTex(TEXT("Badge")), Mid.X - BadgeSize * 0.5f, Mid.Y - BadgeSize * 0.5f, BadgeSize, BadgeSize, FLinearColor::White);
	const float RingR = BadgeSize * 0.5f * (66.f / 92.f);
	DrawArc(Mid, RingR - 9.f * S, RingR - 2.f * S, 0.f, 360.f, Faded(InkColor, 0.8f), 48);
	DrawArc(Mid, RingR - 8.f * S, RingR - 3.f * S, 0.f, 360.f * Progress, AccentColor, 48);
	const bool bMedkit = Hero->GetHealingItem() == EJRConsumable::Medkit;
	const float IconSize = BadgeSize * 0.62f;
	DrawTex(HudTex(bMedkit ? TEXT("Icon_Medkit") : TEXT("Icon_Bandage")), Mid.X - IconSize * 0.5f, Mid.Y - IconSize * 0.5f, IconSize, IconSize, FLinearColor::White);
	const FString Text = bMedkit ? TEXT("USANDO KIT MÉDICO...") : TEXT("ENROLANDO BANDAGEM...");
	const float TextSize = 21.f * S;
	const float PillH = 42.f * S;
	const float PillW = PillWidthFor(TEXT("PillNavy"), PillH, MeasureText(Text, true, TextSize).X);
	DrawPill(TEXT("PillNavy"), Mid.X - PillW * 0.5f, Mid.Y + BadgeSize * 0.5f + 4.f * S, PillW, PillH, FLinearColor::White);
	const float TH = MeasureText(Text, true, TextSize).Y;
	DrawHudText(Text, Mid.X, Mid.Y + BadgeSize * 0.5f + 4.f * S + PillH * 0.44f - TH * 0.5f, TextSize, TextColor, 1);
}

// ---------------------------------------------------------------- Sensação de combate (A-057)

void AJRHUD::DrawHitMarker(const UJRWeaponComponent* Weapon)
{
	if (!Weapon)
	{
		return;
	}
	const bool bKill = Weapon->WasLastHitKill();
	const float Life = bKill ? 0.45f : 0.22f;
	const float Since = static_cast<float>(GetWorld()->GetTimeSeconds() - Weapon->GetLastHitConfirmTime());
	if (Since < 0.f || Since > Life)
	{
		return;
	}
	const float Fade = 1.f - Since / Life;
	// O "X" nasce um pouco maior e encolhe (pop).
	const float Pop = 1.f + 0.35f * Fade * Fade;
	const float Inner = (bKill ? 9.f : 7.f) * S * Pop;
	const float Outer = (bKill ? 22.f : 15.f) * S * Pop;
	const float Thick = (bKill ? 3.5f : 2.5f) * S;
	const FLinearColor Color = bKill ? FLinearColor(1.f, 0.12f, 0.08f, Fade) : FLinearColor(1.f, 1.f, 1.f, Fade);
	const FVector2D C(Canvas->ClipX * 0.5f, Canvas->ClipY * 0.5f);
	for (int32 Corner = 0; Corner < 4; ++Corner)
	{
		const FVector2D D((Corner % 2 == 0) ? 0.7071f : -0.7071f, (Corner < 2) ? 0.7071f : -0.7071f);
		const FVector2D A = C + D * Inner;
		const FVector2D B = C + D * Outer;
		DrawLine(A.X + 1.f, A.Y + 1.f, B.X + 1.f, B.Y + 1.f, FLinearColor(0.f, 0.f, 0.f, 0.5f * Fade), Thick + 1.f);
		DrawLine(A.X, A.Y, B.X, B.Y, Color, Thick);
	}
}

void AJRHUD::DrawDamageIndicators(AJRCharacter* Hero)
{
	const UJRDamageFXComponent* DamageFX = Hero ? Hero->GetDamageFXComponent() : nullptr;
	if (!DamageFX || !PlayerOwner || !PlayerOwner->PlayerCameraManager)
	{
		return;
	}
	const double Now = GetWorld()->GetTimeSeconds();
	const float CamYaw = static_cast<float>(PlayerOwner->PlayerCameraManager->GetCameraRotation().Yaw);
	const FVector HeroLoc = Hero->GetActorLocation();
	const FVector2D Mid(Canvas->ClipX * 0.5f, Canvas->ClipY * 0.5f);
	for (const FJRDamageIndicator& Hit : DamageFX->GetRecentHits())
	{
		const float Age = static_cast<float>(Now - Hit.Time);
		const float Life = 1.4f;
		if (Age < 0.f || Age > Life)
		{
			continue;
		}
		const FVector ToSource = Hit.From - HeroLoc;
		if (ToSource.SizeSquared2D() < 1.f)
		{
			continue;
		}
		// Graus a partir do topo da tela, sentido horário (direita = +90): mesmo sistema do DrawArc.
		const float Rel = static_cast<float>(FRotator::NormalizeAxis(ToSource.Rotation().Yaw - static_cast<double>(CamYaw)));
		const float Alpha = 0.75f * (1.f - Age / Life);
		const float Width = 20.f + FMath::Clamp(Hit.Amount, 5.f, 40.f) * 0.4f;
		DrawArc(Mid, 150.f * S, 168.f * S, Rel - Width, Rel + Width, FLinearColor(0.9f, 0.05f, 0.02f, Alpha), 16);
	}
}

// ---------------------------------------------------------------- Luneta do rifle (A-058, gancho para restyle)

void AJRHUD::DrawSniperScope(AJRCharacter* Hero, float ScopeAlpha)
{
	if (!Hero || !Canvas)
	{
		return;
	}
	const float Fade = FMath::SmoothStep(0.f, 1.f, ScopeAlpha);
	const FVector2D Mid(Canvas->ClipX * 0.5f, Canvas->ClipY * 0.5f);
	const float Radius = Canvas->ClipY * 0.46f;
	const float Far = FMath::Sqrt(Canvas->ClipX * Canvas->ClipX + Canvas->ClipY * Canvas->ClipY) * 0.5f + 4.f;
	// Fora do círculo: preto; borda interna com sombra suave (vinheta).
	DrawArc(Mid, Radius, Far, 0.f, 360.f, FLinearColor(0.f, 0.f, 0.f, Fade), 64);
	DrawArc(Mid, Radius * 0.9f, Radius, 0.f, 360.f, FLinearColor(0.f, 0.f, 0.f, 0.45f * Fade), 64);
	DrawArc(Mid, Radius * 0.97f, Radius, 0.f, 360.f, FLinearColor(0.f, 0.f, 0.f, 0.5f * Fade), 64);
	if (Fade < 0.6f)
	{
		return; // retícula só quando já está dentro da luneta
	}
	const FLinearColor Ink(0.02f, 0.02f, 0.02f, 0.9f * Fade);
	const FLinearColor Dot(1.f, 0.15f, 0.1f, Fade);
	const float Thin = FMath::Max(1.f, 1.5f * S);
	const float Thick = FMath::Max(2.f, 4.f * S);
	const float Gap = 18.f * S;
	// Linhas grossas de fora e finas perto do centro.
	DrawLine(Mid.X - Radius, Mid.Y, Mid.X - Radius * 0.35f, Mid.Y, Ink, Thick);
	DrawLine(Mid.X + Radius * 0.35f, Mid.Y, Mid.X + Radius, Mid.Y, Ink, Thick);
	DrawLine(Mid.X, Mid.Y + Radius * 0.35f, Mid.X, Mid.Y + Radius, Ink, Thick);
	DrawLine(Mid.X - Radius * 0.35f, Mid.Y, Mid.X - Gap, Mid.Y, Ink, Thin);
	DrawLine(Mid.X + Gap, Mid.Y, Mid.X + Radius * 0.35f, Mid.Y, Ink, Thin);
	DrawLine(Mid.X, Mid.Y - Radius * 0.6f, Mid.X, Mid.Y - Gap, Ink, Thin);
	DrawLine(Mid.X, Mid.Y + Gap, Mid.X, Mid.Y + Radius * 0.35f, Ink, Thin);
	// Marcas de queda/distância embaixo.
	for (int32 Mark = 1; Mark <= 4; ++Mark)
	{
		const float Y = Mid.Y + Gap + Mark * 22.f * S;
		const float W = (10.f - Mark) * 2.f * S;
		DrawLine(Mid.X - W, Y, Mid.X + W, Y, Ink, Thin);
	}
	DrawRounded(Mid.X - 2.5f * S, Mid.Y - 2.5f * S, 5.f * S, 5.f * S, 2.5f * S, Dot);
	// Zoom e fôlego (embaixo à direita do círculo).
	const float Zoom = 90.f / FMath::Max(1.f, Hero->GetScopeFOV());
	DrawLabel(FString::Printf(TEXT("x%.1f"), Zoom), Mid.X + Radius * 0.55f, Mid.Y + Radius * 0.62f, 1.1f, FLinearColor(0.85f, 0.95f, 1.f, Fade));
	const float Breath = Hero->GetBreathFraction();
	if (Breath < 0.999f)
	{
		const float BW = 120.f * S;
		const float BX = Mid.X - BW * 0.5f, BY = Mid.Y + Radius * 0.78f;
		DrawRounded(BX, BY, BW, 6.f * S, 3.f * S, FLinearColor(0.f, 0.f, 0.f, 0.6f * Fade));
		DrawRounded(BX, BY, BW * Breath, 6.f * S, 3.f * S, FLinearColor(0.6f, 0.9f, 1.f, 0.9f * Fade));
	}
	DrawLabel(TEXT("[SHIFT] segurar a respiração   [RODA] zoom"), Mid.X, Mid.Y + Radius * 0.86f, 0.8f,
		FLinearColor(0.8f, 0.85f, 0.9f, 0.8f * Fade), true);
}

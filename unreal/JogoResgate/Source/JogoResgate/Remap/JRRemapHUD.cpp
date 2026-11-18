// Copyright utrazin. All Rights Reserved.

#include "Remap/JRRemapHUD.h"
#include "Characters/JRCharacter.h"
#include "Combat/JRWeaponComponent.h"
#include "Engine/Canvas.h"
#include "Engine/Engine.h"
#include "Engine/Font.h"
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

namespace
{
	const FLinearColor PanelColor(0.03f, 0.05f, 0.10f, 0.82f);
	const FLinearColor PanelEdge(0.25f, 0.9f, 1.f, 0.9f);
	const FLinearColor Gold(1.f, 0.82f, 0.25f);
	const FLinearColor Dim(0.62f, 0.66f, 0.75f);
	const FLinearColor Good(0.45f, 1.f, 0.6f);
	const FLinearColor Bad(1.f, 0.4f, 0.35f);
	const FLinearColor RarityColors[] = { FLinearColor(0.75f, 0.8f, 0.9f), FLinearColor(0.35f, 0.7f, 1.f), FLinearColor(0.8f, 0.45f, 1.f) };
}

void AJRRemapHUD::BeginPlay()
{
	Super::BeginPlay();
	// Tarefa no painel OBJETIVO (no lugar do texto do L01).
	if (AJRArenaDirector::FindInWorld(this))
	{
		SetCurrentTask(TEXT("Sobreviva às ondas. A nave de extração chega a cada 3 ondas"), nullptr, 0.f);
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
	const UJRRunSubsystem* Run = GetGameInstance() ? GetGameInstance()->GetSubsystem<UJRRunSubsystem>() : nullptr;
	if (Run && Run->HasReport() && !AJRArenaDirector::FindInWorld(this))
	{
		bReportOpen = true;
		ReportOpenedAt = FPlatformTime::Seconds();
	}
}

// ------------------------------------------------------------------ desenho básico

void AJRRemapHUD::Box(float X, float Y, float W, float H, const FLinearColor& Color)
{
	DrawRect(Color, X, Y, W, H);
}

void AJRRemapHUD::Text(const FString& Str, float X, float Y, const FLinearColor& Color, bool bBig, float Scale)
{
	UFont* Font = bBig ? GEngine->GetLargeFont() : GEngine->GetMediumFont();
	const float TextScale = U * Scale * (bBig ? 1.f : 1.15f);
	DrawText(Str, FLinearColor(0.f, 0.f, 0.f, 0.7f), X + 2.f * U, Y + 2.f * U, Font, TextScale);
	DrawText(Str, Color, X, Y, Font, TextScale);
}

FVector2D AJRRemapHUD::Measure(const FString& Str, bool bBig, float Scale)
{
	UFont* Font = bBig ? GEngine->GetLargeFont() : GEngine->GetMediumFont();
	float W = 0.f, H = 0.f;
	GetTextSize(Str, W, H, Font, U * Scale * (bBig ? 1.f : 1.15f));
	return FVector2D(W, H);
}

FString AJRRemapHUD::Num(int64 Value)
{
	FString Digits = FString::Printf(TEXT("%lld"), FMath::Abs(Value));
	FString Out;
	for (int32 i = 0; i < Digits.Len(); ++i)
	{
		if (i > 0 && (Digits.Len() - i) % 3 == 0)
		{
			Out.AppendChar(TEXT('.'));
		}
		Out.AppendChar(Digits[i]);
	}
	return Value < 0 ? TEXT("-") + Out : Out;
}

// ------------------------------------------------------------------ entrada

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
	for (int32 i = 0; i < FMath::Min(NumOptions, 5); ++i)
	{
		if (Pressed(Digits[i]) || Pressed(Pad[i]))
		{
			InOutSelected = i;
			return i;
		}
	}
	if (Pressed(EKeys::Up) || Pressed(EKeys::Left) || Pressed(EKeys::Gamepad_DPad_Up) || Pressed(EKeys::Gamepad_DPad_Left))
	{
		InOutSelected = (InOutSelected + NumOptions - 1) % NumOptions;
	}
	if (Pressed(EKeys::Down) || Pressed(EKeys::Right) || Pressed(EKeys::Gamepad_DPad_Down) || Pressed(EKeys::Gamepad_DPad_Right))
	{
		InOutSelected = (InOutSelected + 1) % NumOptions;
	}
	InOutSelected = FMath::Clamp(InOutSelected, 0, NumOptions - 1);
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

// ------------------------------------------------------------------ loja

void AJRRemapHUD::OpenShop(AJRShopkeeper* Shopkeeper)
{
	if (!Shopkeeper || bReportOpen)
	{
		return;
	}
	Shop = Shopkeeper;
	ShopSelected = 0;
	ShopFeedback.Reset();
	ShopGreeting = Shopkeeper->PickGreeting();
	ShopOpenedAt = FPlatformTime::Seconds();
	SetPawnInput(false);
}

void AJRRemapHUD::CloseShop()
{
	if (Shop.IsValid())
	{
		Shop.Reset();
		SetPawnInput(true);
	}
}

void AJRRemapHUD::BuildShopEntries(TArray<FShopEntry>& Out) const
{
	const AJRShopkeeper* Keeper = Shop.Get();
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
		struct FW { EJRWeaponSlot Slot; const TCHAR* Name; const TCHAR* Detail; };
		const FW Weapons[] = {
			{ EJRWeaponSlot::Shotgun, TEXT("Escopeta alienígena"), TEXT("Estrago de perto. A melhor para segurar ondas.") },
			{ EJRWeaponSlot::Sniper, TEXT("Rifle de precisão"), TEXT("Um tiro, um zumbi. Lento, para elites.") },
		};
		for (const FW& W : Weapons)
		{
			FShopEntry E;
			E.Label = W.Name;
			E.Detail = W.Detail;
			E.Price = FJRRemapRules::WeaponPrice(W.Slot);
			E.bAvailable = !Economy->OwnsWeapon(W.Slot);
			const EJRWeaponSlot Slot = W.Slot;
			E.Buy = [Economy, PC, Slot]()
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
			Out.Add(MoveTemp(E));
		}
		break;
	}
	case EJRShopType::Bancada:
	{
		const int32 Level = Economy->GetBenchLevel();
		FShopEntry E;
		E.Label = FString::Printf(TEXT("Calibrar armas: nível %d -> %d"), Level, Level + 1);
		E.Detail = FString::Printf(TEXT("Dano de todas as armas: +%d%% -> +%d%%"), Level * 10, (Level + 1) * 10);
		E.Price = Economy->GetNextBenchCost();
		E.Buy = [Economy, PC]()
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
		Out.Add(MoveTemp(E));
		break;
	}
	case EJRShopType::Portao:
	{
		const int32 MaxLevel = FMath::Clamp(1 + Economy->GetBestWave() / 6, 1, 5); // libera nível novo a cada 6 ondas de recorde
		for (int32 L = 1; L <= MaxLevel; ++L)
		{
			FShopEntry E;
			E.Label = FString::Printf(TEXT("Arena nível %d"), L);
			E.Detail = FString::Printf(TEXT("Zumbis com %.0f%% de vida, pagam %.0f%%"),
				FJRRemapRules::EnemyHealthScale(L) * 100.f, FJRRemapRules::CreditsPerCost(L) / 6.f * 100.f);
			E.Price = 0;
			E.Buy = [Run, PC, L]()
			{
				if (!Run)
				{
					return false;
				}
				Run->StartRun(L);
				UGameplayStatics::OpenLevel(PC, FName(FJRRemapRules::ArenaMap));
				return true;
			};
			Out.Add(MoveTemp(E));
		}
		if (MaxLevel < 5)
		{
			FShopEntry Locked;
			Locked.Label = FString::Printf(TEXT("Arena nível %d (bloqueada)"), MaxLevel + 1);
			Locked.Detail = FString::Printf(TEXT("Chegue à onda %d numa corrida"), MaxLevel * 6);
			Locked.bAvailable = false;
			Out.Add(MoveTemp(Locked));
		}
		break;
	}
	}
}

void AJRRemapHUD::DrawShop()
{
	AJRShopkeeper* Keeper = Shop.Get();
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
	const int64 Credits = Economy ? Economy->GetCredits() : 0;

	const int32 Choice = PollChoice(Entries.Num(), ShopSelected);
	const double Now = FPlatformTime::Seconds();
	if (Choice != INDEX_NONE && Entries.IsValidIndex(Choice))
	{
		FShopEntry& E = Entries[Choice];
		if (!E.bAvailable || !E.Buy)
		{
			ShopFeedback = TEXT("Isso não está disponível.");
			ShopFeedbackColor = Dim;
		}
		else if (E.Price > Credits)
		{
			ShopFeedback = FString::Printf(TEXT("Faltam %s créditos."), *Num(E.Price - Credits));
			ShopFeedbackColor = Bad;
		}
		else if (E.Buy())
		{
			ShopFeedback = E.Price > 0 ? FString::Printf(TEXT("Comprado: %s"), *E.Label) : FString(TEXT("Boa sorte lá fora."));
			ShopFeedbackColor = Good;
			Keeper->PlayTalk();
			if (APawn* Pawn = PlayerOwner ? PlayerOwner->GetPawn() : nullptr)
			{
				if (AJRCharacter* Hero = Cast<AJRCharacter>(Pawn))
				{
					Hero->PlayFeedback(0.25f, 0.f, 2.f);
				}
			}
		}
		ShopFeedbackUntil = Now + 2.5;
		Entries.Reset();
		BuildShopEntries(Entries); // preço/estado novos
	}

	// Painel à direita (o vendedor fica visível à esquerda).
	const float W = 620.f * U;
	const float RowH = 74.f * U;
	const float H = (150.f + 40.f) * U + RowH * Entries.Num();
	const float X = Canvas->ClipX - W - 60.f * U;
	const float Y = Canvas->ClipY * 0.5f - H * 0.5f;
	Box(X - 3.f * U, Y - 3.f * U, W + 6.f * U, H + 6.f * U, PanelEdge);
	Box(X, Y, W, H, PanelColor);
	Text(Keeper->GetDisplayName().ToString(), X + 24.f * U, Y + 16.f * U, Gold, true);
	if (!ShopGreeting.IsEmpty())
	{
		Text(FString::Printf(TEXT("\"%s\""), *ShopGreeting), X + 24.f * U, Y + 58.f * U, Dim, false, 0.9f);
	}
	Text(FString::Printf(TEXT("Seus créditos: %s"), *Num(Credits)), X + 24.f * U, Y + 96.f * U, FLinearColor::White);

	float RY = Y + 140.f * U;
	for (int32 i = 0; i < Entries.Num(); ++i)
	{
		const FShopEntry& E = Entries[i];
		const bool bSel = i == ShopSelected;
		const bool bAfford = E.Price <= Credits;
		if (bSel)
		{
			Box(X + 12.f * U, RY - 4.f * U, W - 24.f * U, RowH - 6.f * U, FLinearColor(0.2f, 0.6f, 0.8f, 0.25f));
		}
		const FLinearColor LabelColor = !E.bAvailable ? Dim : (bAfford ? FLinearColor::White : Bad);
		Text(FString::Printf(TEXT("%d  %s"), i + 1, *E.Label), X + 24.f * U, RY, LabelColor);
		Text(E.Detail, X + 58.f * U, RY + 30.f * U, Dim, false, 0.8f);
		FString PriceStr = !E.bAvailable ? FString(E.Price > 0 ? TEXT("COMPRADO") : TEXT("")) : (E.Price > 0 ? Num(E.Price) : FString(TEXT("IR")));
		const FVector2D PS = Measure(PriceStr);
		Text(PriceStr, X + W - 24.f * U - PS.X, RY, !E.bAvailable ? Dim : (bAfford ? Gold : Bad));
		RY += RowH;
	}
	if (!ShopFeedback.IsEmpty() && Now < ShopFeedbackUntil)
	{
		Text(ShopFeedback, X + 24.f * U, RY + 4.f * U, ShopFeedbackColor);
	}
	Text(TEXT("1-4 / setas + Enter: escolher     Q: sair"), X + 24.f * U, Y + H - 34.f * U, Dim, false, 0.75f);
}

// ------------------------------------------------------------------ carteira (cidade)

void AJRRemapHUD::DrawWallet()
{
	const UJREconomySubsystem* Economy = GetGameInstance()->GetSubsystem<UJREconomySubsystem>();
	if (!Economy)
	{
		return;
	}
	const FString L1 = FString::Printf(TEXT("Créditos  %s"), *Num(Economy->GetCredits()));
	const FString L2 = FString::Printf(TEXT("Bancada nível %d  (+%d%% dano)"), Economy->GetBenchLevel(), Economy->GetBenchLevel() * 10);
	const FString L3 = FString::Printf(TEXT("Recorde: onda %d"), Economy->GetBestWave());
	const float W = 360.f * U;
	const float X = Canvas->ClipX - W - 30.f * U;
	const float Y = 300.f * U; // abaixo do minimapa
	Box(X, Y, W, 120.f * U, PanelColor);
	Text(L1, X + 18.f * U, Y + 12.f * U, Gold, true, 0.9f);
	Text(L2, X + 18.f * U, Y + 56.f * U, FLinearColor::White, false, 0.85f);
	Text(L3, X + 18.f * U, Y + 86.f * U, Dim, false, 0.85f);
}

// ------------------------------------------------------------------ corrida (arena)

void AJRRemapHUD::DrawRunPanel()
{
	const UJRRunSubsystem* Run = GetGameInstance()->GetSubsystem<UJRRunSubsystem>();
	const AJRArenaDirector* Director = AJRArenaDirector::FindInWorld(this);
	if (!Run || !Director)
	{
		return;
	}
	const float CX = Canvas->ClipX * 0.5f;
	const float Y = 24.f * U;

	// Onda e quantos faltam
	FString Title = Run->GetWave() > 0 ? FString::Printf(TEXT("ONDA %d"), Run->GetWave()) : FString(TEXT("PREPARE-SE"));
	FString Sub;
	if (Director->IsEnded())
	{
		Sub = Run->IsRunActive() ? TEXT("") : TEXT("Fim da corrida");
	}
	else if (Director->IsInBreak())
	{
		Sub = FString::Printf(TEXT("próxima onda em %.0f s"), FMath::CeilToFloat(Director->GetBreakSecondsLeft()));
	}
	else
	{
		Sub = FString::Printf(TEXT("restam %d"), Director->GetEnemiesLeftInWave());
	}
	const FVector2D TS = Measure(Title, true, 1.1f);
	Text(Title, CX - TS.X * 0.5f, Y, FLinearColor(1.f, 0.45f, 0.35f), true, 1.1f);
	const FVector2D SS = Measure(Sub, false, 0.9f);
	Text(Sub, CX - SS.X * 0.5f, Y + 46.f * U, Dim, false, 0.9f);

	// Barra de energia (nível da corrida)
	const float BW = 520.f * U, BH = 16.f * U;
	const float BX = CX - BW * 0.5f, BY = Y + 84.f * U;
	const float Frac = FMath::Clamp(Run->GetEnergy() / FMath::Max(1.f, Run->GetEnergyNeeded()), 0.f, 1.f);
	Box(BX - 2.f * U, BY - 2.f * U, BW + 4.f * U, BH + 4.f * U, FLinearColor(0.f, 0.f, 0.f, 0.6f));
	Box(BX, BY, BW * Frac, BH, FLinearColor(0.7f, 0.4f, 1.f, 0.95f));
	const FString Lv = FString::Printf(TEXT("Nv %d"), Run->GetRunLevel());
	Text(Lv, BX - Measure(Lv, false, 0.85f).X - 10.f * U, BY - 6.f * U, FLinearColor(0.8f, 0.6f, 1.f), false, 0.85f);
	if (Run->GetPendingChoices() > 1 || (Run->GetPendingChoices() == 1 && !Run->IsChoosingCard()))
	{
		Text(FString::Printf(TEXT("+%d carta(s)"), Run->GetPendingChoices()), BX + BW + 10.f * U, BY - 6.f * U, Gold, false, 0.85f);
	}

	// Créditos da corrida e o contrato de morte (sempre visível, REMAP 7.5)
	const float PX = 30.f * U, PY = Canvas->ClipY * 0.30f;
	Box(PX, PY, 380.f * U, 104.f * U, PanelColor);
	Text(FString::Printf(TEXT("Corrida: %s créditos"), *Num(Run->GetRunCredits())), PX + 16.f * U, PY + 10.f * U, Gold, false, 0.95f);
	Text(FString::Printf(TEXT("Se morrer: fica com %s"), *Num(Run->GetCreditsIfDie())), PX + 16.f * U, PY + 42.f * U, Bad, false, 0.85f);
	Text(FString::Printf(TEXT("Abates %d   ·   Extração x%.2f"), Run->GetKills(),
		FJRRemapRules::ExtractionMultiplier(FMath::Max(3, (Run->GetWavesCleared() / 3 + 1) * 3))),
		PX + 16.f * U, PY + 70.f * U, Dim, false, 0.8f);
}

void AJRRemapHUD::DrawShipMarker()
{
	const AJRArenaDirector* Director = AJRArenaDirector::FindInWorld(this);
	const AJRExtractionShip* Ship = Director ? Director->GetActiveShip() : nullptr;
	if (!Ship || !PlayerOwner)
	{
		return;
	}
	const FVector WorldPos = Ship->GetActorLocation() + FVector(0.f, 0.f, 300.f);
	FVector Screen = Project(WorldPos, true);
	const float Margin = 60.f * U;
	// Atrás da câmera: Project devolve Z <= 0; manda para a borda de baixo.
	if (Screen.Z <= 0.f)
	{
		Screen.X = Canvas->ClipX - Screen.X;
		Screen.Y = Canvas->ClipY - Margin;
	}
	Screen.X = FMath::Clamp(Screen.X, Margin, Canvas->ClipX - Margin);
	Screen.Y = FMath::Clamp(Screen.Y, Margin + 120.f * U, Canvas->ClipY - Margin);
	const APawn* Pawn = PlayerOwner->GetPawn();
	const float Dist = Pawn ? FVector::Dist(Pawn->GetActorLocation(), Ship->GetActorLocation()) / 100.f : 0.f;
	const FLinearColor C(0.3f, 0.95f, 1.f);
	Box(Screen.X - 14.f * U, Screen.Y - 14.f * U, 28.f * U, 28.f * U, C);
	const FString L1 = FString::Printf(TEXT("NAVE  %.0f m"), Dist);
	const FString L2 = FString::Printf(TEXT("%.0f s  ·  x%.2f"), FMath::CeilToFloat(Ship->GetSecondsLeft()), Ship->GetMultiplier());
	Text(L1, Screen.X - Measure(L1, false, 0.9f).X * 0.5f, Screen.Y + 20.f * U, C, false, 0.9f);
	Text(L2, Screen.X - Measure(L2, false, 0.8f).X * 0.5f, Screen.Y + 48.f * U, FLinearColor::White, false, 0.8f);
}

void AJRRemapHUD::DrawCards()
{
	UJRRunSubsystem* Run = GetGameInstance()->GetSubsystem<UJRRunSubsystem>();
	AJRArenaDirector* Director = AJRArenaDirector::FindInWorld(this);
	if (!Run || !Director || !Run->IsChoosingCard())
	{
		return;
	}
	const TArray<EJRRunCard>& Cards = Run->GetOfferedCards();
	const int32 Choice = PollChoice(Cards.Num(), CardSelected);
	if (Choice != INDEX_NONE)
	{
		Director->ConfirmCard(Choice);
		CardSelected = 1;
		return;
	}
	Box(0.f, 0.f, Canvas->ClipX, Canvas->ClipY, FLinearColor(0.02f, 0.f, 0.06f, 0.55f));
	const FString Title = FString::Printf(TEXT("NÍVEL %d!  Escolha uma carta"), Run->GetRunLevel());
	const FVector2D TS = Measure(Title, true, 1.2f);
	Text(Title, Canvas->ClipX * 0.5f - TS.X * 0.5f, Canvas->ClipY * 0.18f, Gold, true, 1.2f);

	const float CW = 330.f * U, CH = 420.f * U, Gap = 40.f * U;
	const float Total = Cards.Num() * CW + (Cards.Num() - 1) * Gap;
	float X = Canvas->ClipX * 0.5f - Total * 0.5f;
	const float Y = Canvas->ClipY * 0.5f - CH * 0.5f + 30.f * U;
	for (int32 i = 0; i < Cards.Num(); ++i)
	{
		const EJRRunCard Card = Cards[i];
		const FLinearColor RC = RarityColors[FMath::Clamp(FJRRemapRules::CardRarity(Card), 0, 2)];
		const bool bSel = i == CardSelected;
		const float Lift = bSel ? -18.f * U : 0.f;
		Box(X - 4.f * U, Y - 4.f * U + Lift, CW + 8.f * U, CH + 8.f * U, bSel ? FLinearColor::White : RC);
		Box(X, Y + Lift, CW, CH, FLinearColor(0.06f, 0.07f, 0.13f, 0.97f));
		Box(X, Y + Lift, CW, 10.f * U, RC);
		const FString Key = FString::Printf(TEXT("%d"), i + 1);
		Text(Key, X + 18.f * U, Y + 20.f * U + Lift, Dim, true, 0.9f);
		const FString Name = FJRRemapRules::CardTitle(Card).ToString();
		Text(Name, X + CW * 0.5f - Measure(Name, true, 0.95f).X * 0.5f, Y + 130.f * U + Lift, RC, true, 0.95f);
		const FString Desc = FJRRemapRules::CardDescription(Card).ToString();
		// quebra simples em 2 linhas se for longa
		FString A = Desc, B;
		if (Measure(Desc, false, 0.9f).X > CW - 30.f * U)
		{
			int32 Cut = Desc.Len() / 2;
			while (Cut < Desc.Len() && Desc[Cut] != TEXT(' ')) { ++Cut; }
			A = Desc.Left(Cut);
			B = Desc.Mid(Cut + 1);
		}
		Text(A, X + CW * 0.5f - Measure(A, false, 0.9f).X * 0.5f, Y + 210.f * U + Lift, FLinearColor::White, false, 0.9f);
		if (!B.IsEmpty())
		{
			Text(B, X + CW * 0.5f - Measure(B, false, 0.9f).X * 0.5f, Y + 244.f * U + Lift, FLinearColor::White, false, 0.9f);
		}
		X += CW + Gap;
	}
	const FString Hint = TEXT("1 / 2 / 3   ou   setas + Enter");
	Text(Hint, Canvas->ClipX * 0.5f - Measure(Hint, false, 0.85f).X * 0.5f, Y + CH + 40.f * U, Dim, false, 0.85f);
}

// ------------------------------------------------------------------ relatório (cidade)

void AJRRemapHUD::DrawReport()
{
	UJRRunSubsystem* Run = GetGameInstance()->GetSubsystem<UJRRunSubsystem>();
	if (!Run || !Run->HasReport())
	{
		bReportOpen = false;
		return;
	}
	const bool bCanClose = FPlatformTime::Seconds() - ReportOpenedAt > 1.0;
	if (bCanClose && (Pressed(EKeys::Enter) || Pressed(EKeys::SpaceBar) || Pressed(EKeys::E) || Pressed(EKeys::Gamepad_FaceButton_Bottom)))
	{
		Run->ConsumeReport();
		bReportOpen = false;
		SetPawnInput(true);
		return;
	}
	SetPawnInput(false);
	const FJRRunReport& R = Run->GetReport();
	const float W = 640.f * U, H = 420.f * U;
	const float X = Canvas->ClipX * 0.5f - W * 0.5f, Y = Canvas->ClipY * 0.5f - H * 0.5f;
	Box(X - 3.f * U, Y - 3.f * U, W + 6.f * U, H + 6.f * U, R.bExtracted ? PanelEdge : Bad);
	Box(X, Y, W, H, PanelColor);
	const FString Title = R.bExtracted ? TEXT("EXTRAÇÃO CONCLUÍDA") : TEXT("VOCÊ CAIU");
	Text(Title, X + W * 0.5f - Measure(Title, true, 1.1f).X * 0.5f, Y + 22.f * U, R.bExtracted ? Good : Bad, true, 1.1f);
	float RY = Y + 100.f * U;
	auto Row = [&](const FString& L, const FString& V, const FLinearColor& C)
	{
		Text(L, X + 40.f * U, RY, Dim);
		Text(V, X + W - 40.f * U - Measure(V).X, RY, C);
		RY += 40.f * U;
	};
	Row(TEXT("Arena"), FString::Printf(TEXT("nível %d"), R.SectorLevel), FLinearColor::White);
	Row(TEXT("Ondas vencidas"), FString::Printf(TEXT("%d%s"), R.Waves, R.bNewRecord ? TEXT("  RECORDE!") : TEXT("")), R.bNewRecord ? Gold : FLinearColor::White);
	Row(TEXT("Abates"), FString::Printf(TEXT("%d"), R.Kills), FLinearColor::White);
	Row(TEXT("Nível da corrida"), FString::Printf(TEXT("%d"), R.RunLevel), FLinearColor::White);
	Row(TEXT("Créditos na corrida"), Num(R.CreditsEarned), FLinearColor::White);
	Row(R.bExtracted ? TEXT("Multiplicador da nave") : TEXT("Contrato de morte"),
		FString::Printf(TEXT("x%.2f"), R.Multiplier), R.bExtracted ? Good : Bad);
	Row(TEXT("Ficou com"), FString::Printf(TEXT("+%s"), *Num(R.CreditsKept)), Gold);
	if (bCanClose)
	{
		const FString Hint = TEXT("Enter / E para continuar");
		Text(Hint, X + W * 0.5f - Measure(Hint, false, 0.8f).X * 0.5f, Y + H - 40.f * U, Dim, false, 0.8f);
	}
}

// ------------------------------------------------------------------ principal

void AJRRemapHUD::DrawHUD()
{
	Super::DrawHUD();
	if (!Canvas || !PlayerOwner)
	{
		return;
	}
	U = Canvas->ClipY / 1080.f;
	const bool bArena = AJRArenaDirector::FindInWorld(this) != nullptr;
	if (bArena)
	{
		DrawRunPanel();
		DrawShipMarker();
		DrawCards();
	}
	else
	{
		DrawWallet();
		if (bReportOpen)
		{
			DrawReport();
		}
		else if (Shop.IsValid())
		{
			DrawShop();
		}
	}
}

// ------------------------------------------------------------------ console

void AJRRemapHUD::JRCreditos(int32 Amount)
{
	if (UJREconomySubsystem* Economy = GetGameInstance()->GetSubsystem<UJREconomySubsystem>())
	{
		Economy->AddCredits(Amount);
	}
}

void AJRRemapHUD::JRArena(int32 Level)
{
	if (UJRRunSubsystem* Run = GetGameInstance()->GetSubsystem<UJRRunSubsystem>())
	{
		Run->StartRun(FMath::Max(1, Level));
		UGameplayStatics::OpenLevel(this, FName(FJRRemapRules::ArenaMap));
	}
}

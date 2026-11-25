// Copyright utrazin. All Rights Reserved.

#include "Remap/JRArenaGenerator.h"
#include "Components/BoxComponent.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Components/PointLightComponent.h"
#include "Engine/CollisionProfile.h"
#include "Engine/Engine.h"
#include "Engine/GameInstance.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "Materials/MaterialInterface.h"
#include "EngineUtils.h"
#include "HAL/IConsoleManager.h"
#include "JogoResgate.h"
#include "Remap/JRArenaInteractives.h"
#include "Remap/JRRunSubsystem.h"
#include "UObject/ConstructorHelpers.h"

static TAutoConsoleVariable<int32> CVarJRArenaSeed(
	TEXT("jr.Arena.Seed"), 0,
	TEXT("[Remap F2] Semente da arena procedural (0 = sorteia). Depois use RestartLevel para remontar."),
	ECVF_Default);

static TAutoConsoleVariable<int32> CVarJRArenaShape(
	TEXT("jr.Arena.Shape"), -1,
	TEXT("[Remap F2] Molde da arena: -1 sorteia, 0 círculo, 1 cruz, 2 U, 3 dois pátios, 4 rua com becos."),
	ECVF_Default);

namespace JRArenaGeneratorPrivate
{
	static const TCHAR* UserProps = TEXT("/Game/Environment/User/Props");
	static const TCHAR* UserCon = TEXT("/Game/Environment/User/Construcoes");
	static const TCHAR* L01Props = TEXT("/Game/Environment/L01/Props");
	static const TCHAR* ZombieKit = TEXT("/Game/Environment/Quaternius/ZombieKit");
	static const TCHAR* CarsPack = TEXT("/Game/Environment/Quaternius/CarsPack");

	static FSoftObjectPath MeshPath(const TCHAR* Dir, const TCHAR* MeshName)
	{
		return FSoftObjectPath(FString::Printf(TEXT("%s/%s.%s"), Dir, MeshName, MeshName));
	}
}

AJRArenaGenerator::AJRArenaGenerator()
{
	PrimaryActorTick.bCanEverTick = false;
	USceneComponent* SceneRoot = CreateDefaultSubobject<USceneComponent>(TEXT("Raiz"));
	SceneRoot->SetMobility(EComponentMobility::Movable);
	RootComponent = SceneRoot;
	ChestClass = AJRArenaChest::StaticClass();

	static ConstructorHelpers::FObjectFinder<UStaticMesh> CubeFinder(TEXT("/Engine/BasicShapes/Cube.Cube"));
	if (CubeFinder.Succeeded())
	{
		FallbackCube = CubeFinder.Object;
	}

	using namespace JRArenaGeneratorPrivate;
	auto AddPiece = [this](const TCHAR* Dir, const TCHAR* MeshName, EJRArenaPieceUse PieceUse, float PieceWeight, bool bSmall,
		const TCHAR* PieceGroups)
	{
		FJRArenaKitPiece Piece;
		Piece.Mesh = TSoftObjectPtr<UStaticMesh>(MeshPath(Dir, MeshName));
		Piece.Use = PieceUse;
		Piece.Weight = PieceWeight;
		Piece.bCluster = bSmall;
		Piece.Groups = PieceGroups;
		Kit.Add(Piece);
	};
	// [A-086] Kit "Posto abandonado" só com modelos do usuário (todos texturizados).
	// [A-089] Cada peça diz onde pode ir. Casas/cabanas fechadas saíram da arena: parecem ter interior e não têm.
	// O posto fica (dá para passar por baixo da cobertura; a loja é de costas para o muro).
	static const TCHAR* UserNat = TEXT("/Game/Environment/User/Natureza");
	AddPiece(UserCon, TEXT("SM_CON_Conteiner"), EJRArenaPieceUse::High, 3.f, false, TEXT("Geral,Patio"));
	AddPiece(UserProps, TEXT("SM_PRP_CarroBatido1"), EJRArenaPieceUse::High, 3.f, false, TEXT("Geral,FerroVelho"));
	AddPiece(UserProps, TEXT("SM_PRP_CarroBatido2"), EJRArenaPieceUse::High, 3.f, false, TEXT("Geral,FerroVelho"));
	AddPiece(UserProps, TEXT("SM_PRP_Onibus"), EJRArenaPieceUse::High, 1.5f, false, TEXT("FerroVelho"));
	AddPiece(UserNat, TEXT("SM_NAT_Pedra3"), EJRArenaPieceUse::High, 1.5f, false, TEXT("Natureza"));
	AddPiece(UserNat, TEXT("SM_NAT_Penhasco"), EJRArenaPieceUse::High, 0.6f, false, TEXT("Natureza"));

	AddPiece(UserProps, TEXT("SM_PRP_Barricada"), EJRArenaPieceUse::Low, 3.f, false, TEXT("Geral,Acampamento"));
	AddPiece(UserCon, TEXT("SM_CON_Cerca"), EJRArenaPieceUse::Low, 2.f, false, TEXT("Geral,Acampamento"));
	AddPiece(UserNat, TEXT("SM_NAT_Tronco"), EJRArenaPieceUse::Low, 1.5f, false, TEXT("Geral,Natureza"));
	AddPiece(UserProps, TEXT("SM_PRP_Barril"), EJRArenaPieceUse::Low, 2.5f, true, TEXT("Geral,FerroVelho,Acampamento"));
	AddPiece(UserProps, TEXT("SM_PRP_Gerador"), EJRArenaPieceUse::Low, 1.5f, true, TEXT("Acampamento"));
	AddPiece(UserNat, TEXT("SM_NAT_Pedra2"), EJRArenaPieceUse::Low, 1.5f, true, TEXT("Geral,Natureza"));

	AddPiece(UserProps, TEXT("SM_PRP_Ossos"), EJRArenaPieceUse::Decor, 1.f, false, TEXT("Geral"));
	AddPiece(UserProps, TEXT("SM_PRP_Placa"), EJRArenaPieceUse::Decor, 0.5f, false, TEXT("Geral"));
	AddPiece(UserNat, TEXT("SM_NAT_Arbusto1"), EJRArenaPieceUse::Decor, 1.5f, false, TEXT("Geral"));
	AddPiece(UserNat, TEXT("SM_NAT_Arbusto2"), EJRArenaPieceUse::Decor, 1.5f, false, TEXT("Geral"));
	AddPiece(UserNat, TEXT("SM_NAT_Arbusto3"), EJRArenaPieceUse::Decor, 1.5f, false, TEXT("Geral"));
	AddPiece(UserNat, TEXT("SM_NAT_Cogumelos"), EJRArenaPieceUse::Decor, 1.f, false, TEXT("Geral"));
	AddPiece(UserNat, TEXT("SM_NAT_Flor"), EJRArenaPieceUse::Decor, 1.f, false, TEXT("Geral"));
	AddPiece(UserNat, TEXT("SM_NAT_Flor2"), EJRArenaPieceUse::Decor, 1.f, false, TEXT("Geral"));
	AddPiece(UserNat, TEXT("SM_NAT_Pedra1"), EJRArenaPieceUse::Decor, 1.f, false, TEXT("Geral"));

	static const TCHAR* Vila = TEXT("/Game/Environment/User/Vila");
	WallMesh = TSoftObjectPtr<UStaticMesh>(MeshPath(Vila, TEXT("SM_BLD_MuroArena")));
	TowerMesh = TSoftObjectPtr<UStaticMesh>(MeshPath(Vila, TEXT("SM_BLD_TorreArena")));
	GateMesh = TSoftObjectPtr<UStaticMesh>(MeshPath(Vila, TEXT("SM_BLD_PortaoArena")));
	for (const TCHAR* Far : { TEXT("SM_NAT_Penhasco"), TEXT("SM_NAT_Arvore1"), TEXT("SM_NAT_Arvore2"), TEXT("SM_NAT_Arvore3"),
		TEXT("SM_NAT_Arvore4"), TEXT("SM_NAT_Cogumelo"), TEXT("SM_NAT_Penhasco") })
	{
		BackdropMeshes.Add(TSoftObjectPtr<UStaticMesh>(MeshPath(UserNat, Far)));
	}

	CanopyMesh = TSoftObjectPtr<UStaticMesh>(MeshPath(UserCon, TEXT("SM_CON_PostoCobertura")));
	PumpMesh = TSoftObjectPtr<UStaticMesh>(MeshPath(UserCon, TEXT("SM_CON_PostoBomba")));
	StoreMesh = TSoftObjectPtr<UStaticMesh>(MeshPath(UserCon, TEXT("SM_CON_PostoLoja")));
	LampMesh = TSoftObjectPtr<UStaticMesh>(MeshPath(UserProps, TEXT("SM_PRP_Poste")));
}

AJRArenaGenerator* AJRArenaGenerator::FindInWorld(const UObject* WorldContext)
{
	const UWorld* Wld = GEngine ? GEngine->GetWorldFromContextObject(WorldContext, EGetWorldErrorMode::ReturnNull) : nullptr;
	if (!Wld)
	{
		return nullptr;
	}
	for (TActorIterator<AJRArenaGenerator> It(Wld); It; ++It)
	{
		return *It;
	}
	return nullptr;
}

void AJRArenaGenerator::BeginPlay()
{
	Super::BeginPlay();
	EnsureBuilt();
}

FVector AJRArenaGenerator::CellToWorld(const FIntPoint& Cell) const
{
	return GetActorLocation() + FVector((Cell.X - Layout.Start.X) * CellSize, (Cell.Y - Layout.Start.Y) * CellSize, 0.f);
}

void AJRArenaGenerator::EnsureBuilt()
{
	if (bBuilt || bBuilding)
	{
		return;
	}
	bBuilding = true;
	int32 SectorLevel = DefaultSectorLevel;
	if (const UGameInstance* GI = GetGameInstance())
	{
		const UJRRunSubsystem* Run = GI->GetSubsystem<UJRRunSubsystem>();
		if (Run && Run->IsRunActive())
		{
			SectorLevel = Run->GetSectorLevel();
		}
	}
	const int32 ConsoleSeed = CVarJRArenaSeed.GetValueOnGameThread();
	const int32 ForcedShape = CVarJRArenaShape.GetValueOnGameThread();
	int32 BaseSeed = ConsoleSeed;
	if (BaseSeed == 0)
	{
		const uint32 Mixed = static_cast<uint32>(FDateTime::Now().GetTicks()) ^ FPlatformTime::Cycles();
		BaseSeed = static_cast<int32>(Mixed & 0x7fffffffu);
	}
	BaseSeed = FMath::Max(1, BaseSeed);

	LoadKit();
	FString Problem;
	for (int32 Pass = 0; Pass < 3 && !bBuilt; ++Pass)
	{
		if (BuildOnce(BaseSeed + Pass * 101, SectorLevel, ForcedShape, Problem))
		{
			bBuilt = true;
		}
		else
		{
			UE_LOG(LogJR, Warning, TEXT("Arena: montagem recusada (%s), tentando outra semente"), *Problem);
			ClearArena();
		}
	}
	if (!bBuilt)
	{
		// Último recurso: aceita a montagem mesmo com aviso (melhor que arena vazia).
		BuildOnce(BaseSeed + 999, SectorLevel, ForcedShape, Problem);
		bBuilt = true;
		UE_LOG(LogJR, Error, TEXT("Arena: aceita com problema (%s)"), *Problem);
	}
	bBuilding = false;
	UE_LOG(LogJR, Log, TEXT("Arena: %s, molde %s, %d m, semente %d (pedida %d), nível %d, %d peças, %d surgimentos, %d pontos da nave\n%s"),
		*ThemeName, *GetShapeName(), GetArenaMeters(), Layout.Seed, ConsoleSeed, SectorLevel, PlacedPieces,
		SpawnPoints.Num(), ExtractionPoints.Num(), *Layout.ToAscii());
}

void AJRArenaGenerator::LoadKit()
{
	LoadedMeshes.Reset();
	LoadedUse.Reset();
	LoadedWeight.Reset();
	LoadedCluster.Reset();
	LoadedGroups.Reset();
	for (const FJRArenaKitPiece& Piece : Kit)
	{
		UStaticMesh* Loaded = Piece.Mesh.LoadSynchronous();
		if (!Loaded)
		{
			UE_LOG(LogJR, Warning, TEXT("Arena: peça do kit não carregou (%s)"), *Piece.Mesh.ToString());
			continue;
		}
		LoadedMeshes.Add(Loaded);
		LoadedUse.Add(Piece.Use);
		LoadedWeight.Add(FMath::Max(0.f, Piece.Weight));
		LoadedCluster.Add(Piece.bCluster);
		LoadedGroups.Add(Piece.Groups);
	}
	LoadedSpecial.Reset();
	LoadedSpecial.Add(CanopyMesh.LoadSynchronous());
	LoadedSpecial.Add(PumpMesh.LoadSynchronous());
	LoadedSpecial.Add(StoreMesh.LoadSynchronous());
	LoadedSpecial.Add(LampMesh.LoadSynchronous());
	LoadedSpecial.Add(WallMesh.LoadSynchronous());  // 4
	LoadedSpecial.Add(TowerMesh.LoadSynchronous()); // 5
	LoadedSpecial.Add(GateMesh.LoadSynchronous());  // 6
	LoadedBackdrop.Reset();
	for (const TSoftObjectPtr<UStaticMesh>& Far : BackdropMeshes)
	{
		if (UStaticMesh* M = Far.LoadSynchronous())
		{
			LoadedBackdrop.Add(M);
		}
	}
	if (!LoadedSpecial[4] || !LoadedSpecial[5])
	{
		UE_LOG(LogJR, Error, TEXT("Arena: muralha da vila não carregou (rode tools/unreal/import_user_assets.py)."));
	}
	UE_LOG(LogJR, Log, TEXT("Arena: %d de %d peças do kit carregadas"), LoadedMeshes.Num(), Kit.Num());
}

int32 AJRArenaGenerator::PickMeshStrict(EJRArenaPieceUse PieceUse, int32 ClusterMode, const TCHAR* Group) const
{
	auto Matches = [this, PieceUse, ClusterMode, Group](int32 i)
	{
		if (LoadedUse[i] != PieceUse || (ClusterMode >= 0 && LoadedCluster[i] != (ClusterMode == 1)))
		{
			return false;
		}
		return Group == nullptr || !LoadedGroups.IsValidIndex(i) || LoadedGroups[i].Contains(Group);
	};
	float Total = 0.f;
	for (int32 i = 0; i < LoadedMeshes.Num(); ++i)
	{
		if (Matches(i))
		{
			Total += LoadedWeight[i];
		}
	}
	if (Total <= 0.f)
	{
		return INDEX_NONE;
	}
	float Roll = DressRng.FRand() * Total;
	int32 Last = INDEX_NONE;
	for (int32 i = 0; i < LoadedMeshes.Num(); ++i)
	{
		if (Matches(i))
		{
			Last = i;
			Roll -= LoadedWeight[i];
			if (Roll <= 0.f)
			{
				return i;
			}
		}
	}
	return Last;
}

int32 AJRArenaGenerator::PickMesh(EJRArenaPieceUse PieceUse, int32 ClusterMode, const TCHAR* Group) const
{
	const int32 Found = PickMeshStrict(PieceUse, ClusterMode, Group);
	return (Found == INDEX_NONE && Group != nullptr) ? PickMeshStrict(PieceUse, ClusterMode, nullptr) : Found;
}

float AJRArenaGenerator::YawFacingIn(const FIntPoint& OutDir)
{
	return static_cast<float>(FMath::RadiansToDegrees(FMath::Atan2(static_cast<double>(-OutDir.Y), static_cast<double>(-OutDir.X))));
}

int32 AJRArenaGenerator::PlaceCluster(const FVector& Center, float Spread, int32 Count, const TCHAR* Group)
{
	int32 Placed = 0;
	const float StartAngle = DressRng.FRandRange(0.f, 360.f);
	for (int32 i = 0; i < Count; ++i)
	{
		const int32 Index = PickMesh(EJRArenaPieceUse::Low, 1, Group);
		if (Index == INDEX_NONE)
		{
			break;
		}
		const float Ang = FMath::DegreesToRadians(StartAngle + i * (360.f / FMath::Max(1, Count)) + DressRng.FRandRange(-20.f, 20.f));
		const float Rad = Count == 1 ? 0.f : Spread * DressRng.FRandRange(0.55f, 1.f);
		const FVector Pos = Center + FVector(FMath::Cos(Ang) * Rad, FMath::Sin(Ang) * Rad, 0.f);
		if (PlacePiece(LoadedMeshes[Index], Pos, DressRng.FRandRange(0.f, 360.f), FVector(120.f, 120.f, 170.f), 1.2f, 0.f, true, true))
		{
			++Placed;
		}
	}
	return Placed;
}

UInstancedStaticMeshComponent* AJRArenaGenerator::GetMeshComponent(UStaticMesh* InMesh, bool bCollide)
{
	for (int32 i = 0; i < MeshComponents.Num(); ++i)
	{
		UInstancedStaticMeshComponent* Existing = MeshComponents[i];
		if (Existing && Existing->GetStaticMesh() == InMesh && MeshComponentCollides.IsValidIndex(i) && MeshComponentCollides[i] == bCollide)
		{
			return Existing;
		}
	}
	UInstancedStaticMeshComponent* Comp = NewObject<UInstancedStaticMeshComponent>(this);
	Comp->SetMobility(EComponentMobility::Movable);
	Comp->SetStaticMesh(InMesh);
	// [A-086] colisão da própria malha (sem paredes invisíveis): o que se vê é o que bloqueia, e dá para subir em cima.
	if (bCollide)
	{
		Comp->SetCollisionProfileName(UCollisionProfile::BlockAll_ProfileName);
		Comp->SetCanEverAffectNavigation(true);
	}
	else
	{
		Comp->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		Comp->SetCanEverAffectNavigation(false);
	}
	Comp->SetupAttachment(GetRootComponent());
	Comp->RegisterComponent();
	AddInstanceComponent(Comp);
	MeshComponents.Add(Comp);
	MeshComponentCollides.Add(bCollide);
	return Comp;
}

void AJRArenaGenerator::AddBlocker(const FVector& Center, const FVector& HalfExtent, float Yaw)
{
	const FTransform ActorXf = GetActorTransform();
	UBoxComponent* BoxComp = NewObject<UBoxComponent>(this);
	BoxComp->SetMobility(EComponentMobility::Movable);
	BoxComp->SetBoxExtent(HalfExtent, false);
	BoxComp->SetCollisionProfileName(UCollisionProfile::BlockAll_ProfileName);
	BoxComp->SetCanEverAffectNavigation(true);
	BoxComp->SetHiddenInGame(true);
	BoxComp->SetupAttachment(GetRootComponent());
	BoxComp->SetRelativeLocationAndRotation(ActorXf.InverseTransformPosition(Center),
		ActorXf.InverseTransformRotation(FRotator(0.f, Yaw, 0.f).Quaternion()));
	BoxComp->RegisterComponent();
	AddInstanceComponent(BoxComp);
	Blockers.Add(BoxComp);
}

void AJRArenaGenerator::TrackArea(const FVector& Center, const FVector& HalfExtent, float Yaw)
{
	const double Rad = FMath::DegreesToRadians(static_cast<double>(Yaw));
	const double CosA = FMath::Abs(FMath::Cos(Rad));
	const double SinA = FMath::Abs(FMath::Sin(Rad));
	const double AX = CosA * HalfExtent.X + SinA * HalfExtent.Y;
	const double AY = SinA * HalfExtent.X + CosA * HalfExtent.Y;
	PieceAreas.Add(FBox2D(FVector2D(Center.X - AX, Center.Y - AY), FVector2D(Center.X + AX, Center.Y + AY)));
}

bool AJRArenaGenerator::PlacePiece(UStaticMesh* InMesh, const FVector& Center, float Yaw, const FVector& Fit, float MaxScale,
	float MinCollisionHeight, bool bCollision, bool bTrackOverlap)
{
	if (!InMesh)
	{
		return false;
	}
	const FBox LocalBox = InMesh->GetBoundingBox();
	const FVector Ext = LocalBox.GetSize();
	if (Ext.X < 1.0 || Ext.Y < 1.0 || Ext.Z < 1.0)
	{
		return false;
	}
	// O lado comprido da malha vai na direção Yaw.
	const bool bLongIsY = Ext.Y > Ext.X;
	const double LongSide = bLongIsY ? Ext.Y : Ext.X;
	const double ShortSide = bLongIsY ? Ext.X : Ext.Y;
	double PieceScale = FMath::Min3(Fit.X / LongSide, Fit.Y / ShortSide, Fit.Z / Ext.Z);
	PieceScale = FMath::Min(PieceScale, static_cast<double>(MaxScale));
	if (PieceScale < 0.45)
	{
		return false; // não cabe sem ficar ridícula
	}
	const float FinalYaw = Yaw + (bLongIsY ? -90.f : 0.f);
	const FRotator Rot(0.f, FinalYaw, 0.f);
	const FVector LocalCenter = LocalBox.GetCenter() * PieceScale;
	FVector Loc = Center - Rot.RotateVector(FVector(LocalCenter.X, LocalCenter.Y, 0.0));
	Loc.Z = GetActorLocation().Z - LocalBox.Min.Z * PieceScale;
	GetMeshComponent(InMesh, bCollision)->AddInstance(FTransform(Rot, Loc, FVector(PieceScale)), true);
	++PlacedPieces;

	const FVector Half = Ext * PieceScale * 0.5;
	(void)MinCollisionHeight; // [A-086] a colisão agora é a da malha (sem caixa invisível mais alta)
	if (bTrackOverlap)
	{
		TrackArea(Center, Half, FinalYaw);
	}
	return true;
}

void AJRArenaGenerator::PlaceBlock(const FVector& Center, const FVector& BlockSize, float Yaw, bool bTrackOverlap)
{
	// [A-086] plano B sem cubo branco e sem parede invisível: 2 ou 3 barris/barricadas no lugar.
	const int32 Index = PickMesh(EJRArenaPieceUse::Low, 1);
	if (Index == INDEX_NONE)
	{
		return;
	}
	const int32 Count = DressRng.RandRange(2, 3);
	const FVector Along = FRotator(0.f, Yaw, 0.f).RotateVector(FVector(1.f, 0.f, 0.f));
	for (int32 i = 0; i < Count; ++i)
	{
		const float T = Count == 1 ? 0.f : (static_cast<float>(i) / (Count - 1) - 0.5f);
		PlacePiece(LoadedMeshes[Index], Center + Along * (T * FMath::Min(BlockSize.X, 300.f)), DressRng.FRandRange(0.f, 360.f),
			FVector(110.f, 110.f, 160.f), 1.3f, 0.f, true, bTrackOverlap);
	}
}

void AJRArenaGenerator::AddLight(const FVector& Location, const FLinearColor& Color, float Intensity, float Radius)
{
	const FTransform ActorXf = GetActorTransform();
	UPointLightComponent* LightComp = NewObject<UPointLightComponent>(this);
	LightComp->SetMobility(EComponentMobility::Movable);
	// [A-088] sem unidade o componente usa Unitless (4500 = menos de 15 cd): arena preta. Valores agora em candelas.
	LightComp->SetIntensityUnits(ELightUnits::Candelas);
	LightComp->SetIntensity(Intensity);
	LightComp->SetAttenuationRadius(Radius);
	LightComp->SetLightColor(Color);
	LightComp->SetCastShadows(false);
	LightComp->SetupAttachment(GetRootComponent());
	LightComp->SetRelativeLocation(ActorXf.InverseTransformPosition(Location));
	LightComp->RegisterComponent();
	AddInstanceComponent(LightComp);
	ArenaLights.Add(LightComp);
}

bool AJRArenaGenerator::BuildOnce(int32 BaseSeed, int32 SectorLevel, int32 ForcedShape, FString& OutProblem)
{
	int32 Attempts = 0;
	FString LayoutProblem;
	if (!FJRArenaLayout::GenerateWithRetries(BaseSeed, SectorLevel, ForcedShape, MaxAttempts, Layout, Attempts, LayoutProblem))
	{
		OutProblem = FString::Printf(TEXT("planta: %s"), *LayoutProblem);
		return false;
	}
	if (Attempts > 1)
	{
		UE_LOG(LogJR, Log, TEXT("Arena: planta aceita na tentativa %d (última recusa: %s)"), Attempts, *LayoutProblem);
	}
	DressRng.Initialize(Layout.Seed ^ 0x2F6B1D3);
	PlacedPieces = 0;
	PieceAreas.Reset();
	BuildCover();
	BuildAssemblies();
	BuildBorder();
	BuildDecor();
	if (!CheckOverlaps(OutProblem))
	{
		return false;
	}
	SpawnChests();

	SpawnPoints.Reset();
	ExtractionPoints.Reset();
	ObjectivePoints.Reset();
	for (const FIntPoint& Cell : Layout.SpawnCells)
	{
		SpawnPoints.Add(CellToWorld(Cell) + FVector(DressRng.FRandRange(-150.f, 150.f), DressRng.FRandRange(-150.f, 150.f), 0.f));
	}
	for (const FIntPoint& Cell : Layout.ExtractionCells)
	{
		ExtractionPoints.Add(CellToWorld(Cell));
	}
	for (const FIntPoint& Cell : Layout.ObjectiveCells)
	{
		ObjectivePoints.Add(CellToWorld(Cell));
	}
	return true;
}

void AJRArenaGenerator::BuildCover()
{
	const float C = CellSize;
	for (int32 X = 0; X < Layout.Grid; ++X)
	{
		for (int32 Y = 0; Y < Layout.Grid; ++Y)
		{
			const EJRArenaCell Kind = Layout.Get(X, Y);
			if ((Kind != EJRArenaCell::Low && Kind != EJRArenaCell::High) || Layout.GetAssemblyIndex(X, Y) >= 0)
			{
				continue; // [A-089] conjuntos temáticos: BuildAssemblies
			}
			const bool bPillar = Layout.GetTag(X, Y) == EJRArenaCellTag::Pillar;
			const FVector CellCenter = CellToWorld(FIntPoint(X, Y));
			const FVector Jitter(DressRng.FRandRange(-0.04f, 0.04f) * C, DressRng.FRandRange(-0.04f, 0.04f) * C, 0.f);
			if (Kind == EJRArenaCell::High)
			{
				// Linha de coberturas altas: todas no mesmo sentido (parece um muro de carros/contêineres).
				float Yaw = DressRng.RandRange(0, 1) * 90.f;
				if (Layout.Get(X + 1, Y) == EJRArenaCell::High || Layout.Get(X - 1, Y) == EJRArenaCell::High)
				{
					Yaw = 0.f;
				}
				else if (Layout.Get(X, Y + 1) == EJRArenaCell::High || Layout.Get(X, Y - 1) == EJRArenaCell::High)
				{
					Yaw = 90.f;
				}
				Yaw += DressRng.FRandRange(-6.f, 6.f) + (DressRng.FRand() < 0.5f ? 180.f : 0.f);
				bool bPlaced = false;
				for (int32 Try = 0; Try < 4 && !bPlaced; ++Try)
				{
					if (bPillar)
					{
						// [A-089] quebra de visão no meio da arena: formação natural (rocha grande), nunca prédio/carro
						const int32 Index = PickMesh(EJRArenaPieceUse::High, 0, TEXT("Natureza"));
						bPlaced = Index != INDEX_NONE && PlacePiece(LoadedMeshes[Index], CellCenter + Jitter, DressRng.FRandRange(0.f, 360.f),
							FVector(0.7f * C, 0.7f * C, 700.f), 1.8f, 0.f, true, true);
						continue;
					}
					const int32 Index = PickMesh(EJRArenaPieceUse::High, 0, TEXT("Geral"));
					bPlaced = Index != INDEX_NONE && PlacePiece(LoadedMeshes[Index], CellCenter + Jitter, Yaw,
						FVector(0.85f * C, 0.6f * C, 650.f), 1.2f, 160.f, true, true);
				}
				if (!bPlaced)
				{
					PlaceBlock(CellCenter, FVector(0.75f * C, 0.4f * C, 280.f), Yaw, true);
				}
				continue;
			}

			// Cobertura baixa: uma peça inteira ou 2 a 4 peças pequenas.
			const bool bCluster = DressRng.FRand() < 0.4f && PickMesh(EJRArenaPieceUse::Low, 1, TEXT("Geral")) != INDEX_NONE;
			if (bCluster)
			{
				TArray<int32> Slots = { 0, 1, 2, 3, 4, 5, 6, 7, 8 };
				for (int32 i = Slots.Num() - 1; i > 0; --i)
				{
					Slots.Swap(i, DressRng.RandRange(0, i));
				}
				const int32 Count = DressRng.RandRange(2, 4);
				const float Sub = C / 3.f;
				int32 Placed = 0;
				for (int32 k = 0; k < Slots.Num() && Placed < Count; ++k)
				{
					const int32 Slot = Slots[k];
					const FVector SubCenter = CellCenter + FVector((Slot % 3 - 1) * Sub, (Slot / 3 - 1) * Sub, 0.f);
					const int32 Index = PickMesh(EJRArenaPieceUse::Low, 1, TEXT("Geral"));
					const float Yaw = DressRng.RandRange(0, 1) * 90.f + DressRng.FRandRange(-10.f, 10.f);
					if (Index != INDEX_NONE && PlacePiece(LoadedMeshes[Index], SubCenter, Yaw, FVector(0.8f * Sub, 0.8f * Sub, 220.f),
						1.0f, 90.f, true, true))
					{
						++Placed;
					}
				}
				if (Placed > 0)
				{
					continue;
				}
			}
			const float Yaw = DressRng.RandRange(0, 3) * 90.f + DressRng.FRandRange(-8.f, 8.f);
			bool bPlaced = false;
			for (int32 Try = 0; Try < 4 && !bPlaced; ++Try)
			{
				const int32 Index = PickMesh(EJRArenaPieceUse::Low, 0, TEXT("Geral"));
				bPlaced = Index != INDEX_NONE && PlacePiece(LoadedMeshes[Index], CellCenter + Jitter, Yaw,
					FVector(0.7f * C, 0.4f * C, 160.f), 1.15f, 100.f, true, true);
			}
			if (!bPlaced)
			{
				PlaceBlock(CellCenter, FVector(0.5f * C, 0.15f * C, 110.f), Yaw, true);
			}
		}
	}
}

void AJRArenaGenerator::BuildLandmark(const FJRArenaAssembly& Asm)
{
	if (Asm.Solid.Num() != 2 || Asm.Yard.Num() != 4)
	{
		return;
	}
	const float C = CellSize;
	const FVector OutVec(static_cast<double>(Asm.OutDir.X), static_cast<double>(Asm.OutDir.Y), 0.0);
	const FVector AlongVec(static_cast<double>(Asm.AlongDir.X), static_cast<double>(Asm.AlongDir.Y), 0.0);
	const float InYaw = YawFacingIn(Asm.OutDir);
	// [A-089] loja de costas para a muralha (porta para dentro), encostada nela; o lado comprido corre ao longo do muro.
	const FVector StoreCenter = (CellToWorld(Asm.Solid[0]) + CellToWorld(Asm.Solid[1])) * 0.5 + OutVec * (0.1f * C);
	FVector CanopyCenter = FVector::ZeroVector;
	for (const FIntPoint& Cell : Asm.Yard)
	{
		CanopyCenter += CellToWorld(Cell) * 0.25;
	}
	if (!PlacePiece(LoadedSpecial.IsValidIndex(2) ? LoadedSpecial[2].Get() : nullptr, StoreCenter, InYaw + 90.f,
		FVector(1.8f * C, 0.8f * C, 900.f), 1.1f, 300.f, true, true))
	{
		PlaceBlock(StoreCenter, FVector(1.6f * C, 0.7f * C, 400.f), InYaw + 90.f, true);
	}
	// Cobertura do posto: só visual (dá para andar embaixo), com 2 bombas e uma luz fria.
	PlacePiece(LoadedSpecial.IsValidIndex(0) ? LoadedSpecial[0].Get() : nullptr, CanopyCenter, InYaw + 90.f,
		FVector(1.95f * C, 1.95f * C, 800.f), 1.2f, 0.f, false, false);
	for (int32 Side = -1; Side <= 1; Side += 2)
	{
		const FVector PumpPos = CanopyCenter + AlongVec * (Side * 0.35f * C);
		if (!PlacePiece(LoadedSpecial.IsValidIndex(1) ? LoadedSpecial[1].Get() : nullptr, PumpPos, InYaw + 90.f,
			FVector(160.f, 160.f, 260.f), 1.3f, 150.f, true, true))
		{
			PlaceBlock(PumpPos, FVector(60.f, 90.f, 180.f), InYaw + 90.f, true);
		}
	}
	AddLight(CanopyCenter + FVector(0.f, 0.f, 480.f), FLinearColor(0.75f, 0.9f, 1.f), 55.f, 1600.f);
}

void AJRArenaGenerator::BuildAssemblies()
{
	const float C = CellSize;
	for (const FJRArenaAssembly& Asm : Layout.Assemblies)
	{
		const FVector OutVec(static_cast<double>(Asm.OutDir.X), static_cast<double>(Asm.OutDir.Y), 0.0);
		const float InYaw = YawFacingIn(Asm.OutDir);
		const float AlongYaw = InYaw + 90.f; // lado comprido paralelo ao muro
		auto IsBackRow = [this, &Asm](const FIntPoint& Cell)
		{
			return !Layout.IsInside(Cell.X + Asm.OutDir.X, Cell.Y + Asm.OutDir.Y);
		};
		switch (Asm.Kind)
		{
		case EJRArenaAssemblyKind::Posto:
			BuildLandmark(Asm);
			break;
		case EJRArenaAssemblyKind::Patio:
			// Contêineres em L: a fila de trás deitada ao longo do muro, a ponta do L perpendicular (protege o baú).
			for (const FIntPoint& Cell : Asm.Solid)
			{
				const bool bBack = IsBackRow(Cell);
				const FVector Pos = CellToWorld(Cell) + OutVec * (bBack ? 0.12f * C : 0.f);
				const float Yaw = (bBack ? AlongYaw : InYaw) + DressRng.FRandRange(-3.f, 3.f) + (DressRng.FRand() < 0.5f ? 180.f : 0.f);
				const int32 Index = PickMesh(EJRArenaPieceUse::High, 0, TEXT("Patio"));
				if (Index == INDEX_NONE || !PlacePiece(LoadedMeshes[Index], Pos, Yaw, FVector(0.95f * C, 0.55f * C, 650.f), 1.3f, 0.f, true, true))
				{
					PlaceBlock(Pos, FVector(0.8f * C, 0.4f * C, 280.f), Yaw, true);
				}
			}
			break;
		case EJRArenaAssemblyKind::FerroVelho:
			// Carcaças tortas (ângulos variados, nada alinhado), barris amontoados na ponta.
			for (const FIntPoint& Cell : Asm.Solid)
			{
				const FVector Pos = CellToWorld(Cell) + OutVec * (0.08f * C);
				const float Yaw = AlongYaw + DressRng.FRandRange(-35.f, 35.f) + (DressRng.FRand() < 0.5f ? 180.f : 0.f);
				const int32 Index = PickMesh(EJRArenaPieceUse::High, 0, TEXT("FerroVelho"));
				if (Index == INDEX_NONE || !PlacePiece(LoadedMeshes[Index], Pos, Yaw, FVector(0.85f * C, 0.6f * C, 600.f), 1.25f, 0.f, true, true))
				{
					PlaceBlock(Pos, FVector(0.7f * C, 0.4f * C, 250.f), Yaw, true);
				}
			}
			for (const FIntPoint& Cell : Asm.LowCells)
			{
				PlaceCluster(CellToWorld(Cell), 0.22f * C, DressRng.RandRange(2, 3), TEXT("FerroVelho"));
			}
			break;
		default: // Acampamento
			// Barricada de costas para o muro + gerador/barris na frente dela; luz quente baixa.
			for (const FIntPoint& Cell : Asm.LowCells)
			{
				const FVector Pos = CellToWorld(Cell) + OutVec * (0.18f * C);
				const int32 Index = PickMesh(EJRArenaPieceUse::Low, 0, TEXT("Acampamento"));
				if (Index != INDEX_NONE)
				{
					PlacePiece(LoadedMeshes[Index], Pos, AlongYaw + DressRng.FRandRange(-8.f, 8.f), FVector(0.75f * C, 0.3f * C, 170.f),
						1.15f, 0.f, true, true);
				}
				PlaceCluster(CellToWorld(Cell) - OutVec * (0.2f * C), 0.12f * C, DressRng.RandRange(1, 2), TEXT("Acampamento"));
			}
			if (Asm.Yard.Num() > 0)
			{
				AddLight(CellToWorld(Asm.Yard[0]) + FVector(0.f, 0.f, 180.f), FLinearColor(1.f, 0.6f, 0.3f), 30.f, 1200.f);
			}
			break;
		}
		UE_LOG(LogJR, Verbose, TEXT("Arena: conjunto %s com %d peças sólidas"), *FJRArenaLayout::AssemblyName(Asm.Kind), Asm.Solid.Num());
	}
}

void AJRArenaGenerator::PlaceScaled(UStaticMesh* InMesh, const FVector& BottomCenter, float Yaw, const FVector& Scale, bool bCollide)
{
	if (!InMesh)
	{
		return;
	}
	// Malhas do prep_tripo: origem no centro de baixo. Corrige se a malha não estiver centrada.
	const FBox Box = InMesh->GetBoundingBox();
	const FRotator Rot(0.f, Yaw, 0.f);
	const FVector LocalCenter(Box.GetCenter().X * Scale.X, Box.GetCenter().Y * Scale.Y, 0.0);
	FVector Loc = BottomCenter - Rot.RotateVector(LocalCenter);
	Loc.Z = BottomCenter.Z - Box.Min.Z * Scale.Z;
	GetMeshComponent(InMesh, bCollide)->AddInstance(FTransform(Rot, Loc, Scale), true);
	++PlacedPieces;
}

void AJRArenaGenerator::BuildBorder()
{
	// [A-086] Muralha de verdade em volta (muro + torres + portão, todos com colisão da própria malha).
	// Antes: caixas invisíveis de 6 m e peças soltas do lado de fora (dava para sair e não parecia arena).
	const float C = CellSize;
	const FVector Origin = GetActorLocation();
	UStaticMesh* Wall = LoadedSpecial.IsValidIndex(4) ? LoadedSpecial[4].Get() : nullptr;
	UStaticMesh* Tower = LoadedSpecial.IsValidIndex(5) ? LoadedSpecial[5].Get() : nullptr;
	UStaticMesh* Gate = LoadedSpecial.IsValidIndex(6) ? LoadedSpecial[6].Get() : nullptr;
	UStaticMesh* Lamp = LoadedSpecial.IsValidIndex(3) ? LoadedSpecial[3].Get() : nullptr;

	// 1) Bordas: célula dentro com vizinho fora. Chave = (linha em meias-células, lado de fora).
	TMap<FIntPoint, TArray<int32>> EdgesAlongX; // linha horizontal (Y fixo), corre em X
	TMap<FIntPoint, TArray<int32>> EdgesAlongY; // linha vertical (X fixo), corre em Y
	for (int32 X = 0; X < Layout.Grid; ++X)
	{
		for (int32 Y = 0; Y < Layout.Grid; ++Y)
		{
			if (!Layout.IsInside(X, Y))
			{
				continue;
			}
			if (!Layout.IsInside(X, Y + 1)) { EdgesAlongX.FindOrAdd(FIntPoint(2 * Y + 1, 1)).Add(X); }
			if (!Layout.IsInside(X, Y - 1)) { EdgesAlongX.FindOrAdd(FIntPoint(2 * Y - 1, -1)).Add(X); }
			if (!Layout.IsInside(X + 1, Y)) { EdgesAlongY.FindOrAdd(FIntPoint(2 * X + 1, 1)).Add(Y); }
			if (!Layout.IsInside(X - 1, Y)) { EdgesAlongY.FindOrAdd(FIntPoint(2 * X - 1, -1)).Add(Y); }
		}
	}
	struct FWallRun
	{
		FVector A;       // começo (mundo, no chão, na linha da borda)
		FVector B;       // fim
		FVector Out;     // para fora
		float Len = 0.f;
	};
	TArray<FWallRun> Runs;
	auto ToWorld = [&](float CX, float CY)
	{
		return Origin + FVector((CX - Layout.Start.X) * C, (CY - Layout.Start.Y) * C, 0.f);
	};
	auto Collect = [&](TMap<FIntPoint, TArray<int32>>& Edges, bool bAlongX)
	{
		for (auto& Pair : Edges)
		{
			TArray<int32>& Along = Pair.Value;
			Along.Sort();
			int32 RunStart = 0;
			for (int32 i = 1; i <= Along.Num(); ++i)
			{
				if (i < Along.Num() && Along[i] == Along[i - 1] + 1)
				{
					continue;
				}
				const float From = Along[RunStart] - 0.5f;
				const float To = Along[i - 1] + 0.5f;
				const float Line = Pair.Key.X * 0.5f;
				FWallRun Run;
				Run.A = bAlongX ? ToWorld(From, Line) : ToWorld(Line, From);
				Run.B = bAlongX ? ToWorld(To, Line) : ToWorld(Line, To);
				Run.Out = bAlongX ? FVector(0.0, static_cast<double>(Pair.Key.Y), 0.0) : FVector(static_cast<double>(Pair.Key.Y), 0.0, 0.0);
				Run.Len = (To - From) * C;
				Runs.Add(Run);
				RunStart = i;
			}
		}
	};
	Collect(EdgesAlongX, true);
	Collect(EdgesAlongY, false);

	const float Thick = WallThickness;
	const float Height = WallVisualHeight;
	const FVector WallExt = Wall ? Wall->GetBoundingBox().GetSize() : FVector(750.f, 1200.f, 594.f);
	// Portão no maior trecho reto (é por onde o herói "entrou").
	int32 GateRun = INDEX_NONE;
	float GateWidth = 1200.f;
	for (int32 i = 0; i < Runs.Num(); ++i)
	{
		if (Gate && Runs[i].Len >= GateWidth + 800.f && (GateRun == INDEX_NONE || Runs[i].Len > Runs[GateRun].Len))
		{
			GateRun = i;
		}
	}

	TArray<FVector> TowerSpots;
	TArray<float> TowerYaws;
	auto AddTowerSpot = [&](const FVector& P, float SpotYaw)
	{
		for (FVector& Existing : TowerSpots)
		{
			if (FVector::Dist2D(Existing, P) < Thick * 1.5f)
			{
				Existing = (Existing + P) * 0.5f; // canto: uma torre só no meio dos dois muros
				return;
			}
		}
		TowerSpots.Add(P);
		TowerYaws.Add(SpotYaw);
	};
	// [A-088] Frestas (print 10): o muro parava exatamente no centro da torre e a malha do muro não enche a própria
	// caixa até a ponta. Agora cada trecho entra por baixo da torre (TowerOverlap de cada lado) e as emendas se
	// cobrem 6%. Portão: centrado na linha do muro, com torre colada dos dois lados.
	const float TowerOverlap = Thick * 0.7f;
	int32 SegmentIndex = 0;
	auto FillWall = [&](const FVector& InA, const FVector& InB, const FVector& Out)
	{
		if (FVector::Dist2D(InA, InB) < 50.f || !Wall)
		{
			return;
		}
		const FVector Dir = (InB - InA).GetSafeNormal2D();
		const FVector A = InA - Dir * TowerOverlap;
		const FVector B = InB + Dir * TowerOverlap;
		const float Len = static_cast<float>(FVector::Dist2D(A, B));
		const float Yaw = static_cast<float>(FMath::RadiansToDegrees(FMath::Atan2(-Out.Y, -Out.X))); // frente (+X local) para dentro
		const int32 Count = FMath::Max(1, FMath::RoundToInt(Len / static_cast<float>(WallExt.Y)));
		const float SegLen = Len / Count;
		for (int32 k = 0; k < Count; ++k)
		{
			const FVector Mid = A + Dir * (SegLen * (k + 0.5f)) + Out * (Thick * 0.5f);
			// 6% a mais de comprimento: as emendas se cobrem (sem fresta).
			PlaceScaled(Wall, Mid, Yaw, FVector(Thick / WallExt.X, SegLen * 1.06 / WallExt.Y, Height / WallExt.Z), true);
			if (k > 0 && k % 2 == 0)
			{
				AddTowerSpot(A + Dir * (SegLen * k) + Out * (Thick * 0.5f), Yaw);
			}
			if (Lamp && ++SegmentIndex % 3 == 0)
			{
				const FVector LampPos = Mid - Out * (Thick * 0.5f + 160.f);
				PlaceScaled(Lamp, LampPos, Yaw, FVector(1.f), true);
				AddLight(LampPos + FVector(0.f, 0.f, 470.f) - Out * 60.f, FLinearColor(1.f, 0.72f, 0.42f), 40.f, 2200.f);
			}
		}
	};
	for (int32 i = 0; i < Runs.Num(); ++i)
	{
		const FWallRun& Run = Runs[i];
		const float RunYaw = static_cast<float>(FMath::RadiansToDegrees(FMath::Atan2(-Run.Out.Y, -Run.Out.X)));
		AddTowerSpot(Run.A + Run.Out * (Thick * 0.5f), RunYaw);
		AddTowerSpot(Run.B + Run.Out * (Thick * 0.5f), RunYaw);
		if (i != GateRun)
		{
			FillWall(Run.A, Run.B, Run.Out);
			continue;
		}
		const FVector Dir = (Run.B - Run.A).GetSafeNormal2D();
		const FVector Mid = (Run.A + Run.B) * 0.5f;
		const FVector GateA = Mid - Dir * (GateWidth * 0.5f);
		const FVector GateB = Mid + Dir * (GateWidth * 0.5f);
		FillWall(Run.A, GateA, Run.Out);
		FillWall(GateB, Run.B, Run.Out);
		const FVector GateExt = Gate->GetBoundingBox().GetSize();
		const float GS = GateWidth / FMath::Max(1.f, static_cast<float>(GateExt.Y));
		// torres coladas dos dois lados do portão (o muro entra embaixo delas)
		AddTowerSpot(GateA + Run.Out * (Thick * 0.5f), RunYaw);
		AddTowerSpot(GateB + Run.Out * (Thick * 0.5f), RunYaw);
		// centrado na linha do muro (antes ficava todo para fora e abria fresta dos lados)
		PlaceScaled(Gate, Mid + Run.Out * (Thick * 0.5f), RunYaw, FVector(GS), true);
		// [A-090] campo de força azul no arco (material M_ForceField do setup_vila_glow.py; sem ele, nada aparece)
		UStaticMesh* PlaneMesh = LoadObject<UStaticMesh>(nullptr, TEXT("/Engine/BasicShapes/Plane.Plane"));
		UMaterialInterface* FieldMat = LoadObject<UMaterialInterface>(nullptr, TEXT("/Game/Materials/Remap/M_ForceField.M_ForceField"));
		if (PlaneMesh && FieldMat)
		{
			UInstancedStaticMeshComponent* FieldComp = GetMeshComponent(PlaneMesh, false);
			FieldComp->SetMaterial(0, FieldMat);
			FieldComp->SetCastShadow(false);
			const float FieldW = GateWidth * 0.62f;
			const float FieldH = FMath::Clamp(static_cast<float>(GateExt.Z) * GS * 0.72f, 300.f, 900.f);
			// plano da engine: 100 x 100 no XY com a face para +Z; pitch 90 deixa em pé, de frente para dentro
			const FVector FieldPos = Mid + Run.Out * (Thick * 0.5f) + FVector(0.f, 0.f, FieldH * 0.5f + 5.f);
			FieldComp->AddInstance(FTransform(FRotator(90.f, RunYaw, 0.f), FieldPos, FVector(FieldH / 100.f, FieldW / 100.f, 1.f)), true);
		}
		AddLight(Mid - Run.Out * 250.f + FVector(0.f, 0.f, 500.f), FLinearColor(0.35f, 0.9f, 1.f), 50.f, 1800.f);
	}
	if (Tower)
	{
		const FVector TowerExt = Tower->GetBoundingBox().GetSize();
		// A torre cobre a quina do muro (largura >= 1,6 x espessura) e passa da altura dele.
		const float TS = FMath::Max(Thick * 1.6f / FMath::Max(1.f, static_cast<float>(FMath::Min(TowerExt.X, TowerExt.Y))),
			Height * 1.25f / FMath::Max(1.f, static_cast<float>(TowerExt.Z)));
		for (int32 i = 0; i < TowerSpots.Num(); ++i)
		{
			// alinhada com o muro (girar a torre ao acaso deixava a quina dela fora da linha do muro)
			PlaceScaled(Tower, TowerSpots[i], TowerYaws.IsValidIndex(i) ? TowerYaws[i] : 0.f, FVector(TS), true);
		}
	}
	BuildBackdrop();
}

void AJRArenaGenerator::BuildBackdrop()
{
	// [A-086] Cenário em volta (fora da muralha, sem colisão: não dá para chegar lá): penhascos e árvores alienígenas.
	if (LoadedBackdrop.Num() == 0)
	{
		return;
	}
	FBox Bounds(ForceInit);
	for (int32 X = 0; X < Layout.Grid; ++X)
	{
		for (int32 Y = 0; Y < Layout.Grid; ++Y)
		{
			if (Layout.IsInside(X, Y))
			{
				Bounds += CellToWorld(FIntPoint(X, Y));
			}
		}
	}
	if (!Bounds.IsValid)
	{
		return;
	}
	const FVector Center = Bounds.GetCenter();
	const float Radius = static_cast<float>(Bounds.GetExtent().Size2D()) + CellSize * 1.5f;
	const int32 Count = 34;
	for (int32 i = 0; i < Count; ++i)
	{
		const float Angle = (2.f * PI * i) / Count + DressRng.FRandRange(-0.06f, 0.06f);
		for (int32 Ring = 0; Ring < 2; ++Ring)
		{
			UStaticMesh* M = LoadedBackdrop[DressRng.RandRange(0, LoadedBackdrop.Num() - 1)];
			const float R = Radius + 1800.f + Ring * 2600.f + DressRng.FRandRange(-500.f, 700.f);
			const FVector P(Center.X + FMath::Cos(Angle) * R, Center.Y + FMath::Sin(Angle) * R, GetActorLocation().Z - 30.f);
			const float S = DressRng.FRandRange(0.9f, 1.5f) * (Ring == 1 ? 1.3f : 1.f);
			PlaceScaled(M, P, DressRng.FRandRange(0.f, 360.f), FVector(S), false);
		}
	}
}

void AJRArenaGenerator::BuildDecor()
{
	const float C = CellSize;
	for (int32 X = 0; X < Layout.Grid; ++X)
	{
		for (int32 Y = 0; Y < Layout.Grid; ++Y)
		{
			if (Layout.Get(X, Y) != EJRArenaCell::Free || Layout.IsReserved(X, Y) || DressRng.FRand() >= DecorChance)
			{
				continue;
			}
			const int32 Index = PickMesh(EJRArenaPieceUse::Decor, -1);
			if (Index == INDEX_NONE)
			{
				return;
			}
			const FVector Pos = CellToWorld(FIntPoint(X, Y))
				+ FVector(DressRng.FRandRange(-0.3f, 0.3f) * C, DressRng.FRandRange(-0.3f, 0.3f) * C, 0.f);
			PlacePiece(LoadedMeshes[Index], Pos, DressRng.FRandRange(0.f, 360.f), FVector(0.25f * C, 0.25f * C, 300.f), 1.f, 0.f,
				false, true);
		}
	}
}

bool AJRArenaGenerator::CheckOverlaps(FString& OutProblem) const
{
	for (int32 i = 0; i < PieceAreas.Num(); ++i)
	{
		const FBox2D A = PieceAreas[i].ExpandBy(-2.0);
		for (int32 j = i + 1; j < PieceAreas.Num(); ++j)
		{
			if (A.Intersect(PieceAreas[j].ExpandBy(-2.0)))
			{
				OutProblem = FString::Printf(TEXT("peças %d e %d sobrepostas"), i, j);
				return false;
			}
		}
	}
	// Nenhum ponto de surgimento, nave ou objetivo dentro de uma peça.
	TArray<FIntPoint> Points = Layout.SpawnCells;
	Points.Append(Layout.ExtractionCells);
	Points.Append(Layout.ObjectiveCells);
	Points.Append(Layout.ChestCells);
	for (const FIntPoint& Cell : Points)
	{
		const FVector P = CellToWorld(Cell);
		for (const FBox2D& Area : PieceAreas)
		{
			if (Area.IsInside(FVector2D(P.X, P.Y)))
			{
				OutProblem = TEXT("ponto especial dentro de uma peça");
				return false;
			}
		}
	}
	return true;
}

void AJRArenaGenerator::SpawnChests()
{
	UClass* Cls = ChestClass ? ChestClass.Get() : AJRArenaChest::StaticClass();
	for (const FIntPoint& Cell : Layout.ChestCells)
	{
		const FVector Pos = CellToWorld(Cell);
		const FRotator Facing = (GetActorLocation() - Pos).GetSafeNormal2D().Rotation();
		FActorSpawnParameters Params;
		Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
		if (AActor* Chest = GetWorld()->SpawnActor<AActor>(Cls, Pos, Facing, Params))
		{
			SpawnedActors.Add(Chest);
		}
	}
}

void AJRArenaGenerator::ClearArena()
{
	for (UInstancedStaticMeshComponent* Comp : MeshComponents)
	{
		if (Comp)
		{
			Comp->DestroyComponent();
		}
	}
	for (UPrimitiveComponent* Comp : Blockers)
	{
		if (Comp)
		{
			Comp->DestroyComponent();
		}
	}
	for (UPointLightComponent* Comp : ArenaLights)
	{
		if (Comp)
		{
			Comp->DestroyComponent();
		}
	}
	for (AActor* Spawned : SpawnedActors)
	{
		if (Spawned)
		{
			Spawned->Destroy();
		}
	}
	MeshComponents.Reset();
	MeshComponentCollides.Reset();
	Blockers.Reset();
	ArenaLights.Reset();
	SpawnedActors.Reset();
	PieceAreas.Reset();
	SpawnPoints.Reset();
	ExtractionPoints.Reset();
	ObjectivePoints.Reset();
	PlacedPieces = 0;
}

// Copyright utrazin. All Rights Reserved.

#include "FX/JRFXSubsystem.h"
#include "FX/JRGameFeel.h"
#include "Components/DecalComponent.h"
#include "Components/PointLightComponent.h"
#include "Components/SceneComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "GameFramework/Actor.h"
#include "Kismet/GameplayStatics.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Materials/MaterialInterface.h"
#include "JogoResgate.h"

namespace JRFX
{
	// Tetos dos pools (desempenho previsível: nada é criado além disto).
	constexpr int32 MaxPlasma = 120;
	constexpr int32 MaxBlood = 140;
	constexpr int32 MaxLights = 10;
	constexpr int32 MaxDecals = 90;

	// Caminhos fixos dos assets criados pelo tools/unreal/setup_combat_feel.py.
	const TCHAR* SpherePath = TEXT("/Engine/BasicShapes/Sphere.Sphere");
	const TCHAR* PlasmaPath = TEXT("/Game/VFX/Materials/M_FX_Plasma.M_FX_Plasma");
	const TCHAR* BloodPath = TEXT("/Game/VFX/Materials/M_FX_Blood.M_FX_Blood");
	const TCHAR* BloodDecalPath = TEXT("/Game/VFX/Materials/M_FX_BloodDecal.M_FX_BloodDecal");
	const TCHAR* ScorchDecalPath = TEXT("/Game/VFX/Materials/M_FX_ScorchDecal.M_FX_ScorchDecal");
	const TCHAR* HitFlashPath = TEXT("/Game/VFX/Materials/M_FX_HitFlash.M_FX_HitFlash");

	// Tipos de partícula (FJRFXParticle::Kind).
	constexpr uint8 KBolt = 0;
	constexpr uint8 KTrail = 1;
	constexpr uint8 KFlash = 2;
	constexpr uint8 KSpark = 3;
	constexpr uint8 KBlood = 4;

	const FName ColorParam(TEXT("Color"));
	const FName IntensityParam(TEXT("Intensity"));
	const FName OpacityParam(TEXT("Opacity"));
	const FName EmissiveParam(TEXT("Emissive"));
}

UJRFXSubsystem* UJRFXSubsystem::Get(const UObject* WorldContext)
{
	const UWorld* World = WorldContext ? WorldContext->GetWorld() : nullptr;
	return World ? World->GetSubsystem<UJRFXSubsystem>() : nullptr;
}

bool UJRFXSubsystem::DoesSupportWorldType(const EWorldType::Type WorldType) const
{
	return WorldType == EWorldType::Game || WorldType == EWorldType::PIE;
}

TStatId UJRFXSubsystem::GetStatId() const
{
	RETURN_QUICK_DECLARE_CYCLE_STAT(UJRFXSubsystem, STATGROUP_Tickables);
}

void UJRFXSubsystem::Deinitialize()
{
	Plasma.Reset();
	Blood.Reset();
	Lights.Reset();
	Decals.Reset();
	Host = nullptr;
	Super::Deinitialize();
}

void UJRFXSubsystem::LoadAssets()
{
	if (bAssetsLoaded)
	{
		return;
	}
	bAssetsLoaded = true;
	Rand.GenerateNewSeed();
	Sphere = LoadObject<UStaticMesh>(nullptr, JRFX::SpherePath, nullptr, LOAD_NoWarn | LOAD_Quiet);
	PlasmaMaterial = LoadObject<UMaterialInterface>(nullptr, JRFX::PlasmaPath, nullptr, LOAD_NoWarn | LOAD_Quiet);
	BloodMaterial = LoadObject<UMaterialInterface>(nullptr, JRFX::BloodPath, nullptr, LOAD_NoWarn | LOAD_Quiet);
	BloodDecalMaterial = LoadObject<UMaterialInterface>(nullptr, JRFX::BloodDecalPath, nullptr, LOAD_NoWarn | LOAD_Quiet);
	ScorchDecalMaterial = LoadObject<UMaterialInterface>(nullptr, JRFX::ScorchDecalPath, nullptr, LOAD_NoWarn | LOAD_Quiet);
	HitFlashMaterial = LoadObject<UMaterialInterface>(nullptr, JRFX::HitFlashPath, nullptr, LOAD_NoWarn | LOAD_Quiet);
	if (!PlasmaMaterial || !BloodMaterial)
	{
		UE_LOG(LogJR, Warning, TEXT("JRFX: materiais de efeito ausentes em /Game/VFX/Materials (rode tools/unreal/setup_combat_feel.py)"));
	}
}

UMaterialInterface* UJRFXSubsystem::GetBloodMaterial()
{
	LoadAssets();
	return BloodMaterial;
}

UMaterialInterface* UJRFXSubsystem::GetBloodDecalMaterial()
{
	LoadAssets();
	return BloodDecalMaterial;
}

UMaterialInterface* UJRFXSubsystem::GetHitFlashMaterial()
{
	LoadAssets();
	return HitFlashMaterial;
}

UStaticMesh* UJRFXSubsystem::GetSphereMesh()
{
	LoadAssets();
	return Sphere;
}

bool UJRFXSubsystem::EnsureHost()
{
	LoadAssets();
	if (Host)
	{
		return Sphere != nullptr;
	}
	UWorld* World = GetWorld();
	if (!World)
	{
		return false;
	}
	FActorSpawnParameters Params;
	Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
	Params.ObjectFlags |= RF_Transient;
	Host = World->SpawnActor<AActor>(AActor::StaticClass(), FTransform::Identity, Params);
	if (!Host)
	{
		return false;
	}
	USceneComponent* HostRoot = NewObject<USceneComponent>(Host, TEXT("FXRoot"));
	Host->SetRootComponent(HostRoot);
	HostRoot->RegisterComponent();
	return Sphere != nullptr;
}

int32 UJRFXSubsystem::Acquire(bool bBloodPool)
{
	if (!EnsureHost())
	{
		return INDEX_NONE;
	}
	TArray<FJRFXParticle>& Pool = bBloodPool ? Blood : Plasma;
	UMaterialInterface* Base = bBloodPool ? BloodMaterial.Get() : PlasmaMaterial.Get();
	if (!Base)
	{
		return INDEX_NONE;
	}
	for (int32 i = 0; i < Pool.Num(); ++i)
	{
		if (!Pool[i].bActive && Pool[i].Mesh)
		{
			return i;
		}
	}
	const int32 Cap = bBloodPool ? JRFX::MaxBlood : JRFX::MaxPlasma;
	if (Pool.Num() < Cap)
	{
		UStaticMeshComponent* Comp = NewObject<UStaticMeshComponent>(Host);
		Comp->SetMobility(EComponentMobility::Movable);
		Comp->SetStaticMesh(Sphere);
		Comp->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		Comp->SetGenerateOverlapEvents(false);
		Comp->SetCastShadow(false);
		Comp->bReceivesDecals = false;
		Comp->SetCanEverAffectNavigation(false);
		Comp->SetVisibility(false);
		Comp->RegisterComponent();
		FJRFXParticle& New = Pool.AddDefaulted_GetRef();
		New.Mesh = Comp;
		New.Material = UMaterialInstanceDynamic::Create(Base, Comp);
		Comp->SetMaterial(0, New.Material);
		return Pool.Num() - 1;
	}
	// Cheio: reaproveita o mais adiantado na vida (some primeiro de qualquer jeito).
	int32 Best = INDEX_NONE;
	float BestT = -1.f;
	for (int32 i = 0; i < Pool.Num(); ++i)
	{
		const float T = Pool[i].Age / FMath::Max(0.01f, Pool[i].Life);
		if (T > BestT)
		{
			BestT = T;
			Best = i;
		}
	}
	if (Best != INDEX_NONE)
	{
		Release(Pool[Best]);
	}
	return Best;
}

int32 UJRFXSubsystem::AcquireLight()
{
	if (!EnsureHost())
	{
		return INDEX_NONE;
	}
	for (int32 i = 0; i < Lights.Num(); ++i)
	{
		if (!Lights[i].bActive && Lights[i].Light)
		{
			return i;
		}
	}
	if (Lights.Num() >= JRFX::MaxLights)
	{
		return INDEX_NONE; // sem luz extra: o efeito continua, só não ilumina
	}
	UPointLightComponent* L = NewObject<UPointLightComponent>(Host);
	L->SetMobility(EComponentMobility::Movable);
	L->SetIntensityUnits(ELightUnits::Unitless);
	L->SetCastShadows(false);
	L->SetIntensity(0.f);
	L->SetVisibility(false);
	L->RegisterComponent();
	FJRFXLight& New = Lights.AddDefaulted_GetRef();
	New.Light = L;
	return Lights.Num() - 1;
}

void UJRFXSubsystem::Release(FJRFXParticle& P)
{
	if (P.bActive)
	{
		--ActiveCount;
	}
	P.bActive = false;
	if (P.Mesh)
	{
		P.Mesh->SetVisibility(false);
	}
	if (Lights.IsValidIndex(P.Light) && Lights[P.Light].Follow != INDEX_NONE)
	{
		ReleaseLight(Lights[P.Light]);
	}
	P.Light = INDEX_NONE;
}

void UJRFXSubsystem::ReleaseLight(FJRFXLight& L)
{
	L.bActive = false;
	L.Follow = INDEX_NONE;
	if (L.Light)
	{
		L.Light->SetIntensity(0.f);
		L.Light->SetVisibility(false);
	}
}

void UJRFXSubsystem::SpawnPlasmaBolt(const FVector& From, const FVector& To, const FLinearColor& Color, float Intensity,
	float Speed, float Length, float Width, float TrailLength, bool bWithLight)
{
	const FVector Delta = To - From;
	const float Dist = static_cast<float>(Delta.Size());
	if (Dist < 5.f)
	{
		return;
	}
	const FVector Dir = Delta / Dist;
	const float Life = Dist / FMath::Max(1000.f, Speed);
	for (int32 Part = 0; Part < 2; ++Part)
	{
		if (Part == 1 && TrailLength <= 1.f)
		{
			break;
		}
		const int32 Index = Acquire(false);
		if (Index == INDEX_NONE)
		{
			return;
		}
		FJRFXParticle& P = Plasma[Index];
		P.Kind = Part == 0 ? JRFX::KBolt : JRFX::KTrail;
		P.bActive = true;
		++ActiveCount;
		P.Origin = From;
		P.Position = From;
		P.Direction = Dir;
		P.Speed = Speed;
		P.Age = 0.f;
		P.Life = Life;
		P.Length = Part == 0 ? Length : TrailLength;
		P.Width = Part == 0 ? Width : Width * 0.45f;
		P.Color = Part == 0 ? FMath::Lerp(Color, FLinearColor::White, 0.35f) : Color;
		P.Opacity = Part == 0 ? 1.f : 0.45f;
		P.Material->SetVectorParameterValue(JRFX::ColorParam, P.Color);
		P.Material->SetScalarParameterValue(JRFX::IntensityParam, Intensity);
		P.Material->SetScalarParameterValue(JRFX::OpacityParam, P.Opacity);
		P.Light = INDEX_NONE;
		if (Part == 0 && bWithLight)
		{
			const int32 LightIndex = AcquireLight();
			if (LightIndex != INDEX_NONE)
			{
				FJRFXLight& L = Lights[LightIndex];
				L.bActive = true;
				L.Age = 0.f;
				L.Life = Life;
				L.Peak = 6000.f;
				L.Follow = Index;
				L.Light->SetLightColor(Color);
				L.Light->SetAttenuationRadius(260.f);
				L.Light->SetWorldLocation(From);
				L.Light->SetIntensity(L.Peak);
				L.Light->SetVisibility(true);
				P.Light = LightIndex;
			}
		}
		UpdateParticle(P, 0.f, false, Index);
		P.Mesh->SetVisibility(true);
	}
}

void UJRFXSubsystem::SpawnFlash(const FVector& Location, const FLinearColor& Color, float Intensity, float StartSize,
	float EndSize, float Life, float LightIntensity, float LightRadius)
{
	if (JRFeel::ReduceFlash())
	{
		// [A-073] acessibilidade: clarões menores, mais fracos e mais curtos
		Intensity *= 0.45f;
		EndSize *= 0.7f;
		Life *= 0.7f;
		LightIntensity *= 0.3f;
	}
	const int32 Index = Acquire(false);
	if (Index != INDEX_NONE)
	{
		FJRFXParticle& P = Plasma[Index];
		P.Kind = JRFX::KFlash;
		P.bActive = true;
		++ActiveCount;
		P.Position = Location;
		P.Age = 0.f;
		P.Life = FMath::Max(0.02f, Life);
		P.StartSize = StartSize;
		P.EndSize = EndSize;
		P.Color = Color;
		P.Opacity = 1.f;
		P.Light = INDEX_NONE;
		P.Material->SetVectorParameterValue(JRFX::ColorParam, Color);
		P.Material->SetScalarParameterValue(JRFX::IntensityParam, Intensity);
		P.Material->SetScalarParameterValue(JRFX::OpacityParam, 1.f);
		UpdateParticle(P, 0.f, false, Index);
		P.Mesh->SetVisibility(true);
	}
	if (LightIntensity > 0.f)
	{
		const int32 LightIndex = AcquireLight();
		if (LightIndex != INDEX_NONE)
		{
			FJRFXLight& L = Lights[LightIndex];
			L.bActive = true;
			L.Age = 0.f;
			L.Life = FMath::Max(0.03f, Life * 1.3f);
			L.Peak = LightIntensity;
			L.Follow = INDEX_NONE;
			L.Light->SetLightColor(Color);
			L.Light->SetAttenuationRadius(LightRadius);
			L.Light->SetWorldLocation(Location);
			L.Light->SetIntensity(LightIntensity);
			L.Light->SetVisibility(true);
		}
	}
}

void UJRFXSubsystem::SpawnPlasmaImpact(const FVector& Location, const FVector& Normal, const FLinearColor& Color,
	float Intensity, float Scale, bool bScorchDecal)
{
	const FVector N = Normal.IsNearlyZero() ? FVector::UpVector : Normal.GetSafeNormal();
	const FVector At = Location + N * 2.f;
	SpawnFlash(At, Color, Intensity, 8.f * Scale, 55.f * Scale, 0.14f, 9000.f * Scale, 320.f * Scale);
	SpawnFlash(At, FLinearColor::White, Intensity * 0.6f, 4.f * Scale, 20.f * Scale, 0.07f, 0.f, 0.f);
	// Faíscas saindo da superfície.
	const int32 Sparks = FMath::Clamp(FMath::RoundToInt(6.f * Scale), 2, 10);
	for (int32 i = 0; i < Sparks; ++i)
	{
		const int32 Index = Acquire(false);
		if (Index == INDEX_NONE)
		{
			break;
		}
		FJRFXParticle& P = Plasma[Index];
		P.Kind = JRFX::KSpark;
		P.bActive = true;
		++ActiveCount;
		P.Position = At;
		P.Velocity = (N + Rand.VRand() * 0.8f).GetSafeNormal() * Rand.FRandRange(250.f, 700.f) * FMath::Max(0.5f, Scale);
		P.Gravity = 900.f;
		P.Age = 0.f;
		P.Life = Rand.FRandRange(0.18f, 0.35f);
		P.StartSize = 2.2f;
		P.EndSize = 0.5f;
		P.Color = Color;
		P.Opacity = 1.f;
		P.FloorZ = -1.0e9;
		P.DecalSize = 0.f;
		P.Light = INDEX_NONE;
		P.Material->SetVectorParameterValue(JRFX::ColorParam, FMath::Lerp(Color, FLinearColor::White, 0.3f));
		P.Material->SetScalarParameterValue(JRFX::IntensityParam, Intensity);
		P.Material->SetScalarParameterValue(JRFX::OpacityParam, 1.f);
		UpdateParticle(P, 0.f, false, Index);
		P.Mesh->SetVisibility(true);
	}
	if (bScorchDecal)
	{
		SpawnDecal(EJRDecalKind::Scorch, Location, N, 14.f * Scale + 6.f, Color, 3.f, 12.f);
	}
}

void UJRFXSubsystem::SpawnDustPuff(const FVector& Location, const FLinearColor& Color, int32 Count, float Speed)
{
	// [A-073] mesmo esquema das gotas (pool Blood): balística, encolhe com a idade, some no chão
	for (int32 i = 0; i < Count; ++i)
	{
		const int32 Index = Acquire(true);
		if (Index == INDEX_NONE)
		{
			return;
		}
		FJRFXParticle& P = Blood[Index];
		P.Kind = JRFX::KBlood;
		P.bActive = true;
		++ActiveCount;
		P.Position = Location + FVector(0.f, 0.f, 3.f);
		const FVector2D Ring = FVector2D(Rand.FRandRange(-1.f, 1.f), Rand.FRandRange(-1.f, 1.f)).GetSafeNormal();
		P.Velocity = FVector(Ring.X, Ring.Y, Rand.FRandRange(0.25f, 0.6f)).GetSafeNormal() * Speed * Rand.FRandRange(0.5f, 1.1f);
		P.Gravity = 650.f;
		P.Age = 0.f;
		P.Life = Rand.FRandRange(0.35f, 0.6f);
		P.StartSize = Rand.FRandRange(2.5f, 4.5f);
		P.EndSize = 0.6f;
		P.Color = Color;
		P.Emissive = 0.f;
		P.Opacity = 1.f;
		P.FloorZ = Location.Z - 2.0; // tocou o chão: some (sem mancha)
		P.DecalSize = 0.f;
		P.Light = INDEX_NONE;
		P.Material->SetVectorParameterValue(JRFX::ColorParam, Color);
		P.Material->SetScalarParameterValue(JRFX::EmissiveParam, 0.f);
		UpdateParticle(P, 0.f, true, Index);
		P.Mesh->SetVisibility(true);
	}
}

void UJRFXSubsystem::SpawnBloodSpray(const FVector& Location, const FVector& ShotDir, const FVector& Normal,
	const FLinearColor& Color, float Emissive, int32 Count, float Speed)
{
	const FVector Dir = ShotDir.GetSafeNormal();
	const FVector N = Normal.IsNearlyZero() ? -Dir : Normal.GetSafeNormal();
	for (int32 i = 0; i < Count; ++i)
	{
		const int32 Index = Acquire(true);
		if (Index == INDEX_NONE)
		{
			return;
		}
		FJRFXParticle& P = Blood[Index];
		P.Kind = JRFX::KBlood;
		P.bActive = true;
		++ActiveCount;
		P.Position = Location;
		// Metade sai pelas costas (na direção do tiro), metade espirra para fora do ferimento.
		const FVector Base = (i % 2 == 0) ? Dir : N;
		P.Velocity = (Base + Rand.VRand() * 0.55f + FVector(0.f, 0.f, 0.25f)).GetSafeNormal() * Speed * Rand.FRandRange(0.4f, 1.1f);
		P.Gravity = 980.f;
		P.Age = 0.f;
		P.Life = Rand.FRandRange(0.3f, 0.6f);
		P.StartSize = Rand.FRandRange(1.6f, 3.4f);
		P.EndSize = 0.4f;
		P.Color = Color;
		P.Emissive = Emissive;
		P.Opacity = 1.f;
		P.FloorZ = -1.0e9;
		P.DecalSize = 0.f;
		P.Light = INDEX_NONE;
		P.Material->SetVectorParameterValue(JRFX::ColorParam, Color);
		P.Material->SetScalarParameterValue(JRFX::EmissiveParam, Emissive);
		UpdateParticle(P, 0.f, true, Index);
		P.Mesh->SetVisibility(true);
	}
}

void UJRFXSubsystem::SpawnBloodDrop(const FVector& Location, const FLinearColor& Color, float Emissive, float DecalSize,
	const AActor* IgnoreActor)
{
	UWorld* World = GetWorld();
	const int32 Index = World ? Acquire(true) : INDEX_NONE;
	if (Index == INDEX_NONE)
	{
		return;
	}
	FJRFXParticle& P = Blood[Index];
	P.Kind = JRFX::KBlood;
	P.bActive = true;
	++ActiveCount;
	P.Position = Location;
	P.Velocity = FVector(Rand.FRandRange(-15.f, 15.f), Rand.FRandRange(-15.f, 15.f), -40.f);
	P.Gravity = 980.f;
	P.Age = 0.f;
	P.Life = 1.2f;
	P.StartSize = Rand.FRandRange(1.2f, 1.9f);
	P.EndSize = P.StartSize;
	P.Color = Color;
	P.Emissive = Emissive;
	P.Opacity = 1.f;
	P.DecalSize = DecalSize;
	P.FloorZ = Location.Z - 600.0;
	P.Light = INDEX_NONE;
	// O chão é procurado uma vez só, na hora da gota (sem traço por quadro).
	FCollisionObjectQueryParams Objects;
	Objects.AddObjectTypesToQuery(ECC_WorldStatic);
	Objects.AddObjectTypesToQuery(ECC_WorldDynamic);
	FCollisionQueryParams Query(SCENE_QUERY_STAT(JRBloodDrop), false, IgnoreActor);
	FHitResult Floor;
	if (World->LineTraceSingleByObjectType(Floor, Location, Location - FVector(0.f, 0.f, 600.f), Objects, Query))
	{
		P.FloorZ = Floor.ImpactPoint.Z;
	}
	else
	{
		P.DecalSize = 0.f;
	}
	P.Material->SetVectorParameterValue(JRFX::ColorParam, Color);
	P.Material->SetScalarParameterValue(JRFX::EmissiveParam, Emissive);
	UpdateParticle(P, 0.f, true, Index);
	P.Mesh->SetVisibility(true);
}

UDecalComponent* UJRFXSubsystem::SpawnDecal(EJRDecalKind Kind, const FVector& Location, const FVector& Normal, float Size,
	const FLinearColor& Color, float Emissive, float Life)
{
	LoadAssets();
	UMaterialInterface* Material = Kind == EJRDecalKind::Blood ? BloodDecalMaterial.Get() : ScorchDecalMaterial.Get();
	UWorld* World = GetWorld();
	if (!Material || !World)
	{
		return nullptr;
	}
	// Limpa as já apagadas e respeita o teto (as mais velhas somem primeiro).
	Decals.RemoveAll([](const TObjectPtr<UDecalComponent>& D) { return !IsValid(D); });
	while (Decals.Num() >= JRFX::MaxDecals)
	{
		if (UDecalComponent* Oldest = Decals[0])
		{
			Oldest->DestroyComponent();
		}
		Decals.RemoveAt(0);
	}
	const FVector N = Normal.IsNearlyZero() ? FVector::UpVector : Normal.GetSafeNormal();
	FRotator Rot = (-N).Rotation();
	Rot.Roll = Rand.FRandRange(0.f, 360.f);
	// X = profundidade da projeção (meia), Y/Z = meio tamanho.
	const FVector Extent(FMath::Max(8.f, Size * 0.5f), Size * 0.5f, Size * 0.5f);
	UDecalComponent* Decal = UGameplayStatics::SpawnDecalAtLocation(World, Material, Extent, Location, Rot, 0.f);
	if (!Decal)
	{
		return nullptr;
	}
	if (UMaterialInstanceDynamic* MID = Decal->CreateDynamicMaterialInstance())
	{
		MID->SetVectorParameterValue(JRFX::ColorParam, Color);
		MID->SetScalarParameterValue(JRFX::EmissiveParam, Emissive);
	}
	Decal->SetFadeScreenSize(0.002f);
	// false: some só o componente (true destruiria o ator dono, que aqui é o WorldSettings).
	Decal->SetFadeOut(FMath::Max(0.1f, Life * 0.75f), FMath::Max(0.1f, Life * 0.25f), false);
	Decals.Add(Decal);
	return Decal;
}

void UJRFXSubsystem::UpdateParticle(FJRFXParticle& P, float DeltaTime, bool bBloodPool, int32 Index)
{
	P.Age += DeltaTime;
	const float T = FMath::Clamp(P.Age / FMath::Max(0.001f, P.Life), 0.f, 1.f);
	FVector Center = P.Position;
	FRotator Rot = FRotator::ZeroRotator;
	FVector Scale(0.01f);
	switch (P.Kind)
	{
	case JRFX::KBolt:
	case JRFX::KTrail:
	{
		const float Traveled = P.Speed * P.Age;
		P.Position = P.Origin + P.Direction * Traveled;
		// O rastro nunca aparece atrás do cano.
		const float Len = FMath::Max(1.f, FMath::Min(P.Length, Traveled + P.Length * 0.25f));
		Center = P.Position - P.Direction * (Len * 0.5f);
		Rot = P.Direction.Rotation();
		Scale = FVector(Len, P.Width, P.Width) / 100.f;
		if (P.Kind == JRFX::KTrail)
		{
			P.Material->SetScalarParameterValue(JRFX::OpacityParam, P.Opacity * (1.f - 0.4f * T));
		}
		break;
	}
	case JRFX::KFlash:
	{
		const float Size = FMath::Lerp(P.StartSize, P.EndSize, FMath::Sqrt(T));
		Scale = FVector(Size / 100.f);
		P.Material->SetScalarParameterValue(JRFX::OpacityParam, FMath::Square(1.f - T));
		break;
	}
	default: // faísca ou gota: balística, esticada na direção da velocidade
	{
		P.Velocity.Z -= P.Gravity * DeltaTime;
		P.Position += P.Velocity * DeltaTime;
		const float Size = FMath::Lerp(P.StartSize, P.EndSize, T);
		const float Speed = static_cast<float>(P.Velocity.Size());
		const float Stretch = 1.f + FMath::Min(3.f, Speed * 0.004f);
		Center = P.Position;
		Rot = Speed > 1.f ? P.Velocity.Rotation() : FRotator::ZeroRotator;
		Scale = FVector(Size * Stretch, Size, Size) / 100.f;
		if (!bBloodPool)
		{
			P.Material->SetScalarParameterValue(JRFX::OpacityParam, 1.f - T);
		}
		break;
	}
	}
	if (P.Mesh)
	{
		P.Mesh->SetWorldTransform(FTransform(Rot, Center, Scale));
	}
	if (Lights.IsValidIndex(P.Light) && Lights[P.Light].Follow == Index && Lights[P.Light].Light)
	{
		Lights[P.Light].Light->SetWorldLocation(P.Position);
	}
}

void UJRFXSubsystem::Tick(float DeltaTime)
{
	Super::Tick(DeltaTime);
	if (ActiveCount <= 0 && Lights.Num() == 0)
	{
		return; // nada voando
	}
	for (int32 i = 0; i < Plasma.Num(); ++i)
	{
		FJRFXParticle& P = Plasma[i];
		if (!P.bActive)
		{
			continue;
		}
		UpdateParticle(P, DeltaTime, false, i);
		if (P.Age >= P.Life)
		{
			Release(P);
		}
	}
	for (int32 i = 0; i < Blood.Num(); ++i)
	{
		FJRFXParticle& P = Blood[i];
		if (!P.bActive)
		{
			continue;
		}
		UpdateParticle(P, DeltaTime, true, i);
		if (P.Position.Z <= P.FloorZ)
		{
			if (P.DecalSize > 0.f)
			{
				SpawnDecal(EJRDecalKind::Blood, FVector(P.Position.X, P.Position.Y, P.FloorZ), FVector::UpVector,
					P.DecalSize * Rand.FRandRange(0.7f, 1.3f), P.Color, P.Emissive, 25.f);
			}
			Release(P);
		}
		else if (P.Age >= P.Life)
		{
			Release(P);
		}
	}
	for (FJRFXLight& L : Lights)
	{
		if (!L.bActive || !L.Light)
		{
			continue;
		}
		L.Age += DeltaTime;
		const float T = FMath::Clamp(L.Age / FMath::Max(0.001f, L.Life), 0.f, 1.f);
		L.Light->SetIntensity(L.Follow != INDEX_NONE ? L.Peak : L.Peak * FMath::Square(1.f - T));
		// Luz que segue um projétil só apaga junto com ele (Release da partícula).
		if (L.Follow == INDEX_NONE && L.Age >= L.Life)
		{
			ReleaseLight(L);
		}
	}
}

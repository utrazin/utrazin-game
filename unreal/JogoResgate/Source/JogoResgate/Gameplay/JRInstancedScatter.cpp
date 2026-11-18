// Copyright utrazin. All Rights Reserved.

#include "Gameplay/JRInstancedScatter.h"
#include "JogoResgate.h"
#include "Components/HierarchicalInstancedStaticMeshComponent.h"
#include "Components/SceneComponent.h"
#include "Engine/CollisionProfile.h"
#include "Engine/StaticMesh.h"
#include "GenericPlatform/GenericPlatformFile.h"
#include "HAL/PlatformFileManager.h"
#include "Templates/UniquePtr.h"

AJRInstancedScatter::AJRInstancedScatter()
{
	PrimaryActorTick.bCanEverTick = false;

	SceneRoot = CreateDefaultSubobject<USceneComponent>(TEXT("SceneRoot"));
	SceneRoot->SetMobility(EComponentMobility::Static);
	RootComponent = SceneRoot;
}

UHierarchicalInstancedStaticMeshComponent* AJRInstancedScatter::FindOrCreateComponent(UStaticMesh* Mesh, const float CullStart, const float CullEnd,
	const bool bCollision, const bool bShadows)
{
	const int32 StartCm = FMath::RoundToInt(CullStart);
	const int32 EndCm = FMath::RoundToInt(CullEnd);
	for (UHierarchicalInstancedStaticMeshComponent* Existing : ScatterComponents)
	{
		if (Existing && Existing->GetStaticMesh() == Mesh && Existing->InstanceStartCullDistance == StartCm
			&& Existing->InstanceEndCullDistance == EndCm && static_cast<bool>(Existing->CastShadow) == bShadows
			&& (Existing->GetCollisionEnabled() != ECollisionEnabled::NoCollision) == bCollision)
		{
			return Existing;
		}
	}

	const FName CompName = MakeUniqueObjectName(this, UHierarchicalInstancedStaticMeshComponent::StaticClass(),
		FName(*FString::Printf(TEXT("HISM_%s"), *Mesh->GetName())));
	UHierarchicalInstancedStaticMeshComponent* Comp = NewObject<UHierarchicalInstancedStaticMeshComponent>(this, CompName, RF_Transactional);
	Comp->SetMobility(EComponentMobility::Static);
	Comp->SetupAttachment(SceneRoot);
	Comp->SetStaticMesh(Mesh);
	Comp->SetCullDistances(StartCm, EndCm);
	Comp->SetCastShadow(bShadows);
	// Plantas pequenas não recebem marcas de tiro (o decal fica no terreno embaixo).
	Comp->SetReceivesDecals(bCollision);
	Comp->bAffectDistanceFieldLighting = false;
	if (bCollision)
	{
		Comp->SetCollisionProfileName(UCollisionProfile::BlockAll_ProfileName);
		Comp->SetCanEverAffectNavigation(true);
	}
	else
	{
		Comp->SetCollisionProfileName(UCollisionProfile::NoCollision_ProfileName);
		Comp->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		Comp->SetGenerateOverlapEvents(false);
		Comp->SetCanEverAffectNavigation(false);
	}
	// Criado pelo script no editor: precisa ser "instância" para ser salvo com o mapa.
	Comp->CreationMethod = EComponentCreationMethod::Instance;
	AddInstanceComponent(Comp);
	Comp->RegisterComponent();
	ScatterComponents.Add(Comp);
	return Comp;
}

int32 AJRInstancedScatter::AddBatch(UStaticMesh* Mesh, const TArray<FTransform>& Transforms, const float CullStart, const float CullEnd,
	const bool bCollision, const bool bShadows)
{
	if (!Mesh || Transforms.Num() == 0)
	{
		return 0;
	}
	Modify();
	UHierarchicalInstancedStaticMeshComponent* Comp = FindOrCreateComponent(Mesh, CullStart, CullEnd, bCollision, bShadows);
	if (!Comp)
	{
		return 0;
	}
	Comp->Modify();
	Comp->AddInstances(Transforms, /*bShouldReturnIndices=*/false, /*bWorldSpace=*/true);
	MarkPackageDirty();
	return Transforms.Num();
}

bool AJRInstancedScatter::DecodeRecords(const TArray<uint8>& Bytes, const float ScaleMultiplier, TArray<FTransform>& OutTransforms)
{
	constexpr int32 RecordBytes = RecordFloats * static_cast<int32>(sizeof(float));
	OutTransforms.Reset();
	if (Bytes.Num() % RecordBytes != 0)
	{
		return false;
	}
	const int32 Count = Bytes.Num() / RecordBytes;
	OutTransforms.Reserve(Count);
	float Values[RecordFloats];
	for (int32 Index = 0; Index < Count; ++Index)
	{
		FMemory::Memcpy(Values, Bytes.GetData() + static_cast<int64>(Index) * RecordBytes, RecordBytes);
		FQuat Rot(static_cast<double>(Values[3]), static_cast<double>(Values[4]), static_cast<double>(Values[5]), static_cast<double>(Values[6]));
		Rot.Normalize();
		const double ScaleXY = static_cast<double>(Values[7]) * ScaleMultiplier;
		const double ScaleZ = static_cast<double>(Values[8]) * ScaleMultiplier;
		OutTransforms.Emplace(Rot, FVector(Values[0], Values[1], Values[2]), FVector(ScaleXY, ScaleXY, ScaleZ));
	}
	return true;
}

int32 AJRInstancedScatter::AddBatchFromFile(UStaticMesh* Mesh, const FString& FilePath, const int32 FirstRecord, const int32 NumRecords,
	const float ScaleMultiplier, const float CullStart, const float CullEnd, const bool bCollision, const bool bShadows)
{
	if (!Mesh || NumRecords <= 0 || FirstRecord < 0)
	{
		return 0;
	}
	IPlatformFile& PlatformFile = FPlatformFileManager::Get().GetPlatformFile();
	TUniquePtr<IFileHandle> Handle(PlatformFile.OpenRead(*FilePath));
	if (!Handle)
	{
		UE_LOG(LogJR, Error, TEXT("JRInstancedScatter: não abriu %s"), *FilePath);
		return 0;
	}

	// Cabeçalho: "JRSC", versão 1, floats por registro, total de registros.
	uint8 Header[HeaderBytes];
	if (!Handle->Read(Header, HeaderBytes) || FMemory::Memcmp(Header, "JRSC", 4) != 0)
	{
		UE_LOG(LogJR, Error, TEXT("JRInstancedScatter: cabeçalho inválido em %s"), *FilePath);
		return 0;
	}
	int32 HeaderInts[3];
	FMemory::Memcpy(HeaderInts, Header + 4, sizeof(HeaderInts));
	if (HeaderInts[0] != 1 || HeaderInts[1] != RecordFloats || static_cast<int64>(FirstRecord) + NumRecords > HeaderInts[2])
	{
		UE_LOG(LogJR, Error, TEXT("JRInstancedScatter: versão/registros fora do esperado em %s (v%d, %d floats, %d registros; pedido %d+%d)"),
			*FilePath, HeaderInts[0], HeaderInts[1], HeaderInts[2], FirstRecord, NumRecords);
		return 0;
	}

	constexpr int64 RecordBytes = RecordFloats * static_cast<int64>(sizeof(float));
	const int64 Offset = HeaderBytes + static_cast<int64>(FirstRecord) * RecordBytes;
	const int64 Size = static_cast<int64>(NumRecords) * RecordBytes;
	if (Size > MAX_int32 || !Handle->Seek(Offset))
	{
		UE_LOG(LogJR, Error, TEXT("JRInstancedScatter: lote grande demais ou seek falhou (%s)"), *FilePath);
		return 0;
	}
	TArray<uint8> Bytes;
	Bytes.SetNumUninitialized(static_cast<int32>(Size));
	if (!Handle->Read(Bytes.GetData(), Size))
	{
		UE_LOG(LogJR, Error, TEXT("JRInstancedScatter: leitura falhou (%s)"), *FilePath);
		return 0;
	}

	TArray<FTransform> Transforms;
	if (!DecodeRecords(Bytes, ScaleMultiplier, Transforms))
	{
		return 0;
	}
	return AddBatch(Mesh, Transforms, CullStart, CullEnd, bCollision, bShadows);
}

void AJRInstancedScatter::ClearScatter()
{
	Modify();
	for (UHierarchicalInstancedStaticMeshComponent* Comp : ScatterComponents)
	{
		if (Comp)
		{
			RemoveInstanceComponent(Comp);
			Comp->DestroyComponent();
		}
	}
	ScatterComponents.Reset();
	MarkPackageDirty();
}

int32 AJRInstancedScatter::GetInstanceTotal() const
{
	int32 Total = 0;
	for (const UHierarchicalInstancedStaticMeshComponent* Comp : ScatterComponents)
	{
		if (Comp)
		{
			Total += Comp->GetInstanceCount();
		}
	}
	return Total;
}

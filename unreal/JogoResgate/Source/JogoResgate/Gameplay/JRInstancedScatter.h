// Copyright utrazin. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "JRInstancedScatter.generated.h"

class UHierarchicalInstancedStaticMeshComponent;
class USceneComponent;
class UStaticMesh;

/**
 * Vegetação e pedras espalhadas em massa (agente Densidade, A-060): um ator por pedaço de 250 m do mapa,
 * com um componente HISM por combinação (malha, corte por distância, colisão, sombra).
 * Preenchido no editor por tools/unreal/scatter_l01.py; no jogo não roda nada (sem Tick, sem BeginPlay):
 * as instâncias ficam salvas no mapa.
 *
 * Arquivo binário (tools/blender/scatter_l01_v3.py): cabeçalho de 16 bytes ("JRSC", versão, floats por
 * registro, total) + registros float32 little-endian: x, y, z (cm), qx, qy, qz, qw, escala_xy, escala_z.
 */
UCLASS()
class JOGORESGATE_API AJRInstancedScatter : public AActor
{
	GENERATED_BODY()

public:
	AJRInstancedScatter();

	/** Floats por registro no arquivo binário. */
	static constexpr int32 RecordFloats = 9;

	/** Bytes do cabeçalho do arquivo binário. */
	static constexpr int32 HeaderBytes = 16;

	/**
	 * Adiciona instâncias (transformações em espaço de MUNDO). CullStart/CullEnd em cm (0 = sem corte).
	 * Retorna quantas instâncias foram adicionadas.
	 */
	UFUNCTION(BlueprintCallable, Category = "Scatter")
	int32 AddBatch(UStaticMesh* Mesh, const TArray<FTransform>& Transforms, float CullStart, float CullEnd, bool bCollision, bool bShadows);

	/**
	 * Lê NumRecords registros a partir de FirstRecord do arquivo binário e adiciona como AddBatch.
	 * ScaleMultiplier corrige a diferença entre o tamanho nominal usado fora da Unreal e a malha importada.
	 */
	UFUNCTION(BlueprintCallable, Category = "Scatter")
	int32 AddBatchFromFile(UStaticMesh* Mesh, const FString& FilePath, int32 FirstRecord, int32 NumRecords, float ScaleMultiplier,
		float CullStart, float CullEnd, bool bCollision, bool bShadows);

	/** Remove todos os componentes de instâncias deste ator. */
	UFUNCTION(BlueprintCallable, Category = "Scatter")
	void ClearScatter();

	/** Total de instâncias somando todos os componentes. */
	UFUNCTION(BlueprintPure, Category = "Scatter")
	int32 GetInstanceTotal() const;

	/** Lógica pura (testável): converte registros brutos (sem cabeçalho) em transformações. */
	static bool DecodeRecords(const TArray<uint8>& Bytes, float ScaleMultiplier, TArray<FTransform>& OutTransforms);

protected:
	UPROPERTY(VisibleAnywhere, Category = "Scatter")
	TObjectPtr<USceneComponent> SceneRoot;

	/** Um componente por (malha, corte, colisão, sombra). */
	UPROPERTY(VisibleAnywhere, Category = "Scatter")
	TArray<TObjectPtr<UHierarchicalInstancedStaticMeshComponent>> ScatterComponents;

private:
	UHierarchicalInstancedStaticMeshComponent* FindOrCreateComponent(UStaticMesh* Mesh, float CullStart, float CullEnd, bool bCollision, bool bShadows);
};

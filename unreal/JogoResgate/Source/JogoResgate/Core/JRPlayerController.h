// Copyright utrazin. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/PlayerController.h"
#include "JRPlayerController.generated.h"

class AJRCharacter;
class AJRVehiclePawn;
class UInputAction;
class UInputMappingContext;
struct FInputActionValue;

DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FJROnControlledPawnChanged, APawn*, NewPawn);

/**
 * Controller independente do pawn atual (veículo ou personagem). Troca o Input Mapping Context
 * por contexto e conduz a transição carro -> a pé sem duplicar personagens.
 */
UCLASS()
class JOGORESGATE_API AJRPlayerController : public APlayerController
{
	GENERATED_BODY()

public:
	/** Sai do veículo atual: estaciona, spawna/reutiliza o personagem, possui e toca a animação. */
	UFUNCTION(BlueprintCallable, Category = "Player")
	bool RequestExitVehicle(const FTransform& FallbackTransform);

	/**
	 * Entra no veículo a pé (E perto do carro): precisa do item-chave do carro (ex.: CarKey) e, se o carro
	 * estiver sem combustível, do item pendente (ex.: Fuel). Esconde o herói, liga o carro e possui.
	 */
	UFUNCTION(BlueprintCallable, Category = "Player")
	bool RequestEnterVehicle(AJRVehiclePawn* Vehicle);

	/** Itens-chave da fase (CarKey, Fuel, Explosive...). Ficam no controller: valem a pé e no carro. */
	UFUNCTION(BlueprintCallable, Category = "Player|Items")
	void GiveKeyItem(FName Item);

	UFUNCTION(BlueprintPure, Category = "Player|Items")
	bool HasKeyItem(FName Item) const { return !Item.IsNone() && KeyItems.Contains(Item); }

	/** Gasta o item (true se tinha). */
	UFUNCTION(BlueprintCallable, Category = "Player|Items")
	bool ConsumeKeyItem(FName Item);

	/** Console (teste): "JRItens" dá chave do buggy, galão e explosivos. */
	UFUNCTION(Exec)
	void JRItens();

	UPROPERTY(BlueprintAssignable, Category = "Player")
	FJROnControlledPawnChanged OnControlledPawnChanged;

	/** Console (teste): "JRHeroi CHR-001" ou "JRHeroi CHR-002". Troca o personagem e reinicia a fase. */
	UFUNCTION(Exec)
	void JRHeroi(const FString& CharacterId);

	/**
	 * Console (teste do diretor de IA): "JRDiretor" liga/desliga o texto na tela (fase, intensidade, vivos);
	 * "JRDiretor horda" / "JRDiretor horda 20" começa uma horda agora (com 20 zumbis no total);
	 * "JRDiretor calma" / "JRDiretor subida" força a fase; "JRDiretor status" escreve no log;
	 * "JRDiretor off" / "JRDiretor on" desliga/liga o diretor.
	 */
	UFUNCTION(Exec)
	void JRDiretor(const FString& Command);

	/** Mesmo que JRDiretor (nome antigo, em inglês). */
	UFUNCTION(Exec)
	void JRDirector(const FString& Command);

	/** Console (teste): "JRCarDamage 30" tira 30 de frente e de motor do carro atual (fumaça, fogo, explosão). */
	UFUNCTION(Exec)
	void JRCarDamage(float Amount);

	/** Alterna primeira/terceira pessoa (mesmo que a tecla V). Também pelo console: "JRVisao". */
	UFUNCTION(Exec, BlueprintCallable, Category = "Player|Camera")
	void JRVisao();

	/** Primeira pessoa escolhida (guardada no GameInstance: vale a pé, no carro e depois de reiniciar a fase). */
	UFUNCTION(BlueprintPure, Category = "Player|Camera")
	bool PrefersFirstPersonView() const;

protected:
	virtual void OnPossess(APawn* InPawn) override;
	virtual void SetupInputComponent() override;

	void HandleToggleMap(const FInputActionValue& Value);

	void HandleToggleView(const FInputActionValue& Value);

	/** Aplica a visão escolhida (primeira/terceira pessoa) ao pawn atual (herói ou carro). */
	void ApplyViewPreference(APawn* InPawn, bool bInstant);

	/** Alterna primeira/terceira pessoa (V / clique do analógico direito). Fica no IMC_JR_Global: vale a pé e no carro. */
	UPROPERTY(EditDefaultsOnly, Category = "Input")
	TObjectPtr<UInputAction> ToggleViewAction;

	/** Abre/fecha o mapa grande (funciona a pé e no carro). */
	UPROPERTY(EditDefaultsOnly, Category = "Input")
	TObjectPtr<UInputAction> ToggleMapAction;

	void ApplyMappingContextFor(const APawn* InPawn);

	/** Contextos ativos ao dirigir (ex.: teclado/controle + mouse). */
	UPROPERTY(EditDefaultsOnly, Category = "Input")
	TArray<TObjectPtr<UInputMappingContext>> VehicleMappingContexts;

	/** Contextos ativos a pé (movimento, mouse, combate). */
	UPROPERTY(EditDefaultsOnly, Category = "Input")
	TArray<TObjectPtr<UInputMappingContext>> OnFootMappingContexts;

	/** Contextos sempre ativos (pausa, menu). */
	UPROPERTY(EditDefaultsOnly, Category = "Input")
	TArray<TObjectPtr<UInputMappingContext>> GlobalMappingContexts;

private:
	UPROPERTY()
	TObjectPtr<AJRCharacter> OnFootCharacter;

	UPROPERTY()
	TObjectPtr<AJRVehiclePawn> ParkedVehicle;

	UPROPERTY()
	TSet<FName> KeyItems;

	bool bExitInProgress = false;

	/** Reserva se não houver UJRGameInstance. */
	bool bPreferFirstPersonLocal = false;
};

---
name: prepare-release
description: Prepara um build de release: QA completo, licenças, créditos, versão e empacotamento Win64.
---

# /prepare-release

Prepara um build de release: QA completo, licenças, créditos, versão e empacotamento Win64.

## Pré-requisitos
- Marco fechado
- QA completo

## Passos
1. `/audit-licenses` sem bloqueios
2. Confirme que todo asset referenciado está `approved` (`manifest.py list --status`)
3. Atualize versão em `Config/DefaultGame.ini` (ProjectVersion)
4. Empacote: `RunUAT.bat BuildCookRun -project=... -platform=Win64 -clientconfig=Shipping -cook -build -stage -pak -archive -archivedirectory=build/artifacts`
5. Rode MANUAL_QA passo 20 no build
6. Escreva `docs/releases/vX.Y.Z.md`
7. Tag Git `vX.Y.Z`

## Ferramentas necessárias
- RunUAT
- check_licenses.py

## Diretórios afetados
- build/
- docs/releases/

## Verificações
- Build abre e completa a fase
- créditos incluídos

## Erros comuns
- Asset placeholder no build

## Critério de sucesso / resultado esperado
Build Shipping arquivado e documentado.

Registre o que foi realmente executado. Se um pré-requisito faltar (ex.: Unreal não instalada), pare nessa etapa e reporte como bloqueado.

---
name: generate-concept
description: Gera ou orienta conceitos visuais (incluindo IA) de um asset com prompts versionados e consistência com a Art Bible.
---

# /generate-concept

Gera ou orienta conceitos visuais (incluindo IA) de um asset com prompts versionados e consistência com a Art Bible.

## Pré-requisitos
- Asset em `planned` com BRIEF.md
- Ferramenta de IA aprovada (OD-025) ou desenho manual

## Passos
1. Leia BRIEF e Art Bible (paleta, silhueta)
2. Escreva prompt em `prompts.md` seguindo `docs/pipeline/AI_CONCEPTS.md` (sem franquias, marcas, artistas)
3. Gere/receba as vistas exigidas pela categoria
4. Salve como `<ID>_concept_v<NNN>_<vista>.png` na pasta do asset
5. Registre ferramenta, versão, licença dos pesos e seed
6. `manifest.py set-status <ID> concept`

## Ferramentas necessárias
- ferramenta de concept escolhida
- tools/pipeline/manifest.py

## Diretórios afetados
- design/concepts/<cat>/<ID>/

## Verificações
- prompts.md completo
- todas as vistas exigidas

## Erros comuns
- Prompt com nome de franquia
- licença dos pesos não registrada

## Critério de sucesso / resultado esperado
Pacote de concept pronto para `/review-art-style`.

Registre o que foi realmente executado. Se um pré-requisito faltar (ex.: Unreal não instalada), pare nessa etapa e reporte como bloqueado.

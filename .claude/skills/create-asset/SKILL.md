---
name: create-asset
description: Cria o brief e a entrada no manifesto de um novo asset (personagem, inimigo, veículo, arma, prop, ambiente, animação, áudio, UI). Use ao iniciar qualquer asset novo.
---

# /create-asset

Cria o brief e a entrada no manifesto de um novo asset (personagem, inimigo, veículo, arma, prop, ambiente, animação, áudio, UI). Use ao iniciar qualquer asset novo.

## Pré-requisitos
- ID livre no manifesto (`python tools/pipeline/manifest.py list`)
- Art Bible lida

## Passos
1. Escolha o ID (`CHR-`, `SKN-`, `ENM-`, `VEH-`, `WPN-`, `PRP-`, `ENV-`, `ANM-`, `SFX-`, `UI-`, `FNT-`, `MAT-` + 3 dígitos)
2. `python tools/pipeline/manifest.py add <ID> --category <cat> --name "<Nome>" --description "<...>"` (status `planned`)
3. Crie `design/concepts/<cat>/<ID>/BRIEF.md`: finalidade, escala (cm), orçamento de polys/texturas da Art Bible, referências de mood (só com licença), restrições de originalidade
4. Preencha `poly_budget` e `texture_budget` no manifesto
5. `python tools/pipeline/manifest.py validate`

## Ferramentas necessárias
- tools/pipeline/manifest.py

## Diretórios afetados
- assets/manifest/
- design/concepts/

## Verificações
- Manifesto valida
- BRIEF completo

## Erros comuns
- ID duplicado
- categoria fora do enum do schema

## Critério de sucesso / resultado esperado
Asset em `planned` com BRIEF pronto para `/generate-concept`.

Registre o que foi realmente executado. Se um pré-requisito faltar (ex.: Unreal não instalada), pare nessa etapa e reporte como bloqueado.

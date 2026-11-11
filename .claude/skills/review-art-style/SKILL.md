---
name: review-art-style
description: Revisa concepts ou arte final contra a Art Bible e prepara o pacote para aprovação humana. Nunca aprova sozinho.
---

# /review-art-style

Revisa concepts ou arte final contra a Art Bible e prepara o pacote para aprovação humana. Nunca aprova sozinho.

## Pré-requisitos
- Concept ou render final disponível

## Passos
1. Checar silhueta (teste preto/branco), paleta, proporções, leitura a distância
2. Checar originalidade (sem semelhança com franquias)
3. Checar especificação técnica (polys, texturas, texel density)
4. Escrever relatório com notas por item
5. Pedir decisão ao usuário (aprovar/rejeitar com motivo)
6. Só após resposta humana: registrar em `design/art-bible/approved/APPROVALS.md` e `manifest.py approve`/`set-status rejected`

## Ferramentas necessárias
- Read
- tools/pipeline/manifest.py

## Diretórios afetados
- design/art-bible/approved/

## Verificações
- Decisão humana registrada com data

## Erros comuns
- Aprovar automaticamente

## Critério de sucesso / resultado esperado
Decisão humana registrada e status atualizado.

Registre o que foi realmente executado. Se um pré-requisito faltar (ex.: Unreal não instalada), pare nessa etapa e reporte como bloqueado.

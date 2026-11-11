# Licenças de assets

Regras para qualquer conteúdo que entre no repositório: modelos, texturas, animações, áudio, fontes, imagens de referência, plugins e pesos de modelos gerativos.

## Princípio

O jogo **pode ser comercializado no futuro** (hipótese A-022). Portanto toda licença é auditada como se fosse para uso comercial. Na dúvida, o asset não entra.

## Licenças aceitas

| Licença | Uso comercial | Atribuição | Observação |
|---|---|---|---|
| CC0 / Domínio público | Sim | Não exigida (registrar mesmo assim) | Preferida |
| CC BY 4.0 | Sim | **Obrigatória** nos créditos | Registrar texto exato |
| SIL OFL 1.1 (fontes) | Sim | Manter licença junto da fonte | Não vender a fonte isolada |
| MIT / BSD / Apache-2.0 (código, plugins) | Sim | Manter aviso de copyright | |
| Conteúdo "Free" do Fab sob Standard License | Sim, **somente dentro de produtos Unreal** | Conforme termos | Ler termos vigentes antes de usar |
| Original do projeto | Sim | n/a | `creation_method: original` |

## Licenças bloqueadas

| Licença | Motivo |
|---|---|
| CC BY-NC (qualquer variante NC) | Proíbe uso comercial |
| CC BY-ND | Proíbe modificação |
| CC BY-SA | Exige compartilhar derivados sob mesma licença; avaliar caso a caso, **bloqueada por padrão** |
| GPL para assets embarcados no jogo | Risco de contaminação; Blender ser GPL não afeta o que você cria nele |
| "Free for personal use" / "Editorial use" | Não comercial |
| Origem desconhecida / sem licença | Proibida |
| Rips de jogos, filmes, franquias | Proibido |

## Animações (Mixamo e similares)

Mixamo é gratuito, mas os termos são da Adobe e mudam. Antes de usar: registrar URL dos termos, data de leitura e captura da página em `assets/licenses/`. Status no manifesto: `commercial_use_status: needs_review` até aprovação humana.

## IA gerativa

Conceitos gerados por IA são **referência de concept**, não asset final automático. Registrar: ferramenta, versão do modelo, licença dos pesos, prompt, seed e data. Image-to-3D nunca vira malha final sem retopologia e revisão humana. Ver [`docs/pipeline/AI_CONCEPTS.md`](docs/pipeline/AI_CONCEPTS.md).

## Como registrar

1. Copie o texto/URL da licença para `assets/licenses/<asset-id>.md`.
2. Preencha `license`, `origin_url`, `author`, `attribution`, `commercial_use_status` no manifesto.
3. Rode `python tools/pipeline/check_licenses.py`.
4. O agente `asset-license-auditor` revisa; aprovação final é humana.

## Créditos

Atribuições obrigatórias são consolidadas automaticamente a partir do manifesto em `docs/licenses/CREDITS.md` (gerado por `check_licenses.py --credits`).

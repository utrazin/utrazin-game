# Contribuindo

## Branches

| Branch | Uso |
|---|---|
| `main` | Sempre íntegra: testes Python passando, docs válidas. Protegida. |
| `feat/<area>-<resumo>` | Novas funcionalidades (ex.: `feat/vehicle-tire-damage`) |
| `fix/<resumo>` | Correções |
| `art/<asset-id>` | Trabalho de arte de um asset do manifesto (ex.: `art/CHR-001`) |
| `docs/<resumo>` | Apenas documentação |

Uma branch por tarefa. Rebase sobre `main` antes do PR.

## Commits

Conventional Commits, em português ou inglês, pequenos e atômicos:

```
feat: componente de saúde com delegate OnDeath
fix: veículo continua acelerando após possess do personagem
docs: ADR-003 StateTree para IA
test: casos de migração do SaveGame v1->v2
refactor: extrai FJRWheelDamageState
perf: reduz tick de inimigos distantes
chore: atualiza .gitattributes
art: CHR-001 blockout aprovado
```

## Binários e LFS

- `.uasset`, `.umap` e `.blend` são **lockable**. Antes de editar: `git lfs lock <arquivo>`; ao terminar: `git lfs unlock <arquivo>`.
- Nunca dois agentes ou pessoas editando o mesmo binário.
- Limite do GitHub LFS gratuito: **1 GiB de armazenamento e 1 GiB/mês de banda** (verificar valores atuais em docs do GitHub). Ver estratégia em [`docs/pipeline/GIT_LFS.md`](docs/pipeline/GIT_LFS.md).

## Pull Requests

Use o template (`.github/PULL_REQUEST_TEMPLATE.md`). Obrigatório:

1. CI verde (`validate.yml`).
2. Evidência de teste: log, print, vídeo curto ou checklist preenchido.
3. Impacto de performance declarado (mesmo que "nenhum").
4. Alterações de licença registradas no manifesto.
5. Plano de rollback.

## Assets

Todo asset passa pelo pipeline de [`docs/pipeline/ASSET_PIPELINE.md`](docs/pipeline/ASSET_PIPELINE.md) e precisa de entrada em `assets/manifest/assets.json`. Arte final exige **aprovação humana registrada** (`reviewer`, `approved_at`).

## Definição de pronto

Ver [`docs/roadmap/DEFINITION_OF_DONE.md`](docs/roadmap/DEFINITION_OF_DONE.md).

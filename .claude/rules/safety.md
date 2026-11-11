# Regras de segurança

- Nada de `rm -rf`, `git push --force`, `git reset --hard`, `git clean -fdx`, formatação de disco ou alteração de políticas do sistema (bloqueado por `.claude/hooks/guard_bash.py`).
- Não instalar software, pacotes ou plugins sem aprovação do usuário. Dependências Python só via `tools/requirements.txt` revisado.
- Não baixar arquivos de origem desconhecida. Verificar origem, licença e segurança antes.
- Não ler, imprimir ou commitar segredos (`.env`, tokens, `.mcp.json`).
- MCPs desabilitados por padrão; ver `docs/pipeline/MCP_SECURITY.md`.
- Antes de automações em binários: árvore Git limpa e backup (`docs/pipeline/BACKUP_RECOVERY.md`).
- Não sobrescrever trabalho existente sem backup e autorização.
- Escrever apenas dentro do repositório.

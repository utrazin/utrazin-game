# Ferramentas externas opcionais

Nenhuma é obrigatória. A pipeline, os testes e o jogo funcionam sem elas. Nada foi baixado ou instalado automaticamente. Verifique o que a máquina suporta com `python tools/setup/check_optional_ai_tools.py`.

Pesquisa feita em 2026-11-16. Reconfirme versões, licenças e flags na hora de instalar.

## ACE-Step 1.5 (música por IA)

| Item | Detalhe |
|---|---|
| Repositório | https://github.com/ace-step/ace-step-1.5 |
| Licença do código | MIT |
| Licença dos pesos | MIT nos model cards do Hugging Face consultados; o README do GitHub não trata de pesos nem de uso comercial. Confirme no card do modelo exato que baixar e registre no manifesto |
| Python | 3.11 a 3.12 |
| Hardware | GPU CUDA recomendada; também CPU, MPS, ROCm e Intel XPU. Faixas de VRAM: até 6 GB (DiT 2B turbo, INT8, offload), 6 a 8 GB, 8 a 16 GB, 16 a 20 GB, 20 a 24 GB, 24 GB ou mais |
| Tamanho | DiT 2B cerca de 4,7 GB; XL cerca de 9 GB em bf16; LMs à parte |
| Instalação | `uv sync` no clone; `uv run acestep` (interface, porta 7860) ou `uv run acestep-api` (REST, porta 8001) |
| API REST | `POST /release_task`, `POST /query_result`, `GET /v1/audio?path=...`, `GET /health`; chave opcional por `ACESTEP_API_KEY` |
| Na pipeline | skill `music-production-acestep`, cliente `tools/audio/acestep_client.py`, agente `sound-designer` |
| Estado | Cliente validado só contra servidor falso local (pytest). **Não testado com o ACE-Step real** |

Instalar fora do repositório (por exemplo `D:\ai\ACE-Step-1.5`). Nunca coloque pesos dentro do repositório.

## NVIDIA Audio2Face-3D (animação facial)

| Item | Detalhe |
|---|---|
| Repositório hub | https://github.com/NVIDIA/Audio2Face-3D (README e links; o código fica em repositórios separados) |
| Licenças | SDK, plugin Unreal e plugin Maya: MIT. Modelos Audio2Face-3D: "NVIDIA Open Model". Modelos Audio2Emotion: licença própria, uso permitido só com Audio2Face. Dados de exemplo: só avaliação. NIM: contrato NVIDIA |
| Unreal | Plugin documentado para UE 5.4 a 5.6; a documentação de instalação cita UE 5.5 e 5.6 como testadas. **Não há suporte documentado para 5.8.4** |
| Decisão | Não instalar o plugin na 5.8.4. Não rebaixar a engine. Fluxo alternativo: processar fora da Unreal e importar as curvas (skill `facial-animation-lipsync`) |
| Pendente | Verificar se o SDK standalone (C++) exporta curvas por arquivo e se roda na GPU disponível. Estado: INVESTIGAR |
| Pré-requisito do personagem | Shape keys ARKit (ver `tools/blender/validate_face_blendshapes.py`). Os heróis atuais podem não ter |

## Blender MCP (ahujasid/blender-mcp, usado pelo blender-skills)

| Item | Detalhe |
|---|---|
| Licença | MIT |
| Funcionamento | Addon no Blender escuta em `localhost:9876`; servidor `uvx blender-mcp` conecta ao Claude Code |
| Risco | Executa Python arbitrário no Blender; integrações de download (Poly Haven, Sketchfab, Hyper3D) trazem licenças variadas. Detalhes e regras em `MCP_SECURITY.md` |
| Estado no repositório | **Desligado.** Só existe `.mcp.json.example`. `.mcp.json` não foi criado (a regra do projeto bloqueia escrita nele) |
| Como ligar | Siga `MCP_SECURITY.md`, copie o exemplo para `.mcp.json`, instale o addon, clique em Connect no painel do Blender, reinicie o Claude Code, teste com "crie um cubo de 1 m" numa cena vazia |
| Sem MCP | Os mesmos passos rodam por `blender -b arquivo.blend --python tools/blender/<script>.py` |
| Versão do Blender | O pacote declara Blender 3.0 ou superior; a documentação do projeto cita 5.2 LTS e o status 5.3. Teste a conexão na versão instalada |

## Alternativas livres para lip sync (a investigar)

Ferramentas de visemas por áudio (por exemplo Rhubarb Lip Sync) não foram instaladas nem tiveram a licença confirmada aqui. Ver a matriz.

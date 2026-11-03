# GitHub Copilot Instructions — Hub de Inteligência Regulatória & Financeira (DECON/MPOR)

Antes de sugerir ou aplicar alterações neste repositório, leia obrigatoriamente:
1. [`CLAUDE.md`](../CLAUDE.md) — Arquitetura geral em nuvem (GitHub Actions), secrets e regras de operação multi-agente.
2. [`clipping/MEMORIA_PROJETO.md`](../clipping/MEMORIA_PROJETO.md) — Memória técnica completa do Clipping Diário Executivo (5 verticais).
3. [`radar_participativo/MEMORIA_PROJETO.md`](../radar_participativo/MEMORIA_PROJETO.md) e [`radar_participativo/2026-10-29_Passagem_Aba_SFN_e_Agencias_para_Gemini.md`](../radar_participativo/2026-10-29_Passagem_Aba_SFN_e_Agencias_para_Gemini.md) — Memória técnica e backlog do Radar Participativo, Estruturação/EVTEAs, Leilões e SFN.

## Diretrizes Críticas
- **Execução 100% em Nuvem:** O agendamento diário roda via `.github/workflows/clipping_diario_nuvem.yml` (Segunda a Sexta às 07:30 BRT). Qualquer modificação em `clipping/*.py` ou `radar_participativo/*.py` deve ser comitada na branch `main`.
- **Resiliência sem IA:** Caso a API Gemini falhe ou fique sem créditos, `curador.py` e `curador_participativo.py` possuem modo de contingência determinístico sem IA que nunca deve ser removido.
- **Segurança de Links e Tom Factual:** Nunca gere links pela IA (use sempre `_vincular_links_originais` por ID numérico) e mantenha tom 100% factual nas fichas documentais do Radar.

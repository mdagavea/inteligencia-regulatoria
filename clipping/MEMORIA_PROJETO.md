# Memória do Projeto: Clipping Regulatório & Financeiro (Estado Atual)

> **Última Atualização:** 03/11/2026  
> **Repositório GitHub (Nuvem Oficial):** `https://github.com/mdagavea/inteligencia-regulatoria`  
> **Painel Web:** `https://mdagavea.github.io/inteligencia-regulatoria/clipping.html`  
> **Histórico de Evoluções Passadas:** consulte [`HISTORICO_PROJETO.md`](HISTORICO_PROJETO.md) apenas quando necessário.

---

## 1. Estado Atual da Arquitetura

* **Execução Diária 100% em Nuvem:** Roda de Segunda a Sexta às **07:30 BRT** via GitHub Actions ([`.github/workflows/clipping_diario_nuvem.yml`](../.github/workflows/clipping_diario_nuvem.yml)), publicando `clipping.html`, `historico/clipping_AAAA-MM-DD.html`, `radar.html` e enviando o e-mail para `EMAIL_DESTINATARIOS`.
* **Sincronização Local (`sincronizar_nuvem.py`):**
  - Baixar da nuvem: `python3.12 ..\sincronizar_nuvem.py pull`
  - Subir alterações de código para a nuvem: `python3.12 ..\sincronizar_nuvem.py push "Mensagem"`
* **Arquivos Principais (`clipping/`):**
  - `coletor.py`: Coleta nas 5 verticais (`infra`, `seguros`, `carbono`, `divida`, `tech`) em 4 motores (VIP, RSS Diretos, Gmail Atom e Google News Aberto).
  - `termos_filtro.json` e `log_descartados_filtro.txt`: Filtro pré-IA editável sem alterar código + registro auditável de itens descartados.
  - `curador.py`: Filtra ruído via `termos_filtro.json` antes da IA, envia em lote único apenas `título + resumo[:280]` (sem URLs), vincula links originais por ID numérico, mantém cache (`historico_noticias_cache.json`) e possui fallback sem IA (`curar_noticias_contingencia_sem_ia`).
  - `renderizador.py`: Gera o dashboard executivo 2x2 + faixa inferior com atalhos para as 4 abas do Radar (`#participativo`, `#estruturacao`, `#leiloes`, `#sfn`).
  - `gerar_clipping.py`: Orquestrador com trava `--skip-if-exists`.

---

## 2. Próximas Tarefas Planejadas

1. **Avaliar Transição para o Degrau 2 de Capacidade:** Caso desejado, elevar o volume das gavetas complementares de 38–45 para 50–60 matérias.
2. **Calibrar `termos_filtro.json`:** Revisar periodicamente `log_descartados_filtro.txt` para refinar termos de ruído ou fontes.

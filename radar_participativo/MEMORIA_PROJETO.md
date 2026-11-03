# Memória do Projeto: Radar DECON/MPor (Estado Atual)

> **Última Atualização:** 03/11/2026  
> **Repositório GitHub (Nuvem Oficial):** `https://github.com/mdagavea/inteligencia-regulatoria`  
> **Painel Web (4 Abas):** `https://mdagavea.github.io/inteligencia-regulatoria/radar.html`  
> **Histórico de Evoluções Passadas:** consulte [`HISTORICO_PROJETO.md`](HISTORICO_PROJETO.md) apenas quando necessário.

---

## 1. Estado Atual (4 Abas Ativas)

1. **Aba 1 (`#participativo` — Consultas & Participação Social):**
   - Coleta via API GraphQL do **Brasil Participativo** + portais próprios da **ANTT (`ParticipANTT`)** e **ANTAQ (`Gov.br`)** com deduplicação automática (`coletor_participativo.py`).
2. **Aba 2 (`#estruturacao` — Estruturação, EVTEAs & Contratações):**
   - Monitoramento 100% factual verificado nos PDFs oficiais (Prioridade A: Portos/Aeroportos/Hidrovias; Prioridade B: Rodovias/Ferrovias — Infra S.A., BNDES, DNIT e PNCP) em `coletor_estruturacao_leiloes.py`.
3. **Aba 3 (`#leiloes` — Radar de Leilões & Outorgas):**
   - Carteira de leilões portuários, hidroviários, aeroportuários e rodoviários (ANTAQ, ANAC, ANTT e B3).
4. **Aba 4 (`#sfn` — SFN, Seguros & Capitais):**
   - Coleta automática de **SUSEP (`SAFE/SCP` API JSON + PDFs diretos)** e **CVM** (`coletor_sfn.py`), filtrada antes da IA por [`termos_filtro.json`](termos_filtro.json), com registro de descartados em [`log_descartados_filtro.txt`](log_descartados_filtro.txt), gaveta de transparência na UI e cache por hash (`analises_sfn_ia` em `historico_processos.json`).

---

## 2. Regras de Operação e Economia de API

* **Tom 100% Factual:** Proibido opinião, juízo de valor, "ótica DECON" ou "recomenda-se".
* **Economia de API Gemini:**
  1. Filtro por `termos_filtro.json` / regex roda **antes** da IA;
  2. Só itens novos (por URL/hash em `historico_processos.json`) vão à IA;
  3. Chamada única em lote enviando apenas título e resumo curto;
  4. Se a IA falhar, o painel sai normalmente sem gravar falha no cache.
* **Sincronização com a Nuvem:** `python3.12 ..\sincronizar_nuvem.py push "Mensagem"`

---

## 3. Próximas Tarefas Planejadas

1. **Fontes Adicionais na Aba 4 (BCB, PREVIC e ANBIMA):** Avaliar integração via DOU (`in.gov.br`) ou endpoints alternativos para BCB (`audpub` retorna HTTP 400 direto), PREVIC e circulares da ANBIMA.
2. **Fontes Adicionais na Aba 1 (ANA, ANEEL e ANP):** Mapear portais próprios de consultas públicas de ANA, ANEEL e ANP para complementar a Aba 1.

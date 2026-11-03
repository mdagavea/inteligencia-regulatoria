# Memória do Projeto: Clipping Regulatório & Financeiro (Estado Atual)

> **Última Atualização:** 03/11/2026  
> **Repositório GitHub (Nuvem Oficial):** `https://github.com/mdagavea/inteligencia-regulatoria`  
> **Painel Web:** `https://mdagavea.github.io/inteligencia-regulatoria/clipping.html`  
> **Análise do Trial Agência iNFRA & Roadmap Futuro:** consulte [`ANALISE_TRIAL_AGENCIA_INFRA_E_ROADMAP.md`](ANALISE_TRIAL_AGENCIA_INFRA_E_ROADMAP.md)  
> **Histórico de Evoluções Passadas:** consulte [`HISTORICO_PROJETO.md`](HISTORICO_PROJETO.md) apenas quando necessário.

---

## 1. Estado Atual da Arquitetura

* **Execução Diária 100% em Nuvem:** Roda de Segunda a Sexta às **07:30 BRT** via GitHub Actions ([`.github/workflows/clipping_diario_nuvem.yml`](../.github/workflows/clipping_diario_nuvem.yml)), publicando `clipping.html`, `historico/clipping_AAAA-MM-DD.html`, `radar.html` e enviando o e-mail para `EMAIL_DESTINATARIOS`.
* **Sincronização Local (`sincronizar_nuvem.py`):**
  - Baixar da nuvem: `python3.12 ..\sincronizar_nuvem.py pull`
  - Subir alterações de código para a nuvem: `python3.12 ..\sincronizar_nuvem.py push "Mensagem"`
* **Arquivos Principais (`clipping/`):**
  - `coletor.py`: Coleta nas 5 verticais (`infra`, `seguros`, `carbono`, `divida`, `tech`) em 4 motores:
    1. Via Expressa VIP (Google News RSS);
    2. Feeds RSS Diretos (`agenciainfra.com/blog/feed/`, `Capital Reset`, `JOTA`, `a16z`);
    3. **Leitura IMAP Estruturada (`fetch_gmail_imap_newsletters` na porta 993 + parser `_parse_boletim_agencia_infra` com fallback HTTPS 443)**: desmembra automaticamente as reportagens exclusivas (`#1`, `#2`, `#3`) e os atos prioritários do DOU (`#Diario`), Pautas (`#Agenda`) e `#Fique` dos boletins de assinantes da Agência iNFRA com links oficiais desembrulhados (`in.gov.br`, `gov.br`, `mailchi.mp`), além de ler newsletters já abertas ou não lidas;
    4. Varredura Aberta no Google News.
  - `termos_filtro.json` e `log_descartados_filtro.txt`: Filtro pré-IA editável sem alterar código + registro auditável de itens descartados.
  - `curador.py`: Filtra ruído via `termos_filtro.json` antes da IA, envia em lote único apenas `título + resumo[:280]` (sem URLs), vincula links originais por ID numérico (aceitando `ALLOWED_FEED_HOSTS`, `mailchi.mp` e domínios oficiais `.gov.br`/`.leg.br`/`.jus.br`), mantém cache (`historico_noticias_cache.json`) e possui fallback sem IA (`curar_noticias_contingencia_sem_ia`).
  - `renderizador.py`: Gera o dashboard executivo 2x2 + faixa inferior com atalhos para as 4 abas do Radar (`#participativo`, `#estruturacao`, `#leiloes`, `#sfn`).
  - `gerar_clipping.py`: Orquestrador com trava `--skip-if-exists`.

---

## 2. Próximas Tarefas Planejadas (Detalhadas em [`ANALISE_TRIAL_AGENCIA_INFRA_E_ROADMAP.md`](ANALISE_TRIAL_AGENCIA_INFRA_E_ROADMAP.md))

1. **Acompanhamento da "Agenda EVTEA 2.0" (Acórdão ANTAQ nº 640/2026 — Processo `50300.014412/2026-68`):** Monitorar a contribuição institucional da ANTAQ à revisão da Portaria MInfra nº 530/2019 (até 13/11/2026), o Grupo Técnico do Catálogo de Dados de Referência com o MPor/TCU e o Plano de Trabalho em 90 dias.
2. **Coletor Próprio do DOU (`coletor_dou.py`):** Extração via índice JSON nativo de `in.gov.br/leiturajornal` (`do1` e `do3`) para atos de MPor, MT, ANTAQ, ANAC, ANTT, PPI/PND e Portarias de Debêntures Incentivadas/REIDI.
3. **Radar Ex-Ante da Semana (Pautas de Diretoria & Controle):** Monitoramento prévio das pautas de julgamento do Plenário do TCU e das reuniões deliberativas da ANTAQ (Sophia), ANTT e ANAC.
4. **Monitor Legislativo Setorial:** Integração com as APIs REST de Dados Abertos da Câmara (`dadosabertos.camara.leg.br`) e do Senado (`legis.senado.leg.br`).

# Memória do Projeto: Clipping Regulatório & Financeiro (Estado Atual)

> **Última Atualização:** 04/11/2026  
> **Repositório GitHub (Nuvem Oficial):** `https://github.com/mdagavea/inteligencia-regulatoria`  
> **Painel Web:** `https://mdagavea.github.io/inteligencia-regulatoria/clipping.html`  
> **Análise do Trial Agência iNFRA:** o arquivo `ANALISE_TRIAL_AGENCIA_INFRA_E_ROADMAP.md` foi **removido do repositório** em 04/11/2026 (retirado de `ARQUIVOS_SINCRONIZADOS`); o estudo comparativo é só local.  
> **Histórico de Evoluções Passadas:** consulte [`HISTORICO_PROJETO.md`](HISTORICO_PROJETO.md) apenas quando necessário.

---

> **Regra de fontes (04/11/2026):** boletim de assinante da Agência iNFRA não é fonte do clipping; o estudo comparativo é só local. Isso vale para a página pública e para o e-mail, inclui os remetentes `infrajornalismo@agenciainfra.com` e `agenciainfra@agenciainfra.com` e os links `mailchi.mp`. O site aberto (`agenciainfra.com/blog`, RSS/API pública) segue como fonte normal (título, fonte e link). Salvaguarda em `coletor.py`: links `mailchi.mp`, `list-manage.com` e `campaign-archive.com` são descartados na coleta.

## 1. Estado Atual da Arquitetura

* **Execução Diária 100% em Nuvem:** Roda de Segunda a Sexta às **07:30 BRT** via GitHub Actions ([`.github/workflows/clipping_diario_nuvem.yml`](../.github/workflows/clipping_diario_nuvem.yml)), publicando `clipping.html`, `historico/clipping_AAAA-MM-DD.html`, `radar.html` e enviando o e-mail para `EMAIL_DESTINATARIOS`.
  * **`GEMINI_API_KEY` apagado (04/11/2026):** o secret foi removido do GitHub e o clipping roda **sem IA** (modo determinístico `curar_noticias_contingencia_sem_ia`). Atenção: neste modo o resumo vem do texto bruto da fonte, cortado em 260 caracteres.
  * **`email_dispatch.json` não é mais publicado:** contém os e-mails dos destinatários e o repositório é público. Fica só na pasta de trabalho do job, é lido pelo passo de envio e não entra no commit (workflow, `.gitignore` e `gerar_clipping.py` ajustados).
  * **Campo opcional `destinatario_teste`** no `workflow_dispatch`: se preenchido, o boletim vai só para esse e-mail, e não para a lista oficial.
  * **Aviso de projeto piloto (04/11/2026):** faixa no topo (só a 1ª frase) e texto completo no rodapé, na página e no e-mail (`AVISO_PILOTO_FRASE` e `AVISO_PILOTO_TEXTO` em `renderizador.py`). A marca DECON/MPOR foi mantida.
* **Sincronização Local (`sincronizar_nuvem.py`):**
  - Baixar da nuvem: `python3.12 ..\sincronizar_nuvem.py pull`
  - Subir alterações de código para a nuvem: `python3.12 ..\sincronizar_nuvem.py push "Mensagem"`
* **Arquivos Principais (`clipping/`):**
  - `coletor.py`: Coleta nas 5 verticais (`infra`, `seguros`, `carbono`, `divida`, `tech`) em 4 motores:
    1. Via Expressa VIP (Google News RSS);
    2. Feeds RSS Diretos (`agenciainfra.com/blog/feed/`, `Capital Reset`, `JOTA`, `a16z`);
    3. **Leitura IMAP de newsletters (`fetch_gmail_imap_newsletters`, porta 993, fallback Atom 443)**: lê newsletters de remetentes permitidos (Capital Reset, JOTA, CNseg etc.). **O boletim de assinante da Agência iNFRA foi DESATIVADO em 04/11/2026** (ver regra de fontes acima); o parser `_parse_boletim_agencia_infra` permanece no código, comentado nos pontos de chamada, só para estudo comparativo local;
    4. Varredura Aberta no Google News.
  - `termos_filtro.json` e `log_descartados_filtro.txt`: Filtro pré-IA editável sem alterar código + registro auditável de itens descartados.
  - `curador.py`: Filtra ruído via `termos_filtro.json` antes da IA, envia em lote único apenas `título + resumo[:280]` (sem URLs), vincula links originais por ID numérico (aceitando `ALLOWED_FEED_HOSTS`, `mailchi.mp` e domínios oficiais `.gov.br`/`.leg.br`/`.jus.br`), mantém cache (`historico_noticias_cache.json`) e possui fallback sem IA (`curar_noticias_contingencia_sem_ia`).
  - `renderizador.py`: Gera o dashboard executivo 2x2 + faixa inferior com atalhos para as 4 abas do Radar (`#participativo`, `#estruturacao`, `#leiloes`, `#sfn`).
  - `gerar_clipping.py`: Orquestrador com trava `--skip-if-exists`.

---

## 2. Próximas Tarefas Planejadas

1. **Acompanhamento da "Agenda EVTEA 2.0" (Acórdão ANTAQ nº 640/2026 — Processo `50300.014412/2026-68`):** Monitorar a contribuição institucional da ANTAQ à revisão da Portaria MInfra nº 530/2019 (até 13/11/2026), o Grupo Técnico do Catálogo de Dados de Referência com o MPor/TCU e o Plano de Trabalho em 90 dias.
2. **Coletor Próprio do DOU (`coletor_dou.py`):** Extração via índice JSON nativo de `in.gov.br/leiturajornal` (`do1` e `do3`) para atos de MPor, MT, ANTAQ, ANAC, ANTT, PPI/PND e Portarias de Debêntures Incentivadas/REIDI.
3. **Radar Ex-Ante da Semana (Pautas de Diretoria & Controle):** Monitoramento prévio das pautas de julgamento do Plenário do TCU e das reuniões deliberativas da ANTAQ (Sophia), ANTT e ANAC.
4. **Monitor Legislativo Setorial:** Integração com as APIs REST de Dados Abertos da Câmara (`dadosabertos.camara.leg.br`) e do Senado (`legis.senado.leg.br`).

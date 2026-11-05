# Memória do Projeto: Clipping Regulatório & Financeiro (Estado Atual)

> **Última Atualização:** 05/11/2026  
> **Repositório GitHub (Nuvem Oficial):** `https://github.com/mdagavea/inteligencia-regulatoria`  
> **Painel Web:** `https://mdagavea.github.io/inteligencia-regulatoria/clipping.html`  
> **Análise do Trial Agência iNFRA:** o arquivo `ANALISE_TRIAL_AGENCIA_INFRA_E_ROADMAP.md` foi **removido do repositório** em 04/11/2026 (retirado de `ARQUIVOS_SINCRONIZADOS`); o estudo comparativo é só local.  
> **Histórico de Evoluções Passadas:** consulte [`HISTORICO_PROJETO.md`](HISTORICO_PROJETO.md) apenas quando necessário.

---

> **Regra de fontes (04/11/2026):** boletim de assinante da Agência iNFRA não é fonte do clipping; o estudo comparativo é só local. Isso vale para a página pública e para o e-mail, inclui os remetentes `infrajornalismo@agenciainfra.com` e `agenciainfra@agenciainfra.com` e os links `mailchi.mp`. O site aberto (`agenciainfra.com/blog`, RSS/API pública) segue como fonte normal (título, fonte e link). Salvaguarda em `coletor.py`: links `mailchi.mp`, `list-manage.com` e `campaign-archive.com` são descartados na coleta.

## 1. Estado Atual da Arquitetura

* **Execução Diária e Envio de E-mail 100% na Nuvem (Ajustado em 05/11/2026):**
  * **Cron da Nuvem às 07:17 BRT (`17 10 * * 1-5`):** adiantado para minuto quebrado no workflow ([`.github/workflows/clipping_diario_nuvem.yml`](../.github/workflows/clipping_diario_nuvem.yml)) para evitar filas de horário cheio no GitHub Actions.
  * **Agendador Local como Despertador Redundante (07:50 BRT):** `executar_automatico.bat` dispara `gh workflow run clipping_diario_nuvem.yml` via HTTPS 443 sem gerar nem subir arquivos locais, garantindo pontualidade caso o cron do GitHub atrase.
  * **Trava Anti-Duplicidade Robusta com Marcador (`historico/.email_enviado_AAAA-MM-DD`):** O workflow só pula a execução se encontrar o marcador criado após o envio com sucesso pelo SMTP do Gmail. Se o e-mail ainda não saiu, a geração e o envio ocorrem normalmente.
  * **Privacidade Absoluta e Mascaramento Nativo (05/11/2026):**
    - `email_dispatch.json` nunca entra no git (não comitado).
    - O marcador `.email_enviado_...` contém apenas texto neutro (sem e-mails).
    - **Secret `EMAIL_TESTE` e booleano `modo_teste`:** O campo de texto livre `destinatario_teste` foi substituído pelo booleano `modo_teste` associado ao secret `EMAIL_TESTE`. **Lição aprendida:** o comando `::add-mask::` não cobre a primeira aparição de valores interpolados em comandos bash pelo runner, expondo dados no cabeçalho; a única garantia de mascaramento nativo com `***` é o uso de secrets registrados no repositório.
    - O log público relata estritamente a quantidade (`"E-mail enviado com sucesso na nuvem para X destinatário(s)."`), com zero endereços em claro.
  * **Desacoplamento Total em Relação ao Radar (05/11/2026):** O clipping não depende do Radar e não sobrescreve `radar.html`. Em `gerar_clipping.py`, foi removida a chamada mutilada de renderização do Radar. No workflow da nuvem, o commit adiciona apenas `clipping.html historico/`, protegendo a integridade das 4 abas do Radar geradas localmente.
  * **`GEMINI_API_KEY` reativada (05/11/2026):** chave do Google AI Studio configurada no `.env` local e como secret no GitHub Actions. A curadoria inteligente via IA do Gemini (modelos Flash) está 100% operacional.
  * **Memória Semântica Deslizante (05/11/2026):** implementado mecanismo de janela temporal retroativa (3 a 5 dias) em `curador.py` (`_obter_memoria_recente_fatos`), injetado no prompt do Gemini e na contingência determinística. Impede requentamentos e prioriza fatos inéditos.
  * **Blindagem Temática da Contingência Sem IA (05/11/2026):** validação temática determinística com verificação de termos âncora e bloqueio de ruídos por vertical (`_validar_e_ajustar_vertical_contingencia`).
  * **Aviso de projeto piloto (04/11/2026):** faixa no topo e rodapé (`AVISO_PILOTO_FRASE` e `AVISO_PILOTO_TEXTO`). A marca DECON/MPOR foi mantida.

* **Trava de Segurança Editorial Pré-Publicação ([`validador_publicacao.py`](../radar_participativo/validador_publicacao.py)):**
  - **Lição aprendida:** A trava precisa de listas e critérios distintos por tipo de arquivo. No `clipping.html` e histórico, "decon" e "mpor" não são varridos (marca oficial mantida por decisão do Marcos).
  - Reprova exclusivamente vazamento de dados institucionais não-públicos: endereço `@mpor.gov.br` e números de processo SEI federais (`\b\d{5}\.\d{6}/\d{4}-\d{2}\b`).
  - Resiliência: se o validador do clipping encontrar erro inesperado, emite aviso em log mas nunca bloqueia a publicação nem o envio do e-mail.

* **Lições Operacionais e Auditoria:**
  - **Correção só no HTML gerado volta quando a página é regerada:** Todo ajuste deve ser feito nos scripts Python na origem.
  - **Auditoria Independente na Ponta:** Toda validação de conformidade deve ser realizada baixando diretamente o arquivo da URL pública (`https://mdagavea.github.io/inteligencia-regulatoria/`), nunca confiando apenas em arquivos intermediários locais.

* **Sincronização Local (`sincronizar_nuvem.py`):**
  - Baixar da nuvem: `python3.12 ..\sincronizar_nuvem.py pull`
  - Subir alterações de código para a nuvem: `python3.12 ..\sincronizar_nuvem.py push "Mensagem"`

* **Arquivos Principais (`clipping/`):**
  - `coletor.py`: Coleta nas 5 verticais em 4 motores (Google News VIP, RSS direto, Newsletters IMAP, Busca Google News).
  - `termos_filtro.json` e `log_descartados_filtro.txt`: Filtro pré-IA auditável.
  - `curador.py`: Curadoria Gemini Flash com memória deslizante e fallback contingencial sem IA.
  - `renderizador.py`: Gera dashboard executivo 2x2.
  - `gerar_clipping.py`: Orquestrador diário com trava anti-duplicidade e isolamento em relação ao Radar.

---

## 2. Próximas Tarefas Planejadas

1. **Acompanhamento da "Agenda EVTEA 2.0" (Acórdão ANTAQ nº 640/2026 — Processo `50300.014412/2026-68`):** Monitorar a contribuição institucional da ANTAQ à revisão da Portaria MInfra nº 530/2019 (até 13/11/2026), o Grupo Técnico do Catálogo de Dados de Referência com o MPor/TCU e o Plano de Trabalho em 90 dias.
2. **Coletor Próprio do DOU (`coletor_dou.py`):** Extração via índice JSON nativo de `in.gov.br/leiturajornal` (`do1` e `do3`) para atos de MPor, MT, ANTAQ, ANAC, ANTT, PPI/PND e Portarias de Debêntures Incentivadas/REIDI (Fase 1 em modo somente leitura).
3. **Radar Ex-Ante da Semana (Pautas de Diretoria & Controle):** Monitoramento prévio das pautas de julgamento do Plenário do TCU e das reuniões deliberativas da ANTAQ (Sophia), ANTT e ANAC.
4. **Monitor Legislativo Setorial:** Integração com as APIs REST de Dados Abertos da Câmara (`dadosabertos.camara.leg.br`) e do Senado (`legis.senado.leg.br`).

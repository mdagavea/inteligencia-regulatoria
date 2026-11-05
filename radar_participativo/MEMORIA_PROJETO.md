# Memória do Projeto: Radar DECON/MPor (Estado Atual)

> **Última Atualização:** 05/11/2026  
> **Repositório GitHub (Nuvem Oficial):** `https://github.com/mdagavea/inteligencia-regulatoria`  
> **Painel Web (4 Abas):** `https://mdagavea.github.io/inteligencia-regulatoria/radar.html`  
> **Histórico de Evoluções Passadas:** consulte [`HISTORICO_PROJETO.md`](HISTORICO_PROJETO.md) apenas quando necessário.

---

## 1. Estado Atual (4 Abas Ativas e Integradas)

1. **Aba 1 (`#participativo` — Consultas & Participação Social):**
   - Coleta via API GraphQL do **Brasil Participativo** + portais próprios da **ANTT (`ParticipANTT`)** e **ANTAQ (`Gov.br`)** com deduplicação automática (`coletor_participativo.py`).
   - **Selo "Lançado Agora" (Ajustado em 05/11/2026):** Janela de 48 horas calculada estritamente a partir da data de publicação do ato (`data_publicacao_iso`), e não da data de encerramento. Atributo `data-pub-iso` embutido nos `<article>` para recálculo dinâmico em tempo real no cliente via JavaScript.
2. **Aba 2 (`#estruturacao` — Estruturação, EVTEAs & Contratações):**
   - Monitoramento 100% factual verificado nos editais e contratos oficiais (DNIT/PNCP, Infra S.A. e 4 contratos estratégicos do BNDES: Hidrovia Tapajós/Tocantins, Porto Greenfield RN, Concessão Santos e Rodovias NE) em `coletor_estruturacao_leiloes.py`.
   - **Selo de Situação em Contratos:** Padronizado para `"Contrato assinado em [data da fonte]"`. É terminantemente proibido utilizar o rótulo genérico `"Em Execução"` sem fonte de vigência expressa.
3. **Aba 3 (`#leiloes` — Radar de Leilões & Outorgas):**
   - Carteira de 12 leilões portuários, hidroviários, aeroportuários e rodoviários (ANTAQ, ANAC, ANTT e B3).
4. **Aba 4 (`#sfn` — SFN, Seguros & Capitais):**
   - Coleta automática de **SUSEP (`SAFE/SCP` API JSON + PDFs diretos)** e **CVM** (`coletor_sfn.py`), filtrada antes da IA por [`termos_filtro.json`](termos_filtro.json), com registro de descartados em [`log_descartados_filtro.txt`](log_descartados_filtro.txt), gaveta de transparência na UI e cache por hash (`analises_sfn_ia` em `historico_processos.json`).
5. **Carimbo Padronizado no Painel:** Formatado estritamente como `"Atualizado em dd/mm hh:mm"` (ex.: `Atualizado em 05/11 17:09`).

---

## 2. Regras Inegociáveis e Lições Aprendidas (05/11/2026)

* **1. Nenhum dado digitado à mão (saída bruta antes de qualquer card):**
  - Proibida inserção manual ou inferência de números, prazos, URLs ou escopos. Todos os dados devem ser extraídos de coletores oficiais de saída bruta verificável.
* **2. Correções valem na origem (código que gera a página), nunca só no HTML gerado:**
  - **Lição desta fase:** Qualquer edição realizada diretamente nos arquivos `.html` é sobrescrita e perdida na próxima execução do gerador. Todo ajuste de layout, texto, dados ou trava deve ser implementado nos coletores e renderizadores Python.
* **3. Trava de Segurança Editorial e Sanidade Pré-Publicação ([`validador_publicacao.py`](validador_publicacao.py)):**
  - **Listas por arquivo:** O validador aplica regras específicas para o Radar (`radar.html`, `index.html`) e para o Clipping (`clipping.html`).
  - **Termos reprovados no Radar:** Substrings `decon`, `núcleo`, `nucleo`, `segurabilidade`; `mpor` fora das exceções léxicas legítimas (`import*`, `tempor*`); e `"em execução"` nos selos de situação (`deadline-pill` e atributos `data-fim-br`).
  - **Sanidade Estrutural:** O validador reprova a publicação se a Aba Estruturação contiver 0 cards (`[SANIDADE_ESTRUTURACAO_VAZIA]`) ou se qualquer uma das abas registrar queda superior a 50% de cards em relação à versão ativa na nuvem (`[SANIDADE_QUEDA_ABRUPTA]`).
* **4. Desacoplamento do Clipping e Agendamento do Radar:**
  - O clipping diário da nuvem não depende do Radar e **não sobrescreve `radar.html`**.
  - O Radar é mantido e publicado exclusivamente pelo pipeline completo local (`gerar_radar.py --no-browser`), configurado no Agendador de Tarefas do Windows (`RadarInteligenciaRegulatoria`) de **segunda a sexta-feira às 08:00 BRT** com opção `StartWhenAvailable` (recuperação imediata caso o computador esteja desligado no horário). Esse modelo elimina o risco de bloqueio de IP por WAF/geobloqueio que ocorreria em datacenters do GitHub Actions contra o portal do BNDES.
* **5. Auditoria Independente na Ponta:**
  - A conformidade do Radar deve ser sempre conferida baixando o arquivo diretamente da URL pública (`https://mdagavea.github.io/inteligencia-regulatoria/radar.html`), auditando contagem de cards, selos e ausência de termos proibidos.
* **6. TCU com Colegiado Plenário:**
  - Nenhum dado de acórdão do TCU pode ser publicado sem conferência prévia via API oficial do TCU com filtro de COLEGIADO "Plenário".
* **7. Operação sem IA no Radar:**
  - A `GEMINI_API_KEY` permanece intencionalmente não configurada em `radar_participativo/.env`. O Radar opera em modo factual nativo, sem consumo de tokens.

---

## 3. Próximas Tarefas Planejadas

1. **Fase 1 (DOU em Leitura Amostral):** Criação do `coletor_dou.py` para leitura do índice JSON (`in.gov.br/leiturajornal`, seções `do1` e `do3`) em modo somente leitura durante 5 dias úteis, avaliando entrega de decretos PND/PPI, resoluções CMN, atos de fundos (FNAC, FMM, FGE, FGI, FGO, FGHAB) e acórdãos ANTAQ (Acórdão nº 640/2026).
2. **Fontes Adicionais na Aba 4 (BCB, PREVIC e ANBIMA):** Avaliar integração via DOU (`in.gov.br`) ou endpoints alternativos para BCB, PREVIC e circulares da ANBIMA.
3. **Fontes Adicionais na Aba 1 (ANA, ANEEL e ANP):** Mapear portais próprios de consultas públicas de ANA, ANEEL e ANP para complementar a Aba 1.

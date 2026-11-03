# Memória do Projeto: Radar Brasil Participativo — Gestão & Dossiês Normativos

> **Data de Criação:** 21 de Outubro de 2026  
> **Última Atualização:** 28 de Outubro de 2026  
> **Local do Projeto:** `C:\Users\marcos.castilho\testes-gemini\radar_participativo`  
> **Projeto Irmão (Integrado):** `C:\Users\marcos.castilho\testes-gemini\clipping`

---

## 1. Links Públicos na Web (GitHub Pages — Atualização Contínua Automática)

Os painéis são publicados automaticamente no repositório `mdagavea/inteligencia-regulatoria` via GitHub CLI (`gh api`):

* 🌐 **Hub Central:** `https://mdagavea.github.io/inteligencia-regulatoria/`
* 🏛️ **Radar DECON/MPor em 3 Abas (Participação, Estruturação/EVTEAs & Leilões):** `https://mdagavea.github.io/inteligencia-regulatoria/radar.html`
  * Aba 1: `#participativo` (Consultas & Participação Social — Brasil Participativo)
  * Aba 2: `#estruturacao` (Estruturação, EVTEAs & Contratações — Infra S.A., BNDES, LabTrans e PNCP)
  * Aba 3: `#leiloes` (Radar de Leilões & Outorgas — MPor/ANTAQ, ANAC, MT/ANTT, B3 e Nacionais)
* 📰 **Clipping Diário Executivo DECON/MPOR:** `https://mdagavea.github.io/inteligencia-regulatoria/clipping.html`
* 🗂️ **Repositório Histórico do Clipping:** `https://mdagavea.github.io/inteligencia-regulatoria/historico/index.html`

---

## 2. Objetivo e Escopo de Negócio

Monitorar de forma autônoma, diária e estruturada todos os processos participativos lançados no portal **Brasil Participativo** (`https://brasilparticipativo.presidencia.gov.br/`) — incluindo **Consultas Públicas, Audiências Públicas, Tomadas de Subsídios, Consultas Setoriais, Planos Participativos, Conferências, Conselhos e Minutas em Pré-Publicação** — que tenham aderência às nossas 4 verticais de trabalho:

1. **Infraestrutura, Transportes & Outorgas (`infra`):** Rodovias, ferrovias, portos, aeroportos, hidrovias, ANTT, ANAC, ANTAQ, DNIT, SENATRAN, Ministério dos Transportes (MT), Ministério de Portos e Aeroportos (MPOR), concessões, PPPs, leilões, reequilíbrio, matrizes de risco e estruturação de projetos.
2. **Seguros, Garantias & Grandes Riscos (`seguros`):** Políticas e diretrizes de seguros em infraestrutura/portos/aeroportos/transportes (ex: Portaria de Seguros do MPOR), seguro-garantia (performance bond), regulação SUSEP e resseguro.
3. **Clima, Carbono & Infraestrutura Sustentável (`carbono`):** Certificação de infraestrutura sustentável, Taxonomia Sustentável Brasileira (TSB), SBCE, Fundo Clima, licenciamento ambiental e logística reversa.
4. **Financiamento, Fomento & Mercado de Capitais (`divida`):** Apoio oficial ao crédito, compliance financeiro (CAMEX/MDIC), garantias, debêntures incentivadas/infraestrutura, CVM e BNDES.

---

## 3. Arquitetura Técnica Validada (Descobertas de 21/10/2026)

| Componente | Decisão Técnica | Vantagem Estratégica |
| :--- | :--- | :--- |
| **Ingestão de Dados** | **API GraphQL Oficial (`Decidim v0.27.2`)** em `https://brasilparticipativo.presidencia.gov.br/api` | Evita web scraping frágil. Extrai metadados puros, HTML completo da descrição, links SEI, publicações no DOU e arquivos PDF anexos em uma única chamada. |
| **Handshake TLS/SSL** | `DEFAULT@SECLEVEL=1` + `OP_IGNORE_UNEXPECTED_EOF` | Resolve a incompatibilidade nativa de SSL entre o Python 3.12 no Windows e o servidor Nginx/Dataprev do Governo Federal. |
| **Radar de Pré-Publicação** | Varredura cruzada entre `participatoryProcesses` e `participatoryProcessTypes` | Enquanto `participatoryProcesses` lista apenas os publicados na vitrine, `participatoryProcessTypes` expõe processos recém-cadastrados pelos ministérios ainda em modo rascunho/pré-publicação (ex: permitiu detectar antecipadamente a CP do Plano Setorial de Transporte Ferroviário - PSTF da SNTF/MT). |
| **Blindagem contra Erro de Cadastro** | Leitura integral do HTML de `description` + URLs embutidas + correção de ano em `endDate` | Operadores frequentemente clonam processos antigos ou digitam `2025` em vez de `2026` no prazo final. O coletor analisa o texto completo e links embutidos (`sei.anac.gov.br`, `in.gov.br`, etc.) e corrige erros de digitação de ano em processos recém-publicados. |
| **Memória & Cache (`historico_processos.json`)** | Persistência local de estado e dossiês | Registra a data da 1ª detecção de cada processo e faz cache das análises do Gemini por versão com granularidade até minuto (`id` + `updatedAt[:16]`), invalidando automaticamente o cache caso o ministério edite o rascunho no mesmo dia. |
| **Higienização Editorial e Rótulos (`coletor_participativo.py`)** | Correção ortográfica de títulos do portal + enriquecimento de links âncora | Corrige erros de digitação de operadores públicos (ex.: `"Cosulta"` $\rightarrow$ `"Consulta"` no `#669`), converte links `"clique aqui"` em botões claros (`📝 Enviar Contribuição (ParticipANTT)`) e exibe `Cadastro no Portal` quando a janela de contribuição iniciou no órgão antes do espelhamento no Brasil Participativo (`#792`/`#793`). |
| **Modo Contínuo + Carência de 72h (`ENCERRADO_RECENTE`)** | Painel único contínuo (`radar_atual.html` / `radar.html`) + filtro de 72h pós-vencimento | O Radar opera sem gerar arquivos datados diários: processos recém-vencidos permanecem visíveis ao final da página por **72h (3 dias)** com o selo `⏹️ PRAZO VENCIDO`, esmaecimento acentuado (`opacity: 0.56`, `grayscale(75%)`, borda tracejada e título tachado, recuperando nitidez ao passar o mouse) antes de saírem automaticamente do painel. |
| **Contador Regressivo em Tempo Real (Live Countdown)** | JavaScript `atualizarContadoresTempoReal()` (`setInterval` de 30s) | Todos os processos abertos exibem cronômetro ao vivo até os minutos (`⏳ XXd XXh XXm`) até as `23:59:59` do dia de encerramento, transitando automaticamente no navegador caso o prazo se encerre com a tela aberta. |
| **Publicação Web & Automação Matinal Integrada** | Upload via `gh api` + Tarefa Agendada `ClippingDiario_DECON_MPOR` (Seg-Sex às 07:30) | Toda manhã útil às 07:30, o fluxo do Clipping executa automaticamente a coleta, curadoria, renderização e publicação do `radar.html` em modo contínuo no GitHub Pages. |
| **Expansão em 3 Abas Executivas (28/10/2026)** | Navegação por abas com *deep-linking* por hash (`#participativo`, `#estruturacao`, `#leiloes`) | Cobre todo o ciclo de vida das outorgas: **Aba 1** (Participação Social no Brasil Participativo), **Aba 2** (Estruturação, EVTEAs & Contratações no BNDES, Infra S.A., DNIT e PNCP) e **Aba 3** (Radar de Leilões & Outorgas — MPor/ANTAQ, ANAC, MT/ANTT, B3 e Nacionais). |
| **Rigor Factual e Verificação nos PDFs Oficiais na Aba 2 (v2 — 28/10/2026)** | Fichas documentais 100% factuais (`ficha_documental_verificada=True`), sem juízo de valor ou prescrições (*"deve contemplar"*, *"ótica DECON"*), estruturadas em **Prioridade A (Núcleo MPor: Portos, Aeroportos e Hidrovias)**, **Prioridade B (Comparação Federal: Rodovias/Ferrovias)** e **Prioridade C (Obras do setor MPor com cláusula de retomada do art. 102 da Lei 14.133 expressa no edital)** | Cada card traz Objeto, Valor, Situação, localização exata do escopo (TR / Especificações Técnicas + nº de páginas), citações literais entre aspas sobre Seguros, Garantias e Matriz de Riscos (diferenciando matriz do contrato de consultoria vs. matriz da futura concessão) e botões diretos para todos os PDFs/XLSX oficiais (incluindo os documentos da `RFP 014/2024` localizados na subpágina `rodovias-ne` do BNDES). |

---

## 4. Inventário dos Arquivos

Todos os arquivos estão em: `C:\Users\marcos.castilho\testes-gemini\radar_participativo`

* **`coletor_participativo.py`**: Motor GraphQL que extrai processos publicados e em pré-publicação, limpa o HTML, extrai links embutidos (SEI, DOU, Minutas, Notas Técnicas, PDFs), deduplica rascunhos já publicados e classifica o ciclo de vida (`LANCADO_48H`, `PRAZO_URGENTE`, `ABERTO`, `PRE_PUBLICACAO`, `ENCERRADO_RECENTE` até 72h e `EXPIRADO_ANTIGO`).
* **`coletor_estruturacao_leiloes.py`**: Coletor das Abas 2 e 3. Na Aba 2 (`#estruturacao`), aplica os critérios estritos de inclusão (**Prioridade A — Núcleo MPor**: EVTEA e modelagem de concessão/PPP/arrendamento de portos, aeroportos e hidrovias; **Prioridade B — Comparação**: EVTEA e modelagem federal de rodovias/ferrovias estruturados por Infra S.A. e BNDES; **Prioridade C**: obras em ativos do setor MPor com cláusula de retomada do art. 102 da Lei 14.133 expressamente exigida no edital), com fichas documentais 100% factuais verificadas nos PDFs oficiais e links diretos para todos os anexos (incluindo os documentos da `RFP 014/2024` na subpágina `rodovias-ne` do BNDES). Na Aba 3 (`#leiloes`), monitora os 12 leilões prioritários (MPor/ANTAQ, MPor/ANAC, MT/ANTT, B3 e nacionais).
* **`curador_participativo.py`**: Filtra ruídos na Aba 1 e consolida as fichas documentais factuais na Aba 2 (sem expressões opinativas ou prescritivas), preservando integralmente os itens com ficha documental verificada nos PDFs oficiais (`ficha_documental_verificada=True`).
* **`renderizador_participativo.py`**: Gera o painel contínuo `radar_atual.html` em 3 abas (`#participativo`, `#estruturacao`, `#leiloes`) com KPIs dinâmicos, filtros por recorte/prioridade, busca instantânea, contador regressivo ao vivo (`⏳ XXd XXh XXm`) e botões diretos para os PDFs/XLSX oficiais.
* **`publicador_web.py`**: Módulo compartilhado que publica automaticamente `radar.html`, `clipping.html`, `historico/` e `email_dispatch.json` no GitHub Pages (`https://mdagavea.github.io/inteligencia-regulatoria/`) via GitHub CLI (`gh api`).
* **`gerar_radar.py`** / **`executar_radar.bat`**: Orquestrador do Radar e atalho de 2 cliques no Windows (usa `python3.12`), também invocado automaticamente todos os dias úteis às 07:30 pelo `gerar_clipping.py`.
* **`historico_processos.json`**: Banco local de estado e cache de dossiês da IA.
* **`radar_atual.html`**: Painel executivo único em modo contínuo (espelhado em `radar.html` no GitHub Pages).

---

## 5. Próximos Passos para Retomada em Futuras Sessões

1. **Ajustes Pós-Feedback da Equipe:** Refinar prompts do dossiê, filtros por órgão (ex: filtro dedicado para MT / MPOR / ANTT / ANTAQ / ANAC) ou destacar processos prioritários.
2. **Extração Profunda de Anexos PDF (Sob Demanda):** Caso desejado, criar funcionalidade para baixar e resumir automaticamente o inteiro teor da Minuta de Portaria / Nota Técnica em PDF dos processos marcados como de "Alta Relevância".
3. **Automação Matinal Unificada:** Criar uma tarefa agendada única no Windows que rode o Radar e o Clipping às 07:30 e atualize ambos os links do GitHub Pages sem intervenção manual.

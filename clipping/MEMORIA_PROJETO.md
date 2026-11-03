# Memória do Projeto: Clipping Regulatório & Financeiro

> **Data de Criação:** 25 de Setembro de 2026  
> **Última Atualização:** 03 de Novembro de 2026  
> **Repositório GitHub (Nuvem Oficial & Código-Fonte):** `https://github.com/mdagavea/inteligencia-regulatoria`  
> **Local Espelhado (Sincronizado via Git):** `C:\Users\marcos.castilho\testes-gemini\clipping`  
> **Projeto Irmão (Integrado):** `C:\Users\marcos.castilho\testes-gemini\radar_participativo`  
> **Perfil do Usuário:** Analista/Executivo, busca uma solução 100% autônoma em nuvem, portátil (independente de máquina/ministério), resiliente a falta de energia ou falta de créditos de IA, e compatível com múltiplos agentes (Gemini, Claude e GitHub Copilot).

---

## 1. Links Públicos na Web (GitHub Pages — Atualização Automática)

Os painéis são publicados automaticamente no repositório `mdagavea/inteligencia-regulatoria` via GitHub CLI (`gh api`):

* 🌐 **Hub Central:** `https://mdagavea.github.io/inteligencia-regulatoria/`
* 📰 **Clipping Diário Regulatório, Financeiro & Tecnológico (Edição Atual):** `https://mdagavea.github.io/inteligencia-regulatoria/clipping.html`
* 📚 **Repositório Histórico de Edições Diárias (Catálogo por Data):** `https://mdagavea.github.io/inteligencia-regulatoria/historico/index.html`
* 🏛️ **Radar Brasil Participativo (Gestão & Dossiês):** `https://mdagavea.github.io/inteligencia-regulatoria/radar.html`

---

## 2. Objetivo e Escopo de Negócio

Construir e manter um sistema autônomo diário de inteligência e curadoria de notícias regulatórias e financeiras focado em 4 verticais estratégicas no Brasil, além de exibir uma faixa informativa com novos processos participativos abertos nas últimas 48h no Governo Federal:

1. **Infraestrutura & Outorgas:** Concessões, PPPs, leilões, reequilíbrio econômico-financeiro, matrizes de risco, PPI, agências reguladoras (ANTT, ANAC, ANTAQ, DNIT), MT, MPOR e portos/ferrovias/rodovias/aeroportos.
2. **Seguros de Grandes Riscos:** Performance bonds (seguro-garantia sob a nova Lei de Licitações), diretrizes de seguros em concessões/arrendamentos, riscos de engenharia/climáticos, regulação SUSEP e resseguro.
3. **Mercado de Carbono & Transição Climática:** Sistema Brasileiro de Comércio de Emissões (SBCE), Taxonomia Sustentável Brasileira (TSB), certificação de infraestrutura sustentável, integridade de créditos de carbono e Fundo Clima.
4. **Instrumentos de Dívida & Mercado de Capitais:** Debêntures incentivadas (Lei 12.431), debêntures de infraestrutura (Lei 14.801), regulação CVM, ANBIMA, BNDES, apoio oficial ao crédito e FIDCs.
5. **Tecnologia, IA & Gestão Aplicada (Adicionada em 25/10/2026):** Infraestrutura digital (data centers e transição energética da IA), regulação de IA/pagamentos agênticos, GovTech/FinTech, produtividade executiva e estratégia global (McKinsey, a16z, Substack, JOTA, grandes veículos).

---

## 3. Decisões Arquiteturais Fundamentadas

| Componente / Desafio | Decisão Adotada na Prática | Racional Técnico |
| :--- | :--- | :--- |
| **Fontes de Notícias** | **Google News RSS Temático + Feeds Abertos** | Evita quebras por bloqueio anti-bot (Cloudflare/paywall) e já indexa Valor, Estadão, G1, ConJur, agências e portais setoriais. |
| **Curadoria e Deduplicação** | **Python (`python3.12`) + Chamada Direta à API Gemini** | Uma única chamada estruturada em JSON filtra ruído, deduplica e classifica tudo nas subseções editoriais, com fallback automático de modelos (`gemini-3.1-flash-lite` $\rightarrow$ `gemini-3.5-flash-lite` $\rightarrow$ `gemini-3.8-flash`). |
| **Integração Brasil Participativo (21/10/2026)** | **Faixa Informativa 48h no topo do Dashboard** | Consulta o módulo `radar_participativo` para listar no topo do `clipping.html` apenas os processos efetivamente lançados no dia ou na véspera (últimas 48h), com botão direto para o painel completo do Radar. |
| **Compartilhamento via WhatsApp (21/10/2026)** | **Publicação Automática no GitHub Pages (`publicador_web.py`)** | Em vez de enviar arquivos `.html` como anexo (que travam em celulares), o script publica automaticamente no GitHub Pages via `gh api` (com `.nojekyll`) e atualiza a URL `https://mdagavea.github.io/inteligencia-regulatoria/clipping.html`. |

---

## 4. Inventário dos Arquivos do Projeto

Todos os arquivos estão consolidados em: `C:\Users\marcos.castilho\testes-gemini\clipping`

* **`coletor.py`**: Motor de busca e agregação RSS nas 4 verticais com fallback automático (24h/48h).
* **`curador.py`**: Integração com a API do Gemini para eliminação de duplicidades e classificação em subseções editoriais em formato JSON.
* **`renderizador.py`**: Gera o HTML final com a **Faixa Informativa do Brasil Participativo (48h)** no topo e o **Grid 2x2 Horizontal** das 4 verticais abaixo.
* **`gerar_clipping.py`**: Script mestre orquestrador. Coordena `coletor.py`, `curador.py`, busca os lançamentos 48h no `radar_participativo`, renderiza o HTML local e aciona o `publicador_web.py` para atualizar o GitHub Pages.
* **`executar_clipping.bat`**: Arquivo executável de 2 cliques para o Windows (usa `python3.12`).
* **`.env`**: Armazena a chave de API do Gemini (`GEMINI_API_KEY=...`).
* **`clipping_atual.html`** e **`clipping_AAAA-MM-DD.html`**: Versão local atualizada e histórico arquivado por data.

---

## 5. Histórico de Evoluções e Próximos Passos

### Concluído em 25/09/2026:
* [x] Concepção e implementação do pipeline `coletor.py` + `curador.py` + `renderizador.py`.
* [x] Homologação do layout executivo Grid 2x2.

### Concluído em 21/10/2026:
* [x] Criação do projeto irmão independente **Radar Brasil Participativo** (`C:\Users\marcos.castilho\testes-gemini\radar_participativo`).
* [x] Adição da **Faixa Informativa 48h** no topo do `clipping_atual.html` listando novos processos participativos abertos no dia/véspera.
* [x] Criação do publicador automático para o **GitHub Pages** (`https://mdagavea.github.io/inteligencia-regulatoria/clipping.html`), permitindo envio e leitura com 1 clique no WhatsApp da equipe.

### Concluído em 25/10/2026:
* [x] Reengenharia do `coletor.py` com **4 motores simultâneos**:
  1. **Via Expressa VIP** (`Valor Econômico, Broadcast, Reuters, O Globo, Folha de S.Paulo, Estadão, Agência iNFRA, JOTA e CNseg`);
  2. **Feeds Diretos Especializados** (`Agência iNFRA` em `agenciainfra.com/blog/feed/`, `Capital Reset` com contorno de certificado SSL da UOL, `JOTA` e `a16z News`);
  3. **Leitor de Newsletters do Gmail via HTTPS Atom (porta 443)** (`marcoslcastilho@gmail.com` com Senha de App, capturando *Reset News, JOTA, CNseg, McKinsey, Environmental Finance, Substack IA*, etc., sem bloqueio de firewall na porta 993/IMAP);
  4. **Varredura Aberta Temática** no Google News RSS.
* [x] Inclusão da **5ª Vertical: Tecnologia, IA & Gestão Aplicada** no `curador.py` e no `renderizador.py` (faixa horizontal panorâmica na base do Grid 2x2).
* [x] Arquitetura de **Dupla Camada (Vitrine de Destaques + Gaveta Expansível "Radar Complementar")**: capacidade elevada para 30 a 50 matérias curadas por edição, mantendo 3–4 destaques abertos por card e guardando as demais pautas relevantes em uma gaveta `<details class="radar-drawer">` expansível por card (ou via botão geral `➕ Expandir Todos os Radares` no topo).
* [x] **Identidade Visual Setorial DECON/MPOR (`renderizador.py`)**: paleta editorial creme/papel/marinho/coral/ocre/teal inspirada nos slides de despacho interno da DECON, com Rosa dos Ventos no cabeçalho, cabeçalhos texturizados estilo contêiner marítimo, medalhões circulares vetoriais (Âncora, Escudo, Folha, Gráfico e Lupa), carimbo de data inclinado e panorama ilustrado em SVG no rodapé (guindastes portuários, navio porta-contêineres, hidrovia, avião decolando e torre de controle).
* [x] **Repositório Histórico por Data (`historico/` Local e GitHub Pages)**: toda edição diária gerada é salva automaticamente em `historico/clipping_AAAA-MM-DD.html` (local e Web), com menu seletor `📚 Acervo de Edições` integrado ao cabeçalho do Clipping e catálogo completo em `historico/index.html`.
* [x] **Automação nos Dias Úteis no Agendador de Tarefas do Windows (`ClippingDiario_DECON_MPOR`)**: configurada para rodar silenciosamente de **Segunda a Sexta-feira às 07:30** via `executar_automatico.bat` (na segunda-feira, o `gerar_clipping.py` usa automaticamente a janela de `72h` para acumular o fim de semana; de terça a sexta, usa `24h`), com `StartWhenAvailable` e suporte à bateria.
* [x] **Disparo Automático por E-mail para a Diretoria (`EMAIL_DESTINATARIOS`) + Botão de Resumo WhatsApp**:
  - **E-mail da Diretoria:** `marcos.castilho@mpor.gov.br`, `helena.venceslau@mpor.gov.br`, `cintia.barreto@mpor.gov.br` e `ana.freitas@mpor.gov.br`. O envio é acionado via HTTPS pelo `gerar_clipping.py` (`email_dispatch.json`) e entregue na nuvem pelo GitHub Actions (`.github/workflows/disparo_email.yml`), contornando qualquer bloqueio de porta SMTP na rede local.
  - **WhatsApp da Diretoria:** Botão **`📲 Copiar Resumo WhatsApp`** integrado ao cabeçalho do `clipping.html`, copiando em 1 clique a síntese executiva formatada em Markdown nativo do WhatsApp + link do painel completo.
* [x] **Responsividade Mobile Vertical (`@media (max-width: 640px)`)**: ajuste nos cabeçalhos dos cards para empilhamento limpo no modo retrato do celular, evitando corte da pílula `X Destaques + Y no Radar`.
* [x] **Sincronização Diária Automática com o Radar Contínuo**: o `gerar_clipping.py` agora re-renderiza e publica automaticamente o `radar.html` a cada execução matinal, mantendo contadores regressivos (`⏳ XXd XXh XXm`) e processos recém-vencidos (até 72h com esmaecimento visual) sempre em dia.

### Concluído em 27/10/2026:
* [x] **Arquitetura de Segurança Anti-*Phantom Squatting* e Defesa em Profundidade (`coletor.py`, `curador.py`, `renderizador.py`)**:
  1. **Vínculo Determinístico de Links por ID Numérico (`_vincular_links_originais` em `curador.py`):** as URLs brutas (incluindo os tokens Base64 de ~250 caracteres do Google News) não são mais enviadas para a IA nem geradas por ela. Cada matéria entra numerada como `[ID: X]`, a IA devolve apenas `"id": X` no JSON e o próprio Python recupera diretamente `noticias_brutas[id - 1]["link"]` (com validação cruzada de título/fonte). Resultado: zero risco de *Phantom Squatting* (domínios alucinados pela IA), zero risco de corrupção de caracteres Base64 e ~35% de economia de tokens/latência na chamada do Gemini.
  2. **Allowlist Estrita de Servidores de Origem (`ALLOWED_FEED_HOSTS` + `_url_segura_permitida` em `curador.py`):** validação sintática via `urllib.parse.urlparse` exigindo protocolo `https://` e restringindo os links exclusivamente aos 6 domínios oficiais dos coletores (`news.google.com`, `agenciainfra.com`, `capitalreset.uol.com.br`, `jota.info`, `a16z.news`, `mail.google.com`).
  3. **Filtro de Qualidade Editorial e Bloqueio de Redes Sociais (`SOCIAL_MEDIA_BLOCKLIST` em `coletor.py`):** na busca do Google News RSS (`fetch_google_news`), valida se `source.href` possui `https://` e descarta postagens de redes sociais (`instagram.com`, `facebook.com`, `tiktok.com`, `x.com`, `twitter.com`, `threads.net`, `pinterest.com`) **sem perder vagas no lote** (substituindo automaticamente pela próxima reportagem jornalística da fila).
  4. **Isolamento de Aba (`rel="noopener noreferrer"` em `renderizador.py`):** adicionado em todos os links externos `<a target="_blank">` para proteção contra *Reverse Tabnabbing*.
* [x] **Auditoria e Reparo Retroativo das Edições de 26/10 e 27/10**: corrigidos os 5 links alucinados da edição de 26/10 e os 3 tokens Base64 da edição matinal de 27/10 tanto nos arquivos locais quanto no GitHub Pages.
* [x] **Plano de Escalonamento de Capacidade em 3 Degraus (Ativado o Degrau 1 — Expansão Moderada)**:
  - Mantida a **Vitrine Principal** enxuta em **3 a 4 destaques por card** (para leitura rápida de 3 minutos sem *flood* visual), concentrando o ganho de volume na **Rede de Pesca Bruta** e na **Gaveta Recolhida ("📂 Radar Complementar")**:

| Parâmetro | Baseline Original | **Degrau 1: Moderado (ATIVO)** | Degrau 2: Denso *(Futuro)* | Degrau 3: Exaustivo *(Futuro)* |
| :--- | :---: | :---: | :---: | :---: |
| **Rede de Pesca Bruta (`coletor.py`)** | ~82–95 brutas | **~125–140 brutas (+45%)** | ~160–180 brutas (+90%) | ~210+ brutas (+130%) |
| • *Via Expressa VIP (por vertical)* | 6 vagas | **9 vagas** | 12 vagas | 15 vagas |
| • *Varredura Aberta (por vertical)* | 6 vagas | **8 vagas** | 10 vagas | 12 vagas |
| • *Feeds Diretos (iNFRA/Reset/JOTA/a16z)* | 12 / 8 / 8 / 5 *(33)* | **15 / 10 / 10 / 6 *(41)*** | 18 / 12 / 12 / 8 *(50)* | 22 / 15 / 15 / 10 *(62)* |
| • *Newsletters do Gmail* | 15 edições | **20 edições** | 25 edições | 30 edições |
| **Vitrine Aberta (`destaque` / card)** | 3 a 4 | **3 a 4 *(Fixo — sem flood)*** | 4 *(Fixo — sem flood)* | 4 a 5 |
| **Gaveta Recolhida (`complementar` / card)** | 1 a 2 | **4 a 5 por card** | 6 a 8 por card | 8 a 10 por card |
| **Total Curado no Painel (5 verticais)** | ~25 a 27 matérias | **~38 a 45 matérias** | ~50 a 60 matérias | ~65 a 75 matérias |

### Concluído em 28/10/2026:
* [x] **Substituição de Matéria Retirada do Ar na Edição de 28/10/2026**: substituída a matéria deletada pelo portal Diarinho (`676477`) pela matéria do dia da Agência iNFRA (*"Tecon 10 e canal de Itajaí devem ganhar ritmo no governo após eleições"*), mantendo a diretriz de **não bloquear** veículos com paywall (como GZH) ou portais regionais no `coletor.py` (pois as manchetes permanecem úteis para pesquisa).
* [x] **Integração com as Novas Abas 2 (`#estruturacao`) e 3 (`#leiloes`) do Radar DECON/MPor**:
  - A faixa superior de processos do Brasil Participativo em `renderizador.py` (`render_faixa_participativo`) agora inclui botões de atalho direto para `radar.html#participativo`, `radar.html#estruturacao` (EVTEAs & Estruturação — BNDES, Infra S.A., DNIT e PNCP) e `radar.html#leiloes` (Leilões & Outorgas — ANTAQ, ANAC, ANTT e B3).
  - Na **Aba 2 (`#estruturacao` v2)**, foi consolidado o padrão 100% factual verificado nos PDFs oficiais (sem juízos de valor/opiniões), focado em **Prioridade A (Núcleo MPor: Portos, Aeroportos e Hidrovias)** e **Prioridade B (Comparação Federal: Rodovias e Ferrovias)**, com links diretos para todos os anexos técnicos.

### Concluído em 03/11/2026:
* [x] **Migração Completa para a Nuvem (`mdagavea/inteligencia-regulatoria` + GitHub Actions) e Portabilidade Total**:
  - Todo o código-fonte de `clipping/` e `radar_participativo/` passou a residir versionado no repositório GitHub `mdagavea/inteligencia-regulatoria` (e sincronizado com a pasta local via Git).
  - Criado o workflow principal em nuvem [`.github/workflows/clipping_diario_nuvem.yml`](../.github/workflows/clipping_diario_nuvem.yml), que roda de **Segunda a Sexta-feira às 07:30 BRT** (`30 10 * * 1-5` UTC) diretamente nos servidores do GitHub (`ubuntu-latest`), **sem depender do computador local estar ligado**.
  - Configurados todos os 4 *Secrets* no GitHub (`GEMINI_API_KEY`, `GMAIL_USER`, `GMAIL_APP_PASSWORD` e `EMAIL_DESTINATARIOS`).
  - Adicionada trava anti-duplicidade (`--skip-if-exists` em `gerar_clipping.py` e no workflow): caso a edição do dia (`historico/clipping_AAAA-MM-DD.html`) já exista, nenhuma segunda execução automática gasta tokens ou reenvia e-mail.
* [x] **Modo de Contingência Determinístico sem IA (`curar_noticias_contingencia_sem_ia` em `curador.py` e resiliência em `curador_participativo.py`)**:
  - Se a chave `GEMINI_API_KEY` ficar sem créditos/cota ou se os servidores da IA falharem, o sistema **não interrompe a execução**: ele aciona automaticamente o classificador determinístico por vertical, gera o painel e dispara o e-mail normalmente (e, no Radar, não grava falha no cache para reprocessar na próxima rodada).
* [x] **Interoperabilidade Multi-Agente (Claude, GitHub Copilot e Gemini)**:
  - Criados na raiz do repositório os guias [`CLAUDE.md`](../CLAUDE.md), [`GEMINI.md`](../GEMINI.md) e [`.github/copilot-instructions.md`](../.github/copilot-instructions.md), permitindo que qualquer agente de IA assuma a manutenção imediatamente na nuvem ou localmente via `git pull` / `git push`.

### Próximos Passos para Futuras Sessões:
1. **Avaliar Transição para o Degrau 2:** Após alguns dias de uso prático do **Degrau 1**, caso deseje ainda mais profundidade nas gavetas complementares, elevar os parâmetros do `coletor.py` e `curador.py` para o **Degrau 2**.
2. **Incorporar Sugestões da Diretoria:** Ajustar recortes temáticos, adicionar novos órgãos/fontes ou calibrar filtros a partir do feedback das execuções automáticas da semana.
3. **Aprofundamento Normativo sob Demanda:** Caso desejado, expandir dossiês específicos do Radar Brasil Participativo com leitura automática de minutas em PDF anexadas.

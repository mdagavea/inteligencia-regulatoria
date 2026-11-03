# Histórico de Evoluções do Projeto: Clipping Regulatório & Financeiro

> Este arquivo armazena o registro histórico das evoluções concluídas (separado do `MEMORIA_PROJETO.md` para manter a leitura de contexto enxuta).

---

## Concluído em 25/09/2026:
* [x] Concepção e implementação do pipeline `coletor.py` + `curador.py` + `renderizador.py`.
* [x] Homologação do layout executivo Grid 2x2.

## Concluído em 21/10/2026:
* [x] Criação do projeto irmão independente **Radar Brasil Participativo** (`radar_participativo/`).
* [x] Adição da **Faixa Informativa 48h** no topo do `clipping_atual.html` listando novos processos participativos abertos no dia/véspera.
* [x] Criação do publicador automático para o **GitHub Pages** (`https://mdagavea.github.io/inteligencia-regulatoria/clipping.html`).

## Concluído em 25/10/2026:
* [x] Reengenharia do `coletor.py` com **4 motores simultâneos** (Via Expressa VIP, Feeds Diretos Especializados, Newsletters do Gmail via HTTPS Atom porta 443 e Varredura Aberta no Google News RSS).
* [x] Inclusão da **5ª Vertical: Tecnologia, IA & Gestão Aplicada**.
* [x] Arquitetura de **Dupla Camada (Vitrine de Destaques + Gaveta Expansível "Radar Complementar")**.
* [x] **Identidade Visual Setorial DECON/MPOR (`renderizador.py`)**.
* [x] **Repositório Histórico por Data (`historico/` Local e GitHub Pages)**.
* [x] **Disparo Automático por E-mail para a Diretoria (`EMAIL_DESTINATARIOS`) + Botão de Resumo WhatsApp**.

## Concluído em 27/10/2026:
* [x] **Arquitetura de Segurança Anti-*Phantom Squatting* e Defesa em Profundidade**:
  1. Vínculo determinístico de links por ID numérico (`_vincular_links_originais` em `curador.py`);
  2. Allowlist estrita de servidores de origem (`ALLOWED_FEED_HOSTS`);
  3. Bloqueio de redes sociais (`SOCIAL_MEDIA_BLOCKLIST` em `coletor.py`);
  4. Isolamento de aba (`rel="noopener noreferrer"`).
* [x] **Plano de Escalonamento de Capacidade em 3 Degraus (Ativado o Degrau 1 — Expansão Moderada: 38–45 matérias)**.

## Concluído em 28/10/2026:
* [x] Substituição de matéria retirada do ar na edição de 28/10/2026.
* [x] Integração da faixa superior do Clipping com as Abas 2 (`#estruturacao`) e 3 (`#leiloes`) do Radar DECON/MPor.

## Concluído em 03/11/2026:
* [x] **Migração 100% para a Nuvem (`mdagavea/inteligencia-regulatoria` + GitHub Actions)**: workflow `.github/workflows/clipping_diario_nuvem.yml` rodando de segunda a sexta às 07:30 BRT independente da máquina local, com trava anti-duplicidade (`--skip-if-exists`) e sincronizador `sincronizar_nuvem.py`.
* [x] **Modo de Contingência Determinístico sem IA (`curar_noticias_contingencia_sem_ia`)**.
* [x] **Economia de Tokens na API (`termos_filtro.json`, `log_descartados_filtro.txt` e `historico_noticias_cache.json`)** e separação de `MEMORIA_PROJETO.md` vs. `HISTORICO_PROJETO.md`.

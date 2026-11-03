# Guia de Arquitetura e Operação Multi-Agente (Claude, Copilot & Gemini)
## Projeto: Hub de Inteligência Regulatória & Financeira (`mdagavea/inteligencia-regulatoria`)

> **Repositório GitHub (Nuvem Oficial):** `https://github.com/mdagavea/inteligencia-regulatoria`  
> **GitHub Pages (Painéis Públicos):** `https://mdagavea.github.io/inteligencia-regulatoria/`  
> **Última Atualização Arquitetural:** 03/11/2026 (Migração para execução 100% em nuvem via GitHub Actions + Interoperabilidade entre Agentes de IA)

---

## 1. Visão Geral para Agentes de IA (Claude, GitHub Copilot e Gemini)

Este repositório unifica dois sistemas autônomos de inteligência executiva da **DECON / MPOR**:

1. **`clipping/` — Clipping Diário Regulatório, Financeiro & Tecnológico:**
   - Coleta notícias e newsletters nas 5 verticais (`infra`, `seguros`, `carbono`, `divida`, `tech`).
   - Faz curadoria via API Gemini (`curador.py`) — com **fallback determinístico automático sem IA** (`curar_noticias_contingencia_sem_ia`) caso os créditos da API Gemini se esgotem.
   - Gera o painel executivo (`clipping.html` e `historico/clipping_AAAA-MM-DD.html`) e dispara o boletim por e-mail via SMTP.
   - **Documentação detalhada:** leia [`clipping/MEMORIA_PROJETO.md`](clipping/MEMORIA_PROJETO.md).

2. **`radar_participativo/` — Radar DECON/MPOR (Participação Social, Estruturação/EVTEAs & Leilões):**
   - Monitora processos no Brasil Participativo, contratações de estudos/EVTEAs (Infra S.A., BNDES, DNIT, PNCP) e carteira de leilões (ANTAQ, ANAC, ANTT, B3).
   - Gera o painel contínuo em abas (`radar.html`).
   - **Documentação detalhada e backlog de evolução:** leia [`radar_participativo/MEMORIA_PROJETO.md`](radar_participativo/MEMORIA_PROJETO.md), [`radar_participativo/2026-10-28_Ajustes_Aba_Estruturacao_para_Gemini.md`](radar_participativo/2026-10-28_Ajustes_Aba_Estruturacao_para_Gemini.md) e [`radar_participativo/2026-10-29_Passagem_Aba_SFN_e_Agencias_para_Gemini.md`](radar_participativo/2026-10-29_Passagem_Aba_SFN_e_Agencias_para_Gemini.md).

---

## 2. Como Funciona a Execução Diária na Nuvem (GitHub Actions)

* **Workflow Principal:** [`.github/workflows/clipping_diario_nuvem.yml`](.github/workflows/clipping_diario_nuvem.yml)
* **Agendamento (`cron`):** Roda automaticamente de **Segunda a Sexta-feira às 07:30 BRT** (`30 10 * * 1-5` UTC) diretamente nos servidores do GitHub (`ubuntu-latest`), **sem depender de nenhum computador local ligado**.
* **Secrets configurados no GitHub (`Settings -> Secrets and variables -> Actions`):**
  - `GEMINI_API_KEY`: Chave da API Google Gemini.
  - `GMAIL_USER`: Conta Gmail para leitura Atom de newsletters e envio SMTP.
  - `GMAIL_APP_PASSWORD`: Senha de aplicativo do Gmail.
  - `EMAIL_DESTINATARIOS`: Lista de destinatários separada por vírgula.
* **Trava Anti-Duplicidade (`--skip-if-exists`):**
  - Se a edição do dia (`historico/clipping_AAAA-MM-DD.html`) já tiver sido gerada e publicada, execuções automáticas subsequentes encerram imediatamente sem gastar tokens e sem reenviar e-mail.

---

## 3. Como Qualquer Agente de IA Deve Atuar Neste Projeto

Sempre que o usuário solicitar manutenção ou evolução (seja pelo **Claude**, **GitHub Copilot** ou **Gemini**):

1. **Sincronizar antes de editar (em máquina corporativa sem `git.exe`, use `sincronizar_nuvem.py` via `gh api`):**
   ```powershell
   python3.12 C:\Users\marcos.castilho\testes-gemini\sincronizar_nuvem.py pull
   ```
   *(Se estiver em outra máquina com `git` instalado: `git pull origin main`)*
2. **Ler a memória da frente correspondente:**
   - Para demandas do Clipping: `clipping/MEMORIA_PROJETO.md`
   - Para demandas do Radar / Novas Abas (ex.: Aba 4 SFN): `radar_participativo/MEMORIA_PROJETO.md` e `radar_participativo/2026-10-29_Passagem_Aba_SFN_e_Agencias_para_Gemini.md`
3. **Respeitar as Regras Inegociáveis do Projeto:**
   - **Proibido alucinar URLs:** no Clipping, os links vêm exclusivamente de `_vincular_links_originais` por ID numérico; no Radar, apenas links oficiais verificados.
   - **Tom 100% factual e verificável nas fichas técnicas do Radar:** nunca usar opiniões ou expressões prescritivas ("deve contemplar", "recomenda-se", "sob a ótica da DECON").
   - **Resiliência sem IA:** nenhuma falha de cota/crédito da API de IA pode derrubar a geração dos painéis ou o envio do e-mail.
4. **Publicar alterações diretamente na nuvem:**
   - Como a execução oficial ocorre no GitHub Actions, toda alteração feita em scripts Python (`clipping/*.py` ou `radar_participativo/*.py`) ou nas memórias (`*.md`) **deve ser enviada ao repositório GitHub** imediatamente após editar:
   ```powershell
   python3.12 C:\Users\marcos.castilho\testes-gemini\sincronizar_nuvem.py push "Descricao da alteracao"
   ```
   - Sempre atualize o respectivo `MEMORIA_PROJETO.md` ao concluir cada etapa.

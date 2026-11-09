# Guia de Arquitetura e Operação Multi-Agente (Claude, Copilot & Gemini)
## Projeto: Hub de Inteligência Regulatória & Financeira (`mdagavea/inteligencia-regulatoria`)

> **Repositório GitHub (Nuvem Oficial):** `https://github.com/mdagavea/inteligencia-regulatoria`  
> **GitHub Pages (Painéis Públicos):** `https://mdagavea.github.io/inteligencia-regulatoria/`  
> **Última Atualização Arquitetural:** 05/11/2026 (GEMINI_API_KEY reativada para o clipping na nuvem e local; Radar operando em modo factual sem IA localmente agendado às 08:00; trava de segurança editorial e sanidade automática; isolamento do radar no clipping; anonimização total via secret EMAIL_TESTE e modo_teste booleano; regra "nenhum dado digitado à mão").

---

## 1. Visão Geral para Agentes de IA (Claude, GitHub Copilot e Gemini)

Este repositório unifica dois sistemas autônomos de inteligência executiva da **DECON / MPOR**:

1. **`clipping/` — Clipping Diário Regulatório, Financeiro & Tecnológico:**
   - Coleta notícias e newsletters nas 5 verticais (`infra`, `seguros`, `carbono`, `divida`, `tech`).
   - Faz curadoria com IA em `curador.py` usando `gemini-2.5-flash`. A chave `GEMINI_API_KEY` foi **reativada por decisão do Marcos em 05/11/2026** (a rodada sem IA trouxe matérias descontextualizadas; o custo é baixo e a decisão está tomada).
   - **Status da chave Gemini por ambiente:**
     - **GitHub Actions (Nuvem):** ATIVA via secret `secrets.GEMINI_API_KEY`.
     - **Clipping Local (`clipping/.env`):** ATIVA.
   - **Resiliência e Fallback:** Se a API Gemini falhar ou ficar sem cota, o fallback determinístico (`curar_noticias_contingencia_sem_ia`) entra automaticamente em ação sem interromper a publicação nem o envio do e-mail.
   - Gera o painel executivo (`clipping.html` e `historico/clipping_AAAA-MM-DD.html`) e dispara o boletim por e-mail via SMTP Gmail.
   - **Documentação detalhada:** leia [`clipping/MEMORIA_PROJETO.md`](clipping/MEMORIA_PROJETO.md).

2. **`radar_participativo/` — Radar DECON/MPOR (Participação Social, Estruturação/EVTEAs & Leilões):**
   - Monitora processos no Brasil Participativo, contratações de estudos/EVTEAs (Infra S.A., BNDES, DNIT, PNCP) e carteira de leilões (ANTAQ, ANAC, ANTT, B3).
   - **Status da chave Gemini no Radar:** Em `radar_participativo/.env`, a `GEMINI_API_KEY` permanece **não configurada** (o log exibe `"GEMINI_API_KEY ausente"`). O radar opera intencionalmente em **modo factual sem IA**, extraindo dados diretamente das fontes oficiais sem consumo de tokens.
   - **Execução e Agendamento:** O Radar é gerado e publicado pelo pipeline local completo (`radar_participativo/gerar_radar.py --no-browser`), configurado no Agendador de Tarefas do Windows (`RadarInteligenciaRegulatoria`) de **segunda a sexta-feira às 08:00 BRT** (com `StartWhenAvailable` para recuperar caso a máquina esteja desligada).
   - O workflow diário de clipping da nuvem **não toca nem publica `radar.html`**, evitando esvaziamento acidental das abas.
   - **Documentação detalhada e backlog de evolução:** leia [`radar_participativo/MEMORIA_PROJETO.md`](radar_participativo/MEMORIA_PROJETO.md), [`radar_participativo/2026-10-28_Ajustes_Aba_Estruturacao_para_Gemini.md`](radar_participativo/2026-10-28_Ajustes_Aba_Estruturacao_para_Gemini.md) e [`radar_participativo/2026-10-29_Passagem_Aba_SFN_e_Agencias_para_Gemini.md`](radar_participativo/2026-10-29_Passagem_Aba_SFN_e_Agencias_para_Gemini.md).

---

## 2. Como Funciona a Execução Diária na Nuvem (GitHub Actions)

* **Workflow Principal:** [`.github/workflows/clipping_diario_nuvem.yml`](.github/workflows/clipping_diario_nuvem.yml)
* **Agendamento (`cron`):** Roda automaticamente de **Segunda a Sexta-feira às 07:17 BRT** (`17 10 * * 1-5` UTC) diretamente nos servidores do GitHub (`ubuntu-latest`), **sem depender de nenhum computador local ligado**.
* **Secrets configurados no GitHub (`Settings -> Secrets and variables -> Actions`):**
  - `GEMINI_API_KEY`: Reativada em 05/11/2026 para a curadoria diária do clipping.
  - `GMAIL_USER`: Conta Gmail para leitura Atom de newsletters e envio SMTP.
  - `GMAIL_APP_PASSWORD`: Senha de aplicativo do Gmail.
  - `EMAIL_DESTINATARIOS`: Lista de destinatários separada por vírgula.
  - `EMAIL_TESTE`: Destinatário exclusivo para execuções de teste (endereço guardado no secret EMAIL_TESTE, não publicado).
* **Execução manual (`workflow_dispatch`):**
  - `forcar_reexecucao`: Permite regenerar e reenviar mesmo que a edição do dia já exista.
  - `modo_teste`: Booleano (`true`/`false`). Quando `true`, o envio é direcionado exclusivamente para o secret `EMAIL_TESTE`.
* **Privacidade e Repositório Público:**
  - Nenhum e-mail de destinatário aparece no console ou logs públicos. O envio no log relata apenas a quantidade (`"E-mail enviado com sucesso na nuvem para X destinatário(s)."`).
  - `email_dispatch.json` fica fora do repositório (não comitado).
* **Fontes do clipping:** o boletim de assinante da Agência iNFRA **não é fonte** (conteúdo pago). O site aberto (`agenciainfra.com/blog`, RSS) continua como fonte.
* **Aviso de projeto piloto:** `AVISO_PILOTO_FRASE` (topo) e `AVISO_PILOTO_TEXTO` (rodapé) mantidos em todas as páginas e no e-mail.
* **Trava Anti-Duplicidade (`check_hoje`):** Encerra sem gastar tokens se a edição do dia já tiver sido enviada e `forcar_reexecucao` não for `true`.

---

## 3. Regras Inegociáveis do Projeto (Respeito Obrigatório por Qualquer Agente)

Sempre que o usuário solicitar manutenção ou evolução (seja pelo **Claude**, **GitHub Copilot** ou **Gemini**):

1. **Nenhum dado digitado à mão (saída bruta antes de qualquer card):**
   - É estritamente proibido inserir informações de contratos, editais, datas, links ou valores de forma manual ou por inferência subjetiva.
   - Todo card deve obrigatoriamente derivar de saída bruta e verificada de coletores oficiais (APIs públicas, PDFs originais, DOU, GraphQL, PNCP, BNDES, TCU Plenário).
   - Se for criar ou alterar cards, exiba a saída bruta da fonte antes da inclusão.

2. **Correções valem na origem (código que gera a página), nunca só no HTML gerado:**
   - Qualquer ajuste em dados, textos, selos, termos proibidos ou formatações deve ser implementado no código Python que renderiza a página (coletores, renderizadores e curadores), nunca apenas no arquivo `.html` gerado, para evitar que novas execuções revertam o que foi corrigido.

3. **Trava de Segurança Editorial e Sanidade Pré-Publicação:**
   - Implementada em [`radar_participativo/validador_publicacao.py`](radar_participativo/validador_publicacao.py).
   - **Radar:** Varredura estrita de substrings proibidas (`decon`, `núcleo`, `nucleo`, `segurabilidade`); varredura estrita de `mpor` (apenas raízes lexicográficas legítimas como `import*` e `tempor*` são autorizadas; `MPOR_FOCO` e `mpor` avulso são reprovados); `"em execução"` proibido nos selos de situação (`deadline-pill` e `data-fim-br`); sanidade obrigatória (reprova se a Aba Estruturação tiver 0 cards ou se qualquer aba cair mais de 50%).
   - **Clipping:** Marca oficial DECON/MPOR mantida por decisão editorial. A trava reprova estritamente vazamento de dados que nunca podem ir a público: endereço institucional `@mpor.gov.br` e número de processo SEI federal (`\b\d{5}\.\d{6}/\d{4}-\d{2}\b`).

4. **Selo de Situação em Contratações (Aba Estruturação):**
   - Usar sempre "Contrato assinado em [data]". Nunca rotular como "Em Execução" sem fonte de vigência expressa.

5. **TCU com Colegiado Plenário:**
   - Nenhum acórdão do TCU pode ser incluído sem conferência pela API oficial do TCU, filtrando COLEGIADO "Plenário".

6. **Proibido alucinar URLs:**
   - No Clipping, os links vêm exclusivamente de `_vincular_links_originais` por ID numérico; no Radar, apenas links oficiais governamentais verificados.

7. **Tom 100% Factual:**
   - Proibido opinião, juízo de valor, "ótica DECON" ou recomendações prescritivas ("deve contemplar", "recomenda-se").

8. **Sincronizar antes e depois de editar:**
   ```powershell
   python3.12 $HOME\testes-gemini\sincronizar_nuvem.py pull
   # ... após editar:
   python3.12 $HOME\testes-gemini\sincronizar_nuvem.py push "Descricao da alteracao"
   ```

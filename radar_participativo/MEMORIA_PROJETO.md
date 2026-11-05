# Memória do Projeto: Radar DECON/MPor (Estado Atual)

> **Última Atualização:** 05/11/2026 (Encerramento do Expediente)  
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

## 2. Fase 1: Coletor do Diário Oficial da União (`coletor_dou.py`)

Em 05/11/2026, foi concluído o desenvolvimento preliminar da Fase 1, em **modo estritamente somente leitura** (sem publicação, sem cards criados e sem alteração no Radar).

### A. Travas no Código
1. **Link exclusivo via `urlTitle` com HTTP 200 obrigatório:** O endereço é montado unicamente a partir de `https://www.in.gov.br/web/dou/-/{urlTitle}` e testado na fonte oficial via requisição HTTP (status 200). Se falhar ou não tiver link válido, o ato é reprovado e vai para a lista de descartados.
2. **Ementa e 1ª linha literais:** Transcrição estrita dos primeiros caracteres do texto do ato (`content`), sem qualquer resumo, dedução ou paráfrase.
3. **Processo e Relator por regra:** Extraídos estritamente por regex; se não forem encontrados no texto bruto, o campo permanece vazio (`""`).
4. **Isolamento de REIDI e Enquadramentos:** Atos fiscais e de enquadramentos de projetos são gravados exclusivamente em arquivo local (`dados_reidi/atos_AAAA-MM.jsonl`), **fora do repositório**. A pasta `dados_reidi/` foi incluída no `.gitignore` e não consta no `ARQUIVOS_SINCRONIZADOS`.
5. **Setor Factual:** O setor só é gravado quando vier expressamente do texto da portaria do ministério; nunca por dedução.

### B. O que o DOU Entrega e o que Não Entrega (5 dias úteis de 2026: 29/10 a 05/11)
* **Total varrido:** 12.014 atos (1.703 no DO1 e 10.311 no DO3; dia 30/10 sem circulação ordinária regular).
* **Nos órgãos do filtro regulatório:** 1.855 atos.
* **O que o DOU entrega factualmente:**
  - Decretos do PPI e PND (ex.: Decreto nº 13.142/2026 no DO1 de 03/11).
  - Resoluções do CMN (ex.: Resolução CMN nº 5.344/2026 no DO1 de 03/11).
  - Portarias de composição do Fundo da Marinha Mercante (Portaria GM-MPOR nº 60/2026 no DO1 de 03/11).
  - Despachos ministeriais sobre Fundos Garantidores (Despacho MF de 28/10/2026 — 60ª Novação FCVS com FGC).
  - Enquadramentos prioritários para debêntures incentivadas (Portarias MCID nº 1.483/2026 [Socicam] e nº 1.484/2026 [Trivia Trens]).
  - Enquadramento e habilitações de REIDI (Portaria MCID nº 1.482/2026 e atos declaratórios da Receita Federal).
  - Acórdãos da ANTAQ (24 acórdãos no DO1 de 03/11 e 1 no DO1 de 04/11, incluindo o Acórdão nº 640/2026 sobre a Agenda EVTEA 2.0).
* **O que o DOU não entrega nessas 10 edições:**
  - Não houve atos normativos específicos publicados para FNAC, FGE, FGI, FGO nem FGHAB por seus órgãos gestores nesse intervalo de 5 dias úteis.
* **Status do Coletor:** O `coletor_dou.py` **NÃO está agendado em nenhum cron ou agendador local e NÃO publica nada**.

---

## 3. Erros da Sessão de 05/11/2026 e Lições Aprendidas

1. **Amostra Inicial com Ano Errado (2024 em vez de 2026):**
   * *Erro:* O coletor rodou inicialmente sobre datas de 2024, distorcendo o levantamento e gerando a conclusão errada de que acórdãos da ANTAQ "não saíam no DOU".
   * *Lição:* Verificar sempre a data corrente do sistema (2026) e auditar os metadados do payload antes de consolidar relatórios.
2. **Links e Ementa Digitados à Mão:**
   * *Erro:* Na formatação da resposta, 12 links foram montados manualmente com sufixos inventados (gerando 404), a ementa do Acórdão 640/2026 foi parafraseada com dados incorretos ("Caio Farias / proc. 009762") e o despacho da Fazenda foi descrito como "limites e diretrizes" em vez de novação do FCVS/FGC.
   * *Lição:* Regra nº 1 reforçada: **Nenhum dado digitado à mão**. Os links devem vir exclusivamente do `urlTitle` com teste prévio HTTP 200, e textos de ementa devem ser cópias literais dos primeiros caracteres do ato bruto.
3. **Filtro de Debêntures Incompleto:**
   * *Erro:* A busca inicial procurou apenas por "debêntures" e omitiu atos com "enquadramento, como prioritário", "Emissor/Controladora" e as Leis 12.431 e 14.801, deixando de fora as Portarias MCID 1.483 e 1.484.
   * *Lição:* Termos de busca em finanças públicas devem contemplar o vocabulário regulatório formal dos ministérios setoriais.
4. **Afirmação de Ausência sem Prova de Busca:**
   * *Erro:* Afirmou-se "não houve ato do tema X" sem exibir a lista de regex utilizada e o universo de atos varridos.
   * *Lição:* Proibido afirmar ausência de atos sem apresentar previamente a lista completa de termos pesquisados e a quantidade exata de atos inspecionados.
5. **Correções Valem na Origem:**
   * *Lição:* Qualquer correção realizada apenas no HTML gerado é revertida na próxima execução. A correção deve sempre residir nos scripts Python geradores.
6. **Desacoplamento e Segurança de Execução:**
   * O clipping na nuvem não toca no radar; o radar é gerado e publicado apenas pela tarefa local agendada às 08:00 BRT (`RadarInteligenciaRegulatoria`), evitando bloqueios de WAF do BNDES. Destinatários de teste ficam restritos a secrets criptografados (`EMAIL_TESTE`), sem expor endereços no console do GitHub Actions.

---

## 4. Pauta da Próxima Sessão (06/11/2026)

Executar strictly em ordem:
1. **Conferência das Rodadas Agendadas:**
   - Rodada das 07:17 BRT na nuvem (Clipping via GitHub Actions): checar logs e confirmar recebimento de e-mail até 08:00.
   - Rodada das 08:00 BRT local (Radar via Agendador de Tarefas do Windows): checar log e confirmar no site público o carimbo `Atualizado em 06/11 08:xx`.
2. **Decisões Editoriais com o Marcos:**
   - Definição do filtro dos Acórdãos da ANTAQ (critérios discriminantes: arrendamento, tarifa, reequilíbrio, EVTEA, seguro, garantia, e interessado MPOR ou autoridade portuária vs. bloco completo).
   - Definição da exibição dos atos do DOU no painel (aba "Atos do DOU" ou integração às abas temáticas).
3. **Construção da Aba "Atos do DOU" no Radar:**
   - Um card por ato individual relevante; REIDI e acórdãos agrupados por dia; todos com travas de link HTTP 200 e texto literal; validação prévia na trava de sanidade (`validador_publicacao.py`).
4. **Evoluções Seguintes:**
   - Integração do feed próprio do Poder360 ao Clipping (uma fonte por vez).
   - Monitor Legislativo (APIs da Câmara e do Senado) e pautas regulatórias da semana.

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

## 2. Fase 1: Coletor do Diário Oficial da União (`coletor_dou.py`) — Integrado e Auditado

Em 06/11/2026, a Fase 1 foi **concluída, refinada editorialmente e integrada diretamente ao pipeline de geração do Radar** (`gerar_radar.py` etapa 4.5), distribuindo os atos aprovados nas abas temáticas existentes sem necessidade de nova aba:

1. **Aba 2 (`#estruturacao`):**
   - Decreto nº 13.142/2026 (Qualificação PPI e inclusão no PND).
   - Acórdãos da ANTAQ aprovados estritamente pelo objeto literal (`"tratam de..."`): Acórdãos nº 650/2026 (modelagem MUC03 Fortaleza), 652/2026 (arrendamento RDJ10 Rio de Janeiro), 637/2026 (aditivo arrendamento Paranaguá), 633/2026 (reajuste tarifário São Sebastião) e 634/2026 (cronograma arrendamento BEL08 Belém).
   - Acórdãos nº 641/2026 (autorização especial de cais público) e 653/2026 (critérios de auditoria) foram **descartados** por não se enquadrarem no escopo estreito.
   - Card prioritário de contingência da Agenda EVTEA 2.0 / Portaria MInfra nº 530/2019 (Acórdão nº 640/2026-ANTAQ).

2. **Aba 4 (`#sfn`):**
   - Resolução CMN nº 5.344/2026 (Conselho Monetário Nacional).
   - Portaria GM nº 60/2026 (Conselho Diretor do Fundo da Marinha Mercante - CDFMM).
   - Despacho MF de 28/10/2026 (Fundos Garantidores — Novação FCVS com FGC).
   - Portarias MCID nº 1.483 e 1.484/2026 (Enquadramento prioritário para debêntures incentivadas — sem CNPJ).
   - **Painel Agregado REIDI:** Card institucional com contagem consolidada de habilitações da Receita Federal. Base analítica completa local em `dados_reidi/`.
   - **Textos de Autoria Eliminados:** Os cards de atos do DOU exibem estritamente a ementa ou objeto literal da fonte oficial, sem resumos sintéticos ou parágrafos autorais.

3. **Travas e Conformidade Editorial:**
   - Extração da Unidade Técnica oficial diretamente do texto do ato (`Unidades Técnicas:`).
   - Validação prévia de HTTP 200 obrigatória em todos os links canônicos (`in.gov.br/web/dou/-/`).
   - Trava contra vazamento de CNPJ (14 dígitos contínuos e formatados) validada por `testar_trava_cnpj.py` (5/5 aprovados).
   - Trava editorial `validador_publicacao.py` aprovada com dicionário expandido para verbos lexicais regulares (`compor`, `comporem`).
   - Mapa de Fontes mantido centralizadamente na planilha oficial `2026-11-05_Mapa_de_Fontes_Clipping_e_Radar.xlsx`.

---

## 3. Fontes Estaduais (SPI-SP e ARTESP) — Diagnóstico

Em 06/11/2026, foi realizada a verificação técnica nos portais estaduais de São Paulo:
* **SPI-SP e ARTESP:** firewall Imperva bloqueia acesso automatizado; consulta manual pelo navegador; sem amostra verificada.
* **Regra Operacional:** Bloqueada qualquer tentativa de raspagem contra o firewall. Novas fontes exigem trecho literal da própria página com o endereço exato; em caso de bloqueio, reportar "não consegui ler", sem preenchimento sintético.

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

## 4. Sessão de 06/11/2026 — Registro de Decisões e Consolidação Editorial

1. **Alerta de Falha e Envio em Feriados (Clipping):**
   * Aprovado o workflow de alerta preventivo das 09:33 BRT (`.github/workflows/alerta_falha_clipping.yml`) que avisa sobre retenção do clipping e informa nova tentativa às 10:18 BRT.
   * O clipping diário continua rodando em feriados nacionais que ocorram em dias de semana, sem calendário de supressão.

2. **Filtro da ANTAQ Ampliado (`filtro_acordaos_antaq.json`):**
   * Aprovada a inclusão de regras para `contrato_transicao` (Acórdão 654), `direito_real_uso` (Acórdão 646) e `revisao_normativa` (Acórdão 644).
   * Mantidos excluídos: Acórdão 643 (terminal privado / TPN Maricá) e Acórdão 639 (passagem de dutos / Cattalini).
   * O rótulo da Unidade Técnica deve vir exclusivamente do campo "Unidade Técnica" extraído do próprio texto do ato. Total de 9 atos aprovados na aba `#estruturacao`.

3. **Diretriz de Fontes Subnacionais (SPI-SP e ARTESP):**
   * Bloqueada qualquer raspagem automatizada contra o firewall Imperva. Acompanhamento exclusivamente manual via navegador.
   * Amostra anterior sintética/não verificada foi 100% eliminada de arquivos, memórias e da planilha central.
   * **Regra permanente para novas fontes:** só entra o que tiver trecho literal comprovado na própria página com endereço exato. Se a página não puder ser lida, registrar expressamente "não consegui ler", sem preenchimento dedutivo.

4. **Consultas Públicas de Ministérios na Aba `#participativo`:**
   * Inclusão e publicação aprovada das **Portarias nº 940/2026 e nº 950/2026** do Ministério dos Transportes (prorrogação do PSTF e PSTR até 15/11/2026).
   * Padrão aprovado: título literal, transcrição ipsis litteris dos artigos do ato, órgão extraído do texto (`MT / SNTF` e `MT / SNTR`), links oficiais com HTTP 200 e confirmação de presença do número no texto aberto.
   * Removido o bloco "Ponto de Atenção & Oportunidade de Incidência" e removida menção a "Janela de Contribuição: 03/11 a 15/11" (03/11 é publicação da prorrogação; início de janela só aparece se o ato trouxer a data expressa; exibido `Prazo de Contribuição: Prorrogada até 15/11/2026`).

5. **Diretriz de Card Único por Plano Setorial (Aprovada com Ajustes):**
   * O mesmo plano setorial (PSTR, PSTF, PSPort) não deve gerar card duplo (um do Brasil Participativo e outro avulso do DOU).
   * **Critério de Casamento:** Exclusivamente por citação cruzada no texto do ato oficial (950→895, 940→893, 509→463). Coincidência por sigla (`PSTR`, `PSTF`, `PSPort`) serve apenas como critério de reserva e deve ser explicitamente sinalizada.
   * **Tratamento de Divergência de Prazos:** Se a data final informada no portal divergir da publicada no Diário Oficial, o card deve exibir as duas datas, destacando visualmente a divergência.
   * **Data de Publicação:** A data de publicação da consulta deve vir do portal original (abertura), e não do ato de prorrogação.
   * **Aplicação:** A unificação dos cards será aplicada somente após validação editorial, aprovação da trava de CNPJ e comunicação do commit e carimbo ao Marcos.

6. **Modo Sombra de Consultas de Ministérios (09/11 a 13/11/2026):**
   * O coletor roda em modo sombra nos dias úteis, gerando apenas uma lista de candidatos por dia com: Órgão, Tipo, Número, Objeto literal do Art. 1º, Frase literal do prazo e Link HTTP 200.
   * Nenhuma publicação automática no painel sem aprovação prévia.
   * "Prorroga/prorrogação" só é capturada se o texto também contiver expressamente "consulta pública", "audiência pública" ou "contribuições" (rejeitando atos administrativos de vigência interna como COFIEX 184, RFB 742 e CVM 246).
   * "Despacho" só entra se trouxer expressamente "consulta pública" ou "audiência pública".
   * Padrão B sem data derivada: prazos de N dias exibem a oração literal sem cálculo de data final.
   * Padrão A com proximidade textual: data explícita só é válida se estiver na mesma frase de consulta/contribuições; caso contrário, registra "Ver ato".
   * A Portaria SNP nº 509/2026 sai do modo sombra apenas junto com a publicação do card único do PSPort 2050.

---

## 5. Roteiro a Partir de Segunda-Feira (09/11/2026)

1. **Abertura da Rodada de Segunda (09/11):**
   * Conferir execução do clipping da nuvem das 07:17 BRT e do despertador local das 07:50 BRT.
   * Confirmar que o e-mail saiu e que o alerta de falha das 09:33 BRT não disparou. Em caso de anomalia, relatar com evidências antes de intervir.
2. **Execução Diária do Modo Sombra (09/11 a 13/11):**
   * Executar a varredura das edições do DO1 e apresentar diariamente a lista estruturada de candidatos para conferência do Marcos.
3. **Pauta de Encerramento do Modo Sombra (13/11/2026):**
   * Decisão do Marcos sobre a automação contínua da coleta de consultas ministeriais.
   * Entrada no painel da Consulta Pública nº 740 (Portaria dos Níveis Operacionais de Hidrovias, prazo até 23/11/2026), via fonte oficial do Brasil Participativo.
   * Monitoramento contínuo dos Planos Setoriais Hidroviário (PSHN) e Aeroviário (PAN), que permanecem classificados como "não verificados" até que ato formal de consulta de minuta seja publicado.

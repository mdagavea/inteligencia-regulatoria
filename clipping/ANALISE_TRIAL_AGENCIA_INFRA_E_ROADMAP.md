# Análise do Free Trial da Agência iNFRA & Roadmap de Evolução do Clipping e Radar (DECON/MPOR)

> **Data do Diagnóstico:** 03/11/2026  
> **Escopo:** Avaliação técnica e editorial dos boletins exclusivos de assinantes da Agência iNFRA recebidos via Gmail, implementação da coleta estruturada via IMAP e plano de evolução do ecossistema `mdagavea/inteligencia-regulatoria`.

---

## 1. Diagnóstico Empírico: Boletim de Assinantes (Trial) vs. Site Oficial (`agenciainfra.com/blog/`)

Entre **28/10/2026** (data de ativação do *free trial*) e **03/11/2026**, foram inspecionados via IMAP todos os e-mails enviados por `infrajornalismo@agenciainfra.com` e `agenciainfra@agenciainfra.com`, cruzando-os com o feed RSS público e a API do WordPress do site oficial (`https://www.agenciainfra.com/blog/wp-json/wp/v2/posts`).

### 1.1. O que é entregue no Trial e em que horário
* **Três produtos enviados por e-mail:**
  1. **iNFRA Transportes / Saneamento & Cidades** (diário, dias úteis, chega entre **06h50 e 07h15 BRT**);
  2. **iNFRAEnergia** (diário, dias úteis, chega entre **07h00 e 07h20 BRT**);
  3. **Resumo da Semana** (domingos, chega às **~07h30 BRT**).
* **Sincronia perfeita com a nossa execução em nuvem:** Como o workflow [`.github/workflows/clipping_diario_nuvem.yml`](../.github/workflows/clipping_diario_nuvem.yml) roda às **07h30 BRT**, os dois boletins diários da Agência iNFRA já estão na caixa de entrada no momento da coleta.
* **Formato dos "Anexos" e Documentos Oficiais:**
  - Os boletins não utilizam anexos MIME tradicionais (evitando filtros de *spam*), mas embutem **dezenas de hiperlinks diretos para documentos primários**:
    * PDFs hospedados no próprio servidor da Agência (`https://agenciainfra.com/blog/wp-content/uploads/...`), como pautas de reuniões de diretoria, acórdãos do TCU e informativos setoriais;
    * Links diretos para peças processuais no **SEI** (ofícios, votos e despachos na ANEEL, ANTAQ, ANTT) e no sistema **Sophia/ANTAQ**;
    * Links diretos para atos normativos publicados no **Diário Oficial da União (`in.gov.br`)**.
  - **Descoberta técnica importante:** A versão web de cada boletim (`https://mailchi.mp/...`, presente na 1ª linha do e-mail) funciona sem o token de rastreamento pessoal (`?e=...`) e já traz **todos os links oficiais desembrulhados** (sem passar pelo redirecionador `us.list-manage.com`).

### 1.2. Diferenciais de Qualidade em relação ao Site Aberto
1. **Antecipação Temporal (Embargo de Horas a Dias) ou Exclusividade Total:**
   - **Exemplo 1 (4 dias de antecedência):** A reportagem *"Seca no Tapajós já reduz capacidade de barcaças para o transporte e governo admite uso de rodovias"* foi entregue no boletim de sexta-feira (**30/10 às 06h52 BRT**), mas só foi liberada no site público na terça-feira (**03/11 às 07h59 BRT**).
   - **Exemplo 2 (Exclusividade em temas financeiros/DECON):** Na edição de **03/11 (07h12 BRT)**, as duas reportagens principais — *"Temor sobre oneração de debêntures cresce enquanto transportes busca mais bolsos para financiamentos"* (entrevistas com George Santoro e Abdib sobre Lei 12.431 vs. Lei 14.801, EcoInvest e Fundo Clima) e *"Demanda por captações em concessões rodoviárias ultrapassa R$ 92 bi"* (levantamento ABCR) — permaneceram **100% exclusivas para assinantes**, sem publicação no site aberto ao longo de todo o dia.
   - **Exemplo 3 (Janela executiva matinal):** Reportagens sobre *Free Flow na ANTT* e *Concessão da Enel Rio / Cortes em PCHs* saíram às 06h52–07h04 no e-mail, mas só foram ao site entre **12h00 e 16h00**.
2. **Cinco Seções Estruturadas que NUNCA vão ao Feed RSS do Site:**
   - **`#Diario` (Diário Oficial):** Triagem diária exaustiva de Decretos (PPI/PND), Portarias (MPor, MT, MCID, MME), Acórdãos (ANTAQ), Resoluções e Despachos (ANTT, ANAC, ANEEL, ANP) e enquadramentos em REIDI / Debêntures Incentivadas.
   - **`#Agenda` e `#Semana` (Agenda de Autoridades, Agências e Controle Externo):** Antecipa a pauta da semana no **TCU**, **STF** (ex.: SecexConsenso), **Cade**, **Comissões da Câmara/Senado** e **Reuniões de Diretoria da ANTAQ, ANTT, ANAC, ANEEL e ANA**, com links para as pautas em PDF/Sophia.
   - **`#Monitor` (iNFRAMonitor Legislativo):** Movimentação de PLs e novas propostas protocoladas no Congresso.
   - **`#Fique` (Fique de Olho):** Notas curtas de bastidores e prorrogações de consultas públicas / tomadas de subsídios.
   - **`#Clipping`:** Curadoria diária de 15 a 30 matérias dos grandes jornais (*Valor, Estadão, Folha, O Globo, Poder360*).

---

## 2. Implementação Realizada em 03/11/2026 (`coletor.py` e `curador.py`)

Para corrigir o fato de que o coletor anterior (baseado apenas no feed Atom de não-lidos e limitado aos primeiros 280 caracteres do e-mail) perdia o conteúdo dos boletins:

1. **Leitura via IMAP SSL (porta 993) em modo `readonly` (`fetch_gmail_imap_newsletters` em [`coletor.py`](coletor.py)):**
   - Consulta a caixa `All Mail / Todos os e-mails` das últimas 48h (ou 96h às segundas-feiras), lendo tanto e-mails **não lidos** quanto **já abertos** pelo usuário, sem alterar o status de leitura no Gmail.
2. **Parser Especializado da Agência iNFRA (`_parse_boletim_agencia_infra` em [`coletor.py`](coletor.py)):**
   - Extrai o link público limpo do boletim (`https://mailchi.mp/...`, sem `?e=...`), baixa o HTML com links desembrulhados e desmembra cada edição em:
     * **Reportagens exclusivas de abertura (`#1`, `#2`, `#3`, `#4`)** com títulos formatados, resumo executivo de ~400 caracteres e classificação automática de vertical (`infra`, `divida`, `carbono`, `seguros`);
     * **Top Atos Estratégicos do DOU (`#Diario`), Pautas (`#Agenda`) e `#Fique`**, filtrados para o escopo da DECON/MPor e ignorando atos administrativos de rotina (como viagens e designações de pessoal), preservando o **link oficial direto (`in.gov.br`, `gov.br`, `sophia.antaq.gov.br`, `portal.antt.gov.br`, `santosdumont.anac.gov.br`)**.
3. **Fallback HTTPS Automático na Porta 443 (`_fetch_agencia_infra_mailchimp_fallback`):**
   - Caso o script seja rodado localmente na rede corporativa (onde a porta 993 IMAP é bloqueada), faz fallback transparente em 5 segundos para HTTPS (porta 443), garantindo o mesmo desmembramento do boletim.
4. **Expansão Segura da Allowlist de Domínios ([`curador.py`](curador.py)):**
   - Inclusão de `mailchi.mp`, `us14.campaign-archive.com` e domínios oficiais de Estado (`.gov.br`, `.leg.br`, `.jus.br`) em `_url_segura_permitida()`.

---

## 3. Dossiê de Monitoramento Prioritário: "Agenda EVTEA 2.0" (Acórdão ANTAQ nº 640/2026)

Identificado na seção `#Diario` do boletim de 03/11/2026, o **[Acórdão nº 640/2026-ANTAQ](https://www.in.gov.br/web/dou/-/acordao-n-640/2026-antaq-741192815)** (DOU de 03/11/2026, Seção 1) é um marco regulatório diretamente conectado às atribuições da **DECON/MPOR** e à **Aba 2 (Estruturação & EVTEAs)** do nosso Radar.

### Ficha Técnica Oficial (Verificada no DOU)
* **Ato:** Acórdão nº 640/2026-ANTAQ (Reunião Ordinária de Diretoria Colegiada nº 621, de 22/10/2026)
* **Processo SEI ANTAQ:** `50300.014412/2026-68`
* **Relator:** Diretor Alber Vasconcelos
* **Unidade Técnica Responsável:** Superintendência de Outorgas (SOG/ANTAQ)
* **Documentos-Base no SEI ANTAQ:** Pré-Projeto Regulatório EVTEA 2.0 (`SEI 2915139`) e Despacho SOG (`SEI 2915140`)

### Deliberações e Impactos Diretos para o MPor / DECON
1. **Instituição da Agenda EVTEA 2.0 (item 5.2):** Projeto institucional da ANTAQ voltado à modernização dos Estudos de Viabilidade Técnica, Econômica e Ambiental aplicados aos arrendamentos portuários, estruturado em **5 eixos e 5 fases** descritos no `SEI 2915139`.
2. **Articulação Direta com o MPor, TCU e CGU (item 5.3):** Autoriza a SOG/ANTAQ a promover discussões técnicas e institucionais diretamente com o **Ministério de Portos e Aeroportos (MPor)**, TCU, CGU, autoridades portuárias e setor privado, bem como a **constituir Grupo Técnico para o Catálogo de Dados de Referência** e **selecionar casos-piloto**.
3. **Interface com a Revisão da Portaria MInfra nº 530/2019 (item 5.4):** Determina à SOG que elabore contribuição institucional da ANTAQ à Consulta Pública aberta pelo MPor em 06/10/2026 (prorrogada até **13/11/2026**) para atualização da Portaria nº 530/2019 (alterações contratuais e reequilíbrio econômico-financeiro em arrendamentos portuários), alinhando-a ao EVTEA 2.0.
4. **Benefícios Fiscais e Acórdão nº 2.206/2026-TCU-Plenário (item 5.5):** Determina que a construção do Catálogo de Dados de Referência e a revisão do Manual de Análise de EVTEA observem o **Acórdão nº 2.206/2026-TCU-Plenário**, em especial quanto ao **tratamento dos benefícios fiscais** (ponto focal da DECON em debêntures incentivadas/REIDI) e à **compatibilidade entre investimentos (CAPEX) e capacidade**.
5. **Cronograma de 90 Dias (item 5.6):** A SOG tem **90 dias** para submeter à Diretoria Colegiada o **Plano de Trabalho Consolidado** (com cronograma, produtos, grupos técnicos, casos-piloto e instrumentos de implementação).

---

## 4. Roadmap de Aperfeiçoamento: O Que Hoje Não Fazemos e Como Implementar com Alto Valor

A análise do boletim da Agência iNFRA revelou **4 lacunas de alto valor executivo** que hoje não temos de forma estruturada e independente no nosso ecossistema (`clipping` + `radar_participativo`):

### 4.1. Automação Própria do Diário Oficial da União (DOU) — Como Superar a Complexidade
* **Por que é crítico:** O DOU é a fonte primária onde nascem:
  1. Portarias de aprovação de projetos prioritários para emissão de **Debêntures Incentivadas (Lei 12.431) e Debêntures de Infraestrutura (Lei 14.801)** e enquadramento no **REIDI**;
  2. **Acórdãos da ANTAQ** e Deliberações da **ANTT/ANAC** (EVTEAs, reequilíbrios, consultas públicas, revisões tarifárias);
  3. **Decretos do PPI/PND** qualificando empreendimentos para concessão;
  4. **Portarias do MPor e do Ministério dos Transportes** (FMM, planos setoriais, grupos de trabalho).
* **Por que parece complexo e como simplificar tecnicamente:**
  - Raspar o DOU por busca livre é instável porque o portal usa renderização dinâmica (Liferay). Porém, a página oficial de leitura diária (`https://www.in.gov.br/leiturajornal?secao=do1` e `do3`) embute no próprio HTML uma tag `<script id="params" type="application/json">` contendo o **índice JSON completo de todos os atos publicados no dia**, já classificados por `artType` (Portaria, Acórdão, Decreto, Aviso) e `hierarchyStr` (`Ministério de Portos e Aeroportos`, `Ministério dos Transportes`, `Agência Nacional de Transportes Aquaviários`, `Agência Nacional de Aviação Civil`, `Agência Nacional de Transportes Terrestres`, `Presidência da República`).
  - **Arquitetura proposta (`coletor_dou.py`):**
    1. Faz 2 requisições HTTP simples às 07h25 BRT (`secao=do1` e `secao=do3`);
    2. Filtra no JSON nativo apenas os órgãos do nosso perímetro (`MPor`, `MT`, `ANTAQ`, `ANAC`, `ANTT`, `PPI/Casa Civil`, `MF`, `MME/ANEEL/ANP` quando tratar de REIDI/debêntures/SAF);
    3. Descarta automaticamente a Seção 2 (atos de pessoal/nomeações/viagens);
    4. Baixa apenas a `<div class="texto-dou">` dos ~10 a 15 atos relevantes do dia, extraindo ementa, nº do processo SEI e link oficial (`https://www.in.gov.br/web/dou/-/...`).

### 4.2. Radar da Semana (Ex-Ante): Pautas de Órgãos de Controle (TCU/STF) e Diretorias (ANTAQ/ANTT/ANAC)
* **O que fazemos hoje vs. Oportunidade:** Hoje nosso Radar monitora decisões *após* sua publicação (ex-post). O boletim mostra o poder de monitorar a **pauta da semana antes da sessão (ex-ante)** — sabendo na segunda/terça-feira o que o Plenário do TCU julgará na quarta-feira às 14h30 e o que as Diretorias da ANTAQ, ANTT e ANAC votarão na semana.
* **Como implementar:**
  - **TCU (`portal.tcu.gov.br/sessoes`):** Coletar às terças e quartas-feiras a pauta da Sessão Plenária Ordinária e Extraordinária, filtrando processos cuja unidade jurisdicionada seja MPor, MT, ANTAQ, ANAC, ANTT, DNIT ou Infra S.A.
  - **ANTAQ (`sophia.antaq.gov.br`), ANTT (`portal.antt.gov.br`) e ANAC (`santosdumont.anac.gov.br`):** Coletar os links das pautas das reuniões deliberativas da semana e destacá-los em uma faixa **"📅 Pautas Deliberativas & Controle da Semana"** no topo do Clipping ou em sub-aba do Radar.

### 4.3. Monitor Legislativo Setorial Automatizado (APIs Oficiais da Câmara e do Senado)
* **Viabilidade Técnica (Alta / Baixa Complexidade):** Ao contrário de portais que bloqueiam robôs, a **Câmara dos Deputados** (`https://dadosabertos.camara.leg.br/api/v2/`) e o **Senado Federal** (`https://legis.senado.leg.br/dadosabertos/`) oferecem APIs REST JSON públicas, gratuitas e extremamente estáveis.
* **O que podemos monitorar automaticamente:**
  1. **Watchlist de Proposições Estratégicas para a DECON:**
     - **PLP 73/2025** (Governança e autonomia das Agências Reguladoras);
     - Projetos e MPs sobre **tributação de debêntures incentivadas / LCI / LCA / IOF / IR** e regulamentação da **Reforma Tributária (CBS/IBS)** em contratos de concessão;
     - Projetos sobre **Seguro Garantia / Performance Bond**, **Marco Legal de Concessões e PPPs**, **SAF / ProBioQAV** e **Mercado de Carbono (SBCE)**.
  2. **Pauta das Comissões Setoriais:** Eventos e votações do dia na **CVT** (Viação e Transportes), **CFT** (Finanças e Tributação) e **CI** (Comissão de Infraestrutura do Senado).

### 4.4. Rastreador Contínuo da "Agenda EVTEA 2.0" e Portaria MPor nº 530/2019 (Aba 2 do Radar)
* **Oportunidade imediata:** Criar um acompanhamento dedicado do **Processo ANTAQ `50300.014412/2026-68` (Agenda EVTEA 2.0)** e da revisão da **Portaria MInfra nº 530/2019**:
  - Monitorar a entrega da contribuição institucional da ANTAQ até **13/11/2026** (item 5.4 do Acórdão 640/2026);
  - Monitorar a constituição do **Grupo Técnico do Catálogo de Dados de Referência** e a definição dos **casos-piloto** com participação do MPor (item 5.3);
  - Monitorar a entrega do **Plano de Trabalho Consolidado em 90 dias** (item 5.6, previsto para ~20/01/2027) e o tratamento de benefícios fiscais segundo o **Acórdão nº 2.206/2026-TCU-Plenário** (item 5.5).

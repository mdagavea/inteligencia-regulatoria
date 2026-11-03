# Passagem: Aba "SFN, Seguros & Capitais" + complemento das agências (para o Gemini)

> **Data:** 29/10/2026. **Origem:** sessão do Gemini de 28/10 (`brain\69d4da95-...`) interrompida por falta de créditos, mais os testes feitos pelo Claude em 29/10 a partir desta máquina.
> **Antes de escrever qualquer código, leia também:** `MEMORIA_PROJETO.md` e `2026-10-28_Ajustes_Aba_Estruturacao_para_Gemini.md`. A regra "factual e verificável" vale para a aba nova.

---

## 0. Objetivo

1. **Etapa 1 (agora):** criar a **aba 4 "SFN, Seguros & Capitais"** (`#sfn`) com os processos participativos de **CVM, BCB, SUSEP, PREVIC, SRE/MF e ANBIMA** que correm **fora** do Brasil Participativo. A decisão de 28/10 foi ser a aba 4, para preservar o ciclo 1-2-3 (Consultas → Estruturação → Leilões) e o *deep-linking* atual.
2. **Etapa 2 (depois):** complementar a **aba 1** com consultas de **ANTT, ANTAQ, ANA, ANEEL e ANP** feitas em portais próprios, deduplicando com o Brasil Participativo (ver seção 4).

**Racional da aba separada:** essas entidades lançam muitas consultas, e a maioria não tem relação com o nosso trabalho. Por isso **só entra o que passar no filtro temático** (seção 3), e não a lista inteira.

---

## 1. Correção prévia obrigatória (robustez)

Hoje, `curador_participativo.chamar_gemini_lote()` lança `RuntimeError` quando todos os modelos falham. Isso **interrompe a rodada inteira**, e o painel do dia não é gerado nem publicado.

**Ajuste pedido:**
- Se a API falhar, **não interromper a rodada.** Registrar um aviso no console, não gravar cache para os pendentes (para que sejam tentados de novo na próxima rodada) e exibi-los com o selo "⚠️ Não analisado (IA indisponível)", usando título, órgão, datas e links da própria fonte.
- O mesmo vale para a aba nova: a coleta e o filtro por palavra-chave **não podem depender da IA**. A IA entra só para escrever o resumo, como reforço opcional.
- Em `gerar_radar.py`, a ausência de `GEMINI_API_KEY` também não deve abortar com `sys.exit(1)`. O radar deve rodar sem IA.

---

## 2. Fontes da aba SFN: o que está confirmado e o que falta

Testes feitos em 29/10/2026 nesta máquina, com Python 3.12 e o contexto SSL do projeto (`criar_contexto_ssl()`):

| Entidade | Fonte | Situação | Observações |
|---|---|---|---|
| **SUSEP** | `https://www2.susep.gov.br/safe/SCP/gateway/SugestaoConsultaAndamento/{pagina}/true` (página começa em **1**; 0 dá HTTP 500) | ✅ **JSON público** | 35 registros em 2 páginas de 20. Campos: `numero`, `ano`, `linkEdital` (é a **ementa**), `enderecoEdital` (link do DOU), `dataInicio`/`dataFim` no formato **MM/DD/AAAA HH:MM** (atenção: mês primeiro), `keyObjectAnexoMinuta`/`ExposicaoMotivos`/`QuadroComparativo`. Temas: `.../gateway/tema`. Página de envio para o usuário: `https://www2.susep.gov.br/safe/SCP/app/consultas-publicas` |
| **SUSEP (audiências)** | `https://www.gov.br/susep/pt-br/documentos-e-publicacoes/normativos/consultas-e-audiencias-publicas/normas-em-audiencia-publica` | ✅ HTML (tabela) | Poucas por ano |
| **CVM** | RSS `https://conteudo.cvm.gov.br/feed/audiencias.xml` **ou** a tabela em `https://conteudo.cvm.gov.br/audiencias_publicas/index.html` | ✅ RSS/HTML | A tabela traz Edital, Tema, **Prazo** e **Fase** ("Aberta para manifestações"). Hoje: SNC 01/26 (até 04/12) e SNC 02/26 (até 03/11). Os links do RSS vêm como `http://www.cvm.gov.br/...`; normalizar para `https://conteudo.cvm.gov.br/...` |
| **BCB** | Página `https://www.bcb.gov.br/estabilidadefinanceira/consultaspublicas` (montada por JavaScript) | ❌ **Não resolvido** | `.../api/servico/sitebcb/audpub/editaisativos` e `editaisencerrados` dão **HTTP 400** (tanto para o Gemini em 28/10 quanto para o Claude em 29/10). `.../api/paginasite/sitebcb/estabilidadefinanceira/consultaspublicas` devolve só `<bcb-pagina-tipo0>`. O BCB também publica parte dos editais no Participa + Brasil, que não respondeu (timeout). **Sugestões:** (a) procurar no chunk `pagina-tipo0.component-*.js` e nos seus *imports* a chamada real de lista; (b) usar o DOU como rede de segurança (seção 2.1) |
| **PREVIC** | `https://sisconp.previc.gov.br/` | ❌ HTTP 400 | A página gov.br da PREVIC lista as **encerradas** (`.../audiencias-e-consultas-publicas/encerradas`). Pode usar o Brasil Participativo/Participa + Brasil. Investigar ou cobrir pelo DOU |
| **ANBIMA** | `https://www.anbima.com.br/pt_br/autorregular/audiencias-publicas.htm` | ❌ Lista carregada por JS (portal Lumis) | As chamadas `ServiceInterfaceInstanceControllerHtml.jsp?...lumII=...` devolvem corpo vazio. **Alternativa:** as **circulares** da ANBIMA anunciam cada audiência (ex.: Circular 2026-000010 e 2026-000017). Verificar se a lista de circulares é estática ou tem RSS. A ANBIMA **não é órgão público**: o selo deve deixar claro que é autorregulação |
| **SRE/MF** | Aparentemente usa o próprio Brasil Participativo | ⚠️ Confirmar | O radar já capta 2 itens "MF / Subsecretaria de Desenvolvimento Econômico Sustentável". Confirmar se a SRE tem outra página. Se não tiver, **não duplicar** na aba 4: só sinalizar |
| **SUSEP no Brasil Participativo** | `brasilparticipativo.presidencia.gov.br/processes/susep-planoderegulacao2027` | ℹ️ Já existe na aba 1 | Deduplicar, para não aparecer nas duas abas |

### 2.1 Rede de segurança sugerida: DOU

BCB, SUSEP, CVM e PREVIC publicam no **DOU** os editais de consulta pública. Uma busca diária no DOU por "edital de consulta pública" / "consulta pública" filtrada por órgão cobriria o BCB e a PREVIC enquanto as páginas próprias não forem resolvidas, e também capturaria o que escapar. **Ainda não testado nesta máquina:** testar primeiro se a busca do `in.gov.br` responde daqui. Se não responder, não insistir.

**Regra:** só ligar no painel a fonte que funcionar de forma confiável. Fonte quebrada fica fora, com um aviso no console, e não vira card com informação inventada.

---

## 3. Filtro temático (sem IA)

Aplicar palavras-chave **na ementa/título + descrição**, por vertical. Lista inicial a refinar com o Marcos:

- **seguros:** seguro-garantia, performance bond, garantia de execução, grandes riscos, riscos de engenharia, resseguro, retrocessão, responsabilidade civil, seguro de danos, riscos nomeados, catástrofe, alagamento, inundação, SRO/registro de apólices, provisões técnicas, capital de risco, sustentabilidade em seguros.
- **divida:** debêntures (incentivadas/de infraestrutura), Lei 12.431, Lei 14.801, valores mobiliários de infraestrutura, FIDC/FIP-IE/FI-Infra, securitização, ofertas públicas, crédito, garantias, *green bonds*/títulos sustentáveis, project finance.
- **carbono:** risco climático, risco social/ambiental/climático (GRSAC/PRSAC), taxonomia, SBCE, carbono, ESG/ASG, divulgação de sustentabilidade (ISSB/CBPS).
- **infra:** infraestrutura, concessão, PPP, porto, aeroporto, hidrovia, rodovia, ferrovia, transporte.

**Excluir** quando o tema for claramente alheio, como capitalização, previdência de pessoas sem vínculo com infraestrutura, contabilidade de fundos sem relação com infraestrutura, *open insurance*/*open finance*, PLD/FT, cooperativas de crédito, câmbio e pagamentos. **Não excluir em silêncio:** manter um contador "X processos ativos fora do filtro" com link para a fonte, para o Marcos conferir de vez em quando se o filtro está deixando passar algo.

---

## 4. Etapa 2: complemento das agências (ANTT, ANTAQ, ANA, ANEEL, ANP)

Destino: **aba 1**, como complemento do Brasil Participativo, com **deduplicação** (mesmo processo nas duas fontes vira **um** card, com os dois links). A aba 1 segue com a mesma curadoria por vertical.

| Agência | Fonte | Situação |
|---|---|---|
| **ANTT** | API `https://participantt.antt.gov.br/api/ManterEvento?Situacao=2&PageSize=50&PageNumber=1` | ✅ JSON confirmado (pelo Gemini em 28/10 e pelo Claude em 29/10). Ex.: Tomada de Subsídios 6/2026 (outorgas ferroviárias por autorização, até 19/11/2026) |
| **ANTAQ** | `https://www.gov.br/antaq/pt-br/acesso-a-informacao/participacao-social/audiencias-e-consultas-publicas/audiencias-publicas-em-andamento` | ✅ HTML (gov.br) respondeu em 28/10. Em andamento: AP 06/2026 (SAIP Sul), 07/2026 (ITJ01), 08/2026 |
| **ANA** | não mapeada | A fazer |
| **ANEEL** | não mapeada | A fazer (a ANEEL costuma ter sistema próprio de participação) |
| **ANP** | `https://www.gov.br/anp/pt-br/assuntos/consultas-e-audiencias-publicas/consulta-audiencia-publica/2026/` | A testar (aparece em buscas com CP/AP numeradas de 2026) |
| **ANAC** | `.../anac/pt-br/acesso-a-informacao/participacao-social/consultas-publicas` | Em 28/10, uma das URLs testadas deu 404. A ANAC usa muito o Brasil Participativo: conferir antes de criar coletor |

**Também vale olhar (fora do SFN, mas com interface):** a AGU/Sejan abriu a **Tomada de Subsídios nº 2/2026**, sobre o impacto da reforma tributária nos contratos de concessão. O prazo aparenta ser **30/10/2026** (aviso em `gov.br/agu/pt-br/assuntos-1/sejan/AvisoPblicoTomadadeSubsdios22026.pdf`). Isso mostra que há órgãos fora da lista que publicam por fora; considerar um campo "outras fontes" no futuro.

---

## 5. Formato do card na aba 4

Mesmo espírito factual da aba 2:

```
Entidade:            SUSEP | CVM | BCB | PREVIC | SRE/MF | ANBIMA (autorregulação)
Modalidade e nº:     Consulta Pública nº 15/2026 (como consta na fonte)
Ementa/objeto:       texto da fonte (sem reescrever)
Prazo:               dd/mm/aaaa (+ contador regressivo, como na aba 1)
Vertical:            seguros | divida | carbono | infra  (palavra-chave que casou: "provisões técnicas")
Links:               edital no DOU, minuta, exposição de motivos, página de envio
Resumo da IA:        opcional; se a IA não rodou, omitir (não preencher com texto genérico)
```

Proibido, como na aba 2: opinião, "ótica DECON", "recomenda-se", relevância sem trecho da fonte.

---

## 6. Ordem sugerida de execução

1. Correção de robustez (seção 1). Testar rodando com `GEMINI_API_KEY` vazia: o painel precisa sair.
2. Coletores SUSEP + CVM + filtro (seções 2 e 3) e a aba 4 no renderizador.
3. BCB, PREVIC e ANBIMA: tentar resolver ou cobrir pelo DOU. Só publicar o que funcionar.
4. Etapa 2 (seção 4).
5. Atualizar `MEMORIA_PROJETO.md` **ao fim de cada etapa**, e não só no final. A sessão de 28/10 se perdeu justamente porque a memória não foi atualizada antes de os créditos acabarem.

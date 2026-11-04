# Regras Oficiais da Aba 3: "Radar de Leilões & Outorgas" (`#leiloes`)

> **Referência Oficial do Repositório Público**  
> Este documento consolida as regras de acompanhamento pré-leilão no Tribunal de Contas da União (TCU), critérios de evidência de vínculo e protocolo de resiliência da Aba 3 do Radar.

---

## 1. Acompanhamento do TCU Antes do Leilão (Portos, Aeroportos e Hidrovias)

Para os projetos de **portos, aeroportos e hidrovias** da carteira de Leilões & Outorgas:

1. **Campo Obrigatório `"Etapa TCU"` em cada card:**
   * `não localizado`
   * `em análise (nº do processo TC)`
   * `acórdão proferido (nº, data e link)`
   * `determinações/recomendações a cumprir`
   * `não consultado hoje` *(utilizado como fallback temporário quando não houver valor anterior válido e a consulta ao TCU falhar no dia)*

2. **Regra Estrita de Evidência de Vínculo:**
   * O vínculo entre o projeto e o processo do TCU **só pode ser estabelecido com evidência oficial**:
     * número do processo TC citado na página oficial do projeto (ANTAQ, ANAC, MPOR, PPI);
     * citação expressa no edital ou nos documentos da audiência/leilão; ou
     * identificação inequívoca do código do ativo/projeto no próprio acórdão ou peça oficial do TCU.
   * **Se não houver vínculo comprovado documentalmente**, o campo deve exibir obrigatoriamente **`"não localizado"`** (proibido presumir ou inferir vínculo por semelhança genérica de termos).

3. **Integração com a Aba 2 (`#estruturacao`):**
   * Cada processo de acompanhamento de desestatização (**IN-TCU nº 81/2018**) ou de solução consensual (**SecexConsenso, IN-TCU nº 91/2022**) de portos, aeroportos e hidrovias gera também um card específico do **tipo (e) — Controle Externo (TCU)** na Aba 2 (*Estruturação, EVTEAs & Contratações*), conforme [`REGRAS_ABA_ESTRUTURACAO.md`](REGRAS_ABA_ESTRUTURACAO.md).

4. **Otimização da Rodada Diária (Economia de Requisições):**
   * Na execução diária do radar, a consulta à API/pesquisa do TCU é realizada **apenas para os projetos da carteira que ainda não possuem acórdão proferido**.
   * Projetos que já possuem acórdão registrado no cache (`historico_processos.json`) **não são consultados novamente**, salvo para monitoramento de eventuais embargos ou recursos.

5. **Resiliência Operacional (Tolerância a Falhas / WAF):**
   * A consulta à base do TCU (`https://pesquisa.apps.tcu.gov.br/`) deve utilizar cabeçalhos completos de navegador (`User-Agent`, `Accept`, `Referer`).
   * Caso a consulta ao TCU falhe (bloqueio de WAF, timeout ou indisponibilidade do portal), a geração do painel **segue normalmente**:
     * se já houver último valor válido no cache, mantém-se o último valor válido;
     * se ainda não houver valor em cache, o campo exibe `"não consultado hoje"`.
   * **Nenhuma falha de conexão com o TCU (ou com FDIRS/FEP) pode interromper ou derrubar a geração do painel.**

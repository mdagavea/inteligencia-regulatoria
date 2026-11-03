# Guia Rápido: Radar Brasil Participativo (Gestão & Dossiês Normativos)

Este sistema monitora diariamente todas as **Consultas Públicas, Audiências Públicas, Tomadas de Subsídios, Consultas Setoriais, Planos Participativos e Minutas em Pré-Publicação** lançadas no portal [Brasil Participativo](https://brasilparticipativo.presidencia.gov.br/) que têm relação com as nossas 4 verticais de atuação:

1. **Infraestrutura, Transportes & Outorgas** (Rodovias, ferrovias, portos, aeroportos, hidrovias, ANTT, ANAC, ANTAQ, DNIT, MT, MPOR, concessões e PPPs).
2. **Seguros, Garantias & Grandes Riscos** (Diretrizes de seguros em concessões/arrendamentos, performance bonds, SUSEP).
3. **Clima, Carbono & Infraestrutura Sustentável** (Certificação de infra sustentável, Taxonomia Sustentável Brasileira - TSB, SBCE, licenciamento).
4. **Financiamento, Fomento & Mercado de Capitais** (Crédito oficial, compliance, garantias, BNDES, CVM, debêntures).

---

## Links Públicos na Web (Para enviar no WhatsApp da Equipe)

Sempre que você executa os scripts, eles atualizam automaticamente na internet os seguintes endereços (abrem com 1 clique no celular ou PC):

* 🌐 **Hub Central:** [https://mdagavea.github.io/inteligencia-regulatoria/](https://mdagavea.github.io/inteligencia-regulatoria/)
* 📰 **Clipping Diário Regulatório & Financeiro:** [https://mdagavea.github.io/inteligencia-regulatoria/clipping.html](https://mdagavea.github.io/inteligencia-regulatoria/clipping.html)
* 🏛️ **Radar Brasil Participativo (Gestão & Dossiês):** [https://mdagavea.github.io/inteligencia-regulatoria/radar.html](https://mdagavea.github.io/inteligencia-regulatoria/radar.html)

---

## Como Executar o Painel Completo de Gestão & Dossiês

Dê dois cliques no arquivo:
👉 [executar_radar.bat](file:///C:/Users/marcos.castilho/testes-gemini/radar_participativo/executar_radar.bat)

O sistema irá:
1. Consultar a API GraphQL oficial do Brasil Participativo em tempo real;
2. Identificar processos recém-lançados (48h), prazos urgentes ($\le 7$ dias), processos abertos e minutas recém-cadastradas no **Radar de Pré-Publicação**;
3. Gerar dossiês normativos com o Gemini (usando cache inteligente em [historico_processos.json](file:///C:/Users/marcos.castilho/testes-gemini/radar_participativo/historico_processos.json) para responder em segundos nas execuções seguintes);
4. Abrir automaticamente o painel interativo [radar_atual.html](file:///C:/Users/marcos.castilho/testes-gemini/radar_participativo/radar_atual.html) no seu navegador.

---

## Integração Automática com o Clipping Diário

Sempre que você rodar o seu [executar_clipping.bat](file:///C:/Users/marcos.castilho/testes-gemini/clipping/executar_clipping.bat), o topo do [clipping_atual.html](file:///C:/Users/marcos.castilho/testes-gemini/clipping/clipping_atual.html) exibirá automaticamente uma **Faixa Informativa** contendo apenas os processos participativos efetivamente lançados no dia ou na véspera (últimas 48h), com um botão direto para abrir o painel completo do Radar.

# Histórico de Evoluções do Projeto: Radar DECON/MPor

> Este arquivo armazena o registro histórico das evoluções concluídas (separado do `MEMORIA_PROJETO.md` para manter a leitura de contexto enxuta).

---

## Concluído em 21/10/2026:
* [x] Concepção e implementação da Aba 1 (`coletor_participativo.py`, `curador_participativo.py`, `renderizador_participativo.py` e `publicador_web.py`) consultando a API GraphQL do Brasil Participativo.

## Concluído em 25/10/2026:
* [x] Modo de gestão contínua com ciclo de vida de 5 estágios (`LANCADO_48H`, `PRAZO_URGENTE`, `ABERTO`, `PRE_PUBLICACAO`, `ENCERRADO_RECENTE` até 72h) e contadores regressivos dinâmicos em JS.

## Concluído em 27/10/2026:
* [x] Higienização de títulos oficiais com erros de digitação do portal e expansão de botões de documentos (DOU, SEI, Minuta, Nota Técnica).

## Concluído em 28/10/2026:
* [x] **Expansão para Abas 2 (`#estruturacao`) e 3 (`#leiloes`)** via `coletor_estruturacao_leiloes.py`.
* [x] Consolidação do padrão 100% factual verificado nos PDFs oficiais na Aba 2 (Prioridade A: Portos/Aeroportos/Hidrovias; Prioridade B: Comparação Federal Rodovias/Ferrovias).

## Concluído em 03/11/2026:
* [x] **Implementação da Aba 4 (`#sfn` — SFN, Seguros & Capitais) em `coletor_sfn.py`**:
  - Integração da API JSON pública da **SUSEP (`SAFE/SCP`)** com download direto de Minutas, Exposições de Motivos e Quadros Comparativos (`AnexoAws/DownloadFile?bucketName=producao`), além de editais da **CVM** e painel de atalhos monitorados (BCB, PREVIC, SRE/MF e ANBIMA).
  - Filtro configurável externo em `termos_filtro.json` + gravação automática dos descartados em `log_descartados_filtro.txt` + gaveta transparente no rodapé da Aba 4.
  - Economia de chamadas à API Gemini (`enriquecer_sfn_com_ia_lote`): filtro regex antes da IA, cache por endereço+hash (`hash_cache_ia`), chamada única em lote apenas para itens novos enviando somente título e ementa curta.
* [x] **Complemento das Agências na Aba 1 (`ANTT` via API ParticipANTT e `ANTAQ` via Gov.br)** com deduplicação automática com o Brasil Participativo.
* [x] **Resiliência sem IA (`curador_participativo.py` e `gerar_radar.py`)**: falhas na API Gemini não interrompem a rodada nem gravam erro no cache.

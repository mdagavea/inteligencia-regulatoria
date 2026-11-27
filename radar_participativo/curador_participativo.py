import json
import os
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

# Versão do critério editorial das CPs (incrementar ao mudar regras de corte para reavaliar itens ativos)
VERSAO_CRITERIO_CP = "v3"
ARQUIVO_PARAMETROS_IA = Path(__file__).resolve().parent.parent / "parametros_ia.json"


def _carregar_parametros_ia():
    """
    Carrega modelos_candidatos e temperatura do arquivo único codigo/parametros_ia.json.
    Sem valor padrão oculto: se o arquivo faltar ou estiver inválido, registra erro visível e falha.
    """
    try:
        if not ARQUIVO_PARAMETROS_IA.exists():
            raise FileNotFoundError(f"Arquivo não encontrado: {ARQUIVO_PARAMETROS_IA}")
        dados = json.loads(ARQUIVO_PARAMETROS_IA.read_text(encoding="utf-8"))
        if not isinstance(dados, dict):
            raise ValueError("Conteúdo JSON não é um objeto")
        modelos = dados.get("modelos_candidatos")
        temperatura = dados.get("temperatura")
        if not isinstance(modelos, list) or not modelos or not all(isinstance(m, str) and m.strip() for m in modelos):
            raise ValueError("Campo 'modelos_candidatos' ausente ou inválido")
        if isinstance(temperatura, bool) or not isinstance(temperatura, (int, float)):
            raise ValueError("Campo 'temperatura' ausente ou inválido")
        return [m.strip() for m in modelos], float(temperatura)
    except Exception as e:
        msg = f"[ERRO] Falha ao carregar parâmetros da IA em {ARQUIVO_PARAMETROS_IA}: {e}"
        print(f"   {msg}")
        raise RuntimeError(msg) from e

PROMPT_CURADORIA_PARTICIPATIVA = """
Você é um Especialista Sênior em Regulação Econômica, Infraestrutura, Concessões/PPPs, Seguros de Grandes Riscos, Financiamento, Energia/Petróleo, Comércio Exterior e Transição Climática no Governo Federal.

Sua tarefa é avaliar uma lista de processos participativos (Consultas Públicas, Audiências Públicas, Tomadas de Subsídios, Planos Setoriais e Minutas em Pré-Publicação) e aprovar APENAS aqueles que possuem relação direta com nossas 4 verticais de atuação, respeitando rigorosamente os critérios de exclusão abaixo:

1. "infra" — Infraestrutura, Regulação Econômica, Transportes, Energia/Petróleo & Outorgas:
   - Regulação econômica, outorgas, concessões, PPPs, leilões, contratos de concessão/arrendamento, tarifas, acesso à infraestrutura, reequilíbrio econômico-financeiro, matriz de riscos, sandbox regulatório e planos setoriais (PNL, PSTF, PSTR, PSPort, PSHN, PAN) em transportes (portos, aeroportos, hidrovias, rodovias, ferrovias, logística, mobilidade), energia elétrica, petróleo, gás e combustíveis (MPor, MT, MME, ANTAQ, ANTT, ANAC, ANEEL, ANP, ANA/saneamento ligado a infra).
   - Concessões e PPPs: APROVAR APENAS quando tiverem relação com Infraestrutura (transportes, logística, energia, saneamento, telecomunicações).
2. "seguros" — Seguros, Garantias & Gestão de Riscos:
   - Políticas e diretrizes de seguros em infraestrutura/portos/aeroportos/transportes, seguro-garantia (performance bond), SUSEP, resseguro, sinistros, riscos de engenharia e matriz de seguros.
3. "carbono" — Transição Climática, Finanças Sustentáveis & Descarbonização:
   - Mercado de carbono e créditos de carbono (Sistema Brasileiro de Comércio de Emissões, Lei nº 15.042/2024), inclusive projetos de crédito de carbono e pagamento por serviços ambientais ligados a carbono em áreas públicas ou unidades de conservação; Taxonomia Sustentável Brasileira (TSB); finanças sustentáveis; Fundo Clima; políticas de mitigação e adaptação à mudança do clima; descarbonização de transportes, energia e indústria; transição energética; licenciamento ambiental ligado a infraestrutura. Nesta vertical, o critério é a pertinência climática do assunto, não a relação com infraestrutura.
4. "divida" — Financiamento, Fomento, Crédito, Mercado de Capitais & Comércio Exterior:
   - Debêntures incentivadas/infraestrutura, CVM, BNDES, fundos públicos/garantidores, mercado de capitais, apoio oficial ao crédito, garantias financeiras e comércio exterior (SECEX/MDIC/CAMEX, tarifas, defesa comercial, acordos comerciais).

REGRA GERAL DE IMPARCIALIDADE POR ÓRGÃO:
- O órgão proponente (ex.: ICMBio, MMA, IBAMA) nunca é, sozinho, motivo de inclusão ou exclusão; decide o assunto da consulta.

REGRAS ESTRITAS DE EXCLUSÃO (`"aprovar": false` — OBRIGATÓRIO):
- EXCLUA normas **técnico-operacionais** de engenharia, manutenção, pavimentação/drenagem rodoviária (ex.: normas DNIT EM/ES de tubo dreno, reciclagem de pavimento), aeronavegabilidade/operação técnica de aviação (ex.: Instruções Suplementares IS e emendas técnicas de RBAC da ANAC sem caráter de regulação econômica/acesso/outorga), metrologia/pesagem (INMETRO), homologação veicular/trânsito operacional (SENATRAN). MANTENHA apenas a parte de **regulação** (regulação econômica, tarifas, acesso à infraestrutura, contratos, outorgas, planos setoriais, governança regulatória).
- EXCLUA concessões e PPPs **sem relação com Infraestrutura** (ex.: apoio à visitação e uso público em parques e unidades de conservação, concessão florestal, concessão de imóveis/patrimônio como Complexo do Itamaraty, PPPs de hospitais/saúde como INCA e CIBS).
- EXCLUA temas puramente administrativos, dados abertos (PDA), conflito de interesses (CGU), contratações de TI/software, controle de produtos controlados pelo Exército (DFPC/COLOG), planos estaduais genéricos, saúde pública, assistência social, cultura (Rouanet), segurança alimentar, educação, pesca/aquicultura, fauna/espécies silvestres ou direitos humanos sem nexo com infraestrutura, regulação econômica ou a agenda climática.
- **Pré-publicação (rascunhos):** aprove APENAS se o título ou descrição trouxer indicativo claro de relação temática com os filtros acima; exclua rascunhos vazios, genéricos ou fora de escopo.

Para cada processo avaliado, retorne:
  * "id": ID exato do processo (string).
  * "aprovar": true ou false.
  * "motivo_rejeicao": (se aprovar=false) frase curta de até 12 palavras explicando o corte.
  * "vertical": (se aprovar=true) uma das chaves ["infra", "seguros", "carbono", "divida"].
  * "modalidade_exibicao": ex: "Consulta Pública", "Audiência Pública", "Tomada de Subsídios", "Consulta Setorial", "Minuta em Pré-Publicação".
  * "orgao_sigla": sigla e nome curto do órgão/secretaria responsável (ex: "Ministério de Portos e Aeroportos / DGH", "MT / SNTF", "ANAC / SSA", "ANTT", "ANTAQ", "MDIC / SECEX", "MME", "MF").
  * "relevancia": "ALTA" (impacto direto em transportes, portos, aeroportos, hidrovias, concessões de infra, seguros ou financiamento de infra) ou "MEDIA" (impacto transversal: energia/petróleo, clima/SBCE, comércio exterior).
  * "objeto_normativo": resumo técnico objetivo e 100% factual (2 frases) explicando qual ato normativo, plano, edital ou diretriz está sendo proposto ou alterado.
  * "pontos_atencao": frase curta e factual (1 frase) destacando o tema regulatório/econômico coberto, sem opinião ou prescrição ("recomenda-se", "deve contemplar").

Retorne ESTRITAMENTE um objeto JSON no formato:
{
  "avaliacoes": [
    {
      "id": "767",
      "aprovar": true,
      "motivo_rejeicao": "",
      "vertical": "infra",
      "modalidade_exibicao": "Consulta Pública",
      "orgao_sigla": "SNP",
      "relevancia": "ALTA",
      "objeto_normativo": "...",
      "pontos_atencao": "..."
    }
  ]
}
"""


def carregar_historico(caminho_json: Path) -> dict:
    if caminho_json.exists():
        try:
            with open(caminho_json, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"vistos_primeira_vez": {}, "analises_ia": {}}


def salvar_historico(caminho_json: Path, dados: dict):
    with open(caminho_json, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)


def chamar_gemini_lote(lote_processos: list, api_key: str) -> dict:
    """Envia um lote de processos novos/atualizados para o Gemini gerar os dossiês executivos."""
    if not lote_processos:
        return {}

    client = genai.Client(api_key=api_key)

    blocos_texto = []
    for p in lote_processos:
        docs_nomes = ", ".join(d["rotulo"] for d in p.get("documentos", [])[:5])
        blocos_texto.append(
            f"ID: {p['id']}\n"
            f"Status Publicação: {'PUBLICADO' if p['publicado'] else 'PRÉ-PUBLICAÇÃO (Rascunho na API)'}\n"
            f"Tipo Catálogo: {p['tipo_catalogo']}\n"
            f"Órgão Informado: {p['orgao_informado']}\n"
            f"Slug: {p['slug']}\n"
            f"Título: {p['titulo']}\n"
            f"Subtítulo: {p['subtitulo']}\n"
            f"Período: {p['data_inicio_br']} a {p['data_fim_br']}\n"
            f"Documentos Anexos: {docs_nomes}\n"
            f"Resumo: {p['descricao_texto'][:450]}\n"
            f"---"
        )

    prompt_completo = f"{PROMPT_CURADORIA_PARTICIPATIVA}\n\nPROCESSOS PARA AVALIAÇÃO:\n\n" + "\n".join(blocos_texto)

    modelos_candidatos, temperatura_ia = _carregar_parametros_ia()

    resposta_json = None
    ultimo_erro = None

    for modelo in modelos_candidatos:
        try:
            resp = client.models.generate_content(
                model=modelo,
                contents=prompt_completo,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=temperatura_ia,
                )
            )
            if resp and resp.text:
                resposta_json = json.loads(resp.text)
                break
        except Exception as e:
            ultimo_erro = e
            continue

    if not resposta_json:
        print(f"   [Aviso] Modelos Gemini indisponíveis em chamar_gemini_lote ({ultimo_erro}). Prosseguindo sem cache para tentar na próxima rodada.")
        return {}

    resultado_por_id = {}
    for item in resposta_json.get("avaliacoes", []):
        pid = str(item.get("id", ""))
        if pid:
            resultado_por_id[pid] = item
    return resultado_por_id


def _chave_cache(c: dict) -> str:
    """Gera chave de cache: fixa (versao_id) para publicados; com timestamp até minuto para rascunhos."""
    pid = c["id"]
    if c.get("publicado"):
        return f"{VERSAO_CRITERIO_CP}_{pid}"
    return f"{VERSAO_CRITERIO_CP}_{pid}_{c['data_atualizacao_iso'][:16]}"


def _extrair_id_chave_cache(chave: str) -> str:
    """Extrai o ID exato do processo de uma chave de cache (v2_857_..., v3_857 ou 857_2026-...)."""
    partes = chave.split("_")
    if not partes:
        return ""
    if len(partes) >= 2 and partes[0].startswith("v") and partes[0][1:].isdigit():
        return partes[1]
    return partes[0]


def _buscar_avaliacao_anterior(cache_ia: dict, pid: str):
    """Retorna (chave, avaliacao) mais recente do mesmo processo no cache (ordem de inserção), ou (None, None)."""
    pid_str = str(pid)
    chave_encontrada = None
    av_encontrada = None
    for k, v in cache_ia.items():
        if _extrair_id_chave_cache(k) == pid_str:
            chave_encontrada = k
            av_encontrada = v
    return chave_encontrada, av_encontrada


def curar_processos_participativos(candidatos: list, pasta_projeto: Path, api_key: str = None) -> list:
    """
    Combina controle de estado local (cache de análises já feitas) com curadoria via Gemini
    para novos processos ou processos atualizados. Se a IA falhar, mantém o radar funcionando.
    """
    key = api_key or os.getenv("GEMINI_API_KEY")
    if not key:
        print("   [Aviso] GEMINI_API_KEY ausente. Processos pendentes usarão avaliação anterior ou dados factuais da fonte (sem cache de IA).")

    caminho_hist = pasta_projeto / "historico_processos.json"
    historico = carregar_historico(caminho_hist)
    vistos = historico.setdefault("vistos_primeira_vez", {})
    cache_ia = historico.setdefault("analises_ia", {})

    hoje_str = datetime.now().strftime("%Y-%m-%d")

    # Filtra processos abertos, com prazo no ato, em pré-publicação ou encerrados nas últimas 72h (ENCERRADO_RECENTE)
    candidatos_ativos = [
        c for c in candidatos
        if c["status_ciclo"] in ("LANCADO_48H", "PRAZO_URGENTE", "ABERTO", "PRAZO_NO_ATO", "PRE_PUBLICACAO", "ENCERRADO_RECENTE")
    ]

    pendentes_ia = []
    for c in candidatos_ativos:
        pid = c["id"]
        # Chave fixa (versao_id) para publicados; com timestamp até minuto para reavaliar rascunhos editados
        chave_versao = _chave_cache(c)
        if pid not in vistos:
            vistos[pid] = hoje_str
        if chave_versao not in cache_ia:
            pendentes_ia.append(c)

    # Processa em lotes menores (10) para evitar truncamento de JSON na resposta do modelo
    TAMANHO_LOTE = 10
    if key and pendentes_ia:
        import time
        for i in range(0, len(pendentes_ia), TAMANHO_LOTE):
            lote = pendentes_ia[i:i + TAMANHO_LOTE]
            avaliacoes = chamar_gemini_lote(lote, api_key=key)
            if not avaliacoes:
                # Falha da API: não grava no cache para tentar novamente na próxima rodada
                continue
            for c in lote:
                pid = c["id"]
                chave_versao = _chave_cache(c)
                if pid in avaliacoes:
                    cache_ia[chave_versao] = avaliacoes[pid]
            if i + TAMANHO_LOTE < len(pendentes_ia):
                time.sleep(1)

    salvar_historico(caminho_hist, historico)

    # Monta a lista final de dossiês aprovados (ou pendentes quando IA indisponível)
    dossies_aprovados = []
    descartados_ia = []
    for c in candidatos_ativos:
        pid = c["id"]
        chave_versao = _chave_cache(c)
        av = cache_ia.get(chave_versao)
        if av is None:
            chave_ant, av_ant = _buscar_avaliacao_anterior(cache_ia, pid)
            if av_ant is not None:
                print(f"   [Aviso] reaproveitada avaliação anterior {chave_ant}")
                av = av_ant
        if av is None:
            # Processo ainda não analisado porque a IA estava indisponível: exibe com selo de aviso factual
            item_enriquecido = dict(c)
            item_enriquecido["vertical"] = "infra"
            item_enriquecido["modalidade_exibicao"] = f"⚠️ {c['tipo_catalogo']} (Não analisado — IA indisponível)"
            item_enriquecido["orgao_sigla"] = c["orgao_informado"] or "Governo Federal"
            item_enriquecido["relevancia"] = "MEDIA"
            item_enriquecido["objeto_normativo"] = c["descricao_texto"][:300] or c["titulo"]
            item_enriquecido["pontos_atencao"] = "⚠️ Curadoria automática por IA temporariamente indisponível nesta rodada. Consulte os documentos oficiais nos botões abaixo."
            item_enriquecido["primeira_deteccao"] = vistos.get(pid, hoje_str)
            dossies_aprovados.append(item_enriquecido)
            continue
        if not av.get("aprovar", False):
            descartados_ia.append({
                "origem": f"CURADORIA-IA ({VERSAO_CRITERIO_CP})",
                "id": pid,
                "orgao": c.get("orgao_informado", ""),
                "titulo": c.get("titulo", ""),
                "motivo": av.get("motivo_rejeicao") or "Fora do escopo editorial",
                "url": c.get("url", ""),
            })
            continue

        item_enriquecido = dict(c)
        item_enriquecido["vertical"] = av.get("vertical", "infra")
        item_enriquecido["modalidade_exibicao"] = av.get("modalidade_exibicao", c["tipo_catalogo"])
        item_enriquecido["orgao_sigla"] = av.get("orgao_sigla") or c["orgao_informado"] or "Governo Federal"
        item_enriquecido["relevancia"] = av.get("relevancia", "ALTA")
        item_enriquecido["objeto_normativo"] = av.get("objeto_normativo", c["descricao_texto"][:280])
        item_enriquecido["pontos_atencao"] = av.get("pontos_atencao", "")
        item_enriquecido["primeira_deteccao"] = vistos.get(pid, hoje_str)

        dossies_aprovados.append(item_enriquecido)

    if descartados_ia:
        try:
            import coletor_participativo
            coletor_participativo.registrar_descartados_participativo(descartados_ia, modo="a")
            print(f"   -> {len(descartados_ia)} processo(s) descartado(s) pela curadoria IA (log_descartados_participativo.txt).")
        except Exception:
            pass

    # Ordena: 1) Lançados 48h, 2) Prazo Urgente, 3) Abertos (por menor dias_restantes), 4) Prazo no Ato, 5) Pré-Publicação, 6) Encerrados Recentes
    ordem_status = {
        "LANCADO_48H": 1,
        "PRAZO_URGENTE": 2,
        "ABERTO": 3,
        "PRAZO_NO_ATO": 4,
        "PRE_PUBLICACAO": 5,
        "ENCERRADO_RECENTE": 6
    }
    ordem_rel = {"ALTA": 1, "MEDIA": 2}

    dossies_aprovados.sort(key=lambda x: (
        ordem_status.get(x["status_ciclo"], 9),
        ordem_rel.get(x["relevancia"], 2),
        x["dias_restantes"] if x["dias_restantes"] is not None else 999,
        -int(x["id"])
    ))

    return dossies_aprovados


PROMPT_CURADORIA_ESTRUTURACAO = """
Você é um analista documental técnico responsável por registrar, de forma 100% factual e verificável na fonte, o conteúdo de editais de EVTEA e estruturação de concessões em infraestrutura de transportes (Portos, Aeroportos, Hidrovias, Rodovias e Ferrovias).

REGRAS ESTRITAS DE TOM E ESTILO (OBRIGATÓRIAS):
1. Descreva APENAS o que consta nos dados e documentos oficiais do certame (Objeto, Valor/Prazo/Data, Situação, Documentos de Escopo e o que consta sobre seguros, garantias e matriz de riscos).
2. NÃO emita opinião, recomendação, juízo de valor ou prescrição sobre o que o estudo "deveria" fazer.
3. É TERMINANTEMENTE PROIBIDO usar expressões como: "deve contemplar", "recomenda-se", "é fundamental", "tende a", "dialoga com", "juízo de valor", "oportunidade para", "Lacuna identificada".
4. Diferencie sempre a matriz de riscos do contrato de consultoria (entre o estruturador e a consultora) da matriz de riscos da futura concessão/arrendamento.

Para cada item abaixo, retorne:
- "id": ID exato do item enviado.
- "titulo_executivo": Título factual identificando Órgão/Estruturador, nº do Edital/RFP/Contrato e objeto (ex: "Infra S.A. — RLE Edital nº 016/2026 (Edital PNCP nº 61/2026) — Elaboração de EVTEA de Rodovias Federais").
- "escopo_sintetico": Resumo factual padronizado contendo Objeto, Valor estimado/contratado, Prazo/Situação e indicação do documento onde está o escopo (Termo de Referência / Especificações Técnicas).
- "analise_riscos_segurabilidade": Bullets factuais (iniciados por "• ") descrevendo exclusivamente o que os documentos oficiais do certame preveem sobre Matriz de Riscos, Seguros e Garantias.

Retorne ESTRITAMENTE um objeto JSON no formato:
{
  "itens": [
    {
      "id": "INFRASA_97404",
      "titulo_executivo": "...",
      "escopo_sintetico": "...",
      "analise_riscos_segurabilidade": "• ..."
    }
  ]
}
"""


def curar_estruturacao_e_licitacoes(itens_brutos: list, pasta_projeto: Path, api_key: str = None) -> list:
    """
    Consolida as fichas documentais da Aba 2 (Estruturação, EVTEAs & Contratações Estratégicas).
    Itens com ficha documental já verificada diretamente nos PDFs oficiais (ficha_documental_verificada=True)
    mantêm seu texto literal verificado e atualizam o cache em historico_processos.json.
    """
    if not itens_brutos:
        return []

    key = api_key or os.getenv("GEMINI_API_KEY")
    caminho_hist = pasta_projeto / "historico_processos.json"
    historico = carregar_historico(caminho_hist)
    # Limpa chaves obsoletas e substitui pelo cache factual v2
    cache_est = historico.setdefault("analises_estruturacao_v2", {})
    if "analises_estruturacao" in historico:
        del historico["analises_estruturacao"]

    pendentes = []
    alterou_cache = False
    for it in itens_brutos:
        if it.get("ficha_documental_verificada"):
            cache_est[it["id"]] = {
                "id": it["id"],
                "titulo_executivo": it["titulo_executivo"],
                "escopo_sintetico": it["escopo_sintetico"],
                "analise_riscos_segurabilidade": it["analise_riscos_segurabilidade"],
            }
            alterou_cache = True
        elif it["id"] not in cache_est:
            pendentes.append(it)

    if alterou_cache:
        salvar_historico(caminho_hist, historico)

    if pendentes and key:
        client = genai.Client(api_key=key)
        blocos = []
        for it in pendentes:
            docs_str = ", ".join(d["rotulo"] for d in it.get("documentos", [])[:6])
            blocos.append(
                f"ID: {it['id']}\n"
                f"Estruturador/Órgão: {it['estruturador_sigla']}\n"
                f"Categoria: {it['categoria_item']} | Modalidade: {it['modalidade']}\n"
                f"Valor: {it['valor_formatado']} | Prazo/Situação: {it.get('data_fim_br', '')}\n"
                f"Título Bruto: {it['titulo']}\n"
                f"Documentos Disponíveis: {docs_str}\n"
                f"Descrição Bruta: {it['descricao_bruta']}\n"
                f"---"
            )
        prompt_full = f"{PROMPT_CURADORIA_ESTRUTURACAO}\n\nITENS PARA REGISTRO FACTUAL:\n\n" + "\n".join(blocos)

        modelos_candidatos, temperatura_ia = _carregar_parametros_ia()
        for modelo in modelos_candidatos:
            try:
                resp = client.models.generate_content(
                    model=modelo,
                    contents=prompt_full,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        temperature=temperatura_ia,
                    )
                )
                if resp and resp.text:
                    dados_ia = json.loads(resp.text)
                    for aval in dados_ia.get("itens", []):
                        iid = str(aval.get("id", ""))
                        if iid:
                            cache_est[iid] = aval
                    salvar_historico(caminho_hist, historico)
                    break
            except Exception as e:
                print(f"   [Aviso] Tentativa de curadoria de estruturação com {modelo}: {e}")
                continue

    resultado = []
    for it in itens_brutos:
        av = cache_est.get(it["id"], {})
        novo = dict(it)
        novo["titulo_executivo"] = it.get("titulo_executivo") or av.get("titulo_executivo") or it["titulo"]
        novo["escopo_sintetico"] = it.get("escopo_sintetico") or av.get("escopo_sintetico") or it["descricao_bruta"][:380]
        novo["analise_riscos_segurabilidade"] = (
            it.get("analise_riscos_segurabilidade")
            or av.get("analise_riscos_segurabilidade")
            or "• Verificar nos anexos técnicos (Termo de Referência / Especificações Técnicas) as disposições sobre matriz de riscos, seguros e garantias."
        )
        resultado.append(novo)

    return resultado


PROMPT_RESUMO_FACTUAL_SFN = """
Você é um analista documental técnico. Para cada consulta pública abaixo (que já passou no filtro temático), redija um resumo estritamente factual de 1 frase curta em português sintetizando o ato normativo alterado e o tema central.
REGRAS:
- Proibido opinião, juízo de valor ou "recomenda-se".
- Use apenas os dados do título e da ementa fornecidos.
Retorne ESTRITAMENTE um JSON no formato:
{"resumos": [{"id": "SUSEP_CP_15_2026", "resumo_ia": "..."}]}
"""


def enriquecer_sfn_com_ia_lote(dados_sfn: dict, pasta_projeto: Path, api_key: str = None) -> dict:
    """
    Aplica as 4 regras de economia de chamadas de API na Aba 4 (SFN):
    1. O filtro regex já rodou antes (apenas dados_sfn['aprovados'] são avaliados);
    2. Apenas itens novos (identificados por hash_cache_ia = URL + SHA256 do texto) vão à IA;
    3. Uma única chamada em lote para todos os itens novos;
    4. Envia apenas título e resumo curto (ementa[:380]). Se a IA não rodar, omite o resumo_ia sem texto genérico.
    """
    if not dados_sfn or not dados_sfn.get("aprovados"):
        return dados_sfn

    key = api_key or os.getenv("GEMINI_API_KEY")
    caminho_hist = Path(pasta_projeto) / "historico_processos.json"
    historico = carregar_historico(caminho_hist)
    cache_sfn = historico.setdefault("analises_sfn_ia", {})

    novos_para_ia = []
    for it in dados_sfn["aprovados"]:
        h_key = it.get("hash_cache_ia") or it["id"]
        if h_key not in cache_sfn:
            novos_para_ia.append(it)

    if novos_para_ia and key:
        modelos_candidatos, temperatura_ia = _carregar_parametros_ia()
        try:
            client = genai.Client(api_key=key)
            linhas = [
                f"ID: {it['id']} | Título: {it['modalidade_numero']} ({it['entidade']}) | Ementa: {it['ementa'][:380]}"
                for it in novos_para_ia
            ]
            prompt = f"{PROMPT_RESUMO_FACTUAL_SFN}\n\nITENS:\n" + "\n".join(linhas)
            for modelo in modelos_candidatos:
                try:
                    resp = client.models.generate_content(
                        model=modelo,
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            response_mime_type="application/json",
                            temperature=temperatura_ia,
                        ),
                    )
                    if resp and resp.text:
                        parsed = json.loads(resp.text)
                        mapa = {str(r.get("id", "")): (r.get("resumo_ia") or "").strip() for r in parsed.get("resumos", [])}
                        for it in novos_para_ia:
                            res_txt = mapa.get(it["id"], "")
                            if res_txt:
                                h_key = it.get("hash_cache_ia") or it["id"]
                                cache_sfn[h_key] = res_txt
                        salvar_historico(caminho_hist, historico)
                        break
                except Exception as e:
                    print(f"   [Aviso SFN IA] Tentativa com {modelo}: {e}")
                    continue
        except Exception as e:
            print(f"   [Aviso SFN IA] Falha geral na chamada opcional de resumo IA: {e}")

    for it in dados_sfn["aprovados"]:
        h_key = it.get("hash_cache_ia") or it["id"]
        it["resumo_ia"] = cache_sfn.get(h_key, "")

    return dados_sfn

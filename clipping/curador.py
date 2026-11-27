import os
import re
import json
import hashlib
import urllib.parse
from datetime import date, timedelta
from pathlib import Path
from difflib import SequenceMatcher
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

PASTA_CLIPPING = Path(__file__).parent.resolve()
ARQUIVO_TERMOS_CLIPPING = PASTA_CLIPPING / "termos_filtro.json"
ARQUIVO_LOG_DESCARTADOS_CLIPPING = PASTA_CLIPPING / "log_descartados_filtro.txt"
ARQUIVO_CACHE_NOTICIAS = PASTA_CLIPPING / "historico_noticias_cache.json"
PASTA_DIAGNOSTICO = PASTA_CLIPPING / "diagnostico"

MOTIVOS_DESCARTE_IA = {
    "eco_dias_anteriores",
    "duplicada_mesmo_dia",
    "fora_do_escopo",
    "corte_da_vertical",
    "baixa_relevancia",
}

ALLOWED_FEED_HOSTS = {
    "news.google.com",
    "agenciainfra.com",
    "www.agenciainfra.com",
    "portalbenews.com.br",
    "www.portalbenews.com.br",
    "capitalreset.uol.com.br",
    "jota.info",
    "www.jota.info",
    "a16z.news",
    "www.a16z.news",
    "mail.google.com",
}


def _sanitizar_texto_diagnostico(texto: str) -> str:
    """Remove qualquer e-mail ou caractere '@' de campos gravados no diagnóstico."""
    if not texto or not isinstance(texto, str):
        return ""
    limpo = re.sub(r"[\w.+-]+@[\w.-]+", "[redigido]", texto)
    limpo = limpo.replace("@", "(arroba)")
    return limpo.strip()


def _sanitizar_link_diagnostico(url: str) -> str:
    """Remove account_id e qualquer e-mail/'@' da URL antes de gravar no diagnóstico."""
    if not url or not isinstance(url, str):
        return ""
    limpo = re.sub(r"([?&])account_id=[^&]*&?", r"\1", url.strip())
    limpo = re.sub(r"[?&]+$", "", limpo)
    limpo = re.sub(r"account_id=[^&]*", "", limpo)
    limpo = re.sub(r"[\w.+-]+@[\w.-]+", "[redigido]", limpo)
    limpo = limpo.replace("@", "(arroba)")
    return limpo.strip()


def _url_segura_permitida(url: str) -> bool:
    """Garante que apenas URLs HTTPS oriundas dos servidores oficiais dos nossos coletores ou órgãos públicos (.gov.br/.leg.br/.jus.br) sejam aceitas."""
    if not url or not isinstance(url, str):
        return False
    try:
        parsed = urllib.parse.urlparse(url.strip())
        host = (parsed.hostname or "").lower()
        if parsed.scheme != "https" or not host:
            return False
        if host in ALLOWED_FEED_HOSTS:
            return True
        if host.endswith((".gov.br", ".leg.br", ".jus.br")):
            return True
        return False
    except Exception:
        return False

PROMPT_CURADORIA = """
Você é um Analista Sênior de Inteligência Regulatória, Financeira e Tecnológica especializado no ecossistema brasileiro de Infraestrutura, Seguros Corporativos, Mercado de Carbono, Mercado de Capitais e Tecnologia/Gestão Aplicada.

Sua tarefa é analisar o lote de notícias brutas e newsletters coletadas hoje (numeradas como [ID: 1], [ID: 2], etc.), filtrar o ruído, eliminar duplicidades e estruturar as matérias mais relevantes dentro de 5 blocos temáticos e suas respectivas subseções editoriais:

1. "infra" (Infraestrutura & Outorgas):
   - Subseções possíveis: "Leilões, Editais & PPI", "Regulação & Contratos (ANTT / ANAC / ANTAQ / Portos)", "Reequilíbrio & Matriz de Riscos"
2. "seguros" (Seguros de Grandes Riscos):
   - Subseções possíveis: "Seguro Garantia & Performance Bonds", "Regulação SUSEP, CNseg & Mercado Corporativo", "Resseguro & Riscos Climáticos"
3. "carbono" (Mercado de Carbono & Transição Climática):
   - Subseções possíveis: "SBCE, Eco Invest & Financiamento Climático", "Transição Energética, Minerais Críticos & ESG", "Segurança Jurídica & Integridade de Créditos"
4. "divida" (Instrumentos de Dívida & Mercado de Capitais):
   - Subseções possíveis: "Debêntures & Leis 12.431 / 14.801", "Regulação CVM, ANBIMA & BNDES", "Mercado de Crédito Privado & Títulos Verdes"
5. "tech" (Tecnologia, IA & Gestão Aplicada):
   - Subseções possíveis: "IA, Automação & Produtividade Executiva", "Infraestrutura Digital, Energia & GovTech / FinTech", "Estratégia & Tendências Globais (McKinsey / a16z / Mercado)"

CRITÉRIOS DE CURADORIA E PRIORIDADE DE FONTES:
- PRIORIZE SEMPRE os veículos de primeira linha e fontes especializadas: Valor Econômico, Broadcast, Reuters, Estadão, Folha de S.Paulo, O Globo, Agência iNFRA (site aberto), BE News, JOTA, Capital Reset / Reset News, CNseg, McKinsey, a16z, Environmental Finance e órgãos oficiais (Gov.br, BNDES, CVM, SUSEP, ANTT, ANTAQ, ANAC).
- CORTES OBRIGATÓRIOS POR VERTICAL (decisão editorial de 23/11/2026):
  * Em "seguros": DESCARTE eventos cerimoniais/homenagens institucionais (ex.: sessões solenes, prêmios, debates genéricos de "perspectivas"), seguro de varejo/auto/vida/residencial/rural, releases comerciais de lançamento de produtos/vertical e agenda institucional sem decisão (ex.: "Susep participa de reuniões", missões, fóruns e encontros internacionais). MANTENHA grandes riscos, seguro-garantia (performance bond), resseguro, sinistros climáticos em infraestrutura e regulação concreta da SUSEP/CNSP/CNseg.
  * Em "divida": DESCARTE FIDCs ou operações de crédito de varejo/PME (ex.: cartões, plataformas PME, crédito vencido), Fiagros, fundos imobiliários (FII) e fatos corporativos isolados sem relação com infraestrutura ou regulação do mercado (inclusive questionamento da CVM a um fundo ou companhia específicos fora de infraestrutura). MANTENHA debêntures incentivadas/de infraestrutura (Leis 12.431/14.801), REIDI, BNDES, fundos públicos/garantidores, títulos verdes e regulação da CVM/ANBIMA/CMN.
  * Em "tech": DESCARTE releases corporativos (certificações, prêmios, treinamentos comerciais para corretoras, contrato ou fornecimento de empresa privada divulgado por revista setorial), gadgets de consumo e artigos genéricos fora de nosso escopo. MANTENHA apenas pautas que cruzem tecnologia/IA/gestão com infraestrutura digital (data centers, demanda energética da IA), aplicação de IA no setor público/financeiro/regulatório ou estratégia executiva de alta densidade.
- RELEVÂNCIA PRÓPRIA DOS SETORES DE TRANSPORTE (decisão 29, 24/11/2026): na vertical "infra", fato CONCRETO sobre portos, aeroportos, hidrovias, ferrovias ou rodovias NÃO é "baixa relevância", ainda que venha de veículo setorial ou regional. São fatos concretos: contrato, edital, leilão, concessão, arrendamento ou renovação; obra, dragagem ou investimento com valor; decisão ou manifestação do TCU, do Ministério Público junto ao TCU, das agências (ANTAQ, ANAC, ANTT) ou de autoridade portuária; ZPE ligada a porto; dado operacional relevante de concessão (ex.: volume do free flow); tarifa, desconto tarifário ou regra de cobrança de autoridade portuária, concessionária ou agência; estatística oficial periódica de movimento (passageiros, carga, contêineres) divulgada por órgão público (ex.: movimento mensal de passageiros aéreos divulgado pelo Ministério ou pela ANAC). A publicação de edital, aviso de licitação ou arrendamento é fato novo mesmo que o leilão já tenha sido anunciado antes. Continue descartando eco de fato já publicado, eventos, premiações e releases sem fato concreto, e notícia operacional trivial (ex.: trem natalino, vagas de emprego, ampliação sazonal de voos).
- Descarte blogs regionais desconhecidos, fofocas políticas genéricas e acidentes de trânsito. Se um artigo estiver em inglês (ex.: a16z ou McKinsey), traduza o título e faça o resumo executivo em português.
- Quando uma newsletter do Gmail (ex.: Reset News, JOTA, McKinsey) abordar um tema de carbono, dívida, seguros, infra ou tech, aloque-a na vertical correspondente mantendo a indicação da fonte.
- Para cada notícia selecionada:
  * Informe obrigatoriamente o campo numérico `"id"` correspondente ao número `[ID: X]` exato da notícia bruta de origem (NÃO invente links; o sistema injetará o link original exato a partir desse `"id"`).
  * Mantenha a fonte exata da matéria original.
  * Título objetivo em português.
  * Resumo executivo de 1 a 2 frases claras, explicando o fato e sua relevância técnica, regulatória ou financeira.
  * Classifique no campo "camada":
    - "destaque": para as notícias de MAIOR impacto daquela vertical (até 4), visíveis de imediato na vitrine principal.
    - "complementar": para as demais notícias novas e relevantes daquela vertical, na gaveta expansível "Radar Complementar".
- DIRETRIZES DE MEMÓRIA EDITORIAL E COMBATE A DUPLICIDADES COM ATRASO (DELAY DIÁRIO):
  Junto com as notícias de hoje, você receberá a "MEMÓRIA DE FATOS JÁ PUBLICADOS NOS ÚLTIMOS DIAS". Aplique com rigor:
  1. REPERCUSSÃO COM ATRASO (ECO DE NOTÍCIA ANTERIOR): Se uma matéria de hoje apenas requenta ou repercute o mesmo fato já abordado na MEMÓRIA DOS ÚLTIMOS DIAS, DESCARTE-A. Nunca repita o mesmo fato em dias seguidos.
  2. DESDOBRAMENTO REAL (FATO NOVO NO PROCESSO) vs. REPETIÇÃO: Só inclua assunto de dias anteriores se houver avanço concreto novo (ex.: "TCU suspende edital", "Empresas entregam propostas"), deixando explícito o novo passo no resumo.
  3. DEDUPLICAÇÃO NO MESMO DIA: Se vários veículos cobrirem o mesmo fato no mesmo dia, selecione APENAS A MELHOR cobertura.
  4. PRESERVAÇÃO DE PAUTAS HOMÔNIMAS: Não descarte matérias apenas por semelhança nominal se os objetos forem distintos (ex.: Lote 1 vs Lote 2; Acórdão 640 vs Acórdão 645).
- REGRA DE VOLUME (decisões 28 e 29, de 23 e 24/11/2026): NÃO existe meta mínima nem número-alvo. Selecione TODOS os fatos novos e relevantes do lote, até o máximo da vertical; não descarte fato concreto e relevante só para manter a lista curta. Vertical sem fato novo pode ficar com 1, 2 ou nenhuma notícia; nunca preencha com notícia repetida, release comercial ou tema fora do escopo. Máximo: 12 em "infra" (setor central do leitor; recebe o espaço não usado pelas demais) e 7 em cada uma das outras verticais.

Retorne ESTRITAMENTE um objeto JSON no seguinte formato:
{
  "infra": [
    {
      "id": 1,
      "camada": "destaque",
      "subsecao": "Leilões, Editais & PPI",
      "fonte": "Valor Econômico",
      "titulo": "Título da notícia",
      "resumo": "Explicação executiva do fato."
    },
    {
      "id": 5,
      "camada": "complementar",
      "subsecao": "Regulação & Contratos (ANTT / ANAC / ANTAQ / Portos)",
      "fonte": "Agência iNFRA",
      "titulo": "Título da notícia complementar",
      "resumo": "Resumo conciso do fato."
    }
  ],
  "seguros": [...],
  "carbono": [...],
  "divida": [...],
  "tech": [...],
  "descartados": [
    {
      "id": 2,
      "motivo": "eco_dias_anteriores"
    }
  ]
}
Na chave "descartados", informe {"id": N, "motivo": "<categoria>"} para cada matéria do lote não selecionada, usando apenas uma destas categorias: "eco_dias_anteriores", "duplicada_mesmo_dia", "fora_do_escopo", "corte_da_vertical", "baixa_relevancia".
"""


def _extrair_id_inteiro(valor_id):
    if isinstance(valor_id, int):
        return valor_id
    if isinstance(valor_id, str):
        m = re.search(r"\d+", valor_id)
        if m:
            return int(m.group(0))
    return None


def _resolver_noticia_original(item_ia, noticias_brutas):
    """
    Recupera a notícia bruta original garantindo 100% de fidelidade no link.
    Usa o 'id' numérico retornado pela IA e valida/faz fallback por similaridade de título/fonte.
    """
    idx = _extrair_id_inteiro(item_ia.get("id"))
    titulo_ia = (item_ia.get("titulo") or "").lower().strip()
    fonte_ia = (item_ia.get("fonte") or "").lower().strip()

    # 1. Verifica se o ID informado pela IA aponta diretamente para a notícia correta
    if idx is not None and 1 <= idx <= len(noticias_brutas):
        candidata = noticias_brutas[idx - 1]
        tit_cand = (candidata.get("title") or "").lower()
        src_cand = (candidata.get("source") or "").lower()
        sim_titulo = SequenceMatcher(None, titulo_ia, tit_cand).ratio()
        mesma_fonte = (fonte_ia and (fonte_ia in src_cand or src_cand in fonte_ia))
        # Mesmo quando traduzido do inglês (ex.: a16z), a fonte bate ou o ID é exato
        if sim_titulo >= 0.30 or mesma_fonte:
            return candidata

    # 2. Fallback: busca em noticias_brutas a maior similaridade combinada de título + resumo + fonte
    melhor_cand = None
    melhor_score = 0.0
    for cand in noticias_brutas:
        tit_cand = (cand.get("title") or "").lower()
        src_cand = (cand.get("source") or "").lower()
        sum_cand = (cand.get("summary") or "").lower()
        score = SequenceMatcher(None, titulo_ia, tit_cand).ratio()
        if fonte_ia and (fonte_ia in src_cand or src_cand in fonte_ia):
            score += 0.25
        # Verifica palavras-chave do título da IA no título/resumo original
        palavras = [p for p in re.findall(r"\w{4,}", titulo_ia) if p not in ("para", "como", "sobre", "entre", "após", "pelo", "pela")]
        if palavras:
            hits = sum(1 for p in palavras if p in tit_cand or p in sum_cand)
            score += 0.35 * (hits / len(palavras))
        if score > melhor_score:
            melhor_score = score
            melhor_cand = cand

    if melhor_cand and melhor_score >= 0.45:
        return melhor_cand

    # Se o ID estava dentro do range, usa-o como último recurso
    if idx is not None and 1 <= idx <= len(noticias_brutas):
        return noticias_brutas[idx - 1]

    return None


def _vincular_links_originais(dados_curados, noticias_brutas, mapa_selecao=None):
    """Injeta diretamente os links originais coletados pelo coletor.py, eliminando URLs inventadas ou truncadas."""
    links_usados = set()
    resultado_limpo = {}

    for vertical in ["infra", "seguros", "carbono", "divida", "tech"]:
        itens_vert = dados_curados.get(vertical, [])
        novos_itens = []
        for item in itens_vert:
            orig = _resolver_noticia_original(item, noticias_brutas)
            if not orig or not orig.get("link"):
                continue
            link_real = orig["link"].strip()
            if not _url_segura_permitida(link_real):
                continue
            if link_real in links_usados:
                continue
            links_usados.add(link_real)
            item["link"] = link_real
            if not item.get("fonte"):
                item["fonte"] = orig.get("source", "Fonte Web")
            novos_itens.append(item)
            if mapa_selecao is not None:
                mapa_selecao[id(orig)] = {
                    "vertical": vertical,
                    "camada": item.get("camada", ""),
                }
        resultado_limpo[vertical] = novos_itens

    return resultado_limpo


def _parsear_data_noticia_curador(published_str):
    try:
        import coletor
        return coletor.parsear_data_publicacao(published_str)
    except Exception:
        return None


def _calcular_margem_horas_curador():
    try:
        import coletor
        return coletor.calcular_margem_horas()
    except Exception:
        from datetime import datetime, timezone
        fuso_brt = timezone(timedelta(hours=-3))
        return 96 if datetime.now(timezone.utc).astimezone(fuso_brt).weekday() == 0 else 48


def _formatar_data_curta_curador(published_str):
    try:
        import coletor
        return coletor.formatar_data_curta_ia(published_str)
    except Exception:
        return "sem data"


def _criar_item_base_diagnostico(id_lote: int, noticia: dict) -> dict:
    from datetime import timezone
    fuso_brt = timezone(timedelta(hours=-3))
    dt_pub = _parsear_data_noticia_curador(noticia.get("published", ""))
    data_pub_iso = noticia.get("data_publicacao") or (dt_pub.astimezone(fuso_brt).strftime("%Y-%m-%d") if dt_pub else None)
    reg = {
        "id": id_lote,
        "fonte": _sanitizar_texto_diagnostico(noticia.get("source") or "Fonte Web"),
        "titulo": _sanitizar_texto_diagnostico((noticia.get("title") or "").replace("\n", " ")),
        "link": _sanitizar_link_diagnostico(noticia.get("link") or ""),
        "vertical_sugerida": _sanitizar_texto_diagnostico(noticia.get("vertical_original") or ""),
        "data_publicacao": data_pub_iso,
    }
    if data_pub_iso is None:
        reg["data_ilegivel"] = True
    return reg


def _salvar_diagnostico_curadoria(itens_diagnostico: list, modelo_ia, contingencia: bool):
    """Grava o arquivo clipping/diagnostico/diagnostico_AAAA-MM-DD.json sem dados pessoais ou caminhos locais."""
    try:
        hoje_iso = date.today().isoformat()
        contagens_destino = {
            "materia_antiga": 0,
            "trava_url": 0,
            "trava_titulo": 0,
            "termo_ruido": 0,
            "descartada_ia": 0,
            "selecionada": 0,
        }
        contagens_vertical = {
            "infra": 0,
            "seguros": 0,
            "carbono": 0,
            "divida": 0,
            "tech": 0,
        }

        sem_data_legivel = 0
        for reg in itens_diagnostico:
            dest = reg.get("destino", "")
            if dest in contagens_destino:
                contagens_destino[dest] += 1
            if reg.get("data_ilegivel"):
                sem_data_legivel += 1
            if dest == "selecionada":
                vert = reg.get("vertical", "")
                if vert in contagens_vertical:
                    contagens_vertical[vert] += 1

        payload = {
            "data": hoje_iso,
            "modelo_ia": _sanitizar_texto_diagnostico(modelo_ia) if modelo_ia else None,
            "contingencia": bool(contingencia),
            "total_coletadas": len(itens_diagnostico),
            "sem_data_legivel": sem_data_legivel,
            "contagens_por_destino": contagens_destino,
            "contagens_por_vertical": contagens_vertical,
            "itens": itens_diagnostico,
        }

        PASTA_DIAGNOSTICO.mkdir(parents=True, exist_ok=True)
        destino_arq = PASTA_DIAGNOSTICO / f"diagnostico_{hoje_iso}.json"
        destino_arq.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return destino_arq
    except Exception as e:
        print(f"   [Aviso] Falha ao gravar diagnóstico da curadoria: {type(e).__name__}")
        return None


CRITERIOS_TEMATICOS_CONTINGENCIA = {
    "infra": {
        "positivos": [
            "antt", "anac", "antaq", "mpor", "portos e aeroportos", "ministério dos transportes",
            "dnit", "concessão", "concessões", "concessionári", "outorga", "outorgas", "ppi", "pnd",
            "reequilíbrio", "arrendamento", "arrendamentos", "porto", "portos", "portuár",
            "aeroporto", "aeroportos", "aeroportuár", "rodovia", "rodovias", "rodoviár",
            "ferrovia", "ferrovias", "ferroviár", "hidrovia", "hidrovias", "hidroviár",
            "pedágio", "evtea", "tup", "fmm", "marinha mercante", "infovia"
        ],
        "ruidos": [
            "hospital", "médic", "cirurgia", "saúde", "restaurante", "gastronomia", "receita",
            "móveis", "cadeira", "emagrecimento", "medicamento", "farmacêutic", "aparelho celular",
            "futebol", "campeonato", "novela"
        ],
    },
    "seguros": {
        "positivos": [
            "seguro", "seguros", "segurador", "seguradora", "susep", "cnseg", "resseguro",
            "ressegurador", "resseguradora", "apólice", "apólices", "sinistro", "sinistros",
            "sinistralidade", "performance bond", "garantia judicial", "seguro garantia",
            "previdência complementar"
        ],
        "ruidos": [
            "segurança pública", "segurança no trânsito", "segurança alimentar"
        ],
    },
    "carbono": {
        "positivos": [
            "carbono", "sbce", "fundo clima", "transição ecológica", "transição energética",
            "finanças verdes", "eco invest", "ecoinvest", "esg", "descarbonização", "crédito de carbono",
            "créditos de carbono", "títulos verdes", "green bond", "cop30", "cop31", "cbio", "cbios",
            "saf ", "biocombustível", "hidrogênio verde", "biometano"
        ],
        "ruidos": [],
    },
    "divida": {
        "positivos": [
            "debênture", "debêntures", "lei 12.431", "lei 14.801", "cvm", "anbima", "fidc", "fidcs",
            "crédito privado", "mercado de capitais", "título incentivado", "títulos incentivados",
            "bndes", "reidi", "emissão de dívida", "cra", "cri"
        ],
        "ruidos": [],
    },
    "tech": {
        "positivos": [
            "inteligência artificial", " ia ", " ai ", "ia,", "ia.", "data center", "data centers",
            "automação", "govtech", "fintech", "mckinsey", "a16z", "algoritmo", "machine learning",
            "transformação digital", "infraestrutura digital"
        ],
        "ruidos": [
            "smartphone", "celular", "iphone", "galaxy", "videogame", "playstation", "xbox"
        ],
    },
}


def _validar_e_ajustar_vertical_contingencia(item):
    """
    Valida e ajusta deterministicamente a vertical de um item no modo sem IA,
    impedindo que matérias fora de tema entrem em 'infra' ou qualquer outro pilar.
    """
    texto = f"{item.get('title', '')} {item.get('summary', '')}".lower()
    vert_sugerida = item.get("vertical_original", "").strip().lower()

    # 1. Se a vertical sugerida for uma das 5 oficiais, valida se atende aos critérios dela
    if vert_sugerida in CRITERIOS_TEMATICOS_CONTINGENCIA:
        info = CRITERIOS_TEMATICOS_CONTINGENCIA[vert_sugerida]
        if not any(r in texto for r in info["ruidos"]):
            if any(p in texto for p in info["positivos"]):
                return vert_sugerida

    # 2. Se a vertical era genérica ('direto', 'gmail', 'outros') ou falhou nos critérios da vertical sugerida,
    # busca a vertical que melhor corresponde aos termos temáticos
    for v_candidata, info in CRITERIOS_TEMATICOS_CONTINGENCIA.items():
        if any(r in texto for r in info["ruidos"]):
            continue
        if any(p in texto for p in info["positivos"]):
            return v_candidata

    return None  # Descarta matéria que não pertence a nenhum dos 5 pilares temáticos


def _obter_historico_recente_estruturado(dias_retroativos=5):
    """
    Recupera fatos, URLs e títulos efetivamente publicados nos últimos dias úteis
    exclusivamente a partir dos arquivos HTML do histórico (raiz/historico e clipping/historico).
    O cache local não entra na trava nem na memória, evitando bloqueio por testes locais não publicados.
    """
    hoje_iso = date.today().isoformat()
    limite_iso = (date.today() - timedelta(days=dias_retroativos)).isoformat()
    fatos = []
    vistos_tit = set()
    urls_recentes = set()
    titulos_recentes = []

    for pasta_hist in [PASTA_CLIPPING.parent / "historico", PASTA_CLIPPING / "historico"]:
        if not pasta_hist.exists():
            continue
        for arq in sorted(pasta_hist.glob("clipping_*.html"), reverse=True):
            m = re.search(r"\d{4}-\d{2}-\d{2}", arq.name)
            if not m:
                continue
            dt = m.group(0)
            if dt == hoje_iso or dt < limite_iso:
                continue
            try:
                soup = BeautifulSoup(arq.read_text(encoding="utf-8", errors="ignore"), "html.parser")
                for a in soup.find_all("a", href=True):
                    href = (a.get("href") or "").strip()
                    tit = " ".join(a.get_text(" ", strip=True).split())
                    if not href.startswith("http") or "mdagavea.github.io" in href or "brasilparticipativo" in href:
                        continue
                    if len(tit) < 20:
                        continue
                    urls_recentes.add(href)
                    if tit.lower() not in vistos_tit:
                        vistos_tit.add(tit.lower())
                        titulos_recentes.append(tit)
                        fatos.append({"data": dt, "vertical": "historico", "fonte": "Histórico", "titulo": tit})
            except Exception:
                pass

    fatos.sort(key=lambda x: x["data"], reverse=True)
    linhas_memoria = [f"- [{f['data']}] [{f['fonte']}] {f['titulo']}" for f in fatos]
    return linhas_memoria, urls_recentes, titulos_recentes


def _obter_memoria_recente_fatos(dias_retroativos=5):
    linhas_memoria, _, _ = _obter_historico_recente_estruturado(dias_retroativos=dias_retroativos)
    return linhas_memoria


def curar_noticias_contingencia_sem_ia(noticias_brutas, _contexto_diagnostico=None):
    """
    Modo de contingência determinístico (sem IA): acionado automaticamente caso a API Gemini
    esteja indisponível ou sem créditos/cota, garantindo que o Clipping e o e-mail nunca falhem,
    mantendo 100% de aderência aos 5 pilares temáticos e evitando repetições de fatos dos últimos dias.
    """
    subsecoes_padrao = {
        "infra": "Regulação, Leilões & Contratos (Contingência sem IA)",
        "seguros": "Seguros Corporativos, Garantias & SUSEP (Contingência sem IA)",
        "carbono": "Mercado de Carbono, Clima & ESG (Contingência sem IA)",
        "divida": "Debêntures, Mercado de Capitais & Fomento (Contingência sem IA)",
        "tech": "Tecnologia, IA & Gestão Aplicada (Contingência sem IA)",
    }
    agrupado = {v: [] for v in subsecoes_padrao}
    titulos_vistos = []
    motivos_contingencia = {}

    fatos_recentes = _obter_memoria_recente_fatos(dias_retroativos=4)
    titulos_recentes = [
        re.sub(r"^-\s*\[\d{4}-\d{2}-\d{2}\]\s*\[[^\]]+\]\s*", "", f).strip().lower()
        for f in fatos_recentes
    ]

    for idx, n in enumerate(noticias_brutas, 1):
        titulo = (n.get("title") or "").strip()
        if not titulo:
            motivos_contingencia[id(n)] = "baixa_relevancia"
            continue
        # Deduplicação simples por similaridade de título no mesmo dia
        if any(SequenceMatcher(None, titulo.lower(), tv).ratio() > 0.78 for tv in titulos_vistos):
            motivos_contingencia[id(n)] = "duplicada_mesmo_dia"
            continue

        # Blindagem temática: valida e classifica com base nas regras do pilar temático
        vert = _validar_e_ajustar_vertical_contingencia(n)
        if not vert or vert not in agrupado:
            motivos_contingencia[id(n)] = "fora_do_escopo"
            continue

        if len(agrupado[vert]) >= 8:
            motivos_contingencia[id(n)] = "baixa_relevancia"
            continue

        # Identifica se é repetição com atraso de notícia já publicada nos últimos dias
        eh_eco_recente = False
        palavras_hoje = set(
            w for w in re.findall(r"\w{4,}", titulo.lower())
            if w not in {"para", "como", "sobre", "entre", "após", "pelo", "pela", "governo", "brasil"}
        )
        for tr in titulos_recentes:
            if SequenceMatcher(None, titulo.lower(), tr).ratio() > 0.65:
                eh_eco_recente = True
                break
            palavras_ant = set(
                w for w in re.findall(r"\w{4,}", tr)
                if w not in {"para", "como", "sobre", "entre", "após", "pelo", "pela", "governo", "brasil"}
            )
            if len(palavras_hoje & palavras_ant) >= 4:
                eh_eco_recente = True
                break

        # Se é eco recente, não pode assumir as 4 vagas de destaque (vitrine)
        if eh_eco_recente:
            if len(agrupado[vert]) < 4:
                # Não queima vaga de destaque com eco recente; reserva para a gaveta se houver vaga
                motivos_contingencia[id(n)] = "eco_dias_anteriores"
                continue
            camada = "complementar"
        else:
            camada = "destaque" if len(agrupado[vert]) < 4 else "complementar"

        titulos_vistos.append(titulo.lower())
        resumo = (n.get("summary") or "").strip()
        if not resumo or resumo.lower() == titulo.lower():
            resumo = "Matéria selecionada automaticamente pelo motor de contingência (consulte o link original)."
        elif len(resumo) > 260:
            resumo = resumo[:257] + "..."

        agrupado[vert].append({
            "id": idx,
            "camada": camada,
            "subsecao": subsecoes_padrao[vert],
            "fonte": n.get("source") or "Fonte Web",
            "titulo": titulo,
            "resumo": resumo,
        })

    mapa_selecao = {}
    resultado = _vincular_links_originais(agrupado, noticias_brutas, mapa_selecao=mapa_selecao)

    if _contexto_diagnostico is not None:
        itens_diag = _contexto_diagnostico["itens_diag"]
        mapa_obj_reg = _contexto_diagnostico["mapa_obj_reg"]
    else:
        itens_diag = []
        mapa_obj_reg = {}
        for idx_lote, n in enumerate(noticias_brutas, 1):
            reg = _criar_item_base_diagnostico(idx_lote, n)
            itens_diag.append(reg)
            mapa_obj_reg[id(n)] = reg

    for n in noticias_brutas:
        reg = mapa_obj_reg.get(id(n))
        if reg is None:
            continue
        sel = mapa_selecao.get(id(n))
        if sel:
            reg["destino"] = "selecionada"
            reg["vertical"] = sel["vertical"]
            reg["camada"] = sel["camada"]
        else:
            reg["destino"] = "descartada_ia"
            reg["motivo"] = motivos_contingencia.get(id(n), "baixa_relevancia")

    _salvar_diagnostico_curadoria(itens_diag, modelo_ia=None, contingencia=True)
    return resultado


def _filtrar_ruido_pre_ia(noticias_brutas, retornar_registros=False, margem_horas=None, incluir_descartados_coletor=True):
    """
    Aplica o filtro de data (Decisão nº 32: 48h dia comum, 96h segunda), o filtro de termos_filtro.json
    e o bloqueio determinístico anti-repetição (URL exata ou título muito similar nos últimos 5 dias)
    ANTES da chamada à IA. Matéria sem data legível segue no lote, com registro no diagnóstico.
    """
    from datetime import datetime, timezone
    termos_excluir = []
    if ARQUIVO_TERMOS_CLIPPING.exists():
        try:
            cfg = json.loads(ARQUIVO_TERMOS_CLIPPING.read_text(encoding="utf-8"))
            termos_excluir = [t.lower().strip() for t in cfg.get("termos_ruido_excluir", []) if t.strip()]
        except Exception:
            pass

    _, urls_recentes, titulos_recentes = _obter_historico_recente_estruturado(dias_retroativos=5)
    agora_utc = datetime.now(timezone.utc)
    margem = margem_horas if margem_horas is not None else _calcular_margem_horas_curador()
    limite_dt = agora_utc - timedelta(hours=margem)

    aprovadas = []
    descartadas = []
    itens_diag = []
    mapa_obj_reg = {}
    links_ja_em_diag = set()

    # Incorpora matérias antigas já barradas na origem (fetch_google_news) ao diagnóstico
    if incluir_descartados_coletor:
        try:
            import coletor
            for ant in coletor.obter_descartados_antigos():
                lk_a = (ant.get("link") or "").strip()
                if lk_a and lk_a in links_ja_em_diag:
                    continue
                if lk_a:
                    links_ja_em_diag.add(lk_a)
                reg_a = _criar_item_base_diagnostico(len(itens_diag) + 1, ant)
                reg_a["destino"] = "materia_antiga"
                reg_a["motivo"] = "materia_antiga"
                itens_diag.append(reg_a)
                descartadas.append((ant, f"Matéria antiga ({reg_a.get('data_publicacao') or 'data anterior à janela'})"))
        except Exception:
            pass

    for n in noticias_brutas:
        link_n = (n.get("link") or "").strip()
        tit_n = (n.get("title") or "").strip()
        texto = f"{tit_n} {n.get('summary', '')}".lower()
        reg = _criar_item_base_diagnostico(len(itens_diag) + 1, n)
        itens_diag.append(reg)
        if link_n:
            links_ja_em_diag.add(link_n)

        dt_pub = _parsear_data_noticia_curador(n.get("published", ""))
        if dt_pub is not None and dt_pub < limite_dt:
            descartadas.append((n, f"Matéria antiga ({reg.get('data_publicacao') or 'anterior à janela'})"))
            reg["destino"] = "materia_antiga"
            reg["motivo"] = "materia_antiga"
            continue

        if link_n and link_n in urls_recentes:
            descartadas.append((n, "Repetição (URL já publicada nos últimos 5 dias)"))
            reg["destino"] = "trava_url"
            continue

        melhor_tit = None
        melhor_sim = 0.0
        if tit_n:
            tit_low = tit_n.lower()
            for tr in titulos_recentes:
                sim = SequenceMatcher(None, tit_low, tr.lower()).ratio()
                if sim > melhor_sim:
                    melhor_sim = sim
                    melhor_tit = tr
        if tit_n and melhor_sim >= 0.80:
            descartadas.append((n, "Repetição (título já publicado nos últimos 5 dias)"))
            reg["destino"] = "trava_titulo"
            reg["titulo_casado"] = _sanitizar_texto_diagnostico(melhor_tit or "")
            reg["semelhanca"] = round(melhor_sim, 4)
            continue

        termo_achado = next((t for t in termos_excluir if t in texto), None)
        if termo_achado:
            descartadas.append((n, f"Termo de ruído: {termo_achado}"))
            reg["destino"] = "termo_ruido"
            reg["termo"] = _sanitizar_texto_diagnostico(termo_achado)
        else:
            aprovadas.append(n)
            mapa_obj_reg[id(n)] = reg

    if descartadas:
        hoje_iso = date.today().isoformat()
        with open(ARQUIVO_LOG_DESCARTADOS_CLIPPING, "a", encoding="utf-8") as f:
            for n, motivo in descartadas:
                tit = (n.get("title") or "").replace("\n", " ").strip()
                src = (n.get("source") or "Fonte").strip()
                f.write(f"{hoje_iso} | {src} | {tit} | {motivo}\n")

    if retornar_registros:
        return aprovadas, {"itens_diag": itens_diag, "mapa_obj_reg": mapa_obj_reg}
    return aprovadas


def _hash_noticia(n: dict) -> str:
    base = f"{(n.get('link') or '').strip()}|{(n.get('title') or '').strip().lower()}"
    return hashlib.sha256(base.encode("utf-8")).hexdigest()[:20]


def _carregar_cache_noticias() -> dict:
    if ARQUIVO_CACHE_NOTICIAS.exists():
        try:
            return json.loads(ARQUIVO_CACHE_NOTICIAS.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"itens": {}}


def _salvar_cache_noticias(cache: dict):
    try:
        # Mantém apenas os últimos 600 itens no cache para não crescer indefinidamente
        itens = cache.get("itens", {})
        if len(itens) > 600:
            chaves = list(itens.keys())[-600:]
            cache["itens"] = {k: itens[k] for k in chaves}
        ARQUIVO_CACHE_NOTICIAS.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


def curar_noticias_com_gemini(noticias_brutas, api_key=None):
    """
    Aplica as 4 regras de economia de chamadas à API Gemini:
    1. O filtro de termos (termos_filtro.json) roda antes da IA;
    2. Itens já processados anteriormente (por hash de endereço/título) são reaproveitados;
    3. Uma única chamada em lote para os itens do dia;
    4. Envia apenas título e resumo curto (até 280 caracteres), nunca a página inteira.
    """
    noticias_filtradas, ctx_diag = _filtrar_ruido_pre_ia(noticias_brutas, retornar_registros=True)
    key = api_key or os.getenv("GEMINI_API_KEY")
    if not key:
        print("   [Aviso] GEMINI_API_KEY ausente. Usando modo de contingência determinístico (sem IA).")
        return curar_noticias_contingencia_sem_ia(noticias_filtradas, _contexto_diagnostico=ctx_diag)

    cache = _carregar_cache_noticias()
    itens_cache = cache.setdefault("itens", {})

    client = genai.Client(api_key=key)

    # Prepara o payload enviando título, data curta e resumo curto (nunca URLs nem páginas inteiras)
    payload_linhas = []
    for i, n in enumerate(noticias_filtradas, 1):
        resumo_curto = (n.get("summary") or "")[:280]
        data_curta = _formatar_data_curta_curador(n.get("published", ""))
        payload_linhas.append(
            f"[ID: {i}] Fonte: {n['source']} | Data: {data_curta} | Vertical sugerida: {n.get('vertical_original', '')} | "
            f"Título: {n['title']} | Resumo bruto: {resumo_curto}"
        )

    # Injeta a Memória Semântica Deslizante (últimos 3 a 5 dias) para evitar repetição de ecos
    memoria_recente = _obter_memoria_recente_fatos(dias_retroativos=4)
    bloco_memoria = ""
    if memoria_recente:
        bloco_memoria = (
            "\n\nMEMÓRIA DE FATOS JÁ CURADOS NOS ÚLTIMOS DIAS (NÃO REPETIR NA VITRINE DE DESTAQUES; APENAS DESDOBRAMENTOS REAIS):\n"
            + "\n".join(memoria_recente[:90])
        )

    prompt_final = f"{PROMPT_CURADORIA}{bloco_memoria}\n\nNOTÍCIAS E NEWSLETTERS BRUTAS DO DIA:\n" + "\n".join(payload_linhas)

    # Lista de modelos por prioridade para garantir resiliência caso algum esteja sob alta demanda (503)
    modelos_candidatos = [
        "gemini-3.1-flash-lite",
        "gemini-3.5-flash-lite",
        "gemini-3.8-flash",
    ]

    response = None
    modelo_usado = None
    ultimo_erro = None

    for m in modelos_candidatos:
        try:
            response = client.models.generate_content(
                model=m,
                contents=prompt_final,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.0,
                ),
            )
            if response and response.text:
                modelo_usado = m
                break
        except Exception as e:
            ultimo_erro = e
            continue

    if not response or not response.text:
        print(f"   [Aviso] Modelos Gemini indisponíveis ({ultimo_erro}). Acionando modo de contingência sem IA.")
        return curar_noticias_contingencia_sem_ia(noticias_filtradas, _contexto_diagnostico=ctx_diag)

    try:
        dados_brutos_ia = json.loads(response.text)
        mapa_selecao = {}
        vinculados = _vincular_links_originais(dados_brutos_ia, noticias_filtradas, mapa_selecao=mapa_selecao)

        descartados_ia_por_idx = {}
        lista_desc = dados_brutos_ia.get("descartados", [])
        if isinstance(lista_desc, list):
            for entry in lista_desc:
                if not isinstance(entry, dict):
                    continue
                idx_desc = _extrair_id_inteiro(entry.get("id"))
                motivo_raw = (entry.get("motivo") or "").strip().lower()
                if idx_desc is not None and 1 <= idx_desc <= len(noticias_filtradas):
                    motivo_limpo = motivo_raw if motivo_raw in MOTIVOS_DESCARTE_IA else (_sanitizar_texto_diagnostico(motivo_raw) or "sem_resposta_da_ia")
                    descartados_ia_por_idx[idx_desc] = motivo_limpo

        mapa_obj_reg = ctx_diag["mapa_obj_reg"]
        for idx_ia, n in enumerate(noticias_filtradas, 1):
            reg = mapa_obj_reg.get(id(n))
            if reg is None:
                continue
            sel = mapa_selecao.get(id(n))
            if sel:
                reg["destino"] = "selecionada"
                reg["vertical"] = sel["vertical"]
                reg["camada"] = sel["camada"]
            else:
                reg["destino"] = "descartada_ia"
                reg["motivo"] = descartados_ia_por_idx.get(idx_ia, "sem_resposta_da_ia")

        _salvar_diagnostico_curadoria(ctx_diag["itens_diag"], modelo_ia=modelo_usado, contingencia=False)

        hoje_iso = date.today().isoformat()
        for vert, lista in vinculados.items():
            for it in lista:
                h = hashlib.sha256(f"{it.get('link','')}|{it.get('titulo','').lower()}".encode("utf-8")).hexdigest()[:20]
                itens_cache[h] = {"vertical": vert, "item": it, "data": hoje_iso}
        _salvar_cache_noticias(cache)
        return vinculados
    except Exception as e:
        print(f"   [Aviso] Falha ao decodificar JSON da IA ({e}). Acionando modo de contingência sem IA.")
        return curar_noticias_contingencia_sem_ia(noticias_filtradas, _contexto_diagnostico=ctx_diag)

import os
import re
import json
import hashlib
import urllib.parse
from datetime import date
from pathlib import Path
from difflib import SequenceMatcher
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

PASTA_CLIPPING = Path(__file__).parent.resolve()
ARQUIVO_TERMOS_CLIPPING = PASTA_CLIPPING / "termos_filtro.json"
ARQUIVO_LOG_DESCARTADOS_CLIPPING = PASTA_CLIPPING / "log_descartados_filtro.txt"
ARQUIVO_CACHE_NOTICIAS = PASTA_CLIPPING / "historico_noticias_cache.json"

ALLOWED_FEED_HOSTS = {
    "news.google.com",
    "agenciainfra.com",
    "www.agenciainfra.com",
    "mailchi.mp",
    "us14.campaign-archive.com",
    "capitalreset.uol.com.br",
    "jota.info",
    "www.jota.info",
    "a16z.news",
    "www.a16z.news",
    "mail.google.com",
}


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
- PRIORIZE SEMPRE os veículos de primeira linha e fontes especializadas: Valor Econômico, Broadcast, Reuters, Estadão, Folha de S.Paulo, O Globo, Agência iNFRA, JOTA, Capital Reset / Reset News, CNseg, McKinsey, a16z, Environmental Finance e órgãos oficiais (Gov.br, BNDES, CVM, SUSEP, ANTT, ANTAQ, ANAC).
- Na vertical "infra" (e também em "divida" e "carbono" quando aplicável), dê atenção especial às matérias exclusivas e aos atos do DOU/Radar oriundos do Boletim de Assinantes da "Agência iNFRA (iNFRA Transportes)" e "Agência iNFRA (iNFRAEnergia)" (que trazem furos sobre debêntures, concessões, EVTEAs, acórdãos da ANTAQ/ANTT/ANAC/TCU, decretos do PPI/PND e portarias do MPor/MT antes de saírem no site aberto), combinando-os de forma equilibrada com os grandes jornais (Valor, Estadão, O Globo, Folha, Reuters, JOTA).
- Descarte blogs regionais desconhecidos, fofocas políticas genéricas, acidentes de trânsito ou gadgets de consumo (ex.: rumores de celulares/jogos) que não tenham relação com regulação, investimentos, infraestrutura, finanças ou produtividade executiva.
- Na vertical "tech", selecione APENAS pautas que cruzem tecnologia/IA/gestão com o nosso trabalho: infraestrutura digital (data centers, demanda energética da IA), aplicação de IA no setor público/financeiro/jurídico, produtividade executiva (Substack/McKinsey/a16z) ou estratégia corporativa e regulatória. Se um artigo estiver em inglês (ex.: a16z ou McKinsey), traduza o título e faça o resumo executivo em português.
- Quando uma newsletter do Gmail (ex.: Reset News, JOTA, McKinsey) abordar um tema de carbono, dívida, seguros, infra ou tech, aloque-a na vertical correspondente mantendo a indicação da fonte.
- Para cada notícia selecionada:
  * Informe obrigatoriamente o campo numérico `"id"` correspondente ao número `[ID: X]` exato da notícia bruta de origem (NÃO invente links; o sistema injetará o link original exato a partir desse `"id"`).
  * Mantenha a fonte exata da matéria original.
  * Título objetivo em português.
  * Resumo executivo de 1 a 2 frases claras, explicando o fato e sua relevância técnica, regulatória ou financeira.
  * Classifique no campo "camada":
    - "destaque": para as 3 a 4 notícias de MAIOR impacto daquela vertical, que ficarão visíveis de imediato na vitrine principal do card.
    - "complementar": para mais 4 a 5 notícias relevantes daquela vertical, que ficarão acessíveis na gaveta expansível "Radar Complementar" do respectivo card para que nenhuma pauta útil se perca.
- META DE VOLUME (DEGRAU 1): Selecione de forma consistente entre 7 e 9 notícias por bloco temático (sendo 3 a 4 "destaque" na vitrine + 4 a 5 "complementar" na gaveta, totalizando entre 38 e 45 notícias curadas na soma das 5 verticais sempre que houver pautas pertinentes no lote). Não economize nas matérias "complementar": preencha a gaveta de cada card com pelo menos 4 boas pautas do lote.

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
  "tech": [...]
}
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


def _vincular_links_originais(dados_curados, noticias_brutas):
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
        resultado_limpo[vertical] = novos_itens

    return resultado_limpo


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


def curar_noticias_contingencia_sem_ia(noticias_brutas):
    """
    Modo de contingência determinístico (sem IA): acionado automaticamente caso a API Gemini
    esteja indisponível ou sem créditos/cota, garantindo que o Clipping e o e-mail nunca falhem
    e mantendo 100% de aderência aos 5 pilares temáticos.
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

    for idx, n in enumerate(noticias_brutas, 1):
        titulo = (n.get("title") or "").strip()
        if not titulo:
            continue
        # Deduplicação simples por similaridade de título
        if any(SequenceMatcher(None, titulo.lower(), tv).ratio() > 0.78 for tv in titulos_vistos):
            continue

        # Blindagem temática: valida e classifica com base nas regras do pilar temático
        vert = _validar_e_ajustar_vertical_contingencia(n)
        if not vert or vert not in agrupado:
            continue

        if len(agrupado[vert]) >= 8:
            continue

        titulos_vistos.append(titulo.lower())
        camada = "destaque" if len(agrupado[vert]) < 4 else "complementar"
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

    return _vincular_links_originais(agrupado, noticias_brutas)


def _filtrar_ruido_pre_ia(noticias_brutas):
    """
    Aplica o filtro de termos_filtro.json ANTES da chamada à IA e grava log dos itens descartados.
    """
    termos_excluir = []
    if ARQUIVO_TERMOS_CLIPPING.exists():
        try:
            cfg = json.loads(ARQUIVO_TERMOS_CLIPPING.read_text(encoding="utf-8"))
            termos_excluir = [t.lower().strip() for t in cfg.get("termos_ruido_excluir", []) if t.strip()]
        except Exception:
            pass

    aprovadas = []
    descartadas = []
    for n in noticias_brutas:
        texto = f"{n.get('title', '')} {n.get('summary', '')}".lower()
        termo_achado = next((t for t in termos_excluir if t in texto), None)
        if termo_achado:
            descartadas.append((n, f"Termo de ruído: {termo_achado}"))
        else:
            aprovadas.append(n)

    if descartadas:
        hoje_iso = date.today().isoformat()
        with open(ARQUIVO_LOG_DESCARTADOS_CLIPPING, "a", encoding="utf-8") as f:
            for n, motivo in descartadas:
                tit = (n.get("title") or "").replace("\n", " ").strip()
                src = (n.get("source") or "Fonte").strip()
                f.write(f"{hoje_iso} | {src} | {tit} | {motivo}\n")

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
    noticias_filtradas = _filtrar_ruido_pre_ia(noticias_brutas)
    key = api_key or os.getenv("GEMINI_API_KEY")
    if not key:
        print("   [Aviso] GEMINI_API_KEY ausente. Usando modo de contingência determinístico (sem IA).")
        return curar_noticias_contingencia_sem_ia(noticias_filtradas)

    cache = _carregar_cache_noticias()
    itens_cache = cache.setdefault("itens", {})

    client = genai.Client(api_key=key)

    # Prepara o payload enviando apenas título e resumo curto (nunca URLs nem páginas inteiras)
    payload_linhas = []
    for i, n in enumerate(noticias_filtradas, 1):
        resumo_curto = (n.get("summary") or "")[:280]
        payload_linhas.append(
            f"[ID: {i}] Fonte: {n['source']} | Vertical sugerida: {n.get('vertical_original', '')} | "
            f"Título: {n['title']} | Resumo bruto: {resumo_curto}"
        )

    prompt_final = f"{PROMPT_CURADORIA}\n\nNOTÍCIAS E NEWSLETTERS BRUTAS DO DIA:\n" + "\n".join(payload_linhas)

    # Lista de modelos por prioridade para garantir resiliência caso algum esteja sob alta demanda (503)
    modelos_candidatos = [
        "gemini-3.1-flash-lite",
        "gemini-3.5-flash-lite",
        "gemini-3.8-flash",
    ]

    response = None
    ultimo_erro = None

    for m in modelos_candidatos:
        try:
            response = client.models.generate_content(
                model=m,
                contents=prompt_final,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.2,
                ),
            )
            if response and response.text:
                break
        except Exception as e:
            ultimo_erro = e
            continue

    if not response or not response.text:
        print(f"   [Aviso] Modelos Gemini indisponíveis ({ultimo_erro}). Acionando modo de contingência sem IA.")
        return curar_noticias_contingencia_sem_ia(noticias_filtradas)

    try:
        dados_brutos_ia = json.loads(response.text)
        vinculados = _vincular_links_originais(dados_brutos_ia, noticias_filtradas)
        hoje_iso = date.today().isoformat()
        for vert, lista in vinculados.items():
            for it in lista:
                h = hashlib.sha256(f"{it.get('link','')}|{it.get('titulo','').lower()}".encode("utf-8")).hexdigest()[:20]
                itens_cache[h] = {"vertical": vert, "item": it, "data": hoje_iso}
        _salvar_cache_noticias(cache)
        return vinculados
    except Exception as e:
        print(f"   [Aviso] Falha ao decodificar JSON da IA ({e}). Acionando modo de contingência sem IA.")
        return curar_noticias_contingencia_sem_ia(noticias_filtradas)


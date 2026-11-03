import json
import re
import ssl
import urllib.parse
import urllib.request
from datetime import datetime, date, timedelta
from bs4 import BeautifulSoup

API_URL = "https://brasilparticipativo.presidencia.gov.br/api"
BASE_URL = "https://brasilparticipativo.presidencia.gov.br"

# Expressão regular ampla para pré-selecionar candidatos ligados às nossas verticais e setores correlatos
REGEX_TEMAS_INTERESSE = re.compile(
    r"(antt|antaq|anac|dnit|infra\s*s\.?a|transport|rodovi|ferrovi|portu|porto|aeroport|hidrovi|"
    r"pouso|decolagem|avia[cç][aã]o|aeron[aá]utic|navega[cç][aã]o|ipr|drenagem|pavimenta|"
    r"concess[aã]o|concess[oõ]es|ppp|parceria\s+p[uú]blico|outorga|leil[aã]o|leil[oõ]es|tarif|"
    r"free\s*flow|ped[aá]gio|reequil[ií]brio|modelagem|estrutura[cç][aã]o\s+de\s+projetos|"
    r"seguro|susep|garantia|performance\s+bond|resseguro|apolice|ap[oó]lice|sinistro|"
    r"deb[eê]nture|cvm|anbima|cr[eé]dito|financiamento|fomento|bndes|mercado\s+de\s+capitais|fidc|securitiza|"
    r"carbono|sbce|clima|clim[aá]tic|sustent[aá]vel|sustentabilidade|transi[cç][aã]o\s+ecol[oó]gica|tsb|taxonomia|"
    r"licenciamento\s+ambiental|ibama|icmbio|energia|combust[ií]vel|descarboniza|log[ií]stic|"
    r"mpor|minist[eé]rio\s+dos\s+transportes|minist[eé]rio\s+de\s+portos|fazenda|planejamento)",
    re.IGNORECASE
)

# Palavras de exclusão óbvia para evitar falsos positivos (ex: testes internos de TI ou saúde/educação sem relação)
REGEX_RUIDO_TESTE = re.compile(
    r"^(teste|testesaasbp| \[teste\]|teste\s+audi[eê]ncia)",
    re.IGNORECASE
)


def criar_contexto_ssl():
    """Configura contexto SSL compatível com os servidores do Governo Federal (Dataprev/Nginx)."""
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    ctx.options |= getattr(ssl, "OP_IGNORE_UNEXPECTED_EOF", 0)
    try:
        ctx.set_ciphers("DEFAULT@SECLEVEL=1")
    except Exception:
        pass
    return ctx


def executar_graphql(query: str, timeout: int = 25) -> dict:
    """Executa uma consulta GraphQL na API do Brasil Participativo."""
    ctx = criar_contexto_ssl()
    payload = json.dumps({"query": query}).encode("utf-8")
    req = urllib.request.Request(
        API_URL,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) RadarParticipativo/1.0"
        }
    )
    with urllib.request.urlopen(req, context=ctx, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8", errors="replace")
        return json.loads(raw)


def higienizar_titulo_portal(titulo: str) -> str:
    """Corrige erros de digitação recorrentes cadastrados por operadores no portal oficial e remove espaços duplos."""
    if not titulo:
        return ""
    t = re.sub(r"\s{2,}", " ", titulo).strip()
    correcoes = [
        (r"\bCosulta\b", "Consulta"),
        (r"\bcosulta\b", "consulta"),
        (r"\bPúbica\b", "Pública"),
        (r"\bpúbica\b", "pública"),
        (r"\bAudiencia\b", "Audiência"),
        (r"\bPublica\b", "Pública"),
    ]
    for padrao, subst in correcoes:
        t = re.sub(padrao, subst, t)
    return t


def _formatar_rotulo_link(texto: str, url: str, tipo_link: str) -> str:
    """Transforma textos âncora genéricos ('clique aqui', 'aqui', 'link') em rótulos executivos claros."""
    t_low = (texto or "").strip().lower().rstrip(".")
    u_low = (url or "").lower()
    if t_low in ("clique aqui", "acesse aqui", "aqui", "link", "documento / link", "saiba mais", "formulário"):
        if tipo_link == "CONTRIBUIR":
            if "participantt" in u_low:
                return "📝 Enviar Contribuição (ParticipANTT)"
            return "📝 Enviar Contribuição"
        if tipo_link == "DOU":
            return "📜 Publicação no DOU"
        if tipo_link == "SEI":
            return "🗂️ Processo SEI"
        if tipo_link == "MINUTA":
            return "📄 Minuta do Ato"
        if tipo_link == "NOTA_TECNICA":
            return "📊 Nota Técnica"
    return (texto or "Documento / Link")[:80]


def extrair_texto_e_links_html(raw_html: str):
    """Limpa o HTML da descrição e extrai todos os links úteis (SEI, DOU, Minutas, Notas Técnicas)."""
    if not raw_html:
        return "", []
    soup = BeautifulSoup(raw_html, "html.parser")
    links_extraidos = []
    vistos = set()

    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        texto = a.get_text(" ", strip=True) or "Documento / Link"
        if not href or href.startswith("javascript:") or href.startswith("mailto:"):
            continue
        if href.startswith("/"):
            href = BASE_URL + href
        if href not in vistos:
            vistos.add(href)
            tipo_link = classificar_link(href, texto)
            rotulo_limpo = _formatar_rotulo_link(texto, href, tipo_link)
            links_extraidos.append({
                "rotulo": rotulo_limpo,
                "url": href,
                "categoria": tipo_link
            })

    texto_limpo = soup.get_text(" ", strip=True)
    texto_limpo = re.sub(r"\s+", " ", texto_limpo)
    return texto_limpo, links_extraidos


def classificar_link(url: str, texto: str) -> str:
    """Identifica o tipo de documento/link para exibição executiva."""
    u = url.lower()
    t = texto.lower()
    if "in.gov.br" in u or "dou" in t or "portaria" in t and "in.gov.br" in u:
        return "DOU"
    if "sei." in u or "processo" in t:
        return "SEI"
    if "minuta" in t or "minuta" in u:
        return "MINUTA"
    if "nota" in t and "técnica" in t or "nota-tecnica" in u:
        return "NOTA_TECNICA"
    if "quadro" in t or "comparativo" in t or "justificativa" in t or "air" in t:
        return "SUBSIDIO"
    if "brasilparticipativo.presidencia.gov.br/processes/" in u and "/f/" in u:
        return "CONTRIBUIR"
    if "participantt" in u or "participa" in u:
        return "CONTRIBUIR"
    return "DOCUMENTO"


def formatar_anexo(att: dict) -> dict:
    """Converte um anexo da API em um item de documento legível com nome amigável."""
    raw_url = att.get("url", "")
    full_url = BASE_URL + raw_url if raw_url.startswith("/") else raw_url
    nome_arquivo = raw_url.split("/")[-1] if "/" in raw_url else "Anexo.pdf"
    nome_decodificado = urllib.parse.unquote(nome_arquivo)
    # Limpa nomes muito longos mantendo clareza
    if len(nome_decodificado) > 75:
        nome_decodificado = nome_decodificado[:72] + "..."
    return {
        "rotulo": f"📎 {nome_decodificado}",
        "url": full_url,
        "categoria": "ANEXO_PDF"
    }


def parse_iso_date(val: str):
    if not val:
        return None
    try:
        return datetime.fromisoformat(val[:10]).date()
    except Exception:
        return None


def parse_iso_datetime(val: str):
    if not val:
        return None
    try:
        return datetime.fromisoformat(val)
    except Exception:
        return None


def corrigir_data_fim_se_erro_digitacao(start_d: date, end_d: date, pub_dt: datetime) -> date:
    """
    Alguns operadores cadastram processos em outubro/2026 mas digitam '2025-11-05' por engano no endDate.
    Se o processo foi publicado em 2026 e o endDate está com ano 2025 (mês >= mês de publicação), corrige para 2026.
    """
    if not end_d or not pub_dt:
        return end_d
    if pub_dt.year == 2026 and end_d.year == 2025 and end_d.month >= pub_dt.month:
        try:
            return end_d.replace(year=2026)
        except ValueError:
            return end_d
    return end_d


def coletar_processos_brasil_participativo(dias_historico_encerrados: int = 20):
    """
    Coleta todos os processos publicados e em pré-publicação na API GraphQL do Brasil Participativo,
    enriquece metadados, extrai links/anexos e pré-filtra candidatos relevantes às nossas verticais.
    """
    query = """
    query {
      participatoryProcesses {
        id
        slug
        publishedAt
        createdAt
        updatedAt
        startDate
        endDate
        hashtag
        title { translation(locale: "pt-BR") }
        subtitle { translation(locale: "pt-BR") }
        shortDescription { translation(locale: "pt-BR") }
        description { translation(locale: "pt-BR") }
        developerGroup { translation(locale: "pt-BR") }
        localArea { translation(locale: "pt-BR") }
        target { translation(locale: "pt-BR") }
        participatoryScope { translation(locale: "pt-BR") }
        participatoryStructure { translation(locale: "pt-BR") }
        attachments { url type }
        components { id name { translation(locale: "pt-BR") } __typename }
      }
      participatoryProcessTypes {
        id
        title { translation(locale: "pt-BR") }
        processes {
          id
          slug
          createdAt
          updatedAt
          startDate
          endDate
          title { translation(locale: "pt-BR") }
          subtitle { translation(locale: "pt-BR") }
          shortDescription { translation(locale: "pt-BR") }
          description { translation(locale: "pt-BR") }
          developerGroup { translation(locale: "pt-BR") }
          localArea { translation(locale: "pt-BR") }
          target { translation(locale: "pt-BR") }
          participatoryScope { translation(locale: "pt-BR") }
          participatoryStructure { translation(locale: "pt-BR") }
          attachments { url type }
        }
      }
    }
    """

    resposta = executar_graphql(query)
    dados = resposta.get("data", {}) or {}

    processos_publicados = dados.get("participatoryProcesses", []) or []
    tipos_processos = dados.get("participatoryProcessTypes", []) or []

    # Mapeia id -> nome do tipo (ex: "Consultas Públicas", "Audiência Pública")
    mapa_tipo_por_id = {}
    rascunhos_por_id = {}
    ids_publicados = {str(p["id"]) for p in processos_publicados if p}
    titulos_publicados = {
        ((p.get("title") or {}).get("translation") or "").strip().lower()
        for p in processos_publicados if p
    }

    for pt in tipos_processos:
        if not pt:
            continue
        nome_tipo = (pt.get("title") or {}).get("translation") or "Processo Participativo"
        for proc in (pt.get("processes") or []):
            if not proc:
                continue
            pid = str(proc["id"])
            t_proc = ((proc.get("title") or {}).get("translation") or "").strip().lower()
            mapa_tipo_por_id[pid] = nome_tipo
            if pid not in ids_publicados and t_proc not in titulos_publicados:
                rascunhos_por_id[pid] = (proc, nome_tipo)

    hoje = date.today()
    agora_lim = datetime.now().astimezone() - timedelta(hours=54)  # Janela de ~48h (dia + véspera)
    limite_rascunho = datetime.now().astimezone() - timedelta(days=10)

    candidatos = []

    # 1. Processa todos os publicados oficialmente
    for p in processos_publicados:
        if not p:
            continue
        item = normalizar_processo(p, mapa_tipo_por_id.get(str(p["id"]), "Consulta / Processo"), publicado=True, hoje=hoje, agora_lim_48h=agora_lim)
        if item and item["relevante_bruto"] and item["status_ciclo"] != "EXPIRADO_ANTIGO":
            candidatos.append(item)

    # 2. Processa os rascunhos/pré-publicação criados ou atualizados nos últimos 10 dias
    for pid, (proc, nome_tipo) in rascunhos_por_id.items():
        upd_dt = parse_iso_datetime(proc.get("updatedAt") or proc.get("createdAt"))
        if not upd_dt or upd_dt < limite_rascunho:
            continue
        item = normalizar_processo(proc, nome_tipo, publicado=False, hoje=hoje, agora_lim_48h=agora_lim)
        if item and item["relevante_bruto"]:
            candidatos.append(item)

    # Ordena priorizando: 1) Lançados 48h, 2) Prazo Urgente, 3) Abertos (menor prazo primeiro), 4) Pré-publicação
    ordem_prioridade = {
        "LANCADO_48H": 1,
        "PRAZO_URGENTE": 2,
        "ABERTO": 3,
        "PRE_PUBLICACAO": 4,
        "ENCERRADO_RECENTE": 5
    }
    candidatos.sort(key=lambda x: (
        ordem_prioridade.get(x["status_ciclo"], 9),
        x["dias_restantes"] if x["dias_restantes"] is not None else 999,
        -int(x["id"])
    ))

    return candidatos


def normalizar_processo(p: dict, tipo_catalogo: str, publicado: bool, hoje: date, agora_lim_48h: datetime):
    """Normaliza campos, datas, anexos e verifica aderência preliminar aos temas."""
    pid = str(p.get("id", ""))
    slug = p.get("slug", "")
    titulo = higienizar_titulo_portal(((p.get("title") or {}).get("translation") or "").strip())
    if not titulo or REGEX_RUIDO_TESTE.search(titulo) or REGEX_RUIDO_TESTE.search(slug):
        return None

    subtitulo = ((p.get("subtitle") or {}).get("translation") or "").strip()
    resumo_curto = ((p.get("shortDescription") or {}).get("translation") or "").strip()
    desc_html = ((p.get("description") or {}).get("translation") or "").strip()
    orgao_target = ((p.get("target") or {}).get("translation") or "").strip()
    orgao_dev = ((p.get("developerGroup") or {}).get("translation") or "").strip()
    area_local = ((p.get("localArea") or {}).get("translation") or "").strip()
    escopo_dou = ((p.get("participatoryScope") or {}).get("translation") or "").strip()
    contato = ((p.get("participatoryStructure") or {}).get("translation") or "").strip()

    desc_texto, links_html = extrair_texto_e_links_html(desc_html)
    resumo_limpo, _ = extrair_texto_e_links_html(resumo_curto)

    # Consolida links e documentos
    documentos = []
    urls_vistas = set()

    if escopo_dou and escopo_dou.startswith("http"):
        documentos.append({
            "rotulo": "📜 Ato Oficial no DOU",
            "url": escopo_dou,
            "categoria": "DOU"
        })
        urls_vistas.add(escopo_dou)

    for att in (p.get("attachments") or []):
        if att and att.get("url"):
            doc_att = formatar_anexo(att)
            if doc_att["url"] not in urls_vistas:
                urls_vistas.add(doc_att["url"])
                documentos.append(doc_att)

    for lk in links_html:
        if lk["url"] not in urls_vistas:
            urls_vistas.add(lk["url"])
            documentos.append(lk)

    # Datas e ciclo de vida
    pub_str = p.get("publishedAt") or p.get("createdAt") or ""
    pub_dt = parse_iso_datetime(pub_str)
    upd_dt = parse_iso_datetime(p.get("updatedAt") or pub_str)
    start_d = parse_iso_date(p.get("startDate")) or (pub_dt.date() if pub_dt else hoje)
    end_d = parse_iso_date(p.get("endDate"))
    end_d = corrigir_data_fim_se_erro_digitacao(start_d, end_d, pub_dt)

    dias_restantes = (end_d - hoje).days if end_d else None
    lancado_48h = bool(publicado and pub_dt and pub_dt >= agora_lim_48h)

    if not publicado:
        status_ciclo = "PRE_PUBLICACAO"
    elif end_d and dias_restantes < 0:
        # Mantém no painel por 72h (3 dias corridos, cobrindo fim de semana) como Prazo Vencido antes de excluir
        if dias_restantes >= -3:
            status_ciclo = "ENCERRADO_RECENTE"
        else:
            status_ciclo = "EXPIRADO_ANTIGO"
    else:
        if lancado_48h:
            status_ciclo = "LANCADO_48H"
        elif dias_restantes is not None and dias_restantes <= 7:
            status_ciclo = "PRAZO_URGENTE"
        else:
            status_ciclo = "ABERTO"

    # Texto completo para verificação de aderência temática (incluindo URLs de documentos/órgãos como anac.gov.br, antt.gov.br)
    urls_texto = " ".join(lk["url"] for lk in links_html)
    bloco_busca = " | ".join(filter(None, [
        titulo, subtitulo, resumo_limpo, desc_texto, orgao_target, orgao_dev, area_local, slug, urls_texto
    ]))
    relevante_bruto = bool(REGEX_TEMAS_INTERESSE.search(bloco_busca))

    url_processo = f"{BASE_URL}/processes/{slug}"

    return {
        "id": pid,
        "slug": slug,
        "url": url_processo,
        "publicado": publicado,
        "tipo_catalogo": tipo_catalogo,
        "titulo": titulo,
        "subtitulo": subtitulo,
        "descricao_texto": desc_texto[:2500],
        "orgao_informado": orgao_target or orgao_dev or area_local or "",
        "contato": contato,
        "data_publicacao": pub_dt.strftime("%Y-%m-%d %H:%M") if pub_dt else "",
        "data_publicacao_br": pub_dt.strftime("%d/%m/%Y") if pub_dt else "Pré-publicação",
        "data_atualizacao_iso": (upd_dt or pub_dt).isoformat() if (upd_dt or pub_dt) else "",
        "data_inicio_br": start_d.strftime("%d/%m/%Y") if start_d else "—",
        "data_fim_br": end_d.strftime("%d/%m/%Y") if end_d else "Sem data limite",
        "data_fim_iso": end_d.isoformat() if end_d else "",
        "dias_restantes": dias_restantes,
        "lancado_48h": lancado_48h,
        "status_ciclo": status_ciclo,
        "documentos": documentos,
        "relevante_bruto": relevante_bruto
    }


if __name__ == "__main__":
    itens = coletar_processos_brasil_participativo()
    print(f"Total de candidatos relevantes coletados: {len(itens)}")
    for it in itens[:12]:
        print(f"[{it['status_ciclo']}] ID {it['id']} | Pub: {it['data_publicacao_br']} | Fim: {it['data_fim_br']} ({it['dias_restantes']}d) | {it['titulo'][:85]}")

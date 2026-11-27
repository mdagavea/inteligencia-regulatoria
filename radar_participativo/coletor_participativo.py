import json
import re
import ssl
import time
import urllib.parse
import urllib.request
from datetime import datetime, date, timedelta
from pathlib import Path
from bs4 import BeautifulSoup

API_URL = "https://brasilparticipativo.presidencia.gov.br/api"
BASE_URL = "https://brasilparticipativo.presidencia.gov.br"
PASTA_PROJETO = Path(__file__).parent.resolve()
ARQUIVO_TERMOS_FILTRO = PASTA_PROJETO / "termos_filtro.json"
LOG_DESCARTADOS_PARTICIPATIVO = PASTA_PROJETO / "log_descartados_participativo.txt"


def carregar_exclusoes_participativo() -> list:
    """Carrega a lista de exclusões determinísticas da Aba 1 a partir de termos_filtro.json."""
    try:
        if ARQUIVO_TERMOS_FILTRO.exists():
            dados = json.loads(ARQUIVO_TERMOS_FILTRO.read_text(encoding="utf-8"))
            return dados.get("exclusoes_participativo", []) or []
    except Exception as e:
        print(f"   [Aviso] Falha ao ler exclusoes_participativo em termos_filtro.json: {e}")
    return []


def verificar_exclusao_participativo(texto_busca: str, exclusoes: list):
    """Retorna o motivo da exclusão se algum termo de exclusoes_participativo casar, ou None."""
    txt_low = (texto_busca or "").lower()
    for regra in exclusoes:
        termo = (regra.get("termo") or "").strip().lower()
        if termo and termo in txt_low:
            return regra.get("motivo") or f"Excluído por termo '{termo}'"
    return None


def registrar_descartados_participativo(descartados: list, modo: str = "w"):
    """Grava log auditável dos processos descartados na Aba 1 (filtro determinístico e IA)."""
    try:
        hoje_s = datetime.now().strftime("%Y-%m-%d %H:%M")
        linhas = []
        if modo == "w":
            linhas.append(f"# Log de descartados da Aba 1 (Consultas Públicas) — atualizado em {hoje_s}\n")
        for d in descartados:
            linhas.append(
                f"{hoje_s} | {d.get('origem', 'PRE-FILTRO')} | ID {d.get('id', '')} | "
                f"{d.get('orgao', '')} | {d.get('titulo', '')[:120]} | "
                f"Motivo: {d.get('motivo', '')} | {d.get('url', '')}\n"
            )
        with open(LOG_DESCARTADOS_PARTICIPATIVO, modo, encoding="utf-8") as f:
            f.writelines(linhas)
    except Exception as e:
        print(f"   [Aviso] Não foi possível gravar log_descartados_participativo.txt: {e}")


def _normalizar_titulo_dedup(titulo: str) -> str:
    t = higienizar_titulo_portal(titulo or "").lower()
    t = re.sub(r"[^a-z0-9à-ÿ]+", " ", t).strip()
    return t


STOPWORDS_TITULO_DEDUP = {
    "consulta", "pública", "publica", "sobre", "de", "da", "do", "das", "dos",
    "e", "a", "o", "que", "em", "no", "na", "para", "relativos", "relativo",
}
# Limiar ajustado de 0.6 para 0.5 no teste da A-046: o #856 x #857 (mesmo órgão ICMBio) tem semelhança 0.52 após edição do título do #857, com zero falsos positivos acima de 0.4
LIMIAR_SEMELHANCA_RASCUNHO = 0.5


def _extrair_orgao_bruto(p: dict) -> str:
    """Extrai o órgão informado pelo mesmo critério de normalizar_processo (target > developerGroup > localArea)."""
    orgao_target = ((p.get("target") or {}).get("translation") or "").strip()
    orgao_dev = ((p.get("developerGroup") or {}).get("translation") or "").strip()
    area_local = ((p.get("localArea") or {}).get("translation") or "").strip()
    return orgao_target or orgao_dev or area_local or ""


def _normalizar_orgao_dedup(orgao: str) -> str:
    return re.sub(r"\s+", " ", (orgao or "").strip().lower())


def _palavras_significativas_titulo(titulo: str) -> set:
    return {
        w for w in _normalizar_titulo_dedup(titulo).split()
        if w and w not in STOPWORDS_TITULO_DEDUP
    }


def _calcular_semelhanca_titulos(titulo_a: str, titulo_b: str) -> float:
    pa = _palavras_significativas_titulo(titulo_a)
    pb = _palavras_significativas_titulo(titulo_b)
    uniao = pa | pb
    if not uniao:
        return 0.0
    return len(pa & pb) / len(uniao)

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
    r"minist[eé]rio\s+dos\s+transportes|minist[eé]rio\s+de\s+portos|fazenda|planejamento)",
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


def executar_graphql(query: str, timeout: int = 35) -> dict:
    """Executa uma consulta GraphQL na API do Brasil Participativo com retry automático."""
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
    for tentativa in range(1, 4):
        try:
            with urllib.request.urlopen(req, context=ctx, timeout=timeout) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
                return json.loads(raw)
        except Exception as e:
            if tentativa == 3:
                raise
            print(f"   [Aviso GraphQL] Tentativa {tentativa}/3 falhou ({e}). Tentando novamente em 3s...")
            time.sleep(3)


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
    Corrige o ano de end_d apenas quando há evidência objetiva de erro de digitação,
    evitando reabrir consultas encerradas recadastradas em massa no portal em 29/10/2026
    (decisão de Marcos em 24/11/2026).

    Troca o ano de end_d para pub_dt.year somente quando as três condições valem juntas:
    a) start_d existe e é do mesmo ano da publicação (start_d.year == pub_dt.year);
    b) end_d é anterior a start_d (fim antes do início: sinal de digitação);
    c) com o ano trocado, o fim fica igual ou depois do início.
    Em qualquer outro caso, devolve end_d sem mudança.
    """
    if not start_d or not end_d or not pub_dt:
        return end_d
    if start_d.year == pub_dt.year and end_d < start_d:
        try:
            end_corrigido = end_d.replace(year=pub_dt.year)
        except ValueError:
            return end_d
        if end_corrigido >= start_d:
            return end_corrigido
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
    descartados_prefiltro = []
    rascunhos_duplicados_registrados = set()
    ids_publicados = {str(p["id"]) for p in processos_publicados if p}
    titulos_publicados = {
        _normalizar_titulo_dedup((p.get("title") or {}).get("translation") or "")
        for p in processos_publicados if p
    }
    publicados_para_dedup = [
        {
            "id": str(p["id"]),
            "titulo_raw": ((p.get("title") or {}).get("translation") or "").strip(),
            "orgao_norm": _normalizar_orgao_dedup(_extrair_orgao_bruto(p)),
            "palavras": _palavras_significativas_titulo((p.get("title") or {}).get("translation") or ""),
        }
        for p in processos_publicados if p
    ]

    for pt in tipos_processos:
        if not pt:
            continue
        nome_tipo = (pt.get("title") or {}).get("translation") or "Processo Participativo"
        for proc in (pt.get("processes") or []):
            if not proc:
                continue
            pid = str(proc["id"])
            titulo_raw = ((proc.get("title") or {}).get("translation") or "").strip()
            t_proc = _normalizar_titulo_dedup(titulo_raw)
            mapa_tipo_por_id[pid] = nome_tipo
            if pid in ids_publicados or t_proc in titulos_publicados:
                continue

            orgao_rasc = _extrair_orgao_bruto(proc)
            orgao_rasc_norm = _normalizar_orgao_dedup(orgao_rasc)
            melhor_pub_id = None
            melhor_sim = 0.0
            if orgao_rasc_norm:
                palavras_rasc = _palavras_significativas_titulo(titulo_raw)
                for pub in publicados_para_dedup:
                    if pub["orgao_norm"] != orgao_rasc_norm:
                        continue
                    uniao = palavras_rasc | pub["palavras"]
                    sim = (len(palavras_rasc & pub["palavras"]) / len(uniao)) if uniao else 0.0
                    if sim >= LIMIAR_SEMELHANCA_RASCUNHO and sim > melhor_sim:
                        melhor_sim = sim
                        melhor_pub_id = pub["id"]

            if melhor_pub_id is not None:
                if pid not in rascunhos_duplicados_registrados:
                    rascunhos_duplicados_registrados.add(pid)
                    descartados_prefiltro.append({
                        "origem": "PRE-FILTRO (RASCUNHO)",
                        "id": pid,
                        "orgao": orgao_rasc,
                        "titulo": higienizar_titulo_portal(titulo_raw),
                        "motivo": f"rascunho duplicado do publicado #{melhor_pub_id} (semelhança {melhor_sim:.2f})",
                        "url": f"{BASE_URL}/processes/{proc.get('slug', '')}",
                    })
                continue

            rascunhos_por_id[pid] = (proc, nome_tipo)

    hoje = date.today()
    agora_lim = datetime.now().astimezone() - timedelta(hours=48)  # Janela estrita de 48h a partir da data de publicação
    limite_rascunho = datetime.now().astimezone() - timedelta(days=10)
    exclusoes = carregar_exclusoes_participativo()

    candidatos = []

    # 1. Processa todos os publicados oficialmente
    for p in processos_publicados:
        if not p:
            continue
        item = normalizar_processo(p, mapa_tipo_por_id.get(str(p["id"]), "Consulta / Processo"), publicado=True, hoje=hoje, agora_lim_48h=agora_lim)
        if item and item["relevante_bruto"] and item["status_ciclo"] != "EXPIRADO_ANTIGO":
            if item.get("dias_restantes") is not None and item["dias_restantes"] > 730:
                descartados_prefiltro.append({
                    "origem": "PRE-FILTRO (PRAZO)",
                    "id": item["id"],
                    "orgao": item["orgao_informado"],
                    "titulo": item["titulo"],
                    "motivo": f"Prazo interminável ({item['dias_restantes']} dias restantes; página permanente sem janela ativa) — decisão de 23/11/2026",
                    "url": item["url"],
                })
                continue
            bloco_exc = f"{item['titulo']} | {item['subtitulo']} | {item['orgao_informado']} | {item['descricao_texto'][:600]}"
            motivo_exc = verificar_exclusao_participativo(bloco_exc, exclusoes)
            if motivo_exc:
                descartados_prefiltro.append({
                    "origem": "PRE-FILTRO",
                    "id": item["id"],
                    "orgao": item["orgao_informado"],
                    "titulo": item["titulo"],
                    "motivo": motivo_exc,
                    "url": item["url"],
                })
                continue
            candidatos.append(item)

    # 2. Processa os rascunhos/pré-publicação criados ou atualizados nos últimos 10 dias
    for pid, (proc, nome_tipo) in rascunhos_por_id.items():
        upd_dt = parse_iso_datetime(proc.get("updatedAt") or proc.get("createdAt"))
        if not upd_dt or upd_dt < limite_rascunho:
            continue
        item = normalizar_processo(proc, nome_tipo, publicado=False, hoje=hoje, agora_lim_48h=agora_lim)
        if item and item["relevante_bruto"]:
            bloco_exc = f"{item['titulo']} | {item['subtitulo']} | {item['orgao_informado']} | {item['descricao_texto'][:600]}"
            motivo_exc = verificar_exclusao_participativo(bloco_exc, exclusoes)
            if motivo_exc:
                descartados_prefiltro.append({
                    "origem": "PRE-FILTRO (RASCUNHO)",
                    "id": item["id"],
                    "orgao": item["orgao_informado"],
                    "titulo": item["titulo"],
                    "motivo": motivo_exc,
                    "url": item["url"],
                })
                continue
            candidatos.append(item)

    registrar_descartados_participativo(descartados_prefiltro, modo="w")
    if descartados_prefiltro:
        print(f"   -> {len(descartados_prefiltro)} processo(s) retido(s) no pré-filtro determinístico (log_descartados_participativo.txt).")

    # 3. Complementa com portais próprios de Agências Reguladoras (ANTT ParticipANTT e ANTAQ Gov.br), deduplicando
    try:
        extras_agencias = coletar_complemento_agencias(hoje=hoje, agora_lim_48h=agora_lim)
        for ext in extras_agencias:
            duplicado = False
            num_ext = (ext.get("_num_norma") or "").strip().lower()
            org_ext = (ext.get("orgao_informado") or "").split()[0].lower()
            url_ext = (ext.get("url") or "").strip().rstrip("/").lower()
            tipo_ext = (ext.get("tipo_catalogo") or "").strip().lower()
            eh_tomada_ext = "tomada" in tipo_ext
            for cand in candidatos:
                tit_c = (cand.get("titulo") or "").lower()
                org_c = (cand.get("orgao_informado") or "").lower()
                url_c = (cand.get("url") or "").strip().rstrip("/").lower()
                tipo_c = (cand.get("tipo_catalogo") or "").strip().lower()
                eh_tomada_c = ("tomada" in tipo_c) or ("tomada de subs" in tit_c)
                mesmo_url = bool(url_ext and url_c and url_ext == url_c)
                mesmo_num_orgao = bool(
                    num_ext and num_ext in tit_c and org_ext in (tit_c + " " + org_c)
                    and (eh_tomada_ext == eh_tomada_c)
                )
                if mesmo_url or mesmo_num_orgao:
                    # Mescla documentos caso já exista no Brasil Participativo ou em outro bloco
                    urls_existentes = {d["url"] for d in cand.get("documentos", [])}
                    for d_ext in ext.get("documentos", []):
                        if d_ext["url"] not in urls_existentes:
                            cand.setdefault("documentos", []).append(d_ext)
                    duplicado = True
                    break
            if not duplicado:
                candidatos.append(ext)
    except Exception as e:
        print(f"   [Aviso] Falha parcial ao coletar portais próprios de ANTT/ANTAQ: {e}")

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
        -int(str(x["id"])) if str(x["id"]).isdigit() else 0
    ))

    return candidatos


def _url_para_api_govbr_antaq(url: str) -> str:
    """Converte URL pública do portal gov.br/antaq para o endpoint JSON ++api++ do Plone/Volto."""
    if "/++api++/" in url:
        return url
    return url.replace("https://www.gov.br/antaq/", "https://www.gov.br/antaq/++api++/", 1)


def _extrair_links_slate_volto(node, saida: list):
    """Percorre recursivamente nós Slate do Volto e coleta tuplas (texto, url)."""
    if isinstance(node, dict):
        if node.get("type") == "link" and isinstance(node.get("data"), dict):
            u = (node["data"].get("url") or "").strip()
            if u:
                txt = "".join(
                    c.get("text", "") for c in (node.get("children") or []) if isinstance(c, dict)
                ).strip()
                saida.append((txt, u))
        for v in node.values():
            _extrair_links_slate_volto(v, saida)
    elif isinstance(node, list):
        for item in node:
            _extrair_links_slate_volto(item, saida)


def _buscar_json_govbr_antaq(url_publica: str, headers: dict, ctx, timeout: int = 20):
    """
    Consulta a interface JSON ++api++ de uma página do gov.br/antaq.
    Se o endpoint redirecionar para HTML (ex.: página movida para subpasta),
    resolve a URL final e consulta ++api++ no endereço definitivo.
    Retorna (dict_json_ou_None, url_final_publica, html_fallback_ou_None).
    """
    hdr_json = dict(headers)
    hdr_json["Accept"] = "application/json"
    url_api = _url_para_api_govbr_antaq(url_publica)
    req = urllib.request.Request(url_api, headers=hdr_json)
    with urllib.request.urlopen(req, context=ctx, timeout=timeout) as r:
        final_u = r.geturl()
        raw = r.read().decode("utf-8", errors="replace")
        ct = (r.headers.get("Content-Type") or "").lower()

    if "json" in ct or raw.lstrip().startswith("{"):
        try:
            return json.loads(raw), url_publica, None
        except Exception:
            pass

    # Se redirecionou para URL pública diferente sem ++api++, tenta ++api++ na URL final
    if "gov.br/antaq/" in final_u and "/++api++/" not in final_u and final_u != url_publica:
        req2 = urllib.request.Request(_url_para_api_govbr_antaq(final_u), headers=hdr_json)
        with urllib.request.urlopen(req2, context=ctx, timeout=timeout) as r2:
            raw2 = r2.read().decode("utf-8", errors="replace")
            ct2 = (r2.headers.get("Content-Type") or "").lower()
        if "json" in ct2 or raw2.lstrip().startswith("{"):
            try:
                return json.loads(raw2), final_u, None
            except Exception:
                pass
        return None, final_u, raw2

    return None, final_u, raw


def _extrair_texto_e_links_volto(dados_json: dict):
    """Extrai texto ordenado e links de blocos Slate e HTML de uma página Volto/Plone."""
    partes = []
    links = []
    blocks = dados_json.get("blocks") or {}
    ordem = (dados_json.get("blocks_layout") or {}).get("items") or list(blocks.keys())
    for bid in ordem:
        b = blocks.get(bid)
        if not isinstance(b, dict):
            continue
        tipo = b.get("@type")
        if tipo == "slate":
            pt = (b.get("plaintext") or "").strip()
            if pt:
                partes.append(pt)
            _extrair_links_slate_volto(b.get("value", []), links)
        elif tipo == "html" and b.get("html"):
            s = BeautifulSoup(b["html"], "html.parser")
            txt_h = re.sub(r"\s+", " ", s.get_text(" ", strip=True))
            if txt_h:
                partes.append(txt_h)
            for a in s.find_all("a", href=True):
                links.append((a.get_text(" ", strip=True), a["href"].strip()))
    return "\n".join(partes), links


def _parse_data_br(d_str: str):
    try:
        dd, mm, yyyy = map(int, d_str.split("/"))
        return date(yyyy, mm, dd)
    except Exception:
        return None


def _extrair_prazos_tomada_antaq(texto_subpagina: str):
    """
    Extrai datas oficiais de início e fim (inclusive prorrogação) exclusivamente
    de frases de período/prazo do aviso oficial da tomada de subsídios.
    Nunca estima ou inventa data. Retorna (d_ini, d_fim, trecho_origem).
    """
    if not texto_subpagina:
        return None, None, ""
    d_ini = None
    d_fim = None
    trechos = []

    m_per = re.search(
        r"per[ií]odo\s+de\s+(\d{2}/\d{2}/\d{4})\s+a\s+(\d{2}/\d{2}/\d{4})",
        texto_subpagina,
        re.I,
    )
    if m_per:
        d_ini = _parse_data_br(m_per.group(1))
        d_fim = _parse_data_br(m_per.group(2))
        trechos.append(m_per.group(0).strip())

    for m_prorr in re.finditer(
        r"prorroga\w*[^\.\n]{0,140}?(\d{2}/\d{2}/\d{4})",
        texto_subpagina,
        re.I,
    ):
        d_cand = _parse_data_br(m_prorr.group(1))
        if d_cand and (d_fim is None or d_cand > d_fim):
            d_fim = d_cand
            trechos.append(m_prorr.group(0).strip())

    if d_fim is None:
        for m_ate in re.finditer(
            r"at[eé]\s+(?:[àa]s\s+\d{1,2}h\d{2}\s+do\s+dia\s+|o\s+dia\s+)?(\d{2}/\d{2}/\d{4})",
            texto_subpagina,
            re.I,
        ):
            d_cand = _parse_data_br(m_ate.group(1))
            if d_cand and (d_fim is None or d_cand > d_fim):
                d_fim = d_cand
                trechos.append(m_ate.group(0).strip())

    return d_ini, d_fim, " | ".join(trechos)


def coletar_complemento_agencias(hoje: date, agora_lim_48h: datetime) -> list:
    """Coleta processos abertos nos portais próprios da ANTT (ParticipANTT) e ANTAQ (Gov.br)."""
    resultados = []
    ctx = criar_contexto_ssl()
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) RadarParticipativo/1.0"}

    # A) ANTT — API JSON ParticipANTT
    try:
        url_antt = "https://participantt.antt.gov.br/api/ManterEvento?Situacao=2&PageSize=50&PageNumber=1"
        req = urllib.request.Request(url_antt, headers=headers)
        with urllib.request.urlopen(req, context=ctx, timeout=20) as r:
            dados_antt = json.loads(r.read().decode("utf-8", errors="replace"))
        itens_antt = ((dados_antt.get("result") or {}).get("items")) or []
        for ev in itens_antt:
            ev_id = ev.get("id")
            tipo_ev = (ev.get("tipoEvento") or "Processo Participativo").strip()
            numero = (ev.get("numero") or "").strip()
            desc_html = ev.get("descricao") or ""
            desc_txt, links_html = extrair_texto_e_links_html(desc_html)
            if not desc_txt:
                continue
            # Exclui planos de dados abertos administrativos sem relação com outorgas/regulação
            if "plano de dados abertos" in desc_txt.lower():
                continue
            if not REGEX_TEMAS_INTERESSE.search(f"{tipo_ev} {numero} {desc_txt}"):
                continue

            d_ini = parse_iso_date((ev.get("dtInicioValidade") or "")[:10]) or hoje
            d_fim = parse_iso_date((ev.get("dtFimValidade") or "")[:10])
            dias_rest = (d_fim - hoje).days if d_fim else None
            if dias_rest is not None and dias_rest < -3:
                continue

            lanc_48h = bool(0 <= (hoje - d_ini).days <= 2)
            if dias_rest is not None and dias_rest < 0:
                st_ciclo = "ENCERRADO_RECENTE"
            elif lanc_48h:
                st_ciclo = "LANCADO_48H"
            elif dias_rest is not None and dias_rest <= 7:
                st_ciclo = "PRAZO_URGENTE"
            else:
                st_ciclo = "ABERTO"

            url_ev = f"https://participantt.antt.gov.br/Site/AudienciaPublica/ConsultarAvisoAudienciaPublica?idEvento={ev_id}"
            docs = [{
                "rotulo": "📝 Abrir e Contribuir no ParticipANTT",
                "url": url_ev,
                "categoria": "CONTRIBUIR",
            }] + links_html

            resumo_tit = desc_txt.split(".")[0][:140].strip()
            titulo_fmt = f"ANTT — {tipo_ev} nº {numero}: {resumo_tit}"

            resultados.append({
                "id": f"900{ev_id}",
                "_num_norma": numero,
                "slug": f"antt-{tipo_ev.lower().replace(' ', '-')}-{numero.replace('/', '-')}",
                "url": url_ev,
                "publicado": True,
                "tipo_catalogo": tipo_ev,
                "titulo": titulo_fmt,
                "subtitulo": f"Portal ParticipANTT • Período: {ev.get('periodoValidade', '')}",
                "descricao_texto": desc_txt[:2500],
                "orgao_informado": "ANTT (ParticipANTT)",
                "contato": "participantt.antt.gov.br",
                "data_publicacao": f"{d_ini.isoformat()} 09:00",
                "data_publicacao_br": d_ini.strftime("%d/%m/%Y"),
                "data_publicacao_iso": f"{d_ini.isoformat()}T09:00:00-03:00",
                "data_atualizacao_iso": f"{d_ini.isoformat()}T09:00:00",
                "data_inicio_br": d_ini.strftime("%d/%m/%Y"),
                "data_fim_br": d_fim.strftime("%d/%m/%Y") if d_fim else "—",
                "data_fim_iso": d_fim.isoformat() if d_fim else "",
                "dias_restantes": dias_rest,
                "lancado_48h": lanc_48h,
                "status_ciclo": st_ciclo,
                "documentos": docs,
                "relevante_bruto": True,
            })
    except Exception as e:
        print(f"   [Aviso] Coleta ANTT ParticipANTT: {e}")

    # B) ANTAQ — Portal Gov.br Audiências Públicas em Andamento
    try:
        url_antaq = "https://www.gov.br/antaq/pt-br/acesso-a-informacao/participacao-social/audiencias-e-consultas-publicas/audiencias-publicas-em-andamento"
        req = urllib.request.Request(url_antaq, headers=headers)
        with urllib.request.urlopen(req, context=ctx, timeout=20) as r:
            html_antaq = r.read().decode("utf-8", errors="replace")
        soup = BeautifulSoup(html_antaq, "html.parser")
        core = soup.select_one("#content-core") or soup

        for idx_p, p_tag in enumerate(core.find_all("p"), 1):
            txt = re.sub(r"\s{2,}", " ", p_tag.get_text(" ", strip=True))
            if "2026" not in txt or "audiência pública" not in txt.lower():
                continue
            a_tag = p_tag.find("a", href=True)
            href = a_tag["href"].strip() if a_tag else ""
            if not href or "gov.br/antaq" not in href:
                continue

            m_num = re.search(r"(\d{1,2}/2026)", txt)
            num_ap = m_num.group(1) if m_num else f"{idx_p}/2026"

            # Inspeciona a subpágina para extrair datas de início/fim e anexos PDF
            req_sub = urllib.request.Request(href, headers=headers)
            with urllib.request.urlopen(req_sub, context=ctx, timeout=15) as r_sub:
                sub_html = r_sub.read().decode("utf-8", errors="replace")
            sub_soup = BeautifulSoup(sub_html, "html.parser").select_one("#content-core") or BeautifulSoup(sub_html, "html.parser")
            sub_txt = re.sub(r"\s{2,}", " ", sub_soup.get_text(" ", strip=True))

            datas_br = re.findall(r"\b(\d{2}/\d{2}/2026)\b", sub_txt)
            datas_obj = []
            for d_s in datas_br:
                try:
                    dd, mm, yyyy = map(int, d_s.split("/"))
                    datas_obj.append(date(yyyy, mm, dd))
                except Exception:
                    pass
            if not datas_obj:
                continue
            d_ini = min(datas_obj)
            d_fim = max(datas_obj)
            dias_rest = (d_fim - hoje).days
            if dias_rest < -3:
                continue

            lanc_48h = bool(0 <= (hoje - d_ini).days <= 2)
            if dias_rest < 0:
                st_ciclo = "ENCERRADO_RECENTE"
            elif lanc_48h:
                st_ciclo = "LANCADO_48H"
            elif dias_rest <= 7:
                st_ciclo = "PRAZO_URGENTE"
            else:
                st_ciclo = "ABERTO"

            docs_antaq = []
            vistas_u = set()
            for a_doc in sub_soup.find_all("a", href=True):
                u_doc = a_doc["href"].strip()
                t_doc = a_doc.get_text(" ", strip=True) or "Documento ANTAQ"
                if not u_doc.startswith("http") or u_doc in vistas_u:
                    continue
                if "gov.br/antaq/pt-br/acesso-a-informacao" not in u_doc and not u_doc.lower().endswith(".pdf"):
                    continue
                if u_doc.rstrip("/").endswith("participacao-social") or u_doc.rstrip("/").endswith("antaq/pt-br"):
                    continue
                vistas_u.add(u_doc)
                cat_d = classificar_link(u_doc, t_doc)
                docs_antaq.append({
                    "rotulo": _formatar_rotulo_link(t_doc, u_doc, cat_d),
                    "url": u_doc,
                    "categoria": cat_d,
                })

            num_limpo = int(re.sub(r"\D", "", num_ap.split("/")[0]) or idx_p)
            resultados.append({
                "id": f"910{num_limpo:03d}",
                "_num_norma": num_ap,
                "slug": f"antaq-ap-{num_ap.replace('/', '-')}",
                "url": href,
                "publicado": True,
                "tipo_catalogo": "Audiência Pública",
                "titulo": f"ANTAQ — {txt[:180]}",
                "subtitulo": f"Portal ANTAQ • Contribuições: {d_ini.strftime('%d/%m/%Y')} a {d_fim.strftime('%d/%m/%Y')}",
                "descricao_texto": f"{txt}\n\n{sub_txt[:1800]}",
                "orgao_informado": "ANTAQ (Portal Próprio)",
                "contato": "antaq.gov.br",
                "data_publicacao": f"{d_ini.isoformat()} 09:00",
                "data_publicacao_br": d_ini.strftime("%d/%m/%Y"),
                "data_publicacao_iso": f"{d_ini.isoformat()}T09:00:00-03:00",
                "data_atualizacao_iso": f"{d_ini.isoformat()}T09:00:00",
                "data_inicio_br": d_ini.strftime("%d/%m/%Y"),
                "data_fim_br": d_fim.strftime("%d/%m/%Y"),
                "data_fim_iso": d_fim.isoformat(),
                "dias_restantes": dias_rest,
                "lancado_48h": lanc_48h,
                "status_ciclo": st_ciclo,
                "documentos": docs_antaq,
                "relevante_bruto": True,
            })
    except Exception as e:
        print(f"   [Aviso] Coleta ANTAQ Portal Próprio: {e}")

    # C) ANTAQ — Tomadas de Subsídios em Andamento (API JSON ++api++ do Gov.br, com fallback HTML)
    url_lista_ts = (
        "https://www.gov.br/antaq/pt-br/acesso-a-informacao/participacao-social/"
        "tomada-de-subsidio-1/tomada-de-subsidios-em-andamento"
    )
    try:
        dados_lista, _, html_lista_fb = _buscar_json_govbr_antaq(url_lista_ts, headers, ctx, timeout=20)
        entradas_ts = []

        if isinstance(dados_lista, dict) and dados_lista.get("blocks"):
            blocks = dados_lista.get("blocks") or {}
            ordem = (dados_lista.get("blocks_layout") or {}).get("items") or list(blocks.keys())
            for bid in ordem:
                b = blocks.get(bid)
                if not isinstance(b, dict) or b.get("@type") != "slate":
                    continue
                pt = re.sub(r"\s+", " ", (b.get("plaintext") or "").replace("\xa0", " ")).strip()
                if not pt or "tomada de subsídios" not in pt.lower():
                    continue
                links_bloco = []
                _extrair_links_slate_volto(b.get("value", []), links_bloco)
                href = next((u for _, u in links_bloco if u.startswith("http")), "")
                if href:
                    entradas_ts.append((pt, href))
        elif html_lista_fb:
            soup_ts = BeautifulSoup(html_lista_fb, "html.parser")
            core_ts = soup_ts.select_one("#content-core") or soup_ts
            for tag in core_ts.find_all(["p", "div", "li"]):
                pt = re.sub(r"\s+", " ", tag.get_text(" ", strip=True).replace("\xa0", " ")).strip()
                if "tomada de subsídios" not in pt.lower():
                    continue
                a_t = tag.find("a", href=True)
                href = a_t["href"].strip() if a_t else ""
                if href.startswith("http") and "tomada-de-subsidio" in href.lower():
                    entradas_ts.append((pt, href))

        if not entradas_ts:
            print("   [Aviso] Coleta ANTAQ Tomadas de Subsídios: nenhuma tomada encontrada na página oficial.")

        vistas_ts = set()
        for idx_ts, (texto_item, href_item) in enumerate(entradas_ts, 1):
            m_num = re.search(r"n[ºo°]?\s*(\d{1,3}/\d{4})(?:\s*[-–]\s*([A-Z]{2,10}))?", texto_item, re.I)
            num_ts = m_num.group(1) if m_num else f"{idx_ts}/{hoje.year}"
            unidade_ts = (m_num.group(2) or "SRG").upper() if m_num else "SRG"
            chave_ts = (num_ts.lower(), href_item.rstrip("/").lower())
            if chave_ts in vistas_ts:
                continue
            vistas_ts.add(chave_ts)

            # Objeto literal da página oficial (sem alterar o texto da ANTAQ)
            objeto_lit = re.sub(
                r"^Tomada\s+de\s+Subs[íi]dios\s+n[ºo°]?\s*\d{1,3}/\d{4}(?:\s*[-–]\s*[A-Z]{2,10})?\s*[-–:]\s*",
                "",
                texto_item,
                flags=re.I,
            ).strip() or texto_item
            # Remove eventual endereço de e-mail por regra de privacidade
            objeto_lit = re.sub(r"[\w\.-]+@[\w\.-]+\.\w+", "[contato no portal]", objeto_lit)

            # Inspeciona a subpágina oficial da tomada para obter prazo oficial e links de documentos
            url_oficial_final = href_item
            d_ini = None
            d_fim = None
            docs_ts = []
            try:
                sub_json, url_oficial_final, sub_html_fb = _buscar_json_govbr_antaq(href_item, headers, ctx, timeout=20)
                sub_txt = ""
                sub_links = []
                if isinstance(sub_json, dict) and sub_json.get("blocks"):
                    sub_txt, sub_links = _extrair_texto_e_links_volto(sub_json)
                elif sub_html_fb:
                    s_fb = BeautifulSoup(sub_html_fb, "html.parser")
                    sub_txt = re.sub(r"\s+", " ", s_fb.get_text(" ", strip=True))
                    for a_d in s_fb.find_all("a", href=True):
                        sub_links.append((a_d.get_text(" ", strip=True), a_d["href"].strip()))
                d_ini, d_fim, _ = _extrair_prazos_tomada_antaq(sub_txt)

                urls_docs_vistas = {url_oficial_final.rstrip("/").lower()}
                for rot_d, u_d in sub_links:
                    if not u_d or not u_d.startswith("http") or u_d.startswith("mailto:"):
                        continue
                    u_norm = u_d.rstrip("/").lower()
                    if u_norm in urls_docs_vistas:
                        continue
                    if u_norm.endswith("gov.br/antaq/pt-br") or u_norm.endswith("participacao-social"):
                        continue
                    urls_docs_vistas.add(u_norm)
                    if "forms.cloud.microsoft" in u_norm or "forms.office.com" in u_norm:
                        docs_ts.append({
                            "rotulo": "📝 Enviar Contribuição (Formulário ANTAQ)",
                            "url": u_d,
                            "categoria": "CONTRIBUIR",
                        })
                    elif "sei.antaq.gov.br" in u_norm:
                        if not any(d["categoria"] == "SEI" for d in docs_ts):
                            rot_sei = f"🗂️ Processo SEI {rot_d}" if rot_d and "." in rot_d else "🗂️ Processo SEI ANTAQ"
                            docs_ts.append({
                                "rotulo": rot_sei[:80],
                                "url": u_d,
                                "categoria": "SEI",
                            })
                    elif ".pdf" in u_norm or "@@display-file" in u_norm or "youtu" in u_norm:
                        cat_d = classificar_link(u_d, rot_d or "Documento ANTAQ")
                        if cat_d == "DOCUMENTO" and (".pdf" in u_norm or "@@display-file" in u_norm):
                            cat_d = "ANEXO_PDF"
                        docs_ts.append({
                            "rotulo": _formatar_rotulo_link(rot_d or "Documento ANTAQ", u_d, cat_d),
                            "url": u_d,
                            "categoria": cat_d,
                        })
            except Exception as e_sub:
                print(f"   [Aviso] Coleta ANTAQ Tomada {num_ts} ({href_item}): falha ao ler subpágina ({e_sub}); seguindo com prazo a conferir.")

            if d_fim is not None:
                dias_rest = (d_fim - hoje).days
                if dias_rest < -3:
                    continue
                lanc_48h = bool(d_ini and 0 <= (hoje - d_ini).days <= 2)
                if dias_rest < 0:
                    st_ciclo = "ENCERRADO_RECENTE"
                elif lanc_48h:
                    st_ciclo = "LANCADO_48H"
                elif dias_rest <= 7:
                    st_ciclo = "PRAZO_URGENTE"
                else:
                    st_ciclo = "ABERTO"
                data_ini_br = d_ini.strftime("%d/%m/%Y") if d_ini else "—"
                data_fim_br = d_fim.strftime("%d/%m/%Y")
                data_fim_iso = d_fim.isoformat()
                data_pub_ref = d_ini or hoje
                subtitulo_ts = (
                    f"Portal ANTAQ ({unidade_ts}) • Contribuições: {data_ini_br} a {data_fim_br}"
                    if d_ini else f"Portal ANTAQ ({unidade_ts}) • Contribuições até {data_fim_br}"
                )
                texto_janela_ts = ""
            else:
                dias_rest = None
                lanc_48h = False
                st_ciclo = "PRAZO_NO_ATO"
                data_ini_br = "—"
                data_fim_br = "Prazo a conferir"
                data_fim_iso = ""
                data_pub_ref = hoje
                subtitulo_ts = f"Portal ANTAQ ({unidade_ts}) • Prazo a conferir na página oficial"
                texto_janela_ts = "Prazo a conferir na página oficial"

            partes_num = num_ts.split("/")
            num_int = int(re.sub(r"\D", "", partes_num[0]) or idx_ts)
            ano_2d = re.sub(r"\D", "", partes_num[1])[-2:] if len(partes_num) > 1 else str(hoje.year)[-2:]
            item_ts = {
                "id": f"92{ano_2d}{num_int:03d}",
                "_num_norma": num_ts,
                "slug": f"antaq-ts-{num_ts.replace('/', '-')}",
                "url": url_oficial_final,
                "publicado": True,
                "tipo_catalogo": "Tomada de Subsídios",
                "titulo": f"ANTAQ — Tomada de Subsídios nº {num_ts}-{unidade_ts}: {objeto_lit[:180]}",
                "subtitulo": subtitulo_ts,
                "descricao_texto": objeto_lit,
                "orgao_informado": f"ANTAQ / {unidade_ts}",
                "contato": "antaq.gov.br",
                "data_publicacao": f"{data_pub_ref.isoformat()} 09:00",
                "data_publicacao_br": data_pub_ref.strftime("%d/%m/%Y") if d_ini else "—",
                "data_publicacao_iso": f"{data_pub_ref.isoformat()}T09:00:00-03:00" if d_ini else "",
                "data_atualizacao_iso": f"{data_pub_ref.isoformat()}T09:00:00",
                "data_inicio_br": data_ini_br,
                "data_fim_br": data_fim_br,
                "data_fim_iso": data_fim_iso,
                "dias_restantes": dias_rest,
                "lancado_48h": lanc_48h,
                "status_ciclo": st_ciclo,
                "documentos": docs_ts,
                "relevante_bruto": True,
            }
            if texto_janela_ts:
                item_ts["texto_janela"] = texto_janela_ts
            resultados.append(item_ts)
    except Exception as e:
        print(f"   [Aviso] Coleta ANTAQ Tomadas de Subsídios: {e}")

    return resultados


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
    agora_atual = datetime.now().astimezone()
    lancado_48h = bool(publicado and pub_dt and agora_lim_48h <= pub_dt <= agora_atual)

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
        "data_publicacao_iso": pub_dt.isoformat() if pub_dt else "",
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

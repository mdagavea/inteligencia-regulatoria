import os
import re
import socket
import imaplib
import email
from email.header import decode_header
from email.utils import parsedate_to_datetime
import urllib.parse
import urllib3
import requests
import feedparser
from bs4 import BeautifulSoup
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
load_dotenv()

VIP_SITES_QUERY = (
    "(site:valor.globo.com OR site:oglobo.globo.com OR site:folha.uol.com.br "
    "OR site:estadao.com.br OR site:broadcast.com.br OR site:agenciainfra.com "
    "OR site:jota.info OR site:cnseg.org.br OR site:reuters.com OR \"Reuters\")"
)

GMAIL_ALLOWED_SENDERS = [
    "capitalreset",
    "jota.info",
    "cnseg",
    "noticiasseguro",
    "mckinsey.com",
    "a16z",
    "substack.com",
    "jeffsu.org",
    "environmental-finance.com",
    "cfainstitute.org",
    "garp.com",
    "valor.globo.com",
    "estadao.com.br",
    "folha.uol.com.br",
    "oglobo.globo.com",
    # DESATIVADO (04/11/2026): boletim de assinante da Agencia iNFRA (infrajornalismo@/agenciainfra@agenciainfra.com) nao e fonte do clipping (conteudo pago).
    # "agenciainfra.com",
]


def clean_html(raw_html):
    if not raw_html:
        return ""
    text = BeautifulSoup(raw_html, "html.parser").get_text(" ", strip=True)
    # Remove sequências de caracteres invisíveis de espaçamento de e-mail (\u200c, \u034f, etc.)
    text = re.sub(r"[\u200b-\u200f\u202a-\u202e\u034f\ufeff]+", "", text)
    text = re.sub(r"\s{2,}", " ", text).strip()
    return text


SOCIAL_MEDIA_BLOCKLIST = (
    "instagram.com",
    "facebook.com",
    "tiktok.com",
    "x.com",
    "twitter.com",
    "threads.net",
    "pinterest.com",
)


def fetch_google_news(query, when="24h", max_results=6):
    """Coleta notícias no Google News RSS com filtros de tempo e bloqueio de redes sociais."""
    encoded = urllib.parse.quote(f"{query} when:{when}")
    url = f"https://news.google.com/rss/search?q={encoded}&hl=pt-BR&gl=BR&ceid=BR:pt-419"
    feed = feedparser.parse(url)
    items = []
    for entry in feed.entries:
        source_obj = entry.get("source", {})
        source = source_obj.get("title", "")
        source_href = (source_obj.get("href") or "").lower().strip()
        title = entry.get("title", "")
        if not source and " - " in title:
            source = title.split(" - ")[-1]

        # Filtra redes sociais ou origens sem HTTPS válido (sem perder vaga no lote)
        if source_href and not source_href.startswith("https://"):
            continue
        if any(dom in source_href for dom in SOCIAL_MEDIA_BLOCKLIST):
            continue
        if source.strip().lower() in ("instagram", "facebook", "tiktok", "threads"):
            continue

        link = entry.get("link", "").strip()
        if not link.startswith("https://news.google.com/"):
            continue

        items.append({
            "title": title,
            "link": link,
            "published": entry.get("published", ""),
            "source": source or "Fonte Web",
            "summary": clean_html(entry.get("summary", "")),
        })
        if len(items) >= max_results:
            break
    return items


def fetch_direct_rss_feeds(max_per_feed=10):
    """Lê feeds RSS diretos de veículos estratégicos (Agência iNFRA, Capital Reset, JOTA, a16z) — Degrau 1."""
    direct_feeds = [
        {
            "source": "Agência iNFRA",
            "url": "https://www.agenciainfra.com/blog/feed/",
            "vertical": "infra",
            "verify_ssl": False,
            "max": 15,
        },
        {
            "source": "Capital Reset",
            "url": "https://capitalreset.uol.com.br/feed/",
            "vertical": "carbono",
            "verify_ssl": False,  # Contorna erro de cadeia SSL intermediária do servidor UOL
            "max": max_per_feed,
        },
        {
            "source": "JOTA",
            "url": "https://www.jota.info/feed",
            "vertical": "infra",
            "verify_ssl": True,
            "max": 10,
        },
        {
            "source": "a16z News",
            "url": "https://www.a16z.news/feed",
            "vertical": "tech",
            "verify_ssl": True,
            "max": 6,
        },
    ]

    results = []
    for cfg in direct_feeds:
        try:
            r = requests.get(
                cfg["url"],
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
                verify=cfg["verify_ssl"],
                timeout=10,
            )
            if r.status_code != 200:
                continue
            feed = feedparser.parse(r.content)
            for entry in feed.entries[: cfg["max"]]:
                results.append({
                    "title": entry.get("title", ""),
                    "link": entry.get("link", ""),
                    "published": entry.get("published", entry.get("updated", "")),
                    "source": cfg["source"],
                    "summary": clean_html(entry.get("summary", entry.get("description", "")))[:450],
                    "vertical_original": cfg["vertical"],
                })
        except Exception as e:
            print(f"   [Aviso] Falha ao ler feed direto {cfg['source']}: {e}")
    return results


SIGLAS_PRESERVAR_TITULO = {
    "ANTT", "ANTAQ", "ANAC", "ANEEL", "ANP", "ANA", "ANM", "TCU", "STF", "STJ", "CGU",
    "MPOR", "MME", "MDIC", "MCID", "MMA", "MAPA", "AGU", "BNDES", "CVM", "SUSEP", "CNSEG",
    "PPP", "PPPS", "PPI", "PND", "PAC", "PCH", "PCHS", "SAF", "DOU", "EVTEA", "EVTEAS",
    "PL", "PLS", "PLP", "PEC", "MP", "IBS", "CBS", "IOF", "IR", "ICMS", "IPCA", "SELIC",
    "FIDC", "LCI", "LCA", "REIDI", "FMM", "CDFMM", "TUP", "TUPS", "ONS", "EPE", "CCEE",
    "CNPE", "CADE", "IBAMA", "DNIT", "INFRA", "S.A.", "BR", "SP", "RJ", "MG", "RS", "PR",
    "SC", "BA", "PE", "CE", "PA", "AM", "MT", "MS", "GO", "DF", "ES", "MA", "PI", "RN",
    "PB", "AL", "SE", "TO", "RO", "AC", "AP", "RR", "EUA", "UE", "COP", "COP30", "COP31",
    "ESG", "CBIO", "CBIOS", "SBCE", "MRV", "B3", "ABCR", "ABDIB", "ABEPAM", "ABRATEC",
    "ANBIMA", "CNH", "PF", "TI", "IA", "PIB", "SPE", "AIR", "PMR",
}


def _decodificar_header_email(val: str) -> str:
    if not val:
        return ""
    partes = decode_header(val)
    saida = []
    for texto, enc in partes:
        if isinstance(texto, bytes):
            saida.append(texto.decode(enc or "utf-8", errors="replace"))
        else:
            saida.append(str(texto))
    return "".join(saida).strip()


def _formatar_titulo_caixa_alta(titulo_bruto: str) -> str:
    """Converte títulos em CAIXA ALTA dos boletins da Agência iNFRA para formato editorial legível preservando siglas."""
    t = re.sub(r"\s+", " ", titulo_bruto or "").strip()
    if not t.isupper():
        return t
    minusculas = {
        "de", "da", "do", "das", "dos", "e", "em", "na", "no", "nas", "nos",
        "para", "por", "com", "sem", "sob", "sobre", "a", "o", "as", "os",
        "ao", "aos", "à", "às", "que", "se",
    }
    resultado = []
    for idx, p in enumerate(t.split(" ")):
        m = re.match(r"^([^\wÀ-ÿ]*)([\wÀ-ÿ\-\./]+)([^\wÀ-ÿ]*)$", p)
        if not m:
            resultado.append(p.lower())
            continue
        pref, miolo, suf = m.groups()
        miolo_up = miolo.upper()
        if miolo_up == "MPOR":
            formatada = "MPor"
        elif miolo_up == "PPPS":
            formatada = "PPPs"
        elif miolo_up == "PCHS":
            formatada = "PCHs"
        elif miolo_up == "EVTEAS":
            formatada = "EVTEAs"
        elif miolo_up in SIGLAS_PRESERVAR_TITULO or re.match(r"^(BR-\d+|R\$|\d+.*)$", miolo_up):
            formatada = miolo_up
        elif idx > 0 and miolo.lower() in minusculas:
            formatada = miolo.lower()
        else:
            formatada = miolo.capitalize()
        resultado.append(f"{pref}{formatada}{suf}")
    return " ".join(resultado)


def _classificar_vertical_boletim(titulo: str, resumo: str) -> str:
    texto = f"{titulo} {resumo}".lower()
    if any(k in texto for k in ["debênture", "debenture", "lei 12.431", "lei 14.801", "fidc", "mercado de capitais", "emissão de", "títulos incentivados", "anbima", "cvm", "reidi"]):
        return "divida"
    if any(k in texto for k in ["mercado de carbono", "cbio", "cbios", "saf ", "combustível sustentável", "probioqav", "fundo clima", "eco invest", "ecoinvest", "minerais críticos", "transição energética", "descarbonização", "cop31", "cop 31", "biometano"]):
        return "carbono"
    if any(k in texto for k in ["seguro garantia", "susep", "cnseg", "resseguro", "apólice", "sinistro"]):
        return "seguros"
    return "infra"


def _parse_boletim_agencia_infra(html_content: str, base_url: str, published_str: str = "", max_atos_dou: int = 10) -> list:
    """
    Desmembra o boletim de assinantes da Agência iNFRA (iNFRA Transportes / Saneamento & Cidades e iNFRAEnergia) em:
    1) Reportagens exclusivas de abertura (#1, #2, #3, #4);
    2) Atos estratégicos selecionados do Diário Oficial (#Diario), Agenda Regulatória (#Agenda) e Fique de Olho (#Fique),
       já com os links oficiais desembrulhados (.gov.br / in.gov.br / agenciainfra.com).
    """
    if not html_content:
        return []
    soup = BeautifulSoup(html_content, "html.parser")
    for bar in soup.select("#archiveBar, #awesomewrap, script, style"):
        bar.decompose()

    itens = []
    header_txt = soup.get_text(" ", strip=True)[:500].lower()
    escopo = "iNFRAEnergia" if "infraenergia" in header_txt else "iNFRA Transportes"
    fonte_label = f"Agência iNFRA ({escopo})"

    blocos_td = soup.select(".mcnTextContent")
    if not blocos_td:
        blocos_td = [soup]

    rep_idx = 0
    atos_candidatos = []
    atos_vistos = set()

    palavras_chave_atos = (
        "mpor", "portos e aeroportos", "ministério dos transportes", "antaq", "anac", "antt",
        "ppi", "pnd", "evtea", "debênture", "reidi", "arrendamento", "concessão", "concessões",
        "reequilíbrio", "fmm", "marinha mercante", "saf", "probioqav", "tcu", "secexconsenso",
        "ferrovi", "rodovi", "portuári", "aeroport", "tup", "hidrovi", "bndes", "aneel",
    )
    termos_rotina_ignorar = (
        "autorizou o diretor",
        "autoriza o afastamento",
        "viajar a ",
        "afastamento do país",
        "designa representantes",
        "consolida os membros titulares",
        "comissão gestora do plano diretor de logística",
    )
    termos_alta_prioridade = (
        "evtea", "debênture", "reidi", "ppi", "pnd", "portaria 530", "arrendamento",
        "concessão", "concessões", "leilão", "reequilíbrio", "consulta pública",
        "audiência pública", "tomada de subsídios", "saf", "probioqav", "tcu",
        "acórdão", "decreto", "tarif",
    )

    for td in blocos_td:
        td_copy = BeautifulSoup(str(td), "html.parser")
        for br in td_copy.find_all("br"):
            br.replace_with("\n")
        for blk in td_copy.find_all(["p", "div", "h1", "h2", "h3", "h4", "li"]):
            blk.insert_before("\n")
            blk.insert_after("\n")
        linhas = [re.sub(r"[ \t\xa0]+", " ", ln).strip() for ln in td_copy.get_text().splitlines()]
        linhas = [ln for ln in linhas if ln]

        # 1. Reportagem principal em CAIXA ALTA
        tit_cand = None
        inicio_idx = 0
        for i, ln in enumerate(linhas):
            if (
                len(ln) >= 28
                and ln.isupper()
                and not ln.startswith("TRAMITAÇÃO DE PROPOSTAS")
                and not ln.startswith("NOVAS PROPOSTAS")
                and "AGÊNCIA INFRA" not in ln
            ):
                tit_cand = ln
                inicio_idx = i + 1
                break

        if tit_cand:
            rep_idx += 1
            paragrafos = []
            for ln in linhas[inicio_idx:]:
                if "voltar para o topo" in ln.lower():
                    break
                if "da agência infra" in ln.lower() and len(ln) < 95:
                    continue
                if len(ln) > 45:
                    paragrafos.append(ln)
                if len(" ".join(paragrafos)) >= 390:
                    break
            resumo = " ".join(paragrafos)[:430].strip()
            if resumo:
                titulo_limpo = _formatar_titulo_caixa_alta(tit_cand)
                vert = _classificar_vertical_boletim(titulo_limpo, resumo)
                itens.append({
                    "title": titulo_limpo,
                    "link": f"{base_url}#{rep_idx}",
                    "published": published_str,
                    "source": fonte_label,
                    "summary": resumo,
                    "vertical_original": vert,
                })

        # 2. Itens estruturados de Diário Oficial (#Diario), Agenda e Fique de Olho (#Fique)
        raw_td_html = str(td)
        fragmentos_html = re.split(r"(?:<br\s*/?>\s*){1,}|</p>|<p[^>]*>", raw_td_html, flags=re.I)
        for frag in fragmentos_html:
            if "<strong>" not in frag.lower() and "<b>" not in frag.lower():
                continue
            f_soup = BeautifulSoup(frag, "html.parser")
            strong = f_soup.find(["strong", "b"])
            if not strong:
                continue
            topico = strong.get_text(" ", strip=True).strip(" -–—:")
            if not topico or len(topico) > 45 or len(topico) < 3:
                continue
            txt_item = re.sub(r"\s+", " ", f_soup.get_text(" ", strip=True)).strip()
            if not txt_item.startswith(topico) or " - " not in txt_item[: len(topico) + 6]:
                continue
            if len(txt_item) < 70 or len(txt_item) > 950:
                continue
            if topico.lower() in (
                "lula", "george santoro", "tomé franca", "dario durigan",
                "vladimir lima", "alexandre silveira", "não publicado",
                "imagens", "artes", "spam", "importante",
            ):
                continue
            txt_low = txt_item.lower()
            if any(ign in txt_low for ign in termos_rotina_ignorar):
                continue
            if not any(k in txt_low for k in palavras_chave_atos):
                continue
            if txt_item in atos_vistos:
                continue
            atos_vistos.add(txt_item)

            link_ato = None
            for a in f_soup.find_all("a", href=True):
                href = a["href"].strip()
                if href.startswith("https://") and "list-manage.com" not in href and "mailchi.mp" not in href:
                    link_ato = href
                    break
            if not link_ato:
                link_ato = f"{base_url}#Diario-{len(atos_vistos)}"

            corpo_ato = txt_item.split(" - ", 1)[-1].strip()
            primeira_frase = corpo_ato.split(". ")[0].strip()
            titulo_ato = f"[{topico}] {primeira_frase}"
            if len(titulo_ato) > 130:
                titulo_ato = titulo_ato[:127] + "..."

            score_prioridade = sum(2 for k in termos_alta_prioridade if k in txt_low)
            if "mpor" in txt_low or "antaq" in txt_low or "anac" in txt_low or "antt" in txt_low:
                score_prioridade += 3

            vert = _classificar_vertical_boletim(titulo_ato, txt_item)
            atos_candidatos.append((
                score_prioridade,
                {
                    "title": titulo_ato,
                    "link": link_ato,
                    "published": published_str,
                    "source": f"{fonte_label} — DOU & Radar",
                    "summary": txt_item[:430],
                    "vertical_original": vert,
                },
            ))

    # Seleciona os atos de maior prioridade estratégica para não inflar excessivamente o lote
    atos_candidatos.sort(key=lambda x: x[0], reverse=True)
    for _, item_ato in atos_candidatos[:max_atos_dou]:
        itens.append(item_ato)

    return itens


def _fetch_agencia_infra_mailchimp_fallback(when="24h") -> list:
    """
    Fallback HTTPS (porta 443) para ler e desmembrar as edições recentes do boletim de assinantes
    da Agência iNFRA mesmo quando a máquina local estiver sob bloqueio de firewall na porta 993 (IMAP).
    """
    horas_janela = 84 if when == "72h" else 36
    limite_dt = datetime.now(timezone.utc) - timedelta(hours=horas_janela)
    feed_url = "https://us14.campaign-archive.com/feed?u=d460dd1bcf9ba0ae040e1fc0f&id=849973d069"
    itens_extraidos = []

    try:
        r = requests.get(feed_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10, verify=False)
        if r.status_code != 200:
            return []
        feed = feedparser.parse(r.content)
        for entry in feed.entries[:6]:
            title = entry.get("title", "")
            link = (entry.get("link") or "").split("?")[0].strip()
            pub_str = entry.get("published", "")
            if not link.startswith("https://mailchi.mp/"):
                continue
            if "degustação" in title.lower() or "nova fase" in title.lower():
                continue
            try:
                dt_pub = parsedate_to_datetime(pub_str)
                if dt_pub.tzinfo is None:
                    dt_pub = dt_pub.replace(tzinfo=timezone.utc)
                if dt_pub < limite_dt:
                    continue
            except Exception:
                pass

            r_ed = requests.get(link, headers={"User-Agent": "Mozilla/5.0"}, timeout=10, verify=False)
            if r_ed.status_code == 200:
                itens_ed = _parse_boletim_agencia_infra(r_ed.text, link, pub_str, max_atos_dou=8)
                itens_extraidos.extend(itens_ed)
    except Exception as e:
        print(f"   [Aviso] Falha no fallback HTTPS do boletim Agência iNFRA: {e}")

    return itens_extraidos


def fetch_gmail_imap_newsletters(when="24h", max_items=35):
    """
    Lê newsletters recentes no Gmail diretamente via IMAP SSL (porta 993) em modo readonly:
    - Alcança tanto e-mails não lidos quanto já lidos;
    - Quando encontra boletins da Agência iNFRA (infrajornalismo@agenciainfra.com), busca a versão
      web limpa (mailchi.mp) e desmembra cada reportagem exclusiva (#1, #2, #3) e os atos estratégicos
      do DOU / Agenda / Fique de Olho com links oficiais desembrulhados;
    - Quando executado em rede corporativa local com porta 993 bloqueada, aciona automaticamente
      o fallback HTTPS (porta 443) sem interromper a execução.
    """
    user = os.getenv("GMAIL_USER", "").strip()
    password = os.getenv("GMAIL_APP_PASSWORD", "").replace(" ", "").strip()
    if not user or not password:
        # DESATIVADO: boletim de assinante da Agencia iNFRA (conteudo pago) nao e fonte do clipping.
        # return _fetch_agencia_infra_mailchimp_fallback(when=when)
        return []

    dias_busca = 4 if when == "72h" else 2
    itens_coletados = []
    extraiu_agencia_infra_imap = False

    old_timeout = socket.getdefaulttimeout()
    socket.setdefaulttimeout(5)
    try:
        M = imaplib.IMAP4_SSL("imap.gmail.com", 993)
        M.login(user, password)

        # Seleciona a caixa Todos os e-mails (All Mail) para alcançar todas as abas e mensagens já lidas
        status, folders = M.list()
        mailbox = "INBOX"
        if status == "OK" and folders:
            for f in folders:
                f_str = f.decode("utf-8", errors="replace")
                if "\\All" in f_str or "Todos" in f_str or "All Mail" in f_str:
                    m = re.search(r'"([^"]+)"$', f_str)
                    if m:
                        mailbox = m.group(1)
                        break

        M.select(f'"{mailbox}"', readonly=True)

        # Busca mensagens recentes dos remetentes monitorados
        typ, data = M.uid("SEARCH", "X-GM-RAW", f'"newer_than:{dias_busca}d"')
        uids = data[0].split() if (typ == "OK" and data and data[0]) else []

        # Processa das mais recentes para as mais antigas (limite de segurança de 80 cabeçalhos)
        for uid in reversed(uids[-80:]):
            typ_h, hdr_data = M.uid("FETCH", uid, "(BODY.PEEK[HEADER.FIELDS (FROM SUBJECT DATE)])")
            if typ_h != "OK" or not hdr_data or not hdr_data[0]:
                continue
            raw_hdr = hdr_data[0][1]
            msg_hdr = email.message_from_bytes(raw_hdr)
            frm = _decodificar_header_email(msg_hdr.get("From", ""))
            subj = _decodificar_header_email(msg_hdr.get("Subject", ""))
            dt_str = _decodificar_header_email(msg_hdr.get("Date", ""))

            frm_low = frm.lower()
            if not any(dom in frm_low for dom in GMAIL_ALLOWED_SENDERS):
                continue
            if any(w in subj.lower() for w in ["agradecemos por escolher", "pedido foi recebido", "recebemos o seu cadastro", "senha", "fatura"]):
                continue

            # Baixa o corpo completo apenas para os remetentes aprovados na allowlist
            typ_b, body_data = M.uid("FETCH", uid, "(RFC822)")
            if typ_b != "OK" or not body_data or not body_data[0]:
                continue
            msg_full = email.message_from_bytes(body_data[0][1])

            text_parts = []
            html_parts = []
            for part in msg_full.walk():
                ctype = part.get_content_type()
                cdisp = str(part.get("Content-Disposition") or "")
                if "attachment" in cdisp.lower():
                    continue
                if ctype == "text/plain":
                    payload = part.get_payload(decode=True)
                    if payload:
                        charset = part.get_content_charset() or "utf-8"
                        text_parts.append(payload.decode(charset, errors="replace"))
                elif ctype == "text/html":
                    payload = part.get_payload(decode=True)
                    if payload:
                        charset = part.get_content_charset() or "utf-8"
                        html_parts.append(payload.decode(charset, errors="replace"))

            full_txt = "\n".join(text_parts)
            full_html = "\n".join(html_parts)

            # Tratamento especializado para os boletins de assinantes da Agência iNFRA
            # DESATIVADO (04/11/2026): boletim de assinante da Agencia iNFRA (conteudo pago) nao e fonte do clipping; codigo mantido so para estudo comparativo local.
            # if "agenciainfra.com" in frm_low:
            #     m_mc = re.search(r"https://mailchi\.mp/[a-zA-Z0-9_/\-]+", full_txt + " " + full_html)
            #     if m_mc:
            #         clean_mc_url = m_mc.group(0).strip()
            #         html_para_parse = full_html
            #         try:
            #             r_mc = requests.get(clean_mc_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=8, verify=False)
            #             if r_mc.status_code == 200 and len(r_mc.text) > 5000:
            #                 html_para_parse = r_mc.text
            #         except Exception:
            #             pass
            #         itens_infra = _parse_boletim_agencia_infra(html_para_parse, clean_mc_url, dt_str, max_atos_dou=8)
            #         if itens_infra:
            #             itens_coletados.extend(itens_infra)
            #             extraiu_agencia_infra_imap = True
            #             continue
            if "agenciainfra.com" in frm_low:
                continue  # salvaguarda: nunca processar e-mails da Agencia iNFRA

            # Demais newsletters (Reset News, JOTA, CNseg, McKinsey, a16z, Substack, etc.)
            resumo_limpo = clean_html(full_html or full_txt)
            # Remove cabeçalhos genéricos de 'View in browser' do início do resumo
            resumo_limpo = re.sub(r"^(View this email in your browser|Ver no navegador|Read online)\s*", "", resumo_limpo, flags=re.I)
            link_ext = ""
            if full_html:
                s_nl = BeautifulSoup(full_html, "html.parser")
                for a in s_nl.find_all("a", href=True):
                    href = a["href"].strip()
                    if href.startswith("https://") and any(d in href.lower() for d in ("capitalreset", "jota.info", "a16z", "mckinsey", "substack", "agenciainfra")):
                        link_ext = href
                        break
            if not link_ext:
                link_ext = f"https://mail.google.com/mail/u/0/#inbox/{uid.decode()}"

            sender_clean = re.sub(r"<[^>]+>", "", frm).replace('"', "").strip() or "Newsletter"
            vert = _classificar_vertical_boletim(subj, resumo_limpo[:450])
            itens_coletados.append({
                "title": subj,
                "link": link_ext,
                "published": dt_str,
                "source": f"{sender_clean} (Newsletter Gmail)",
                "summary": resumo_limpo[:450],
                "vertical_original": vert,
            })

            if len(itens_coletados) >= max_items:
                break

        M.logout()
    except Exception as e:
        print(f"   [Info] IMAP 993 indisponível nesta rede ({type(e).__name__}) — acionando fallback HTTPS 443.")
        # DESATIVADO: boletim de assinante da Agencia iNFRA (conteudo pago) nao e fonte do clipping.
        # itens_fallback_infra = _fetch_agencia_infra_mailchimp_fallback(when=when)
        itens_fallback_infra = []
        itens_fallback_atom = fetch_gmail_newsletters(max_items=15)
        return itens_fallback_infra + itens_fallback_atom
    finally:
        socket.setdefaulttimeout(old_timeout)

    # DESATIVADO: boletim de assinante da Agencia iNFRA (conteudo pago) nao e fonte do clipping.
    # if not extraiu_agencia_infra_imap:
    #     itens_coletados.extend(_fetch_agencia_infra_mailchimp_fallback(when=when))

    return itens_coletados


def fetch_gmail_newsletters(max_items=12):
    """
    Lê newsletters recentes no Gmail via canal HTTPS Atom (porta 443).
    Não sofre bloqueio de firewall na porta 993/IMAP.
    """
    user = os.getenv("GMAIL_USER", "").strip()
    password = os.getenv("GMAIL_APP_PASSWORD", "").replace(" ", "").strip()
    if not user or not password:
        return []

    tags = ["", "important", "^smartlabel_notification", "clipping"]
    seen_ids = set()
    newsletters = []

    for tag in tags:
        url = f"https://mail.google.com/mail/feed/atom/{tag}" if tag else "https://mail.google.com/mail/feed/atom"
        try:
            r = requests.get(url, auth=(user, password), timeout=8)
            if r.status_code != 200:
                continue
            feed = feedparser.parse(r.content)
            for entry in feed.entries:
                eid = entry.get("id", entry.get("link", ""))
                if eid in seen_ids:
                    continue
                author = entry.get("author_detail", {})
                sender_name = author.get("name", "Newsletter")
                sender_email = author.get("email", "").lower()

                if not any(domain in sender_email for domain in GMAIL_ALLOWED_SENDERS):
                    continue

                # Ignora e-mails administrativos de assinatura/cadastro
                title = entry.get("title", "")
                if any(w in title.lower() for w in ["agradecemos por escolher", "pedido foi recebido", "senha", "fatura"]):
                    continue

                seen_ids.add(eid)
                summary = clean_html(entry.get("summary", ""))
                newsletters.append({
                    "title": title,
                    "link": entry.get("link", ""),
                    "published": entry.get("issued", entry.get("published", "")),
                    "source": f"{sender_name} (Newsletter Gmail)",
                    "summary": summary[:450],
                    "vertical_original": "newsletter",
                })
                if len(newsletters) >= max_items:
                    return newsletters
        except Exception as e:
            print(f"   [Aviso] Falha ao consultar aba Gmail '{tag or 'inbox'}': {e}")

    return newsletters


def fetch_all_raw_news(when="24h"):
    """
    Varre todas as 5 verticais estratégicas combinando:
    1) Via Expressa VIP (Valor, O Globo, Folha, Estadão, Agência iNFRA, JOTA, CNseg)
    2) Feeds Diretos Especializados (Capital Reset, JOTA, a16z)
    3) Newsletters do Gmail (Reset News, JOTA, CNseg, McKinsey, Substack IA, Environmental Finance, etc.)
    4) Varredura Aberta Temática no Google News RSS
    """
    queries = {
        "infra": {
            "nome": "Infraestrutura & Outorgas",
            "query": "(concessão OR leilão OR outorga OR PPI OR reequilíbrio) AND (ANTT OR ANAC OR ANTAQ OR rodovia OR ferrovia OR porto OR aeroporto)",
            "vip_query": f"{VIP_SITES_QUERY} AND (concessão OR leilão OR outorga OR PPI OR ANTT OR ANAC OR ANTAQ OR ferrovia OR rodovia OR porto OR aeroporto)",
        },
        "seguros": {
            "nome": "Seguros de Grandes Riscos",
            "query": '("seguro garantia" OR "performance bond" OR SUSEP OR CNseg OR "grandes riscos" OR "resseguro") AND (seguros OR regulação OR obras OR sinistro)',
            "vip_query": f'{VIP_SITES_QUERY} AND ("seguro garantia" OR SUSEP OR CNseg OR resseguro OR "grandes riscos" OR apólice OR seguradora)',
        },
        "carbono": {
            "nome": "Mercado de Carbono & Transição Climática",
            "query": '("crédito de carbono" OR "mercado de carbono" OR SBCE OR "Fundo Clima" OR "transição ecológica" OR "finanças verdes" OR "Eco Invest")',
            "vip_query": f'{VIP_SITES_QUERY} AND ("mercado de carbono" OR "crédito de carbono" OR SBCE OR "Fundo Clima" OR "transição energética" OR descarbonização)',
        },
        "divida": {
            "nome": "Instrumentos de Dívida & Mercado de Capitais",
            "query": '("debêntures de infraestrutura" OR "debêntures incentivadas" OR "Lei 14.801" OR "Lei 12.431" OR CVM OR ANBIMA OR FIDC) AND (emissão OR mercado OR crédito OR infraestrutura)',
            "vip_query": f'{VIP_SITES_QUERY} AND (debêntures OR "Lei 14.801" OR "Lei 12.431" OR CVM OR ANBIMA OR FIDC OR "crédito privado" OR BNDES)',
        },
        "tech": {
            "nome": "Tecnologia, IA & Gestão Aplicada",
            "query": '("inteligência artificial" OR "data center" OR McKinsey OR GovTech OR automação) AND (infraestrutura OR energia OR regulação OR governo OR financeiro OR produtividade)',
            "vip_query": f'{VIP_SITES_QUERY} AND ("inteligência artificial" OR "data center" OR McKinsey OR automação) AND (infraestrutura OR energia OR regulação OR bancos OR seguros OR gestão)',
        },
    }

    coleta = []
    seen_links = set()

    def adicionar_itens(lista, vertical_tag):
        for it in lista:
            lk = it.get("link", "")
            if "mailchi.mp" in lk or "list-manage.com" in lk or "campaign-archive.com" in lk:
                continue  # salvaguarda: links de boletim de assinante nunca entram no clipping
            if lk and lk not in seen_links:
                seen_links.add(lk)
                it["vertical_original"] = it.get("vertical_original") or vertical_tag
                coleta.append(it)

    # 1. Via Expressa VIP + Varredura Aberta por vertical (Degrau 1: 9 VIP + 8 Abertas)
    for key, info in queries.items():
        # 1a. Faixa VIP (Assinaturas & Veículos Prioritários)
        itens_vip = fetch_google_news(info["vip_query"], when=when, max_results=9)
        if len(itens_vip) < 4:
            itens_vip = fetch_google_news(info["vip_query"], when="72h", max_results=9)
        adicionar_itens(itens_vip, key)

        # 1b. Faixa Aberta (Descoberta geral)
        itens_abertos = fetch_google_news(info["query"], when=when, max_results=8)
        if len(itens_abertos) < 4 and when == "24h":
            itens_abertos = fetch_google_news(info["query"], when="48h", max_results=8)
        adicionar_itens(itens_abertos, key)

    # 2. Feeds Diretos Especializados (Agência iNFRA=15, Capital Reset=10, JOTA=10, a16z=6)
    itens_diretos = fetch_direct_rss_feeds(max_per_feed=10)
    adicionar_itens(itens_diretos, "direto")

    # 3. Newsletters do Gmail via IMAP 993 + Extrator Estruturado Agência iNFRA (com fallback HTTPS 443)
    itens_gmail = fetch_gmail_imap_newsletters(when=when, max_items=35)
    adicionar_itens(itens_gmail, "gmail")

    return coleta


if __name__ == "__main__":
    dados = fetch_all_raw_news(when="24h")
    print(f"Total de notícias brutas coletadas: {len(dados)}")
    por_fonte = {}
    for d in dados:
        por_fonte[d["source"]] = por_fonte.get(d["source"], 0) + 1
    print("Distribuição por fonte:", por_fonte)

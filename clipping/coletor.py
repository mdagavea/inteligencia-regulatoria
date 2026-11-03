import os
import re
import urllib.parse
import urllib3
import requests
import feedparser
from bs4 import BeautifulSoup
from datetime import datetime
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
    "agenciainfra.com",
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

    # 3. Newsletters do Gmail (Reset News, McKinsey, JOTA, CNseg, Substack IA, etc. — até 20)
    itens_gmail = fetch_gmail_newsletters(max_items=20)
    adicionar_itens(itens_gmail, "gmail")

    return coleta


if __name__ == "__main__":
    dados = fetch_all_raw_news(when="24h")
    print(f"Total de notícias brutas coletadas: {len(dados)}")
    por_fonte = {}
    for d in dados:
        por_fonte[d["source"]] = por_fonte.get(d["source"], 0) + 1
    print("Distribuição por fonte:", por_fonte)

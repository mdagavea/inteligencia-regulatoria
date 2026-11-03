"""
Coletor determinístico e filtro temático (sem IA) para a Aba 4 do Radar DECON/MPor:
"SFN, Seguros & Capitais" (SUSEP, CVM e atalhos monitorados para BCB, PREVIC, SRE/MF e ANBIMA).

Regras estritas (conforme 2026-10-29_Passagem_Aba_SFN_e_Agencias_para_Gemini.md):
1. 100% factual e verificável na fonte (sem opiniões, sem "ótica DECON", sem "recomenda-se").
2. Coleta e filtro temático por palavras-chave não dependem de IA.
3. Não excluir em silêncio: retorna tanto os processos aprovados no filtro (com indicação explícita
   da palavra-chave que casou) quanto a lista/contador de processos ativos fora do filtro temático.
"""

import hashlib
import json
import re
import ssl
import urllib.parse
import urllib.request
from datetime import datetime, date
from pathlib import Path
from bs4 import BeautifulSoup


PASTA_RADAR = Path(__file__).parent.resolve()
ARQUIVO_TERMOS = PASTA_RADAR / "termos_filtro.json"
ARQUIVO_LOG_DESCARTADOS = PASTA_RADAR / "log_descartados_filtro.txt"

SUSEP_GATEWAY_BASE = "https://www2.susep.gov.br/safe/SCP/gateway"
SUSEP_APP_URL = "https://www2.susep.gov.br/safe/SCP/app/consultas-publicas"
SUSEP_BUCKET = "producao"

CVM_AUDIENCIAS_URL = "https://conteudo.cvm.gov.br/audiencias_publicas/index.html"
CVM_BASE_URL = "https://conteudo.cvm.gov.br"


def carregar_config_filtro() -> dict:
    """Lê a configuração externa de termos em termos_filtro.json."""
    if ARQUIVO_TERMOS.exists():
        try:
            return json.loads(ARQUIVO_TERMOS.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"   [Aviso SFN] Erro ao ler {ARQUIVO_TERMOS.name}: {e}")
    return {"exclusoes_sfn": [], "regras_inclusao_sfn": []}


def registrar_log_descartados(itens_descartados: list):
    """Grava registro auditável (data, fonte, título, motivo) dos itens descartados pelo filtro, sem duplicar linhas."""
    if not itens_descartados:
        return
    linhas_existentes = set()
    if ARQUIVO_LOG_DESCARTADOS.exists():
        try:
            for ln in ARQUIVO_LOG_DESCARTADOS.read_text(encoding="utf-8").splitlines():
                partes = [p.strip() for p in ln.split("|")]
                if len(partes) >= 3:
                    linhas_existentes.add(f"{partes[1]}|{partes[2]}")
        except Exception:
            pass

    hoje_iso = date.today().isoformat()
    novas_linhas = []
    for it in itens_descartados:
        fonte = it.get("entidade", "SFN")
        titulo = f"{it.get('modalidade_numero', '')} - {it.get('ementa', '')[:140]}".replace("\n", " ").strip()
        chave = f"{fonte}|{titulo}"
        if chave in linhas_existentes:
            continue
        linhas_existentes.add(chave)
        motivo = it.get("motivo_exclusao", "Fora do filtro")
        url = it.get("url_principal", "")
        novas_linhas.append(f"{hoje_iso} | {fonte} | {titulo} | Motivo: {motivo} | {url}")

    if novas_linhas:
        with open(ARQUIVO_LOG_DESCARTADOS, "a", encoding="utf-8") as f:
            for ln in novas_linhas:
                f.write(ln + "\n")


def _criar_contexto_ssl():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    ctx.options |= getattr(ssl, "OP_IGNORE_UNEXPECTED_EOF", 0)
    try:
        ctx.set_ciphers("DEFAULT@SECLEVEL=1")
    except Exception:
        pass
    return ctx


def _requisitar_texto(url: str, timeout: int = 20) -> str:
    ctx = _criar_contexto_ssl()
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) RadarDECON/1.0",
            "Accept": "application/json, text/html, application/xhtml+xml, */*",
        },
    )
    with urllib.request.urlopen(req, context=ctx, timeout=timeout) as r:
        return r.read().decode("utf-8", errors="replace")


def classificar_item_sfn(texto_completo: str) -> dict:
    """
    Aplica o filtro temático determinístico (sem IA) a partir de termos_filtro.json.
    Retorna {"aprovado": bool, "vertical": str, "termo_casado": str, "motivo_exclusao": str}.
    """
    t_low = (texto_completo or "").lower()
    cfg = carregar_config_filtro()

    # 1. Verifica exclusões explícitas (a menos que mencione expressamente seguro-garantia, grandes riscos ou infraestrutura)
    tem_excecao_forte = bool(re.search(r"seguro[- ]garantia|grandes\s+riscos|riscos\s+de\s+engenharia|deb[eê]nture|infraestrutura", t_low))
    if not tem_excecao_forte:
        for item_exc in cfg.get("exclusoes_sfn", []):
            padrao_exc = (item_exc.get("termo") or "").lower().strip()
            rotulo_exc = item_exc.get("motivo") or "Fora do escopo"
            if padrao_exc and padrao_exc in t_low:
                return {
                    "aprovado": False,
                    "vertical": "seguros",
                    "termo_casado": "",
                    "motivo_exclusao": rotulo_exc,
                }

    # 2. Verifica casamento positivo nas verticais a partir de termos_filtro.json
    for regra in cfg.get("regras_inclusao_sfn", []):
        vertical = regra.get("vertical", "seguros")
        rotulo_termo = regra.get("rotulo", "")
        for termo in regra.get("termos", []):
            t_busca = (termo or "").lower().strip()
            if t_busca and t_busca in t_low:
                return {
                    "aprovado": True,
                    "vertical": vertical,
                    "termo_casado": f'{rotulo_termo} ("{termo}")',
                    "motivo_exclusao": "",
                }

    return {
        "aprovado": False,
        "vertical": "seguros",
        "termo_casado": "",
        "motivo_exclusao": "Fora das palavras-chave de termos_filtro.json",
    }


def gerar_hash_item_sfn(url_principal: str, titulo: str, ementa: str) -> str:
    """Gera identificador único determinístico (URL + hash SHA-256 curto do título e ementa) para evitar reprocessamento na IA."""
    base = f"{(url_principal or '').strip()}|{(titulo or '').strip()}|{(ementa or '').strip()}"
    h = hashlib.sha256(base.encode("utf-8")).hexdigest()[:16]
    return f"{(url_principal or '').strip()}#{h}"


def _url_download_susep(key_object: str) -> str:
    if not key_object:
        return ""
    encoded = urllib.parse.quote(key_object.strip(), safe="")
    return f"{SUSEP_GATEWAY_BASE}/AnexoAws/DownloadFile?bucketName={SUSEP_BUCKET}&keyObject={encoded}"


def _parse_data_susep(dt_str: str):
    """Converte data SUSEP no formato 'MM/DD/YYYY HH:MM' para (date, str_br, str_iso)."""
    if not dt_str:
        return None, "—", ""
    partes = dt_str.strip().split(" ")[0].split("/")
    if len(partes) == 3:
        try:
            mes, dia, ano = int(partes[0]), int(partes[1]), int(partes[2])
            d = date(ano, mes, dia)
            return d, d.strftime("%d/%m/%Y"), d.isoformat()
        except Exception:
            pass
    return None, dt_str, ""


def coletar_susep_consultas() -> list:
    """Coleta Consultas Públicas da SUSEP via API pública JSON (SAFE/SCP)."""
    hoje = date.today()
    itens = []
    vistos = set()

    for pagina in (1, 2):
        url = f"{SUSEP_GATEWAY_BASE}/SugestaoConsultaAndamento/{pagina}/true"
        try:
            raw = _requisitar_texto(url)
            dados = json.loads(raw)
            registros = (dados.get("retorno") or {}).get("registros") or []
        except Exception as e:
            print(f"   [Aviso SFN] Falha ao consultar SUSEP página {pagina}: {e}")
            break

        for reg in registros:
            num = str(reg.get("numero") or "").strip()
            ano = str(reg.get("ano") or "").strip()
            chave = f"SUSEP_CP_{num}_{ano}"
            if not num or chave in vistos:
                continue
            vistos.add(chave)

            d_ini, ini_br, _ = _parse_data_susep(reg.get("dataInicio", ""))
            d_fim, fim_br, fim_iso = _parse_data_susep(reg.get("dataFim", ""))
            if not d_fim:
                continue

            dias_restantes = (d_fim - hoje).days
            # Mantém abertas ou encerradas nos últimos 5 dias para visibilidade de fechamento recente
            if dias_restantes < -5:
                continue

            if dias_restantes < 0:
                status_ciclo = "ENCERRADO_RECENTE"
            elif d_ini and (hoje - d_ini).days <= 2:
                status_ciclo = "LANCADO_48H"
            elif dias_restantes <= 7:
                status_ciclo = "PRAZO_URGENTE"
            else:
                status_ciclo = "ABERTO"

            ementa = re.sub(r"\s{2,}", " ", (reg.get("linkEdital") or "").strip())
            obs = re.sub(r"\s{2,}", " ", (reg.get("observacoes") or "").strip())
            if obs == ".":
                obs = ""

            url_dou = (reg.get("enderecoEdital") or "").strip()
            email_resp = (reg.get("emailAreaResponsavel") or "").strip()

            docs = []
            if url_dou.startswith("http"):
                docs.append({
                    "rotulo": "📜 Edital no DOU",
                    "url": url_dou,
                    "categoria": "DOU",
                })
            if reg.get("keyObjectAnexoMinuta"):
                docs.append({
                    "rotulo": "📄 Minuta da Norma (PDF)",
                    "url": _url_download_susep(reg["keyObjectAnexoMinuta"]),
                    "categoria": "MINUTA",
                })
            if reg.get("keyObjectAnexoExposicaoMotivos"):
                docs.append({
                    "rotulo": "📊 Exposição de Motivos (PDF)",
                    "url": _url_download_susep(reg["keyObjectAnexoExposicaoMotivos"]),
                    "categoria": "NOTA_TECNICA",
                })
            if reg.get("keyObjectAnexoQuadroComparativo"):
                docs.append({
                    "rotulo": "📐 Quadro Comparativo",
                    "url": _url_download_susep(reg["keyObjectAnexoQuadroComparativo"]),
                    "categoria": "SUBSIDIO",
                })
            docs.append({
                "rotulo": "📝 Enviar Sugestão (Portal SUSEP SCP)",
                "url": SUSEP_APP_URL,
                "categoria": "CONTRIBUIR",
            })

            classif = classificar_item_sfn(f"{ementa} {obs}")

            itens.append({
                "id": chave,
                "entidade": "SUSEP",
                "entidade_nome": "Superintendência de Seguros Privados (SUSEP / CNSP)",
                "modalidade_numero": f"Consulta Pública SUSEP nº {num}/{ano}",
                "ementa": ementa,
                "observacoes": obs,
                "email_area": email_resp,
                "data_inicio_br": ini_br,
                "data_fim_br": fim_br,
                "data_fim_iso": fim_iso,
                "dias_restantes": dias_restantes,
                "status_ciclo": status_ciclo,
                "url_principal": url_dou if url_dou.startswith("http") else SUSEP_APP_URL,
                "documentos": docs,
                "aprovado_filtro": classif["aprovado"],
                "vertical": classif["vertical"],
                "termo_casado": classif["termo_casado"],
                "motivo_exclusao": classif["motivo_exclusao"],
            })

    return itens


def _parse_data_cvm(prazo_str: str):
    """Converte strings como 'Fri Dec 04 23:59:00 BRST 2026' ou 'dd/mm/yyyy' para (date, str_br, str_iso)."""
    if not prazo_str:
        return None, "—", ""
    s = prazo_str.strip()
    m_br = re.search(r"(\d{2})/(\d{2})/(\d{4})", s)
    if m_br:
        try:
            d = date(int(m_br.group(3)), int(m_br.group(2)), int(m_br.group(1)))
            return d, d.strftime("%d/%m/%Y"), d.isoformat()
        except Exception:
            pass

    meses_en = {
        "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
        "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12
    }
    m_en = re.search(r"\b([A-Za-z]{3})\s+(\d{1,2})\s+[\d:]+\s+[A-Z]+\s+(\d{4})", s)
    if m_en:
        mes = meses_en.get(m_en.group(1).lower())
        if mes:
            try:
                d = date(int(m_en.group(3)), mes, int(m_en.group(2)))
                return d, d.strftime("%d/%m/%Y"), d.isoformat()
            except Exception:
                pass
    return None, s, ""


def coletar_cvm_audiencias() -> list:
    """Coleta Consultas/Audiências Públicas abertas na CVM."""
    hoje = date.today()
    itens = []
    try:
        html = _requisitar_texto(CVM_AUDIENCIAS_URL)
        soup = BeautifulSoup(html, "html.parser")
    except Exception as e:
        print(f"   [Aviso SFN] Falha ao consultar CVM ({CVM_AUDIENCIAS_URL}): {e}")
        return []

    for tr in soup.select("table tr"):
        cols = [td.get_text(" ", strip=True) for td in tr.find_all("td")]
        if len(cols) < 4:
            continue
        edital_nome, tema, prazo_raw, fase = cols[0], cols[1], cols[2], cols[3]
        if "aberta" not in fase.lower() and "andamento" not in fase.lower():
            continue

        a_tag = tr.find("a", href=True)
        href = a_tag["href"].strip() if a_tag else CVM_AUDIENCIAS_URL
        if href.startswith("/"):
            href = CVM_BASE_URL + href
        elif href.startswith("http://www.cvm.gov.br"):
            href = href.replace("http://www.cvm.gov.br", CVM_BASE_URL)

        d_fim, fim_br, fim_iso = _parse_data_cvm(prazo_raw)
        dias_restantes = (d_fim - hoje).days if d_fim else None
        if dias_restantes is not None and dias_restantes < -5:
            continue

        if dias_restantes is not None and dias_restantes < 0:
            status_ciclo = "ENCERRADO_RECENTE"
        elif dias_restantes is not None and dias_restantes <= 7:
            status_ciclo = "PRAZO_URGENTE"
        else:
            status_ciclo = "ABERTO"

        # Busca links de PDFs dentro da página do edital da CVM
        docs = [{
            "rotulo": "📄 Página Oficial do Edital (CVM)",
            "url": href,
            "categoria": "EDITAL",
        }]
        if href != CVM_AUDIENCIAS_URL:
            try:
                sub_html = _requisitar_texto(href, timeout=12)
                sub_soup = BeautifulSoup(sub_html, "html.parser")
                for a_sub in sub_soup.find_all("a", href=True):
                    h_sub = a_sub["href"].strip()
                    txt_sub = a_sub.get_text(" ", strip=True) or "Anexo CVM"
                    if h_sub.lower().endswith(".pdf"):
                        if h_sub.startswith("/"):
                            h_sub = CVM_BASE_URL + h_sub
                        elif not h_sub.startswith("http"):
                            h_sub = href.rsplit("/", 1)[0] + "/" + h_sub
                        docs.append({
                            "rotulo": f"📑 {txt_sub[:45]}",
                            "url": h_sub,
                            "categoria": "MINUTA",
                        })
            except Exception:
                pass

        classif = classificar_item_sfn(f"{edital_nome} {tema}")
        chave_id = "CVM_" + re.sub(r"\W+", "_", edital_nome)

        itens.append({
            "id": chave_id,
            "entidade": "CVM",
            "entidade_nome": "Comissão de Valores Mobiliários (CVM)",
            "modalidade_numero": edital_nome,
            "ementa": tema,
            "observacoes": f"Fase: {fase}",
            "email_area": "",
            "data_inicio_br": "Em andamento",
            "data_fim_br": fim_br,
            "data_fim_iso": fim_iso,
            "dias_restantes": dias_restantes,
            "status_ciclo": status_ciclo,
            "url_principal": href,
            "documentos": docs,
            "aprovado_filtro": classif["aprovado"],
            "vertical": classif["vertical"],
            "termo_casado": classif["termo_casado"],
            "motivo_exclusao": classif["motivo_exclusao"],
        })

    return itens


def coletar_tudo_aba_sfn() -> dict:
    """
    Coleta todos os processos ativos das entidades do SFN/Seguros/Capitais,
    separa entre aprovados pelo filtro temático e retidos fora do filtro (sem excluir em silêncio),
    e fornece o status das demais origens monitoradas.
    """
    todos = []
    todos.extend(coletar_susep_consultas())
    todos.extend(coletar_cvm_audiencias())

    # Ordena por menor prazo restante
    todos.sort(key=lambda x: (
        0 if (x["dias_restantes"] is not None and x["dias_restantes"] >= 0) else 1,
        x["dias_restantes"] if x["dias_restantes"] is not None else 999,
        x["id"],
    ))

    aprovados = []
    for it in todos:
        if it["aprovado_filtro"]:
            it["hash_cache_ia"] = gerar_hash_item_sfn(it["url_principal"], it["modalidade_numero"], it["ementa"])
            aprovados.append(it)

    fora_do_filtro = [it for it in todos if not it["aprovado_filtro"]]
    registrar_log_descartados(fora_do_filtro)

    fontes_monitoradas = [
        {
            "sigla": "SUSEP / CNSP",
            "status": "ATIVO_AUTOMATICO",
            "rotulo": "API JSON SAFE/SCP Conectada",
            "url": SUSEP_APP_URL,
        },
        {
            "sigla": "CVM",
            "status": "ATIVO_AUTOMATICO",
            "rotulo": "Portal de Audiências Conectado",
            "url": CVM_AUDIENCIAS_URL,
        },
        {
            "sigla": "SRE / MF",
            "status": "INTEGRADO_ABA_1",
            "rotulo": "Captado via Brasil Participativo (Aba 1)",
            "url": "https://brasilparticipativo.presidencia.gov.br/processes",
        },
        {
            "sigla": "BCB (Banco Central)",
            "status": "PORTAL_JS",
            "rotulo": "Consulta Direta no Portal BCB",
            "url": "https://www.bcb.gov.br/estabilidadefinanceira/consultaspublicas",
        },
        {
            "sigla": "ANBIMA (Autorregulação)",
            "status": "PORTAL_JS",
            "rotulo": "Audiências Públicas ANBIMA",
            "url": "https://www.anbima.com.br/pt_br/autorregular/audiencias-publicas.htm",
        },
        {
            "sigla": "PREVIC",
            "status": "PORTAL_GOV",
            "rotulo": "Consultas Públicas PREVIC",
            "url": "https://www.gov.br/previc/pt-br/assuntos/regulacao/audiencias-e-consultas-publicas",
        },
    ]

    return {
        "aprovados": aprovados,
        "fora_do_filtro": fora_do_filtro,
        "fontes_monitoradas": fontes_monitoradas,
    }


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    res = coletar_tudo_aba_sfn()
    print(f"Aprovados no filtro temático: {len(res['aprovados'])} | Fora do filtro (visíveis na gaveta): {len(res['fora_do_filtro'])}")
    for it in res["aprovados"]:
        print(f"  [APROVADO - {it['vertical'].upper()}] {it['modalidade_numero']} (até {it['data_fim_br']}) | Termo: {it['termo_casado']}")
    for it in res["fora_do_filtro"]:
        print(f"  [FORA DO FILTRO] {it['modalidade_numero']} (até {it['data_fim_br']}) | Motivo: {it['motivo_exclusao']}")

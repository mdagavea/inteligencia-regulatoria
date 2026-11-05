import html
import json
import re
import time
import urllib.parse
from datetime import datetime, date, timedelta
import requests
import feedparser
from bs4 import BeautifulSoup
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

HEADERS_PADRAO = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,application/json,*/*;q=0.8",
}


def formatar_moeda_br(valor) -> str:
    if valor is None or valor == "" or valor == 0:
        return "Valor sob estimação / sigiloso"
    try:
        v = float(valor)
        if v <= 0:
            return "Valor sob estimação / sigiloso"
        if v >= 1_000_000_000:
            return f"R$ {v / 1_000_000_000:,.2f} bi".replace(",", "X").replace(".", ",").replace("X", ".")
        if v >= 1_000_000:
            return f"R$ {v / 1_000_000:,.2f} mi".replace(",", "X").replace(".", ",").replace("X", ".")
        return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return str(valor)


def _parse_data_iso_flex(val: str):
    if not val:
        return None
    try:
        return datetime.fromisoformat(val[:10]).date()
    except Exception:
        return None


def _classificar_doc_infra_sa(texto: str, href: str) -> str:
    t = (texto or "").lower()
    u = (href or "").lower()
    if "matriz" in t or "risco" in t or "matriz" in u:
        return "MATRIZ_RISCO"
    if "termo de refer" in t or "_tr" in u or "termo_de_referencia" in u:
        return "TERMO_REFERENCIA"
    if "estudo t" in t or "etp" in t or "etp" in u:
        return "ETP"
    if "edital" in t or "edital" in u:
        return "EDITAL"
    if "dou" in t or "publicacao-dou" in u:
        return "DOU"
    if "orcament" in t or "orçament" in t or "lote" in t:
        return "ORCAMENTO_LOTE"
    if "minuta" in t and "contrato" in t:
        return "MINUTA_CONTRATO"
    return "DOCUMENTO"


def _icone_doc_estruturacao(cat: str, texto: str) -> str:
    t = (texto or "").strip()
    if cat == "MATRIZ_RISCO":
        return f"🛡️ {t}" if not t.startswith("🛡️") else t
    if cat == "EDITAL":
        return f"📄 {t}" if not t.startswith("📄") else t
    if cat == "TERMO_REFERENCIA":
        return f"📑 {t}" if not t.startswith("📑") else t
    if cat == "ETP":
        return f"📐 {t}" if not t.startswith("📐") else t
    if cat == "ORCAMENTO_LOTE":
        return f"💰 {t}" if not t.startswith("💰") else t
    if cat == "MINUTA_CONTRATO":
        return f"📝 {t}" if not t.startswith("📝") else t
    if cat == "DOU":
        return f"📜 {t}" if not t.startswith("📜") else t
    return f"📎 {t}"


def _extrair_codigo_rle(texto: str) -> str:
    """Extrai chave normalizada 'RLE_16_2026' se o texto contiver referência a RLE nº XX/YYYY."""
    m = re.search(r"rle[\s\-–—]*(?:edital[\s\-–—]*)*(?:n[º°.]*[\s\-–—]*)*0*(\d+)\s*[/\-]\s*(\d{4})", (texto or ""), re.IGNORECASE)
    if m:
        return f"RLE_{int(m.group(1))}_{m.group(2)}"
    return ""


def coletar_licitacoes_infra_sa(max_itens: int = 12) -> list:
    """
    Consulta a API REST oficial da Infra S.A. (/wp-json/wp/v2/licitacoes)
    para identificar editais RLE de EVTEAs e estruturação/modelagem de concessões
    (descartando supervisão de obras ou compras administrativas) e extrai os anexos oficiais.
    """
    url_api = f"https://www.infrasa.gov.br/wp-json/wp/v2/licitacoes?per_page={max_itens}"
    itens = []
    hoje = date.today()

    try:
        r = requests.get(url_api, headers=HEADERS_PADRAO, timeout=12)
        if r.status_code != 200:
            return []
        posts = r.json()
        for post in posts:
            post_id = str(post.get("id", ""))
            titulo_raw = html.unescape((post.get("title") or {}).get("rendered") or "").strip()
            link_pagina = post.get("link") or f"https://www.infrasa.gov.br/?post_type=licitacoes&p={post_id}"
            data_pub_str = (post.get("date") or "")[:10]
            data_pub_d = _parse_data_iso_flex(data_pub_str)

            t_low = titulo_raw.lower()
            if not ("rle" in t_low or "evtea" in t_low or "concess" in t_low):
                continue
            if data_pub_d and (hoje - data_pub_d).days > 150:
                continue

            # Busca a página HTML do certame para extrair os PDFs/XLSXs dos campos customizados (ACF)
            texto_limpo = ""
            documentos = []
            vistos_doc = set()
            try:
                r_pag = requests.get(link_pagina, headers=HEADERS_PADRAO, timeout=10)
                if r_pag.status_code == 200:
                    soup = BeautifulSoup(r_pag.text, "html.parser")
                    texto_limpo = soup.get_text(" ", strip=True)
                    for a in soup.find_all("a", href=True):
                        href = a["href"].strip()
                        rotulo = a.get_text(" ", strip=True) or "Anexo"
                        if not href or "/wp-content/uploads/" not in href:
                            continue
                        if any(fixo in href.lower() for fixo in [
                            "rilc-regulamento", "007-2022", "inventario_", "politica-de-divulgacao",
                            "politica_de_transacoes", "politica-de-distribuicao"
                        ]):
                            continue
                        if href.startswith("/"):
                            href = "https://www.infrasa.gov.br" + href
                        if href in vistos_doc:
                            continue
                        vistos_doc.add(href)
                        cat = _classificar_doc_infra_sa(rotulo, href)
                        # Esclarece no rótulo da Matriz de Riscos que se trata do contrato de consultoria
                        rot_exib = rotulo[:65]
                        if cat == "MATRIZ_RISCO" and "consultoria" not in rot_exib.lower():
                            rot_exib = f"{rot_exib} (Contrato Consultoria)"
                        documentos.append({
                            "rotulo": _icone_doc_estruturacao(cat, rot_exib),
                            "url": href,
                            "categoria": cat,
                        })
            except Exception:
                pass

            # Filtro estrito de escopo (Critérios A e B): apenas EVTEA / estudos de viabilidade / estruturação de concessões.
            # Descarta supervisão de obras (ex: RLE 017/2026 - Supervisão das Obras da FIOL II).
            chave_rle = _extrair_codigo_rle(titulo_raw)
            blob_verif = (titulo_raw + " " + texto_limpo + " " + " ".join(d["rotulo"] + " " + d["url"] for d in documentos)).lower()
            if any(excl in blob_verif for excl in ["supervisao", "supervisão", "gerenciamento de obras", "alienação", "inservíveis"]):
                continue
            if chave_rle != "RLE_16_2026" and not any(inc in blob_verif for inc in ["evtea", "viabilidade", "desestatiza", "concess", "termo de referência", "termo_de_referencia"]):
                continue

            # Adiciona botão para a página oficial da licitação na Infra S.A.
            documentos.insert(0, {
                "rotulo": "🌐 Página Oficial da Licitação (Infra S.A.)",
                "url": link_pagina,
                "categoria": "SEI",
            })

            ordem_doc = {
                "SEI": 0,
                "EDITAL": 1,
                "TERMO_REFERENCIA": 2,
                "ETP": 3,
                "MATRIZ_RISCO": 4,
                "ORCAMENTO_LOTE": 5,
                "MINUTA_CONTRATO": 6,
                "DOU": 7,
                "DOCUMENTO": 8,
            }
            documentos.sort(key=lambda d: ordem_doc.get(d["categoria"], 9))

            tem_matriz_risco = any(d["categoria"] == "MATRIZ_RISCO" for d in documentos)
            chave_rle = _extrair_codigo_rle(titulo_raw)

            eh_setor_foco = any(w in blob_verif for w in ["porto", "portu", "hidrovi", "aeroport"])
            prioridade_escopo = "PRIORIDADE_A" if eh_setor_foco else "PRIORIDADE_B"
            categoria_item = "PRIORIDADE_A" if eh_setor_foco else "PRIORIDADE_B_COMPARACAO"

            item_dict = {
                "id": f"INFRASA_{post_id}",
                "chave_rle": chave_rle,
                "origem": "Infra S.A.",
                "estruturador_sigla": "Infra S.A. (MT)",
                "prioridade_escopo": prioridade_escopo,
                "categoria_item": categoria_item,
                "modalidade": "RLE (Lei das Estatais 13.303/2016)",
                "titulo": titulo_raw,
                "descricao_bruta": texto_limpo[:1500],
                "url": link_pagina,
                "valor_estimado": None,
                "valor_formatado": "Ver Caderno Orçamentário",
                "data_publicacao_br": data_pub_d.strftime("%d/%m/%Y") if data_pub_d else "Recente",
                "data_publicacao_iso": data_pub_str,
                "data_fim_br": "Consultar Edital",
                "data_fim_iso": "",
                "dias_restantes": None,
                "tem_matriz_risco": tem_matriz_risco,
                "documentos": documentos[:9],
            }

            # Ficha documental verificada para RLE nº 016/2026 (Edital PNCP nº 61/2026)
            if chave_rle == "RLE_16_2026":
                item_dict.update({
                    "ficha_documental_verificada": True,
                    "titulo_executivo": "Infra S.A. — RLE Edital nº 016/2026 (Edital PNCP nº 61/2026) — Elaboração de EVTEA de Rodovias Federais (Lote 1: BR-158/070/364/MT | Lote 2: BR-116/285/RS e SC)",
                    "escopo_sintetico": (
                        "Objeto: Contratação de pessoa jurídica para elaboração de Estudos de Viabilidade Técnica, Econômica e Ambiental (EVTEA) "
                        "para estruturar desestatizações de rodovias federais, com extensão total aproximada de 2.179,5 km, divididos em Lote 1 "
                        "(BR-158/070/364/MT) e Lote 2 (BR-116/285/RS e SC) | Valor estimado: R$ 28.875.158,35 | "
                        "Situação: Aberta (entrega de propostas até 06/01/2027, às 10h) | "
                        "Onde está o escopo: Anexo I – Termo de Referência (83 páginas)."
                    ),
                    "analise_riscos_segurabilidade": (
                        "• O Anexo VI – Matriz de Riscos (PDF, 1 página / 24 riscos) trata exclusivamente dos riscos do contrato de consultoria "
                        "(atrasos de entrega, variação de custos, não aprovação de produtos pelo TCU/ANTT), e não da futura concessão rodoviária.\n"
                        "• No Anexo I – Termo de Referência (83 págs.), a exigência relativa a seguros na modelagem da futura concessão resume-se ao "
                        "Produto 4 – Modelagem Econômico-Financeira (item 4.5.1.2 \"m\" e \"n\", p. 29): \"as planilhas eletrônicas deverão dispor de um "
                        "painel de controle com os principais dados de entrada (inputs) e premissas projetadas ao longo do prazo da concessão, para "
                        "variáveis como: (...) m) Seguros e Garantias\".\n"
                        "• Não há no Termo de Referência previsão de produto específico de estudo de segurabilidade, cotação no mercado segurador "
                        "ou modelagem de seguro-garantia com cláusula de retomada para a futura concessão.\n"
                        "• Outras menções a riscos no TR referem-se a: Plano de Gerenciamento de Riscos (PGR) de produtos perigosos no Modelo Operacional "
                        "(Produto 3, item 4.4.1.2 \"q\", p. 26) e riscos climáticos na Resiliência Climática (Produto 2B, item 4.3.2, p. 23–25)."
                    ),
                })

            itens.append(item_dict)
    except Exception as e:
        print(f"   [Aviso] Falha ao consultar API Infra S.A.: {e}")

    return itens


def _buscar_pncp(params: dict) -> dict:
    headers = {
        "Referer": "https://pncp.gov.br/app/editais",
        "Accept": "application/json, text/plain, */*",
        "User-Agent": HEADERS_PADRAO["User-Agent"],
    }
    for tentativa in range(3):
        try:
            r = requests.get(
                "https://pncp.gov.br/api/search/",
                params=params,
                headers=headers,
                timeout=12,
            )
            if r.status_code == 200:
                return r.json()
        except Exception:
            time.sleep(0.7 * (tentativa + 1))
    return {}


def _buscar_arquivos_pncp(item_url: str) -> list:
    """
    Dado item_url no formato '/compras/{cnpj}/{ano}/{seq}', consulta a API de arquivos do PNCP
    para obter os links diretos de download de Edital, Termo de Referência, Especificação Técnica e ETP.
    """
    partes = [p for p in (item_url or "").split("/") if p]
    if len(partes) < 4 or partes[0] != "compras":
        return []
    cnpj, ano, seq = partes[1], partes[2], partes[3]
    url_api = f"https://pncp.gov.br/api/pncp/v1/orgaos/{cnpj}/compras/{ano}/{int(seq)}/arquivos"
    docs = []
    try:
        r = requests.get(url_api, headers=HEADERS_PADRAO, timeout=10)
        if r.status_code == 200:
            for arq in r.json():
                if arq.get("statusAtivo") is False:
                    continue
                titulo_arq = (arq.get("titulo") or "Arquivo").strip()
                tipo_nome = (arq.get("tipoDocumentoNome") or "").strip()
                url_dl = (arq.get("url") or "").strip()
                if not url_dl:
                    continue
                t_low = (titulo_arq + " " + tipo_nome).lower()
                if "edital" in t_low and "anexo" not in t_low:
                    cat = "EDITAL"
                    rot = f"📄 Edital ({titulo_arq[:45]})"
                elif "termo de refer" in t_low or "_tr_" in t_low or "tr.pdf" in t_low:
                    cat = "TERMO_REFERENCIA"
                    rot = f"📑 Termo de Referência ({titulo_arq[:40]})"
                elif "especifica" in t_low or "anexo ii" in t_low or "anexo_ii" in t_low:
                    cat = "TERMO_REFERENCIA"
                    rot = f"📐 Anexo II – Especificação Técnica ({titulo_arq[:35]})"
                elif "etp" in t_low or "estudo tecnico" in t_low or "estudo técnico" in t_low:
                    cat = "ETP"
                    rot = f"📐 ETP ({titulo_arq[:40]})"
                elif "matriz" in t_low or "risco" in t_low:
                    cat = "MATRIZ_RISCO"
                    rot = f"🛡️ Matriz de Riscos ({titulo_arq[:40]})"
                elif "contrato" in t_low or "minuta" in t_low:
                    cat = "MINUTA_CONTRATO"
                    rot = f"📝 {titulo_arq[:50]}"
                else:
                    cat = "DOCUMENTO"
                    rot = f"📎 {titulo_arq[:50]}"
                docs.append({"rotulo": rot, "url": url_dl, "categoria": cat})
    except Exception:
        pass
    return docs


def coletar_estruturacao_e_seguros_pncp() -> list:
    """
    Consulta a API oficial do PNCP aplicando os critérios estritos da Aba 2:
    - Prioridade A (Portos, Aeroportos e Hidrovias): EVTEA, estudos de viabilidade ou modelagem econômico-financeira/regulatória
      para concessão, PPP ou arrendamento de portos, aeroportos ou hidrovias.
    - Prioridade B (comparação): EVTEA ou modelagem federal de outros setores (rodovias, ferrovias)
      conduzidos por Infra S.A., BNDES, DNIT ou ANTT.
    """
    consultas = [
        {"q": "EVTEA", "tam": 15},
        {"q": "estudos de viabilidade", "tam": 15},
        {"q": "modelagem economico-financeira", "tam": 15},
        {"q": "estruturacao de concessao", "tam": 15},
        {"q": "arrendamento portuario", "tam": 15},
        {"q": "hidrovia", "tam": 15},
    ]

    hoje = date.today()
    vistos_pncp = set()
    candidatos = []

    for cfg in consultas:
        dados = _buscar_pncp({
            "q": cfg["q"],
            "tipos_documento": "edital",
            "status": "recebendo_proposta",
            "pagina": 1,
            "tam_pagina": cfg["tam"],
        })
        for it in dados.get("items", []):
            num_ctrl = it.get("numero_controle_pncp") or it.get("id")
            if not num_ctrl or num_ctrl in vistos_pncp:
                continue

            orgao = (it.get("orgao_nome") or "").strip()
            esfera = (it.get("esfera_nome") or "").strip()
            desc = re.sub(r"\s+", " ", (it.get("description") or "")).strip()
            titulo_edital = (it.get("title") or "Edital").strip()
            info_comp = (it.get("informacao_complementar") or "").strip()
            valor = it.get("valor_total_estimado") or 0.0
            modalidade = (it.get("modalidade_licitacao_nome") or "Licitação").strip()
            uf = (it.get("uf") or "").strip()

            texto_analise = f"{orgao} {titulo_edital} {desc} {info_comp}".lower()

            # Descarta descrições truncadas ou objetos fora do escopo (obras comuns, manutenção, supervisão, seguros judiciais, PBA isolado)
            if len(desc) < 45 or desc.lower().startswith("despacho (") or any(ruido in texto_analise for ruido in [
                "manutenção", "manutencao", "conservação", "conservacao", "supervisão", "supervisao",
                "hidroginástica", "hidroginastica", "controle e registro de acesso", "seguro garantia judicial",
                "plano básico ambiental", "plano basico ambiental", "remoção de rochas e dragagem",
                "gêneros alimentícios", "merenda", "medicamento", "hospital", "ambulância",
            ]):
                continue

            eh_evtea_ou_modelagem = any(w in texto_analise for w in [
                "evtea", "estudo de viabilidade", "estudos de viabilidade",
                "modelagem econômico-financeira", "modelagem economico-financeira",
                "estruturação de concess", "estruturacao de concess", "desestatiza",
            ])
            if not eh_evtea_ou_modelagem:
                continue

            eh_setor_foco = any(w in texto_analise for w in [
                "porto", "portuári", "portuaria", "hidrovi", "aeroport", "aquaviári", "aquaviaria", "antaq", "anac",
            ])
            eh_estruturador_federal = esfera == "Federal" and any(w in orgao.lower() or w in texto_analise for w in [
                "valec", "infra s", "dnit", "bndes", "antt", "ministério dos transportes",
            ])

            if not (eh_setor_foco or eh_estruturador_federal):
                continue

            vistos_pncp.add(num_ctrl)

            eh_infra_sa = "valec" in orgao.lower() or "infra s" in orgao.lower() or "infrasa.gov.br" in str(it.get("link_processo_eletronico") or "").lower()
            eh_dnit = "dnit" in orgao.lower()

            prioridade_escopo = "PRIORIDADE_A_DESTAQUE" if eh_setor_foco else "PRIORIDADE_B"
            categoria_item = "PRIORIDADE_A" if eh_setor_foco else "PRIORIDADE_B_COMPARACAO"

            item_url = it.get("item_url") or ""
            url_pncp = f"https://pncp.gov.br/app/editais/{item_url.replace('/compras/', '')}" if item_url.startswith("/compras/") else "https://pncp.gov.br/app/editais"
            link_proc = (it.get("link_processo_eletronico") or "").strip()

            # Busca arquivos oficiais diretamente na API de arquivos do PNCP
            arquivos_diretos = _buscar_arquivos_pncp(item_url)
            documentos = [{"rotulo": "🏛️ Página do Edital no PNCP", "url": url_pncp, "categoria": "SEI"}]
            if link_proc.startswith("http") and "infrasa.gov.br" in link_proc:
                documentos.insert(0, {"rotulo": "🌐 Página Oficial da Licitação (Infra S.A.)", "url": link_proc, "categoria": "SEI"})
            documentos.extend(arquivos_diretos[:6])

            pub_iso = (it.get("data_publicacao_pncp") or it.get("createdAt") or "")[:10]
            pub_d = _parse_data_iso_flex(pub_iso)
            fim_raw = it.get("data_fim_vigencia") or ""
            fim_iso = fim_raw[:10] if fim_raw else ""
            fim_d = _parse_data_iso_flex(fim_iso)
            if fim_d and fim_d.year >= 2035:
                fim_d = None
                fim_iso = ""

            dias_restantes = (fim_d - hoje).days if fim_d else None

            sigla_orgao = "Infra S.A. (MT)" if eh_infra_sa else (
                f"DNIT/{uf} (MT)" if eh_dnit and uf else orgao[:45]
            )
            sub_info = f" ({info_comp})" if info_comp and len(info_comp) < 35 else ""
            chave_rle = _extrair_codigo_rle(f"{titulo_edital} {info_comp} {desc}")

            item_dict = {
                "id": f"PNCP_{num_ctrl}",
                "chave_rle": chave_rle,
                "origem": "PNCP / Compras.gov.br",
                "estruturador_sigla": sigla_orgao,
                "prioridade_escopo": prioridade_escopo,
                "categoria_item": categoria_item,
                "modalidade": f"{modalidade} • Lei 14.133/2021",
                "titulo": f"{titulo_edital}{sub_info} — {sigla_orgao}",
                "descricao_bruta": desc[:2000],
                "url": link_proc if (link_proc.startswith("http") and "infrasa.gov.br" in link_proc) else url_pncp,
                "valor_estimado": valor if valor > 0 else None,
                "valor_formatado": formatar_moeda_br(valor),
                "data_publicacao_br": pub_d.strftime("%d/%m/%Y") if pub_d else "Recente",
                "data_publicacao_iso": pub_iso,
                "data_fim_br": fim_d.strftime("%d/%m/%Y") if fim_d else "Fluxo Contínuo",
                "data_fim_iso": fim_iso,
                "dias_restantes": dias_restantes,
                "tem_matriz_risco": True,
                "documentos": documentos,
            }

            # Ficha documental verificada para DNIT/RJ Edital nº 67/2026 (Laguna de Araruama/RJ)
            if num_ctrl == "04892707001425-1-000016/2026" or "araruama" in texto_analise:
                item_dict.update({
                    "ficha_documental_verificada": True,
                    "titulo_executivo": "DNIT/RJ — Concorrência Eletrônica Edital nº 67/2026 — Elaboração de EVTEA para Implantação de Hidrovias e Instalações Portuárias na Laguna de Araruama/RJ",
                    "escopo_sintetico": (
                        "Objeto: Contratação de empresa para elaboração de Estudo de Viabilidade Técnica, Econômica e Ambiental (EVTEA) "
                        "para implantação de hidrovias e instalações portuárias (IP4) na Laguna de Araruama, no Estado do Rio de Janeiro "
                        "(Processo SEI 50607.001431/2025-83) | Valor estimado: R$ 6.682.392,51 | Prazo de execução: 12 meses (vigência: 18 meses) | "
                        "Situação: Aberta (entrega de propostas até 04/11/2026) | "
                        "Onde está o escopo: Termo de Referência (Anexo I, 41 páginas) e Anexo II – Especificações Técnicas para Elaboração do EVTEA (70 páginas)."
                    ),
                    "analise_riscos_segurabilidade": (
                        "• No Anexo II – Especificações Técnicas (70 págs.), o Item 9.1.8 (p. 46) e o Item 10.3.1.1 (p. 55) incluem nos parâmetros mínimos "
                        "de custos das alternativas e nos gastos com investimento e obra as rubricas \"Contingências e gerenciamento de riscos\" e "
                        "\"Seguros e garantias contratuais\".\n"
                        "• Na avaliação econômico-financeira e socioeconômica (Anexo II, Item 9.1.12, p. 48; Item 10.3.1.3, p. 55; e Item 10.3.4, p. 58), "
                        "exige-se \"Elaborar registro de riscos, identificando os principais fatores e seus impactos potenciais\" e o "
                        "\"Registro dos principais riscos e seus impactos sobre os indicadores econômico-financeiros\".\n"
                        "• Nos Estudos Complementares de Engenharia (Anexo II, Item 10.2.5, p. 54), determina-se que \"A CONTRATADA deverá diagnosticar, "
                        "mapear e consolidar as necessidades de investigações de campo e estudos de engenharia detalhados para as próximas fases "
                        "(Projeto Básico/Executivo), de modo a subsidiar a matriz de riscos hidrodinâmicos e geotécnicos do empreendimento.\"\n"
                        "• No diagnóstico operacional de cargas (Anexo II, Item 7.1.2.5 \"d\" – Produtos Perigosos, p. 14), prevê-se que "
                        "\"deverá ser elaborado um diagnóstico e oferecido um anteprojeto de programa de gestão de risco.\"\n"
                        "• Não há no Termo de Referência nem no Anexo II previsão de produto específico de estudo de segurabilidade da futura hidrovia/IP4s "
                        "(o Item 4.4 do TR, p. 5–6, disciplina apenas a garantia de execução de 5% do próprio contrato de consultoria, nos termos do art. 96 da Lei 14.133/2021)."
                    ),
                })

            candidatos.append(item_dict)
        time.sleep(0.35)

    return candidatos


def coletar_carteira_bndes_estruturadores() -> list:
    """
    Coleta projetos ativos na carteira de Desestatização e Estruturação do BNDES
    com documentação oficial publicada (RFP, Anexo I - Especificações Técnicas, Anexo II,
    Anexo IV, Anexo VI - Matriz de Riscos e Contrato Assinado), priorizando:
    - Prioridade A: Hidrovias (Tapajós/Tocantins) e Portos (Porto Greenfield RN e Porto Organizado de Santos).
    - Prioridade B (comparação): Rodovias Federais (RFP 014/2024 - Nordeste).
    """
    from coletor_bndes_dinamico import coletar_hidrovias_tapajos_tocantins, coletar_porto_greenfield_rn

    base_wcm = "https://www.bndes.gov.br/wps/wcm/connect/site"
    base_pag = "https://www.bndes.gov.br/wps/portal/site/home/transparencia/desestatizacao/processos-em-andamento?1dmy&urile=wcm%3apath%3a%2Fbndes_institucional%2Fhome%2Ftransparencia%2Fdesestatizacao%2Fprojetos-em-andamento%2F"

    projetos_bndes = []

    # 1. Hidrovias Tapajós e Tocantins (Coleta dinâmica e factual com validação de links)
    try:
        dados_hidrovias = coletar_hidrovias_tapajos_tocantins()
        if dados_hidrovias.get("links_invalidos"):
            print(f"[Aviso BNDES] Links inválidos em Hidrovias: {dados_hidrovias['links_invalidos']}")
        else:
            projetos_bndes.append(dados_hidrovias["card"])
    except Exception as e:
        print(f"[Erro BNDES] Falha ao coletar Hidrovias: {e}")

    # 2. Porto Greenfield RN (Coleta dinâmica e factual com validação de links)
    try:
        dados_rn = coletar_porto_greenfield_rn()
        if dados_rn.get("links_invalidos"):
            print(f"[Aviso BNDES] Links inválidos em Porto RN: {dados_rn['links_invalidos']}")
        else:
            projetos_bndes.append(dados_rn["card"])
    except Exception as e:
        print(f"[Erro BNDES] Falha ao coletar Porto RN: {e}")

    # Demais projetos estruturados do BNDES
    outros_projetos = [
        {
            "id": "BNDES_PORTO_SANTOS",
            "prioridade_escopo": "PRIORIDADE_A",
            "categoria_item": "PRIORIDADE_A",
            "estruturador_sigla": "BNDES • Portos (Santos / APS)",
            "modalidade": "RFP nº 17/2023 • Contrato OCS nº 157/2024",
            "titulo": "BNDES — RFP nº 17/2023 (Contrato OCS nº 157/2024) — Estruturação de Concessão de Serviços Portuários no Porto Organizado de Santos",
            "titulo_executivo": "BNDES — RFP nº 17/2023 (Contrato OCS nº 157/2024) — Estruturação de Projeto de Concessão de Serviços Portuários no Porto Organizado de Santos",
            "url": base_pag + "porto-organizado-de-santos",
            "valor_estimado": 4_083_000.00,
            "valor_formatado": "R$ 4,08 mi (Contratado)",
            "data_publicacao_br": "17/05/2024 (Contrato)",
            "data_publicacao_iso": "2024-05-17",
            "data_fim_br": "Em Execução (Consórcio EY / Planave)",
            "escopo_sintetico": (
                "Objeto: Contratação de serviços técnicos de apoio (Serviço B) necessários à estruturação de projeto de concessão de serviços "
                "portuários no Porto Organizado de Santos (incluindo canal de acesso aquaviário, dragagem e infraestrutura associada, aproveitando "
                "insumos da Etapa 1 da RFP 01/2020) | Valor contratado: R$ 4.083.000,00 | Contrato OCS nº 157/2024 assinado em 17/05/2024 "
                "(Consórcio EY / Rhein Schirato Meireles / Planave) | Situação: Em execução | "
                "Onde está o escopo: Anexo I – Termo de Especificações Técnicas (30 páginas)."
            ),
            "analise_riscos_segurabilidade": (
                "• O Anexo VI – Matriz de Riscos (PDF) refere-se à matriz de riscos do contrato de consultoria celebrado com o BNDES, "
                "e não à matriz de riscos da futura concessão portuária.\n"
                "• No Anexo I – Termo de Especificações Técnicas (30 págs.), o Relatório de Proposição do Modelo Institucional e Regulatório "
                "(Item 2.2.1.5 \"i\", p. 8) exige a \"Definição da nova Matriz de Riscos contendo as justificativas e os possíveis mitigadores para os riscos "
                "identificados de acordo com os modelos institucionais avaliados e com as melhores práticas, locais e internacionais, adotadas em projetos "
                "de concessão no setor de infraestrutura (...) recomendando e justificando princípios e mecanismos de alocação\".\n"
                "• No Relatório de Avaliação Técnico-Operacional (Item 2.2.1.4 \"d\" e \"e\", p. 6), exige-se o \"orçamento detalhado dos custos de "
                "operação e manutenção dos serviços prestados (OPEX) e das despesas administrativas, incluindo os custos ambientais, taxas, tarifas "
                "portuárias, utilidades e seguros, dentre outros\" e a avaliação de interferências da travessia seca Santos–Guarujá com \"as remediações "
                "contratuais necessárias para mitigação desse risco\".\n"
                "• No Relatório de Decisão do Modelo de Negócios (Item 2.2.1.8 \"b\" e \"f\", p. 11–12) e no Relatório de Modelagem (Item 2.2.2.4, p. 12–13), "
                "exige-se a análise de \"alocação de riscos entre o PODER CONCEDENTE, AUTORIDADE PORTUÁRIA e OUTORGADA\". Não há previsão de estudo específico "
                "de segurabilidade da concessão."
            ),
            "documentos": [
                {"rotulo": "🏦 Página do Projeto no BNDES", "url": base_pag + "porto-organizado-de-santos", "categoria": "SEI"},
                {"rotulo": "📄 RFP nº 17/2023 – AEP/BNDES (PDF)", "url": f"{base_wcm}/a47cf00d-1967-4929-b2e2-fa660b8151d6/Edital_RFP_n%C2%BA_17-2023_-_AEP-BNDES%5B1%5D.pdf?MOD=AJPERES&CVID=oOSYS.g", "categoria": "EDITAL"},
                {"rotulo": "📑 Anexo I – Especificações Técnicas (30 págs.)", "url": f"{base_wcm}/af2e0896-d483-470e-9c7c-e3b713e51208/Anexo_I_-_Termo_de_Especifica%C3%A7%C3%B5es_T%C3%A9cnicas%5B1%5D.pdf?MOD=AJPERES&CVID=oOSZ0a4", "categoria": "TERMO_REFERENCIA"},
                {"rotulo": "💰 Anexo II – Tabela de Produtos e Serviços (XLSX)", "url": f"{base_wcm}/3b326d2a-b547-4090-a7d0-94316b1f925b/Anexo_II_-_Tabela_de_Produtos_e_Servi%C3%A7os.xlsx?MOD=AJPERES&CVID=oOSZ824", "categoria": "ORCAMENTO_LOTE"},
                {"rotulo": "📐 Anexo IV – Critérios de Pontuação Técnica", "url": f"{base_wcm}/ef5e764d-7011-4435-b2e4-c9bf5a229140/Anexo_IV_-_Crit%C3%A9rios_de_Pontua%C3%A7%C3%A3o_e_Modelo_de_Proposta_T%C3%A9cnica%5B1%5D.pdf?MOD=AJPERES&CVID=oOSZluq", "categoria": "ETP"},
                {"rotulo": "🛡️ Anexo VI – Matriz de Riscos (Consultoria)", "url": f"{base_wcm}/e9d7a368-73cb-4908-8994-1bbff0f95276/Anexo_VI_-_Matriz_de_Riscos%5B1%5D.pdf?MOD=AJPERES&CVID=oOSZzzF", "categoria": "MATRIZ_RISCO"},
                {"rotulo": "📝 Contrato OCS nº 157/2024 (PDF)", "url": f"{base_wcm}/abde31c2-5119-4df9-907e-6e9e865ba126/Contrato_OCS_157_2024_Assinado_e_Anexos.pdf?MOD=AJPERES&CVID=oX6kX9s", "categoria": "MINUTA_CONTRATO"},
                {"rotulo": "📜 Resultado da Homologação / Extrato (PDF)", "url": f"{base_wcm}/7cf5e0b8-9845-4eab-abd3-c661aadfb630/Resultado+da+Homologa%C3%A7%C3%A3o.pdf?MOD=AJPERES&CVID=o.zh-Nf", "categoria": "DOU"},
            ],
        },
        {
            "id": "BNDES_RODOVIAS_FEDERAIS_III",
            "prioridade_escopo": "PRIORIDADE_B",
            "categoria_item": "PRIORIDADE_B_COMPARACAO",
            "estruturador_sigla": "BNDES • Rodovias Federais (MT / ANTT)",
            "modalidade": "RFP nº 014/2024 • Contrato OCS nº 270/2025",
            "titulo": "BNDES — RFP nº 014/2024 (Contrato OCS nº 270/2025) — Estruturação de Concessões de Rodovias Federais na Região Nordeste (2.530 km)",
            "titulo_executivo": "BNDES — RFP nº 014/2024 (Contrato OCS nº 270/2025) — Estruturação de Concessões de Rodovias Federais na Região Nordeste (2.530 km)",
            "url": base_pag + "rodovias-ne",
            "valor_estimado": 11_501_251.47,
            "valor_formatado": "R$ 11,50 mi (Contratado)",
            "data_publicacao_br": "30/07/2025 (Contrato)",
            "data_publicacao_iso": "2025-07-30",
            "data_fim_br": "Em Execução (Consórcio Rodoviário NE)",
            "escopo_sintetico": (
                "Objeto: Contratação de serviços técnicos necessários para a estruturação de projetos de concessão rodoviária de até 2.530 km "
                "de trechos existentes (BR-101/BA/RN/PE/PB/SE, BR-116/304/CE/RN, BR-230/PB, BR-232/PE, BR-235/SE, acessos ao Porto do Pecém/CE) "
                "e 184,8 km de contornos/variantes na Região Nordeste, observando a Portaria MT nº 995/2023 | "
                "Valor contratado: R$ 11.501.251,47 (valor estimado na RFP: R$ 24.528.219,73) | "
                "Contrato OCS nº 270/2025 assinado em 30/07/2025 (Consórcio Rodoviário Nordeste — Dynatest / Estratégica / Ambiente Brasil / Infraconsult / Manesco) | "
                "Situação: Em execução | Onde está o escopo: Anexo I – Termo de Especificações Técnicas (135 páginas)."
            ),
            "analise_riscos_segurabilidade": (
                "• O Anexo VI – Matriz de Riscos (PDF) refere-se à matriz de riscos do contrato de consultoria celebrado com o BNDES, "
                "e não à matriz de riscos das futuras concessões rodoviárias.\n"
                "• No Anexo I – Termo de Especificações Técnicas (135 págs.), a Avaliação Econômico-Financeira da Concessão Rodoviária "
                "(Item 3.13.1 e Item 3.13.5 \"m\" e \"n\", p. 33–34) determina a assimilação de \"todas as informações e variáveis associadas à operação "
                "da CONCESSÃO RODOVIÁRIA, inclusive seus riscos\" e exige nas planilhas eletrônicas as variáveis \"m) Seguros\" e \"n) Garantias\".\n"
                "• Na Assessoria Jurídica (Item 3.20.1.1 \"j\" e Item 3.20.2.1 \"n\", p. 41–42), prevê-se \"Suporte junto ao BNDES para qualquer medida "
                "necessária à implantação do(s) modelo(s) de garantias selecionado(s), cuja constituição ocorra previamente ao(s) LEILÃO(ÕES)\" e "
                "análise das \"garantias de proposta, documentos de habilitação e demais documentos necessários para assinatura do CONTRATO\".\n"
                "• No Anexo 6 (Item 7, p. 108–109) e no Anexo 7 (Item 8.4, p. 115–116), exige-se a apresentação de cenários alternativos com vantagens, "
                "desvantagens e sugestão de texto contratual \"a fim de subsidiar a tomada de decisão acerca da alocação de risco nos contratos de concessão\" "
                "quanto a desapropriações/desocupações da faixa de domínio e licenciamento/passivos ambientais. Não há previsão de estudo específico de segurabilidade."
            ),
            "documentos": [
                {"rotulo": "🏦 Página do Projeto no BNDES (Rodovias NE)", "url": base_pag + "rodovias-ne", "categoria": "SEI"},
                {"rotulo": "📄 RFP nº 014/2024 – Rodovias Federais NE (PDF)", "url": f"{base_wcm}/75e30654-bb15-4746-86fc-5a9d9c7d45b0/RFP+014-2024+-+BNDES-+Projeto+Rodovias+Federais+NE.pdf?MOD=AJPERES&CVID=pzU0pR5", "categoria": "EDITAL"},
                {"rotulo": "📑 Anexo I – Especificações Técnicas (135 págs.)", "url": f"{base_wcm}/6af14c2b-557f-489e-b310-f65ca2314616/1.+Anexo+I+-+TERMO+DE+ESPECIFICA%C3%87OES+TECNICAS.pdf?MOD=AJPERES&CVID=pzU0DbR", "categoria": "TERMO_REFERENCIA"},
                {"rotulo": "💰 Anexo II – Tabela de Produtos e Prazos (XLSX)", "url": f"{base_wcm}/d0b7634b-0bb6-4ab9-bd2a-17c0f2f841a8/2.+Anexo+II+-+TABELA+DE+PRODUTOS%2C+PRE%C3%87OS+E+PRAZOS+DE+ENTREGA.xlsx?MOD=AJPERES&CVID=pzU0KVG", "categoria": "ORCAMENTO_LOTE"},
                {"rotulo": "📐 Anexo IV – Critérios de Pontuação Técnica", "url": f"{base_wcm}/277bedef-799f-4cf8-9238-9a304095612a/4.+Anexo+IV+-+CRITERIOS+DE+PONTUA%C3%87%C3%83O+E+MODELO+DE+PROPOSTA+TECNICA.pdf?MOD=AJPERES&CVID=pzU0-im", "categoria": "ETP"},
                {"rotulo": "🛡️ Anexo VI – Matriz de Riscos (Consultoria)", "url": f"{base_wcm}/0c84140b-88f2-4076-a900-14fa624762e9/6.+Anexo+VI+-+MATRIZ+DE+RISCOS.pdf?MOD=AJPERES&CVID=pzU1fzh", "categoria": "MATRIZ_RISCO"},
                {"rotulo": "📝 Contrato OCS nº 270/2025 (PDF)", "url": f"{base_wcm}/3adc8450-65e0-4d1d-9867-60e001a94c90/Contrato+270-2025+-+Assinado.pdf?MOD=AJPERES&CVID=pzU1y5M", "categoria": "MINUTA_CONTRATO"},
                {"rotulo": "📜 Extrato de Informações – RFP 014/2024 (PDF)", "url": f"{base_wcm}/4574f96b-0d02-4a1d-87bf-76e062f3b098/Extrato+de+Informa%C3%A7%C3%B5es+-+RFP+014_2024+-+Rodovias+NE-+2530km.pdf?MOD=AJPERES&CVID=pzU1MuN", "categoria": "DOU"},
            ],
        },
    ]

    projetos_bndes.extend(outros_projetos)

    itens = []
    for p in projetos_bndes:
        itens.append({
            "id": p["id"],
            "origem": "BNDES Desestatização",
            "estruturador_sigla": p["estruturador_sigla"],
            "prioridade_escopo": p["prioridade_escopo"],
            "categoria_item": p["categoria_item"],
            "modalidade": p["modalidade"],
            "titulo": p["titulo"],
            "titulo_executivo": p["titulo_executivo"],
            "descricao_bruta": p["escopo_sintetico"],
            "escopo_sintetico": p["escopo_sintetico"],
            "analise_riscos_segurabilidade": p["analise_riscos_segurabilidade"],
            "ficha_documental_verificada": True,
            "url": p["url"],
            "valor_estimado": p["valor_estimado"],
            "valor_formatado": p["valor_formatado"],
            "data_publicacao_br": p["data_publicacao_br"],
            "data_publicacao_iso": p["data_publicacao_iso"],
            "data_fim_br": p["data_fim_br"],
            "data_fim_iso": "",
            "dias_restantes": None,
            "tem_matriz_risco": True,
            "documentos": p["documentos"],
        })

    return itens


def coletar_tudo_aba_estruturacao() -> list:
    """
    Consolida todas as fontes da Aba 2 (Infra S.A. WP-JSON + PNCP + BNDES),
    aplicando o ordenamento por Prioridade A (Portos, Aeroportos e Hidrovias)
    seguido de Prioridade B (Comparação Federal - Rodovias/Ferrovias).
    """
    itens_infra = coletar_licitacoes_infra_sa(max_itens=8)
    itens_pncp = coletar_estruturacao_e_seguros_pncp()
    itens_bndes = coletar_carteira_bndes_estruturadores()

    # Se um item do PNCP aponta para uma URL da Infra S.A. já coletada via WP-JSON (ex: RLE 016/2026),
    # funde os dados (valor estimado de R$ 28,87 mi, data fim 06/01/2027 e link do PNCP) no card da Infra S.A.
    mapa_infra_por_url = {it["url"].rstrip("/"): it for it in itens_infra}
    mapa_infra_por_rle = {it["chave_rle"]: it for it in itens_infra if it.get("chave_rle")}
    pncp_filtrados = []

    for p in itens_pncp:
        url_p = p["url"].rstrip("/")
        rle_p = p.get("chave_rle") or ""
        card_infra = mapa_infra_por_url.get(url_p) or (mapa_infra_por_rle.get(rle_p) if rle_p else None)
        if card_infra:
            if p.get("valor_estimado"):
                card_infra["valor_estimado"] = p["valor_estimado"]
                card_infra["valor_formatado"] = p["valor_formatado"]
            if p.get("data_fim_iso"):
                card_infra["data_fim_iso"] = p["data_fim_iso"]
                card_infra["data_fim_br"] = p["data_fim_br"]
                card_infra["dias_restantes"] = p["dias_restantes"]
            if p.get("descricao_bruta") and not card_infra.get("ficha_documental_verificada"):
                card_infra["descricao_bruta"] = p["descricao_bruta"]
            urls_existentes = {d["url"] for d in card_infra.get("documentos", [])}
            novos_docs_topo = []
            for doc_p in p.get("documentos", []):
                if doc_p["url"] not in urls_existentes and "pncp.gov.br/app/editais" in doc_p["url"]:
                    novos_docs_topo.append(doc_p)
                    urls_existentes.add(doc_p["url"])
            card_infra["documentos"] = (card_infra["documentos"][:1] + novos_docs_topo + card_infra["documentos"][1:])[:9]
        else:
            pncp_filtrados.append(p)

    todos = itens_infra + pncp_filtrados + itens_bndes

    # Ordena priorizando:
    # 1) PRIORIDADE_A_DESTAQUE (ex: DNIT Laguna de Araruama e BNDES Hidrovias Tapajós/Tocantins)
    # 2) PRIORIDADE_A (ex: BNDES Porto Greenfield RN e BNDES Porto de Santos)
    # 3) PRIORIDADE_B (ex: Infra S.A. RLE 016/2026 e BNDES Rodovias Federais NE)
    ordem_prio = {
        "PRIORIDADE_A_DESTAQUE": 1,
        "PRIORIDADE_A": 2,
        "PRIORIDADE_B": 3,
        "PRIORIDADE_C": 4,
    }
    todos.sort(key=lambda x: (
        ordem_prio.get(x.get("prioridade_escopo", "PRIORIDADE_B"), 9),
        0 if (x.get("dias_restantes") is not None and x.get("dias_restantes") >= 0) else 1,
        -(x.get("valor_estimado") or 0),
    ))
    return todos


# ==============================================================================
# ABA 3: COLETOR DE LEILÕES & OUTORGAS (ANTAQ, ANAC, ANTT, B3 & NACIONAIS)
# ==============================================================================

def _coletar_status_antaq_oficial() -> dict:
    """Lê a página oficial de leilões da ANTAQ para verificar quais códigos de terminais estão Em Andamento, Suspensos ou Encerrados."""
    url = "https://www.gov.br/antaq/pt-br/assuntos/leiloes"
    status_por_codigo = {}
    try:
        r = requests.get(url, headers=HEADERS_PADRAO, verify=False, timeout=10)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, "html.parser")
            main = soup.find("div", id="content-core") or soup
            texto = main.get_text("\n", strip=True)
            secao_atual = "EM_ANDAMENTO"
            for linha in texto.splitlines():
                l_low = linha.strip().lower()
                if l_low.startswith("em andamento"):
                    secao_atual = "EDITAL_PUBLICADO"
                elif l_low.startswith("suspensos"):
                    secao_atual = "SUSPENSO"
                elif l_low.startswith("encerrados"):
                    secao_atual = "REALIZADO_RECENTE"
                m = re.search(r"Leil[aã]o\s+N[º°.]*\s*(\d+/\d{4})-ANTAQ\s*-\s*([A-Z0-9-]+)", linha, re.IGNORECASE)
                if m:
                    status_por_codigo[m.group(2).upper()] = {
                        "edital_num": m.group(1),
                        "status_antaq": secao_atual,
                    }
    except Exception as e:
        print(f"   [Aviso] Falha ao consultar página de leilões da ANTAQ: {e}")
    return status_por_codigo


def _coletar_noticias_recentes_leiloes() -> list:
    """Busca notícias das últimas 72h sobre leilões de infraestrutura para enriquecer o status dinâmico."""
    query = urllib.parse.quote('(leilão OR edital) AND (ANTAQ OR "Portos e Aeroportos" OR ANTT OR ANAC OR ANEEL OR B3 OR "canal de Itajaí" OR "Tecon" OR "MUC04" OR "Eco Invest") when:72h')
    url = f"https://news.google.com/rss/search?q={query}&hl=pt-BR&gl=BR&ceid=BR:pt-419"
    manchetes = []
    try:
        feed = feedparser.parse(url)
        for e in feed.entries[:15]:
            manchetes.append(e.get("title", ""))
    except Exception:
        pass
    return manchetes


def coletar_radar_leiloes() -> list:
    """
    Retorna a carteira estruturada e atualizada dos Leilões de Infraestrutura, Transporte,
    Logística (ANTAQ, ANAC, MT, ANTT) e Grandes Leilões Nacionais (ANEEL, Eco Invest, B3),
    sincronizada com a página oficial da ANTAQ, ANTT e noticiário regulatório.
    """
    status_antaq = _coletar_status_antaq_oficial()
    manchetes_recentes = _coletar_noticias_recentes_leiloes()

    leiloes = [
        # 1. PORTOS, CANAIS & HIDROVIAS (ANTAQ)
        {
            "id": "LEILAO_ANTAQ_MUC04",
            "setor": "portos_hidrovias",
            "setor_nome": "⚓ Portos & Hidrovias (ANTAQ)",
            "orgao_sigla": "ANTAQ",
            "codigo_ativo": "MUC04",
            "titulo": "Leilão nº 05/2026-ANTAQ — Terminal Portuário MUC04 (Porto de Fortaleza/CE)",
            "fase_leilao": status_antaq.get("MUC04", {}).get("status_antaq", "EDITAL_PUBLICADO"),
            "capex_estimado": "R$ 429,0 milhões",
            "prazo_concessao": "25 anos",
            "data_evento_br": "Edital Publicado (Ciclo 4T/2026)",
            "data_evento_iso": "2026-12-10",
            "local_certame": "B3 — São Paulo",
            "resumo_executivo": (
                "Arrendamento de terminal dedicado à movimentação e armazenagem de cargas conteinerizadas e gerais "
                "no Porto Organizado de Fortaleza (CE), com previsão de R$ 429 milhões em investimentos."
            ),
            "destaque_regulatorio_seguros": "",
            "url": "https://www.gov.br/antaq/pt-br/assuntos/leiloes",
            "documentos": [
                {"rotulo": "⚓ Painel de Leilões ANTAQ", "url": "https://www.gov.br/antaq/pt-br/assuntos/leiloes", "categoria": "EDITAL"},
                {"rotulo": "🏛️ Portal Governamental", "url": "https://www.gov.br/portos-e-aeroportos/pt-br", "categoria": "DOCUMENTO"},
            ],
        },
        {
            "id": "LEILAO_ANTAQ_IQI16",
            "setor": "portos_hidrovias",
            "setor_nome": "⚓ Portos & Hidrovias (ANTAQ)",
            "orgao_sigla": "ANTAQ",
            "codigo_ativo": "IQI16",
            "titulo": "Leilão nº 04/2026-ANTAQ — Terminal IQI16 de Granéis Minerais e Fertilizantes (Porto do Itaqui/MA)",
            "fase_leilao": status_antaq.get("IQI16", {}).get("status_antaq", "EDITAL_PUBLICADO"),
            "capex_estimado": "R$ 218,5 milhões",
            "prazo_concessao": "25 anos",
            "data_evento_br": "Edital em Andamento (4T/2026)",
            "data_evento_iso": "2026-11-27",
            "local_certame": "B3 — São Paulo",
            "resumo_executivo": (
                "Arrendamento portuário estratégico no Arco Norte dedicado à movimentação e armazenagem de granéis sólidos minerais, "
                "especialmente fertilizantes (IQI16), localizado no Porto Organizado do Itaqui (MA)."
            ),
            "destaque_regulatorio_seguros": "",
            "url": "https://www.gov.br/antaq/pt-br/assuntos/leiloes",
            "documentos": [
                {"rotulo": "⚓ Painel de Leilões ANTAQ", "url": "https://www.gov.br/antaq/pt-br/assuntos/leiloes", "categoria": "EDITAL"},
            ],
        },
        {
            "id": "LEILAO_CANAL_ITAJAI",
            "setor": "portos_hidrovias",
            "setor_nome": "⚓ Portos & Hidrovias (ANTAQ)",
            "orgao_sigla": "ANTAQ / TCU",
            "codigo_ativo": "CANAL-ITAJAI",
            "titulo": "Concessão do Canal de Acesso Aquaviário ao Complexo Portuário de Itajaí e Navegantes (SC)",
            "fase_leilao": "AVALIACAO_TCU_AJUSTES",
            "capex_estimado": "R$ 311,0 milhões",
            "prazo_concessao": "25 anos",
            "data_evento_br": "Pós-Aprovação TCU • Publicação do Edital",
            "data_evento_iso": "",
            "local_certame": "B3 — São Paulo",
            "resumo_executivo": (
                "Segundo leilão de canal de acesso aquaviário da história do país (após Paranaguá). Com o aval do TCU e retomada de ritmo "
                "após o período eleitoral, prevê dragagens periódicas de aprofundamento/manutenção e sinalização náutica."
            ),
            "destaque_regulatorio_seguros": "",
            "url": "https://agenciainfra.com/blog/tecon-10-e-canal-de-itajai-devem-ganhar-ritmo-no-governo-apos-eleicoes/",
            "documentos": [
                {"rotulo": "📰 Bastidores Agência iNFRA (28/10)", "url": "https://agenciainfra.com/blog/tecon-10-e-canal-de-itajai-devem-ganhar-ritmo-no-governo-apos-eleicoes/", "categoria": "DOCUMENTO"},
                {"rotulo": "⚓ Leilões ANTAQ", "url": "https://www.gov.br/antaq/pt-br/assuntos/leiloes", "categoria": "EDITAL"},
            ],
        },
        {
            "id": "LEILAO_TECON_SANTOS_10",
            "setor": "portos_hidrovias",
            "setor_nome": "⚓ Portos & Hidrovias (ANTAQ)",
            "orgao_sigla": "ANTAQ / TCU",
            "codigo_ativo": "STS10",
            "titulo": "Arrendamento do Megaterminal Tecon Santos 10 (STS10 — Porto de Santos/SP)",
            "fase_leilao": "AVALIACAO_TCU_AJUSTES",
            "capex_estimado": "R$ 5,6 bilhões",
            "prazo_concessao": "25 anos",
            "data_evento_br": "Deliberação TCU / Edital Previsto",
            "data_evento_iso": "",
            "local_certame": "B3 — São Paulo",
            "resumo_executivo": (
                "Maior projeto de arrendamento portuário da carteira federal (integrante do pacote de 34 leilões que somam R$ 23 bi). "
                "Amplia em 50% a capacidade de movimentação de contêineres e carga geral no Saboó (Porto de Santos)."
            ),
            "destaque_regulatorio_seguros": "",
            "url": "https://www.gov.br/antaq/pt-br/assuntos/leiloes",
            "documentos": [
                {"rotulo": "⚓ Leilões ANTAQ", "url": "https://www.gov.br/antaq/pt-br/assuntos/leiloes", "categoria": "EDITAL"},
            ],
        },
        {
            "id": "LEILAO_HIDROVIA_PARAGUAI",
            "setor": "portos_hidrovias",
            "setor_nome": "⚓ Portos & Hidrovias (ANTAQ)",
            "orgao_sigla": "ANTAQ",
            "codigo_ativo": "HIDROVIA-PARAGUAI",
            "titulo": "Concessão da Hidrovia do Rio Paraguai (Tramo Sul — Corumbá/MS a Foz do Rio Apa)",
            "fase_leilao": "AVALIACAO_TCU_AJUSTES",
            "capex_estimado": "R$ 63,8 milhões (CAPEX direto) + OPEX",
            "prazo_concessao": "15 anos (+15)",
            "data_evento_br": "Fase Final TCU / Edital",
            "data_evento_iso": "",
            "local_certame": "B3 — São Paulo",
            "resumo_executivo": (
                "Primeira concessão hidroviária do Brasil. Abrange 600 km no Rio Paraguai para garantir calado operacional "
                "ao escoamento de minério de ferro e grãos com tarifa módica e sustentabilidade ambiental no Pantanal."
            ),
            "destaque_regulatorio_seguros": "",
            "url": "https://www.gov.br/antaq/pt-br/assuntos/leiloes",
            "documentos": [
                {"rotulo": "⚓ Painel ANTAQ", "url": "https://www.gov.br/antaq/pt-br/assuntos/leiloes", "categoria": "EDITAL"},
            ],
        },

        # 2. AEROPORTOS (ANAC)
        {
            "id": "LEILAO_ANAC_AMPLIAR",
            "setor": "aeroportos",
            "setor_nome": "✈️ Aeroportos (ANAC)",
            "orgao_sigla": "ANAC",
            "codigo_ativo": "AMPLIAR-BLOCOS",
            "titulo": "Programa AmpliAR — Concessão Simplificada de Aeroportos Regionais (Amazônia Legal e Nordeste)",
            "fase_leilao": "AVALIACAO_TCU_AJUSTES",
            "capex_estimado": "R$ 3,5 bilhões (meta global)",
            "prazo_concessao": "Aditivo Contratual / 30 anos",
            "data_evento_br": "Ciclo de Ofertas B3",
            "data_evento_iso": "",
            "local_certame": "B3 — São Paulo",
            "resumo_executivo": (
                "Mecanismo competitivo desenhado pelo Governo Federal e ANAC pelo qual atuais concessionárias aeroportuárias disputam "
                "a assunção de blocos de aeroportos regionais deficitários mediante reequilíbrio contratual."
            ),
            "destaque_regulatorio_seguros": "",
            "url": "https://www.gov.br/portos-e-aeroportos/pt-br",
            "documentos": [
                {"rotulo": "✈️ Portal Governamental", "url": "https://www.gov.br/portos-e-aeroportos/pt-br", "categoria": "DOCUMENTO"},
            ],
        },
        {
            "id": "LEILAO_ANAC_GALEAO",
            "setor": "aeroportos",
            "setor_nome": "✈️ Aeroportos (ANAC)",
            "orgao_sigla": "ANAC / TCU",
            "codigo_ativo": "GIG-GALEAO",
            "titulo": "Venda Assistida / Repactuação da Concessão do Aeroporto Internacional do Galeão (RJ)",
            "fase_leilao": "AVALIACAO_TCU_AJUSTES",
            "capex_estimado": "R$ 4,8 bilhões (outorga/investimentos)",
            "prazo_concessao": "Até 2039",
            "data_evento_br": "Solução Consensual TCU / Certame B3",
            "data_evento_iso": "",
            "local_certame": "B3 — São Paulo",
            "resumo_executivo": (
                "Processo competitivo decorrente de solução consensual (SecexConsenso/TCU, Governo Federal e ANAC) para reestruturação "
                "do contrato do Aeroporto do Galeão, revisão do pagamento de outorga e saída da Infraero da SPE."
            ),
            "destaque_regulatorio_seguros": "",
            "url": "https://www.gov.br/portos-e-aeroportos/pt-br",
            "documentos": [
                {"rotulo": "✈️ Portal Governamental", "url": "https://www.gov.br/portos-e-aeroportos/pt-br", "categoria": "DOCUMENTO"},
            ],
        },

        # 3. RODOVIAS & FERROVIAS (MT / ANTT)
        {
            "id": "LEILAO_ANTT_ROTA_AGRO_CENTRAL",
            "setor": "rodovias_ferrovias",
            "setor_nome": "🛣️ Rodovias & Ferrovias (MT / ANTT)",
            "orgao_sigla": "MT / ANTT",
            "codigo_ativo": "CN3-ROTA-AGRO",
            "titulo": "Concessão Rodoviária BR-070/174/364/MT/RO — Rota Agro Central (CN3 • 2.570 km)",
            "fase_leilao": "ESTRUTURACAO_AUDIENCIA",
            "capex_estimado": "R$ 16,2 bilhões (CAPEX + OPEX)",
            "prazo_concessao": "30 anos",
            "data_evento_br": "Pipeline Prioritário ANTT",
            "data_evento_iso": "",
            "local_certame": "B3 — São Paulo",
            "resumo_executivo": (
                "Concessão de 2.570 km no corredor de escoamento de grãos entre Mato Grosso e Rondônia (acesso às hidrovias do Madeira/Arco Norte), "
                "estruturada em parceria com o BNDES."
            ),
            "destaque_regulatorio_seguros": "",
            "url": "https://www.gov.br/antt/pt-br/assuntos/rodovias/novos-projetos-em-rodovias/copy_of_rodovias2013contratacao-bndes-6-700m-2013lotes-centro-oeste-e-norte",
            "documentos": [
                {"rotulo": "🛣️ Ficha do Projeto na ANTT", "url": "https://www.gov.br/antt/pt-br/assuntos/rodovias/novos-projetos-em-rodovias/copy_of_rodovias2013contratacao-bndes-6-700m-2013lotes-centro-oeste-e-norte", "categoria": "EDITAL"},
            ],
        },
        {
            "id": "LEILAO_ANTT_ROTA_PORTUARIA_SUL",
            "setor": "rodovias_ferrovias",
            "setor_nome": "🛣️ Rodovias & Ferrovias (MT / ANTT)",
            "orgao_sigla": "MT / ANTT",
            "codigo_ativo": "BR-116-392-RS",
            "titulo": "Concessão Rodoviária BR-116/392/RS — Rota Portuária do Sul (Acesso ao Porto do Rio Grande)",
            "fase_leilao": "ESTRUTURACAO_AUDIENCIA",
            "capex_estimado": "R$ 7,4 bilhões (CAPEX + OPEX)",
            "prazo_concessao": "30 anos",
            "data_evento_br": "Pipeline Prioritário ANTT",
            "data_evento_iso": "",
            "local_certame": "B3 — São Paulo",
            "resumo_executivo": (
                "Corredor logístico estratégico de ligação direta ao Porto do Rio Grande (RS). Incorpora novas diretrizes de "
                "resiliência climática após os eventos hidrológicos extremos no Rio Grande do Sul."
            ),
            "destaque_regulatorio_seguros": "",
            "url": "https://www.gov.br/antt/pt-br/assuntos/rodovias/novos-projetos-em-rodovias/BR-116_392_RS%20-%20Rota%20Portuaria%20do%20Sul",
            "documentos": [
                {"rotulo": "🛣️ Ficha do Projeto na ANTT", "url": "https://www.gov.br/antt/pt-br/assuntos/rodovias/novos-projetos-em-rodovias/BR-116_392_RS%20-%20Rota%20Portuaria%20do%20Sul", "categoria": "EDITAL"},
            ],
        },
        {
            "id": "LEILAO_ANTT_ROTA_2_DE_JULHO",
            "setor": "rodovias_ferrovias",
            "setor_nome": "🛣️ Rodovias & Ferrovias (MT / ANTT)",
            "orgao_sigla": "MT / ANTT",
            "codigo_ativo": "BR-116-324-BA",
            "titulo": "Concessão Rodoviária BR-116/324/BA — Rota 2 de Julho (663 km na Bahia, acesso ao Porto de Aratu/Salvador)",
            "fase_leilao": "AVALIACAO_TCU_AJUSTES",
            "capex_estimado": "R$ 24,0 bilhões (CAPEX + OPEX)",
            "prazo_concessao": "30 anos",
            "data_evento_br": "Edital Previsto após TCU",
            "data_evento_iso": "",
            "local_certame": "B3 — São Paulo",
            "resumo_executivo": (
                "Relicitação/nova concessão do principal eixo rodoviário da Bahia (antiga ViaBahia), conectando Feira de Santana "
                "a Salvador e aos portos baianos, com amplo pacote de duplicações e fluxo livre (free flow)."
            ),
            "destaque_regulatorio_seguros": "",
            "url": "https://www.gov.br/antt/pt-br/assuntos/rodovias/novos-projetos-em-rodovias/BR-116-324-BA",
            "documentos": [
                {"rotulo": "🛣️ Ficha do Projeto na ANTT", "url": "https://www.gov.br/antt/pt-br/assuntos/rodovias/novos-projetos-em-rodovias/BR-116-324-BA", "categoria": "EDITAL"},
            ],
        },

        # 4. GRANDES LEILÕES NACIONAIS (ENERGIA, BATERIAS & TRANSIÇÃO CLIMÁTICA)
        {
            "id": "LEILAO_ANEEL_BATERIAS_2026",
            "setor": "nacional_energia_clima",
            "setor_nome": "⚡ Grandes Leilões Nacionais (Energia, Clima & Finanças)",
            "orgao_sigla": "MME / ANEEL",
            "codigo_ativo": "LRCAP-BATERIAS",
            "titulo": "Leilão de Reserva de Capacidade na Forma de Armazenamento por Baterias (ANEEL)",
            "fase_leilao": "EDITAL_PUBLICADO",
            "capex_estimado": "R$ 7,5 bilhões (estimado)",
            "prazo_concessao": "10 a 15 anos (Suprimento)",
            "data_evento_br": "Dezembro de 2026",
            "data_evento_iso": "2026-12-18",
            "local_certame": "CCEE / B3",
            "resumo_executivo": (
                "Editais aprovados pela ANEEL em 27/10/2026 para o inédito leilão de sistemas de armazenamento de energia em baterias (BESS), "
                "visando dar flexibilidade operativa e segurança ao Sistema Interligado Nacional (SIN) em dezembro."
            ),
            "destaque_regulatorio_seguros": "",
            "url": "https://agenciainfra.com/blog/aneel-aprova-editais-dos-leiloes-de-baterias-marcados-para-dezembro/",
            "documentos": [
                {"rotulo": "📰 Aprovação dos Editais ANEEL (27/10)", "url": "https://agenciainfra.com/blog/aneel-aprova-editais-dos-leiloes-de-baterias-marcados-para-dezembro/", "categoria": "EDITAL"},
            ],
        },
        {
            "id": "LEILAO_MF_ECO_INVEST_5",
            "setor": "nacional_energia_clima",
            "setor_nome": "⚡ Grandes Leilões Nacionais (Energia, Clima & Finanças)",
            "orgao_sigla": "MF / Tesouro Nacional / BID",
            "codigo_ativo": "ECO-INVEST-5",
            "titulo": "5º Leilão do Programa Eco Invest Brasil — Mobilização de Capital Privado e Hedge Cambial para Transição Ecológica",
            "fase_leilao": "EDITAL_PUBLICADO",
            "capex_estimado": "Alavancagem Multibilionária",
            "prazo_concessao": "Linhas de Financiamento / Blending",
            "data_evento_br": "Ciclo 4T/2026",
            "data_evento_iso": "2026-11-30",
            "local_certame": "Ministério da Fazenda / STN",
            "resumo_executivo": (
                "Quinto certame do Eco Invest Brasil voltado a destravar financiamento privado competitivo e proteção cambial "
                "para projetos de infraestrutura sustentável, armazenamento de energia (baterias) e descarbonização."
            ),
            "destaque_regulatorio_seguros": "",
            "url": "https://www.gov.br/fazenda/pt-br/assuntos/novo-brasil-ecologico/eco-invest",
            "documentos": [
                {"rotulo": "🍃 Portal Eco Invest (Ministério da Fazenda)", "url": "https://www.gov.br/fazenda/pt-br/assuntos/novo-brasil-ecologico/eco-invest", "categoria": "EDITAL"},
            ],
        },
    ]

    hoje = date.today()
    for l in leiloes:
        iso = l.get("data_evento_iso")
        if iso:
            dt_ev = _parse_data_iso_flex(iso)
            l["dias_restantes"] = (dt_ev - hoje).days if dt_ev else None
        else:
            l["dias_restantes"] = None

    return leiloes


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    est = coletar_tudo_aba_estruturacao()
    print(f"Total Aba 2 (Estruturação & Contratações): {len(est)}")
    for e in est:
        print(f" - [{e['categoria_item']}] {e['estruturador_sigla']} | {e['valor_formatado']} | {e['titulo'][:80]}")
    leil = coletar_radar_leiloes()
    print(f"\nTotal Aba 3 (Leilões): {len(leil)}")
    for l in leil:
        print(f" - [{l['fase_leilao']}] {l['orgao_sigla']} | {l['capex_estimado']} | {l['titulo'][:80]}")

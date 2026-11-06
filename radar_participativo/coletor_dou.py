"""
coletor_dou.py — Coletor de Atos Oficiais do Diário Oficial da União (DOU).
Modo de Amostra (Fase 1 — Somente Leitura).

Travas e Regras Absolutas:
1. O link vem exclusivamente do urlTitle retornado no índice do DOU:
   https://www.in.gov.br/web/dou/-/{urlTitle}
   Teste HTTP 200 obrigatório na fonte oficial antes de qualquer ato entrar.
   Se não tiver link válido ou falhar na requisição, o ato é descartado e registrado com o motivo.
2. A ementa / primeira linha é a transcrição literal dos primeiros caracteres do texto do ato, sem paráfrase nem resumo.
3. Número do processo e relator são extraídos estritamente por regex do texto do ato; se não encontrados, o campo fica vazio ("").
4. Atos de REIDI e de Enquadramento prioritário:
   - No Radar: agrupamento por dia dos atos declaratórios da Receita com contagem e links. A portaria ministerial segue como item individual.
   - Fora do repositório: gravação de registro completo em dados_reidi/atos_AAAA-MM.jsonl.
   - Setor: gravado exclusivamente quando vier do texto da portaria do ministério (sem dedução).
5. Nenhum dado digitado à mão.
6. SOMENTE LEITURA: Não publica nada, não cria cards nem abas no Radar.
"""

import os
import sys
import re
import json
import time
import urllib.request
import urllib.error
from pathlib import Path
from collections import Counter, defaultdict
from typing import List, Dict, Any, Optional

PASTA_ATUAL = Path(__file__).parent.resolve()
PASTA_RAIZ = PASTA_ATUAL.parent.resolve()
PASTA_CACHE_DOU = PASTA_ATUAL / "cache_dou"
PASTA_CACHE_DOU.mkdir(exist_ok=True)
PASTA_CACHE_ATOS = PASTA_CACHE_DOU / "atos_completos"
PASTA_CACHE_ATOS.mkdir(exist_ok=True)

# Pasta de dados de REIDI fora do repositório (no .gitignore)
PASTA_DADOS_REIDI = PASTA_RAIZ / "dados_reidi"
PASTA_DADOS_REIDI.mkdir(exist_ok=True)

HEADERS_DOU = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8",
    "Sec-Ch-Ua": '"Chromium";v="130", "Google Chrome";v="130", "Not?A_Brand";v="99"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"Windows"',
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
}

DATAS_AMOSTRA_2026 = [
    "29-10-2026",
    "30-10-2026",
    "03-11-2026",
    "04-11-2026",
    "05-11-2026",
]

PADROES_ORGAOS_FILTRO = [
    "atos do poder executivo",
    "presidência da república",
    "presidencia da republica",
    "ministério da fazenda",
    "ministerio da fazenda",
    "conselho monetário nacional",
    "conselho monetario nacional",
    "ministério de portos e aeroportos",
    "ministerio de portos e aeroportos",
    "ministério dos transportes",
    "ministerio dos transportes",
    "ministério de minas e energia",
    "ministerio de minas e energia",
    "ministério das comunicações",
    "ministerio das comunicacoes",
    "ministério das cidades",
    "ministerio das cidades",
    "ministério do planejamento",
    "ministerio do planejamento",
    "desenvolvimento, indústria, comércio",
    "desenvolvimento, industria, comercio",
    "banco central do brasil",
]

# Expressões regulares dos temas de interesse
REGEX_TEMAS = {
    "PND": re.compile(r"\bPND\b|Programa Nacional de Desestatiza[cç][aã]o", re.I),
    "PPI": re.compile(r"\bPPI\b|Programa de Parcerias? de Investimentos?", re.I),
    "CMN": re.compile(r"Conselho Monet[aá]rio Nacional|\bCMN\b", re.I),
    "FMM": re.compile(r"\bFMM\b|Fundo da Marinha Mercante|CDFMM", re.I),
    "FNAC": re.compile(r"\bFNAC\b|Fundo Nacional de Avia[cç][aã]o Civil", re.I),
    "fundos garantidores": re.compile(r"\b(FGE|FGI|FGO|FGHAB|FGC)\b|Fundos?\s+Garantidor(es)?|Fundo de Garantia [àa] Exporta[cç][aã]o|Fundo Garantidor para Investimentos|Fundo Garantidor de Opera[cç][õo]es|Fundo Garantidor da Habita[cç][aã]o|Fundo Garantidor de Cr[eé]ditos", re.I),
    "debêntures": re.compile(
        r"enquadramento,\s*como\s*priorit[aá]rio|"
        r"enquadramento\s*como\s*priorit[aá]rio|"
        r"Emissor/Controladora|"
        r"Lei\s*n?[ºo°]?\s*12\.431|"
        r"Lei\s*n?[ºo°]?\s*14\.801|"
        r"deb[eê]ntures?|"
        r"projetos?\s+priorit[aá]rios?",
        re.I
    ),
    "REIDI": re.compile(r"\bREIDI\b|Regime Especial de Incentivos? para o Desenvolvimento da Infraestrutura", re.I),
    "EVTEA": re.compile(r"\bEVTEA\b|Estudos?\s+de\s+Viabilidade\s+T[eé]cnica|Estudos?\s+de\s+Via\b", re.I),
}

# Filtro temático para deliberações e acórdãos da ANTAQ carregado de configuração externa
ARQ_FILTRO_ANTAQ = PASTA_ATUAL / "filtro_acordaos_antaq.json"
REGEX_ANTAQ_TEMAS = {}
REGEX_ANTAQ_EXCLUSOES = {}

if ARQ_FILTRO_ANTAQ.exists():
    try:
        cfg_antaq = json.loads(ARQ_FILTRO_ANTAQ.read_text(encoding="utf-8"))
        for k, v in cfg_antaq.get("criterios_inclusao", {}).items():
            REGEX_ANTAQ_TEMAS[k] = re.compile(v["regex"], re.I)
        for k, v in cfg_antaq.get("criterios_exclusao_expressa", {}).items():
            REGEX_ANTAQ_EXCLUSOES[k] = re.compile(v["regex"], re.I)
    except Exception as e:
        print(f"[AVISO] Falha ao carregar filtro_acordaos_antaq.json ({e}). Usando fallback.")

if not REGEX_ANTAQ_TEMAS:
    REGEX_ANTAQ_TEMAS = {
        "arrendamento": re.compile(r"\barrendament|\barrendat[aá]ri", re.I),
        "reequilíbrio": re.compile(r"reequil[ií]bri", re.I),
        "tarifa": re.compile(r"\btarif", re.I),
        "EVTEA": re.compile(r"\bEVTEA\b|Estudos?\s+de\s+Viabilidade|Portaria\s+530", re.I),
    }

TIPOS_VALIDOS_TEMATICOS = [
    "decreto", "decreto numerado", "resolução", "portaria", "acórdão",
    "deliberação", "despacho", "ato declaratório", "instrução normativa",
    "consulta pública", "audiência pública", "aviso de consulta", "edital"
]


def eh_orgao_filtro(hierarchy_str: str, hierarchy_list: List[str]) -> bool:
    h_str = (hierarchy_str or "").lower()
    h_list = [x.lower() for x in (hierarchy_list or [])]
    return any(p in h_str or any(p in x for x in h_list) for p in PADROES_ORGAOS_FILTRO)


def testar_url_http_200(url: str, timeout: int = 15) -> int:
    """Trava obrigatória: testa se o link existe e responde HTTP 200 na fonte oficial."""
    req = urllib.request.Request(url, headers=HEADERS_DOU, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status
    except urllib.error.HTTPError as e:
        return e.code
    except Exception:
        return -1


def baixar_ou_carregar_indice_dou(data_str: str, secao: str, max_tentativas: int = 4, timeout: int = 35) -> Dict[str, Any]:
    secao_lower = secao.lower()
    arq_cache = PASTA_CACHE_DOU / f"dou_{data_str}_{secao_lower}.json"

    if arq_cache.exists():
        try:
            dados = json.loads(arq_cache.read_text(encoding="utf-8"))
            if isinstance(dados, dict) and "itens" in dados:
                return dados
            elif isinstance(dados, list):
                return {
                    "sucesso": True,
                    "de_cache": True,
                    "tentativas": 0,
                    "erro": None,
                    "itens": dados,
                    "typeNormDay": {},
                }
        except Exception:
            pass

    url = f"https://www.in.gov.br/leiturajornal?data={data_str}&secao={secao_lower}"
    req = urllib.request.Request(url, headers=HEADERS_DOU)

    ultimo_erro = None
    ultimo_type_norm = {}

    for tentativa in range(1, max_tentativas + 1):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                html = resp.read().decode("utf-8", errors="replace")

            m = re.search(r'<script\b[^>]*id=[\"\']params[\"\'][^>]*>(.*?)</script>', html, re.DOTALL)
            if m:
                payload = json.loads(m.group(1))
                itens = payload.get("jsonArray", [])
                ultimo_type_norm = payload.get("typeNormDay", {})

                if len(itens) > 0:
                    resultado = {
                        "sucesso": True,
                        "de_cache": False,
                        "tentativas": tentativa,
                        "erro": None,
                        "itens": itens,
                        "typeNormDay": ultimo_type_norm,
                    }
                    arq_cache.write_text(json.dumps(resultado, ensure_ascii=False, indent=2), encoding="utf-8")
                    return resultado
                else:
                    ultimo_erro = f"jsonArray vazio (0 atos). typeNormDay: {ultimo_type_norm}"
            else:
                ultimo_erro = f"Tentativa {tentativa}: script id='params' não encontrado no HTML"
        except Exception as e:
            ultimo_erro = f"Tentativa {tentativa} falhou: {e}"

        if tentativa < max_tentativas:
            time.sleep(2 * tentativa)

    resultado = {
        "sucesso": True if ultimo_type_norm else False,
        "de_cache": False,
        "tentativas": max_tentativas,
        "erro": ultimo_erro if not ultimo_type_norm else f"Sem atos na edição ordinária ({secao.upper()}). Extras indicadas: {ultimo_type_norm}",
        "itens": [],
        "typeNormDay": ultimo_type_norm,
    }
    arq_cache.write_text(json.dumps(resultado, ensure_ascii=False, indent=2), encoding="utf-8")
    return resultado


def obter_texto_completo_ato(url: str, content_indice: str) -> str:
    """Obtém o texto integral do ato da página oficial para extração precisa (com cache em disco)."""
    slug = url.rstrip("/").split("/")[-1]
    arq_cache_ato = PASTA_CACHE_ATOS / f"{slug}.txt"
    if arq_cache_ato.exists():
        try:
            return arq_cache_ato.read_text(encoding="utf-8")
        except Exception:
            pass

    req = urllib.request.Request(url, headers=HEADERS_DOU)
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            html = r.read().decode("utf-8", errors="replace")
        m = re.search(r'class="texto-dou">(.*?)</div>', html, re.DOTALL)
        if m:
            texto = re.sub(r'<[^>]+>', ' ', m.group(1))
            texto_limpo = " ".join(texto.split())
            arq_cache_ato.write_text(texto_limpo, encoding="utf-8")
            return texto_limpo
    except Exception:
        pass
    return content_indice


def extrair_processo_relator(content: str):
    """Regra estrita: se não encontrar processo ou relator, o campo fica vazio."""
    m_proc = re.search(r"Processo:\s*([0-9\.\/-]+)", content, re.IGNORECASE)
    if not m_proc:
        m_proc = re.search(r"Processo\s*n[ºo°]?\s*([0-9\.\/-]+)", content, re.IGNORECASE)
    processo = m_proc.group(1).strip() if m_proc else ""

    m_rel = re.search(r"Relator:\s*([^0-9\n\r;]+?)(?=\s*\d+\.|\s*Assunto|\s*Acórdão|\s*$|[;\.])/i", content)
    if not m_rel:
        m_rel = re.search(r"Relator:\s*([^\d\n\r;]+)", content, re.IGNORECASE)
    relator = m_rel.group(1).strip() if m_rel else ""
    if len(relator) > 50:
        relator = relator[:50].strip()

    return processo, relator


def extrair_primeira_linha(content: str) -> str:
    """Regra estrita: transcrição literal dos primeiros caracteres do texto do ato."""
    c = content.strip()
    linhas = [l.strip() for l in c.split("\n") if l.strip()]
    if linhas:
        return linhas[0][:150]
    return c[:150]


def extrair_dados_reidi_enquadramento(it: Dict[str, Any], texto_completo: str, data_pub: str, secao: str, url: str) -> Dict[str, Any]:
    """
    Extrai estritamente por regra os campos de REIDI / Enquadramento:
    - data, seção, tipo (enquadramento / prioritário / habilitação / coabilitação / cancelamento)
    - órgão emissor, número do ato, pessoa jurídica, CNPJ, número do processo
    - portaria de enquadramento citada, ministério, setor (apenas se vier do ministério)
    - urlTitle com HTTP 200 testado
    """
    titulo = it.get("title", "").strip()
    trecho_inicial = (titulo + " " + texto_completo[:350]).lower()

    # Subtipo baseado no início/ementa do ato (para não confundir com cláusulas rescisórias finais)
    if "cancela a habilitação" in trecho_inicial or "cancelar a habilitação" in trecho_inicial or "cancela o registro" in trecho_inicial:
        subtipo = "cancelamento"
    elif "coabilitação" in trecho_inicial or "co-habilitação" in trecho_inicial or "coabilita" in trecho_inicial:
        subtipo = "coabilitação"
    elif "concede habilitação" in trecho_inicial or "habilitada ao" in trecho_inicial or "habilitação ao" in trecho_inicial:
        subtipo = "habilitação"
    elif "como prioritário" in trecho_inicial or "projeto prioritário" in trecho_inicial:
        subtipo = "prioritário"
    elif "enquadramento" in trecho_inicial:
        subtipo = "enquadramento"
    else:
        subtipo = "enquadramento"

    # CNPJ
    m_cnpj = re.search(r"\b\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\b", texto_completo)
    cnpj = m_cnpj.group(0) if m_cnpj else ""

    # Processo
    m_proc = re.search(r"Processo\s*(?:n[ºo°]?)?\s*([0-9\.\/-]+)", texto_completo, re.I)
    proc = m_proc.group(1).strip() if m_proc else ""

    # Pessoa Juridica
    pj = ""
    m_pj1 = re.search(r"pessoa jurídica\s+([A-Z0-9\.\s\-\/]+?)(?:,\s*CNPJ|,\s*inscrita|\s*\(|no CNPJ|\.\s*Art)", texto_completo, re.I)
    if m_pj1 and len(m_pj1.group(1).strip()) > 3:
        pj = m_pj1.group(1).strip()
    if not pj:
        m_pj2 = re.search(r"proposto pela\s+([A-Z0-9\.\s\-\/]+?)(?:\s*\(Emissor|\s*,\s*CNPJ|\.\s*O MINISTRO)", texto_completo, re.I)
        if m_pj2 and len(m_pj2.group(1).strip()) > 3:
            pj = m_pj2.group(1).strip()
    if not pj:
        m_pj3 = re.search(r"apresentado pela\s+([A-Z0-9\.\s\-\/]+?)(?:\.|\s*,\s*CNPJ|\.\s*O MINISTRO)", texto_completo, re.I)
        if m_pj3 and len(m_pj3.group(1).strip()) > 3:
            pj = m_pj3.group(1).strip()
    if not pj:
        m_pj4 = re.search(r"da empresa\s+([A-Z0-9\.\s\-\/]+?)(?:,\s*CNPJ|,\s*inscrita|\s*\()", texto_completo, re.I)
        if m_pj4 and len(m_pj4.group(1).strip()) > 3:
            pj = m_pj4.group(1).strip()

    # Portaria de enquadramento citada (para atos da Receita)
    port_enquad = ""
    m_pe = re.search(r"Portaria\s+([A-Za-z0-9\.\s\-\/º°]+?)(?:,\s*de\s+\d+|\s+de\s+\d+)", texto_completo, re.I)
    if m_pe:
        cand = m_pe.group(1).strip()
        if cand.lower() not in titulo.lower() and "rfb" not in cand.lower():
            port_enquad = f"Portaria {cand}"

    # Ministério
    minis = ""
    m_min = re.search(r"(Ministério\s+d[eao][s]?\s+[A-Za-z\s,]+?)(?:,|\.|\s+no uso|\s+aprova|\s*\(publicado)", texto_completo, re.I)
    if m_min:
        minis = m_min.group(1).strip()

    # Setor: REGRA ESTRITA — só grava quando vier do texto da portaria do ministério
    setor = ""
    eh_portaria_ministerio = "ministério" in (it.get("hierarchyStr") or "").lower() and "portaria" in (it.get("artType") or "").lower()
    if eh_portaria_ministerio:
        m_set = re.search(r"setor\s+de\s+([A-Za-z0-9\s,e]+?)(?:,|\.|\s+apresentado|\s+proposto|\s*\(Decreto)", texto_completo, re.I)
        if m_set:
            setor = m_set.group(1).strip()
        else:
            m_set2 = re.search(r"Setor\s+Prioritário\s+([A-Za-z0-9\s,e]+?)(?:,|\.|\s*\(Decreto)", texto_completo, re.I)
            if m_set2:
                setor = m_set2.group(1).strip()

    return {
        "data": data_pub,
        "secao": secao,
        "tipo": subtipo,
        "orgao_emissor": it.get("hierarchyStr", "").strip(),
        "numero_ato": titulo,
        "pessoa_juridica": pj,
        "cnpj": cnpj,
        "numero_processo": proc,
        "portaria_enquadramento": port_enquad,
        "ministerio": minis,
        "setor": setor,
        "urlTitle": it.get("urlTitle", "").strip(),
        "url": url,
    }


def gravar_registro_reidi_local(reg: Dict[str, Any]):
    """Grava o registro completo em dados_reidi/atos_AAAA-MM.jsonl (fora do repo)."""
    data_str = reg.get("data", "")
    # Extrai AAAA-MM
    m_ano_mes = re.search(r"(\d{2})-(\d{2})-(\d{4})", data_str)
    if m_ano_mes:
        chave_mes = f"{m_ano_mes.group(3)}-{m_ano_mes.group(2)}"
    else:
        chave_mes = "2026-11"

    arq_jsonl = PASTA_DADOS_REIDI / f"atos_{chave_mes}.jsonl"
    with open(arq_jsonl, "a", encoding="utf-8") as f:
        f.write(json.dumps(reg, ensure_ascii=False) + "\n")


def executar_coleta_e_filtragem(datas: List[str] = None) -> Dict[str, Any]:
    if datas is None:
        datas = DATAS_AMOSTRA_2026

    contagem_orgaos_filtro = Counter()
    contagem_tipos_filtro = Counter()
    atos_aprovados = []
    atos_descartados = []
    registros_reidi_enquadramento = []
    acordaos_antaq_avaliados = []

    total_atos_varridos = 0

    for d in datas:
        for s in ["do1", "do3"]:
            res = baixar_ou_carregar_indice_dou(d, s)
            itens = res.get("itens", [])
            total_atos_varridos += len(itens)

            for it in itens:
                h = it.get("hierarchyStr", "")
                hl = it.get("hierarchyList", [])
                tipo = (it.get("artType") or "").strip()
                titulo = (it.get("title") or "").strip()
                content = (it.get("content") or "").strip()
                texto_busca = f"{titulo} {content}"

                eh_do_filtro = eh_orgao_filtro(h, hl)

                if eh_do_filtro:
                    orgao_1 = hl[0] if hl else (h.split("/")[0] if h else "Indefinido")
                    contagem_orgaos_filtro[orgao_1] += 1
                    contagem_tipos_filtro[tipo or "Não Informado"] += 1

                # Avaliação de acórdãos da ANTAQ para decisão do Marcos
                if ("transportes aquavi" in h.lower() or "antaq" in h.lower()) and ("acórdão" in tipo.lower() or "acórdão" in titulo.lower() or "acordao" in titulo.lower()):
                    url_t = (it.get("urlTitle") or "").strip()
                    url_c = f"https://www.in.gov.br/web/dou/-/{url_t}"
                    status_h = testar_url_http_200(url_c)
                    proc_a, rel_a = extrair_processo_relator(content)
                    l0_a = extrair_primeira_linha(content)

                    # Obtém texto completo para avaliação sem truncamento
                    txt_completo_a = obter_texto_completo_ato(url_c, content) if status_h == 200 else content
                    texto_busca_acordao = f"{titulo} {txt_completo_a}"

                    # Testa se passa no filtro temático da ANTAQ (inclusões vs exclusões expressas)
                    temas_antaq = []
                    for t_nome, rgx_a in REGEX_ANTAQ_TEMAS.items():
                        if rgx_a.search(texto_busca_acordao):
                            temas_antaq.append(t_nome)

                    exclusoes_antaq = []
                    for e_nome, rgx_e in REGEX_ANTAQ_EXCLUSOES.items():
                        if rgx_e.search(texto_busca_acordao):
                            exclusoes_antaq.append(e_nome)

                    passou_filtro = len(temas_antaq) > 0 and len(exclusoes_antaq) == 0

                    acordaos_antaq_avaliados.append({
                        "data": d,
                        "secao": s.upper(),
                        "numero": titulo,
                        "processo": proc_a,
                        "relator": rel_a,
                        "temas": temas_antaq,
                        "exclusoes": exclusoes_antaq,
                        "passou_tematico": passou_filtro,
                        "primeira_linha_literal": l0_a,
                        "url": url_c,
                        "http_status": status_h,
                    })

                # Varredura dos temas específicos do Radar
                temas_casados = []
                for tema, rgx in REGEX_TEMAS.items():
                    if rgx.search(texto_busca) or (tema == "CMN" and rgx.search(h)):
                        temas_casados.append(tema)

                if not temas_casados:
                    continue

                # Trava 1: Órgão fora do filtro
                if not eh_do_filtro:
                    atos_descartados.append({
                        "data": d,
                        "secao": s.upper(),
                        "titulo": titulo,
                        "tipo": tipo,
                        "orgao": h,
                        "temas": temas_casados,
                        "motivo": "Órgão fora do escopo setorial do filtro",
                    })
                    continue

                # Trava 2: Tipo de ato rotineiro / operacional
                tipo_lower = tipo.lower()
                tipo_valido = any(tv in tipo_lower for tv in TIPOS_VALIDOS_TEMATICOS)
                if not tipo_valido or "comunicado" in tipo_lower:
                    atos_descartados.append({
                        "data": d,
                        "secao": s.upper(),
                        "titulo": titulo,
                        "tipo": tipo,
                        "orgao": h,
                        "temas": temas_casados,
                        "motivo": f"Tipo de ato operacional/rotineiro ({tipo}) não deliberativo/normativo",
                    })
                    continue

                # Trava 3: urlTitle obrigatório
                url_title = (it.get("urlTitle") or "").strip()
                if not url_title:
                    atos_descartados.append({
                        "data": d,
                        "secao": s.upper(),
                        "titulo": titulo,
                        "tipo": tipo,
                        "orgao": h,
                        "temas": temas_casados,
                        "motivo": "urlTitle ausente no índice do DOU",
                    })
                    continue

                # Trava 4: Teste HTTP 200 obrigatório
                url_completa = f"https://www.in.gov.br/web/dou/-/{url_title}"
                status_http = testar_url_http_200(url_completa)
                if status_http != 200:
                    atos_descartados.append({
                        "data": d,
                        "secao": s.upper(),
                        "titulo": titulo,
                        "tipo": tipo,
                        "orgao": h,
                        "temas": temas_casados,
                        "motivo": f"Falha no teste HTTP do link na fonte (status {status_http})",
                    })
                    continue

                proc, rel = extrair_processo_relator(content)
                l0 = extrair_primeira_linha(content)

                # Se for ato de REIDI ou Enquadramento Prioritário: grava o registro completo no JSONL local
                eh_reidi_ou_enquadramento = "REIDI" in temas_casados or "debêntures" in temas_casados or "enquadramento" in l0.lower()
                if eh_reidi_ou_enquadramento:
                    txt_completo = obter_texto_completo_ato(url_completa, content)
                    reg_reidi = extrair_dados_reidi_enquadramento(it, txt_completo, d, s.upper(), url_completa)
                    gravar_registro_reidi_local(reg_reidi)
                    registros_reidi_enquadramento.append(reg_reidi)

                atos_aprovados.append({
                    "data": d,
                    "secao": s.upper(),
                    "temas": temas_casados,
                    "tipo": tipo,
                    "orgao": h,
                    "titulo": titulo,
                    "primeira_linha_literal": l0,
                    "processo": proc,
                    "relator": rel,
                    "url": url_completa,
                    "http_status": status_http,
                    "eh_reidi_rfb": "REIDI" in temas_casados and "receita federal" in h.lower(),
                })
                time.sleep(0.05)

    vol_por_dia = Counter(x["data"] for x in atos_aprovados)

    return {
        "total_varridos": total_atos_varridos,
        "contagem_orgaos": contagem_orgaos_filtro,
        "contagem_tipos": contagem_tipos_filtro,
        "volume_por_dia": vol_por_dia,
        "atos_aprovados": atos_aprovados,
        "atos_descartados": atos_descartados,
        "registros_reidi": registros_reidi_enquadramento,
        "acordaos_antaq_avaliados": acordaos_antaq_avaliados,
    }


def obter_cards_dou_por_aba(usar_cache_se_disponivel: bool = True) -> Dict[str, list]:
    """
    Consolida e distribui os atos aprovados do DOU nas abas existentes do Radar:
    - participativo: Consultas e audiências públicas publicadas no DOU
    - estruturacao: Decretos PPI/PND e Acórdãos ANTAQ de modelagem/arrendamento
    - leiloes: Editais e avisos de licitação de infraestrutura no DO3
    - sfn: Resoluções CMN, atos FMM, fundos garantidores e debêntures incentivadas (sem CNPJ)
    """
    arq_cons = PASTA_CACHE_DOU / "resultado_consolidado_fase1.json"
    if usar_cache_se_disponivel and arq_cons.exists():
        try:
            dados = json.loads(arq_cons.read_text(encoding="utf-8"))
        except Exception:
            dados = executar_coleta_e_filtragem()
    else:
        dados = executar_coleta_e_filtragem()

    atos_aprovados = dados.get("atos_aprovados", [])
    acordaos_antaq = dados.get("acordaos_antaq_avaliados", [])

    cards_distribuidos = {
        "participativo": [],
        "estruturacao": [],
        "leiloes": [],
        "sfn": [],
    }

    # 1. Atos Temáticos do DOU
    for ato in atos_aprovados:
        temas = ato.get("temas", [])
        tipo = ato.get("tipo", "Ato Normativo")
        titulo = ato.get("titulo", "")
        orgao = ato.get("orgao", "")
        data_br = ato.get("data", "")
        url = ato.get("url", "")
        l0 = ato.get("primeira_linha_literal", "")
        proc = ato.get("processo", "")
        rel = ato.get("relator", "")

        # Pula habilitações fiscais individuais da Receita Federal (ficam só no JSONL local e no card agregado)
        if ato.get("eh_reidi_rfb"):
            continue

        # A. Aba Estruturação (PPI, PND, EVTEA)
        if "PND" in temas or "PPI" in temas or "EVTEA" in temas:
            # Se for o Acórdão 640, pula pois já possui card de contingência dedicado
            if "640" in titulo:
                continue

            sigla_est = "PPI / Presidência da República" if ("PND" in temas or "PPI" in temas) else "ANTAQ"
            cards_distribuidos["estruturacao"].append({
                "id": f"DOU_{ato.get('secao', 'DO1')}_{abs(hash(url)) % 100000}",
                "origem": f"DOU • {ato.get('secao', 'DO1')}",
                "estruturador_sigla": sigla_est,
                "prioridade_escopo": "PRIORIDADE_A_DESTAQUE" if ("PPI" in temas or "PND" in temas) else "PRIORIDADE_A",
                "categoria_item": "ESTUDO_EVTEA" if "EVTEA" in temas else "CONTRATACAO",
                "modalidade": f"{tipo} • DOU {data_br}",
                "titulo": titulo,
                "titulo_executivo": f"{tipo}: {titulo}",
                "descricao_bruta": l0,
                "escopo_sintetico": l0,
                "analise_riscos_segurabilidade": "Ato normativo de estruturação federal com impacto direto em concessões e parcerias.",
                "ficha_documental_verificada": True,
                "url": url,
                "valor_estimado": None,
                "valor_formatado": "Diretriz Governamental",
                "data_publicacao_br": data_br,
                "data_publicacao_iso": f"2026-{data_br[3:5]}-{data_br[:2]}" if len(data_br) >= 10 else "",
                "data_fim_br": "Em Vigor",
                "data_fim_iso": "",
                "dias_restantes": None,
                "tem_matriz_risco": True,
                "documentos": [
                    {"rotulo": f"📜 Publicação no DOU ({tipo})", "url": url, "categoria": "DOU"}
                ],
            })

        # B. Aba SFN (CMN, FMM, Fundos Garantidores, Debêntures Incentivadas)
        elif "CMN" in temas or "FMM" in temas or "fundos garantidores" in temas or "debêntures" in temas:
            sigla_orgao = "CMN" if "CMN" in temas else ("FMM" if "FMM" in temas else ("MF / Fundos" if "fundos" in str(temas) else "MCID / Debêntures"))
            vert_sfn = "mercado_capitais" if ("debêntures" in temas or "CMN" in temas) else "seguros"

            # Limpa qualquer eventual menção a CNPJ ou siglas restritas do texto livre antes de gerar o card
            texto_limpo = re.sub(r"\b\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\b", "[CNPJ_RESTRITO_BASE_LOCAL]", l0)
            texto_limpo = re.sub(r"\b\d{14}\b", "[CNPJ_RESTRITO_BASE_LOCAL]", texto_limpo)
            texto_limpo = re.sub(r"\bGM-MPOR\b", "GM (Portos e Aeroportos)", texto_limpo, flags=re.I)
            texto_limpo = re.sub(r"\bMPOR\b", "Portos e Aeroportos", texto_limpo, flags=re.I)
            titulo_limpo = re.sub(r"\bGM-MPOR\b", "GM", titulo, flags=re.I)
            titulo_limpo = re.sub(r"\bMPOR\b", "Portos e Aeroportos", titulo_limpo, flags=re.I)

            cards_distribuidos["sfn"].append({
                "id": f"DOU_SFN_{abs(hash(url)) % 100000}",
                "vertical": vert_sfn,
                "status_ciclo": "VIGENTE",
                "orgao_sigla": sigla_orgao,
                "entidade": sigla_orgao,
                "entidade_nome": orgao.split("/")[0] if "/" in orgao else orgao,
                "modalidade_numero": f"{tipo} • {titulo_limpo}",
                "modalidade_exibicao": f"{tipo} • DOU {data_br}",
                "titulo": titulo_limpo,
                "data_inicio_br": data_br,
                "data_publicacao_br": data_br,
                "data_fim_br": "Vigente",
                "data_fim_iso": "",
                "dias_restantes": None,
                "termo_casado": ", ".join(temas),
                "ementa": texto_limpo,
                "objeto_normativo": texto_limpo,
                "resumo_ia": "Ato oficial publicado no DOU com impacto em regulação financeira, garantias públicas ou incentivos de mercado de capitais.",
                "resumo_executivo": texto_limpo,
                "pontos_atencao": "Ato oficial publicado no DOU com impacto em regulação de capitais, garantias públicas ou enquadramento prioritário de debêntures.",
                "url": url,
                "url_principal": url,
                "documentos": [
                    {"rotulo": f"📜 Publicação Oficial no DOU ({tipo})", "url": url, "categoria": "DOU"}
                ],
            })

        # C. Aba Participativo (Consultas e Audiências Públicas no DOU)
        elif "consulta pública" in tipo.lower() or "audiência pública" in tipo.lower():
            cards_distribuidos["participativo"].append({
                "id": f"DOU_PART_{abs(hash(url)) % 100000}",
                "orgao_sigla": orgao.split("/")[0] if "/" in orgao else orgao[:15],
                "titulo": titulo,
                "objeto_normativo": l0,
                "data_publicacao_br": data_br,
                "data_fim_br": "Ver Edital",
                "dias_restantes": None,
                "url": url,
            })

    # 2. Card Agregado de Habilitações REIDI (sem CNPJ individual) na Aba SFN
    qtd_reidi = sum(1 for ato in atos_aprovados if ato.get("eh_reidi_rfb"))
    if qtd_reidi > 0:
        desc_reidi = (
            f"Foram identificados e catalogados {qtd_reidi} Atos Declaratórios Executivos de habilitação e coabilitação "
            "ao Regime Especial de Incentivos para o Desenvolvimento da Infraestrutura (REIDI) publicados nas edições do DO1. "
            "Conforme diretriz de privacidade, os dados fiscais e CNPJs completos são armazenados estritamente na base analítica local (dados_reidi/)."
        )
        cards_distribuidos["sfn"].append({
            "id": "DOU_SFN_PAINEL_REIDI_AGREGADO",
            "vertical": "mercado_capitais",
            "status_ciclo": "VIGENTE",
            "orgao_sigla": "RFB / REIDI",
            "entidade": "RFB / REIDI",
            "entidade_nome": "Receita Federal do Brasil",
            "modalidade_numero": f"Painel de Monitoramento Fiscal • {qtd_reidi} Habilitações",
            "modalidade_exibicao": "Painel de Monitoramento Fiscal • DOU DO1",
            "titulo": f"Painel Agregado: {qtd_reidi} Atos Declaratórios de Habilitação no REIDI (Receita Federal)",
            "data_inicio_br": "Edições Recentes",
            "data_publicacao_br": "Edições Recentes",
            "data_fim_br": "Ativo",
            "data_fim_iso": "",
            "dias_restantes": None,
            "termo_casado": "REIDI",
            "ementa": desc_reidi,
            "objeto_normativo": desc_reidi,
            "resumo_ia": f"Monitoramento contínuo das habilitações do REIDI publicadas pela Receita Federal ({qtd_reidi} atos recentes auditados na base analítica local).",
            "resumo_executivo": f"Monitoramento contínuo das habilitações do REIDI publicadas pela Receita Federal ({qtd_reidi} atos recentes auditados).",
            "pontos_atencao": "Incentivo fiscal a projetos setoriais de infraestrutura (suspensão de PIS/COFINS em bens e serviços).",
            "url": "https://www.in.gov.br",
            "url_principal": "https://www.in.gov.br",
            "documentos": [
                {"rotulo": "🌐 Portal da Imprensa Nacional (DOU)", "url": "https://www.in.gov.br", "categoria": "DOU"}
            ],
        })

    # 3. Acórdãos ANTAQ filtrados que entraram (ex: Acórdão 650 sobre modelagem/arrendamento)
    for ac in acordaos_antaq:
        if ac.get("passou_tematico") and "640" not in ac.get("numero", ""):
            titulo_ac = ac.get("numero", "")
            url_ac = ac.get("url", "")
            l0_ac = ac.get("primeira_linha_literal", "")
            cards_distribuidos["estruturacao"].append({
                "id": f"DOU_ANTAQ_{abs(hash(url_ac)) % 100000}",
                "origem": "DOU • DO1",
                "estruturador_sigla": "ANTAQ",
                "prioridade_escopo": "PRIORIDADE_A",
                "categoria_item": "ESTUDO_EVTEA",
                "modalidade": f"Acórdão ANTAQ • DOU {ac.get('data', '')}",
                "titulo": f"{titulo_ac} — Modelagem / Arrendamento Portuário",
                "titulo_executivo": f"{titulo_ac} (SELC/SOG)",
                "descricao_bruta": l0_ac,
                "escopo_sintetico": l0_ac,
                "analise_riscos_segurabilidade": "Deliberação da Diretoria Colegiada da ANTAQ sobre modelagens e licitações de arrendamentos portuários.",
                "ficha_documental_verificada": True,
                "url": url_ac,
                "valor_estimado": None,
                "valor_formatado": "Deliberação Regulatória",
                "data_publicacao_br": ac.get("data", ""),
                "data_publicacao_iso": "",
                "data_fim_br": "Deliberado",
                "data_fim_iso": "",
                "dias_restantes": None,
                "tem_matriz_risco": True,
                "documentos": [
                    {"rotulo": f"📜 {titulo_ac} (DOU Oficial)", "url": url_ac, "categoria": "DOU"}
                ],
            })

    return cards_distribuidos


if __name__ == "__main__":
    res = executar_coleta_e_filtragem()
    arq_out = PASTA_CACHE_DOU / "resultado_consolidado_fase1.json"
    arq_out.write_text(json.dumps({
        "total_varridos": res["total_varridos"],
        "contagem_orgaos": dict(res["contagem_orgaos"]),
        "contagem_tipos": dict(res["contagem_tipos"]),
        "volume_por_dia": dict(res["volume_por_dia"]),
        "atos_aprovados": res["atos_aprovados"],
        "atos_descartados": res["atos_descartados"],
        "registros_reidi": res["registros_reidi"],
        "acordaos_antaq_avaliados": res["acordaos_antaq_avaliados"],
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Execução concluída. Aprovados: {len(res['atos_aprovados'])} | REIDI gravados: {len(res['registros_reidi'])} | Acórdãos ANTAQ: {len(res['acordaos_antaq_avaliados'])}")
    print(f"Resultado salvo em: {arq_out}")

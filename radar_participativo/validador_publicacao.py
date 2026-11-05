"""
validador_publicacao.py — Trava automática de segurança editorial pré-publicação.

Regras por tipo de arquivo:
1. RADAR / HUB (radar.html, radar_atual.html, index.html):
   - Reprova substrings (case-insensitive): "decon", "núcleo", "nucleo", "segurabilidade".
   - Reprova "mpor" exceto em palavras de dicionário com raízes autorizadas (import*, tempor*, contempor*, extempor*).
     Identificadores como MPOR_FOCO, PRIORIDADE_A_MPOR ou mpor avulso são reprovados.
   - Reprova "em execução" / "em execucao" RESTRITO aos selos de situação dos cards:
     dentro de elementos com classe 'deadline-pill' (ou 'est-deadline-pill') ou atributos 'data-fim-br'.
     Não varre o texto livre da página inteira para evitar falsos positivos de fontes externas.

2. CLIPPING (clipping.html, historico/*.html):
   - "decon" e "mpor" NÃO são varridos (marca oficial DECON/MPOR mantida por decisão editorial).
   - Reprova APENAS padrões que nunca podem ir ao público:
     - Endereço de e-mail institucional: @mpor.gov.br
     - Número de processo SEI: ex. 00000.000000/0000-00 (padrão federal de processo SEI).
   - Qualquer outro achado gera apenas aviso no log, sem bloquear a publicação nem o e-mail.
   - Resiliência: se ocorrer qualquer erro inesperado ao validar o clipping, registra aviso e libera
     a publicação, garantindo que o envio de e-mail nunca seja impedido.
"""

import sys
import re
from pathlib import Path
from typing import List, Dict, Tuple

try:
    from bs4 import BeautifulSoup
    TEM_BS4 = True
except ImportError:
    TEM_BS4 = False

# ==============================================================================
# CONFIGURAÇÕES DE REGRAS
# ==============================================================================

# Para RADAR e INDEX
TERMOS_PROIBIDOS_RADAR = [
    "decon",
    "núcleo",
    "nucleo",
    "segurabilidade",
]

PREFIXOS_EXCECAO_MPOR = (
    "import",
    "tempor",
    "contempor",
    "extempor",
)

# Para CLIPPING (padrões estritamente proibidos em repositório público)
PADRAO_EMAIL_INSTITUCIONAL = re.compile(r"[\w\.-]+@mpor\.gov\.br", re.IGNORECASE)
PADRAO_PROCESSO_SEI = re.compile(r"\b\d{5}\.\d{6}/\d{4}-\d{2}\b")


def obter_trecho_contexto(texto: str, inicio_idx: int, fim_idx: int, raio: int = 35) -> str:
    """Extrai trecho de contexto sem quebras de linha."""
    start = max(0, inicio_idx - raio)
    end = min(len(texto), fim_idx + raio)
    snippet = texto[start:end].replace("\r", " ").replace("\n", " ")
    return " ".join(snippet.split())


def identificar_tipo_arquivo(nome_ou_caminho: str) -> str:
    """Identifica se o arquivo segue a regra do CLIPPING ou do RADAR/HUB."""
    nome = Path(nome_ou_caminho).name.lower()
    caminho_str = str(nome_ou_caminho).lower().replace("\\", "/")
    if "clipping" in nome or "historico" in caminho_str:
        return "CLIPPING"
    return "RADAR"


# ==============================================================================
# VALIDAÇÃO RADAR / HUB
# ==============================================================================

def verificar_em_execucao_selos(conteudo: str, nome_arquivo: str) -> List[Dict]:
    """
    Verifica a presença de 'em execução' APENAS nos selos de situação dos cards
    (classe deadline-pill / est-deadline-pill e atributo data-fim-br).
    """
    violacoes = []

    # 1. Checagem via BeautifulSoup se disponível
    if TEM_BS4:
        try:
            soup = BeautifulSoup(conteudo, "html.parser")
            # Elementos com classe deadline-pill
            for el in soup.find_all(class_=lambda c: c and "deadline-pill" in c):
                texto_selo = el.get_text()
                if "em execução" in texto_selo.lower() or "em execucao" in texto_selo.lower():
                    violacoes.append({
                        "arquivo": nome_arquivo,
                        "termo": "em execução (em selo de situação)",
                        "posicao": 0,
                        "trecho": f"<{el.name} class='{el.get('class')}'>{texto_selo}</{el.name}>",
                        "detalhe": "Selo de situação de card utilizando 'Em Execução' em vez de 'Contrato assinado em [data]'."
                    })

            # Atributos data-fim-br
            for el in soup.find_all(attrs={"data-fim-br": True}):
                val = el.get("data-fim-br", "")
                if "em execução" in val.lower() or "em execucao" in val.lower():
                    violacoes.append({
                        "arquivo": nome_arquivo,
                        "termo": "em execução (atributo data-fim-br)",
                        "posicao": 0,
                        "trecho": f"data-fim-br='{val}' no elemento {el.name}",
                        "detalhe": "Atributo data-fim-br contendo 'Em Execução'."
                    })
            return violacoes
        except Exception as e:
            print(f"   [Aviso validador BeautifulSoup] {e}. Usando fallback regex.")

    # 2. Fallback via Regex para deadline-pill e data-fim-br
    padrao_pill = re.compile(r"<[^>]+class=[\"'][^\"']*deadline-pill[^\"']*[\"'][^>]*>(.*?)</[^>]+>", re.IGNORECASE | re.DOTALL)
    for m in padrao_pill.finditer(conteudo):
        corpo = m.group(1).lower()
        if "em execução" in corpo or "em execucao" in corpo:
            violacoes.append({
                "arquivo": nome_arquivo,
                "termo": "em execução (em selo deadline-pill)",
                "posicao": m.start(),
                "trecho": obter_trecho_contexto(conteudo, m.start(), m.end()),
                "detalhe": "Selo de situação deadline-pill contendo 'Em Execução'."
            })

    padrao_attr = re.compile(r"data-fim-br=[\"'][^\"']*em execu[çc][ãa]o[^\"']*[\"']", re.IGNORECASE)
    for m in padrao_attr.finditer(conteudo):
        violacoes.append({
            "arquivo": nome_arquivo,
            "termo": "em execução (atributo data-fim-br)",
            "posicao": m.start(),
            "trecho": obter_trecho_contexto(conteudo, m.start(), m.end()),
            "detalhe": "Atributo data-fim-br contendo 'Em Execução'."
        })

    return violacoes


def verificar_radar_html(conteudo: str, nome_arquivo: str) -> List[Dict]:
    """Varredura completa e estrita para radar.html, radar_atual.html e index.html."""
    violacoes = []
    texto_lower = conteudo.lower()

    # 1. Termos proibidos por substring direta
    for termo in TERMOS_PROIBIDOS_RADAR:
        pos = 0
        while True:
            idx = texto_lower.find(termo, pos)
            if idx == -1:
                break
            fim = idx + len(termo)
            trecho = obter_trecho_contexto(conteudo, idx, fim)
            violacoes.append({
                "arquivo": nome_arquivo,
                "termo": termo,
                "posicao": idx,
                "trecho": trecho,
                "detalhe": f"Substring proibida '{termo}' detectada no Radar."
            })
            pos = fim

    # 2. Varredura de 'mpor' com regra estrita de palavras autorizadas
    pos = 0
    while True:
        idx = texto_lower.find("mpor", pos)
        if idx == -1:
            break
        fim_mpor = idx + 4

        ini_tok = idx
        while ini_tok > 0 and (conteudo[ini_tok - 1].isalnum() or conteudo[ini_tok - 1] in "_-"):
            ini_tok -= 1
        fim_tok = fim_mpor
        while fim_tok < len(conteudo) and (conteudo[fim_tok].isalnum() or conteudo[fim_tok] in "_-"):
            fim_tok += 1

        token = conteudo[ini_tok:fim_tok]
        token_lower = token.lower()
        letras_puras = re.sub(r"[^a-záàâãéèêíïóôõöúçñ]", "", token_lower)

        eh_excecao = False
        if any(letras_puras.startswith(pfx) for pfx in PREFIXOS_EXCECAO_MPOR):
            if "_mpor" not in token_lower and "mpor_" not in token_lower and token_lower != "mpor":
                eh_excecao = True

        if not eh_excecao:
            trecho = obter_trecho_contexto(conteudo, ini_tok, fim_tok)
            violacoes.append({
                "arquivo": nome_arquivo,
                "termo": "mpor",
                "posicao": idx,
                "trecho": trecho,
                "token": token,
                "detalhe": f"Ocorrência de 'mpor' no token '{token}' fora das exceções autorizadas."
            })

        pos = fim_mpor

    # 3. 'Em execução' restrito aos selos de situação
    violacoes.extend(verificar_em_execucao_selos(conteudo, nome_arquivo))

    # 4. Checagem de Sanidade de Cards por Aba
    violacoes.extend(verificar_sanidade_radar(conteudo, nome_arquivo))

    return violacoes


def contar_cards_radar(conteudo: str) -> Dict[str, int]:
    """Conta os cards presentes em cada painel do Radar."""
    contagens = {"participativo": 0, "estruturacao": 0, "leiloes": 0, "sfn": 0}
    if TEM_BS4:
        try:
            soup = BeautifulSoup(conteudo, "html.parser")
            for chave, pid in [
                ("participativo", "panel-participativo"),
                ("estruturacao", "panel-estruturacao"),
                ("leiloes", "panel-leiloes"),
                ("sfn", "panel-sfn"),
            ]:
                el = soup.find(id=pid)
                if el:
                    contagens[chave] = len(el.find_all("article"))
            return contagens
        except Exception:
            pass

    # Fallback via regex por section de painel
    for chave, pid in [
        ("participativo", "panel-participativo"),
        ("estruturacao", "panel-estruturacao"),
        ("leiloes", "panel-leiloes"),
        ("sfn", "panel-sfn"),
    ]:
        m = re.search(rf'id=[\"\']{pid}[\"\'][^>]*>(.*?)(?:</section>|<section|$)', conteudo, re.DOTALL)
        if m:
            contagens[chave] = len(re.findall(r'<article\b', m.group(1), re.IGNORECASE))
    return contagens


def verificar_sanidade_radar(conteudo: str, nome_arquivo: str) -> List[Dict]:
    """
    Checagem de sanidade obrigatória para o Radar:
    1. Reprova se a aba Estruturação tiver 0 cards.
    2. Reprova se qualquer aba cair mais de 50% em relação à versão publicada.
    """
    if "radar" not in nome_arquivo.lower():
        return []

    violacoes = []
    contagens = contar_cards_radar(conteudo)

    # 1. Checagem obrigatória: Aba Estruturação nunca pode ter 0 cards
    if contagens["estruturacao"] == 0:
        violacoes.append({
            "arquivo": nome_arquivo,
            "termo": "[SANIDADE_ESTRUTURACAO_VAZIA]",
            "posicao": 0,
            "trecho": f"Contagem de cards detectada: {contagens}",
            "detalhe": "Aba Estruturação contém 0 cards. A publicação de radar com abas vazias foi bloqueada."
        })

    # 2. Checagem contra versão publicada na nuvem (se acessível)
    try:
        import urllib.request
        url_ref = "https://mdagavea.github.io/inteligencia-regulatoria/radar.html"
        req = urllib.request.Request(url_ref, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=4) as resp:
            html_ref = resp.read().decode("utf-8", errors="replace")
        contagens_ref = contar_cards_radar(html_ref)

        for aba, qtd_ref in contagens_ref.items():
            if qtd_ref > 0:
                qtd_atual = contagens.get(aba, 0)
                # Se cair mais de 50% em relação à versão publicada
                if qtd_atual < (qtd_ref * 0.5):
                    violacoes.append({
                        "arquivo": nome_arquivo,
                        "termo": f"[SANIDADE_QUEDA_ABRUPTA_{aba.upper()}]",
                        "posicao": 0,
                        "trecho": f"Aba '{aba}': caiu de {qtd_ref} cards publicados para {qtd_atual} cards no HTML atual.",
                        "detalhe": f"Queda anômala superior a 50% detectada na aba '{aba}'. Publicação reprovada."
                    })
    except Exception:
        pass

    return violacoes


# ==============================================================================
# VALIDAÇÃO CLIPPING
# ==============================================================================

def verificar_clipping_html(conteudo: str, nome_arquivo: str) -> Tuple[List[Dict], List[Dict]]:
    """
    Varredura específica do clipping.
    Retorna: (violacoes_bloqueantes, avisos_nao_bloqueantes).
    - Marca DECON/MPOR é mantida por decisão do Marcos (não varre 'decon' nem 'mpor').
    - Reprova APENAS:
      - Endereço de e-mail institucional @mpor.gov.br
      - Número de processo SEI (00000.000000/0000-00)
    - Demais termos sensíveis geram apenas avisos informativos no log.
    """
    violacoes = []
    avisos = []

    # 1. Bloqueante: E-mail institucional do MPOR
    for m in PADRAO_EMAIL_INSTITUCIONAL.finditer(conteudo):
        trecho = obter_trecho_contexto(conteudo, m.start(), m.end())
        violacoes.append({
            "arquivo": nome_arquivo,
            "termo": "@mpor.gov.br",
            "posicao": m.start(),
            "trecho": trecho,
            "detalhe": f"Endereço de e-mail institucional proibido no clipping público: '{m.group(0)}'."
        })

    # 2. Bloqueante: Número de processo SEI
    for m in PADRAO_PROCESSO_SEI.finditer(conteudo):
        trecho = obter_trecho_contexto(conteudo, m.start(), m.end())
        violacoes.append({
            "arquivo": nome_arquivo,
            "termo": "número de processo SEI",
            "posicao": m.start(),
            "trecho": trecho,
            "detalhe": f"Número de processo SEI proibido no clipping público: '{m.group(0)}'."
        })

    # 3. Avisos informativos (NÃO bloqueiam a publicação nem o envio)
    for termo_aviso in ["segurabilidade", "núcleo", "nucleo"]:
        pos = 0
        clower = conteudo.lower()
        while True:
            idx = clower.find(termo_aviso, pos)
            if idx == -1:
                break
            trecho = obter_trecho_contexto(conteudo, idx, idx + len(termo_aviso))
            avisos.append({
                "arquivo": nome_arquivo,
                "termo": termo_aviso,
                "posicao": idx,
                "trecho": trecho,
                "detalhe": f"Termo '{termo_aviso}' encontrado em matéria externa do clipping (apenas aviso, não bloqueante)."
            })
            pos = idx + len(termo_aviso)

    return violacoes, avisos


# ==============================================================================
# FUNÇÃO PRINCIPAL DE ENTRADA
# ==============================================================================

def verificar_conteudo_html(conteudo: str, nome_referencia: str = "documento.html") -> Tuple[List[Dict], List[Dict]]:
    """Direciona a validação conforme o tipo de documento (RADAR ou CLIPPING)."""
    tipo = identificar_tipo_arquivo(nome_referencia)
    if tipo == "CLIPPING":
        return verificar_clipping_html(conteudo, nome_referencia)
    else:
        violacoes = verificar_radar_html(conteudo, nome_referencia)
        return violacoes, []


def validar_arquivo_html(caminho_arquivo: Path) -> Tuple[bool, List[Dict], List[Dict]]:
    """
    Valida um arquivo HTML do disco.
    Retorna (aprovado, violacoes, avisos).
    Garante resiliência: se o clipping gerar exceção inesperada, nunca bloqueia.
    """
    caminho = Path(caminho_arquivo)
    tipo = identificar_tipo_arquivo(caminho.name)

    if not caminho.exists():
        return False, [{
            "arquivo": str(caminho),
            "termo": "[ARQUIVO_INEXISTENTE]",
            "posicao": 0,
            "trecho": "",
            "detalhe": f"Arquivo não encontrado: {caminho}"
        }], []

    try:
        conteudo = caminho.read_text(encoding="utf-8", errors="replace")
        violacoes, avisos = verificar_conteudo_html(conteudo, nome_referencia=caminho.name)
        aprovado = len(violacoes) == 0
        return aprovado, violacoes, avisos
    except Exception as e:
        if tipo == "CLIPPING":
            # Regra 6: A trava NUNCA pode impedir o e-mail do clipping.
            print(f"[AVISO VALIDADOR] Exceção inesperada ao validar clipping ({e}). Prosseguindo com aviso para não impedir e-mail.")
            return True, [], [{
                "arquivo": caminho.name,
                "termo": "[EXCECAO_VALIDADOR]",
                "posicao": 0,
                "trecho": "",
                "detalhe": str(e)
            }]
        else:
            return False, [{
                "arquivo": caminho.name,
                "termo": "[ERRO_LEITURA]",
                "posicao": 0,
                "trecho": "",
                "detalhe": str(e)
            }], []


def emitir_relatorio_validacao(aprovado: bool, violacoes: List[Dict], avisos: List[Dict], nome_referencia: str) -> None:
    """Imprime log do resultado da validação."""
    tipo = identificar_tipo_arquivo(nome_referencia)
    if aprovado:
        print(f"[APROVADO] Varredura de segurança editorial ({tipo}): {nome_referencia}")
        if tipo == "CLIPPING":
            print("           Nenhum dado sensível proibido (@mpor.gov.br ou processo SEI) encontrado.")
        else:
            print("           Nenhum termo proibido encontrado (mpor, decon, núcleo, segurabilidade, em execução em selos).")
    else:
        print("=" * 80)
        print(f"[REPROVADO] TRAVA DE SEGURANÇA EDITORIAL ({tipo}): {nome_referencia}")
        print("=" * 80)
        print(f"Total de violações bloqueantes: {len(violacoes)}")
        for i, v in enumerate(violacoes, 1):
            print(f"\n--- Violação #{i} ---")
            print(f"  Arquivo : {v['arquivo']}")
            print(f"  Termo   : {v['termo']}")
            print(f"  Posição : caractere {v['posicao']}")
            print(f"  Trecho  : \"...{v['trecho']}...\"")
            if "detalhe" in v:
                print(f"  Motivo  : {v['detalhe']}")
        print("=" * 80)

    if avisos:
        print(f"   [Avisos Não-Bloqueantes] {len(avisos)} aviso(s) informativo(s) registrado(s) em {nome_referencia}:")
        for a in avisos[:5]:
            print(f"     - {a['termo']}: \"{a['trecho'][:60]}...\"")


def main():
    """CLI para uso no workflow do GitHub Actions ou local."""
    arquivos = sys.argv[1:]
    if not arquivos:
        print("Uso: python validador_publicacao.py <arquivo1.html> [arquivo2.html ...]")
        sys.exit(2)

    total_violacoes = 0
    for arq_str in arquivos:
        caminho = Path(arq_str)
        if not caminho.exists():
            print(f"[Aviso] Arquivo ignorado (não existe localmente): {caminho}")
            continue
        aprovado, violacoes, avisos = validar_arquivo_html(caminho)
        emitir_relatorio_validacao(aprovado, violacoes, avisos, caminho.name)
        if not aprovado:
            total_violacoes += len(violacoes)

    if total_violacoes > 0:
        print(f"\n[FALHA] Validação reprovada com {total_violacoes} ocorrência(s) bloqueante(s). Publicação bloqueada.")
        sys.exit(1)

    print("\n[SUCESSO] Todos os arquivos analisados estão em conformidade editorial. Publicação liberada.")
    sys.exit(0)


if __name__ == "__main__":
    main()

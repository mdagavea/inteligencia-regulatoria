import os
from datetime import datetime

# Aviso de projeto piloto (exibido na pagina, no e-mail e no radar): faixa no topo = so a 1a frase; texto completo no rodape.
AVISO_PILOTO_FRASE = "Projeto piloto de inteligência regulatória, em fase de testes."
AVISO_PILOTO_TEXTO = (
    "Projeto piloto de inteligência regulatória, em fase de testes. Compilação automatizada de notícias e documentos de acesso público. Os resumos podem ser gerados com apoio de inteligência artificial e estão sujeitos a erros. Este conteúdo não representa posição ou opinião oficial do Ministério de Portos e Aeroportos (MPOR) nem de suas unidades e não substitui a consulta às fontes originais, indicadas em cada item."
)

# Ícones SVG dos medalhões circulares (inspirados no padrão visual DECON/MPOR)
MEDALHOES_SVG = {
    "infra": """<svg viewBox="0 0 100 100" width="44" height="44">
      <circle cx="50" cy="50" r="47" fill="#FFFBF3" stroke="#CDB892" stroke-width="2"/>
      <circle cx="50" cy="50" r="41" fill="#1F3A5F"/>
      <circle cx="50" cy="50" r="35.5" fill="none" stroke="#FFF8EC" stroke-opacity=".4" stroke-width="1.3" stroke-dasharray="2.5 3.5"/>
      <g fill="none" stroke="#FFF8EC" stroke-width="4.8" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="50" cy="27" r="6"/><path d="M50 33 V75"/><path d="M38 42 H62"/>
        <path d="M28 58 C30 74 70 74 72 58"/><path d="M24 62 L28 56 L34 61"/><path d="M76 62 L72 56 L66 61"/>
      </g>
    </svg>""",
    "seguros": """<svg viewBox="0 0 100 100" width="44" height="44">
      <circle cx="50" cy="50" r="47" fill="#FFFBF3" stroke="#CDB892" stroke-width="2"/>
      <circle cx="50" cy="50" r="41" fill="#D2694A"/>
      <circle cx="50" cy="50" r="35.5" fill="none" stroke="#FFF8EC" stroke-opacity=".4" stroke-width="1.3" stroke-dasharray="2.5 3.5"/>
      <g fill="none" stroke="#FFF8EC" stroke-width="4.8" stroke-linecap="round" stroke-linejoin="round">
        <path d="M50 22 L72 30 V50 C72 64 62 74 50 80 C38 74 28 64 28 50 V30 Z"/>
        <path d="M40 50 L47 57 L61 43"/>
      </g>
    </svg>""",
    "carbono": """<svg viewBox="0 0 100 100" width="44" height="44">
      <circle cx="50" cy="50" r="47" fill="#FFFBF3" stroke="#CDB892" stroke-width="2"/>
      <circle cx="50" cy="50" r="41" fill="#2F8291"/>
      <circle cx="50" cy="50" r="35.5" fill="none" stroke="#FFF8EC" stroke-opacity=".4" stroke-width="1.3" stroke-dasharray="2.5 3.5"/>
      <g fill="none" stroke="#FFF8EC" stroke-width="4.8" stroke-linecap="round" stroke-linejoin="round">
        <path d="M28 72 C28 44 48 28 74 26 C74 52 58 70 28 72 Z"/><path d="M28 72 L58 42"/>
      </g>
    </svg>""",
    "divida": """<svg viewBox="0 0 100 100" width="44" height="44">
      <circle cx="50" cy="50" r="47" fill="#FFFBF3" stroke="#CDB892" stroke-width="2"/>
      <circle cx="50" cy="50" r="41" fill="#C18C24"/>
      <circle cx="50" cy="50" r="35.5" fill="none" stroke="#FFF8EC" stroke-opacity=".4" stroke-width="1.3" stroke-dasharray="2.5 3.5"/>
      <g fill="none" stroke="#FFF8EC" stroke-width="4.8" stroke-linecap="round" stroke-linejoin="round">
        <path d="M26 74 H76"/><path d="M33 74 V60"/><path d="M46 74 V52"/><path d="M59 74 V44"/>
        <path d="M28 48 L44 34 L54 40 L72 24"/><path d="M62 24 H72 V34"/>
      </g>
    </svg>""",
    "tech": """<svg viewBox="0 0 100 100" width="44" height="44">
      <circle cx="50" cy="50" r="47" fill="#FFFBF3" stroke="#CDB892" stroke-width="2"/>
      <circle cx="50" cy="50" r="41" fill="#3B4D6B"/>
      <circle cx="50" cy="50" r="35.5" fill="none" stroke="#FFF8EC" stroke-opacity=".4" stroke-width="1.3" stroke-dasharray="2.5 3.5"/>
      <g fill="none" stroke="#FFF8EC" stroke-width="4.8" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="45" cy="45" r="16"/><path d="M57 57 L73 73"/><path d="M37 48 L43 42 L48 46 L54 39"/>
      </g>
    </svg>""",
}

TEMPLATE_HTML = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Clipping Diário Regulatório, Financeiro & Tecnológico - {data_formatada}</title>
  <style>
    :root {{
      --bg-cream: #F4EFE6;
      --card-paper: #FFFCF6;
      --ink: #2C2B28;
      --muted: #6B6457;
      --kraft: #8A7350;
      --sand-border: #CDB892;
      --navy: #1F3A5F;
      
      --color-infra: #1F3A5F;
      --dark-infra: #162944;
      --bg-infra: #E6ECF4;
      
      --color-seguros: #D2694A;
      --dark-seguros: #B55437;
      --bg-seguros: #F9E5DE;
      
      --color-carbono: #2F8291;
      --dark-carbono: #226470;
      --bg-carbono: #E0F1F3;
      
      --color-divida: #C18C24;
      --dark-divida: #9B6F19;
      --bg-divida: #F8EDD2;
      
      --color-tech: #3B4D6B;
      --dark-tech: #28364D;
      --bg-tech: #E5E9F0;
    }}

    * {{ box-sizing: border-box; }}

    body {{
      font-family: "Segoe UI", -apple-system, BlinkMacSystemFont, Roboto, Helvetica, Arial, sans-serif;
      background-color: var(--bg-cream);
      background-image: radial-gradient(rgba(138, 115, 80, 0.08) 1px, transparent 1px);
      background-size: 18px 18px;
      color: var(--ink);
      margin: 0;
      padding: 18px 24px 0 24px;
      line-height: 1.45;
      min-height: 100vh;
      display: flex;
      flex-direction: column;
    }}

    .outer-frame {{
      max-width: 1420px;
      width: 100%;
      margin: 0 auto;
      border: 2px dotted var(--sand-border);
      border-radius: 16px;
      padding: 20px 24px 0 24px;
      background: rgba(244, 239, 230, 0.65);
      position: relative;
      overflow: hidden;
    }}

    header {{
      background: var(--card-paper);
      padding: 16px 24px;
      border-radius: 12px;
      border: 1px solid #DECZAA;
      border-bottom: 3px solid var(--sand-border);
      margin-bottom: 20px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 14px;
      box-shadow: 0 3px 10px rgba(42, 32, 16, 0.07);
      position: relative;
    }}

    .header-left {{
      display: flex;
      align-items: center;
      gap: 16px;
    }}

    .compass-icon {{
      flex-shrink: 0;
      filter: drop-shadow(0 2px 4px rgba(42,32,16,0.15));
    }}

    .header-kicker {{
      font-family: "Bahnschrift", "Segoe UI", sans-serif;
      font-size: 0.74rem;
      font-weight: 700;
      letter-spacing: 0.16em;
      text-transform: uppercase;
      color: var(--kraft);
      margin: 0 0 2px 0;
    }}

    .header-title-area h1 {{
      font-family: "Bahnschrift", "Segoe UI", sans-serif;
      margin: 0;
      font-size: 1.55rem;
      font-weight: 700;
      color: var(--navy);
      letter-spacing: -0.01em;
    }}

    .header-bars {{
      display: flex;
      gap: 6px;
      margin-top: 6px;
    }}

    .bar-ochre {{
      width: 58px;
      height: 5px;
      border-radius: 4px;
      background: #D9A23C;
    }}

    .bar-coral {{
      width: 18px;
      height: 5px;
      border-radius: 4px;
      background: #D2694A;
    }}

    .bar-teal {{
      width: 18px;
      height: 5px;
      border-radius: 4px;
      background: #2F8291;
    }}

    .header-meta {{
      display: flex;
      align-items: center;
      gap: 10px;
      flex-wrap: wrap;
    }}

    .toggle-drawers-btn {{
      font-size: 0.78rem;
      font-weight: 600;
      color: var(--navy);
      background: #F4EFE6;
      border: 1px solid var(--sand-border);
      padding: 6px 13px;
      border-radius: 20px;
      cursor: pointer;
      transition: all 0.15s ease;
    }}

    .toggle-drawers-btn:hover {{
      background: #E9DCC3;
    }}

    .whatsapp-btn {{
      font-size: 0.78rem;
      font-weight: 700;
      color: #FFF8EC;
      background: #1F3A5F;
      border: 1px solid #162944;
      padding: 6px 13px;
      border-radius: 20px;
      cursor: pointer;
      transition: all 0.15s ease;
    }}

    .whatsapp-btn:hover {{
      background: #2F8291;
      border-color: #226470;
    }}

    .history-select {{
      font-size: 0.78rem;
      font-weight: 600;
      color: var(--navy);
      background: #F4EFE6;
      border: 1px solid var(--sand-border);
      padding: 5px 11px;
      border-radius: 20px;
      cursor: pointer;
      outline: none;
      transition: all 0.15s ease;
    }}

    .history-select:hover {{
      background: #E9DCC3;
    }}

    /* Carimbo de Data estilo DECON */
    .date-stamp {{
      font-family: "Bahnschrift", "Segoe UI", sans-serif;
      font-size: 0.82rem;
      font-weight: 700;
      color: #B5462B;
      background: #FBF7EE;
      border: 2px solid #B5462B;
      outline: 1px dashed #B5462B;
      outline-offset: -5px;
      padding: 6px 16px;
      border-radius: 24px;
      transform: rotate(-1.5deg);
      box-shadow: 0 2px 5px rgba(42, 32, 16, 0.1);
      letter-spacing: 0.03em;
    }}

    .grid-dashboard {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 20px;
      position: relative;
      z-index: 2;
    }}

    @media (max-width: 960px) {{
      .grid-dashboard {{
        grid-template-columns: 1fr;
      }}
    }}

    .theme-card {{
      background: var(--card-paper);
      border-radius: 12px;
      border: 1px solid #E2D5BE;
      box-shadow: 3px 4px 0px rgba(205, 184, 146, 0.45), 0 3px 10px rgba(42, 32, 16, 0.06);
      display: flex;
      flex-direction: column;
      overflow: hidden;
      transition: transform 0.15s ease, box-shadow 0.15s ease;
    }}

    .theme-card:hover {{
      box-shadow: 4px 6px 0px rgba(205, 184, 146, 0.65), 0 6px 16px rgba(42, 32, 16, 0.09);
    }}

    /* Faixa superior com textura sutil de Container Marítimo (inspirado nos slides DECON) */
    .card-header {{
      padding: 10px 16px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      flex-wrap: wrap;
      gap: 8px 10px;
      color: #FFF8EC;
      position: relative;
      border-bottom: 3px solid rgba(0, 0, 0, 0.18);
    }}

    .card-header-left {{
      display: flex;
      align-items: center;
      gap: 10px;
      flex: 1 1 190px;
      min-width: 0;
    }}

    .medallion-wrap {{
      display: flex;
      align-items: center;
      justify-content: center;
      flex-shrink: 0;
      filter: drop-shadow(0 2px 3px rgba(0,0,0,0.22));
    }}

    .card-title {{
      font-family: "Bahnschrift", "Segoe UI", sans-serif;
      font-size: 1.05rem;
      font-weight: 700;
      margin: 0;
      color: #FFF8EC;
      letter-spacing: 0.01em;
      line-height: 1.2;
      text-shadow: 0 1px 2px rgba(0,0,0,0.2);
    }}

    .item-count-badge {{
      font-family: "Bahnschrift", "Segoe UI", sans-serif;
      font-size: 0.72rem;
      font-weight: 700;
      padding: 3px 9px;
      border-radius: 12px;
      background: #FFF8EC;
      letter-spacing: 0.02em;
      text-transform: uppercase;
      box-shadow: 0 1px 3px rgba(0,0,0,0.15);
      white-space: nowrap;
      flex-shrink: 0;
      margin-left: auto;
    }}

    @media (max-width: 640px) {{
      body {{
        padding: 8px 8px 0 8px;
      }}
      .outer-frame {{
        padding: 12px 10px 0 10px;
        border-radius: 12px;
      }}
      header {{
        padding: 12px 14px;
      }}
      .header-title-area h1 {{
        font-size: 1.25rem;
      }}
      .card-header {{
        padding: 9px 12px;
      }}
      .medallion-wrap svg {{
        width: 36px;
        height: 36px;
      }}
      .card-title {{
        font-size: 0.95rem;
      }}
      .item-count-badge {{
        font-size: 0.66rem;
        padding: 2px 7px;
      }}
      .card-body {{
        padding: 12px 14px;
      }}
      .theme-tech .card-body {{
        grid-template-columns: 1fr;
      }}
      .theme-tech .subsection {{
        border-right: none;
        border-bottom: 1.5px dotted var(--sand-border);
        padding-right: 0;
        padding-bottom: 12px;
      }}
      .scenic-footer, .footer-caption {{
        margin-left: -10px;
        margin-right: -10px;
      }}
    }}

    .theme-infra .card-header {{
      background: repeating-linear-gradient(90deg, var(--color-infra) 0px, var(--color-infra) 14px, var(--dark-infra) 14px, var(--dark-infra) 16px);
    }}
    .theme-infra .item-count-badge {{ color: var(--color-infra); }}

    .theme-seguros .card-header {{
      background: repeating-linear-gradient(90deg, var(--color-seguros) 0px, var(--color-seguros) 14px, var(--dark-seguros) 14px, var(--dark-seguros) 16px);
    }}
    .theme-seguros .item-count-badge {{ color: var(--color-seguros); }}

    .theme-carbono .card-header {{
      background: repeating-linear-gradient(90deg, var(--color-carbono) 0px, var(--color-carbono) 14px, var(--dark-carbono) 14px, var(--dark-carbono) 16px);
    }}
    .theme-carbono .item-count-badge {{ color: var(--color-carbono); }}

    .theme-divida .card-header {{
      background: repeating-linear-gradient(90deg, var(--color-divida) 0px, var(--color-divida) 14px, var(--dark-divida) 14px, var(--dark-divida) 16px);
    }}
    .theme-divida .item-count-badge {{ color: var(--color-divida); }}

    .theme-tech {{ grid-column: 1 / -1; }}
    .theme-tech .card-header {{
      background: repeating-linear-gradient(90deg, var(--color-tech) 0px, var(--color-tech) 14px, var(--dark-tech) 14px, var(--dark-tech) 16px);
    }}
    .theme-tech .item-count-badge {{ color: var(--color-tech); }}
    .theme-tech .card-body {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
      gap: 18px;
    }}
    .theme-tech .subsection {{
      border-bottom: none;
      border-right: 1.5px dotted var(--sand-border);
      padding-right: 14px;
      padding-bottom: 0;
    }}
    .theme-tech .subsection:last-child {{
      border-right: none;
      padding-right: 0;
    }}

    .card-body {{
      padding: 14px 18px;
      display: flex;
      flex-direction: column;
      gap: 14px;
      flex: 1;
    }}

    .subsection {{
      border-bottom: 1.5px dotted var(--sand-border);
      padding-bottom: 12px;
    }}

    .subsection:last-child {{
      border-bottom: none;
      padding-bottom: 2px;
    }}

    .subsection-title {{
      font-family: "Bahnschrift", "Segoe UI", sans-serif;
      font-size: 0.74rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      color: var(--kraft);
      margin-bottom: 8px;
    }}

    .news-item {{
      margin-bottom: 11px;
      padding-left: 10px;
      border-left: 2.5px solid #E5D7BE;
    }}

    .news-item:last-child {{
      margin-bottom: 0;
    }}

    .news-meta {{
      display: flex;
      align-items: center;
      gap: 6px;
      margin-bottom: 3px;
    }}

    .source-tag {{
      font-size: 0.69rem;
      font-weight: 700;
      color: var(--navy);
      background: #F4EFE6;
      padding: 1px 7px;
      border-radius: 4px;
      border: 1px solid #DECZAA;
    }}

    .news-link {{
      font-size: 0.93rem;
      font-weight: 700;
      color: var(--navy);
      text-decoration: none;
      line-height: 1.35;
      display: block;
    }}

    .news-link:hover {{
      color: #D2694A;
      text-decoration: underline;
    }}

    .news-desc {{
      font-size: 0.84rem;
      color: #4A463F;
      margin: 3px 0 0 0;
      line-height: 1.42;
    }}

    .empty-note {{
      font-size: 0.82rem;
      color: var(--muted);
      font-style: italic;
      padding: 8px 0;
    }}

    /* Gaveta Expansível (Radar Complementar) */
    .radar-drawer {{
      border-top: 1.5px dotted var(--sand-border);
      background: #F8F3E8;
    }}

    .radar-drawer-summary {{
      padding: 9px 18px;
      font-size: 0.8rem;
      font-weight: 700;
      color: var(--navy);
      cursor: pointer;
      display: flex;
      justify-content: space-between;
      align-items: center;
      list-style: none;
      user-select: none;
      transition: background 0.15s ease;
    }}

    .radar-drawer-summary::-webkit-details-marker {{
      display: none;
    }}

    .radar-drawer-summary:hover {{
      background: #EFE6D5;
    }}

    .drawer-chevron {{
      font-size: 0.74rem;
      color: #D2694A;
      font-weight: 700;
    }}

    .radar-drawer-content {{
      padding: 8px 18px 14px 18px;
      display: flex;
      flex-direction: column;
      gap: 9px;
      border-top: 1px dashed var(--sand-border);
      background: #FAF6ED;
    }}

    .radar-compact-item {{
      padding: 7px 11px;
      background: var(--card-paper);
      border: 1px solid #E2D5BE;
      border-radius: 8px;
    }}

    .subsecao-pill {{
      font-size: 0.66rem;
      font-weight: 600;
      color: var(--muted);
      background: #F4EFE6;
      padding: 1px 6px;
      border-radius: 4px;
      border: 1px solid #E2D5BE;
    }}

    /* Faixa Informativa Compacta Brasil Participativo (No Rodapé) */
    .participativo-strip {{
      background: var(--card-paper);
      border: 1px solid var(--sand-border);
      border-left: 5px solid var(--navy);
      border-radius: 10px;
      margin-top: 20px;
      box-shadow: 0 2px 6px rgba(42,32,16,0.05);
      overflow: hidden;
      position: relative;
      z-index: 2;
    }}

    .participativo-summary {{
      padding: 10px 16px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 8px;
      cursor: pointer;
      list-style: none;
      user-select: none;
    }}

    .participativo-summary::-webkit-details-marker {{
      display: none;
    }}

    .participativo-summary:hover {{
      background: #F8F3E8;
    }}

    .participativo-title {{
      font-size: 0.84rem;
      font-weight: 600;
      color: var(--navy);
      display: flex;
      align-items: center;
      gap: 8px;
      margin: 0;
    }}

    .participativo-actions {{
      display: flex;
      align-items: center;
      gap: 10px;
    }}

    .participativo-radar-link {{
      font-size: 0.75rem;
      font-weight: 700;
      color: var(--navy);
      background: #E6ECF4;
      border: 1px solid #B8C7DC;
      padding: 4px 11px;
      border-radius: 16px;
      text-decoration: none;
      transition: background 0.15s ease;
    }}

    .participativo-radar-link:hover {{
      background: #D0DCEC;
    }}

    .participativo-list {{
      display: flex;
      flex-direction: column;
      gap: 6px;
      padding: 8px 16px 12px 16px;
      border-top: 1px dashed var(--sand-border);
      background: #FAF6ED;
    }}

    .participativo-item {{
      display: flex;
      align-items: baseline;
      flex-wrap: wrap;
      gap: 8px;
      font-size: 0.83rem;
      padding: 5px 10px;
      background: var(--card-paper);
      border: 1px solid #E5D7BE;
      border-radius: 6px;
    }}

    .part-badge {{
      font-size: 0.68rem;
      font-weight: 700;
      padding: 1px 6px;
      border-radius: 4px;
      background: #E0F1F3;
      color: #226470;
      white-space: nowrap;
    }}

    .part-orgao {{
      font-size: 0.72rem;
      font-weight: 700;
      color: var(--kraft);
      white-space: nowrap;
    }}

    .part-link {{
      font-weight: 600;
      color: var(--navy);
      text-decoration: none;
    }}

    .part-link:hover {{
      color: #D2694A;
      text-decoration: underline;
    }}

    .part-prazo {{
      font-size: 0.75rem;
      color: var(--muted);
      margin-left: auto;
      white-space: nowrap;
    }}

    /* Ilustração Panorâmica Setorial no Rodapé (Portos, Hidrovias, Aviação e Sustentabilidade) */
    .scenic-footer {{
      margin-top: 12px;
      margin-left: -24px;
      margin-right: -24px;
      position: relative;
      line-height: 0;
    }}

    .scenic-footer svg {{
      width: 100%;
      height: auto;
      display: block;
    }}

    .footer-caption {{
      background: #1F3A5F;
      color: #E9DCC3;
      text-align: center;
      font-size: 0.76rem;
      padding: 8px 16px 12px 16px;
      margin-left: -24px;
      margin-right: -24px;
      letter-spacing: 0.04em;
    }}
    /* Aviso de projeto piloto: faixa discreta no topo + texto completo no rodape */
    .aviso-piloto-faixa {{
      background: #FFF4D6;
      color: #6B5314;
      border-bottom: 1px solid #E6D3A0;
      text-align: center;
      font-size: 0.72rem;
      padding: 4px 12px;
      letter-spacing: 0.02em;
    }}
    .aviso-piloto-rodape {{
      background: #16294A;
      color: #D9CDB2;
      text-align: left;
      font-size: 0.68rem;
      line-height: 1.45;
      padding: 8px 20px 12px 20px;
      margin-left: -24px;
      margin-right: -24px;
      border-top: 1px solid #2D4A75;
    }}
  </style>
  <script>
    function toggleAllDrawers() {{
      const drawers = document.querySelectorAll('details.radar-drawer');
      const btn = document.getElementById('btn-toggle-drawers');
      const anyClosed = Array.from(drawers).some(d => !d.open);
      drawers.forEach(d => d.open = anyClosed);
      if (btn) {{
        btn.textContent = anyClosed ? '➖ Recolher Radares Complementares' : '➕ Expandir Todos os Radares';
      }}
    }}

    function navegarHistorico(arquivo) {{
      if (!arquivo) return;
      const inHistorico = window.location.pathname.replace(/\\\\/g, '/').includes('/historico/');
      if (arquivo === 'ATUAL') {{
        window.location.href = inHistorico ? '../clipping.html' : './clipping.html';
      }} else {{
        window.location.href = inHistorico ? ('./' + arquivo) : ('./historico/' + arquivo);
      }}
    }}

    function copyWhatsAppSummary() {{
      const el = document.getElementById('whatsapp-summary-text');
      const btn = document.getElementById('btn-copy-whatsapp');
      if (!el) return;
      navigator.clipboard.writeText(el.value).then(() => {{
        if (btn) {{
          const orig = btn.textContent;
          btn.textContent = '✅ Copiado! (Cole no WhatsApp)';
          btn.style.background = '#2F8291';
          setTimeout(() => {{
            btn.textContent = orig;
            btn.style.background = '';
          }}, 3000);
        }}
      }});
    }}
  </script>
</head>
<body>
  <textarea id="whatsapp-summary-text" style="display:none;" readonly>{resumo_whatsapp_texto}</textarea>
  <div class="aviso-piloto-faixa" role="note">{AVISO_PILOTO_FRASE}</div>
  <div class="outer-frame">
    <header>
      <div class="header-left">
        <!-- Rosa dos Ventos DECON/MPOR -->
        <svg class="compass-icon" width="54" height="54" viewBox="-52 -52 104 104">
          <circle r="46" fill="#F9F5EC" stroke="#CDB892" stroke-width="2"/>
          <circle r="36" fill="none" stroke="#CDB892" stroke-width="1.5" stroke-dasharray="3 5"/>
          <polygon points="0,-40 8,0 0,40 -8,0" fill="#1F3A5F"/>
          <polygon points="-40,0 0,-8 40,0 0,8" fill="#D9A23C"/>
          <polygon points="0,-40 8,0 -8,0" fill="#D2694A"/>
          <circle r="4" fill="#F9F5EC"/>
        </svg>
        <div class="header-title-area">
          <p class="header-kicker">DECON · Inteligência Regulatória, Financeira & Setorial · MPOR</p>
          <h1>Clipping Diário Executivo</h1>
          <div class="header-bars">
            <div class="bar-ochre"></div>
            <div class="bar-coral"></div>
            <div class="bar-teal"></div>
          </div>
        </div>
      </div>
      <div class="header-meta">
        <button id="btn-copy-whatsapp" class="whatsapp-btn" onclick="copyWhatsAppSummary()" title="Copia o resumo executivo formatado para colar no Grupo da Diretoria no WhatsApp">📲 Copiar Resumo WhatsApp</button>
        {badge_participativo_header}
        {seletor_historico_html}
        <button id="btn-toggle-drawers" class="toggle-drawers-btn" onclick="toggleAllDrawers()">➕ Expandir Todos os Radares</button>
        <span class="date-stamp">📅 {data_formatada}</span>
      </div>
    </header>

    <div class="grid-dashboard">
      {blocos_html}
    </div>

    {faixa_participativo_html}

    <!-- Panorama Setorial DECON/MPOR: Terminal Portuário, Navio Porta-Contêineres, Hidrovia, Avião e Torre -->
    <div class="scenic-footer">
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 810 1920 270" preserveAspectRatio="xMidYMax slice">
        <defs>
          <filter id="sh" x="-10%" y="-10%" width="120%" height="130%">
            <feDropShadow dx="0" dy="2" stdDeviation="2.5" flood-color="#2a2010" flood-opacity=".22"/>
          </filter>
        </defs>
        <!-- Terminal Portuário, Guindastes e Contêineres -->
        <g transform="translate(0,18)">
          <g filter="url(#sh)">
            <rect x="0" y="972" width="560" height="22" fill="#CDB892"/>
            <g stroke="#00000022" stroke-width="1">
              <rect x="40" y="944" width="64" height="28" fill="#D2694A"/><rect x="104" y="944" width="64" height="28" fill="#2F8291"/><rect x="168" y="944" width="64" height="28" fill="#D9A23C"/>
              <rect x="56" y="916" width="64" height="28" fill="#1F3A5F"/><rect x="120" y="916" width="64" height="28" fill="#D2694A"/>
              <rect x="88" y="888" width="64" height="28" fill="#D9A23C"/>
            </g>
            <g transform="translate(37.5,148.5) scale(0.85)">
              <g fill="#D2694A">
                <rect x="300" y="880" width="9" height="92"/><rect x="362" y="880" width="9" height="92"/>
                <rect x="292" y="876" width="88" height="10"/><rect x="250" y="858" width="250" height="8"/>
                <polygon points="318,858 336,818 344,818 356,858"/>
                <rect x="430" y="866" width="18" height="10" fill="#1F3A5F"/>
              </g>
              <g stroke="#D2694A" stroke-width="2"><line x1="340" y1="818" x2="498" y2="860"/><line x1="340" y1="818" x2="252" y2="860"/></g>
              <g fill="#B85A3E" transform="translate(165,97.2) scale(0.9)">
                <rect x="300" y="880" width="9" height="92"/><rect x="362" y="880" width="9" height="92"/>
                <rect x="292" y="876" width="88" height="10"/><rect x="250" y="858" width="250" height="8"/>
                <polygon points="318,858 336,818 344,818 356,858"/>
              </g>
            </g>
          </g>
          <!-- Navio Porta-Contêineres -->
          <g filter="url(#sh)" transform="translate(0,-26)">
            <rect x="600" y="958" width="44" height="20" fill="#D9A23C"/><rect x="644" y="958" width="44" height="20" fill="#2F8291"/><rect x="688" y="958" width="44" height="20" fill="#D2694A"/><rect x="732" y="958" width="44" height="20" fill="#E9DCC3"/>
            <rect x="622" y="938" width="44" height="20" fill="#1F3A5F"/><rect x="666" y="938" width="44" height="20" fill="#D9A23C"/>
            <rect x="790" y="930" width="26" height="48" fill="#F4EFE6"/><rect x="794" y="936" width="18" height="6" fill="#1F3A5F"/>
            <polygon points="575,978 840,978 815,1012 595,1012" fill="#16304F"/>
            <rect x="580" y="984" width="250" height="5" fill="#D2694A"/>
          </g>
          <!-- Aviação e Torre de Controle -->
          <path d="M1060,1000 C1160,980 1250,930 1330,880" fill="none" stroke="#1F3A5F" stroke-width="3" stroke-dasharray="2 10" stroke-linecap="round" opacity=".55"/>
          <g transform="translate(1352,866) rotate(-28) scale(1.15)" fill="#1F3A5F" filter="url(#sh)">
            <path d="M-34,0 C-34,-5 30,-6 36,-1 C38,1 36,4 30,4 L-30,5 C-33,5 -34,3 -34,0 Z"/>
            <path d="M-4,-2 L-22,-26 L-13,-26 L14,-2 Z"/><path d="M-4,3 L-22,27 L-13,27 L14,3 Z" fill="#2F8291"/>
            <path d="M-30,-1 L-38,-14 L-32,-14 L-22,-2 Z"/>
          </g>
          <g filter="url(#sh)">
            <rect x="1530" y="890" width="24" height="88" fill="#E9DCC3"/>
            <polygon points="1514,868 1570,868 1562,892 1522,892" fill="#1F3A5F"/>
            <rect x="1520" y="874" width="44" height="8" fill="#A9CBD8"/>
            <rect x="1538" y="852" width="8" height="16" fill="#1F3A5F"/>
            <rect x="1380" y="972" width="540" height="12" fill="#CDB892"/>
            <rect x="1580" y="944" width="110" height="28" fill="#F4EFE6"/><rect x="1580" y="944" width="110" height="7" fill="#2F8291"/>
          </g>
        </g>
        <!-- Ondas Marítimas e Hidroviárias -->
        <g transform="translate(0,40)">
          <path d="M0,968 C160,940 320,995 480,968 S800,940 960,968 S1280,995 1440,968 S1760,940 1920,968 L1920,1080 L0,1080 Z" fill="#A9CBD8"/>
          <path d="M0,1000 C200,978 380,1022 600,998 S980,975 1200,1000 S1600,1025 1920,996 L1920,1080 L0,1080 Z" fill="#3E8E9C"/>
          <path d="M0,1035 C240,1015 420,1055 700,1035 S1100,1012 1400,1036 S1750,1052 1920,1030 L1920,1080 L0,1080 Z" fill="#1F3A5F"/>
        </g>
      </svg>
    </div>
    <div class="footer-caption">
      DECON / MPOR • Curadoria Autônoma de Inteligência Regulatória, Financeira e Tecnológica • Portos, Aeroportos, Hidrovias, Seguros, Clima & Mercado de Capitais
    </div>
    <div class="aviso-piloto-rodape">{AVISO_PILOTO_TEXTO}</div>
  </div>
</body>
</html>
"""


def render_bloco(chave_tema, titulo, itens):
    """Renderiza um quadrante temático com Medalhão Setorial, Destaques Principais e Gaveta Expansível."""
    destaques = [it for it in itens if it.get("camada") == "destaque"][:4]
    if not destaques:
        destaques = itens[:3]
    ids_destaques = {id(it) for it in destaques}
    complementares = [it for it in itens if id(it) not in ids_destaques]

    n_dest = len(destaques)
    n_comp = len(complementares)
    if n_comp > 0:
        badge_texto = f"{n_dest} destaque{'s' if n_dest != 1 else ''} + {n_comp} no radar"
    else:
        badge_texto = f"{n_dest} matéria{'s' if n_dest != 1 else ''}"

    medalhao_svg = MEDALHOES_SVG.get(chave_tema, "")

    # Agrupa os destaques por subseção
    subsecoes = {}
    for it in destaques:
        sub = it.get("subsecao", "Geral")
        if sub not in subsecoes:
            subsecoes[sub] = []
        subsecoes[sub].append(it)

    corpo_html = []
    if not destaques:
        corpo_html.append('<div class="empty-note">Nenhum evento relevante registrado no período.</div>')
    else:
        for sub_nome, lista in subsecoes.items():
            itens_sub_html = []
            for item in lista:
                fonte = item.get("fonte", "Fonte")
                link = item.get("link", "#")
                titulo_item = item.get("titulo", "")
                resumo = item.get("resumo", "")

                itens_sub_html.append(f"""
            <div class="news-item">
              <div class="news-meta">
                <span class="source-tag">{fonte}</span>
              </div>
              <a class="news-link" href="{link}" target="_blank" rel="noopener noreferrer">{titulo_item}</a>
              <p class="news-desc">{resumo}</p>
            </div>""")

            corpo_html.append(f"""
          <div class="subsection">
            <div class="subsection-title">{sub_nome}</div>
            {''.join(itens_sub_html)}
          </div>""")

    gaveta_html = ""
    if complementares:
        itens_comp_html = []
        for item in complementares:
            fonte = item.get("fonte", "Fonte")
            sub = item.get("subsecao", "Geral")
            link = item.get("link", "#")
            titulo_item = item.get("titulo", "")
            resumo = item.get("resumo", "")
            itens_comp_html.append(f"""
            <div class="radar-compact-item">
              <div class="news-meta">
                <span class="source-tag">{fonte}</span>
                <span class="subsecao-pill">{sub}</span>
              </div>
              <a class="news-link" href="{link}" target="_blank" rel="noopener noreferrer">{titulo_item}</a>
              <p class="news-desc">{resumo}</p>
            </div>""")

        gaveta_html = f"""
        <details class="radar-drawer">
          <summary class="radar-drawer-summary">
            <span>📂 Radar Complementar (+{n_comp} matéria{'s' if n_comp != 1 else ''} relevante{'s' if n_comp != 1 else ''} no período)</span>
            <span class="drawer-chevron">Expandir lista ▾</span>
          </summary>
          <div class="radar-drawer-content">
            {''.join(itens_comp_html)}
          </div>
        </details>"""

    return f"""
      <div class="theme-card theme-{chave_tema}">
        <div class="card-header">
          <div class="card-header-left">
            <div class="medallion-wrap">{medalhao_svg}</div>
            <h2 class="card-title">{titulo}</h2>
          </div>
          <span class="item-count-badge">{badge_texto}</span>
        </div>
        <div class="card-body">
          {''.join(corpo_html)}
        </div>{gaveta_html}
      </div>"""


def render_faixa_participativo(processos_recentes, caminho_radar_html=None):
    """Renderiza barra discreta e recolhível no fundo do painel + pílula rápida para o cabeçalho."""
    link_radar = caminho_radar_html or "https://brasilparticipativo.presidencia.gov.br/processes"
    qtd = len(processos_recentes)

    if qtd == 0:
        header_pill = f'<a class="participativo-radar-link" href="{link_radar}" target="_blank" rel="noopener noreferrer" title="Abrir Radar de Participação, Estruturação & Leilões">🏛️ Radar: Participação, EVTEAs & Leilões ↗</a>'
        rodape_strip = f"""
    <div class="participativo-strip">
      <div class="participativo-summary" style="cursor:default;">
        <span class="participativo-title">🏛️ <strong>Radar Integrado DECON/MPor:</strong> Brasil Participativo (0 novos 48h) • Estruturação/EVTEAs & Carteira de Leilões</span>
        <div class="participativo-actions">
          <a class="participativo-radar-link" href="{link_radar}#estruturacao" target="_blank" rel="noopener noreferrer">📐 EVTEAs & Contratações ↗</a>
          <a class="participativo-radar-link" href="{link_radar}#leiloes" target="_blank" rel="noopener noreferrer">🔔 Leilões ↗</a>
          <a class="participativo-radar-link" href="{link_radar}#sfn" target="_blank" rel="noopener noreferrer">🛡️ SFN, Seguros & Capitais ↗</a>
          <a class="participativo-radar-link" href="{link_radar}" target="_blank" rel="noopener noreferrer">Abrir Painel Completo ↗</a>
        </div>
      </div>
    </div>"""
        return header_pill, rodape_strip

    orgaos_unicos = []
    for p in processos_recentes:
        org = (p.get("orgao_sigla") or p.get("orgao_informado") or "Gov").split("/")[0].strip()
        if org not in orgaos_unicos:
            orgaos_unicos.append(org)
    resumo_orgaos = ", ".join(orgaos_unicos[:4])

    header_pill = f'<a class="participativo-radar-link" href="{link_radar}" target="_blank" rel="noopener noreferrer" title="Abrir Radar de Participação, Estruturação & Leilões">🏛️ Radar: {qtd} novo{"s" if qtd != 1 else ""} ({resumo_orgaos}) | EVTEAs & Leilões ↗</a>'

    linhas = []
    for p in processos_recentes:
        modalidade = p.get("modalidade_exibicao") or p.get("tipo_catalogo") or "Processo"
        orgao = p.get("orgao_sigla") or p.get("orgao_informado") or "Governo Federal"
        titulo = p.get("titulo", "")
        url = p.get("url", "#")
        fim_br = p.get("data_fim_br", "—")
        pub_br = p.get("data_publicacao_br", "Recente")
        badge_st = "📡 Pré-Publicação" if p.get("status_ciclo") == "PRE_PUBLICACAO" else f"🆕 {modalidade}"

        linhas.append(f"""
        <div class="participativo-item">
          <span class="part-badge">{badge_st}</span>
          <span class="part-orgao">[{orgao}]</span>
          <a class="part-link" href="{url}" target="_blank" rel="noopener noreferrer">{titulo}</a>
          <span class="part-prazo">Abertura: {pub_br} • Até: <strong>{fim_br}</strong></span>
        </div>""")

    rodape_strip = f"""
    <details class="participativo-strip">
      <summary class="participativo-summary">
        <span class="participativo-title">🏛️ <strong>Radar Integrado DECON/MPor (48h):</strong> {qtd} novo{'s' if qtd != 1 else ''} processo{'s' if qtd != 1 else ''} ({resumo_orgaos}) + Monitoramento de EVTEAs & Leilões</span>
        <div class="participativo-actions">
          <span class="drawer-chevron">Espiar lista ▾</span>
          <a class="participativo-radar-link" href="{link_radar}#estruturacao" target="_blank" rel="noopener noreferrer" onclick="event.stopPropagation();">📐 EVTEAs & Contratações ↗</a>
          <a class="participativo-radar-link" href="{link_radar}#leiloes" target="_blank" rel="noopener noreferrer" onclick="event.stopPropagation();">🔔 Leilões ↗</a>
          <a class="participativo-radar-link" href="{link_radar}#sfn" target="_blank" rel="noopener noreferrer" onclick="event.stopPropagation();">🛡️ SFN, Seguros & Capitais ↗</a>
          <a class="participativo-radar-link" href="{link_radar}" target="_blank" rel="noopener noreferrer" onclick="event.stopPropagation();">Abrir Radar Completo ↗</a>
        </div>
      </summary>
      <div class="participativo-list">
        {''.join(linhas)}
      </div>
    </details>"""

    return header_pill, rodape_strip


def _formatar_data_iso_br(iso_str):
    partes = iso_str.split("-")
    if len(partes) == 3:
        return f"{partes[2]}/{partes[1]}/{partes[0]}"
    return iso_str


def gerar_catalogo_historico(pasta_historico, datas_iso):
    """Gera a página historico/index.html listando todas as edições diárias salvas."""
    itens_html = []
    for i, dt_iso in enumerate(datas_iso):
        dt_br = _formatar_data_iso_br(dt_iso)
        tag_atual = ' <span style="background:#D2694A;color:#FFF8EC;padding:2px 8px;border-radius:10px;font-size:0.7rem;margin-left:8px;">MAIS RECENTE</span>' if i == 0 else ""
        itens_html.append(f"""
        <a class="hist-card" href="./clipping_{dt_iso}.html">
          <div>
            <span class="hist-date">📅 Edição de {dt_br}</span>{tag_atual}
            <p class="hist-sub">Clipping Diário Regulatório, Financeiro & Tecnológico (DECON / MPOR)</p>
          </div>
          <span class="hist-arrow">Abrir Edição →</span>
        </a>""")

    catalogo_html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Acervo Histórico de Clippings — DECON / MPOR</title>
  <style>
    body {{
      font-family: "Segoe UI", -apple-system, sans-serif;
      background-color: #F4EFE6;
      color: #2C2B28;
      margin: 0;
      padding: 28px 20px;
    }}
    .wrap {{
      max-width: 860px;
      margin: 0 auto;
      background: #FFFCF6;
      border: 2px dotted #CDB892;
      border-radius: 16px;
      padding: 28px;
      box-shadow: 0 4px 16px rgba(42,32,16,0.07);
    }}
    .top-bar {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 12px;
      border-bottom: 2px solid #CDB892;
      padding-bottom: 16px;
      margin-bottom: 20px;
    }}
    .kicker {{
      font-size: 0.74rem;
      font-weight: 700;
      letter-spacing: 0.14em;
      text-transform: uppercase;
      color: #8A7350;
      margin: 0 0 4px 0;
    }}
    h1 {{
      margin: 0;
      font-size: 1.45rem;
      color: #1F3A5F;
    }}
    .btn-back {{
      text-decoration: none;
      font-size: 0.82rem;
      font-weight: 700;
      color: #FFF8EC;
      background: #1F3A5F;
      padding: 8px 16px;
      border-radius: 20px;
    }}
    .btn-back:hover {{ background: #2F8291; }}
    .hist-list {{
      display: flex;
      flex-direction: column;
      gap: 12px;
    }}
    a.hist-card {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      text-decoration: none;
      background: #FAF6ED;
      border: 1px solid #E2D5BE;
      border-left: 5px solid #1F3A5F;
      border-radius: 10px;
      padding: 14px 18px;
      color: #1F3A5F;
      transition: transform 0.12s ease, background 0.12s ease;
    }}
    a.hist-card:hover {{
      transform: translateX(3px);
      background: #F3EBD9;
      border-left-color: #D2694A;
    }}
    .hist-date {{
      font-size: 1rem;
      font-weight: 700;
    }}
    .hist-sub {{
      margin: 4px 0 0 0;
      font-size: 0.82rem;
      color: #6B6457;
    }}
    .hist-arrow {{
      font-size: 0.82rem;
      font-weight: 700;
      color: #D2694A;
      white-space: nowrap;
    }}
  </style>
</head>
<body>
  <div class="wrap">
    <div class="top-bar">
      <div>
        <p class="kicker">DECON · DIRETORIA DE ASSUNTOS ECONÔMICOS · MPOR</p>
        <h1>📚 Repositório Histórico de Clippings Diários</h1>
      </div>
      <a class="btn-back" href="../clipping.html">← Voltar ao Clipping Atual</a>
    </div>
    <div class="hist-list">
      {''.join(itens_html)}
    </div>
  </div>
</body>
</html>"""

    caminho_catalogo = os.path.join(pasta_historico, "index.html")
    with open(caminho_catalogo, "w", encoding="utf-8") as f:
        f.write(catalogo_html)
    return caminho_catalogo


def gerar_resumo_whatsapp(dados_curados, data_formatada, processos_recentes=None):
    """Gera o texto executivo formatado para colar no Grupo da Diretoria no WhatsApp."""
    linhas = [
        f"🧭 *CLIPPING DIÁRIO EXECUTIVO — DECON / MPOR*",
        f"📅 _{data_formatada}_",
        "",
    ]
    icones = {
        "infra": ("⚓", "Infraestrutura & Outorgas"),
        "seguros": ("🛡️", "Seguros & Grandes Riscos"),
        "carbono": ("🍃", "Carbono & Transição Climática"),
        "divida": ("📈", "Dívida & Mercado de Capitais"),
        "tech": ("🔍", "Tecnologia, IA & Gestão"),
    }
    for chave, (emoji, nome) in icones.items():
        itens = dados_curados.get(chave, [])
        if not itens:
            continue
        destaques = [it for it in itens if it.get("camada") == "destaque"][:2] or itens[:2]
        linhas.append(f"{emoji} *{nome}*")
        for it in destaques:
            linhas.append(f"• [{it.get('fonte', '')}] {it.get('titulo', '')}")
        linhas.append("")

    qtd_part = len(processos_recentes or [])
    if qtd_part > 0:
        linhas.append(f"🏛️ *Brasil Participativo (48h):* {qtd_part} novo(s) processo(s) aberto(s).")
        linhas.append("")

    linhas.append("🔗 *Acesse o Painel Completo e Radares Complementares:*")
    linhas.append("https://mdagavea.github.io/inteligencia-regulatoria/clipping.html")
    return "\n".join(linhas)


def gerar_html_email_resumo(dados_curados, data_formatada, processos_recentes=None):
    """Gera o corpo HTML executivo compatível com clientes de e-mail corporativos (Outlook / M365)."""
    configs = [
        ("infra", "⚓ Infraestrutura & Outorgas", "#1F3A5F"),
        ("seguros", "🛡️ Seguros de Grandes Riscos", "#D2694A"),
        ("carbono", "🍃 Mercado de Carbono & Transição Climática", "#2F8291"),
        ("divida", "📈 Instrumentos de Dívida & Mercado de Capitais", "#C18C24"),
        ("tech", "🔍 Tecnologia, IA & Gestão Aplicada", "#3B4D6B"),
    ]

    blocos_email = []
    for chave, titulo, cor in configs:
        itens = dados_curados.get(chave, [])
        destaques = [it for it in itens if it.get("camada") == "destaque"][:3] or itens[:3]
        n_comp = max(0, len(itens) - len(destaques))
        nota_comp = f' <span style="font-size:11px;color:#6B6457;font-weight:normal;">(+{n_comp} no radar web)</span>' if n_comp > 0 else ""

        linhas_it = []
        for it in destaques:
            linhas_it.append(f"""
            <div style="margin-bottom:12px;padding-left:10px;border-left:3px solid {cor};">
              <div style="font-size:11px;font-weight:bold;color:#6B6457;margin-bottom:2px;">[{it.get('fonte', 'Fonte')}] • {it.get('subsecao', '')}</div>
              <a href="{it.get('link', '#')}" style="font-size:14px;font-weight:bold;color:#1F3A5F;text-decoration:none;">{it.get('titulo', '')}</a>
              <div style="font-size:13px;color:#3B3A36;margin-top:3px;line-height:1.4;">{it.get('resumo', '')}</div>
            </div>""")

        blocos_email.append(f"""
        <div style="background:#FFFCF6;border:1px solid #E2D5BE;border-top:4px solid {cor};border-radius:8px;padding:14px 18px;margin-bottom:14px;">
          <h3 style="margin:0 0 12px 0;font-size:15px;color:{cor};">{titulo}{nota_comp}</h3>
          {''.join(linhas_it)}
        </div>""")

    qtd_part = len(processos_recentes or [])
    bloco_part = ""
    if qtd_part > 0:
        bloco_part = f"""
        <div style="background:#FAF6ED;border:1px solid #CDB892;border-left:4px solid #1F3A5F;border-radius:8px;padding:12px 16px;margin-top:16px;font-size:13px;color:#1F3A5F;">
          🏛️ <strong>Radar Brasil Participativo (Últimas 48h):</strong> {qtd_part} novo(s) processo(s) detectado(s).
          <a href="https://mdagavea.github.io/inteligencia-regulatoria/radar.html" style="color:#D2694A;font-weight:bold;margin-left:8px;">Abrir Painel do Radar ↗</a>
        </div>"""

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<body style="margin:0;padding:20px;background-color:#F4EFE6;font-family:'Segoe UI',Arial,sans-serif;color:#2C2B28;">
  <div style="max-width:740px;margin:0 auto 10px auto;background:#FFF4D6;border:1px solid #E6D3A0;border-radius:6px;padding:4px 10px;text-align:center;font-size:11px;color:#6B5314;">{AVISO_PILOTO_FRASE}</div>
  <div style="max-width:740px;margin:0 auto;background:#F4EFE6;">
    <div style="background:#FFFCF6;border:1px solid #CDB892;border-bottom:3px solid #1F3A5F;border-radius:10px;padding:18px 22px;margin-bottom:16px;">
      <div style="font-size:11px;font-weight:bold;letter-spacing:1.5px;color:#8A7350;text-transform:uppercase;">DECON · Diretoria de Assuntos Econômicos · MPOR</div>
      <h1 style="margin:4px 0 8px 0;font-size:21px;color:#1F3A5F;">Clipping Diário Executivo — {data_formatada}</h1>
      <div style="margin-top:12px;">
        <a href="https://mdagavea.github.io/inteligencia-regulatoria/clipping.html" style="display:inline-block;background:#1F3A5F;color:#FFF8EC;text-decoration:none;font-size:13px;font-weight:bold;padding:9px 18px;border-radius:20px;margin-right:8px;">👉 Abrir Painel Completo & Radares Complementares ↗</a>
        <a href="https://mdagavea.github.io/inteligencia-regulatoria/historico/index.html" style="display:inline-block;background:#F4EFE6;color:#1F3A5F;border:1px solid #CDB892;text-decoration:none;font-size:12px;font-weight:bold;padding:8px 14px;border-radius:20px;">📚 Acervo de Edições</a>
      </div>
    </div>
    {''.join(blocos_email)}
    {bloco_part}
    <div style="text-align:center;font-size:11px;color:#6B6457;margin-top:18px;padding-top:10px;border-top:1px dotted #CDB892;">
      DECON / MPOR • Curadoria Autônoma de Inteligência Regulatória, Financeira e Tecnológica
    </div>
    <div style="font-size:10.5px;line-height:1.45;color:#6B6457;margin-top:10px;text-align:left;">{AVISO_PILOTO_TEXTO}</div>
  </div>
</body>
</html>"""


def gerar_html_dashboard(dados_curados, pasta_saida, processos_recentes=None, caminho_radar_html=None):
    """Gera o arquivo HTML com data de hoje, salva no repositório histórico e atualiza clipping_atual.html."""
    hoje = datetime.now()
    hoje_iso = hoje.strftime("%Y-%m-%d")
    data_formatada = hoje.strftime("%d de %B de %Y").replace(
        "January", "Janeiro").replace("February", "Fevereiro").replace("March", "Março").replace(
        "April", "Abril").replace("May", "Maio").replace("June", "Junho").replace(
        "July", "Julho").replace("August", "Agosto").replace("September", "Setembro").replace(
        "October", "Outubro").replace("November", "Novembro").replace("December", "Dezembro")

    pasta_historico = os.path.join(pasta_saida, "historico")
    os.makedirs(pasta_historico, exist_ok=True)

    # Descobre todas as datas salvas no repositório histórico (local e raiz do repo)
    datas_set = {hoje_iso}
    pastas_busca_hist = [pasta_historico]
    pasta_hist_raiz_repo = os.path.join(os.path.dirname(os.path.abspath(pasta_saida)), "historico")
    if os.path.isdir(pasta_hist_raiz_repo) and pasta_hist_raiz_repo not in pastas_busca_hist:
        pastas_busca_hist.append(pasta_hist_raiz_repo)

    for p_hist in pastas_busca_hist:
        if not os.path.isdir(p_hist):
            continue
        for nome_arq in os.listdir(p_hist):
            if nome_arq.startswith("clipping_") and nome_arq.endswith(".html"):
                dt_parte = nome_arq.replace("clipping_", "").replace(".html", "")
                if len(dt_parte) == 10:
                    datas_set.add(dt_parte)
    datas_ordenadas = sorted(datas_set, reverse=True)

    opcoes_select = ['<option value="">📚 Acervo de Edições (' + str(len(datas_ordenadas)) + ')</option>']
    opcoes_select.append('<option value="index.html">🗂️ Ver Catálogo Completo de Datas...</option>')
    for dt_iso in datas_ordenadas[:30]:
        dt_br = _formatar_data_iso_br(dt_iso)
        sufixo = " (Hoje)" if dt_iso == hoje_iso else ""
        opcoes_select.append(f'<option value="clipping_{dt_iso}.html">📄 Edição de {dt_br}{sufixo}</option>')

    seletor_historico_html = (
        '<select class="history-select" onchange="navegarHistorico(this.value); this.selectedIndex=0;" '
        'title="Consultar edições anteriores por data">'
        + "".join(opcoes_select)
        + "</select>"
    )

    configs = [
        ("infra", "Infraestrutura & Outorgas"),
        ("seguros", "Seguros de Grandes Riscos"),
        ("carbono", "Mercado de Carbono & Transição Climática"),
        ("divida", "Instrumentos de Dívida & Mercado de Capitais"),
        ("tech", "Tecnologia, IA & Gestão Aplicada"),
    ]

    blocos = []
    for chave, titulo in configs:
        itens = dados_curados.get(chave, [])
        blocos.append(render_bloco(chave, titulo, itens))

    header_pill, faixa_html = render_faixa_participativo(processos_recentes or [], caminho_radar_html=caminho_radar_html)
    resumo_wpp = gerar_resumo_whatsapp(dados_curados, data_formatada, processos_recentes=processos_recentes)

    html_final = TEMPLATE_HTML.format(
        AVISO_PILOTO_FRASE=AVISO_PILOTO_FRASE,
        AVISO_PILOTO_TEXTO=AVISO_PILOTO_TEXTO,
        data_formatada=data_formatada,
        resumo_whatsapp_texto=resumo_wpp.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"),
        badge_participativo_header=header_pill,
        seletor_historico_html=seletor_historico_html,
        faixa_participativo_html=faixa_html,
        blocos_html="\n".join(blocos),
    )

    nome_arquivo_data = f"clipping_{hoje_iso}.html"
    caminho_data_raiz = os.path.join(pasta_saida, nome_arquivo_data)
    caminho_data_hist = os.path.join(pasta_historico, nome_arquivo_data)
    caminho_atual = os.path.join(pasta_saida, "clipping_atual.html")

    with open(caminho_data_raiz, "w", encoding="utf-8") as f:
        f.write(html_final)

    with open(caminho_data_hist, "w", encoding="utf-8") as f:
        f.write(html_final)

    with open(caminho_atual, "w", encoding="utf-8") as f:
        f.write(html_final)

    gerar_catalogo_historico(pasta_historico, datas_ordenadas)

    return caminho_data_hist, caminho_atual

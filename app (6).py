"""
╔══════════════════════════════════════════════════════════╗
║     CBR LOGÍSTICA — Portal de Recebimento Streamlit      ║
║     v5.0  |  Supabase + Etiquetas X/Y + XML + Manual     ║
╚══════════════════════════════════════════════════════════╝

Instalar:
    pip install streamlit pillow requests

Rodar:
    streamlit run app.py
"""

import io
import os
import zipfile
import xml.etree.ElementTree as ET
from xml.dom import minidom
from datetime import datetime, date

import requests
import streamlit as st
from PIL import Image, ImageDraw, ImageFont

# ─── CONFIG ───────────────────────────────────────────────────────────────────
# ── Credenciais via st.secrets (Streamlit Cloud) ou fallback local ──
def _secret(key, fallback=""):
    try:
        return st.secrets[key]
    except Exception:
        return fallback

SUPABASE_URL       = _secret("SUPABASE_URL",  "https://qoohwyaajiapqyjvotms.supabase.co")
SUPABASE_KEY       = _secret("SUPABASE_KEY",  "sb_publishable_SD5nlCcBenrdnftETZZ7JQ_3QlLizf_")
OPERADOR_LOGISTICO = _secret("OPERADOR",      "CBR LOGÍSTICA")
NS                 = {"nfe": "http://www.portalfiscal.inf.br/nfe"}

SB_HDR = {
    "apikey":        SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type":  "application/json",
    "Prefer":        "return=representation",
}

# Cores da etiqueta
COR_AZUL    = "#003366"
COR_CLARO   = "#E8F0F7"
COR_LARANJA = "#FF6600"
COR_TEXTO   = "#1A1A2E"
COR_BRANCA  = "#FFFFFF"
COR_VERDE   = "#28A745"
COR_AZUL2   = "#001F40"

# ─── PAGE CONFIG ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="CBR Logística — Portal de Recebimento",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── ESTILO GLOBAL ────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@700;800&family=Barlow:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap');

html, body, [class*="css"] { font-family: 'Barlow', sans-serif; }

/* Header customizado */
.cbr-header {
    background: linear-gradient(135deg, #003366 0%, #001f3f 100%);
    border-bottom: 4px solid #FF6600;
    padding: 18px 28px;
    border-radius: 10px;
    margin-bottom: 24px;
    display: flex;
    align-items: center;
    justify-content: space-between;
}
.cbr-header-title {
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 26px; font-weight: 800;
    color: #fff; letter-spacing: .5px;
}
.cbr-header-sub { font-size: 13px; color: #FF6600; font-weight: 700; letter-spacing: 2px; text-transform: uppercase; }
.cbr-badge {
    background: rgba(26,158,74,.2); border: 1px solid rgba(26,158,74,.5);
    color: #4adf82; border-radius: 20px; padding: 4px 14px;
    font-size: 12px; font-weight: 700;
}

/* Stat cards */
.stat-card {
    background: #161b22; border: 1px solid #30363d;
    border-radius: 10px; padding: 18px 22px;
    border-top: 3px solid #FF6600;
}
.stat-label { font-size: 11px; text-transform: uppercase; letter-spacing: 2px; color: #8b949e; font-weight: 700; }
.stat-value { font-family: 'Barlow Condensed', sans-serif; font-size: 38px; font-weight: 800; color: #FF6600; line-height: 1.1; }
.stat-sub   { font-size: 12px; color: #8b949e; margin-top: 4px; }

/* Seção */
.section-title {
    font-family: 'Barlow Condensed', sans-serif; font-size: 16px; font-weight: 800;
    color: #FF6600; text-transform: uppercase; letter-spacing: 1px;
    border-bottom: 1px solid #30363d; padding-bottom: 6px; margin: 18px 0 12px;
}

/* Badge status */
.badge-ok {
    background: rgba(26,158,74,.15); border: 1px solid rgba(26,158,74,.3);
    color: #4adf82; border-radius: 20px; padding: 2px 10px;
    font-size: 11px; font-weight: 700;
}

/* Chave NF-e */
.chave-box {
    font-family: 'IBM Plex Mono', monospace; font-size: 12px;
    background: #0d1117; border: 1px solid #30363d; border-radius: 6px;
    padding: 8px 12px; color: #a5d6ff; word-break: break-all;
}

/* Ajuste sidebar */
section[data-testid="stSidebar"] { background: #0d1117; border-right: 1px solid #30363d; }
</style>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
#  SUPABASE
# ═══════════════════════════════════════════════════════════════════════════════
@st.cache_data(ttl=30, show_spinner=False)
def sb_listar():
    try:
        r = requests.get(
            f"{SUPABASE_URL}/rest/v1/recebimentos",
            headers=SB_HDR,
            params={"order": "criado_em.desc", "limit": "500"},
            timeout=15,
        )
        return r.json() if r.status_code == 200 else []
    except Exception:
        return []


def sb_inserir(payload: dict):
    hdrs = {**SB_HDR, "Prefer": "resolution=merge-duplicates,return=representation"}
    try:
        r = requests.post(
            f"{SUPABASE_URL}/rest/v1/recebimentos",
            headers=hdrs, json=payload, timeout=15,
        )
        data = r.json()
        if r.status_code in (200, 201):
            return (True, data[0] if isinstance(data, list) else data)
        return (False, str(data)[:200])
    except Exception as e:
        return (False, str(e))


def sb_deletar(uid: str):
    try:
        r = requests.delete(
            f"{SUPABASE_URL}/rest/v1/recebimentos",
            headers=SB_HDR,
            params={"id": f"eq.{uid}"},
            timeout=15,
        )
        return r.status_code in (200, 204)
    except Exception:
        return False


# ═══════════════════════════════════════════════════════════════════════════════
#  LEITURA DE XML NF-e
# ═══════════════════════════════════════════════════════════════════════════════
def parsear_nfe(conteudo_xml: bytes) -> dict:
    raiz = ET.fromstring(conteudo_xml)

    def tag(path):
        r = raiz.find(path, NS)
        if r is not None:
            return (r.text or "").strip()
        tl = path.split(":")[-1] if ":" in path else path
        for el in raiz.iter():
            if el.tag.split("}")[-1] == tl:
                return (el.text or "").strip()
        return ""

    chave = tag(".//nfe:chNFe")
    if not chave:
        el = raiz.find(".//{http://www.portalfiscal.inf.br/nfe}infNFe")
        if el is not None:
            chave = el.get("Id", "").replace("NFe", "")

    raw_dt = tag(".//nfe:dhEmi")
    data_emi = ""
    if raw_dt:
        try:
            data_emi = datetime.fromisoformat(raw_dt).strftime("%d/%m/%Y %H:%M")
        except Exception:
            data_emi = raw_dt[:10]

    numero_nf = tag(".//nfe:nNF")
    serie     = tag(".//nfe:serie")

    vNF = tag(".//nfe:vNF")
    try:
        valor = f"R$ {float(vNF):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        valor = ""

    qvol = tag(".//nfe:vol/nfe:qVol")
    try:
        qtd_vol = int(float(qvol))
    except Exception:
        qtd_vol = 0

    return {
        "numero_nf":     f"{numero_nf}-{serie}" if serie else numero_nf,
        "serie":         serie,
        "chave_nfe":     chave or None,
        "data_emissao":  data_emi,
        "natureza_op":   tag(".//nfe:natOp"),
        "protocolo":     tag(".//nfe:nProt"),
        "emitente":      tag(".//nfe:emit/nfe:xNome"),
        "cnpj_emit":     tag(".//nfe:emit/nfe:CNPJ"),
        "destinatario":  tag(".//nfe:dest/nfe:xNome"),
        "cnpj_dest":     tag(".//nfe:dest/nfe:CNPJ"),
        "cidade_dest":   tag(".//nfe:dest/nfe:enderDest/nfe:xMun"),
        "uf_dest":       tag(".//nfe:dest/nfe:enderDest/nfe:UF"),
        "produto":       tag(".//nfe:det/nfe:prod/nfe:xProd"),
        "qtd_produto":   tag(".//nfe:det/nfe:prod/nfe:qCom"),
        "valor_total":   valor,
        "qtd_paletes":   qtd_vol or 1,
        "transportadora":tag(".//nfe:transporta/nfe:xNome"),
        "operador_logistico": OPERADOR_LOGISTICO,
        "xml_original":  conteudo_xml.decode("utf-8", errors="replace"),
        "xml_etiqueta":  "",
    }


# ═══════════════════════════════════════════════════════════════════════════════
#  GERAÇÃO DE XML ETIQUETA
# ═══════════════════════════════════════════════════════════════════════════════
def gerar_xml_etiqueta(d: dict, qtd: int) -> str:
    raiz = ET.Element("RecebimentoMercadoria"); raiz.set("versao", "2.0")
    cab  = ET.SubElement(raiz, "Cabecalho")
    ET.SubElement(cab, "DataEmissao").text     = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    ET.SubElement(cab, "NumeroNota").text       = d.get("numero_nf", "")
    ET.SubElement(cab, "Serie").text            = d.get("serie", "")
    ET.SubElement(cab, "ChaveNFe").text         = d.get("chave_nfe") or ""
    ET.SubElement(cab, "DataEmissaoNF").text    = d.get("data_emissao", "")
    ET.SubElement(cab, "NaturezaOperacao").text = d.get("natureza_op", "")
    ET.SubElement(cab, "Protocolo").text        = d.get("protocolo", "")
    e = ET.SubElement(cab, "Emitente")
    ET.SubElement(e, "RazaoSocial").text = d.get("emitente", "")
    ET.SubElement(e, "CNPJ").text        = d.get("cnpj_emit", "")
    dest = ET.SubElement(cab, "Destinatario")
    ET.SubElement(dest, "RazaoSocial").text = d.get("destinatario", "")
    ET.SubElement(dest, "CNPJ").text        = d.get("cnpj_dest", "")
    ET.SubElement(dest, "Cidade").text      = d.get("cidade_dest", "")
    ET.SubElement(dest, "UF").text          = d.get("uf_dest", "")
    ET.SubElement(cab, "OperadorLogistico").text = OPERADOR_LOGISTICO
    ET.SubElement(cab, "Transportadora").text    = d.get("transportadora", "")
    pr = ET.SubElement(cab, "Produto")
    ET.SubElement(pr, "Descricao").text  = d.get("produto", "")
    ET.SubElement(pr, "Quantidade").text = d.get("qtd_produto", "")
    ET.SubElement(pr, "ValorTotal").text = d.get("valor_total", "")
    pal = ET.SubElement(raiz, "Paletes"); pal.set("quantidadeTotal", str(qtd))
    for i in range(1, qtd + 1):
        p = ET.SubElement(pal, "Palete"); p.set("numero", str(i))
        ET.SubElement(p, "CodigoBarras").text = f"{d.get('numero_nf','')}-P{i:03d}"
        ET.SubElement(p, "Status").text       = "RECEBIDO"
    rod = ET.SubElement(raiz, "Rodape")
    ET.SubElement(rod, "TotalPaletes").text = str(qtd)
    ET.SubElement(rod, "Operador").text     = OPERADOR_LOGISTICO
    dom = minidom.parseString(ET.tostring(raiz, encoding="unicode"))
    return dom.toprettyxml(indent="  ", encoding=None)


# ═══════════════════════════════════════════════════════════════════════════════
#  GERAÇÃO DE ETIQUETA PNG
# ═══════════════════════════════════════════════════════════════════════════════
def _fonte(size: int):
    candidatos = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "arialbd.ttf", "arial.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ]
    for c in candidatos:
        try:
            return ImageFont.truetype(c, size)
        except Exception:
            pass
    return ImageFont.load_default()


def gerar_etiqueta_png(d: dict, num: int, total: int) -> bytes:
    """Retorna bytes PNG da etiqueta num/total."""
    W, H = 900, 580
    img  = Image.new("RGB", (W, H), COR_BRANCA)
    draw = ImageDraw.Draw(img)

    # Cabeçalho
    draw.rectangle([0, 0, W, 100], fill=COR_AZUL)
    draw.text((18, 10), "ETIQUETA DE RECEBIMENTO", font=_fonte(28), fill=COR_BRANCA)
    draw.text((18, 52), OPERADOR_LOGISTICO,         font=_fonte(24), fill=COR_LARANJA)
    draw.text((W - 240, 36), datetime.now().strftime("%d/%m/%Y  %H:%M"),
              font=_fonte(18), fill=COR_CLARO)
    draw.rectangle([0, 100, W, 107], fill=COR_LARANJA)
    draw.rectangle([0, 107, W, H],   fill=COR_CLARO)

    # Bloco NF
    draw.rectangle([20, 122, 400, 290], fill=COR_BRANCA, outline=COR_AZUL, width=2)
    draw.text((36, 130), "Nº NOTA FISCAL", font=_fonte(13), fill=COR_AZUL)
    draw.line([36, 154, 384, 154], fill=COR_AZUL, width=1)
    draw.text((36, 162), (d.get("numero_nf") or "—")[:14], font=_fonte(42), fill=COR_TEXTO)
    draw.text((36, 252),
              f"Série: {d.get('serie','—')}   Emissão: {d.get('data_emissao','—')}",
              font=_fonte(12), fill="#555")

    # Bloco PALETE X/Y
    draw.rectangle([420, 122, 878, 290], fill=COR_AZUL, outline=COR_AZUL, width=2)
    draw.text((436, 130), "PALETE", font=_fonte(14), fill=COR_CLARO)
    draw.line([436, 154, 862, 154], fill=COR_LARANJA, width=2)
    draw.text((440, 155), str(num),   font=_fonte(96), fill=COR_LARANJA)
    draw.text((630, 175), "/",        font=_fonte(56), fill="#7799BB")
    draw.text((668, 194), str(total), font=_fonte(52), fill="#AABBCC")
    cod = f"{d.get('numero_nf','')}-P{num:03d}"
    draw.rectangle([420, 258, 878, 288], fill=COR_AZUL2)
    draw.text((436, 263), f"CÓD: {cod}", font=_fonte(13), fill=COR_LARANJA)

    # Separador
    draw.line([20, 308, W - 20, 308], fill=COR_AZUL, width=1)

    # Remetente / Destinatário
    draw.text((20, 320), "REMETENTE:",   font=_fonte(12), fill=COR_AZUL)
    draw.text((20, 340), (d.get("emitente") or "—")[:48], font=_fonte(15), fill=COR_TEXTO)
    draw.text((480, 320), "DESTINATÁRIO:", font=_fonte(12), fill=COR_AZUL)
    draw.text((480, 340),
              f"{(d.get('destinatario') or '—')[:28]} – {d.get('cidade_dest','')} /{d.get('uf_dest','')}",
              font=_fonte(13), fill=COR_TEXTO)
    draw.line([20, 372, W - 20, 372], fill="#CCC", width=1)

    # Produto / Valor
    draw.text((20, 380), "PRODUTO:", font=_fonte(12), fill=COR_AZUL)
    draw.text((20, 398), f"{d.get('produto','—')}  ×  {d.get('qtd_produto','—')} UN",
              font=_fonte(14), fill=COR_TEXTO)
    draw.text((380, 380), "VALOR TOTAL NF:", font=_fonte(12), fill=COR_AZUL)
    draw.text((380, 398), d.get("valor_total") or "—", font=_fonte(16), fill=COR_TEXTO)
    draw.rectangle([680, 376, 878, 415], fill=COR_VERDE)
    draw.text((700, 384), "RECEBIDO", font=_fonte(18), fill=COR_BRANCA)
    draw.line([20, 428, W - 20, 428], fill="#CCC", width=1)

    # Transportadora / Protocolo
    draw.text((20, 436), "TRANSPORTADORA:", font=_fonte(11), fill=COR_AZUL)
    draw.text((20, 452), (d.get("transportadora") or "—")[:55], font=_fonte(13), fill=COR_TEXTO)
    draw.text((480, 436), "PROTOCOLO:", font=_fonte(11), fill=COR_AZUL)
    draw.text((480, 452), d.get("protocolo") or "—", font=_fonte(13), fill=COR_TEXTO)
    draw.line([20, 478, W - 20, 478], fill="#CCC", width=1)

    # Chave NF-e
    chave = d.get("chave_nfe") or ""
    chave_fmt = " ".join([chave[i:i+4] for i in range(0, 44, 4)]) if len(chave) == 44 else chave
    draw.text((20, 486), "CHAVE NF-e:", font=_fonte(11), fill=COR_AZUL)
    draw.text((20, 502), chave_fmt,     font=_fonte(11), fill="#444")
    draw.text((20,  540),
              f"REF: {d.get('numero_nf','')}-P{num:03d} | {datetime.now().strftime('%Y%m%d%H%M')}",
              font=_fonte(11), fill="#888")
    draw.text((700, 540), "CBR Logística", font=_fonte(11), fill="#888")
    draw.rectangle([2, 2, W - 2, H - 2], outline=COR_AZUL, width=3)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def gerar_zip_etiquetas(d: dict, total: int) -> bytes:
    buf = io.BytesIO()
    nf  = d.get("numero_nf", "NF")
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for i in range(1, total + 1):
            png  = gerar_etiqueta_png(d, i, total)
            nome = f"etiqueta_{nf}_P{i:03d}de{total:03d}.png"
            zf.writestr(nome, png)
    return buf.getvalue()


# ═══════════════════════════════════════════════════════════════════════════════
#  HELPERS UI
# ═══════════════════════════════════════════════════════════════════════════════
def stat_card(label, value, sub=""):
    return f"""
    <div class="stat-card">
      <div class="stat-label">{label}</div>
      <div class="stat-value">{value}</div>
      <div class="stat-sub">{sub}</div>
    </div>"""


def fmt_valor(rows):
    soma = 0.0
    for r in rows:
        v = (r.get("valor_total") or "").replace("R$", "").replace(".", "").replace(",", ".").strip()
        try:
            soma += float(v)
        except Exception:
            pass
    return f"R$ {soma:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


# ═══════════════════════════════════════════════════════════════════════════════
#  SIDEBAR — NAVEGAÇÃO
# ═══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("""
    <div style='text-align:center;padding:16px 0 8px'>
      <div style='background:#FF6600;width:50px;height:50px;border-radius:10px;
                  display:inline-flex;align-items:center;justify-content:center;
                  font-family:Barlow Condensed,sans-serif;font-size:22px;font-weight:800;color:#fff'>
        CB
      </div>
      <div style='font-family:Barlow Condensed,sans-serif;font-size:18px;font-weight:800;color:#fff;margin-top:8px'>
        CBR LOGÍSTICA
      </div>
      <div style='font-size:11px;color:#FF6600;font-weight:700;letter-spacing:2px'>PORTAL v5.0</div>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    pagina = st.radio(
        "Navegação",
        ["📊 Dashboard", "📋 Recebimentos", "📄 Importar XML", "✏️ Inserir Manual", "🖨️ Emitir Etiquetas"],
        label_visibility="collapsed",
    )

    st.divider()
    st.markdown("<div style='font-size:11px;color:#555;text-align:center'>⚡ Conectado ao Supabase</div>",
                unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
#  HEADER
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<div class="cbr-header">
  <div>
    <div class="cbr-header-title">📦 Portal de Recebimento</div>
    <div class="cbr-header-sub">CBR Logística — Sistema de Etiquetas</div>
  </div>
  <div class="cbr-badge">● Supabase conectado</div>
</div>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
#  PÁGINA: DASHBOARD
# ═══════════════════════════════════════════════════════════════════════════════
if pagina == "📊 Dashboard":
    rows = sb_listar()

    total_nf     = len(rows)
    total_pal    = sum(r.get("qtd_paletes", 0) or 0 for r in rows)
    total_valor  = fmt_valor(rows)
    ultimo_nf    = rows[0].get("numero_nf", "—") if rows else "—"
    ultimo_data  = ""
    if rows and rows[0].get("criado_em"):
        try:
            ultimo_data = datetime.fromisoformat(rows[0]["criado_em"]).strftime("%d/%m/%Y")
        except Exception:
            pass

    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(stat_card("Total Recebimentos", total_nf,    "notas registradas"),  unsafe_allow_html=True)
    c2.markdown(stat_card("Total Paletes",      total_pal,   "volumes recebidos"),  unsafe_allow_html=True)
    c3.markdown(stat_card("Valor Acumulado",    total_valor, "soma das NFs"),        unsafe_allow_html=True)
    c4.markdown(stat_card("Última NF",          ultimo_nf,   ultimo_data),           unsafe_allow_html=True)

    st.markdown("---")

    if rows:
        import pandas as pd
        df = pd.DataFrame(rows)

        col_graf1, col_graf2 = st.columns(2)

        with col_graf1:
            st.markdown("**📦 Paletes por Emitente (top 8)**")
            if "emitente" in df.columns and "qtd_paletes" in df.columns:
                g = df.groupby("emitente")["qtd_paletes"].sum().nlargest(8).reset_index()
                g.columns = ["Emitente", "Paletes"]
                g["Emitente"] = g["Emitente"].str[:25]
                st.bar_chart(g.set_index("Emitente"))

        with col_graf2:
            st.markdown("**📅 Recebimentos por data**")
            if "criado_em" in df.columns:
                df2 = df.copy()
                df2["data"] = pd.to_datetime(df2["criado_em"], errors="coerce").dt.date
                g2 = df2.groupby("data").size().reset_index(name="qtd")
                st.line_chart(g2.set_index("data"))

        st.markdown("---")
        st.markdown("**🕐 Últimos 5 recebimentos**")
        cols_show = ["numero_nf", "emitente", "destinatario", "qtd_paletes", "valor_total", "criado_em"]
        cols_ok   = [c for c in cols_show if c in df.columns]
        st.dataframe(df[cols_ok].head(5), use_container_width=True, hide_index=True)
    else:
        st.info("Nenhum recebimento encontrado. Importe um XML ou insira manualmente.")

    if st.button("↺ Atualizar dados", use_container_width=False):
        st.cache_data.clear()
        st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
#  PÁGINA: RECEBIMENTOS
# ═══════════════════════════════════════════════════════════════════════════════
elif pagina == "📋 Recebimentos":
    import pandas as pd

    st.subheader("📋 Todos os Recebimentos")

    rows = sb_listar()
    if not rows:
        st.info("Sem registros. Importe um XML ou insira manualmente.")
        st.stop()

    df = pd.DataFrame(rows)

    # Filtros
    col_b, col_s, col_r = st.columns([3, 1, 1])
    with col_b:
        busca = st.text_input("🔍 Buscar", placeholder="nota, emitente, destinatário…", label_visibility="collapsed")
    with col_s:
        if st.button("↺ Atualizar", use_container_width=True):
            st.cache_data.clear(); st.rerun()
    with col_r:
        # Export CSV
        csv_buf = df.to_csv(index=False).encode("utf-8-sig")
        st.download_button("⬇ CSV", csv_buf, "recebimentos_cbr.csv", "text/csv", use_container_width=True)

    if busca:
        mask = df.apply(lambda row: busca.lower() in " ".join(str(v) for v in row.values).lower(), axis=1)
        df   = df[mask]

    # Exibir tabela
    cols_show = ["numero_nf", "data_emissao", "emitente", "destinatario", "qtd_paletes", "valor_total", "transportadora"]
    cols_ok   = [c for c in cols_show if c in df.columns]
    st.dataframe(
        df[cols_ok].rename(columns={
            "numero_nf":     "NF",
            "data_emissao":  "Emissão",
            "emitente":      "Emitente",
            "destinatario":  "Destinatário",
            "qtd_paletes":   "Paletes",
            "valor_total":   "Valor",
            "transportadora":"Transportadora",
        }),
        use_container_width=True,
        hide_index=True,
        height=340,
    )

    st.markdown("---")
    st.subheader("🔍 Detalhe do Recebimento")

    nfs = [r.get("numero_nf", "") for r in rows]
    sel = st.selectbox("Selecionar NF:", nfs, label_visibility="visible")
    rec = next((r for r in rows if r.get("numero_nf") == sel), None)

    if rec:
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown("<div class='section-title'>Identificação</div>", unsafe_allow_html=True)
            st.write(f"**NF:** {rec.get('numero_nf','—')}")
            st.write(f"**Série:** {rec.get('serie','—')}")
            st.write(f"**Emissão:** {rec.get('data_emissao','—')}")
            st.write(f"**Nat. Op.:** {rec.get('natureza_op','—')}")
            st.write(f"**Protocolo:** {rec.get('protocolo','—')}")
        with c2:
            st.markdown("<div class='section-title'>Partes</div>", unsafe_allow_html=True)
            st.write(f"**Emitente:** {rec.get('emitente','—')}")
            st.write(f"**CNPJ:** {rec.get('cnpj_emit','—')}")
            st.write(f"**Destinatário:** {rec.get('destinatario','—')}")
            st.write(f"**Destino:** {rec.get('cidade_dest','')}/{rec.get('uf_dest','')}")
            st.write(f"**Transportadora:** {rec.get('transportadora','—')}")
        with c3:
            st.markdown("<div class='section-title'>Mercadoria</div>", unsafe_allow_html=True)
            st.write(f"**Produto:** {rec.get('produto','—')}")
            st.write(f"**Quantidade:** {rec.get('qtd_produto','—')} UN")
            st.metric("Paletes", rec.get("qtd_paletes", "—"))
            st.metric("Valor NF", rec.get("valor_total", "—"))

        chave = rec.get("chave_nfe") or ""
        if chave:
            st.markdown("**Chave NF-e:**")
            st.markdown(f'<div class="chave-box">{chave}</div>', unsafe_allow_html=True)

        col_a, col_b2, col_c2 = st.columns(3)
        with col_a:
            # Download XML etiqueta
            xml_bytes = (rec.get("xml_etiqueta") or rec.get("xml_original") or "").encode()
            st.download_button("⬇ Baixar XML", xml_bytes,
                               f"recebimento_{sel}.xml", "application/xml")
        with col_b2:
            if st.button("🖨️ Gerar Etiquetas", key="det_etq"):
                st.session_state["etq_rec"]   = rec
                st.session_state["etq_palete"] = 1
                st.rerun()
        with col_c2:
            if st.button("🗑️ Excluir", key="del_rec", type="secondary"):
                if sb_deletar(rec["id"]):
                    st.success("Excluído!")
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error("Erro ao excluir.")


# ═══════════════════════════════════════════════════════════════════════════════
#  PÁGINA: IMPORTAR XML
# ═══════════════════════════════════════════════════════════════════════════════
elif pagina == "📄 Importar XML":
    st.subheader("📄 Importar XML NF-e")

    arq = st.file_uploader(
        "Arraste ou selecione o arquivo XML NF-e (.xml)",
        type=["xml"],
        help="Suporta NF-e versão 4.00",
    )

    if arq:
        try:
            conteudo = arq.read()
            d = parsear_nfe(conteudo)
            st.success(f"✔ XML lido — NF **{d['numero_nf']}** | {d['qtd_paletes']} paletes")

            st.markdown("<div class='section-title'>Dados Extraídos</div>", unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            with c1:
                st.write(f"**Nº NF / Série:** {d['numero_nf']}")
                st.write(f"**Data Emissão:** {d['data_emissao']}")
                st.write(f"**Emitente:** {d['emitente']}")
                st.write(f"**Destinatário:** {d['destinatario']} — {d['cidade_dest']}/{d['uf_dest']}")
            with c2:
                st.write(f"**Produto:** {d['produto']} × {d['qtd_produto']} UN")
                st.write(f"**Valor Total:** {d['valor_total']}")
                st.write(f"**Transportadora:** {d['transportadora']}")
                st.write(f"**Protocolo:** {d['protocolo']}")

            st.markdown("---")
            qtd = st.number_input("Quantidade de Paletes", min_value=1, max_value=9999,
                                  value=d["qtd_paletes"], step=1)
            st.caption(f"→ Serão geradas **{qtd}** etiqueta(s): 1/{qtd}, 2/{qtd} … {qtd}/{qtd}")

            d["qtd_paletes"]  = qtd
            d["xml_etiqueta"] = gerar_xml_etiqueta(d, qtd)

            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button("✔ Salvar no Banco", type="primary", use_container_width=True):
                    with st.spinner("Salvando no Supabase…"):
                        ok, res = sb_inserir(d)
                    if ok:
                        st.success(f"Salvo! ID: {str(res.get('id',''))[:8]}…")
                        st.session_state["etq_rec"]    = d
                        st.session_state["etq_palete"] = 1
                        st.cache_data.clear()
                    else:
                        st.error(f"Erro: {res}")
            with col2:
                st.download_button("⬇ Baixar XML Etiqueta",
                                   d["xml_etiqueta"].encode(),
                                   f"recebimento_{d['numero_nf']}.xml",
                                   "application/xml", use_container_width=True)
            with col3:
                if st.button("🖨️ Ver Etiquetas", use_container_width=True):
                    st.session_state["etq_rec"]    = d
                    st.session_state["etq_palete"] = 1
                    st.rerun()

        except Exception as ex:
            st.error(f"Erro ao ler XML: {ex}")


# ═══════════════════════════════════════════════════════════════════════════════
#  PÁGINA: INSERIR MANUAL
# ═══════════════════════════════════════════════════════════════════════════════
elif pagina == "✏️ Inserir Manual":
    st.subheader("✏️ Inserção Manual de Recebimento")

    with st.form("form_manual", clear_on_submit=False):
        st.markdown("<div class='section-title'>Nota Fiscal</div>", unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        with c1: numero_nf  = st.text_input("Nº Nota Fiscal *", placeholder="Ex: 57527")
        with c2: serie      = st.text_input("Série",             placeholder="Ex: 2")
        with c3: data_emi   = st.date_input("Data Emissão", value=date.today())

        c4, c5 = st.columns(2)
        with c4: natureza   = st.text_input("Natureza da Operação", placeholder="Ex: Remessa de Vasilhame")
        with c5: protocolo  = st.text_input("Protocolo",            placeholder="Número do protocolo")

        st.markdown("<div class='section-title'>Emitente</div>", unsafe_allow_html=True)
        c6, c7 = st.columns(2)
        with c6: emitente   = st.text_input("Razão Social Emitente *", placeholder="Nome do remetente")
        with c7: cnpj_emit  = st.text_input("CNPJ Emitente",            placeholder="00.000.000/0000-00")

        st.markdown("<div class='section-title'>Destinatário</div>", unsafe_allow_html=True)
        c8, c9 = st.columns(2)
        with c8: destinat   = st.text_input("Razão Social Destinatário *", placeholder="Nome do destinatário")
        with c9: cnpj_dest  = st.text_input("CNPJ Destinatário",            placeholder="00.000.000/0000-00")

        c10, c11 = st.columns([3, 1])
        with c10: cidade    = st.text_input("Cidade Destino", placeholder="Ex: Davinópolis")
        with c11: uf        = st.text_input("UF", placeholder="MA", max_chars=2)

        st.markdown("<div class='section-title'>Mercadoria & Logística</div>", unsafe_allow_html=True)
        c12, c13, c14 = st.columns(3)
        with c12: produto   = st.text_input("Produto / Mercadoria", placeholder="Ex: PALLET CHEP")
        with c13: qtd_prod  = st.text_input("Qtd. Produto",         placeholder="Ex: 50")
        with c14: valor     = st.text_input("Valor Total (R$)",      placeholder="Ex: 6700,00")

        transp = st.text_input("Transportadora", placeholder="Nome da transportadora")

        st.markdown("<div class='section-title'>Paletes</div>", unsafe_allow_html=True)
        qtd_pal = st.number_input("Quantidade de Paletes *", min_value=1, max_value=9999, value=1)
        st.caption(f"→ Serão geradas **{qtd_pal}** etiqueta(s): 1/{qtd_pal}, 2/{qtd_pal} … {qtd_pal}/{qtd_pal}")

        submitted = st.form_submit_button("✔ Salvar no Banco", type="primary", use_container_width=True)

    if submitted:
        if not numero_nf.strip():
            st.error("Informe o Nº da Nota Fiscal.")
        elif not emitente.strip():
            st.error("Informe o Emitente.")
        elif not destinat.strip():
            st.error("Informe o Destinatário.")
        else:
            # Formatar valor
            v = valor.strip()
            if v and not v.startswith("R$"):
                try:
                    v = f"R$ {float(v.replace(',','.').replace('.','',v.count('.')-1)):,.2f}".replace(",","X").replace(".",",").replace("X",".")
                except Exception:
                    v = f"R$ {v}"

            nf_fmt = f"{numero_nf.strip()}-{serie.strip()}" if serie.strip() else numero_nf.strip()

            d = {
                "numero_nf":      nf_fmt,
                "serie":          serie.strip(),
                "chave_nfe":      None,
                "data_emissao":   data_emi.strftime("%d/%m/%Y"),
                "natureza_op":    natureza.strip(),
                "protocolo":      protocolo.strip(),
                "emitente":       emitente.strip(),
                "cnpj_emit":      cnpj_emit.strip(),
                "destinatario":   destinat.strip(),
                "cnpj_dest":      cnpj_dest.strip(),
                "cidade_dest":    cidade.strip(),
                "uf_dest":        uf.strip().upper(),
                "produto":        produto.strip(),
                "qtd_produto":    qtd_prod.strip(),
                "valor_total":    v,
                "qtd_paletes":    int(qtd_pal),
                "transportadora": transp.strip(),
                "operador_logistico": OPERADOR_LOGISTICO,
                "xml_original":   "",
                "xml_etiqueta":   "",
            }
            d["xml_etiqueta"] = gerar_xml_etiqueta(d, int(qtd_pal))

            with st.spinner("Salvando no Supabase…"):
                ok, res = sb_inserir(d)
            if ok:
                st.success(f"✔ Salvo! ID: {str(res.get('id',''))[:8]}…")
                st.session_state["etq_rec"]    = d
                st.session_state["etq_palete"] = 1
                st.cache_data.clear()
                st.info("Vá para 🖨️ Emitir Etiquetas para gerar as etiquetas.")
            else:
                st.error(f"Erro ao salvar: {res}")


# ═══════════════════════════════════════════════════════════════════════════════
#  PÁGINA: EMITIR ETIQUETAS
# ═══════════════════════════════════════════════════════════════════════════════
elif pagina == "🖨️ Emitir Etiquetas":
    st.subheader("🖨️ Emitir Etiquetas de Palete")

    rows = sb_listar()

    # Selecionar registro
    col_sel, col_op = st.columns([3, 1])
    with col_sel:
        opcoes = [r.get("numero_nf", "") for r in rows]
        if "etq_rec" in st.session_state and st.session_state["etq_rec"].get("numero_nf") in opcoes:
            idx_default = opcoes.index(st.session_state["etq_rec"]["numero_nf"])
        else:
            idx_default = 0

        sel_nf = st.selectbox("Selecionar NF:", opcoes, index=idx_default) if opcoes else None

    rec = st.session_state.get("etq_rec") or (
        next((r for r in rows if r.get("numero_nf") == sel_nf), None) if sel_nf else None
    )

    if not rec:
        st.info("Nenhuma NF selecionada. Importe um XML ou insira manualmente.")
        st.stop()

    total = rec.get("qtd_paletes") or 1

    st.markdown(f"""
    <div style='background:#161b22;border:1px solid #30363d;border-radius:8px;padding:14px 20px;margin:10px 0'>
      <span style='color:#8b949e;font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:1px'>NF Selecionada</span><br>
      <span style='font-family:IBM Plex Mono,monospace;font-size:18px;font-weight:700;color:#FF6600'>{rec.get('numero_nf','—')}</span>
      &nbsp;&nbsp;
      <span style='color:#e6edf3'>{rec.get('emitente','')[:40]}</span>
      &nbsp;→&nbsp;
      <span style='color:#e6edf3'>{rec.get('destinatario','')[:30]}</span>
      <span style='float:right;font-size:22px;font-weight:800;color:#FF6600'>{total} paletes</span>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    # Navegação
    if "etq_palete" not in st.session_state:
        st.session_state["etq_palete"] = 1

    num = st.session_state["etq_palete"]

    col_prev, col_num, col_next = st.columns([1, 2, 1])
    with col_prev:
        if st.button("← Anterior", disabled=(num <= 1), use_container_width=True):
            st.session_state["etq_palete"] -= 1
            st.rerun()
    with col_num:
        novo_num = st.number_input(
            "Palete", min_value=1, max_value=total, value=num, step=1,
            label_visibility="collapsed",
        )
        if novo_num != num:
            st.session_state["etq_palete"] = novo_num
            st.rerun()
        st.markdown(
            f"<div style='text-align:center;font-family:IBM Plex Mono,monospace;"
            f"font-size:28px;font-weight:700;color:#FF6600'>{num} / {total}</div>",
            unsafe_allow_html=True,
        )
    with col_next:
        if st.button("Próximo →", disabled=(num >= total), use_container_width=True):
            st.session_state["etq_palete"] += 1
            st.rerun()

    st.markdown("---")

    # Gerar e exibir etiqueta atual
    with st.spinner(f"Gerando etiqueta {num}/{total}…"):
        png_atual = gerar_etiqueta_png(rec, num, total)

    st.image(png_atual, use_container_width=True)

    # Downloads
    st.markdown("---")
    col_d1, col_d2, col_d3, col_d4 = st.columns(4)
    nf = rec.get("numero_nf", "NF")

    with col_d1:
        st.download_button(
            f"⬇ Baixar P{num:03d}",
            png_atual,
            f"etiqueta_{nf}_P{num:03d}de{total:03d}.png",
            "image/png",
            use_container_width=True,
        )
    with col_d2:
        with st.spinner("Gerando ZIP…"):
            zip_bytes = gerar_zip_etiquetas(rec, total)
        st.download_button(
            f"⬇ Baixar todas ({total}) ZIP",
            zip_bytes,
            f"etiquetas_{nf}_todas.zip",
            "application/zip",
            use_container_width=True,
        )
    with col_d3:
        xml_bytes = (rec.get("xml_etiqueta") or gerar_xml_etiqueta(rec, total)).encode()
        st.download_button(
            "⬇ Baixar XML",
            xml_bytes,
            f"recebimento_{nf}.xml",
            "application/xml",
            use_container_width=True,
        )
    with col_d4:
        csv_row = ";".join([
            rec.get("numero_nf",""), rec.get("emitente",""), rec.get("destinatario",""),
            str(total), rec.get("valor_total",""), rec.get("data_emissao","")
        ])
        st.download_button(
            "⬇ CSV desta NF",
            ("numero_nf;emitente;destinatario;qtd_paletes;valor_total;data_emissao\n" + csv_row).encode("utf-8-sig"),
            f"nf_{nf}.csv",
            "text/csv",
            use_container_width=True,
        )

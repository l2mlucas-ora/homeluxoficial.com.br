# -*- coding: utf-8 -*-
"""Catálogo COMERCIAL Homelux em PDF — o catálogo "de vendas": capa, abertura institucional, linhas em destaque,
índice ilustrado, uma divisória por categoria e as famílias em cartões com foto, códigos e embalagem.
(O catálogo TÉCNICO, 1 família por página com desenho e tabela, é outro arquivo: gerar-catalogo-tecnico.py.)

Uso:
  python gerar-catalogo-pdf.py                       # completo → catalogo/pdf/catalogo-homelux-<AAAA-MM>.pdf
  python gerar-catalogo-pdf.py --categorias iluminacao,antenas
  python gerar-catalogo-pdf.py --destaques           # só famílias marcadas destaque=1
  python gerar-catalogo-pdf.py --promo "Setembro"    # folha de promoções (grade 2×2 dos destaques) — substitui o flyer
  python gerar-catalogo-pdf.py --com-precos precos.csv   # coluna de preço para lojista (codigo;preco) — NUNCA vai para o site
  python gerar-catalogo-pdf.py --saida caminho.pdf
Fotos: usa as versões leves do site (jpg 1200 px) quando existem → PDF pequeno.
"""
import argparse, csv, datetime, html, io, json, os, subprocess, sys
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import importlib
gc = importlib.import_module("gerar-catalogo")

RAIZ = gc.RAIZ; CAT = gc.CAT; MARCA = gc.MARCA; SITE = gc.SITE
CHROME = gc.CHROME
esc = gc.esc
def furl(p): return "file:///" + os.path.abspath(p).replace(os.sep, "/")
def marca(nome):
    """Arquivo da marca: MARCA/nome, MARCA/qr/nome ou site/assets/nome (o que existir)."""
    for p in (os.path.join(MARCA, nome), os.path.join(MARCA, "qr", nome), os.path.join(SITE, "assets", nome)):
        if os.path.exists(p): return furl(p)
    return ""

CSS = """
@page { size: A4; margin: 0; }
:root { --navy:#1B2A5B; --navy2:#111B3D; --sol:#F5B82E; --sol2:#FFD166; --verm:#D9342B; --grafite:#1E2129; --cinza:#5B6170; --linha:#E1E4EC; --papel:#F7F8FA; }
* { box-sizing:border-box; -webkit-print-color-adjust:exact !important; print-color-adjust:exact !important; }
html, body { margin:0; }
body { font-family:Manrope,"Segoe UI",sans-serif; color:var(--grafite); font-size:9.2pt; line-height:1.4; }
.pag { width:210mm; height:297mm; padding:14mm 14mm 16mm; page-break-after:always; position:relative; overflow:hidden; background:#fff; }
.pag:last-child { page-break-after:auto; }
h1,h2,h3 { font-family:Sora,"Segoe UI",sans-serif; font-weight:600; color:var(--navy); line-height:1.15; margin:0; }
.kicker { font-size:7.5pt; letter-spacing:.18em; text-transform:uppercase; color:var(--sol); font-weight:700; }
.rod { position:absolute; left:14mm; right:14mm; bottom:8mm; display:flex; justify-content:space-between; align-items:center; font-size:7.5pt; color:var(--cinza); border-top:1px solid var(--linha); padding-top:2.5mm; }
.rod img { height:8mm; }
.rod .n { font-family:Sora; font-weight:600; color:var(--navy); }
/* capa */
.capa { background:var(--navy2); color:#fff; padding:0; }
.capa .faixa { position:absolute; left:0; right:0; top:0; height:6mm; background:linear-gradient(90deg,var(--sol) 0 70%,var(--verm) 70% 100%); }
.capa .topo { padding:22mm 18mm 0; display:flex; justify-content:space-between; align-items:flex-start; }
.capa .topo img { width:64mm; }
.capa .ano { font-family:Sora; font-weight:700; font-size:30pt; color:var(--sol); line-height:1; }
.capa .ano small { display:block; font-size:8pt; letter-spacing:.2em; text-transform:uppercase; color:#c9cfe0; font-weight:600; margin-bottom:1mm; }
.capa .hero { margin:16mm 18mm 0; }
.capa h1 { color:#fff; font-size:34pt; max-width:14ch; }
.capa .sub { color:#c9cfe0; font-size:11.5pt; max-width:46ch; margin-top:5mm; }
.capa .mosaico { position:absolute; left:18mm; right:18mm; bottom:34mm; display:grid; grid-template-columns:repeat(4,1fr); gap:4mm; }
.capa .mosaico div { background:#fff; border-radius:3mm; aspect-ratio:1; display:flex; align-items:center; justify-content:center; padding:4mm; }
.capa .mosaico img { max-width:100%; max-height:100%; object-fit:contain; }
.capa .base { position:absolute; left:18mm; right:18mm; bottom:14mm; display:flex; justify-content:space-between; align-items:flex-end; font-size:8.5pt; color:#c9cfe0; }
.capa .base img { height:12mm; }
/* abertura institucional */
.abre .lead { font-size:12pt; color:var(--navy); max-width:60ch; margin-top:4mm; font-family:Sora; font-weight:600; line-height:1.35; }
.abre .texto { max-width:70ch; color:var(--cinza); font-size:9.5pt; margin-top:4mm; }
.abre .numeros { display:grid; grid-template-columns:repeat(4,1fr); gap:4mm; margin-top:10mm; }
.abre .numeros div { border-top:3px solid var(--sol); padding-top:3mm; }
.abre .numeros b { font-family:Sora; font-size:20pt; color:var(--navy); display:block; line-height:1; }
.abre .numeros span { font-size:8pt; color:var(--cinza); }
.abre .publicos { display:grid; grid-template-columns:repeat(3,1fr); gap:5mm; margin-top:10mm; }
.abre .publicos div { background:var(--papel); border-radius:3mm; padding:5mm; }
.abre .publicos h3 { font-size:11pt; margin-bottom:1.5mm; }
.abre .publicos p { margin:0; font-size:8.5pt; color:var(--cinza); }
.abre .compra { margin-top:10mm; display:grid; grid-template-columns:1fr auto; gap:8mm; align-items:center; background:var(--navy); color:#fff; border-radius:3mm; padding:6mm 7mm; }
.abre .compra h3 { color:#fff; font-size:12pt; }
.abre .compra p { color:#c9cfe0; margin:1.5mm 0 0; font-size:9pt; }
.abre .compra .qr { background:#fff; border-radius:2mm; padding:2mm; width:30mm; height:30mm; }
.abre .compra .qr img { width:100%; height:100%; }
.abre .selo { position:absolute; right:14mm; top:13mm; height:11mm; }
.abre h2 { padding-right:60mm; }
.abre .linhas { display:grid; grid-template-columns:repeat(5,1fr); gap:4mm; margin-top:9mm; }
.abre .linhas figure { margin:0; height:30mm; background:var(--papel); border-radius:2mm; display:flex; align-items:center; justify-content:center; padding:3mm; }
.abre .linhas img { max-height:100%; max-width:100%; object-fit:contain; }
.abre .linhas b { display:block; font-family:Sora; font-weight:600; color:var(--navy); font-size:8.5pt; margin-top:1.5mm; text-align:center; }
/* destaques */
.dest .grade { display:grid; grid-template-columns:1fr 1fr; gap:6mm; margin-top:6mm; }
.dest .item { border:1px solid var(--linha); border-radius:3mm; padding:4mm; display:grid; grid-template-columns:40mm 1fr; gap:4mm; align-items:center; }
.dest .item figure { margin:0; height:40mm; display:flex; align-items:center; justify-content:center; }
.dest .item img { max-height:100%; max-width:100%; object-fit:contain; }
.dest .item h3 { font-size:12pt; }
.dest .item p { margin:1.5mm 0 0; font-size:8.5pt; color:var(--cinza); }
.dest .item .cod { margin-top:2mm; font-size:8pt; color:var(--navy); font-weight:700; }
.tag { display:inline-block; background:var(--sol); color:var(--grafite); font-weight:700; font-size:7pt; letter-spacing:.12em; text-transform:uppercase; padding:1mm 2.5mm; border-radius:1.5mm; }
/* índice ilustrado */
.idx { display:grid; grid-template-columns:1fr; gap:3mm; margin-top:5mm; }
.idx.duas { grid-template-columns:1fr 1fr; }
.idx a { display:grid; grid-template-columns:32mm 1fr auto; gap:5mm; align-items:center; text-decoration:none; color:var(--grafite); border:1px solid var(--linha); border-radius:3mm; padding:2.5mm; }
.idx figure { margin:0; height:24mm; display:flex; align-items:center; justify-content:center; background:var(--papel); border-radius:2mm; }
.idx img { max-height:100%; max-width:100%; object-fit:contain; }
.idx b { font-family:Sora; font-weight:600; color:var(--navy); font-size:11pt; display:block; }
.idx small { color:var(--cinza); font-size:8pt; }
.idx .pg { font-family:Sora; font-weight:700; color:var(--sol); font-size:20pt; }
.como { margin-top:6mm; display:grid; grid-template-columns:repeat(3,1fr); gap:4mm; }
.como div { background:var(--papel); border-radius:3mm; padding:4mm; font-size:8.5pt; color:var(--cinza); }
.como b { display:block; font-family:Sora; color:var(--navy); font-size:10pt; margin-bottom:1mm; }
/* divisória de categoria */
.div { background:var(--navy); color:#fff; padding:0; }
.div .bloco { position:absolute; left:18mm; right:18mm; top:26mm; }
.div .num { font-family:Sora; font-weight:700; font-size:60pt; color:var(--sol); line-height:1; }
.div h2 { color:#fff; font-size:30pt; margin-top:4mm; }
.div p { color:#c9cfe0; font-size:11pt; max-width:50ch; margin-top:4mm; }
.div ul { list-style:none; padding:0; margin:8mm 0 0; display:flex; flex-wrap:wrap; gap:2.5mm; }
.div li { border:1px solid rgb(255 255 255 / .3); border-radius:99px; padding:1.5mm 4mm; font-size:8.5pt; }
.div .foto { position:absolute; left:18mm; right:18mm; bottom:24mm; height:120mm; display:grid; grid-template-columns:1fr 1fr; grid-auto-rows:1fr; gap:4mm; }
.div .foto figure { margin:0; min-height:0; min-width:0; overflow:hidden; background:#fff; border-radius:4mm; display:flex; align-items:center; justify-content:center; padding:5mm; }
.div .foto img { max-height:100%; max-width:100%; width:auto; height:auto; object-fit:contain; }
.div .foto.uma { grid-template-columns:1fr; }
.div .rod .n { color:var(--sol); }
.div .rod { border-color:rgb(255 255 255 / .2); color:#c9cfe0; left:18mm; right:18mm; }
/* categoria — cartões */
.cat-topo { display:flex; align-items:baseline; gap:4mm; margin-bottom:5mm; border-bottom:2px solid var(--sol); padding-bottom:2mm; }
.cat-topo h2 { font-size:15pt; }
.cat-topo .n { margin-left:auto; color:var(--cinza); font-size:8pt; }
.grade { display:grid; grid-template-columns:1fr 1fr; gap:5mm; }
.fam { border:1px solid var(--linha); border-radius:3mm; padding:4mm; display:grid; grid-template-columns:40mm 1fr; gap:4mm; min-height:118mm; page-break-inside:avoid; break-inside:avoid; position:relative; }
.fam figure { margin:0; background:#fff; border:1px solid var(--linha); border-radius:2mm; aspect-ratio:1; display:flex; align-items:center; justify-content:center; padding:2mm; }
.fam img { max-width:100%; max-height:100%; object-fit:contain; }
.fam .thumbs { display:flex; gap:1.5mm; margin-top:1.5mm; }
.fam .thumbs figure { width:12mm; aspect-ratio:1; padding:1mm; }
.fam h3 { font-size:11pt; margin-bottom:1mm; }
.fam .desc { color:var(--cinza); font-size:8pt; margin:0 0 2mm; }
.fam .emb { font-size:7.5pt; color:var(--cinza); margin-top:1.5mm; }
.fam table { border-collapse:collapse; width:100%; font-size:7.6pt; margin-top:1mm; }
.fam td { padding:.8mm 1.5mm .8mm 0; border-bottom:1px solid var(--linha); vertical-align:top; }
.fam td.cod { font-weight:700; color:var(--navy); white-space:nowrap; width:14mm; font-variant-numeric:tabular-nums; }
.fam td.preco { text-align:right; white-space:nowrap; font-weight:700; }
.fam .spec { font-size:7.4pt; color:var(--cinza); margin-top:1.5mm; }
.fam .tag { margin-bottom:1.5mm; }
.fam.largo { grid-column:1 / -1; }
/* promo */
.promo h1 { font-size:26pt; }
.promo .tagp { display:inline-block; background:var(--verm); color:#fff; font-weight:700; font-size:8pt; letter-spacing:.14em; text-transform:uppercase; padding:1.5mm 4mm; border-radius:2mm; }
.promo .grade2 { display:grid; grid-template-columns:1fr 1fr; gap:6mm; margin-top:8mm; }
.promo .item { border:1px solid var(--linha); border-radius:3mm; padding:5mm; text-align:center; }
.promo .item figure { margin:0 0 3mm; height:52mm; display:flex; align-items:center; justify-content:center; }
.promo .item img { max-height:100%; max-width:100%; object-fit:contain; }
.promo .item h3 { font-size:12pt; }
.promo .item .cod { color:var(--cinza); font-size:8pt; }
.promo .cond { margin-top:8mm; background:var(--navy); color:#fff; border-radius:3mm; padding:6mm; display:flex; justify-content:space-between; align-items:center; }
.promo .cond b { font-family:Sora; font-size:14pt; }
/* contracapa */
.contra { background:var(--navy2); color:#fff; display:flex; flex-direction:column; align-items:center; justify-content:center; text-align:center; gap:4mm; }
.contra p { color:#c9cfe0; margin:0; }
.contra .wa { background:#25D366; color:#fff; font-weight:700; padding:3mm 6mm; border-radius:3mm; }
.contra .qrs { display:flex; gap:10mm; margin-top:6mm; }
.contra .qrs div { background:#fff; border-radius:2mm; padding:2mm; width:26mm; }
.contra .qrs img { width:100%; display:block; }
.contra .qrs span { display:block; font-size:7pt; color:#c9cfe0; margin-top:2mm; }
"""

def foto_src(f):
    base = os.path.splitext(os.path.basename(f["jpg"]))[0]
    leve = os.path.join(SITE, "catalogo", "fotos", base + ".jpg")
    if os.path.exists(leve): return furl(leve)
    for ext in (".png", ".jpg"):
        p = os.path.join(CAT, "fotos", base + ext)
        if os.path.exists(p): return furl(p)
    return ""

def img_de(p, i=0):
    fotos = [f for f in p["fotos"] if foto_src(f)]
    return f'<img src="{foto_src(fotos[i])}" alt="">' if len(fotos) > i else ""

def fig(p, i=0, cls=""):
    fotos = [f for f in p["fotos"] if foto_src(f)]
    if len(fotos) <= i: return f'<figure class="{cls}"></figure>'
    return f'<figure class="{cls}"><img src="{foto_src(fotos[i])}" alt=""></figure>'

def familia(p, precos):
    linhas = ""
    for v in p["variacoes"]:
        preco = f'<td class="preco">R$ {precos[v["codigo"]]}</td>' if precos and v["codigo"] in precos else ("<td></td>" if precos else "")
        linhas += f'<tr><td class="cod">{esc(v["codigo"])}</td><td>{esc(v["nome"]) or esc(p["nome"])}</td>{preco}</tr>'
    specs = " · ".join(f'{esc(s["k"])}: {esc(s["v"])}' for s in p["especificacoes"][:4])
    largo = " largo" if len(p["variacoes"]) > 7 else ""
    extras = [f for f in p["fotos"][1:4] if foto_src(f)]
    thumbs = ('<div class="thumbs">' + "".join(f'<figure><img src="{foto_src(f)}" alt=""></figure>' for f in extras) + "</div>") if extras else ""
    tag = '<span class="tag">Destaque</span>' if p["destaque"] else ""
    return f'''<div class="fam{largo}"><div>{fig(p)}{thumbs}</div><div>{tag}<h3>{esc(p["nome"])}</h3><p class="desc">{esc(p["descricao_curta"])}</p>
<table>{linhas}</table>{('<div class="spec">' + specs + '</div>') if specs else ''}<div class="emb">Embalagem: {esc(p["embalagem"])}{(' · ' + esc(p["medidas"])) if p["medidas"] else ''}</div></div></div>'''

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--categorias"); ap.add_argument("--destaques", action="store_true"); ap.add_argument("--promo")
    ap.add_argument("--com-precos"); ap.add_argument("--saida")
    a = ap.parse_args()
    cfg, cats, linhas, _ = gc.carregar()
    prods = [p for p in gc.montar_produtos(linhas, cats, cfg) if p["ativo"]]
    if a.categorias:
        ids = a.categorias.split(","); cats = [c for c in cats if c["id"] in ids]; prods = [p for p in prods if p["categoria"] in ids]
    if a.destaques: prods = [p for p in prods if p["destaque"]]
    precos = None
    if a.com_precos:
        precos = {r["codigo"].strip(): r["preco"].strip() for r in csv.DictReader(io.open(a.com_precos, encoding="utf-8-sig"), delimiter=";")}
    hoje = datetime.date.today(); mes = hoje.strftime("%Y-%m")
    fontes = io.open(gc.FONTES, encoding="utf-8").read()
    logo_neg = marca("logo-homelux-negativo.svg"); logo_h = marca("logo-homelux-horizontal.svg"); logo_hneg = marca("logo-homelux-horizontal-negativo.svg") or logo_neg
    selo = marca("selo-industria-brasileira.svg"); selo_neg = marca("selo-industria-brasileira-negativo.svg") or selo
    qr_site = marca("qr-site.svg"); qr_wa = marca("qr-whatsapp.svg"); qr_cat = marca("qr-catalogo.svg")
    contato = f'SAC {esc(" / ".join(cfg["telefones"]))} · WhatsApp {esc(cfg["whatsapp_exibicao"])} · www.homeluxoficial.com.br'
    def rod(n, escuro=False): return f'<div class="rod"><img src="{logo_hneg if escuro else logo_h}"><span>{contato}</span><span class="n">{n}</span></div>'
    pags = []
    if a.promo:
        sel = sorted(prods, key=lambda p: (not p["destaque"], not p["fotos"]))[:4]
        itens = "".join(f'<div class="item">{fig(p)}<h3>{esc(p["nome"])}</h3><div class="cod">cód. {esc(p["codigo"])} · emb. {esc(p["embalagem"])}</div></div>' for p in sel)
        pags.append(f'''<section class="pag promo"><span class="tagp">Promoção de {esc(a.promo)}</span><h1 style="margin-top:4mm">Promoções de {esc(a.promo)}</h1>
<p style="color:var(--cinza)">Condições especiais para lojistas e distribuidores — válidas durante o mês de {esc(a.promo.lower())} de {hoje.year} ou enquanto durarem os estoques.</p>
<div class="grade2">{itens}</div>
<div class="cond"><div><div class="kicker">Consulte condições</div><b>WhatsApp {esc(cfg["whatsapp_exibicao"])} · SAC {esc(cfg["telefones"][0])}</b></div><img src="{logo_neg}" style="height:22mm"></div>{rod(1)}</section>''')
    else:
        n_fam = len(prods); n_cod = sum(len(p["variacoes"]) for p in prods)
        def capa_de(c):
            fams = [p for p in prods if p["categoria"] == c["id"]]
            return next((p for p in fams if p["destaque"] and p["fotos"]), next((p for p in fams if p["fotos"]), {"fotos": []}))
        destaques = [p for p in prods if p["destaque"] and p["fotos"]]
        # 1 capa
        mosaico = "".join(f'<div>{img_de(p)}</div>' for p in destaques[:8])
        pags.append(f'''<section class="pag capa"><div class="faixa"></div>
<div class="topo"><img src="{logo_neg}"><div class="ano"><small>Catálogo de produtos</small>{hoje.year}</div></div>
<div class="hero"><h1>Materiais elétricos e iluminação feitos em Blumenau</h1><p class="sub">{cfg["anos"]} anos fabricando para lojistas, distribuidores, instaladores e para a sua casa. {n_fam} famílias · {n_cod} códigos.</p></div>
<div class="mosaico">{mosaico}</div>
<div class="base"><div>{esc(cfg["razao_social"])} · CNPJ {esc(cfg.get("cnpj", ""))}<br>{esc(cfg["endereco"])}</div><img src="{selo_neg}"></div></section>''')
        # 2 abertura institucional
        pags.append(f'''<section class="pag abre"><img class="selo" src="{selo}"><span class="kicker">Quem somos</span><h2 style="font-size:22pt;margin-top:2mm">Homelux Soluções Elétricas</h2>
<p class="lead">Há {cfg["anos"]} anos a Homelux fabrica em Blumenau/SC produtos elétricos e de iluminação pensados para quem instala, para quem revende e para quem usa todos os dias.</p>
<p class="texto">{esc(cfg["missao"])} Fabricação própria por injeção de plásticos técnicos, controle de qualidade em cada lote e linhas certificadas onde a norma exige. Tudo o que está neste catálogo é <b>indústria brasileira</b>.</p>
<div class="numeros"><div><b>{cfg["anos"]}</b><span>anos de fábrica em Blumenau/SC</span></div><div><b>{n_fam}</b><span>famílias de produtos</span></div><div><b>{n_cod}</b><span>códigos disponíveis</span></div><div><b>{len(cats)}</b><span>linhas: {esc(", ".join(c["nome"].lower() for c in cats))}</span></div></div>
<div class="publicos"><div><h3>Lojistas e distribuidores</h3><p>Embalagens coletivas para revenda, reposição rápida e representante na sua região. Condições de atacado pelo WhatsApp comercial.</p></div><div><h3>Eletricistas e instaladores</h3><p>Caixas de inspeção certificadas, luminárias e acessórios de instalação com medidas e especificações claras — também no catálogo técnico.</p></div><div><h3>Consumidor</h3><p>Encontre nossos produtos nas lojas de material elétrico e de construção da sua cidade, ou peça pelo site.</p></div></div>
<div class="compra"><div><h3>Como comprar</h3><p>Escolha os códigos neste catálogo ou em <b>www.homeluxoficial.com.br/catalogo</b>, monte o pedido e envie pelo WhatsApp <b>{esc(cfg["whatsapp_exibicao"])}</b>. Nosso comercial responde com prazo e condições. SAC {esc(" / ".join(cfg["telefones"]))} · {esc(cfg["email"])}</p></div><div class="qr"><img src="{qr_cat or qr_site}" alt="QR do catálogo online"></div></div>
<div class="linhas">{"".join(f'<div>{fig(capa_de(c))}<b>{esc(c["nome"])}</b></div>' for c in cats)}</div>{rod(2)}</section>''')
        n = 3
        # 3 linhas em destaque
        if destaques:
            itens = "".join(f'<div class="item">{fig(p)}<div><span class="tag">Destaque</span><h3 style="margin-top:1.5mm">{esc(p["nome"])}</h3><p>{esc(p["descricao_curta"])}</p><div class="cod">{esc(", ".join(v["codigo"] for v in p["variacoes"][:6]))}{"…" if len(p["variacoes"]) > 6 else ""} · emb. {esc(p["embalagem"])}</div></div></div>' for p in destaques[:8])
            pags.append(f'<section class="pag dest"><span class="kicker">Linhas em destaque</span><h2 style="font-size:18pt;margin-top:2mm">Os mais pedidos pelos lojistas</h2><div class="grade">{itens}</div>{rod(n)}</section>'); n += 1
        # 4 índice ilustrado — calcula as páginas de cada categoria antes
        POR_PAG = 4
        blocos = []  # (cat, [fams])
        for c in cats:
            fams = [p for p in prods if p["categoria"] == c["id"]]
            if fams: blocos.append((c, fams))
        pag_idx = n; n += 1
        inicio = {}
        cursor = n
        for c, fams in blocos:
            inicio[c["id"]] = cursor
            cursor += 1 + -(-len(fams) // POR_PAG)   # divisória + páginas de cartões
        idx = ""
        for c, fams in blocos:
            capa = next((p for p in fams if p["destaque"] and p["fotos"]), next((p for p in fams if p["fotos"]), None))
            idx += f'<a href="#cat-{c["id"]}">{fig(capa) if capa else "<figure></figure>"}<div><b>{esc(c["nome"])}</b><small>{esc(c.get("descricao", ""))}<br>{len(fams)} famílias · {sum(len(p["variacoes"]) for p in fams)} códigos</small></div><span class="pg">{inicio[c["id"]]}</span></a>'
        pags.append(f'''<section class="pag"><span class="kicker">Índice</span><h2 style="font-size:18pt;margin-top:2mm">O que você encontra neste catálogo</h2><div class="idx{' duas' if len(blocos) > 6 else ''}">{idx}</div>
<div class="como"><div><b>1. Escolha os códigos</b>Cada família tem os códigos das versões (cor, tamanho, quantidade). São os mesmos do site e da nota fiscal.</div><div><b>2. Monte o pedido</b>Informe código e quantidade; a embalagem coletiva indica a quantidade mínima por caixa para revenda.</div><div><b>3. Envie pelo WhatsApp</b>{esc(cfg["whatsapp_exibicao"])} — o comercial responde com prazo, frete e condições. Ou peça pelo site: www.homeluxoficial.com.br/pedido.html</div></div>
<p style="margin-top:6mm;color:var(--cinza);font-size:8pt;max-width:90ch">Imagens ilustrativas. Especificações completas, medidas e desenhos técnicos no <b>catálogo técnico</b> e na página de cada produto no site.</p>{rod(pag_idx)}</section>''')
        # 5 categorias: divisória + cartões
        for i, (c, fams) in enumerate(blocos, 1):
            capa = next((p for p in fams if p["destaque"] and p["fotos"]), next((p for p in fams if p["fotos"]), None))
            com_foto = ([capa] if capa else []) + [p for p in fams if p["fotos"] and p is not capa][:3]
            com_foto = com_foto[:4] if len(com_foto) >= 4 else com_foto[:1] if len(com_foto) < 2 else com_foto[:2]
            subs = c.get("subcategorias", {}); presentes = [subs.get(s, s) for s in dict.fromkeys(p["subcategoria"] for p in fams if p["subcategoria"])]
            pags.append(f'''<section class="pag div" id="cat-{c["id"]}"><div class="bloco"><div class="num">{i:02d}</div><h2>{esc(c["nome"])}</h2><p>{esc(c.get("descricao", ""))}</p><ul>{"".join(f"<li>{esc(s)}</li>" for s in presentes)}</ul></div>
<div class="foto{' uma' if len(com_foto) == 1 else ''}">{"".join(fig(p) for p in com_foto)}</div>{rod(n, True)}</section>'''); n += 1
            for j in range(0, len(fams), POR_PAG):
                bloco = fams[j:j + POR_PAG]
                pags.append(f'''<section class="pag"><div class="cat-topo"><h2>{esc(c["nome"])}</h2><span class="n">{len(fams)} famílias · página {j // POR_PAG + 1} de {-(-len(fams) // POR_PAG)}</span></div>
<div class="grade">{"".join(familia(p, precos) for p in bloco)}</div>{rod(n)}</section>'''); n += 1
        # contracapa
        qrs = "".join(f'<div><img src="{u}"><span>{t}</span></div>' for u, t in ((qr_site, "Site"), (qr_cat, "Catálogo online"), (qr_wa, "WhatsApp comercial")) if u)
        pags.append(f'''<section class="pag contra"><img src="{logo_neg}" style="width:70mm"><p style="margin-top:6mm"><b style="color:#fff">{esc(cfg["razao_social"])}</b><br>CNPJ {esc(cfg.get("cnpj", ""))}<br>{esc(cfg["endereco"])}</p><p>SAC {esc(" / ".join(cfg["telefones"]))} · {esc(cfg["email"])}</p><p>www.homeluxoficial.com.br · @{esc(cfg["instagram"])}</p><span class="wa">Pedidos pelo WhatsApp {esc(cfg["whatsapp_exibicao"])}</span><div class="qrs">{qrs}</div><img src="{selo_neg}" style="height:12mm;margin-top:8mm"><p style="font-size:7.5pt;margin-top:4mm">Catálogo {hoje.strftime("%m/%Y")}. Especificações conforme cadastro oficial da Homelux. Imagens ilustrativas. Preços e condições sob consulta.{" Tabela de preços de uso exclusivo do lojista." if precos else ""}</p></section>''')
    doc = f'<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><title>Catálogo Homelux {hoje.year}</title><style>{fontes}</style><style>{CSS}</style></head><body>{"".join(pags)}</body></html>'
    os.makedirs(os.path.join(CAT, "pdf"), exist_ok=True)
    nome = a.saida or os.path.join(CAT, "pdf", ("promo-homelux-" + gc.slug(a.promo) + ".pdf") if a.promo else f"catalogo-homelux-{mes}{'-precos' if precos else ''}{'-' + gc.slug(a.categorias) if a.categorias else ''}{'-destaques' if a.destaques else ''}.pdf")
    html_path = os.path.splitext(nome)[0] + ".html"
    io.open(html_path, "w", encoding="utf-8").write(doc)
    subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--no-first-run", "--hide-scrollbars", "--virtual-time-budget=30000", "--no-pdf-header-footer",
                    f"--print-to-pdf={os.path.abspath(nome)}", furl(html_path)], check=True, capture_output=True, timeout=300)
    print("PDF:", nome, f"({os.path.getsize(nome) // 1024} KB, {len(pags)} páginas)")

if __name__ == "__main__":
    main()

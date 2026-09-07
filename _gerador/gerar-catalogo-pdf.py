# -*- coding: utf-8 -*-
"""Catálogo Homelux em PDF sob demanda — gerado do mesmo produtos.csv do site (HTML → Chrome print-to-pdf).

Uso:
  python ferramentas/gerar-catalogo-pdf.py                       # completo, todas as categorias
  python ferramentas/gerar-catalogo-pdf.py --categorias iluminacao,antenas
  python ferramentas/gerar-catalogo-pdf.py --destaques           # só famílias marcadas destaque=1
  python ferramentas/gerar-catalogo-pdf.py --promo "Setembro"    # folha de promoções (grade 2×2 dos destaques) — substitui o flyer
  python ferramentas/gerar-catalogo-pdf.py --com-precos precos.csv   # coluna de preço para lojista (codigo;preco) — NUNCA vai para o site
  python ferramentas/gerar-catalogo-pdf.py --saida catalogo/pdf/meu.pdf

Saída padrão: catalogo/pdf/catalogo-homelux-<AAAA-MM>.pdf (+ HTML fonte ao lado, para ajustes).
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

CSS = """
@page { size: A4; margin: 0; }
:root { --navy:#1B2A5B; --navy2:#111B3D; --sol:#F5B82E; --verm:#D9342B; --grafite:#1E2129; --cinza:#5B6170; --linha:#E1E4EC; --papel:#F7F8FA; }
* { box-sizing:border-box; -webkit-print-color-adjust:exact !important; print-color-adjust:exact !important; }
html, body { margin:0; }
body { font-family:Manrope,"Segoe UI",sans-serif; color:var(--grafite); font-size:9.2pt; line-height:1.4; }
.pag { width:210mm; height:297mm; padding:14mm 14mm 16mm; page-break-after:always; position:relative; overflow:hidden; background:#fff; }
.pag:last-child { page-break-after:auto; }
h1,h2,h3 { font-family:Sora,"Segoe UI",sans-serif; font-weight:600; color:var(--navy); line-height:1.15; margin:0; }
.kicker { font-size:7.5pt; letter-spacing:.18em; text-transform:uppercase; color:var(--sol); font-weight:700; }
.rod { position:absolute; left:14mm; right:14mm; bottom:8mm; display:flex; justify-content:space-between; align-items:center; font-size:7.5pt; color:var(--cinza); border-top:1px solid var(--linha); padding-top:2.5mm; }
.rod img { height:8mm; }
/* capa */
.capa { background:var(--navy2); color:#fff; display:flex; flex-direction:column; justify-content:space-between; padding:22mm 18mm; }
.capa .kicker { color:var(--sol); }
.capa h1 { color:#fff; font-size:30pt; max-width:12ch; margin-top:6mm; }
.capa p { color:#c9cfe0; font-size:11pt; max-width:40ch; }
.capa .cats { display:flex; flex-wrap:wrap; gap:3mm; margin-top:8mm; }
.capa .cats span { border:1px solid rgb(255 255 255 / .25); border-radius:99px; padding:1.5mm 4mm; font-size:8pt; letter-spacing:.08em; text-transform:uppercase; }
.capa .mosaico { display:grid; grid-template-columns:repeat(4,1fr); gap:3mm; margin:10mm 0; }
.capa .mosaico div { background:#fff; border-radius:2.5mm; aspect-ratio:1; display:flex; align-items:center; justify-content:center; padding:3mm; }
.capa .mosaico img { max-width:100%; max-height:100%; object-fit:contain; }
/* índice */
.indice { display:grid; grid-template-columns:1fr 1fr; gap:6mm; margin-top:8mm; }
.indice a { display:flex; justify-content:space-between; align-items:baseline; gap:4mm; text-decoration:none; color:var(--grafite); border-bottom:1px dotted var(--linha); padding:2mm 0; }
.indice b { font-family:Sora; font-weight:600; color:var(--navy); }
/* categoria */
.cat-topo { display:flex; align-items:center; gap:4mm; margin-bottom:6mm; }
.cat-topo h2 { font-size:15pt; }
.cat-topo .n { margin-left:auto; color:var(--cinza); font-size:8pt; }
.grade { display:grid; grid-template-columns:1fr 1fr; gap:5mm; }
.fam { border:1px solid var(--linha); border-radius:3mm; padding:4mm; display:grid; grid-template-columns:34mm 1fr; gap:4mm; page-break-inside:avoid; break-inside:avoid; }
.fam figure { margin:0; background:#fff; border:1px solid var(--linha); border-radius:2mm; aspect-ratio:1; display:flex; align-items:center; justify-content:center; padding:2mm; }
.fam img { max-width:100%; max-height:100%; object-fit:contain; }
.fam h3 { font-size:10.5pt; margin-bottom:1mm; }
.fam .desc { color:var(--cinza); font-size:8pt; margin:0 0 2mm; }
.fam .emb { font-size:7.5pt; color:var(--cinza); }
.fam table { border-collapse:collapse; width:100%; font-size:7.6pt; margin-top:2mm; }
.fam td { padding:.9mm 1.5mm .9mm 0; border-bottom:1px solid var(--linha); vertical-align:top; }
.fam td.cod { font-weight:700; color:var(--navy); white-space:nowrap; width:14mm; font-variant-numeric:tabular-nums; }
.fam td.preco { text-align:right; white-space:nowrap; font-weight:700; }
.fam .spec { font-size:7.4pt; color:var(--cinza); margin-top:1.5mm; }
.fam.largo { grid-column:1 / -1; grid-template-columns:34mm 1fr; }
/* promo */
.promo h1 { font-size:26pt; }
.promo .tag { display:inline-block; background:var(--verm); color:#fff; font-weight:700; font-size:8pt; letter-spacing:.14em; text-transform:uppercase; padding:1.5mm 4mm; border-radius:2mm; }
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
"""

def fig(p, foto_dir):
    if not p["fotos"]: return "<figure></figure>"
    f = os.path.splitext(os.path.basename(p["fotos"][0]["jpg"]))[0]
    src = os.path.join(SITE, "catalogo", "fotos", f + ".jpg")   # versão leve gerada pelo site (1200 px)
    if not os.path.exists(src): src = os.path.join(CAT, "fotos", f + ".png")
    if not os.path.exists(src): src = os.path.join(CAT, "fotos", f + ".jpg")
    return f'<figure><img src="file:///{src.replace(os.sep, "/")}" alt=""></figure>'

def familia(p, precos):
    linhas = ""
    for v in p["variacoes"]:
        preco = f'<td class="preco">R$ {precos[v["codigo"]]}</td>' if precos and v["codigo"] in precos else ("<td></td>" if precos else "")
        linhas += f'<tr><td class="cod">{esc(v["codigo"])}</td><td>{esc(v["nome"]) or esc(p["nome"])}</td>{preco}</tr>'
    specs = " · ".join(f'{esc(s["k"])}: {esc(s["v"])}' for s in p["especificacoes"][:4])
    largo = " largo" if len(p["variacoes"]) > 7 else ""
    return f'''<div class="fam{largo}">{fig(p, None)}<div><h3>{esc(p["nome"])}</h3><p class="desc">{esc(p["descricao_curta"])}</p>
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
    logo_neg = "file:///" + os.path.join(MARCA, "logo-homelux-negativo.svg").replace(os.sep, "/")
    logo_h = "file:///" + os.path.join(MARCA, "logo-homelux-horizontal.svg").replace(os.sep, "/")
    rod = lambda n: f'<div class="rod"><img src="{logo_h}"><span>SAC {esc(" / ".join(cfg["telefones"]))} · {esc(cfg["email"])} · www.homeluxoficial.com.br</span><span>{n}</span></div>'
    pags = []
    if a.promo:
        sel = sorted(prods, key=lambda p: (not p["destaque"], not p["fotos"]))[:4]
        itens = "".join(f'<div class="item">{fig(p, None)}<h3>{esc(p["nome"])}</h3><div class="cod">cód. {esc(p["codigo"])} · emb. {esc(p["embalagem"])}</div></div>' for p in sel)
        pags.append(f'''<section class="pag promo"><span class="tag">Promoção de {esc(a.promo)}</span><h1 style="margin-top:4mm">Promoções de {esc(a.promo)}</h1>
<p style="color:var(--cinza)">Condições especiais para lojistas e distribuidores — válidas durante o mês de {esc(a.promo.lower())} de {hoje.year} ou enquanto durarem os estoques.</p>
<div class="grade2">{itens}</div>
<div class="cond"><div><div class="kicker">Consulte condições</div><b>WhatsApp {esc(cfg["whatsapp_exibicao"])} · SAC {esc(cfg["telefones"][0])}</b></div><img src="{logo_neg}" style="height:22mm"></div>{rod(1)}</section>''')
    else:
        destaques = [p for p in prods if p["destaque"] and p["fotos"]][:8]
        mosaico = "".join(f"<div>{fig(p, None)[8:-9]}</div>" for p in destaques)
        pags.append(f'''<section class="pag capa"><div><span class="kicker">Catálogo de produtos · {hoje.year}</span><h1>Materiais elétricos e iluminação</h1><p style="margin-top:4mm">{cfg["anos"]} anos fabricando em Blumenau/SC para lojistas, distribuidores e para a sua casa.</p>
<div class="cats">{"".join(f"<span>{esc(c['nome'])}</span>" for c in cats)}</div></div><div class="mosaico">{mosaico}</div><div style="display:flex;justify-content:space-between;align-items:flex-end"><img src="{logo_neg}" style="width:60mm"><div style="text-align:right;font-size:8.5pt;color:#c9cfe0">{esc(cfg["razao_social"])}<br>SAC {esc(cfg["telefones"][0])} · www.homeluxoficial.com.br</div></div></section>''')
        idx = "".join(f'<a href="#cat-{c["id"]}"><b>{esc(c["nome"])}</b><span>{sum(1 for p in prods if p["categoria"] == c["id"])} famílias · {sum(len(p["variacoes"]) for p in prods if p["categoria"] == c["id"])} códigos</span></a>' for c in cats)
        pags.append(f'''<section class="pag"><span class="kicker">Índice</span><h2 style="font-size:18pt;margin-top:2mm">O que você encontra neste catálogo</h2>
<div class="indice">{idx}</div><p style="margin-top:10mm;color:var(--cinza);max-width:70ch">Nossa missão: {esc(cfg["missao"])}</p>
<p style="color:var(--cinza)">Pedidos e condições: WhatsApp {esc(cfg["whatsapp_exibicao"])} · SAC {esc(" / ".join(cfg["telefones"]))} · {esc(cfg["email"])}. Catálogo online sempre atualizado em www.homeluxoficial.com.br/catalogo.</p>{rod(2)}</section>''')
        n = 3
        for c in cats:
            fams = [p for p in prods if p["categoria"] == c["id"]]
            if not fams: continue
            # até 6 famílias por página (3 linhas × 2)
            for i in range(0, len(fams), 6):
                bloco = fams[i:i + 6]
                topo = f'<div class="cat-topo"><span class="kicker">{esc(c.get("descricao", ""))}</span></div>' if i else ""
                pags.append(f'''<section class="pag" id="cat-{c["id"]}"><div class="cat-topo"><h2>{esc(c["nome"])}</h2><span class="n">{esc(c.get("descricao", ""))}</span></div>
<div class="grade">{"".join(familia(p, precos) for p in bloco)}</div>{rod(n)}</section>''')
                n += 1
        pags.append(f'''<section class="pag contra"><img src="{logo_neg}" style="width:70mm"><p style="margin-top:6mm"><b style="color:#fff">{esc(cfg["razao_social"])}</b><br>{esc(cfg["endereco"])}</p><p>SAC {esc(" / ".join(cfg["telefones"]))} · {esc(cfg["email"])}</p><p>www.homeluxoficial.com.br · @{esc(cfg["instagram"])}</p><span class="wa">Pedidos pelo WhatsApp {esc(cfg["whatsapp_exibicao"])}</span><p style="font-size:7.5pt;margin-top:8mm">Especificações conforme o catálogo {hoje.year}. Imagens ilustrativas. Preços e condições sob consulta.{" Tabela de preços de uso exclusivo do lojista." if precos else ""}</p></section>''')
    doc = f'<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><title>Catálogo Homelux {hoje.year}</title><style>{fontes}</style><style>{CSS}</style></head><body>{"".join(pags)}</body></html>'
    os.makedirs(os.path.join(CAT, "pdf"), exist_ok=True)
    nome = a.saida or os.path.join(CAT, "pdf", ("promo-homelux-" + gc.slug(a.promo) + ".pdf") if a.promo else f"catalogo-homelux-{mes}{'-precos' if precos else ''}{'-' + gc.slug(a.categorias) if a.categorias else ''}{'-destaques' if a.destaques else ''}.pdf")
    html_path = os.path.splitext(nome)[0] + ".html"
    io.open(html_path, "w", encoding="utf-8").write(doc)
    subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--no-first-run", "--hide-scrollbars", "--virtual-time-budget=30000", "--no-pdf-header-footer",
                    f"--print-to-pdf={os.path.abspath(nome)}", "file:///" + os.path.abspath(html_path).replace(os.sep, "/")], check=True, capture_output=True, timeout=300)
    print("PDF:", nome, f"({os.path.getsize(nome) // 1024} KB, {len(pags)} páginas)")

if __name__ == "__main__":
    main()

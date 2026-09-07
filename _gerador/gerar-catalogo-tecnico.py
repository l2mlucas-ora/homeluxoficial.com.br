# -*- coding: utf-8 -*-
"""Catálogo TÉCNICO Homelux (estilo OPL): 1 família por página, com fotos, informações técnicas, desenho técnico e tabela de códigos.

Uso:
  python ferramentas/gerar-catalogo-tecnico.py                          # todas as categorias → catalogo/pdf/catalogo-tecnico-homelux-<AAAA>.pdf
  python ferramentas/gerar-catalogo-tecnico.py --categorias iluminacao  # só uma linha (ex.: "Catálogo Iluminação")
  python ferramentas/gerar-catalogo-tecnico.py --com-precos precos.csv  # coluna de preço (só lojista; nunca no site)
  python ferramentas/gerar-catalogo-tecnico.py --saida caminho.pdf

Requer: catalogo/desenhos/<codigo>.svg (python ferramentas/gerar-desenhos.py) e fonts-inline.css.
"""
import argparse, csv, datetime, io, math, os, random, subprocess, sys
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import importlib
gc = importlib.import_module("gerar-catalogo")
RAIZ, CAT, MARCA, SITE = gc.RAIZ, gc.CAT, gc.MARCA, gc.SITE
CHROME = gc.CHROME
esc = gc.esc
def furl(p): return "file:///" + os.path.abspath(p).replace(os.sep, "/")

CORES = {"branco": "#FFFFFF", "branca": "#FFFFFF", "preto": "#15161A", "preta": "#15161A", "marrom": "#4B2E1E", "marrom café": "#4B2E1E", "café": "#4B2E1E", "azul": "#1E5AA8", "verde": "#2E8B57",
         "vermelho": "#D9342B", "vermelha": "#D9342B", "amarelo": "#F5C400", "bege": "#E8D9B8", "cinza": "#9A9AA0", "inox": "#C6C8CC", "cristal": "#DDE6F0", "colorido": "linear-gradient(90deg,#D9342B,#F5C400,#2E8B57,#1E5AA8)"}

CSS = """
@page { size: A4; margin: 0; }
:root { --navy:#1B2A5B; --navy2:#111B3D; --sol:#F5B82E; --ouro:#C9A24A; --grafite:#1E2129; --cinza:#5B6170; --linha:#D9DDE6; --papel:#F4F5F8; }
* { box-sizing:border-box; -webkit-print-color-adjust:exact !important; print-color-adjust:exact !important; }
html, body { margin:0; } body { font-family:Manrope,"Segoe UI",sans-serif; color:var(--grafite); font-size:8.6pt; line-height:1.45; }
.pag { width:210mm; height:297mm; padding:16mm 16mm 18mm; page-break-after:always; position:relative; overflow:hidden; background:#fff; }
.pag:last-child { page-break-after:auto; }
h1,h2,h3 { font-family:Sora,"Segoe UI",sans-serif; margin:0; line-height:1.1; color:var(--navy); }
.rod { position:absolute; left:16mm; right:16mm; bottom:9mm; display:flex; justify-content:flex-end; align-items:center; gap:3mm; font-size:8pt; color:var(--cinza); border-top:1.2px solid var(--navy); padding-top:2.5mm; }
.rod img { height:6.5mm; } .rod .n { font-weight:700; color:var(--navy); }
/* capa e divisórias */
.capa { padding:0; background:var(--navy2); color:#fff; }
.capa svg { position:absolute; inset:0; width:100%; height:100%; }
.capa .tit { position:absolute; left:0; right:0; top:44%; text-align:center; font-family:Sora; font-weight:500; letter-spacing:.16em; font-size:11pt; text-transform:uppercase; }
.capa .tit b { display:block; font-weight:700; font-size:12pt; margin-top:1mm; }
.capa .logo { position:absolute; left:0; right:0; bottom:20mm; text-align:center; } .capa .logo img { width:62mm; }
.div { background:var(--navy); color:#fff; padding:0; }
.div svg { position:absolute; inset:0; width:100%; height:100%; }
.div .txt { position:absolute; left:18mm; right:18mm; bottom:26mm; }
.div .kick { font-size:8pt; letter-spacing:.22em; text-transform:uppercase; color:var(--sol); font-weight:700; }
.div h1 { color:#fff; font-size:34pt; font-weight:700; margin:3mm 0 5mm; }
.div ul { list-style:none; margin:0; padding:0; columns:2; column-gap:10mm; font-size:9pt; color:#d5dbea; }
.div li { padding:1mm 0; border-bottom:1px solid rgb(255 255 255 / .12); break-inside:avoid; }
/* institucional */
.inst { display:grid; grid-template-columns:1fr 1fr; gap:10mm; align-items:end; height:100%; }
.inst .faixa { position:absolute; left:0; right:0; top:38%; height:2mm; background:linear-gradient(90deg, var(--papel), var(--linha)); }
.inst p { margin:0 0 3mm; font-size:9pt; }
.inst .logo { text-align:center; margin-top:8mm; } .inst .logo img { width:38mm; }
/* técnica */
.tec h2 { font-size:15pt; font-weight:400; letter-spacing:.02em; margin-bottom:2mm; }
.tec h3 { font-size:8pt; letter-spacing:.14em; text-transform:uppercase; border-bottom:1.2px solid var(--navy); padding-bottom:1mm; margin:5mm 0 2mm; }
.tec .g2 { display:grid; grid-template-columns:1fr 1fr; gap:10mm; }
.tec table { width:100%; border-collapse:collapse; font-size:7.8pt; } .tec td { padding:1.1mm 1.5mm 1.1mm 0; border-bottom:1px solid var(--linha); vertical-align:top; }
.tec td.n { font-family:Sora; font-weight:600; color:var(--navy); width:7mm; font-size:10pt; }
.tec .chip { display:inline-block; border:1px solid var(--navy); color:var(--navy); border-radius:2mm; padding:.6mm 2.4mm; margin:0 1.5mm 1.5mm 0; font-weight:700; font-size:8pt; }
/* produto */
.prod .cab { margin-bottom:4mm; } .prod .cab .sub { font-family:Sora; font-weight:400; font-size:13pt; letter-spacing:.14em; text-transform:uppercase; color:var(--grafite); }
.prod .cab .sub::after { content:"|"; margin:0 3mm; color:var(--cinza); } .prod .cab .nome { font-family:Sora; font-weight:800; font-size:24pt; text-transform:uppercase; color:var(--navy); letter-spacing:-.01em; }
.prod .topo { display:grid; grid-template-columns:1fr 78mm; gap:8mm; min-height:60mm; }
.prod .desc { font-size:8.8pt; margin:0 0 3mm; } .prod ul { margin:0 0 3mm; padding-left:4mm; font-size:8.6pt; } .prod li { margin-bottom:.6mm; }
.prod .selo { height:8mm; margin-top:2mm; display:block; }
.prod .fotos { display:grid; grid-template-columns:repeat(2, 1fr); gap:3mm; align-content:start; }
.prod .fotos figure { margin:0; background:#fff; border:1px solid var(--linha); border-radius:2mm; aspect-ratio:1; display:flex; align-items:center; justify-content:center; padding:2mm; }
.prod .fotos figure:first-child { grid-column:1 / -1; aspect-ratio:auto; height:48mm; }
.prod .fotos img { max-width:100%; max-height:100%; object-fit:contain; }
.prod .meio { display:grid; grid-template-columns:1fr 84mm; gap:8mm; margin-top:5mm; } .prod .meio.so-info { grid-template-columns:1fr; }
.prod h3 { font-size:7.6pt; letter-spacing:.14em; text-transform:uppercase; border-bottom:1.2px solid var(--navy); padding-bottom:1mm; margin:0 0 2mm; }
.prod table.info { width:100%; border-collapse:collapse; font-size:8pt; } .prod table.info td { padding:1.2mm 0; border-bottom:1px solid var(--linha); } .prod table.info td:first-child { color:var(--cinza); font-style:italic; width:34%; } .prod table.info td:last-child { text-align:right; font-weight:600; }
.prod .des { border:1px solid var(--linha); border-radius:2mm; padding:2mm; background:#fff; } .prod .des img { width:100%; display:block; }
.prod .cods { margin-top:5mm; display:grid; grid-template-columns:repeat(3, 1fr); gap:5mm; align-items:start; }
.prod table.cod { width:100%; border-collapse:collapse; font-size:7.8pt; border:1px solid var(--linha); }
.prod table.cod th { background:var(--papel); font-size:6.8pt; letter-spacing:.1em; text-transform:uppercase; text-align:left; padding:1.4mm 2mm; border-bottom:1px solid var(--linha); color:var(--navy); }
.prod table.cod td { padding:1.3mm 2mm; border-bottom:1px solid var(--linha); vertical-align:middle; } .prod table.cod td.c { font-family:Sora; font-weight:700; color:var(--navy); white-space:nowrap; font-variant-numeric:tabular-nums; }
.prod .sw { display:inline-block; width:3.2mm; height:3.2mm; border:1px solid #bbb; border-radius:.6mm; vertical-align:middle; margin-right:1.5mm; }
.prod td.preco { text-align:right; font-weight:700; white-space:nowrap; }
/* contracapa */
.contra { background:var(--navy2); color:#fff; display:flex; flex-direction:column; align-items:center; justify-content:center; text-align:center; gap:3mm; }
.contra p { color:#c9cfe0; margin:0; font-size:9.5pt; } .contra .wa { background:#25D366; color:#fff; font-weight:700; padding:3mm 6mm; border-radius:3mm; margin-top:4mm; }
"""

def fundo_capa(seed=7, w=210, h=297, ondas=True):
    """Ondas em camadas de azul + linhas finas de 'circuito' (vetor, sem raster) — a capa OPL, na paleta Homelux."""
    rnd = random.Random(seed); s = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" preserveAspectRatio="xMidYMid slice"><rect width="{w}" height="{h}" fill="#111B3D"/>'
    tons = ["#15224A", "#1B2A5B", "#22366F", "#2A4382", "#345194"]
    if ondas:
        for i, cor in enumerate(tons):
            y0 = 40 + i * 55 + rnd.uniform(-10, 10); pts = [(-20, y0)]
            for x in range(0, w + 60, 45): pts.append((x, y0 + rnd.uniform(-45, 45) - i * 6))
            d = f"M{pts[0][0]} {pts[0][1]} " + " ".join(f"S{x - 20} {y - rnd.uniform(-25, 25)} {x} {y}" for x, y in pts[1:]) + f" L{w + 20} {h + 20} L-20 {h + 20} Z"
            s += f'<path d="{d}" fill="{cor}" opacity=".95"/>'
    # circuito: polilinhas finas com nós
    for _ in range(9):
        x, y = rnd.uniform(0, w), rnd.uniform(0, h); d = f"M{x:.1f} {y:.1f}"; nos = [(x, y)]
        for _ in range(rnd.randint(3, 6)):
            ang = rnd.choice([0, 60, 120, 180, 240, 300]); L = rnd.uniform(18, 60); x += L * math.cos(math.radians(ang)); y += L * math.sin(math.radians(ang)); d += f" L{x:.1f} {y:.1f}"; nos.append((x, y))
        s += f'<path d="{d}" fill="none" stroke="#9fb3e8" stroke-width=".35" opacity=".8"/>' + "".join(f'<circle cx="{nx:.1f}" cy="{ny:.1f}" r=".9" fill="#F5B82E" opacity=".9"/>' for nx, ny in nos[1:-1])
    return s + "</svg>"

def foto_src(f):
    base = os.path.splitext(os.path.basename(f["jpg"]))[0]
    leve = os.path.join(SITE, "catalogo", "fotos", base + ".jpg")   # versão leve gerada pelo site (1200 px)
    if os.path.exists(leve): return furl(leve)
    for ext in (".png", ".jpg"):
        p = os.path.join(CAT, "fotos", base + ext)
        if os.path.exists(p): return furl(p)
    return ""

def cor_da(nome, familia_cores):
    n = (nome or "").lower()
    for k, v in CORES.items():
        if k in n: return v, k
    if familia_cores: return CORES.get(familia_cores[0].lower(), "#FFFFFF"), familia_cores[0]
    return None, ""

def pagina_produto(p, n, precos, logo_h):
    subcat = p.get("subcategoria", "").replace("-", " ") or p["categoria_nome"]
    fotos = [f for f in p["fotos"][:3] if foto_src(f)]
    figs = "".join(f'<figure><img src="{foto_src(f)}" alt=""></figure>' for f in fotos)
    specs = p["especificacoes"]
    bullets = [f"{esc(s['k'])}: {esc(s['v'])}" for s in specs if s["k"].lower() in ("uso", "linha", "certificada", "homologação", "antivibratório", "portátil", "inclui")]
    bullets += [esc(t.capitalize()) for t in p["tags"][:4]]
    bullets = bullets[:6] or ["Fabricação própria em Blumenau/SC", "Embalagem coletiva para revenda"]
    info = "".join(f'<tr><td>{esc(s["k"])}</td><td>{esc(s["v"])}</td></tr>' for s in specs)
    if p["medidas"]: info += f'<tr><td>Dimensões / medidas</td><td>{esc(p["medidas"])}</td></tr>'
    if p["cores"]: info += f'<tr><td>Cores</td><td>{esc(", ".join(p["cores"]))}</td></tr>'
    info += f'<tr><td>Embalagem coletiva</td><td>{esc(p["embalagem"])}</td></tr>'
    des = os.path.join(CAT, "desenhos", f'{p["codigo"]}.svg')
    desenho = f'<div><h3>Desenho técnico</h3><div class="des"><img src="{furl(des)}" alt="Desenho técnico"></div></div>' if os.path.exists(des) else ""
    vs = p["variacoes"]; por_col = max(4, math.ceil(len(vs) / 3)); tabelas = ""
    for i in range(0, len(vs), por_col):
        linhas = ""
        for v in vs[i:i + por_col]:
            hexc, nomec = cor_da(v["nome"], p["cores"]); sw = f'<span class="sw" style="background:{hexc}"></span>' if hexc else ""
            preco = f'<td class="preco">R$ {esc(precos.get(v["codigo"], "—"))}</td>' if precos else ""
            linhas += f'<tr><td class="c">{esc(v["codigo"])}</td><td>{sw}{esc(v["nome"] or p["nome"])}</td>{preco}</tr>'
        tabelas += f'<table class="cod"><thead><tr><th>Código</th><th>Cor / versão</th>{"<th>Preço</th>" if precos else ""}</tr></thead><tbody>{linhas}</tbody></table>'
    return f'''<section class="pag prod" id="p-{esc(p["codigo"])}">
<div class="cab"><span class="sub">{esc(subcat)}</span><span class="nome">{esc(p["nome"])}</span></div>
<div class="topo"><div><p class="desc">{esc(p["descricao"] or p["descricao_curta"])}</p><ul>{"".join(f"<li>{b}</li>" for b in bullets)}</ul><img class="selo" src="{furl(os.path.join(MARCA, "selo-industria-brasileira.svg"))}" alt="Indústria brasileira"></div><div class="fotos">{figs}</div></div>
<div class="meio{'' if desenho else ' so-info'}"><div><h3>Informações técnicas</h3><table class="info">{info}</table></div>{desenho}</div>
<div class="cods">{tabelas}</div>
<div class="rod"><span class="n">{n}</span><img src="{logo_h}"></div></section>'''

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--categorias"); ap.add_argument("--com-precos"); ap.add_argument("--saida"); a = ap.parse_args()
    cfg, cats, linhas, _ = gc.carregar()
    prods = [p for p in gc.montar_produtos(linhas, cats, cfg) if p["ativo"]]
    if a.categorias:
        ids = a.categorias.split(","); cats = [c for c in cats if c["id"] in ids]; prods = [p for p in prods if p["categoria"] in ids]
    precos = {r["codigo"].strip(): r["preco"].strip() for r in csv.DictReader(io.open(a.com_precos, encoding="utf-8-sig"), delimiter=";")} if a.com_precos else None
    ano = datetime.date.today().year
    fontes = io.open(gc.FONTES, encoding="utf-8").read()
    logo_neg = furl(os.path.join(MARCA, "logo-homelux-negativo.svg")); logo_h = furl(os.path.join(MARCA, "logo-homelux-horizontal.svg")); logo_v = furl(os.path.join(MARCA, "logo-homelux.svg"))
    titulo = ("Catálogo " + " · ".join(c["nome"] for c in cats)) if a.categorias and len(cats) <= 2 else "Catálogo técnico"
    pags = [f'<section class="pag capa">{fundo_capa()}<div class="tit">{esc(titulo)}<b>{ano}</b></div><div class="logo"><img src="{logo_neg}"></div></section>']
    pags.append(f'''<section class="pag"><div class="inst"><div></div><div><div class="faixa"></div>
<p>A <b>Homelux Soluções Elétricas</b> é uma indústria genuinamente brasileira, sediada em Blumenau, Santa Catarina, que há {cfg["anos"]} anos fabrica materiais elétricos e de iluminação para atender lojistas, distribuidores e consumidores que buscam qualidade, durabilidade e preço justo.</p>
<p>Com estrutura fabril própria e uma equipe comercial voltada ao atendimento do ponto de venda, a empresa oferece suporte da concepção do produto à exposição na gôndola: embalagens coletivas pensadas para revenda, códigos únicos por versão e um catálogo técnico completo, com fotos, especificações e desenho de cada família.</p>
<p>Nossa estrutura comercial atende lojas de material elétrico, de construção e distribuidores em todo o Brasil e na América Latina, com representantes por região e pedidos também pelo WhatsApp e pelo site.</p>
<p>Todos os produtos seguem as normas técnicas vigentes no país; os itens certificados trazem a indicação na ficha. Trabalhar com a Homelux é ter um mix completo, uma fábrica que responde e a segurança de {cfg["anos"]} anos de mercado.</p>
<p style="color:var(--cinza)">{esc(cfg["missao"])}</p><img src="{furl(os.path.join(MARCA, "selo-industria-brasileira.svg"))}" style="height:9mm;margin-top:2mm" alt="Indústria brasileira"><div class="logo"><img src="{logo_v}"></div></div></div><div class="rod"><span class="n">2</span><img src="{logo_h}"></div></section>''')
    ip_s = [("0", "Sem proteção"), ("1", "Corpos sólidos > 50 mm (contato das mãos)"), ("2", "Corpos sólidos > 12 mm (dedos)"), ("3", "Corpos sólidos > 2,5 mm (ferramentas)"), ("4", "Corpos sólidos > 1 mm (fios)"), ("5", "Protegido contra poeira"), ("6", "Totalmente protegido contra poeira")]
    ip_l = [("0", "Sem proteção"), ("1", "Gotas verticais (condensação)"), ("2", "Gotas até 15° da vertical"), ("3", "Chuva até 60° da vertical"), ("4", "Projeções de água em todas as direções"), ("5", "Jatos de água"), ("6", "Jatos fortes / ondas"), ("7", "Imersão temporária"), ("8", "Imersão prolongada")]
    tab = lambda L: "<table>" + "".join(f'<tr><td class="n">{n}</td><td>{esc(t)}</td></tr>' for n, t in L) + "</table>"
    pags.append(f'''<section class="pag tec"><h2>Informações técnicas</h2><p style="max-width:70ch;color:var(--cinza)">Como ler as fichas deste catálogo. Cada família traz especificações, dimensões de referência, embalagem coletiva e os códigos de cada cor ou versão — o código é o que vai no pedido.</p>
<div class="g2"><div><h3>Índice de proteção (IP) — sólidos</h3>{tab(ip_s)}</div><div><h3>Índice de proteção (IP) — líquidos</h3>{tab(ip_l)}</div></div>
<div class="g2" style="margin-top:6mm"><div><h3>Bases e soquetes</h3><p>{"".join(f'<span class="chip">{c}</span>' for c in ("E-27", "E-40", "G9", "Porcelana E-27", "Bivolt 127/220 V"))}</p><p>Luminárias e plafons Homelux usam soquete E-27 (padrão residencial) salvo indicação na ficha; refletores de alta potência trazem E-27/E-40. Não acompanham lâmpada.</p>
<h3>Materiais</h3><p><b>PVC</b> (caixas de inspeção certificadas), <b>PP / Nylon</b> (plafons, monoblock antivibratório), <b>policarbonato</b> (difusores cristal, parafusos e abraçadeiras), <b>alumínio</b> (spots, refletores, suportes), <b>aço zincado</b> (braços articulados), <b>porcelana</b> (soquetes).</p></div>
<div><h3>Como pedir</h3><p>Monte o pedido no site (<b>www.homeluxoficial.com.br/catalogo</b>: quantidade por código → carrinho → enviar pelo WhatsApp) ou fale com o representante da sua região. Embalagens são fechadas — a quantidade mínima é a embalagem coletiva indicada em cada ficha.</p>
<h3>Desenho técnico</h3><p>Vistas ortográficas com cotas em centímetros (tolerância ±3%). Itens flexíveis (cabos, extensões, passa-fio, varal) e famílias ainda sem medição de fábrica não trazem desenho; consulte o comercial para projetos.</p>
<h3>Garantia e normas</h3><p>Produtos fabricados conforme as normas técnicas vigentes; caixas de inspeção e aterramento certificadas. SAC {esc(" / ".join(cfg["telefones"]))} · {esc(cfg["email"])}.</p></div></div>
<div class="rod"><span class="n">3</span><img src="{logo_h}"></div></section>''')
    n = 4
    for i, c in enumerate(cats):
        fams = [p for p in prods if p["categoria"] == c["id"]]
        if not fams: continue
        pags.append(f'<section class="pag div">{fundo_capa(seed=11 + i, ondas=False)}<div class="txt"><div class="kick">Linha {i + 1:02d}</div><h1>{esc(c["nome"])}</h1><ul>{"".join(f"<li>{esc(p['nome'])} <span style=\'opacity:.6\'>· pág. {n + 1 + k}</span></li>" for k, p in enumerate(fams))}</ul></div></section>'); n += 1
        for p in fams: pags.append(pagina_produto(p, n, precos, logo_h)); n += 1
    pags.append(f'''<section class="pag contra"><img src="{logo_neg}" style="width:70mm"><p style="margin-top:6mm"><b style="color:#fff">{esc(cfg["razao_social"])}</b><br>{esc(cfg["endereco"])}</p><p>SAC {esc(" / ".join(cfg["telefones"]))} · {esc(cfg["email"])}</p><p>www.homeluxoficial.com.br · @{esc(cfg["instagram"])}</p><span class="wa">Pedidos pelo WhatsApp {esc(cfg["whatsapp_exibicao"])}</span><p style="font-size:7.5pt;margin-top:8mm;max-width:80ch">Catálogo técnico {ano}. Imagens ilustrativas; cotas de referência. Preços e condições sob consulta.{" Tabela de preços de uso exclusivo do lojista." if precos else ""}</p></section>''')
    doc = f'<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><title>{esc(titulo)} Homelux {ano}</title><style>{fontes}</style><style>{CSS}</style></head><body>{"".join(pags)}</body></html>'
    os.makedirs(os.path.join(CAT, "pdf"), exist_ok=True)
    nome = a.saida or os.path.join(CAT, "pdf", f"catalogo-tecnico-homelux-{ano}{'-' + gc.slug(a.categorias) if a.categorias else ''}{'-precos' if precos else ''}.pdf")
    html_path = os.path.splitext(nome)[0] + ".html"; io.open(html_path, "w", encoding="utf-8").write(doc)
    subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--no-first-run", "--hide-scrollbars", "--virtual-time-budget=60000", "--no-pdf-header-footer", f"--print-to-pdf={os.path.abspath(nome)}", furl(html_path)], check=True, capture_output=True, timeout=600)
    print("PDF:", nome, f"({os.path.getsize(nome) // 1024} KB, {len(pags)} páginas)")

if __name__ == "__main__":
    main()

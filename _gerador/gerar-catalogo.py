# -*- coding: utf-8 -*-
"""Gera o catálogo online e "carimba" o site a partir de catalogo/ (fonte de dados única).

Entradas:  catalogo/produtos.csv (UTF-8 BOM, ';') · catalogo/categorias.json · _gerador/config.json · catalogo/fotos/*.png|jpg
           (desde 07/09/2026 o catálogo é exportado do CRM: python site/_gerador/publicar.py baixa e gera; o CSV não se edita à mão)
           marca/*.svg + marca/*.png (logos, favicons, og-image)
Saídas:    site/catalogo/catalogo.json · site/catalogo/p/<codigo>-<slug>.html · site/catalogo/fotos/* (webp + jpg + thumb)
           site/sitemap.xml · site/assets/{logos, favicons, og-image} · catalogo/relatorio.md
           + em TODAS as páginas escritas à mão de site/: blocos <!-- @head -->, <!-- @topo -->, <!-- @rodape --> e os
             atributos data-wa/data-wa-msgs do <body> (config.json em um lugar só).

Uso:  python ferramentas/gerar-catalogo.py [--so-json] [--forcar-fotos]
Falha ruidosamente (exit 1) se: código duplicado, categoria inexistente, foto referenciada ausente, campo obrigatório vazio.
"""
import argparse, csv, datetime, html, io, json, os, re, shutil, sys, unicodedata
import sys
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass
from PIL import Image

# Onde as coisas estão. Este arquivo vive em site/_gerador/. Dois arranjos:
#  · estúdio (pasta Homelux/): RAIZ = ../.. → catalogo/, marca/, site/, fonts-inline.css
#  · GitHub Action (só o repositório do site): publicar.py baixa o catálogo do CRM em _gerador/_trabalho/ e aponta as variáveis
GERADOR = os.path.dirname(os.path.abspath(__file__))
_estudio = os.path.dirname(os.path.dirname(GERADOR))
RAIZ = os.environ.get("HOMELUX_RAIZ") or (_estudio if os.path.exists(os.path.join(_estudio, "catalogo", "produtos.csv")) else os.path.join(GERADOR, "_trabalho"))
CAT = os.environ.get("HOMELUX_CATALOGO") or os.path.join(RAIZ, "catalogo")
SITE = os.environ.get("HOMELUX_SITE") or os.path.dirname(GERADOR)
MARCA = os.environ.get("HOMELUX_MARCA") or (os.path.join(RAIZ, "marca") if os.path.isdir(os.path.join(RAIZ, "marca")) else os.path.join(SITE, "assets"))
TPL = os.path.join(GERADOR, "templates")
CONFIG = os.path.join(GERADOR, "config.json")
FONTES = os.path.join(RAIZ, "fonts-inline.css") if os.path.exists(os.path.join(RAIZ, "fonts-inline.css")) else os.path.join(GERADOR, "fonts-inline.css")
CHROME = os.environ.get("CHROME") or next((c for c in [r"C:\Program Files\Google\Chrome\Application\chrome.exe", "/usr/bin/google-chrome", "/usr/bin/google-chrome-stable", "/usr/bin/chromium-browser", "/usr/bin/chromium"] if os.path.exists(c)), "google-chrome")
OBRIGATORIOS = ["codigo", "nome", "categoria", "descricao_curta", "variacoes", "embalagem"]
PAGINAS_FIXAS = ["index.html", "promocoes.html", "sobre.html", "onde-comprar.html", "contato.html", "pedido.html", "catalogo/index.html", "links/index.html"]

def esc(s): return html.escape(str(s or ""), quote=True)
def slug(s):
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s).strip("-").lower()
    return re.sub(r"-{2,}", "-", s)
def norm(s): return unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower()
def rd(p): return io.open(p, encoding="utf-8").read()
def wr(p, t):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    io.open(p, "w", encoding="utf-8", newline="\n").write(t)

def carregar():
    cfg = json.load(io.open(CONFIG, encoding="utf-8"))
    cats = json.load(io.open(os.path.join(CAT, "categorias.json"), encoding="utf-8"))
    cats.sort(key=lambda c: c["ordem"])
    linhas = list(csv.DictReader(io.open(os.path.join(CAT, "produtos.csv"), encoding="utf-8-sig"), delimiter=";"))
    erros = []
    vistos = set()
    ids_cat = {c["id"] for c in cats}
    for i, l in enumerate(linhas, 2):
        if None in l: erros.append(f"linha {i}: campos a mais (';' dentro de texto?)")
        for k in OBRIGATORIOS:
            if not (l.get(k) or "").strip(): erros.append(f"linha {i} ({l.get('codigo')}): campo obrigatório vazio: {k}")
        c = l["codigo"].strip()
        if c in vistos: erros.append(f"linha {i}: código duplicado: {c}")
        vistos.add(c)
        if l["categoria"] not in ids_cat: erros.append(f"linha {i} ({c}): categoria inexistente: {l['categoria']}")
        for f in [x.strip() for x in l["fotos"].split(",") if x.strip()]:
            if not os.path.exists(os.path.join(CAT, "fotos", f)): erros.append(f"linha {i} ({c}): foto não encontrada: {f}")
    # códigos de variação duplicados entre famílias = aviso (o catálogo 2025 tem 12711/12712 em duas famílias)
    avisos = []
    vcod = {}
    for l in linhas:
        for v in parse_variacoes(l["variacoes"]):
            vcod.setdefault(v["codigo"], []).append(l["codigo"])
    for k, fams in vcod.items():
        if len(fams) > 1: avisos.append(f"código de variação {k} aparece em {fams} — confirmar com a Homelux")
    if erros:
        print("ERROS — nada foi gerado:\n  " + "\n  ".join(erros)); sys.exit(1)
    return cfg, cats, linhas, avisos

def parse_variacoes(s):
    out = []
    for item in [x.strip() for x in (s or "").split("|") if x.strip()]:
        if "=" in item:
            c, n = item.split("=", 1); out.append({"codigo": c.strip(), "nome": n.strip()})
        else:
            out.append({"codigo": item, "nome": ""})
    return out

def parse_specs(s):
    out = []
    for item in [x.strip() for x in (s or "").split("|") if x.strip()]:
        if "=" in item:
            k, v = item.split("=", 1); out.append({"k": k.strip(), "v": v.strip()})
    return out

def processar_fotos(linhas, forcar=False):
    dst = os.path.join(SITE, "catalogo", "fotos"); os.makedirs(dst, exist_ok=True)
    total = 0
    for l in linhas:
        for f in [x.strip() for x in l["fotos"].split(",") if x.strip()]:
            src = os.path.join(CAT, "fotos", f)
            base = os.path.splitext(f)[0]
            alvos = {"webp": os.path.join(dst, base + ".webp"), "jpg": os.path.join(dst, base + ".jpg"), "thumb": os.path.join(dst, base + "-thumb.webp")}
            if not forcar and all(os.path.exists(a) and os.path.getmtime(a) >= os.path.getmtime(src) for a in alvos.values()):
                continue
            im = Image.open(src)
            if im.mode in ("RGBA", "LA", "P"):
                im = im.convert("RGBA"); fundo = Image.new("RGB", im.size, (255, 255, 255)); fundo.paste(im, mask=im.split()[-1]); im = fundo
            else:
                im = im.convert("RGB")
            g = im.copy(); g.thumbnail((1200, 1200)); g.save(alvos["webp"], "WEBP", quality=84); g.save(alvos["jpg"], "JPEG", quality=86, optimize=True)
            t = im.copy(); t.thumbnail((480, 480)); t.save(alvos["thumb"], "WEBP", quality=80)
            total += 1
    return total

def montar_produtos(linhas, cats, cfg):
    nome_cat = {c["id"]: c["nome"] for c in cats}
    prods = []
    for l in linhas:
        cod = l["codigo"].strip()
        s = f"{cod}-{slug(l['nome'])}"
        fotos = []
        for f in [x.strip() for x in l["fotos"].split(",") if x.strip()]:
            base = os.path.splitext(f)[0]
            fotos.append({"src": f"fotos/{base}.webp", "jpg": f"fotos/{base}.jpg", "thumb": f"fotos/{base}-thumb.webp", "alt": f"{l['nome']} — Homelux"})
        vari = parse_variacoes(l["variacoes"])
        specs = parse_specs(l["especificacoes"])
        busca = " ".join([cod, l["nome"], l["descricao_curta"], nome_cat.get(l["categoria"], ""), l.get("subcategoria", ""), l.get("tags", ""), l.get("cores", "")] + [v["codigo"] + " " + v["nome"] for v in vari])
        desenho = ""
        for ext in ("png", "jpg", "webp", "pdf", "svg"):
            if os.path.exists(os.path.join(CAT, "desenhos", f"{cod}.{ext}")): desenho = f"desenhos/{cod}.{ext}"; break
        prods.append({
            "desenho": desenho,
            "codigo": cod, "slug": s, "url": f"p/{s}.html", "nome": l["nome"].strip(), "categoria": l["categoria"], "categoria_nome": nome_cat.get(l["categoria"], ""),
            "subcategoria": l.get("subcategoria", ""), "descricao_curta": l["descricao_curta"].strip(), "descricao": l["descricao"].strip(),
            "especificacoes": specs, "medidas": l.get("medidas", ""), "cores": [c.strip() for c in l.get("cores", "").split(",") if c.strip()],
            "variacoes": vari, "unidade": l.get("unidade", ""), "embalagem": l["embalagem"].strip(), "fotos": fotos,
            "destaque": l.get("destaque", "0") == "1", "ativo": l.get("ativo", "1") == "1", "provisorio": l.get("provisorio", "0") == "1",
            "tags": [t.strip() for t in l.get("tags", "").split(",") if t.strip()], "busca": norm(busca),
        })
    return prods

def bloco_head(cfg, raiz, titulo, descricao, canonical, og_image=None, extra=""):
    return f"""<!-- @head -->
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(titulo)}</title>
<meta name="description" content="{esc(descricao)}">
<link rel="canonical" href="{esc(canonical)}">
<meta property="og:type" content="website"><meta property="og:site_name" content="Homelux Soluções Elétricas"><meta property="og:locale" content="pt_BR">
<meta property="og:title" content="{esc(titulo)}"><meta property="og:description" content="{esc(descricao)}"><meta property="og:url" content="{esc(canonical)}">
<meta property="og:image" content="{esc(og_image or cfg['site'] + '/assets/og-image-1200x630.png')}"><meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="{raiz}assets/favicon.svg" type="image/svg+xml"><link rel="icon" href="{raiz}assets/favicon-32.png" sizes="32x32"><link rel="apple-touch-icon" href="{raiz}assets/favicon-180.png">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Sora:wght@400;600;700&family=Manrope:wght@400;500;700&display=swap">
<link rel="stylesheet" href="{raiz}assets/styles.css">
<meta name="theme-color" content="#1B2A5B">{extra}
<!-- /@head -->"""

SUBS_PRESENTES = {}   # preenchido em main(): categoria -> [subcategorias com produto ativo]

def menu_produtos(cats, raiz):
    cols = []
    for c in cats:
        subs = c.get("subcategorias", {})
        itens = "".join(f'<li><a href="{raiz}catalogo/index.html?cat={c["id"]}&amp;sub={s}">{esc(subs.get(s, s.replace("-", " ").capitalize()))}</a></li>'
                        for s in SUBS_PRESENTES.get(c["id"], []))
        cols.append(f'<div class="mega-col"><a class="mega-titulo" href="{raiz}catalogo/index.html?cat={c["id"]}">{esc(c["nome"])}</a><ul>{itens}</ul></div>')
    return "".join(cols)

def bloco_topo(cfg, raiz, atual, cats=None):
    t = rd(os.path.join(TPL, "topo.html")).replace("{{raiz}}", raiz)
    t = t.replace("{{menu_produtos}}", menu_produtos(cats or [], raiz))
    return re.sub(r"\{\{atual:([\w-]+)\}\}", lambda m: ' aria-current="page"' if m.group(1) == atual else "", t)

def bloco_rodape(cfg, cats, raiz):
    t = rd(os.path.join(TPL, "rodape.html"))
    links_cat = "".join(f'<li><a href="{raiz}catalogo/index.html?cat={c["id"]}">{esc(c["nome"])}</a></li>' for c in cats)
    tel = "".join(f'<li><a href="tel:{re.sub(r"[^0-9+]", "", "+55" + t)}">{esc(t)}</a></li>' for t in cfg["telefones"])
    for k, v in {"raiz": raiz, "razao_social": esc(cfg["razao_social"]), "endereco": esc(cfg["endereco"]), "anos": cfg["anos"],
                 "links_categorias": links_cat, "links_telefones": tel, "whatsapp_exibicao": esc(cfg["whatsapp_exibicao"]),
                 "email": esc(cfg["email"]), "instagram": esc(cfg["instagram"]), "ano": datetime.date.today().year}.items():
        t = t.replace("{{" + k + "}}", str(v))
    return t

def body_attrs(cfg, pagina, raiz="", classe=""):
    msgs = esc(json.dumps(cfg["mensagens_whatsapp"], ensure_ascii=False))
    cls = f' class="{esc(classe)}"' if classe else ""
    crm = f' data-crm="{esc(cfg.get("crm_pedidos_url", ""))}"' if cfg.get("crm_pedidos_url") else ""
    return f'<body data-pagina="{esc(pagina)}"{cls} data-raiz="{raiz}" data-wa="{esc(cfg["whatsapp"])}"{crm} data-wa-msgs="{msgs}">'

def carimbar_pagina(caminho, cfg, cats):
    """Substitui os blocos @head/@topo/@rodape e o <body> de uma página escrita à mão."""
    t = rd(caminho)
    rel = os.path.relpath(caminho, SITE).replace("\\", "/")
    raiz = "../" * (rel.count("/"))
    m = re.search(r'<body[^>]*data-pagina="([\w-]+)"[^>]*>', t)
    pagina = m.group(1) if m else slug(os.path.splitext(os.path.basename(caminho))[0])
    # metadados da própria página vêm de um comentário <!-- meta: {...} -->
    mm = re.search(r"<!-- meta: (\{.*?\}) -->", t, flags=re.S)
    meta = json.loads(mm.group(1)) if mm else {}
    titulo = meta.get("titulo", "Homelux Soluções Elétricas")
    desc = meta.get("descricao", "Materiais elétricos e iluminação fabricados em Blumenau/SC há 40 anos.")
    canonical = cfg["site"] + "/" + ("" if rel == "index.html" else rel.replace("index.html", ""))
    t = re.sub(r"<!-- @head -->.*?<!-- /@head -->", lambda _: bloco_head(cfg, raiz, titulo, desc, canonical, extra=meta.get("head_extra", "")), t, flags=re.S)
    t = re.sub(r"<!-- @topo(?: [^>]*)?-->.*?<!-- /@topo -->", lambda _: bloco_topo(cfg, raiz, pagina, cats), t, flags=re.S)
    t = re.sub(r"<!-- @rodape(?: [^>]*)?-->.*?<!-- /@rodape -->", lambda _: bloco_rodape(cfg, cats, raiz), t, flags=re.S)
    mc = re.search(r'<body[^>]*\sclass="([^"]*)"', t)
    t = re.sub(r"<body[^>]*>", lambda _: body_attrs(cfg, pagina, raiz, mc.group(1) if mc else ""), t, count=1)
    wr(caminho, t)
    return rel

def pagina_produto(p, prods, cfg, cats):
    tpl = rd(os.path.join(TPL, "produto.html"))
    raiz = "../../"
    url = f"{cfg['site']}/catalogo/{p['url']}"
    titulo = f"{p['nome']} — cód. {p['codigo']} · Homelux"
    desc = (p["descricao_curta"] + f" Embalagem: {p['embalagem']}. Fabricado pela Homelux em Blumenau/SC.")[:158]
    og = f"{cfg['site']}/catalogo/{p['fotos'][0]['jpg']}" if p["fotos"] else None
    galeria_principal = (f'<img src="../{p["fotos"][0]["src"]}" alt="{esc(p["fotos"][0]["alt"])}" width="800" height="800">' if p["fotos"]
                         else '<img src="../../assets/simbolo-homelux.svg" alt="" width="200" height="200" style="opacity:.25">')
    minis = "".join(f'<button type="button" aria-pressed="{"true" if i == 0 else "false"}" data-src="../{f["src"]}" aria-label="Foto {i+1}"><img src="../{f["thumb"]}" alt="{esc(f["alt"])}" loading="lazy" width="72" height="72"></button>' for i, f in enumerate(p["fotos"]))
    minis = f'<div class="miniaturas">{minis}</div>' if len(p["fotos"]) > 1 else ""
    linhas_var = "".join(f'<tr data-codigo="{esc(v["codigo"])}" data-nome="{esc(v["nome"]) or esc(p["nome"])}"><td class="cod">{esc(v["codigo"])}</td><td>{esc(v["nome"]) or esc(p["nome"])}</td><td class="qtd"><div class="qtd-ctl"><button type="button" data-mais="-1" aria-label="Menos">−</button><input type="number" min="0" step="1" inputmode="numeric" placeholder="0" aria-label="Quantidade do código {esc(v["codigo"])}"><button type="button" data-mais="1" aria-label="Mais">+</button></div></td></tr>' for v in p["variacoes"])
    tabela_var = f'<div class="tabela-wrap"><table class="var"><thead><tr><th scope="col">Código</th><th scope="col">Versão</th><th scope="col">Qtd.</th></tr></thead><tbody>{linhas_var}</tbody></table></div>'
    specs = list(p["especificacoes"])
    if p["medidas"]: specs.append({"k": "Medidas", "v": p["medidas"]})
    if p["cores"]: specs.append({"k": "Cores", "v": ", ".join(p["cores"])})
    specs.append({"k": "Embalagem", "v": p["embalagem"]})
    tabela_specs = '<div class="tabela-wrap"><table class="specs"><tbody>' + "".join(f"<tr><td>{esc(s['k'])}</td><td>{esc(s['v'])}</td></tr>" for s in specs) + "</tbody></table></div>"
    relacionados = [q for q in prods if q["ativo"] and q["categoria"] == p["categoria"] and q["codigo"] != p["codigo"]][:4]
    rel_html = "".join(
        f'<a class="prod" href="{esc(q["slug"])}.html"><figure>' + (f'<img src="../{q["fotos"][0]["thumb"]}" alt="{esc(q["fotos"][0]["alt"])}" loading="lazy" width="480" height="360">' if q["fotos"] else "") +
        f'</figure><div class="info"><span class="cat">{esc(q["categoria_nome"])}</span><b>{esc(q["nome"])}</b><span class="cod">cód. {esc(q["codigo"])}</span></div></a>' for q in relacionados)
    json_ld = {
        "@context": "https://schema.org", "@graph": [
            {"@type": "Product", "name": p["nome"], "sku": p["codigo"], "description": p["descricao"] or p["descricao_curta"],
             "brand": {"@type": "Brand", "name": "Homelux"}, "manufacturer": {"@type": "Organization", "name": cfg["razao_social"]},
             "image": [f"{cfg['site']}/catalogo/{f['jpg']}" for f in p["fotos"]], "url": url, "category": p["categoria_nome"]},
            {"@type": "BreadcrumbList", "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "Início", "item": cfg["site"] + "/"},
                {"@type": "ListItem", "position": 2, "name": "Catálogo", "item": cfg["site"] + "/catalogo/"},
                {"@type": "ListItem", "position": 3, "name": p["categoria_nome"], "item": f"{cfg['site']}/catalogo/?cat={p['categoria']}"},
                {"@type": "ListItem", "position": 4, "name": p["nome"], "item": url}]}]}
    head_extra = f'\n<script type="application/ld+json">{json.dumps(json_ld, ensure_ascii=False)}</script>'
    subs = {
        "head": bloco_head(cfg, raiz, titulo, desc, url, og, head_extra), "topo": bloco_topo(cfg, raiz, "catalogo", cats), "rodape": bloco_rodape(cfg, cats, raiz),
        "body": body_attrs(cfg, "produto", raiz), "raiz": raiz, "nome": esc(p["nome"]), "codigo": esc(p["codigo"]), "categoria_id": esc(p["categoria"]),
        "categoria_nome": esc(p["categoria_nome"]), "descricao_curta": esc(p["descricao_curta"]), "descricao": esc(p["descricao"] or p["descricao_curta"]),
        "galeria_principal": galeria_principal, "miniaturas": minis, "tabela_variacoes": tabela_var, "tabela_specs": tabela_specs,
        "embalagem": esc(p["embalagem"]), "n_variacoes": str(len(p["variacoes"])), "relacionados": rel_html,
        "selo_prov": '<span class="selo-prov">foto provisória</span>' if p["provisorio"] else "",
        "desenho": (('<h2>Desenho técnico</h2><figure class="desenho"><img src="../' + esc(p["desenho"]) + '" alt="Desenho técnico ' + esc(p["nome"]) + '" loading="lazy"></figure><p><a class="link-seta" href="../' + esc(p["desenho"]) + '" download>Baixar desenho técnico</a></p>')
                    if p["desenho"] and not p["desenho"].endswith(".pdf") else
                    ('<h2>Desenho técnico</h2><p><a class="link-seta" href="../' + esc(p["desenho"]) + '" download>Baixar desenho técnico (PDF)</a></p>' if p["desenho"] else "")),
        "wa_nome": esc(p["nome"]), "wa_codigo": esc(p["codigo"]),
        "bloco_relacionados": "" if not relacionados else None,
    }
    t = tpl
    for k, v in subs.items():
        if v is None: continue
        t = t.replace("{{" + k + "}}", v)
    if not relacionados:
        t = re.sub(r"<!-- @relacionados -->.*?<!-- /@relacionados -->", "", t, flags=re.S)
    return t

def carregar_promocao():
    p = os.path.join(CAT, "promocao.json")
    if not os.path.exists(p): return None
    try: d = json.load(io.open(p, encoding="utf-8"))
    except Exception: return None
    return d if d and d.get("itens") else None

def _qtd_html(cod):
    return f'<td class="qtd"><div class="qtd-ctl"><button type="button" data-mais="-1" aria-label="Menos">−</button><input type="number" min="0" step="1" inputmode="numeric" placeholder="0" aria-label="Quantidade do código {esc(cod)}"><button type="button" data-mais="1" aria-label="Mais">+</button></div></td>'

def html_promocao(promo, prods, cfg):
    """Devolve (slide_home, corpo_pagina, meta_pagina, mensagem_whatsapp). Sem promoção: slide vazio e página 'sem promoção'."""
    if not promo:
        corpo = ('<section class="promo-hero"><div class="wrap"><span class="tag-promo">Promoções</span><h1>Nenhuma promoção ativa no momento</h1>'
                 '<p class="lead">Acompanhe nossas redes e o WhatsApp comercial: a próxima campanha aparece aqui. Enquanto isso, o catálogo completo está sempre atualizado.</p>'
                 '<p><a class="btn" href="catalogo/index.html">Ver o catálogo</a></p></div></section>')
        return "", corpo, {"titulo": "Promoções — Homelux", "descricao": "Promoções da Homelux para lojistas, distribuidores e consumidores."}, cfg["mensagens_whatsapp"].get("promo", cfg["mensagens_whatsapp"]["geral"])
    por_cod = {p["codigo"]: p for p in prods}
    titulo = f'{promo.get("titulo", "").strip()} {promo.get("destaque", "").strip()}'.strip()
    periodo = (promo.get("periodo") or "").strip()
    tag = f'Promoção · {periodo.lower()}' if periodo else (promo.get("tag") or "Promoção")
    sub = (promo.get("subtitulo") or "").strip().rstrip(".")
    cond = (promo.get("condicao") or "").strip()
    itens = promo["itens"][:4]
    nomes = [i["nome"] for i in itens]
    lista_nomes = ", ".join(nomes[:-1]) + (" e " + nomes[-1] if len(nomes) > 1 else nomes[0]) if nomes else ""
    # slide da home (até 3 fotos)
    fotos = [os.path.splitext(i["foto"])[0] for i in itens if i.get("foto")][:3]
    imgs = "".join(f'<img class="p{n + 1}" src="catalogo/fotos/{esc(f)}.webp" alt="" width="600" height="600" loading="eager">' for n, f in enumerate(fotos))
    slide = (f'<div class="wrap slide-in"><div class="texto"><span class="tag-promo">{esc(tag)}</span><h1>{esc(titulo)}{": " + esc(sub) if sub else ""}</h1>'
             f'<p>{esc(lista_nomes)}{", com condição especial para lojista e distribuidor" if lista_nomes else ""}{(" · " + esc(periodo)) if periodo else ""}.</p>'
             f'<div class="acoes"><a class="btn" href="promocoes.html">Ver a promoção</a><a class="btn wa" href="#" data-wa-msg="promo">Pedir condições no WhatsApp</a></div></div>'
             f'<div class="produtos" aria-hidden="true">{imgs}</div></div>')
    # página
    cards = ""
    for i in itens:
        p = por_cod.get(i["codigo"]); foto = os.path.splitext(i["foto"])[0] if i.get("foto") else ""
        img = f'<img src="catalogo/fotos/{esc(foto)}.webp" alt="{esc(i["nome"])}" width="600" height="600" loading="lazy">' if foto else ""
        link = f'catalogo/p/{p["slug"]}.html' if p else "catalogo/index.html"
        emb = p["embalagem"] if p else ""
        vari = p["variacoes"] if p and p["variacoes"] else [{"codigo": i["codigo"], "nome": ""}]
        linhas = "".join(f'<tr data-codigo="{esc(v["codigo"])}" data-nome="{esc((i["nome"] + (" " + v["nome"] if v["nome"] else "") + (" (emb. " + emb + ")" if emb else "")).strip())}"><td class="cod">{esc(v["codigo"])}</td><td>{esc(v["nome"] or i["nome"])}</td>{_qtd_html(v["codigo"])}</tr>' for v in vari[:12])
        cards += (f'<article class="promo-card"><a href="{link}">{img}</a><h2>{esc(i["nome"])}</h2><p class="secundario">{esc(i.get("detalhe", ""))}</p>'
                  f'<table class="var variacoes"><tbody>{linhas}</tbody></table></article>')
    corpo = (f'<section class="promo-hero"><div class="wrap"><span class="tag-promo">{esc(tag)}</span><h1>{esc(titulo)}</h1>'
             f'<p class="lead">{esc(sub) + ". " if sub else ""}Escolha as quantidades, adicione ao pedido e envie pelo WhatsApp: o comercial responde com tabela e prazo.</p>'
             f'{("<p class=" + chr(34) + "aviso-claro" + chr(34) + ">" + esc(cond) + "</p>") if cond else ""}</div></section>'
             f'<section class="promo-itens"><div class="wrap"><form class="form-pedido" data-familia="{esc(titulo)}" data-embalagem="ver item"><div class="promo-grade">{cards}</div>'
             f'<div class="form-pedido-acoes promo-acoes"><button class="btn" type="submit">Adicionar ao pedido</button><a class="link-seta" href="pedido.html">Ver pedido (<span class="pedido-badge" hidden>0</span>)</a><a class="btn wa" href="#" data-wa-msg="promo">Pedir condições pelo WhatsApp</a></div></form></div></section>'
             f'<section class="cta"><div class="wrap cta-in"><div><span class="kicker">Também para o consumidor</span><h2>Encontrou o que precisa? Fale com a gente</h2><p>Consumidor final compra nas lojas parceiras ou pelo WhatsApp comercial. Lojista recebe a tabela na hora.</p></div><a class="btn wa" href="#" data-wa-msg="promo">Falar com o comercial</a></div></section>')
    meta = {"titulo": f"{titulo} — promoção Homelux para lojistas e distribuidores", "descricao": f"{lista_nomes} com condição especial de fábrica{(' em ' + periodo.lower()) if periodo else ''}. Monte o pedido e envie pelo WhatsApp."}
    msg = f"Olá! Vi a promoção {titulo} no site da Homelux e quero as condições dos itens ({lista_nomes}). Sou: ( ) lojista/distribuidor ( ) consumidor."
    return slide, corpo, meta, msg

def aplicar_promocao(promo, prods, cfg):
    """Escreve o slide (index.html) e a página (promocoes.html) entre os marcadores @promo-slide / @promo; devolve a mensagem de WhatsApp."""
    slide, corpo, meta, msg = html_promocao(promo, prods, cfg)
    idx = os.path.join(SITE, "index.html")
    if os.path.exists(idx):
        t = rd(idx)
        novo = (f'<article class="slide ativo slide-promo" data-slide="promo">{slide}</article>' if slide else "")
        t2 = re.sub(r"<!-- @promo-slide -->.*?<!-- /@promo-slide -->", lambda _: f"<!-- @promo-slide -->\n      {novo}\n      <!-- /@promo-slide -->", t, flags=re.S)
        if t2 != t: wr(idx, t2)
    pg = os.path.join(SITE, "promocoes.html")
    if os.path.exists(pg):
        t = rd(pg)
        t2 = re.sub(r"<!-- @promo -->.*?<!-- /@promo -->", lambda _: f"<!-- @promo -->\n{corpo}\n<!-- /@promo -->", t, flags=re.S)
        t2 = re.sub(r"<!-- meta: \{.*?\} -->", lambda _: "<!-- meta: " + json.dumps(meta, ensure_ascii=False) + " -->", t2, count=1, flags=re.S)
        if t2 != t: wr(pg, t2)
    return msg

def sitemap(cfg, prods, paginas):
    hoje = datetime.date.today().isoformat()
    urls = [cfg["site"] + "/" + ("" if p == "index.html" else p.replace("index.html", "")) for p in paginas]
    urls += [f"{cfg['site']}/catalogo/{p['url']}" for p in prods if p["ativo"]]
    itens = "".join(f"<url><loc>{esc(u)}</loc><lastmod>{hoje}</lastmod></url>" for u in urls)
    return f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{itens}</urlset>\n'

def copiar_desenhos():
    src = os.path.join(CAT, "desenhos"); dst = os.path.join(SITE, "catalogo", "desenhos")
    if os.path.isdir(dst): shutil.rmtree(dst)
    os.makedirs(dst, exist_ok=True)
    n = 0
    for f in os.listdir(src) if os.path.isdir(src) else []:
        if f.lower().endswith((".png", ".jpg", ".webp", ".pdf", ".svg")): shutil.copy(os.path.join(src, f), os.path.join(dst, f)); n += 1
    return n

def copiar_catalogo_crm():
    """Cópia do catalogo.json para o CRM (fallback do seletor de itens quando o site estiver fora)."""
    dst = os.path.join(RAIZ, "crm", "public")
    if os.path.isdir(dst): shutil.copy(os.path.join(SITE, "catalogo", "catalogo.json"), os.path.join(dst, "catalogo.json"))

def limpar_fotos_orfas(linhas):
    """Remove de site/catalogo/fotos o que não pertence mais a nenhum produto."""
    dst = os.path.join(SITE, "catalogo", "fotos")
    if not os.path.isdir(dst): return 0
    bases = {os.path.splitext(f.strip())[0] for l in linhas for f in l["fotos"].split(",") if f.strip()}
    n = 0
    for f in os.listdir(dst):
        base = re.sub(r"-thumb$", "", os.path.splitext(f)[0])
        if base not in bases: os.remove(os.path.join(dst, f)); n += 1
    return n

def copiar_marca():
    dst = os.path.join(SITE, "assets"); os.makedirs(dst, exist_ok=True)
    if os.path.abspath(MARCA) == os.path.abspath(dst): return
    for f in ["logo-homelux.svg", "logo-homelux-horizontal.svg", "logo-homelux-negativo.svg", "logo-homelux-horizontal-negativo.svg", "logo-homelux-vertical-negativo.svg", "logo-homelux-mono.svg", "logo-homelux-animada.svg", "simbolo-homelux.svg", "simbolo-homelux-negativo.svg",
              "selo-industria-brasileira.svg", "favicon.svg", "favicon-32.png", "favicon-180.png", "favicon-512.png", "og-image-1200x630.png"]:
        src = os.path.join(MARCA, f)
        if os.path.exists(src): shutil.copy(src, os.path.join(dst, f))
    for f in ["qr-site.svg", "qr-whatsapp.svg", "qr-catalogo.svg"]:   # QRs (marca/qr/) usados nos PDFs
        src = os.path.join(MARCA, "qr", f)
        if os.path.exists(src): shutil.copy(src, os.path.join(dst, f))

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--so-json", action="store_true", help="não reprocessa fotos nem páginas de produto")
    ap.add_argument("--forcar-fotos", action="store_true")
    a = ap.parse_args()
    cfg, cats, linhas, avisos = carregar()
    prods = montar_produtos(linhas, cats, cfg)
    for c in cats:
        vistos = []
        for p in prods:
            if p["ativo"] and p["categoria"] == c["id"] and p["subcategoria"] and p["subcategoria"] not in vistos: vistos.append(p["subcategoria"])
        SUBS_PRESENTES[c["id"]] = vistos
    promo = carregar_promocao(); cfg["mensagens_whatsapp"]["promo"] = aplicar_promocao(promo, prods, cfg)   # promoção do CRM → slide, página e mensagem
    n_fotos = 0 if a.so_json else processar_fotos(linhas, a.forcar_fotos)
    copiar_marca(); copiar_desenhos(); copiar_catalogo_crm(); orfas = limpar_fotos_orfas(linhas)
    saida = {"gerado_em": datetime.datetime.now().isoformat(timespec="seconds"), "whatsapp": cfg["whatsapp"],
             "categorias": [{"id": c["id"], "nome": c["nome"], "descricao": c.get("descricao", ""), "subcategorias": c.get("subcategorias", {})} for c in cats],
             "produtos": [{k: v for k, v in p.items() if k not in ("descricao",)} for p in prods]}
    wr(os.path.join(SITE, "catalogo", "catalogo.json"), json.dumps(saida, ensure_ascii=False, separators=(",", ":")))
    # páginas de produto (remove órfãs)
    pdir = os.path.join(SITE, "catalogo", "p"); os.makedirs(pdir, exist_ok=True)
    esperadas = set()
    if not a.so_json:
        for p in prods:
            if not p["ativo"]: continue
            wr(os.path.join(pdir, p["slug"] + ".html"), pagina_produto(p, prods, cfg, cats)); esperadas.add(p["slug"] + ".html")
        for f in os.listdir(pdir):
            if f.endswith(".html") and f not in esperadas: os.remove(os.path.join(pdir, f))
    # carimbo das páginas fixas
    carimbadas = [carimbar_pagina(os.path.join(SITE, p), cfg, cats) for p in PAGINAS_FIXAS if os.path.exists(os.path.join(SITE, p))]
    wr(os.path.join(SITE, "sitemap.xml"), sitemap(cfg, prods, carimbadas))
    # relatório
    ativos = [p for p in prods if p["ativo"]]
    rel = [f"# Relatório do catálogo — {saida['gerado_em']}", "",
           f"- Famílias: {len(prods)} ({len(ativos)} ativas) · variações/SKUs: {sum(len(p['variacoes']) for p in prods)}",
           f"- Fotos processadas nesta rodada: {n_fotos} · famílias sem foto: {[p['codigo'] for p in prods if not p['fotos']] or 'nenhuma'}",
           f"- Provisórias (foto de terceiro ou sem código oficial): {[p['codigo'] for p in prods if p['provisorio']] or 'nenhuma'}",
           f"- Destaques: {[p['codigo'] for p in prods if p['destaque']]}", "",
           "## Por categoria", ""] + [f"- {c['nome']}: {sum(1 for p in ativos if p['categoria'] == c['id'])}" for c in cats]
    if avisos: rel += ["", "## Avisos", ""] + [f"- {x}" for x in avisos]
    wr(os.path.join(CAT, "relatorio.md"), "\n".join(rel) + "\n")
    print(f"OK: {len(ativos)} produtos ativos, {len(esperadas)} páginas, {n_fotos} fotos processadas, {orfas} fotos órfãs removidas, {len(carimbadas)} páginas carimbadas")
    for x in avisos: print("AVISO:", x)
    if cfg["whatsapp"].endswith("999999999"): print("AVISO: WhatsApp em catalogo/config.json ainda é PLACEHOLDER (GATE B)")

if __name__ == "__main__":
    main()

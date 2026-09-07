# -*- coding: utf-8 -*-
"""Publica o site a partir do CRM: baixa o catálogo (CSV, categorias, fotos, desenhos) da rota /api/catalogo/exportar,
gera páginas/fotos/sitemap (gerar-catalogo.py) e os dois PDFs, e avisa o CRM (/api/catalogo/publicado) entregando os PDFs.

Uso:
  python site/_gerador/publicar.py                 # tudo (no GitHub Action; no estúdio também funciona)
  python site/_gerador/publicar.py --so-baixar     # só atualiza catalogo/ local a partir do CRM (depois rode os geradores de sempre)
  python site/_gerador/publicar.py --sem-pdf       # não gera PDFs (mais rápido)
Ambiente: CRM_URL (padrão https://crm.homeluxoficial.com.br) · CATALOGO_TOKEN (obrigatório) · PUBLICACAO_ID (opcional, vem do CRM).
No estúdio, lê CATALOGO_TOKEN de crm/.env.local se a variável não existir.
"""
import argparse, io, json, os, subprocess, sys, time, urllib.request, urllib.error, uuid
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass
G = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.dirname(G)
ESTUDIO = os.path.dirname(SITE)
NO_ESTUDIO = os.path.exists(os.path.join(ESTUDIO, "catalogo", "produtos.csv"))
RAIZ = ESTUDIO if NO_ESTUDIO else os.path.join(G, "_trabalho")
CAT = os.path.join(RAIZ, "catalogo")
CRM = os.environ.get("CRM_URL", "https://crm.homeluxoficial.com.br").rstrip("/")
UA = "homelux-publicar/1.0 (+https://www.homeluxoficial.com.br)"  # o Cloudflare bloqueia o agente padrao do urllib (403)

def token():
    t = os.environ.get("CATALOGO_TOKEN", "").strip()
    if not t and NO_ESTUDIO:
        env = os.path.join(ESTUDIO, "crm", ".env.local")
        if os.path.exists(env):
            for l in io.open(env, encoding="utf-8"):
                if l.startswith("CATALOGO_TOKEN="): t = l.split("=", 1)[1].strip().strip('"')
    if not t: print("ERRO: CATALOGO_TOKEN ausente"); sys.exit(2)
    return t

def baixar(url, cabecalhos=None, tentativas=3):
    for i in range(tentativas):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, **(cabecalhos or {})})
            with urllib.request.urlopen(req, timeout=120) as r: return r.read()
        except (urllib.error.URLError, TimeoutError) as e:
            if i == tentativas - 1: raise
            time.sleep(2 * (i + 1))

def sincronizar(tok):
    """Baixa o catálogo do CRM para CAT/ (produtos.csv, categorias.json, fotos/, desenhos/). Devolve o resumo."""
    dados = json.loads(baixar(f"{CRM}/api/catalogo/exportar", {"Authorization": f"Bearer {tok}"}).decode("utf-8"))
    os.makedirs(os.path.join(CAT, "fotos"), exist_ok=True); os.makedirs(os.path.join(CAT, "desenhos"), exist_ok=True)
    io.open(os.path.join(CAT, "produtos.csv"), "w", encoding="utf-8", newline="").write(dados["produtos_csv"])
    io.open(os.path.join(CAT, "categorias.json"), "w", encoding="utf-8", newline="\n").write(json.dumps(dados["categorias"], ensure_ascii=False, indent=2) + "\n")
    esperados = set(); n = 0
    for a in dados["arquivos"]:
        destino = os.path.join(CAT, a["destino"].replace("/", os.sep)); esperados.add(os.path.abspath(destino))
        if os.path.exists(destino) and os.path.getsize(destino) > 0 and os.environ.get("HOMELUX_REBAIXAR") != "1":
            # já temos: confere o tamanho remoto (HEAD) para pegar substituições com o mesmo nome
            try:
                req = urllib.request.Request(a["url"], method="HEAD", headers={"User-Agent": UA})
                with urllib.request.urlopen(req, timeout=60) as r: tam = int(r.headers.get("Content-Length") or -1)
                if tam == os.path.getsize(destino): continue
            except Exception: pass
        io.open(destino, "wb").write(baixar(a["url"])); n += 1
        print(f"\r  baixados {n}", end="")
    # o que não está mais no CRM sai da pasta (foto/desenho de produto removido)
    removidos = 0
    for sub in ("fotos", "desenhos"):
        d = os.path.join(CAT, sub)
        for f in os.listdir(d):
            p = os.path.abspath(os.path.join(d, f))
            if p not in esperados and not f.startswith("_") and not f.endswith(".md"): os.remove(p); removidos += 1
    print(f"\nCRM: {dados['familias']} famílias ({dados['ativas']} ativas), {len(dados['arquivos'])} arquivos ({n} baixados, {removidos} removidos)")
    return dados

def rodar(script, *args):
    env = dict(os.environ, HOMELUX_RAIZ=RAIZ, HOMELUX_SITE=SITE)
    if not NO_ESTUDIO: env["HOMELUX_MARCA"] = os.path.join(SITE, "assets")
    r = subprocess.run([sys.executable, os.path.join(G, script), *args], env=env, capture_output=True, text=True, encoding="utf-8", errors="replace")
    print(r.stdout.strip());
    if r.returncode != 0: print(r.stderr.strip()); raise SystemExit(f"{script} falhou ({r.returncode})")

def avisar(tok, status, detalhe, pdfs):
    """POST multipart para /api/catalogo/publicado (sem dependências externas)."""
    limite = uuid.uuid4().hex; corpo = io.BytesIO()
    def campo(n, v): corpo.write(f"--{limite}\r\nContent-Disposition: form-data; name=\"{n}\"\r\n\r\n{v}\r\n".encode("utf-8"))
    campo("publicacao_id", os.environ.get("PUBLICACAO_ID", "")); campo("status", status); campo("detalhe", json.dumps(detalhe, ensure_ascii=False))
    for n, p in pdfs.items():
        if p and os.path.exists(p):
            corpo.write(f"--{limite}\r\nContent-Disposition: form-data; name=\"{n}\"; filename=\"{os.path.basename(p)}\"\r\nContent-Type: application/pdf\r\n\r\n".encode("utf-8"))
            corpo.write(io.open(p, "rb").read()); corpo.write(b"\r\n")
    corpo.write(f"--{limite}--\r\n".encode("utf-8"))
    req = urllib.request.Request(f"{CRM}/api/catalogo/publicado", data=corpo.getvalue(), method="POST", headers={"Authorization": f"Bearer {tok}", "Content-Type": f"multipart/form-data; boundary={limite}", "User-Agent": UA})
    with urllib.request.urlopen(req, timeout=300) as r: print("CRM avisado:", r.read().decode("utf-8")[:200])

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--so-baixar", action="store_true"); ap.add_argument("--sem-pdf", action="store_true"); ap.add_argument("--sem-avisar", action="store_true")
    a = ap.parse_args(); tok = token(); t0 = time.time()
    detalhe = {"ambiente": "estudio" if NO_ESTUDIO else "github-action", "runner": os.environ.get("GITHUB_RUN_ID", "")}
    try:
        dados = sincronizar(tok); detalhe.update(familias=dados["familias"], ativas=dados["ativas"])
        if a.so_baixar: print("Catálogo local atualizado a partir do CRM."); return
        rodar("gerar-catalogo.py")
        pdfs = {}
        if not a.sem_pdf:
            os.makedirs(os.path.join(CAT, "pdf"), exist_ok=True)
            pdfs["pdf_catalogo"] = os.path.join(CAT, "pdf", "catalogo-homelux.pdf"); rodar("gerar-catalogo-pdf.py", "--saida", pdfs["pdf_catalogo"])
            pdfs["pdf_tecnico"] = os.path.join(CAT, "pdf", "catalogo-tecnico-homelux.pdf"); rodar("gerar-catalogo-tecnico.py", "--saida", pdfs["pdf_tecnico"])
            detalhe["pdf_kb"] = {k: os.path.getsize(v) // 1024 for k, v in pdfs.items()}
        detalhe["segundos"] = int(time.time() - t0)
        if not a.sem_avisar: avisar(tok, "concluida", detalhe, pdfs)
        print(f"Publicação concluída em {detalhe['segundos']}s")
    except SystemExit as e:
        if str(e) and str(e) != "0":
            detalhe["erro"] = str(e)[:300]
            if not a.sem_avisar and not a.so_baixar:
                try: avisar(tok, "erro", detalhe, {})
                except Exception as e2: print("não consegui avisar o CRM:", e2)
        raise
    except Exception as e:
        detalhe["erro"] = f"{type(e).__name__}: {e}"[:300]
        if not a.sem_avisar and not a.so_baixar:
            try: avisar(tok, "erro", detalhe, {})
            except Exception as e2: print("não consegui avisar o CRM:", e2)
        raise

if __name__ == "__main__":
    main()

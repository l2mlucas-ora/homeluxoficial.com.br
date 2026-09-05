/* Homelux — catálogo online: filtro por categoria + busca, sem dependências.
   Lê catalogo.json (gerado por ferramentas/gerar-catalogo.py). Estado na URL: ?cat=<id>&q=<termo>. */
(function () {
  'use strict';
  var grade = document.getElementById('grade');
  var chips = document.getElementById('chips');
  var busca = document.getElementById('busca');
  var contagem = document.getElementById('contagem');
  if (!grade) return;

  var estado = { cat: 'todas', q: '', sub: '' };
  var dados = null;

  function norm(s) {
    return (s || '').toString().toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '');
  }
  function lerUrl() {
    var p = new URLSearchParams(location.search);
    estado.cat = p.get('cat') || 'todas';
    estado.q = p.get('q') || '';
    estado.sub = p.get('sub') || '';
  }
  function gravarUrl() {
    var p = new URLSearchParams();
    if (estado.cat !== 'todas') p.set('cat', estado.cat);
    if (estado.q) p.set('q', estado.q);
    if (estado.sub) p.set('sub', estado.sub);
    var qs = p.toString();
    history.replaceState(null, '', location.pathname + (qs ? '?' + qs : ''));
  }
  function el(tag, attrs, filhos) {
    var e = document.createElement(tag);
    for (var k in attrs) if (attrs.hasOwnProperty(k)) {
      if (k === 'text') e.textContent = attrs[k]; else e.setAttribute(k, attrs[k]);
    }
    (filhos || []).forEach(function (f) { if (f) e.appendChild(f); });
    return e;
  }
  function nomeCat(id) {
    for (var i = 0; i < dados.categorias.length; i++) if (dados.categorias[i].id === id) return dados.categorias[i].nome;
    return id;
  }
  function nomeSub(cat, sub) {
    for (var i = 0; i < dados.categorias.length; i++) if (dados.categorias[i].id === cat) return (dados.categorias[i].subcategorias || {})[sub] || sub;
    return sub;
  }
  function cardProduto(p) {
    var foto = p.fotos && p.fotos[0];
    var fig = el('figure', {}, [foto ? el('img', { src: foto.thumb, alt: foto.alt || p.nome, loading: 'lazy', width: 480, height: 360 }) : null]);
    if (p.provisorio) fig.appendChild(el('span', { 'class': 'selo-prov', text: 'foto provisória' }));
    var nvar = p.variacoes ? p.variacoes.length : 0;
    var info = el('div', { 'class': 'info' }, [
      el('span', { 'class': 'cat', text: nomeCat(p.categoria) }),
      el('b', { text: p.nome }),
      el('span', { 'class': 'cod', text: 'cód. ' + p.codigo + (p.embalagem ? ' · emb. ' + p.embalagem : '') }),
      nvar > 1 ? el('span', { 'class': 'var', text: nvar + ' variações' }) : null
    ]);
    return el('a', { 'class': 'prod', href: p.url, style: 'position:relative' }, [fig, info]);
  }
  function filtrar() {
    var q = norm(estado.q).trim();
    return dados.produtos.filter(function (p) {
      if (!p.ativo) return false;
      if (estado.cat !== 'todas' && p.categoria !== estado.cat) return false;
      if (estado.sub && p.subcategoria !== estado.sub) return false;
      if (q && p.busca.indexOf(q) === -1) return false;
      return true;
    });
  }
  function render() {
    var lista = filtrar();
    grade.innerHTML = '';
    if (!lista.length) {
      grade.appendChild(el('div', { 'class': 'vazio', text: 'Nenhum produto com esse filtro. Tente outra palavra ou fale conosco pelo WhatsApp.' }));
    } else {
      var frag = document.createDocumentFragment();
      lista.forEach(function (p) { frag.appendChild(cardProduto(p)); });
      grade.appendChild(frag);
    }
    contagem.textContent = lista.length + (lista.length === 1 ? ' produto' : ' produtos') +
      (estado.cat !== 'todas' ? ' em ' + nomeCat(estado.cat) : '') + (estado.sub ? ' › ' + nomeSub(estado.cat, estado.sub) : '') + (estado.q ? ' para "' + estado.q + '"' : '');
    var bs = chips.querySelectorAll('.chip');
    for (var i = 0; i < bs.length; i++) bs[i].setAttribute('aria-pressed', bs[i].getAttribute('data-cat') === estado.cat ? 'true' : 'false');
    gravarUrl();
  }
  function montarChips() {
    chips.innerHTML = '';
    var todas = [{ id: 'todas', nome: 'Todas' }].concat(dados.categorias);
    todas.forEach(function (c) {
      var b = el('button', { 'class': 'chip', type: 'button', 'data-cat': c.id, 'aria-pressed': 'false', text: c.nome });
      b.addEventListener('click', function () { estado.cat = c.id; estado.sub = ''; render(); });
      chips.appendChild(b);
    });
  }
  var timer;
  busca.addEventListener('input', function () {
    clearTimeout(timer);
    timer = setTimeout(function () { estado.q = busca.value; render(); }, 150);
  });

  lerUrl();
  busca.value = estado.q;
  fetch('catalogo.json', { cache: 'no-cache' }).then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
    .then(function (j) {
      dados = j;
      if (!dados.categorias.some(function (c) { return c.id === estado.cat; })) estado.cat = 'todas';
      montarChips();
      render();
      // deep-link antigo #/produto/<codigo> → página estática
      var m = location.hash.match(/^#\/produto\/(.+)$/);
      if (m) { var alvo = dados.produtos.filter(function (p) { return p.codigo === m[1]; })[0]; if (alvo) location.replace(alvo.url); }
    })
    .catch(function () {
      grade.innerHTML = '';
      grade.appendChild(el('div', { 'class': 'vazio', text: 'Não conseguimos carregar o catálogo agora — fale conosco pelo WhatsApp ou tente novamente em instantes.' }));
      contagem.textContent = '';
    });
})();

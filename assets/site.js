/* Homelux — site.js: menu mobile + montagem dos links de WhatsApp.
   O número e as mensagens vêm do <body data-wa="..." data-wa-msgs='{...}'> (injetados pelo gerador a partir de catalogo/config.json). */
(function () {
  'use strict';
  var body = document.body;
  var numero = body.getAttribute('data-wa') || '';
  var msgs = {};
  try { msgs = JSON.parse(body.getAttribute('data-wa-msgs') || '{}'); } catch (e) { msgs = {}; }

  function linkWa(texto) {
    return 'https://wa.me/' + numero + (texto ? '?text=' + encodeURIComponent(texto) : '');
  }
  function preencher(modelo, dados) {
    return modelo.replace(/\{(\w+)\}/g, function (_, k) { return dados && dados[k] != null ? dados[k] : ''; });
  }
  // Todo elemento com data-wa-msg="chave" (opcionalmente data-wa-nome / data-wa-codigo) vira link wa.me
  var els = document.querySelectorAll('[data-wa-msg]');
  for (var i = 0; i < els.length; i++) {
    var el = els[i];
    var chave = el.getAttribute('data-wa-msg');
    var modelo = msgs[chave] || msgs.geral || '';
    var texto = preencher(modelo, { nome: el.getAttribute('data-wa-nome'), codigo: el.getAttribute('data-wa-codigo') });
    el.setAttribute('href', linkWa(texto));
    el.setAttribute('target', '_blank');
    el.setAttribute('rel', 'noopener');
  }

  // Menu mobile
  var btn = document.querySelector('.menu-btn');
  var nav = document.getElementById('menu-principal');
  if (btn && nav) {
    btn.addEventListener('click', function () {
      var aberto = nav.classList.toggle('aberto');
      btn.setAttribute('aria-expanded', aberto ? 'true' : 'false');
      btn.setAttribute('aria-label', aberto ? 'Fechar menu' : 'Abrir menu');
    });
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape' && nav.classList.contains('aberto')) btn.click(); });
  }

  // Mega-menu Produtos: clique abre/fecha no mobile e no teclado (hover já abre no desktop via CSS)
  var temSub = document.querySelector('.tem-sub');
  if (temSub) {
    var gat = temSub.querySelector('a[aria-haspopup]');
    gat.addEventListener('click', function (e) {
      var mobile = window.matchMedia('(max-width: 900px)').matches;
      if (mobile || e.detail === 0) {   // toque no mobile ou Enter/Espaço via teclado: alterna em vez de navegar
        e.preventDefault();
        var ab = temSub.classList.toggle('aberto');
        gat.setAttribute('aria-expanded', ab ? 'true' : 'false');
      }
    });
    document.addEventListener('click', function (e) { if (!temSub.contains(e.target)) { temSub.classList.remove('aberto'); gat.setAttribute('aria-expanded', 'false'); } });
  }

  // Cadastro rápido de lojista: vira mensagem de WhatsApp (sem backend, sem armazenar dado)
  var fl = document.querySelector('.form-lojista');
  if (fl) {
    fl.addEventListener('submit', function (e) {
      e.preventDefault();
      var d = new FormData(fl);
      function campo(rotulo, valor) { valor = (valor || '').toString().trim(); return valor ? rotulo + ': ' + valor + '\n' : ''; }
      var txt = '*CADASTRO DE LOJISTA — HOMELUX*\n\n' +
        campo('Empresa', d.get('empresa')) + campo('CNPJ', d.get('cnpj')) + campo('Cidade/UF', d.get('cidade')) + campo('Responsável', d.get('nome')) +
        campo('Ramo', d.get('ramo')) + campo('Interesse', d.get('interesse')) +
        '\nQuero abrir cadastro para comprar direto da fábrica. Aguardo retorno do comercial. Obrigado!';
      window.open(linkWa(txt), '_blank', 'noopener');
    });
  }

  // abertura: logo animada some após ~2,2 s (ou ao tocar)
  var ab = document.getElementById('abertura');
  if (ab) { var fechar = function () { ab.classList.add('saindo'); setTimeout(function () { if (ab.parentNode) ab.parentNode.removeChild(ab); }, 500); }; ab.addEventListener('click', fechar); setTimeout(fechar, 2100); }

  // ?dev=1 mostra selos internos (foto provisória)
  if (/[?&]dev=1/.test(location.search)) body.classList.add('dev');


  // Fachada (carrossel de linhas): auto 7 s, pausa no hover/foco, setas, pontos, respeita reduced-motion
  var fachada = document.querySelector('.fachada');
  if (fachada) {
    var slides = fachada.querySelectorAll('.slide'), pontos = fachada.querySelector('.pontos'), atual = 0, timer, parado = false;
    var reduzido = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    function ir(n) {
      atual = (n + slides.length) % slides.length;
      for (var i = 0; i < slides.length; i++) {
        slides[i].classList.toggle('ativo', i === atual);
        slides[i].setAttribute('aria-hidden', i === atual ? 'false' : 'true');
      }
      var bs = pontos.querySelectorAll('button');
      for (var k = 0; k < bs.length; k++) bs[k].setAttribute('aria-selected', k === atual ? 'true' : 'false');
    }
    function agendar() { clearTimeout(timer); if (!reduzido && !parado) timer = setTimeout(function () { ir(atual + 1); agendar(); }, 7000); }
    for (var s = 0; s < slides.length; s++) (function (idx) {
      var b = document.createElement('button'); b.type = 'button'; b.setAttribute('role', 'tab');
      b.setAttribute('aria-label', 'Linha ' + (idx + 1)); b.addEventListener('click', function () { ir(idx); agendar(); });
      pontos.appendChild(b);
    })(s);
    fachada.querySelector('.seta.ant').addEventListener('click', function () { ir(atual - 1); agendar(); });
    fachada.querySelector('.seta.prox').addEventListener('click', function () { ir(atual + 1); agendar(); });
    fachada.addEventListener('mouseenter', function () { parado = true; clearTimeout(timer); });
    fachada.addEventListener('mouseleave', function () { parado = false; agendar(); });
    fachada.addEventListener('focusin', function () { parado = true; clearTimeout(timer); });
    fachada.addEventListener('focusout', function () { parado = false; agendar(); });
    ir(0); agendar();
  }

  // Galeria da página de produto
  var principal = document.querySelector('.galeria .principal img');
  var minis = document.querySelectorAll('.galeria .miniaturas button');
  for (var j = 0; j < minis.length; j++) {
    minis[j].addEventListener('click', function () {
      for (var k = 0; k < minis.length; k++) minis[k].setAttribute('aria-pressed', 'false');
      this.setAttribute('aria-pressed', 'true');
      principal.src = this.getAttribute('data-src');
      principal.alt = this.querySelector('img').alt;
    });
  }
})();

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

  // ?dev=1 mostra selos internos (foto provisória)
  if (/[?&]dev=1/.test(location.search)) body.classList.add('dev');

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

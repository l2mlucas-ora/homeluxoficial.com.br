/* Homelux — pedido.js: carrinho de pedido sem backend.
   Itens ficam em localStorage ("homelux.pedido"); "Enviar pedido" abre o WhatsApp com o resumo.
   Usado na página de produto (adicionar), no header (contador) e em pedido.html (carrinho + dados do cliente). */
(function () {
  'use strict';
  var CHAVE = 'homelux.pedido';
  var body = document.body;
  var numero = body.getAttribute('data-wa') || '';

  function ler() { try { return JSON.parse(localStorage.getItem(CHAVE) || '[]'); } catch (e) { return []; } }
  function gravar(itens) { try { localStorage.setItem(CHAVE, JSON.stringify(itens)); } catch (e) {} atualizarContador(); }
  function total(itens) { return itens.reduce(function (s, i) { return s + i.qtd; }, 0); }
  function atualizarContador() {
    var n = total(ler());
    var els = document.querySelectorAll('.pedido-badge');
    for (var i = 0; i < els.length; i++) { els[i].textContent = n; els[i].hidden = n === 0; }
  }
  function adicionar(item) {
    var itens = ler();
    for (var i = 0; i < itens.length; i++) {
      if (itens[i].codigo === item.codigo) { itens[i].qtd += item.qtd; gravar(itens); return; }
    }
    itens.push(item); gravar(itens);
  }
  function avisar(msg) {
    var t = document.getElementById('pedido-aviso');
    if (!t) { t = document.createElement('div'); t.id = 'pedido-aviso'; t.className = 'pedido-aviso'; t.setAttribute('role', 'status'); document.body.appendChild(t); }
    t.innerHTML = '';
    t.appendChild(document.createTextNode(msg + ' '));
    var a = document.createElement('a'); a.href = body.getAttribute('data-raiz') + 'pedido.html'; a.textContent = 'Ver pedido →'; t.appendChild(a);
    t.classList.add('visivel');
    clearTimeout(avisar._t); avisar._t = setTimeout(function () { t.classList.remove('visivel'); }, 4500);
  }

  // ---- página de produto: linhas de variação com quantidade
  var formProd = document.querySelector('.form-pedido');
  if (formProd) {
    formProd.addEventListener('submit', function (e) {
      e.preventDefault();
      var linhas = formProd.querySelectorAll('tr[data-codigo]'), n = 0;
      for (var i = 0; i < linhas.length; i++) {
        var q = parseInt(linhas[i].querySelector('input').value, 10) || 0;
        if (q > 0) {
          adicionar({ codigo: linhas[i].getAttribute('data-codigo'), nome: linhas[i].getAttribute('data-nome'), familia: formProd.getAttribute('data-familia'), embalagem: formProd.getAttribute('data-embalagem'), qtd: q });
          linhas[i].querySelector('input').value = ''; n += q;
        }
      }
      if (n) avisar(n + (n === 1 ? ' item adicionado ao pedido.' : ' itens adicionados ao pedido.'));
      else avisar('Informe a quantidade de pelo menos um código.');
    });
    var mais = formProd.querySelectorAll('button[data-mais]');
    for (var m = 0; m < mais.length; m++) mais[m].addEventListener('click', function () {
      var inp = this.parentNode.querySelector('input'); inp.value = (parseInt(inp.value, 10) || 0) + parseInt(this.getAttribute('data-mais'), 10); if (inp.value < 0) inp.value = 0;
    });
  }

  // ---- página do pedido
  var lista = document.getElementById('pedido-itens');
  if (lista) {
    var form = document.getElementById('pedido-form');
    var vazio = document.getElementById('pedido-vazio');
    var resumo = document.getElementById('pedido-resumo');
    function render() {
      var itens = ler();
      lista.innerHTML = '';
      vazio.hidden = itens.length > 0; form.hidden = itens.length === 0;
      itens.forEach(function (it, idx) {
        var tr = document.createElement('tr');
        var c1 = document.createElement('td'); c1.className = 'cod'; c1.textContent = it.codigo; tr.appendChild(c1);
        var c2 = document.createElement('td'); var b = document.createElement('b'); b.textContent = it.familia; c2.appendChild(b);
        if (it.nome && it.nome !== it.familia) { c2.appendChild(document.createElement('br')); var s = document.createElement('span'); s.className = 'secundario'; s.textContent = it.nome; c2.appendChild(s); }
        if (it.embalagem) { c2.appendChild(document.createElement('br')); var e2 = document.createElement('span'); e2.className = 'secundario'; e2.textContent = 'emb. ' + it.embalagem; c2.appendChild(e2); }
        tr.appendChild(c2);
        var c3 = document.createElement('td'); c3.className = 'qtd';
        var inp = document.createElement('input'); inp.type = 'number'; inp.min = '1'; inp.value = it.qtd; inp.setAttribute('aria-label', 'Quantidade de ' + it.codigo);
        inp.addEventListener('change', function () { var v = parseInt(inp.value, 10) || 1; var arr = ler(); arr[idx].qtd = Math.max(1, v); gravar(arr); render(); });
        c3.appendChild(inp); tr.appendChild(c3);
        var c4 = document.createElement('td'); var rm = document.createElement('button'); rm.type = 'button'; rm.className = 'remover'; rm.setAttribute('aria-label', 'Remover ' + it.codigo); rm.textContent = '×';
        rm.addEventListener('click', function () { var arr = ler(); arr.splice(idx, 1); gravar(arr); render(); });
        c4.appendChild(rm); tr.appendChild(c4);
        lista.appendChild(tr);
      });
      resumo.textContent = itens.length ? itens.length + (itens.length === 1 ? ' código · ' : ' códigos · ') + total(itens) + ' unidades' : '';
    }
    render();
    document.getElementById('pedido-limpar').addEventListener('click', function () { if (confirm('Limpar todos os itens do pedido?')) { gravar([]); render(); } });

  // Validação dos dados do cliente: tudo obrigatório; CPF/CNPJ com dígito verificador (o CRM confere de novo no servidor).
  function soDig(s) { return (s || '').replace(/\D/g, ''); }
  function cpfValido(d) {
    if (d.length !== 11 || /^(\d)\1+$/.test(d)) return false;
    for (var t = 9; t < 11; t++) { var soma = 0; for (var i = 0; i < t; i++) soma += parseInt(d.charAt(i), 10) * (t + 1 - i); var dv = (soma * 10) % 11; if (dv === 10) dv = 0; if (dv !== parseInt(d.charAt(t), 10)) return false; }
    return true;
  }
  function cnpjValido(d) {
    if (d.length !== 14 || /^(\d)\1+$/.test(d)) return false;
    var calc = function (base, pesos) { var soma = 0; for (var i = 0; i < base.length; i++) soma += parseInt(base.charAt(i), 10) * pesos[i]; var r = soma % 11; return r < 2 ? 0 : 11 - r; };
    var p1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2], p2 = [6].concat(p1);
    return calc(d.slice(0, 12), p1) === parseInt(d.charAt(12), 10) && calc(d.slice(0, 13), p2) === parseInt(d.charAt(13), 10);
  }
  function validarCliente(form) {
    var d = new FormData(form); var erros = []; var campos = {};
    var marcar = function (n, msg) { erros.push(msg); campos[n] = true; };
    var nome = (d.get('nome') || '').trim(); if (nome.split(/\s+/).length < 2) marcar('nome', 'Informe o nome completo.');
    var tel = soDig(d.get('telefone')); if (tel.length < 10 || tel.length > 11 || /^(\d)\1+$/.test(tel)) marcar('telefone', 'Telefone inválido: use DDD + número (10 ou 11 dígitos).');
    var doc = soDig(d.get('documento')); if (!(doc.length === 11 ? cpfValido(doc) : doc.length === 14 ? cnpjValido(doc) : false)) marcar('documento', 'CPF ou CNPJ inválido — confira os dígitos.');
    var tipo = (d.get('tipo') || '').trim(); if (!tipo) marcar('tipo', 'Diga se você é lojista, instalador ou consumidor.');
    if (/lojista|distrib/i.test(tipo) && (d.get('empresa') || '').trim().length < 3) marcar('empresa', 'Lojista/distribuidor: informe o nome da empresa.');
    if (/lojista|distrib/i.test(tipo) && doc.length !== 14) marcar('documento', 'Lojista/distribuidor: informe o CNPJ.');
    var cid = (d.get('cidade') || '').trim(); if (cid.length < 4) marcar('cidade', 'Informe cidade e UF (ex.: Blumenau / SC).');
    var email = (d.get('email') || '').trim(); if (!/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(email)) marcar('email', 'E-mail inválido.');
    var els = form.querySelectorAll('input,select'); for (var i = 0; i < els.length; i++) els[i].classList.toggle('invalido', !!campos[els[i].name]);
    var caixa = document.getElementById('pedido-erros');
    if (!caixa) { caixa = document.createElement('div'); caixa.id = 'pedido-erros'; caixa.className = 'form-erros'; caixa.setAttribute('role', 'alert'); form.insertBefore(caixa, form.querySelector('.form-acoes') || form.lastElementChild); }
    caixa.innerHTML = erros.length ? '<b>Confira os dados antes de enviar:</b><ul>' + erros.map(function (e) { return '<li>' + e + '</li>'; }).join('') + '</ul>' : '';
    caixa.style.display = erros.length ? '' : 'none';
    if (erros.length) { var primeiro = form.querySelector('.invalido'); if (primeiro) primeiro.focus(); }
    return erros.length === 0;
  }
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      var itens = ler(); if (!itens.length) { avisar('Adicione ao menos um item ao pedido.'); return; }
      if (!validarCliente(form)) return;
      var d = new FormData(form);
      // Mensagem em blocos (WhatsApp aceita *negrito* e quebras de linha); campos vazios ficam de fora.
      function campo(rotulo, valor) { valor = (valor || '').toString().trim(); return valor ? rotulo + ': ' + valor + '\n' : ''; }
      var agora = new Date(); var pad = function (n) { return (n < 10 ? '0' : '') + n; };
      var ref = agora.getFullYear() + pad(agora.getMonth() + 1) + pad(agora.getDate()) + '-' + pad(agora.getHours()) + pad(agora.getMinutes());
      var linhas = itens.map(function (it, i) {
        var det = [];
        if (it.nome && it.nome !== it.familia) det.push(it.nome);
        det.push(it.qtd + ' un');
        if (it.embalagem) det.push('emb. ' + it.embalagem);
        return (i + 1) + '. *' + it.codigo + '* — ' + it.familia + '\n    ' + det.join(' · ');
      });
      var txt = '*PEDIDO PELO SITE — HOMELUX*\n' +
        'Ref. ' + ref + ' · ' + pad(agora.getDate()) + '/' + pad(agora.getMonth() + 1) + '/' + agora.getFullYear() + ' ' + pad(agora.getHours()) + ':' + pad(agora.getMinutes()) + '\n' +
        '\n*DADOS DO CLIENTE*\n' +
        campo('Nome', d.get('nome')) + campo('Empresa', d.get('empresa')) + campo('CNPJ/CPF', d.get('documento')) + campo('Tipo', d.get('tipo')) +
        campo('Cidade/UF', d.get('cidade')) + campo('Telefone', d.get('telefone')) + campo('E-mail', d.get('email')) +
        '\n*ITENS DO PEDIDO* (' + itens.length + (itens.length === 1 ? ' código' : ' códigos') + ' · ' + total(itens) + ' unidades)\n' + linhas.join('\n') + '\n' +
        (d.get('obs') ? '\n*OBSERVAÇÕES*\n' + d.get('obs').trim() + '\n' : '') +
        '\nAguardo orçamento com prazo e condições de pagamento. Obrigado!';
      // registra no CRM (se configurado) antes de abrir o WhatsApp — falha silenciosa: o WhatsApp abre de qualquer jeito
      var crm = document.body.getAttribute('data-crm');
      if (crm) {
        try {
          var ctrl = ('AbortController' in window) ? new AbortController() : null; if (ctrl) setTimeout(function () { ctrl.abort(); }, 4000);
          fetch(crm, { method: 'POST', mode: 'cors', keepalive: true, headers: { 'content-type': 'application/json' }, signal: ctrl ? ctrl.signal : undefined,
            body: JSON.stringify({ ref: ref, nome: d.get('nome'), empresa: d.get('empresa'), documento: d.get('documento'), tipo: d.get('tipo'), cidade: d.get('cidade'), telefone: d.get('telefone'), email: d.get('email'), obs: d.get('obs'), hp: d.get('hp') || '',
              itens: itens.map(function (it) { return { codigo: it.codigo, familia: it.familia, nome: it.nome, qtd: it.qtd, embalagem: it.embalagem }; }) }) }).catch(function () {});
        } catch (e) { /* ignora */ }
      }
      window.open('https://wa.me/' + numero + '?text=' + encodeURIComponent(txt), '_blank', 'noopener');
      var ok = document.getElementById('pedido-enviado'); if (ok) ok.hidden = false;
    });
  }

  atualizarContador();
})();

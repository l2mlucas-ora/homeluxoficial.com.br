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
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      var itens = ler(); if (!itens.length) return;
      var d = new FormData(form);
      var linhas = itens.map(function (it, i) { return (i + 1) + ') ' + it.codigo + ' — ' + it.familia + (it.nome && it.nome !== it.familia ? ' (' + it.nome + ')' : '') + ' — ' + it.qtd + ' un'; });
      var txt = 'PEDIDO PELO SITE — Homelux\n' +
        'Cliente: ' + (d.get('nome') || '') + '\n' +
        'Empresa: ' + (d.get('empresa') || '-') + '\n' +
        'CNPJ/CPF: ' + (d.get('documento') || '-') + '\n' +
        'Tipo: ' + (d.get('tipo') || '') + '\n' +
        'Cidade/UF: ' + (d.get('cidade') || '') + '\n' +
        'Telefone: ' + (d.get('telefone') || '') + '\n' +
        (d.get('email') ? 'E-mail: ' + d.get('email') + '\n' : '') +
        '\nITENS (' + itens.length + ' códigos, ' + total(itens) + ' un):\n' + linhas.join('\n') + '\n' +
        (d.get('obs') ? '\nObservações: ' + d.get('obs') + '\n' : '') +
        '\nAguardo orçamento com prazo e condições. Obrigado!';
      window.open('https://wa.me/' + numero + '?text=' + encodeURIComponent(txt), '_blank', 'noopener');
      var ok = document.getElementById('pedido-enviado'); if (ok) ok.hidden = false;
    });
  }

  atualizarContador();
})();

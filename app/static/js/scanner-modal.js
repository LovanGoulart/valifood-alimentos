let html5QrCode = null;
let isScanning = false;
let lastScannedCode = null;
let scanCooldown = false;

function openScannerModal() {
    const modal = document.getElementById('scanner-modal');
    const resultDiv = document.getElementById('scanner-result');
    const readerDiv = document.getElementById('scanner-reader');
    const loadingDiv = document.getElementById('scanner-loading');

    modal.style.display = 'flex';
    resultDiv.style.display = 'none';
    readerDiv.style.display = 'block';
    loadingDiv.style.display = 'none';
    lastScannedCode = null;
    scanCooldown = false;

    startScanner();
}

function closeScannerModal() {
    const modal = document.getElementById('scanner-modal');
    modal.style.display = 'none';
    stopScanner();
}

// Para e limpa a câmera — retorna Promise
function stopScanner() {
    return new Promise((resolve) => {
        if (!html5QrCode || !isScanning) {
            isScanning = false;
            resolve();
            return;
        }
        html5QrCode.stop().then(() => {
            html5QrCode.clear();
            isScanning = false;
            resolve();
        }).catch((err) => {
            console.error("Erro ao parar scanner:", err);
            isScanning = false;
            resolve();
        });
    });
}

function startScanner() {
    const readerDiv = document.getElementById('scanner-reader');

    // Se por algum motivo ainda estiver escaneando, não inicia
    if (isScanning) {
        console.log("Scanner já está ativo");
        return;
    }

    // Garante que a área da câmera está visível
    readerDiv.style.display = 'block';
    readerDiv.innerHTML = '';

    html5QrCode = new Html5Qrcode("scanner-reader");

    const config = {
        fps: 10,
        qrbox: { width: 260, height: 160 },
        aspectRatio: 1.333
    };

    html5QrCode.start(
        { facingMode: "environment" },
        config,
        onScanSuccess,
        onScanFailure
    ).then(() => {
        isScanning = true;
        console.log("Câmera iniciada");
    }).catch(err => {
        console.error("Erro ao iniciar scanner:", err);
        alert("Não foi possível acessar a câmera. Verifique as permissões.");
        closeScannerModal();
    });
}

function onScanSuccess(decodedText, decodedResult) {
    if (scanCooldown) return;
    if (decodedText === lastScannedCode) return;

    lastScannedCode = decodedText;
    scanCooldown = true;

    const loadingDiv = document.getElementById('scanner-loading');
    const resultDiv = document.getElementById('scanner-result');
    const readerDiv = document.getElementById('scanner-reader');
    const codeSpan = document.getElementById('scanned-code');
    const actionsDiv = document.getElementById('scanner-actions');

    readerDiv.style.display = 'none';
    loadingDiv.style.display = 'block';
    codeSpan.textContent = decodedText;

    // Para a câmera primeiro, depois consulta o servidor
    stopScanner().then(() => {
        fetch('/api/barcode/lookup', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ barcode: decodedText })
        })
        .then(r => r.json())
        .then(data => {
            loadingDiv.style.display = 'none';
            resultDiv.style.display = 'block';
            renderActions(data, decodedText, actionsDiv);
        })
        .catch(err => {
            console.error(err);
            loadingDiv.style.display = 'none';
            resultDiv.style.display = 'block';
            actionsDiv.innerHTML = '<p class="error-msg">Erro ao consultar servidor.</p><button class="btn btn-primary" onclick="rescan()">Tentar de novo</button>';
        });
    });
}

function onScanFailure(error) {
    // Silencioso — scanner contínuo
}

function rescan() {
    const resultDiv = document.getElementById('scanner-result');
    resultDiv.style.display = 'none';
    lastScannedCode = null;
    scanCooldown = false;

    // Aguarda parar completamente antes de reabrir
    stopScanner().then(() => {
        startScanner();
    });
}

function renderActions(data, barcode, container) {
    container.innerHTML = '';
    const btnGroup = document.createElement('div');
    btnGroup.className = 'btn-group';
    btnGroup.style.cssText = 'display:flex;flex-direction:column;gap:8px;';

    if (data.found && data.product) {
        const p = data.product;
        const info = document.createElement('div');
        info.className = 'result-info';
        info.innerHTML = `
            <p><strong>${p.name}</strong></p>
            <p>${Math.floor(p.quantity || 0)} ${p.unit || 'unidade'} em estoque</p>
            <p style="font-size:0.85em;opacity:0.7;">Validade: ${p.expiration_date || 'Sem validade'}</p>
        `;
        container.appendChild(info);

        // 1. Dar baixa (consumir 1 unidade)
        const btnBaixa = document.createElement('button');
        btnBaixa.className = 'btn btn-secondary';
        btnBaixa.innerHTML = '➖ Dar baixa (1 unidade)';
        btnBaixa.onclick = function() {
            postForm('/produtos/consumir-por-codigo', { barcode: barcode, amount: '1' });
        };
        btnGroup.appendChild(btnBaixa);

        // 2. Adicionar — vai direto para a edição do produto para
        // complementar quantidade, validade e demais opções
        const btnAdd = document.createElement('a');
        btnAdd.className = 'btn btn-primary';
        btnAdd.innerHTML = '➕ Adicionar (1 unidade)';
        btnAdd.href = '/produtos/' + p.id + '/editar';
        btnGroup.appendChild(btnAdd);

        // 3. Editar
        const btnEdit = document.createElement('a');
        btnEdit.className = 'btn btn-ghost';
        btnEdit.href = '/produtos/' + p.id + '/editar';
        btnEdit.textContent = '✏️ Editar produto';
        btnGroup.appendChild(btnEdit);

        // 4. Excluir
        const btnDel = document.createElement('button');
        btnDel.className = 'btn btn-danger';
        btnDel.innerHTML = '🗑️ Excluir produto';
        btnDel.onclick = function() {
            if (confirm('Tem certeza que deseja excluir "' + p.name + '"?')) {
                postForm('/produtos/excluir-por-codigo', { barcode: barcode });
            }
        };
        btnGroup.appendChild(btnDel);

    } else {
        const info = document.createElement('div');
        info.className = 'result-info';
        if (data.prefill) {
            info.innerHTML = `
                <p><strong>${data.prefill.name}</strong></p>
                <p style="font-size:0.85em;opacity:0.7;">Produto excluído anteriormente — os dados serão pré-preenchidos no cadastro.</p>
            `;
        } else {
            info.innerHTML = `<p>Produto não cadastrado no sistema.</p>`;
        }
        container.appendChild(info);

        const btnNew = document.createElement('a');
        btnNew.className = 'btn btn-primary';
        btnNew.href = '/produtos/novo/' + barcode;
        btnNew.textContent = '➕ Cadastrar novo produto';
        btnGroup.appendChild(btnNew);
    }

    // Escanear outro
    const btnRescan = document.createElement('button');
    btnRescan.className = 'btn btn-ghost';
    btnRescan.textContent = '📷 Escanear outro código';
    btnRescan.onclick = rescan;
    btnGroup.appendChild(btnRescan);

    container.appendChild(btnGroup);
}

function postForm(action, fields) {
    const form = document.createElement('form');
    form.method = 'POST';
    form.action = action;
    for (const [key, value] of Object.entries(fields)) {
        const input = document.createElement('input');
        input.type = 'hidden';
        input.name = key;
        input.value = value;
        form.appendChild(input);
    }
    document.body.appendChild(form);
    form.submit();
}
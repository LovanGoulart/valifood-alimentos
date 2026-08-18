let scannerStream = null;
function openScanner() {
    const container = document.getElementById('scanner-container');
    if (!container) { window.location.href = '/products/new'; return; }
    container.classList.add('active'); startScanner();
}
function closeScanner() {
    const container = document.getElementById('scanner-container');
    if (container) container.classList.remove('active');
    if (scannerStream) { scannerStream.getTracks().forEach(t => t.stop()); scannerStream = null; }
}
async function startScanner() {
    const video = document.getElementById('scanner-video');
    if (!video) return;
    try {
        scannerStream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' } });
        video.srcObject = scannerStream; await video.play();
        setTimeout(() => {
            if (scannerStream) { closeScanner(); const code = prompt('Digite o código de barras manualmente:'); if (code) handleBarcode(code); }
        }, 4000);
    } catch (err) {
        alert('Não foi possível acessar a câmera. Use a digitação manual.');
        closeScanner();
    }
}
function handleBarcode(barcode) {
    closeScanner();
    fetch('/api/barcode/lookup', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ barcode: barcode }) })
    .then(r => r.json())
    .then(data => {
        if (data.found) window.location.href = '/products/' + data.product.id;
        else window.location.href = '/products/new/' + barcode;
    })
    .catch(() => window.location.href = '/products/new/' + barcode);
}
if (!document.getElementById('scanner-container')) {
    const div = document.createElement('div');
    div.id = 'scanner-container'; div.className = 'scanner-container';
    div.innerHTML = `<video id="scanner-video" class="scanner-video" autoplay playsinline muted></video>
        <div class="scanner-overlay"><div class="scanner-frame"></div><p class="scanner-text">Aponte para o código de barras</p></div>
        <button class="scanner-close" onclick="closeScanner()">✕</button>
        <button class="scanner-manual" onclick="closeScanner();window.location.href='/products/new'">Digitar código manualmente</button>`;
    document.body.appendChild(div);
}

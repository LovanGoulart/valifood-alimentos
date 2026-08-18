// Inscrição de notificações push (Web Push + VAPID)

function urlBase64ToUint8Array(base64String) {
    const padding = '='.repeat((4 - base64String.length % 4) % 4);
    const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');
    const rawData = atob(base64);
    const outputArray = new Uint8Array(rawData.length);
    for (let i = 0; i < rawData.length; ++i) outputArray[i] = rawData.charCodeAt(i);
    return outputArray;
}

async function getSwRegistration() {
    if (!('serviceWorker' in navigator)) throw new Error('Navegador sem suporte a service worker');
    return await navigator.serviceWorker.ready;
}

async function subscribeToPush() {
    if (!('Notification' in window)) {
        alert('⚠️ Seu navegador não suporta notificações.');
        return false;
    }
    if (!('PushManager' in window)) {
        alert('⚠️ Seu navegador não suporta notificações push.');
        return false;
    }

    const permission = await Notification.requestPermission();
    if (permission !== 'granted') {
        alert('⚠️ Permissão negada. Ative as notificações nas configurações do navegador/celular.');
        return false;
    }

    try {
        const reg = await getSwRegistration();
        const keyResp = await fetch('/api/push/public-key');
        const { publicKey } = await keyResp.json();

        let subscription = await reg.pushManager.getSubscription();
        if (!subscription) {
            subscription = await reg.pushManager.subscribe({
                userVisibleOnly: true,
                applicationServerKey: urlBase64ToUint8Array(publicKey)
            });
        }

        const resp = await fetch('/api/push/subscribe', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ subscription: subscription.toJSON() })
        });

        if (resp.ok) {
            return true;
        }
        alert('⚠️ Erro ao registrar inscrição no servidor.');
        return false;
    } catch (err) {
        console.error('Erro ao inscrever push:', err);
        alert('⚠️ Não foi possível ativar as notificações: ' + err.message);
        return false;
    }
}

async function sendTestPush() {
    try {
        const resp = await fetch('/api/push/test', { method: 'POST' });
        const data = await resp.json();
        if (resp.ok) {
            alert('✓ Notificação de teste enviada! Ela deve chegar em instantes.');
        } else {
            alert('⚠️ ' + (data.error || 'Erro ao enviar teste.'));
        }
    } catch (err) {
        alert('⚠️ Erro de conexão ao enviar teste.');
    }
}

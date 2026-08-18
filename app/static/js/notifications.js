function checkAlerts() {
    fetch('/api/alerts').then(r => r.json()).then(alerts => {
        if (alerts.length > 0) {
            const urgent = alerts.filter(a => a.level === 'vencido' || a.level === 'vence_hoje').length;
            if (urgent > 0 && 'Notification' in window && Notification.permission === 'granted') {
                new Notification('ValiFood', { body: 'Você tem ' + urgent + ' alimento(s) vencendo hoje ou já vencidos!', icon: '/static/icons/icon-192x192.png' });
            }
        }
    });
}
setInterval(checkAlerts, 3600000);
if (document.visibilityState === 'visible') checkAlerts();

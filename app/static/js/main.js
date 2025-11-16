// Простые JavaScript функции для улучшения UX
document.addEventListener('DOMContentLoaded', function() {
    // Автоматическое скрытие alert через 5 секунд
    setTimeout(function() {
        const alerts = document.querySelectorAll('.alert');
        alerts.forEach(function(alert) {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        });
    }, 5000);
});
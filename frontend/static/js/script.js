// Конфетти при достижениях
document.addEventListener('DOMContentLoaded', () => {
    const alerts = document.querySelectorAll('.alert-success');
    alerts.forEach(alert => {
        if (alert.textContent.includes('🏆')) {
            for (let i = 0; i < 30; i++) {
                const confetti = document.createElement('div');
                confetti.textContent = ['🎉', '⭐', '🌟', '✨', '🏆'][Math.floor(Math.random() * 5)];
                confetti.style.cssText = `
                    position: fixed;
                    top: ${Math.random() * 100}%;
                    left: ${Math.random() * 100}%;
                    font-size: ${20 + Math.random() * 30}px;
                    pointer-events: none;
                    animation: confetti ${0.8 + Math.random() * 0.5}s ease forwards;
                    z-index: 9999;
                `;
                document.body.appendChild(confetti);
                setTimeout(() => confetti.remove(), 2000);
            }
        }
    });
});

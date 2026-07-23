// Конфетти при достижениях
function secureRandom() {
    const array = new Uint32Array(1);
    window.crypto.getRandomValues(array);
    return array[0] / (0xffffffff + 1);
}

document.addEventListener('DOMContentLoaded', () => {
    const alerts = document.querySelectorAll('.alert-success');
    alerts.forEach(alert => {
        if (alert.textContent.includes('🏆')) {
            for (let i = 0; i < 30; i++) {
                const confetti = document.createElement('div');
                confetti.textContent = ['🎉', '⭐', '🌟', '✨', '🏆'][Math.floor(secureRandom() * 5)];
                confetti.style.cssText = `
                    position: fixed;
                    top: ${secureRandom() * 100}%;
                    left: ${secureRandom() * 100}%;
                    font-size: ${20 + secureRandom() * 30}px;
                    pointer-events: none;
                    animation: confetti ${0.8 + secureRandom() * 0.5}s ease forwards;
                    z-index: 9999;
                `;
                document.body.appendChild(confetti);
                setTimeout(() => confetti.remove(), 2000);
            }
        }
    });
});

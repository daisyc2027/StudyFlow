const timer = document.querySelector('[data-timer-seconds]');
if (timer && timer.dataset.running === 'true') {
  const base = Number(timer.dataset.timerSeconds);
  const started = performance.now();
  setInterval(() => { timer.textContent = ((base + (performance.now() - started) / 1000) / 60).toFixed(1) + ' min'; }, 1000);
}

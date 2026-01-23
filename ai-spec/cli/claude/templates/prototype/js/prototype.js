// Prototype State Switcher
document.addEventListener('DOMContentLoaded', function() {
  const switcher = document.querySelector('.state-switcher');
  if (!switcher) return;

  const buttons = switcher.querySelectorAll('.state-btn');
  const stateContainers = document.querySelectorAll('[data-state]');

  buttons.forEach(btn => {
    btn.addEventListener('click', function() {
      const state = this.dataset.state;
      
      // Update button states
      buttons.forEach(b => b.classList.remove('active'));
      this.classList.add('active');

      // Show/hide state containers
      stateContainers.forEach(container => {
        if (container.dataset.state === state) {
          container.style.display = 'block';
        } else {
          container.style.display = 'none';
        }
      });
    });
  });

  // Initialize: show default state
  const defaultBtn = switcher.querySelector('[data-state="default"]');
  if (defaultBtn) defaultBtn.click();
});

// Retry function for error states
function retry() {
  location.reload();
}

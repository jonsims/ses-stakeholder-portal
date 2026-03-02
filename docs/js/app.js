document.addEventListener('DOMContentLoaded', () => {

  // --- Page data ---
  const dataEl = document.getElementById('page-data');
  if (!dataEl) return; // Only run on role pages
  const pageData = JSON.parse(dataEl.textContent);
  const prefix = `ses-${pageData.category}-${pageData.role}`;

  // --- Scroll progress bar ---
  const progressBar = document.querySelector('.scroll-progress');
  if (progressBar) {
    window.addEventListener('scroll', () => {
      const scrollTop = window.scrollY;
      const docHeight = document.documentElement.scrollHeight - window.innerHeight;
      const progress = docHeight > 0 ? scrollTop / docHeight : 0;
      progressBar.style.transform = `scaleX(${progress})`;
    }, { passive: true });
  }

  // --- Scroll-reveal for intel cards ---
  const revealCards = document.querySelectorAll('.reveal-ready');
  if (revealCards.length > 0 && 'IntersectionObserver' in window) {
    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add('revealed');
          observer.unobserve(entry.target);
        }
      });
    }, { threshold: 0.15 });
    revealCards.forEach(card => observer.observe(card));
  } else {
    revealCards.forEach(card => card.classList.add('revealed'));
  }

  // --- Debounced save ---
  const saveIndicator = document.getElementById('save-indicator');
  let saveTimeout;
  function showSaved() {
    if (saveIndicator) {
      saveIndicator.classList.add('visible');
      clearTimeout(saveTimeout);
      saveTimeout = setTimeout(() => saveIndicator.classList.remove('visible'), 2000);
    }
  }

  // --- Textarea auto-save ---
  document.querySelectorAll('textarea[data-key]').forEach(textarea => {
    const key = `${prefix}-${textarea.dataset.key}`;

    // Load saved value
    const saved = localStorage.getItem(key);
    if (saved) textarea.value = saved;

    // Save on input (debounced)
    let inputTimeout;
    textarea.addEventListener('input', () => {
      clearTimeout(inputTimeout);
      inputTimeout = setTimeout(() => {
        localStorage.setItem(key, textarea.value);
        showSaved();
      }, 400);
    });
  });

  // --- Star buttons on evidence ---
  const starKey = `${prefix}-starred-evidence`;
  let starred = new Set();
  try {
    const saved = localStorage.getItem(starKey);
    if (saved) starred = new Set(JSON.parse(saved));
  } catch (e) {}

  document.querySelectorAll('.star-btn').forEach(btn => {
    const item = btn.closest('.evidence-item');
    const index = parseInt(item.dataset.index);

    // Restore state
    if (starred.has(index)) {
      btn.classList.add('starred');
      btn.innerHTML = '&#9733;'; // filled star
      item.classList.add('starred-item');
    }

    btn.addEventListener('click', () => {
      if (starred.has(index)) {
        starred.delete(index);
        btn.classList.remove('starred');
        btn.innerHTML = '&#9734;'; // empty star
        item.classList.remove('starred-item');
      } else {
        starred.add(index);
        btn.classList.add('starred');
        btn.innerHTML = '&#9733;';
        item.classList.add('starred-item');
      }
      localStorage.setItem(starKey, JSON.stringify([...starred]));
      showSaved();
    });
  });

  // --- Coalition prediction cards ---
  const coalitionKey = `${prefix}-coalitions`;
  const states = ['neutral', 'ally', 'complicated', 'opponent'];
  const stateLabels = {
    neutral: 'Tap to predict',
    ally: 'Likely Ally',
    complicated: "It's Complicated",
    opponent: 'Likely Opponent'
  };

  let coalitions = {};
  try {
    const saved = localStorage.getItem(coalitionKey);
    if (saved) coalitions = JSON.parse(saved);
  } catch (e) {}

  document.querySelectorAll('.coalition-card').forEach(card => {
    const shId = card.dataset.stakeholderId;

    // Restore state
    if (coalitions[shId]) {
      card.dataset.state = coalitions[shId];
      card.querySelector('.coalition-card__state').textContent = stateLabels[coalitions[shId]];
    }

    card.addEventListener('click', () => {
      const currentState = card.dataset.state;
      const nextIndex = (states.indexOf(currentState) + 1) % states.length;
      const nextState = states[nextIndex];

      card.dataset.state = nextState;
      card.querySelector('.coalition-card__state').textContent = stateLabels[nextState];

      if (nextState === 'neutral') {
        delete coalitions[shId];
      } else {
        coalitions[shId] = nextState;
      }
      localStorage.setItem(coalitionKey, JSON.stringify(coalitions));
      showSaved();
    });
  });

  // --- Post-summit unlock ---
  const unlockBtn = document.getElementById('unlock-btn');
  const postContent = document.getElementById('post-summit-content');
  const unlockKey = `${prefix}-post-summit-unlocked`;

  if (unlockBtn && postContent) {
    // Restore unlock state
    if (localStorage.getItem(unlockKey) === 'true') {
      unlockBtn.style.display = 'none';
      postContent.style.display = 'block';
    }

    unlockBtn.addEventListener('click', () => {
      unlockBtn.style.display = 'none';
      postContent.style.display = 'block';
      localStorage.setItem(unlockKey, 'true');
    });
  }

  // --- Coalition reveal ---
  const revealBtn = document.getElementById('reveal-btn');
  const revealContent = document.getElementById('coalition-reveal');
  const revealKey = `${prefix}-coalition-revealed`;

  if (revealBtn && revealContent) {
    if (localStorage.getItem(revealKey) === 'true') {
      revealBtn.style.display = 'none';
      revealContent.style.display = 'block';
    }

    revealBtn.addEventListener('click', () => {
      revealBtn.style.display = 'none';
      revealContent.style.display = 'block';
      localStorage.setItem(revealKey, 'true');
    });
  }
});

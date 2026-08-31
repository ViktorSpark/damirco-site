// Mobile navigation toggle
function initNav() {
  var toggle = document.querySelector('.nav-toggle');
  var links = document.querySelector('.nav-links');
  if (toggle && links) {
    toggle.addEventListener('click', function () {
      links.classList.toggle('open');
    });
  }
}

// Form validation + "unlock" of full catalog
// NOTE: email/backend sending is intentionally NOT wired yet (see below).
function validateLead(form) {
  var name = form.querySelector('[name="name"]');
  var phone = form.querySelector('[name="phone"]');
  var err = form.querySelector('.form-error');
  var problems = [];
  if (!name || !name.value.trim()) problems.push('Укажите ваше имя');
  if (phone) {
    var phoneVal = phone.value.replace(/[^0-9+]/g, '');
    if (phoneVal.length < 10) problems.push('Укажите корректный телефон');
  }
  if (problems.length) {
    if (err) err.textContent = problems.join('. ') + '.';
    return null;
  }
  if (err) err.textContent = '';
  return {
    name: name.value.trim(),
    phone: phone.value.trim(),
    company: (form.querySelector('[name="company"]') || {}).value || ''
  };
}

function initOrderForm() {
  var form = document.getElementById('orderForm');
  if (!form) return;
  form.addEventListener('submit', function (e) {
    e.preventDefault();
    var lead = validateLead(form);
    if (!lead) return;
    var success = document.getElementById('orderSuccess');
    if (success) success.classList.remove('hidden');
    form.reset();
  });
}

// Catalog form: unlock the full catalog after submit
function initCatalogForm() {
  var form = document.getElementById('catalogForm');
  if (!form) return;

  form.addEventListener('submit', function (e) {
    e.preventDefault();
    var name = form.querySelector('#name');
    var phone = form.querySelector('#phone');
    var company = form.querySelector('#company');
    var err = form.querySelector('.form-error');

    var problems = [];
    if (!name.value.trim()) problems.push('Укажите ваше имя');
    var phoneVal = phone.value.replace(/[^0-9+]/g, '');
    if (phoneVal.length < 10) problems.push('Укажите корректный телефон');

    if (problems.length) {
      if (err) err.textContent = problems.join('. ') + '.';
      return;
    }
    if (err) err.textContent = '';

    // Collect lead data (for future backend wiring)
    var lead = {
      name: name.value.trim(),
      phone: phone.value.trim(),
      company: (company && company.value.trim()) || '',
      source: 'catalog-form',
      date: new Date().toISOString()
    };

    // ============================================================
    // EMAIL / BACKEND PLACEHOLDER
    // Настроить отправку на почту (например, damirgrupp@mail.ru):
    //   1) Подключите серверный обработчик (PHP/Node/Formspree/EmailJS)
    //      и отправьте сюда объект `lead`.
    //   2) Или используйте сервис Formspree:
    //      fetch('https://formspree.io/f/YOUR_FORM_ID', {
    //          method: 'POST',
    //          headers: {'Content-Type':'application/json'},
    //          body: JSON.stringify(lead)
    //      });
    // ============================================================

    // Unlock the full catalog
    var gate = document.getElementById('catalogGate');
    var full = document.getElementById('fullCatalog');
    var fullBody = document.getElementById('fullBody');
    var success = document.getElementById('formSuccess');
    if (success) success.classList.remove('hidden');
    if (gate) gate.classList.add('hidden');
    if (full) full.classList.remove('hidden');
    if (fullBody) fullBody.classList.remove('hidden');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  });
}

// Category filter chips on catalog page
function initFilter() {
  var chips = document.querySelectorAll('.chip');
  if (!chips.length) return;
  chips.forEach(function (chip) {
    chip.addEventListener('click', function () {
      chips.forEach(function (c) { c.classList.remove('active'); });
      chip.classList.add('active');
      var target = chip.getAttribute('data-target');
      var groups = document.querySelectorAll('.cat-group');
      groups.forEach(function (g) {
        if (target === 'all' || g.getAttribute('data-category') === target) {
          g.style.display = '';
        } else {
          g.style.display = 'none';
        }
      });
    });
  });
}

// Product search on catalog page
function initSearch() {
  var input = document.querySelector('.cat-search input');
  if (!input) return;
  input.addEventListener('input', function () {
    var q = input.value.trim().toLowerCase();
    var cards = document.querySelectorAll('.card[data-title]');
    cards.forEach(function (card) {
      var ok = !q || (card.getAttribute('data-title') || '').toLowerCase().indexOf(q) !== -1;
      card.style.display = ok ? '' : 'none';
    });
  });
}

document.addEventListener('DOMContentLoaded', function () {
  initNav();
  initOrderForm();
  initCatalogForm();
  initFilter();
  initSearch();
});

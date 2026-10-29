/* BALA CRM — сайт: тема, меню, контакты */
(function () {
  /* Номер WhatsApp для заявок на облачную версию. Пусто — кнопки заявок скрыты. Формат: 77011234567 */
  var CONTACT_WA = '';

  var root = document.documentElement;
  try { var s = localStorage.getItem('bala-site-theme'); if (s === 'dark' || s === 'light') root.setAttribute('data-theme', s); } catch (e) {}
  function eff() { return root.getAttribute('data-theme') || (matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'); }
  var SUN = '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></svg>';
  var MOON = '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"/></svg>';
  function paint() { var b = document.getElementById('theme'); if (b) { b.innerHTML = eff() === 'dark' ? SUN : MOON; b.setAttribute('aria-label', eff() === 'dark' ? 'Светлая тема' : 'Тёмная тема'); } }
  document.addEventListener('DOMContentLoaded', function () {
    paint();
    var t = document.getElementById('theme');
    if (t) t.addEventListener('click', function () { var n = eff() === 'dark' ? 'light' : 'dark'; root.setAttribute('data-theme', n); try { localStorage.setItem('bala-site-theme', n); } catch (e) {} paint(); });
    var bg = document.getElementById('burger'), nav = document.getElementById('nav');
    if (bg && nav) {
      bg.addEventListener('click', function () { var o = nav.classList.toggle('open'); bg.setAttribute('aria-expanded', o ? 'true' : 'false'); });
      nav.addEventListener('click', function (e) { if (e.target.closest('a')) { nav.classList.remove('open'); bg.setAttribute('aria-expanded', 'false'); } });
    }
    document.querySelectorAll('[data-wa]').forEach(function (el) {
      if (!CONTACT_WA) { el.hidden = true; return; }
      el.href = 'https://wa.me/' + CONTACT_WA + '?text=' + encodeURIComponent(el.getAttribute('data-wa'));
      el.target = '_blank'; el.rel = 'noopener';
    });
    document.querySelectorAll('[data-wa-off]').forEach(function (el) { el.hidden = !!CONTACT_WA; });
    var y = document.getElementById('year'); if (y) y.textContent = new Date().getFullYear();
  });
})();

'use strict';

// ── TELEGRAM INIT ──
const tg = window.Telegram?.WebApp;
if (tg) { tg.ready(); tg.expand(); }

const TG_USER  = tg?.initDataUnsafe?.user ?? null;
const TG_INIT  = tg?.initData ?? '';
const ADMIN_ID = 941957416;
const IS_ADMIN = TG_USER?.id === ADMIN_ID;
const IS_DEV   = !TG_INIT;

if (IS_ADMIN || IS_DEV) {
  document.querySelector('.nav-admin')?.classList.remove('hidden');
}

// ── НАВИГАЦИЯ ──
let curPage = 'home';

function nav(page) {
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.nav-btn').forEach(b => b.classList.toggle('active', b.dataset.page === page));
  document.getElementById(`page-${page}`)?.classList.add('active');
  curPage = page;

  if (page === 'services')   loadServices();
  if (page === 'book')       resetBook();
  if (page === 'mybookings') loadMyBookings();
  if (page === 'admin')      loadAdminBookings();
}

// ── API ──
async function api(path, opts = {}) {
  const res = await fetch(`/api${path}`, {
    ...opts,
    headers: {
      'Content-Type': 'application/json',
      'X-Telegram-Init-Data': TG_INIT,
      ...(opts.headers ?? {}),
    },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? `Ошибка ${res.status}`);
  }
  return res.json();
}

// ── UI УТИЛИТЫ ──
function showLoader() { document.getElementById('loader').classList.remove('hidden'); }
function hideLoader() { document.getElementById('loader').classList.add('hidden'); }

let _toastTimer;
function toast(msg, type = '') {
  const el = document.getElementById('toast');
  el.textContent = msg;
  el.className = `toast ${type}`;
  el.classList.remove('hidden');
  clearTimeout(_toastTimer);
  _toastTimer = setTimeout(() => el.classList.add('hidden'), 2600);
}

async function confirmDlg(msg) {
  if (tg?.showConfirm) return new Promise(r => tg.showConfirm(msg, r));
  return confirm(msg);
}

function spinner() {
  return '<div class="loading-wrap"><div class="spinner"></div></div>';
}

// ── УСЛУГИ — с разделением по полу и категориям ──
let _services = null;
let _servicesGender = null; // 'female' | 'male'

async function loadServices() {
  const list = document.getElementById('services-list');
  list.innerHTML = `
    <div class="gender-btns" style="margin-bottom:16px">
      <button class="gender-btn active" id="gbtn-female" onclick="setServicesGender('female')">
        <span class="g-icon">👩</span><span>Женский</span>
      </button>
      <button class="gender-btn" id="gbtn-male" onclick="setServicesGender('male')">
        <span class="g-icon">👨</span><span>Мужской</span>
      </button>
    </div>
    <div id="services-content">${spinner()}</div>`;
  try {
    _services ??= await api('/services');
    _servicesGender ??= 'female';
    renderServicesByGender(_servicesGender);
  } catch (e) {
    document.getElementById('services-content').innerHTML =
      `<div class="empty"><div class="empty-ico">⚠️</div><div class="empty-tit">${e.message}</div></div>`;
  }
}

function setServicesGender(gender) {
  _servicesGender = gender;
  document.getElementById('gbtn-female').classList.toggle('active', gender === 'female');
  document.getElementById('gbtn-male').classList.toggle('active', gender === 'male');
  renderServicesByGender(gender);
}

function renderServicesByGender(gender) {
  const content = document.getElementById('services-content');
  const filtered = _services.filter(s => s.gender === gender);

  const cats = {};
  filtered.forEach(s => {
    if (!cats[s.category]) cats[s.category] = [];
    cats[s.category].push(s);
  });

  if (!Object.keys(cats).length) {
    content.innerHTML = '<div class="empty"><div class="empty-ico">😭</div><div class="empty-tit">Услуг не найдено</div></div>';
    return;
  }

  content.innerHTML = Object.entries(cats).map(([cat, items]) => `
    <div class="cat-block">
      <div class="cat-title" onclick="toggleCat(this)">
        <div class="cat-title-left">
          <span class="cat-dot"></span>
          <span>${cat}</span>
          <span class="cat-count">${items.length}</span>
        </div>
        <span class="cat-arrow">▶</span>
      </div>
      <div class="cat-items collapsed">
        ${items.map(s => `
          <div class="svc-card">
            <div class="svc-info">
              <div class="svc-name">${s.name}</div>
              <div class="svc-price">${s.price}</div>
              <div class="svc-dur">⏱ ${s.duration} мин</div>
            </div>
            <button class="svc-btn" onclick="quickBook('${s.id}')">Записаться</button>
          </div>`).join('')}
      </div>
    </div>`).join('');
}

function toggleCat(el) {
  const items = el.nextElementSibling;
  const arrow = el.querySelector('.cat-arrow');
  const isOpen = !items.classList.contains('collapsed');
  items.classList.toggle('collapsed', isOpen);
  arrow.classList.toggle('open', !isOpen);
}

function quickBook(svcId) {
  nav('book');
  setTimeout(() => pickService(svcId), 150);
}

// ── ЗАПИСЬ — состояние ──
const bk = {};

function resetBook() {
  Object.keys(bk).forEach(k => delete bk[k]);
  goStep('gender');
  renderBookGender();
}

function goStep(name) {
  document.querySelectorAll('.step').forEach(s => s.classList.remove('active'));
  document.getElementById(`step-${name}`)?.classList.add('active');
}

// Шаг 0 — пол
function renderBookGender() {
  const list = document.getElementById('book-gender-list');
  list.innerHTML = `
    <button class="gender-btn" onclick="pickBookGender('female')">
      <span class="g-icon">👩</span>
      <span>Женский</span>
    </button>
    <button class="gender-btn" onclick="pickBookGender('male')">
      <span class="g-icon">👨</span>
      <span>Мужской</span>
    </button>`;
}

function pickBookGender(gender) {
  bk.gender = gender;
  goStep('category');
  loadBookCategories(gender);
}

// Шаг 1 — категория
async function loadBookCategories(gender) {
  const list = document.getElementById('book-category-list');
  list.innerHTML = spinner();
  try {
    _services ??= await api('/services');
    const cats = [...new Set(_services.filter(s => s.gender === gender).map(s => s.category))];
    list.innerHTML = cats.map(cat => `
      <div class="book-option" onclick="pickCategory('${cat.replace(/'/g, "\\'")}')">
        <div><div class="book-option-name">${cat}</div></div>
      </div>`).join('');
  } catch (e) {
    list.innerHTML = `<div class="empty"><div class="empty-ico">⚠️</div><div class="empty-tit">${e.message}</div></div>`;
  }
}

function pickCategory(cat) {
  bk.category = cat;
  goStep('service');
  loadBookServices(bk.gender, cat);
}

// Шаг 2 — услуга
async function loadBookServices(gender, category) {
  const list = document.getElementById('book-service-list');
  list.innerHTML = spinner();
  try {
    _services ??= await api('/services');
    const items = _services.filter(s => s.gender === gender && s.category === category);
    list.innerHTML = items.map(s => `
      <div class="book-option" onclick="pickService('${s.id}')">
        <div style="flex:1">
          <div class="book-option-name">${s.name}</div>
          <div class="book-option-price">${s.price} · ⏱ ${s.duration} мин</div>
        </div>
        <span class="book-option-arrow">›</span>
      </div>`).join('');
  } catch (e) {
    list.innerHTML = `<div class="empty"><div class="empty-ico">⚠️</div><div class="empty-tit">${e.message}</div></div>`;
  }
}

function pickService(id) {
  const svc = _services?.find(s => s.id === id);
  bk.service = id;
  bk.serviceName  = svc?.name  ?? id;
  bk.servicePrice = svc?.price ?? '';
  goStep('date');
  renderDates();
}

// Шаг 3 — дата
function renderDates() {
  const DAY = ['Вс','Пн','Вт','Ср','Чт','Пт','Сб'];
  const MONTHS = ['янв','фев','мар','апр','май','июн','июл','авг','сен','окт','ноя','дек'];
  const list = document.getElementById('dates-list');
  const today = new Date();
  let html = '';
  for (let i = 1; i <= 7; i++) {
    const d = new Date(today);
    d.setDate(today.getDate() + i);
    const dd   = String(d.getDate()).padStart(2,'0');
    const mm   = String(d.getMonth()+1).padStart(2,'0');
    const yyyy = d.getFullYear();
    const str  = `${dd}.${mm}.${yyyy}`;
    const isWe = d.getDay() === 0 || d.getDay() === 6;
    html += `
      <div class="date-option ${isWe ? 'date-weekend' : ''}" onclick="pickDate('${str}')">
        <div class="date-day-badge">${DAY[d.getDay()]}</div>
        <div>
          <div class="date-val">${dd} ${MONTHS[d.getMonth()]}</div>
          <div class="date-subval">${yyyy}</div>
        </div>
        <span class="book-option-arrow" style="margin-left:auto">›</span>
      </div>`;
  }
  list.innerHTML = html;
}

async function pickDate(str) {
  bk.date = str;
  goStep('time');
  const grid = document.getElementById('times-grid');
  grid.innerHTML = spinner();
  try {
    const slots = await api(`/available-times/${encodeURIComponent(str)}`);
    grid.innerHTML = slots.map(t => `
      <div class="time-slot ${t.available ? 'free' : 'busy'}"
           ${t.available ? `onclick="pickTime('${t.time}', this)"` : ''}>
        ${t.available ? '✓' : '✗'} ${t.time}
      </div>`).join('');
  } catch (e) {
    grid.innerHTML = `<p style="color:var(--hint);grid-column:1/-1">${e.message}</p>`;
  }
}

// Шаг 4 — время
function pickTime(t, el) {
  document.querySelectorAll('.time-slot.free').forEach(s => s.classList.remove('sel'));
  el.classList.add('sel');
  bk.time = t;
  tg?.HapticFeedback?.selectionChanged();
  setTimeout(() => goStep('name'), 280);
  if (TG_USER) {
    const fullName = [TG_USER.first_name, TG_USER.last_name].filter(Boolean).join(' ');
    document.getElementById('inp-name').value = fullName;
  }
}

// Шаг 5 — имя
function submitName() {
  const v = document.getElementById('inp-name').value.trim();
  if (!v) { toast('Введите имя', 'err'); return; }
  bk.name = v;
  goStep('phone');
}

// Шаг 6 — телефон
function submitPhone() {
  const v = document.getElementById('inp-phone').value.trim();
  if (!v) { toast('Введите номер телефона', 'err'); return; }
  bk.phone = v;
  renderConfirm();
  goStep('confirm');
}

// Шаг 7 — подтверждение
function renderConfirm() {
  document.getElementById('confirm-card').innerHTML = confirmRows([
    ['Услуга',   bk.serviceName,  false],
    ['Цена',     bk.servicePrice, true],
    ['Дата',     bk.date,         false],
    ['Время',    bk.time,         false],
    ['Имя',      bk.name,         false],
    ['Телефон',  bk.phone,        false],
  ]);
}

function confirmRows(rows) {
  return rows.map(([l, v, pink]) =>
    `<div class="c-row"><span class="c-lbl">${l}</span><span class="c-val${pink ? ' c-pink' : ''}">${v}</span></div>`
  ).join('');
}

async function confirmBooking() {
  showLoader();
  try {
    await api('/bookings', {
      method: 'POST',
      body: JSON.stringify({
        service:     bk.service,
        date:        bk.date,
        time:        bk.time,
        client_name: bk.name,
        phone:       bk.phone,
      }),
    });
    document.getElementById('success-card').innerHTML = confirmRows([
      ['Услуга', bk.serviceName,              false],
      ['Дата',   `${bk.date} в ${bk.time}`,   false],
      ['Адрес',  'г. Махачкала, ул. Насрутдинова 2к3', false],
    ]);
    goStep('success');
    tg?.HapticFeedback?.notificationOccurred('success');
  } catch (e) {
    toast(e.message, 'err');
  } finally {
    hideLoader();
  }
}

// ── МОИ ЗАПИСИ ──
async function loadMyBookings() {
  const list = document.getElementById('my-bookings-list');
  list.innerHTML = spinner();
  try {
    const items = await api('/my-bookings');
    if (!items.length) {
      list.innerHTML = `
        <div class="empty">
          <div class="empty-ico">😭</div>
          <div class="empty-tit">Нет предстоящих записей</div>
          <div class="empty-txt">Запишись прямо сейчас!</div>
          <button class="btn-primary" style="max-width:200px" onclick="nav('book')">📅 Записаться</button>
        </div>`;
      return;
    }
    list.innerHTML = items.map(b => `
      <div class="booking-card" id="bk-${b.id}">
        <div class="bk-header">
          <div class="bk-name">${b.service_name}</div>
          <div class="bk-id">#${b.id}</div>
        </div>
        <div class="bk-meta"><span>📅 <b>${b.date}</b></span><span>⏰ <b>${b.time}</b></span></div>
        <div class="bk-price">${b.service_price}</div>
        <button class="btn-cancel" onclick="cancelMyBooking(${b.id})">✕ Отменить запись</button>
      </div>`).join('');
  } catch (e) {
    list.innerHTML = `<div class="empty"><div class="empty-ico">⚠️</div><div class="empty-tit">${e.message}</div></div>`;
  }
}

async function cancelMyBooking(id) {
  const ok = await confirmDlg('Отменить эту запись?');
  if (!ok) return;
  showLoader();
  try {
    await api(`/my-bookings/${id}`, { method: 'DELETE' });
    document.getElementById(`bk-${id}`)?.remove();
    toast('Запись отменена', 'ok');
    tg?.HapticFeedback?.notificationOccurred('warning');
    if (!document.querySelector('.booking-card')) loadMyBookings();
  } catch (e) {
    toast(e.message, 'err');
  } finally {
    hideLoader();
  }
}

// ── АДМИНИСТРАТОР ──
function showTab(name) {
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
  document.querySelector(`.tab[onclick="showTab('${name}')"]`)?.classList.add('active');
  document.getElementById(`tab-${name}`)?.classList.add('active');
  if (name === 'bookings') loadAdminBookings();
  if (name === 'stats')    loadAdminStats();
  if (name === 'reviews')  loadAdminReviews();
}

async function loadAdminBookings() {
  const el = document.getElementById('admin-bookings');
  el.innerHTML = spinner();
  try {
    const items = await api('/admin/bookings');
    if (!items.length) {
      el.innerHTML = '<div class="empty"><div class="empty-ico">😭</div><div class="empty-tit">Записей пока нет</div></div>';
      return;
    }
    el.innerHTML = items.map(b => `
      <div class="booking-card" id="abk-${b.id}">
        <div class="bk-header">
          <div class="bk-name">${b.service_name}</div>
          <div class="bk-id">#${b.id}</div>
        </div>
        <div class="bk-meta"><span>📅 <b>${b.date}</b></span><span>⏰ <b>${b.time}</b></span></div>
        <div style="font-size:14px;margin-bottom:12px">👤 <b>${b.client_name}</b> · 📱 ${b.phone}</div>
        <button class="btn-cancel" onclick="adminCancel(${b.id})">✕ Отменить</button>
      </div>`).join('');
  } catch (e) {
    el.innerHTML = `<div class="empty"><div class="empty-ico">⚠️</div><div class="empty-tit">${e.message}</div></div>`;
  }
}

async function adminCancel(id) {
  const ok = await confirmDlg(`Отменить запись #${id}?`);
  if (!ok) return;
  showLoader();
  try {
    await api(`/admin/bookings/${id}`, { method: 'DELETE' });
    document.getElementById(`abk-${id}`)?.remove();
    toast('Запись отменена', 'ok');
  } catch (e) {
    toast(e.message, 'err');
  } finally {
    hideLoader();
  }
}

async function loadAdminStats() {
  const el = document.getElementById('admin-stats');
  el.innerHTML = spinner();
  try {
    const s = await api('/admin/stats');
    const ratingStr = s.avg_rating ? `${s.avg_rating}⭐` : '—';
    el.innerHTML = `
      <div class="stat-grid">
        <div class="stat-mini"><div class="stat-val">${s.total_bookings}</div><div class="stat-lbl">Записей</div></div>
        <div class="stat-mini"><div class="stat-val">${s.total_reviews}</div><div class="stat-lbl">Отзывов</div></div>
        <div class="stat-mini"><div class="stat-val">${ratingStr}</div><div class="stat-lbl">Рейтинг</div></div>
      </div>
      <div class="stat-block">
        <div class="stat-block-title">💅 Услуги</div>
        ${s.service_breakdown.map(r => `
          <div style="margin-bottom:14px">
            <div style="display:flex;justify-content:space-between;font-size:14px;margin-bottom:4px">
              <span>${r.service_name}</span>
              <b style="color:var(--pink)">${r.count} (${r.pct}%)</b>
            </div>
            <div class="progress-wrap"><div class="progress-fill" style="width:${r.pct}%"></div></div>
          </div>`).join('')}
      </div>
      <div class="stat-block">
        <div class="stat-block-title">⏰ Популярные часы</div>
        ${s.top_hours.map(h => `
          <div class="stat-row"><span>${h.hour}</span><span class="stat-row-right">${h.count} записей</span></div>`).join('')}
      </div>
      <div class="stat-block">
        <div class="stat-block-title">📅 По дням</div>
        ${s.day_breakdown.map(d => `
          <div class="stat-row"><span>${d.day}</span><span>${'🔥'.repeat(Math.min(d.count,5))} ${d.count}</span></div>`).join('')}
      </div>`;
  } catch (e) {
    el.innerHTML = `<div class="empty"><div class="empty-ico">⚠️</div><div class="empty-tit">${e.message}</div></div>`;
  }
}

async function loadAdminReviews() {
  const el = document.getElementById('admin-reviews');
  el.innerHTML = spinner();
  try {
    const reviews = await api('/admin/reviews');
    if (!reviews.length) {
      el.innerHTML = '<div class="empty"><div class="empty-ico">😭</div><div class="empty-tit">Отзывов пока нет</div></div>';
      return;
    }
    const total = reviews.length;
    const avg   = reviews.reduce((a, r) => a + r.stars, 0) / total;
    el.innerHTML = `
      <div class="stat-block" style="margin-bottom:16px;display:flex;justify-content:space-between;align-items:center">
        <div><div class="stat-lbl">Средняя оценка</div><div class="stat-val">${avg.toFixed(1)} ⭐</div></div>
        <div style="text-align:right"><div class="stat-lbl">Всего</div><div class="stat-val">${total}</div></div>
      </div>
      ${reviews.map(r => `
        <div class="review-card">
          <div class="review-stars">${'⭐'.repeat(r.stars)}</div>
          <div class="review-svc">${r.service_name}</div>
          <div class="review-meta">👤 ${r.client_name} · 📅 ${r.date}</div>
        </div>`).join('')}`;
  } catch (e) {
    el.innerHTML = `<div class="empty"><div class="empty-ico">⚠️</div><div class="empty-tit">${e.message}</div></div>`;
  }
}

// ── СТАРТ ──
nav('home');

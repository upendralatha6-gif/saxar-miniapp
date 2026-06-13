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

// ── ХЕЛПЕРЫ ИКОНОК / ТЕКСТА ──
// Возвращает inline-иконку из SVG-спрайта
function icon(id) { return `<svg><use href="#i-${id}"/></svg>`; }
// Убирает ведущий эмодзи из названия категории для чистого вида
function cleanCat(s) { return s.replace(/^[^\p{L}\p{N}]+/u, '').trim(); }
// Экранирование строки для вставки в onclick='...'
function esc(s) { return String(s).replace(/'/g, "\\'"); }

// ── НАВИГАЦИЯ ──
let curPage = 'home';

function nav(page) {
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.nav-btn').forEach(b => b.classList.toggle('active', b.dataset.page === page));
  document.getElementById(`page-${page}`)?.classList.add('active');
  curPage = page;
  window.scrollTo({ top: 0, behavior: 'smooth' });

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

// Унифицированные пустые/ошибочные состояния
function emptyState(ico, title, text = '', btn = '') {
  return `<div class="empty">
    <div class="empty-ico">${icon(ico)}</div>
    <div class="empty-tit">${title}</div>
    ${text ? `<div class="empty-txt">${text}</div>` : ''}
    ${btn}
  </div>`;
}
function errorState(msg) { return emptyState('alert', 'Что-то пошло не так', msg); }

// ── УСЛУГИ — разделение по полу и категориям ──
let _services = null;

// Разделы (полы), реально присутствующие в прайсе
const GENDERS = [
  { key: 'female', label: 'Женский', ico: 'venus' },
  { key: 'male',   label: 'Мужской', ico: 'mars'  },
];
function getGenders() {
  const present = new Set((_services ?? []).map(s => s.gender));
  return GENDERS.filter(g => present.has(g.key));
}

async function loadServices() {
  const list = document.getElementById('services-list');
  list.innerHTML = `<div id="services-content">${spinner()}</div>`;
  try {
    _services ??= await api('/services');
    const avail = getGenders();
    const seg = document.getElementById('services-gender-seg');
    // переключатель пола показываем только если разделов несколько
    if (avail.length > 1) {
      seg.innerHTML = avail.map((g, i) =>
        `<button class="seg-btn ${i === 0 ? 'active' : ''}" onclick="switchServicesGender('${g.key}', this)">${g.label}</button>`
      ).join('');
      seg.classList.remove('hidden');
    } else {
      seg.classList.add('hidden');
    }
    renderServicesByGender(avail[0]?.key ?? 'female');
  } catch (e) {
    document.getElementById('services-content').innerHTML = errorState(e.message);
  }
}

// Переключатель пола на странице услуг (сегмент-контрол)
function switchServicesGender(gender, btn) {
  document.querySelectorAll('#services-gender-seg .seg-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
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
    content.innerHTML = emptyState('inbox', 'В этом разделе пока нет услуг');
    return;
  }

  content.innerHTML = Object.entries(cats).map(([cat, items]) => `
    <div class="cat-block">
      <div class="cat-title" onclick="toggleCat(this)">
        <div class="cat-title-left">
          <span class="cat-dot"></span>
          <span class="cat-name">${cleanCat(cat)}</span>
          <span class="cat-count">${items.length}</span>
        </div>
        <span class="cat-arrow">${icon('chev-r')}</span>
      </div>
      <div class="cat-items collapsed">
        ${items.map(s => `
          <div class="svc-card">
            <div class="svc-info">
              <div class="svc-name">${s.name}</div>
              <div class="svc-meta">
                <span class="svc-price">${s.price}</span>
                <span class="svc-dur">${icon('clock')} ${s.duration} мин</span>
              </div>
            </div>
            <button class="svc-btn" onclick="quickBook('${esc(s.id)}')">Записаться</button>
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
  const svc = _services?.find(s => s.id === svcId);
  nav('book');
  if (svc) bk.gender = svc.gender;
  setTimeout(() => pickService(svcId), 150);
}

// ── ЗАПИСЬ — состояние ──
const bk = {};

async function resetBook() {
  Object.keys(bk).forEach(k => delete bk[k]);
  try { _services ??= await api('/services'); } catch (_) {}
  const avail = getGenders();
  // если раздел один — шаг выбора пола пропускаем
  if (avail.length <= 1) {
    bk.gender = avail[0]?.key ?? 'female';
    goStep('category');
    loadBookCategories(bk.gender);
  } else {
    goStep('gender');
    loadBookGenders();
  }
}

// Возврат с шага категории: к выбору пола либо на главную
function backFromCategory() {
  if (getGenders().length > 1) goStep('gender');
  else nav('home');
}

// Последовательность шагов записи (gender может выпадать)
const BOOK_STEPS = ['gender', 'category', 'service', 'date', 'time', 'name', 'phone'];

function goStep(name) {
  document.querySelectorAll('.step').forEach(s => s.classList.remove('active'));
  document.getElementById(`step-${name}`)?.classList.add('active');
  updateStepMeta(name);
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

// Пересчитывает «шаг N из M» и прогресс-точки с учётом пропуска выбора пола
function updateStepMeta(name) {
  const seq = getGenders().length > 1 ? BOOK_STEPS : BOOK_STEPS.filter(s => s !== 'gender');
  const idx = seq.indexOf(name);
  if (idx === -1) return;
  const stepEl = document.getElementById(`step-${name}`);
  const eb = stepEl?.querySelector('[data-step]');
  const pr = stepEl?.querySelector('[data-progress]');
  if (eb) eb.textContent = `Запись · шаг ${idx + 1} из ${seq.length}`;
  if (pr) pr.innerHTML = seq.map((_, i) => `<i class="sp-dot ${i <= idx ? 'done' : ''}"></i>`).join('');
}

// Шаг 1 — пол (раздел)
async function loadBookGenders() {
  const list = document.getElementById('book-gender-list');
  list.innerHTML = spinner();
  try {
    _services ??= await api('/services');
    const present = new Set(_services.map(s => s.gender));
    const avail = GENDERS.filter(g => present.has(g.key));
    list.innerHTML = avail.map(g => `
      <button class="gender-btn" onclick="pickGender('${g.key}')">
        <span class="g-icon">${icon(g.ico)}</span>
        <span>${g.label}</span>
      </button>`).join('');
  } catch (e) {
    list.innerHTML = errorState(e.message);
  }
}

function pickGender(gender) {
  bk.gender = gender;
  tg?.HapticFeedback?.selectionChanged();
  goStep('category');
  loadBookCategories(gender);
}

// Шаг 2 — категория
async function loadBookCategories(gender) {
  const list = document.getElementById('book-category-list');
  list.innerHTML = spinner();
  try {
    _services ??= await api('/services');
    const cats = [...new Set(_services.filter(s => s.gender === gender).map(s => s.category))];
    if (!cats.length) { list.innerHTML = emptyState('inbox', 'Нет доступных категорий'); return; }
    list.innerHTML = cats.map(cat => `
      <div class="book-option" onclick="pickCategory('${esc(cat)}')">
        <div class="book-option-icon">${icon('folder')}</div>
        <div class="book-option-body">
          <div class="book-option-name">${cleanCat(cat)}</div>
        </div>
        <span class="book-option-arrow">${icon('chev-r')}</span>
      </div>`).join('');
  } catch (e) {
    list.innerHTML = errorState(e.message);
  }
}

function pickCategory(cat) {
  bk.category = cat;
  goStep('service');
  loadBookServices(bk.gender, cat);
}

// Шаг 3 — услуга
async function loadBookServices(gender, category) {
  const list = document.getElementById('book-service-list');
  list.innerHTML = spinner();
  try {
    _services ??= await api('/services');
    const items = _services.filter(s => s.gender === gender && s.category === category);
    list.innerHTML = items.map(s => `
      <div class="book-option" onclick="pickService('${esc(s.id)}')">
        <div class="book-option-icon">${icon('spark')}</div>
        <div class="book-option-body">
          <div class="book-option-name">${s.name}</div>
          <div class="book-option-price">${s.price} <span class="svc-dur">${icon('clock')} ${s.duration} мин</span></div>
        </div>
        <span class="book-option-arrow">${icon('chev-r')}</span>
      </div>`).join('');
  } catch (e) {
    list.innerHTML = errorState(e.message);
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

// Шаг 4 — дата
function renderDates() {
  const DAY_SHORT = ['Вс','Пн','Вт','Ср','Чт','Пт','Сб'];
  const DAY_FULL  = ['Воскресенье','Понедельник','Вторник','Среда','Четверг','Пятница','Суббота'];
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
        <div class="date-day-badge">
          <span class="dd-num">${d.getDate()}</span>
          <span class="dd-day">${DAY_SHORT[d.getDay()]}</span>
        </div>
        <div>
          <div class="date-val">${DAY_FULL[d.getDay()]}</div>
          <div class="date-subval">${str}</div>
        </div>
        <span class="book-option-arrow" style="margin-left:auto">${icon('chev-r')}</span>
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
        ${t.time}
      </div>`).join('');
  } catch (e) {
    grid.innerHTML = `<p style="color:var(--ink-2);grid-column:1/-1">${e.message}</p>`;
  }
}

// Шаг 5 — время
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

// Шаг 6 — имя
function submitName() {
  const v = document.getElementById('inp-name').value.trim();
  if (!v) { toast('Введите имя', 'err'); return; }
  bk.name = v;
  goStep('phone');
}

// Шаг 7 — телефон
function submitPhone() {
  const v = document.getElementById('inp-phone').value.trim();
  if (!v) { toast('Введите номер телефона', 'err'); return; }
  bk.phone = v;
  renderConfirm();
  goStep('confirm');
}

// Подтверждение
function renderConfirm() {
  document.getElementById('confirm-card').innerHTML = confirmRows([
    ['Услуга',   bk.serviceName,  false],
    ['Стоимость',bk.servicePrice, true],
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
      ['Когда',  `${bk.date} в ${bk.time}`,   false],
      ['Адрес',  'ул. Магомеда Ярагского, 42А', false],
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
      list.innerHTML = emptyState(
        'inbox',
        'Пока нет записей',
        'Запишитесь на удобное время прямо сейчас',
        `<button class="btn-primary" style="max-width:220px;margin:0 auto" onclick="nav('book')">${icon('calendar')}Записаться</button>`
      );
      return;
    }
    list.innerHTML = items.map(b => `
      <div class="booking-card" id="bk-${b.id}">
        <div class="bk-header">
          <div class="bk-name">${b.service_name}</div>
          <div class="bk-id">№${b.id}</div>
        </div>
        <div class="bk-meta">
          <span>${icon('calendar')}<b>${b.date}</b></span>
          <span>${icon('clock')}<b>${b.time}</b></span>
        </div>
        <div class="bk-price">${b.service_price}</div>
        <button class="btn-cancel" onclick="cancelMyBooking(${b.id})">Отменить запись</button>
      </div>`).join('');
  } catch (e) {
    list.innerHTML = errorState(e.message);
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
    if (!document.querySelector('#my-bookings-list .booking-card')) loadMyBookings();
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
    if (!items.length) { el.innerHTML = emptyState('inbox', 'Записей пока нет'); return; }
    el.innerHTML = items.map(b => `
      <div class="booking-card" id="abk-${b.id}">
        <div class="bk-header">
          <div class="bk-name">${b.service_name}</div>
          <div class="bk-id">№${b.id}</div>
        </div>
        <div class="bk-meta">
          <span>${icon('calendar')}<b>${b.date}</b></span>
          <span>${icon('clock')}<b>${b.time}</b></span>
        </div>
        <div class="bk-client">
          <span>${icon('user')} <b>${b.client_name}</b></span>
          <span>${icon('phone')} ${b.phone}</span>
        </div>
        <button class="btn-cancel" onclick="adminCancel(${b.id})">Отменить запись</button>
      </div>`).join('');
  } catch (e) {
    el.innerHTML = errorState(e.message);
  }
}

async function adminCancel(id) {
  const ok = await confirmDlg(`Отменить запись №${id}?`);
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
    const ratingStr = s.avg_rating ? `${s.avg_rating}` : '—';
    el.innerHTML = `
      <div class="stat-grid">
        <div class="stat-mini"><div class="stat-val">${s.total_bookings}</div><div class="stat-lbl">Записей</div></div>
        <div class="stat-mini"><div class="stat-val">${s.total_reviews}</div><div class="stat-lbl">Отзывов</div></div>
        <div class="stat-mini"><div class="stat-val">${ratingStr}</div><div class="stat-lbl">Рейтинг</div></div>
      </div>
      <div class="stat-block">
        <div class="stat-block-title">${icon('tag')} Услуги</div>
        ${s.service_breakdown.map(r => `
          <div style="margin-bottom:14px">
            <div style="display:flex;justify-content:space-between;font-size:13.5px;margin-bottom:6px">
              <span>${r.service_name}</span>
              <b style="color:var(--brand)">${r.count} · ${r.pct}%</b>
            </div>
            <div class="progress-wrap"><div class="progress-fill" style="width:${r.pct}%"></div></div>
          </div>`).join('')}
      </div>
      <div class="stat-block">
        <div class="stat-block-title">${icon('clock')} Популярные часы</div>
        ${s.top_hours.map(h => `
          <div class="stat-row"><span>${h.hour}</span><span class="stat-row-right">${h.count} записей</span></div>`).join('')}
      </div>
      <div class="stat-block">
        <div class="stat-block-title">${icon('chart')} По дням недели</div>
        ${s.day_breakdown.map(d => `
          <div class="stat-row"><span>${d.day}</span><span class="stat-row-right">${d.count}</span></div>`).join('')}
      </div>`;
  } catch (e) {
    el.innerHTML = errorState(e.message);
  }
}

async function loadAdminReviews() {
  const el = document.getElementById('admin-reviews');
  el.innerHTML = spinner();
  try {
    const reviews = await api('/admin/reviews');
    if (!reviews.length) { el.innerHTML = emptyState('star-line', 'Отзывов пока нет'); return; }
    const total = reviews.length;
    const avg   = reviews.reduce((a, r) => a + r.stars, 0) / total;
    el.innerHTML = `
      <div class="stat-grid" style="grid-template-columns:repeat(2,1fr)">
        <div class="stat-mini"><div class="stat-val">${avg.toFixed(1)}</div><div class="stat-lbl">Средняя оценка</div></div>
        <div class="stat-mini"><div class="stat-val">${total}</div><div class="stat-lbl">Всего отзывов</div></div>
      </div>
      ${reviews.map(r => `
        <div class="review-card">
          <div class="review-stars">${'★'.repeat(r.stars)}${'☆'.repeat(5 - r.stars)}</div>
          <div class="review-svc">${r.service_name}</div>
          <div class="review-meta">${r.client_name} · ${r.date}</div>
        </div>`).join('')}`;
  } catch (e) {
    el.innerHTML = errorState(e.message);
  }
}

// ── СТАРТ ──
nav('home');

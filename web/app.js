import { sampleArticle } from './sample.js';

const $ = (id) => document.getElementById(id);
const isExtension = Boolean(globalThis.chrome?.runtime?.id);
const API = isExtension ? 'http://127.0.0.1:8765' : location.origin;
const state = { documents: [], current: null, health: null, history: [], study: null, busy: false, controller: null, settings: null, settingsBusy: false };
const initialWelcome = $('chat-log').innerHTML;
const PERSONAS = {
  whale: { name: '鲸鱼娘 · 小汐', image: './whale.png', hello: '你好呀，我是鲸鱼娘', bubble: '先读懂，再开饭～', tags: ['蓝白鲸尾', '聪明又好奇', '白米饭爱好者'], description: '在知识海里打捞线索的鲸鱼娘，偶尔有点小傲娇。喜欢把难懂的概念讲成直观的类比，遇到没有依据的地方会坦率停下来。', quote: '哼，这个知识点本鲸捞到了。先看原文，再下结论～' },
  mochi: { name: '糯米 Mochi', image: './mochi.svg', hello: '你好呀，我是糯米', bubble: '一起读懂吧！', tags: ['温柔耐心', '耳机糯米团', '慢慢拆解'], description: '一只戴着耳机的小糯米团，喜欢陪你把复杂概念一点点拆开，用简洁中文和类比解释技术。', quote: '不着急，我们一起把它读懂。' },
  senpai: { name: '糯米 · 学姐模式', image: './mochi.svg', hello: '今天，一起认真读懂', bubble: '先结论，再证据。', tags: ['严谨清晰', '工程取舍', '证据优先'], description: '糯米的严谨导师风格。先给结论，再解释工程取舍。遇到资料不足，明确指出缺少的依据。', quote: '先确认边界，再讨论方案。' },
};
const savedPersona = readLocal('mochi.persona');
if (savedPersona && PERSONAS[savedPersona]) $('persona').value = savedPersona;
let messageIndex = 0;
let toastTimer;
if (isExtension) { document.body.classList.add('extension'); $('capture-button').classList.remove('hidden'); }

function node(tag, className, text) {
  const item = document.createElement(tag);
  if (className) item.className = className;
  if (text !== undefined) item.textContent = text;
  return item;
}
function readLocal(key) { try { return localStorage.getItem(key); } catch { return null; } }
function writeLocal(key, value) { try { value === null ? localStorage.removeItem(key) : localStorage.setItem(key, value); } catch { /* Browser privacy mode can disable localStorage. */ } }
function studyKey() { return `mochi.study.${state.current?.id}.${$('persona').value}`; }
function setStatus(text, error = false) { $('status').textContent = text; $('status').className = error ? 'error' : ''; }
function toast(text, error = false) {
  document.querySelector('.toast')?.remove();
  clearTimeout(toastTimer);
  const item = node('div', `toast${error ? ' error' : ''}`, text);
  item.setAttribute('role', 'status');
  document.body.append(item);
  toastTimer = setTimeout(() => item.remove(), 5000);
  setStatus(text, error);
}

async function api(path, { method = 'GET', body, timeout = 15000, signal } = {}) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeout);
  const abort = () => controller.abort();
  if (signal?.aborted) controller.abort();
  signal?.addEventListener('abort', abort, { once: true });
  try {
    const response = await fetch(`${API}/api${path}`, {
      method, signal: controller.signal,
      headers: body === undefined ? {} : { 'Content-Type': 'application/json' },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
    if (!response.ok) {
      const payload = await response.json().catch(() => ({}));
      throw new Error(typeof payload.detail === 'string' ? payload.detail : Array.isArray(payload.detail) ? payload.detail.map((item) => item.msg).join('；') : `请求未完成（${response.status}），请检查输入或本机服务。`);
    }
    return await response.json();
  } catch (error) {
    if (error.name === 'AbortError') throw new Error('请求已停止或超时，请稍后重试。');
    if (error instanceof TypeError) throw new Error('没有连接到本机服务。请先启动 Mochi，再检查连接。');
    throw error;
  } finally { clearTimeout(timer); signal?.removeEventListener('abort', abort); }
}

function updateActions() {
  const needsDoc = ['explain-button', 'study-button', 'quiz-button', 'send-button', 'generate-cards'];
  for (const id of needsDoc) $(id).disabled = state.busy || !state.current || !state.health;
  for (const id of ['new-reading', 'change-reading', 'import-button', 'sample-button', 'delete-document', 'save-article', 'persona']) $(id).disabled = state.busy;
  $('export-button').disabled = !state.study || state.busy;
  $('stop-button').classList.toggle('hidden', !state.controller);
  $('send-button').classList.toggle('hidden', Boolean(state.controller));
  document.querySelectorAll('.doc-button').forEach((button) => { button.disabled = state.busy; });
  $('composer-note').textContent = !state.health ? '本机服务未连接 · 打开连接设置查看说明' : !state.current ? '先导入一篇文章，开始有依据的对话' : state.health.mode === 'demo' ? '演示 · 原文摘录模式 / Enter 发送' : '相关片段将发送到配置的模型服务 / Enter 发送';
  updateSettingsActions();
}

async function connect() {
  try {
    state.health = await api('/health', { timeout: 5000 });
    const live = state.health.mode === 'live';
    $('mode-badge').textContent = live ? `${state.health.model} · 已配置` : '演示 · 原文摘录';
    $('mode-badge').title = live ? `已配置模型：${state.health.model}；可用性需测试连接` : '无密钥的原文摘录演示模式';
    $('mode-badge').classList.remove('offline');
    $('connection-dot').classList.add('on');
    $('connection-info').replaceChildren(node('strong', '', live ? '已连接本机 · API 已配置' : '已连接本机 · 无密钥演示模式'), node('small', '', `模型：${state.health.model} · ${API}`));
    await refreshDocuments();
    if (!state.current) {
      const active = readLocal('mochi.active');
      if (active && state.documents.some((doc) => doc.id === active)) await selectDocument(active);
    }
    setStatus(live ? '本机服务已连接；模型可用性将在实际调用时确认。' : '演示模式已就绪，不调用外部模型。');
  } catch (error) {
    state.health = null;
    $('mode-badge').textContent = '本机服务未连接';
    $('mode-badge').classList.add('offline');
    $('connection-dot').classList.remove('on');
    $('connection-info').replaceChildren(node('strong', '', '还没有连接到本机服务'), node('small', '', `请按 README 启动服务：${API}`));
    setStatus(error.message, true);
  }
  updateActions();
}

function settingsFeedback(message, error = false) {
  $('settings-feedback').textContent = message;
  $('settings-feedback').classList.toggle('error', error);
}
function clearKeyInput() {
  $('api-key').value = '';
  $('api-key').type = 'password';
  $('toggle-api-key').textContent = '显示';
  $('toggle-api-key').setAttribute('aria-label', '显示密钥');
  $('toggle-api-key').setAttribute('aria-pressed', 'false');
}
function normalizeBase(value) { return value.trim().replace(/\/+$/, ''); }
function updateSettingsHint() {
  const saved = state.settings;
  $('api-key-state').textContent = saved?.has_api_key ? '已保存 · 留空保留' : '尚未配置';
  $('api-key').placeholder = saved?.has_api_key ? '留空保留已保存的密钥，输入新值可替换' : '输入你的 API Key';
  const changed = saved?.has_api_key && normalizeBase($('api-base').value) !== normalizeBase(saved.api_base);
  $('api-key-hint').textContent = changed ? '更换模型服务地址时，请填写对应的新密钥。旧密钥不会自动转发到另一个服务。' : '密钥只提交给本机服务，以明文保存在本机配置文件中；浏览器不持久保存，也不会回显已保存的密钥。';
}
function updateSettingsActions() {
  const disabled = state.settingsBusy || state.busy || !state.settings;
  for (const id of ['api-base', 'api-model', 'api-key', 'toggle-api-key', 'save-api-settings']) $(id).disabled = disabled;
  $('test-api').disabled = disabled || !state.settings?.has_api_key;
  $('clear-api-key').disabled = disabled || !state.settings?.has_api_key;
  $('retry-connection').disabled = state.settingsBusy;
}
function applySettings(config) {
  state.settings = config;
  $('api-base').value = config.api_base;
  $('api-model').value = config.model;
  clearKeyInput();
  updateSettingsHint();
}
async function loadSettings() {
  state.settingsBusy = true; updateSettingsActions();
  settingsFeedback('正在读取当前配置…');
  try {
    applySettings(await api('/settings'));
    settingsFeedback(state.busy ? '当前阅读请求结束后即可修改配置。' : state.settings.has_api_key ? '已保存 API 配置。填写新密钥可替换，留空会保留原值。' : '尚未配置密钥，当前可使用原文摘录演示。');
  } catch (error) {
    state.settings = null;
    settingsFeedback(error.message, true);
  } finally { state.settingsBusy = false; updateSettingsActions(); }
}
async function openSettings() {
  clearKeyInput();
  if (!$('settings-dialog').open) $('settings-dialog').showModal();
  await loadSettings();
}
async function saveSettings(event) {
  event.preventDefault();
  if (state.settingsBusy || state.busy || !state.settings) return;
  const body = { api_base: normalizeBase($('api-base').value), model: $('api-model').value.trim() };
  const newKey = $('api-key').value.trim();
  if (newKey) body.api_key = newKey;
  state.settingsBusy = true; updateSettingsActions();
  settingsFeedback('正在保存到本机…');
  try {
    applySettings(await api('/settings', { method: 'PUT', body }));
    state.history = [];
    await connect();
    settingsFeedback(state.settings.mode === 'live' ? '配置已保存并生效。可点击「测试已保存配置」检查连接。' : '配置已保存，当前为无密钥演示模式。');
    toast('API 设置已保存，无需重启。');
  } catch (error) { settingsFeedback(error.message, true); }
  finally { state.settingsBusy = false; updateSettingsActions(); }
}
async function testSettings() {
  if (state.settingsBusy || state.busy || !state.settings?.has_api_key) return;
  const dirty = $('api-key').value.trim() || normalizeBase($('api-base').value) !== normalizeBase(state.settings.api_base) || $('api-model').value.trim() !== state.settings.model;
  if (dirty) { settingsFeedback('请先保存修改，再测试已保存配置。', true); return; }
  state.settingsBusy = true; updateSettingsActions();
  $('test-api').textContent = '正在测试…';
  settingsFeedback('正在检查鉴权和模型列表，不发送文章、不生成内容…');
  try {
    const result = await api('/settings/test', { method: 'POST', timeout: 15000 });
    settingsFeedback(result.message, !result.ok);
  } catch (error) { settingsFeedback(error.message, true); }
  finally { state.settingsBusy = false; $('test-api').textContent = '测试已保存配置'; updateSettingsActions(); }
}
async function clearAPIKey() {
  if (state.settingsBusy || state.busy || !state.settings?.has_api_key || !confirm('清除本机保存的 API 密钥并返回原文摘录演示模式？')) return;
  state.settingsBusy = true; updateSettingsActions();
  settingsFeedback('正在清除密钥…');
  try {
    applySettings(await api('/settings', { method: 'PUT', body: { api_base: state.settings.api_base, model: state.settings.model, clear_api_key: true } }));
    state.history = [];
    await connect();
    settingsFeedback('密钥已清除，已返回原文摘录演示模式。');
    toast('密钥已清除。');
  } catch (error) { settingsFeedback(error.message, true); }
  finally { state.settingsBusy = false; updateSettingsActions(); }
}

async function refreshDocuments() {
  state.documents = (await api('/documents')).documents;
  $('doc-count').textContent = state.documents.length;
  $('document-list').replaceChildren();
  if (!state.documents.length) $('document-list').append(node('p', 'muted empty-small', '还没有文章，开始第一篇吧。'));
  for (const doc of state.documents) {
    const button = node('button', `doc-button${doc.id === state.current?.id ? ' selected' : ''}`);
    button.append(node('span', '', doc.title));
    button.title = doc.title;
    button.addEventListener('click', () => selectDocument(doc.id).catch((error) => toast(error.message, true)));
    $('document-list').append(button);
  }
  updateActions();
}

async function selectDocument(id) {
  if (state.busy) return;
  const doc = await api(`/documents/${encodeURIComponent(id)}`);
  state.current = doc;
  state.history = [];
  writeLocal('mochi.active', doc.id);
  $('source-empty').classList.add('hidden');
  $('source-article').classList.remove('hidden');
  $('delete-document').classList.remove('hidden');
  $('source-state').textContent = `${doc.chunk_count} 个原文片段`;
  $('source-meta').textContent = '点击回答中的引用编号，可定位原文';
  renderArticle(doc);
  resetChat();
  loadSavedStudy();
  showView('read');
  await refreshDocuments();
  setStatus(`已打开「${doc.title}」。`);
}

function renderArticle(doc) {
  const article = $('source-article');
  article.replaceChildren(node('h2', '', doc.title));
  const origin = node('div', 'article-origin');
  if (safeURL(doc.url)) { const link = node('a', '', new URL(doc.url).hostname + ' ↗'); link.href = doc.url; link.target = '_blank'; link.rel = 'noopener noreferrer'; origin.append(link); }
  else origin.append(node('span', '', '本地导入的文本'));
  origin.append(node('span', '', '·'), node('span', '', `${doc.chunk_count} 个片段`));
  article.append(origin);
  for (const chunk of doc.chunks) {
    const block = node('div', 'article-chunk'); block.dataset.sourceId = chunk.id;
    for (const line of chunk.text.split(/\n\s*\n/)) {
      block.append(node('p', `article-paragraph${/^\d{2}\s*\//.test(line.trim()) ? ' section-title' : ''}`, line.trim()));
    }
    article.append(block);
  }
}
function safeURL(value) { try { return ['https:', 'http:'].includes(new URL(value).protocol); } catch { return false; } }
function personaConfig() { return PERSONAS[$('persona').value]; }
function applyPersona() {
  const persona = personaConfig();
  document.body.dataset.persona = $('persona').value;
  $('persona-name').textContent = persona.name;
  $('persona-avatar').src = persona.image;
  $('persona-avatar').alt = persona.name;
  const welcome = document.querySelector('.welcome');
  if (welcome) {
    welcome.querySelector('.hero-mochi img').src = persona.image;
    welcome.querySelector('.hero-mochi img').alt = `${persona.name}角色立绘`;
    welcome.querySelector('h3').textContent = persona.hello + ' ~';
    welcome.querySelector('.bubble').textContent = persona.bubble;
    welcome.querySelector('.profile-link').addEventListener('click', openCharacter);
  }
}
function openCharacter() {
  const persona = personaConfig();
  $('character-title').textContent = persona.name;
  $('character-image').src = persona.image;
  $('character-image').alt = persona.name;
  $('character-description').textContent = persona.description;
  $('character-quote').textContent = persona.quote;
  $('character-tags').replaceChildren(...persona.tags.map((tag) => node('span', '', tag)));
  $('character-dialog').showModal();
}
function resetChat() { $('chat-log').innerHTML = initialWelcome; applyPersona(); }
function showView(view) {
  $('reader-view').classList.toggle('hidden', view !== 'read');
  $('cards-view').classList.toggle('hidden', view !== 'cards');
  $('nav-read').classList.toggle('active', view === 'read');
  $('nav-cards').classList.toggle('active', view === 'cards');
}
function openImport() { if (!state.busy) $('import-dialog').showModal(); }
function fillImport(article) { $('article-title').value = article.title; $('article-url').value = article.url; $('article-text').value = article.text; }
async function importArticle(article) {
  state.busy = true; updateActions();
  setStatus('正在把文章保存到本机…');
  try {
    const doc = await api('/documents', { method: 'POST', body: article });
    state.busy = false;
    await selectDocument(doc.id);
    $('import-dialog').close();
    $('import-form').reset();
    toast('文章已导入，和糯米一起读吧。');
  } finally { state.busy = false; updateActions(); }
}

function newMessage(role, text = '') {
  const wrapper = node('div', `message ${role}`);
  if (role === 'assistant') {
    const label = node('div', 'message-label');
    const avatar = node('img'); avatar.src = personaConfig().image; avatar.alt = '';
    label.append(avatar, node('span', '', personaConfig().name));
    wrapper.append(label);
  }
  const body = node('div', 'message-body', text);
  wrapper.append(body);
  $('chat-log').append(wrapper);
  return { wrapper, body };
}
function scrollChat() { $('chat-log').scrollTop = $('chat-log').scrollHeight; }
function citationButton(id, sources, prefix) {
  const button = node('button', 'citation-button', `[${id}]`);
  button.title = '定位原文并展开引用';
  button.addEventListener('click', () => {
    const detail = document.getElementById(`${prefix}-sources`);
    if (detail) detail.open = true;
    const source = document.getElementById(`${prefix}-${id}`);
    source?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    const chunk = Array.from(document.querySelectorAll('.article-chunk')).find((item) => item.dataset.sourceId === id);
    if (chunk) {
      chunk.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      chunk.classList.add('highlighted');
      setTimeout(() => chunk.classList.remove('highlighted'), 2500);
    }
  });
  return button;
}
function renderCitedText(body, text, sources, prefix) {
  body.replaceChildren();
  const valid = new Set(sources.map((source) => source.id));
  for (const piece of text.split(/(\[S\d+\])/g)) {
    const id = piece.slice(1, -1);
    body.append(valid.has(id) && /^\[S\d+\]$/.test(piece) ? citationButton(id, sources, prefix) : document.createTextNode(piece));
  }
}
function sourcesDetails(sources, prefix) {
  const details = node('details', 'source-citations'); details.id = `${prefix}-sources`;
  details.append(node('summary', '', `查看 ${sources.length} 个原文片段`));
  for (const source of sources) {
    const block = node('div', 'source-citation'); block.id = `${prefix}-${source.id}`;
    block.append(node('strong', '', `[${source.id}] `), document.createTextNode(source.text));
    if (safeURL(source.url)) { const link = node('a', '', '打开原文 ↗'); link.href = source.url; link.target = '_blank'; link.rel = 'noopener noreferrer'; block.append(link); }
    details.append(block);
  }
  return details;
}

/** Parse SSE incrementally, including CRLF boundaries and split UTF-8 characters. */
async function consumeSSE(response, onEvent) {
  if (!response.body) throw new Error('浏览器未提供流式响应，请换用较新的 Chrome。');
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  let terminal = false;
  function dispatch(frame) {
    let event = 'message'; const lines = [];
    for (const line of frame.split(/\r?\n/)) {
      if (line.startsWith('event:')) event = line.slice(6).trim();
      if (line.startsWith('data:')) lines.push(line.slice(5).trimStart());
    }
    if (!lines.length) return;
    const data = JSON.parse(lines.join('\n'));
    onEvent(event, data);
    if (event === 'done' || event === 'error') terminal = true;
  }
  try {
    while (true) {
      const { value, done } = await reader.read();
      buffer += decoder.decode(value, { stream: !done });
      let boundary;
      while ((boundary = /\r?\n\r?\n/.exec(buffer))) {
        dispatch(buffer.slice(0, boundary.index));
        buffer = buffer.slice(boundary.index + boundary[0].length);
      }
      if (done) break;
    }
    if (buffer.trim()) dispatch(buffer);
    if (!terminal) throw new Error('响应提前结束，请重试。');
  } finally { reader.releaseLock(); }
}

async function ask(question) {
  if (state.busy || !state.current) return;
  question = question.trim();
  if (question.length < 2) { toast('请至少输入两个字。'); return; }
  showView('read');
  if (!state.history.length) $('chat-log').replaceChildren();
  newMessage('user', question);
  const answer = newMessage('assistant', '正在寻找原文依据…');
  answer.body.classList.add('typing');
  const prefix = `message-${++messageIndex}`;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 100000);
  state.busy = true; state.controller = controller; updateActions();
  $('question').value = '';
  let text = ''; let sources = []; let doneData = null;
  setStatus('正在检索相关片段…'); scrollChat();
  try {
    const response = await fetch(`${API}/api/chat`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, signal: controller.signal, body: JSON.stringify({ document_id: state.current.id, question, persona: $('persona').value, history: state.history.slice(-8) }) });
    if (!response.ok) {
      const data = await response.json().catch(() => ({}));
      throw new Error(typeof data.detail === 'string' ? data.detail : `请求未完成（${response.status}）。`);
    }
    await consumeSSE(response, (event, data) => {
      if (event === 'sources') { sources = data.sources; setStatus(`找到 ${sources.length} 个相关片段，正在${data.mode === 'demo' ? '整理原文' : '生成讲解'}…`); }
      else if (event === 'token') { text += data.text; answer.body.classList.remove('typing'); answer.body.textContent = text; scrollChat(); }
      else if (event === 'error') throw new Error(data.message);
      else if (event === 'done') doneData = data;
    });
    renderCitedText(answer.body, text, sources, prefix);
    if (sources.length) answer.wrapper.append(sourcesDetails(sources, prefix));
    const footer = node('div', 'message-footer');
    footer.append(node('span', '', doneData?.mode === 'demo' ? '演示 · 原文摘录' : state.health?.model || '在线模型'), node('span', '', '·'), node('span', '', `${((doneData?.elapsed_ms || 0) / 1000).toFixed(1)}s`));
    if (doneData?.citations?.length) footer.append(node('span', '', doneData.grounded ? '· 引用编号已校验' : '· 引用编号需核对'));
    answer.wrapper.append(footer);
    state.history.push({ role: 'user', content: question }, { role: 'assistant', content: text.slice(0, 4000) || '资料不足。' });
    state.history = state.history.slice(-8);
    setStatus('已完成。点击引用编号，可以核对原文。');
  } catch (error) {
    const reason = error.name === 'AbortError' ? '已停止本次回答。' : error instanceof TypeError ? '连接中断，请检查本机服务。' : error.message;
    answer.body.classList.remove('typing');
    answer.wrapper.classList.add('error');
    answer.body.textContent = text ? `${text}\n\n—— ${reason}（以上为未完成的回答）` : reason;
    setStatus(reason, true);
  } finally {
    clearTimeout(timer); state.busy = false; state.controller = null; updateActions(); scrollChat();
  }
}

function loadSavedStudy() {
  let saved = null;
  try { saved = JSON.parse(readLocal(studyKey())); } catch { /* Invalid cache is ignored. */ }
  state.study = saved && Array.isArray(saved.cards) && Array.isArray(saved.quiz) && Array.isArray(saved.sources) ? saved : null;
  renderStudy(); updateActions();
}
async function generateStudy(force = false) {
  showView('cards');
  if (state.study && !force) { renderStudy(); return; }
  if (!state.current || state.busy) return;
  state.busy = true; updateActions();
  $('study-content').replaceChildren(node('div', 'panel busy-skeleton', `${personaConfig().name}正在整理学习卡和小测，请稍等…`));
  setStatus('正在整理学习卡…');
  try {
    state.study = await api('/study', { method: 'POST', body: { document_id: state.current.id, persona: $('persona').value }, timeout: 90000 });
    writeLocal(studyKey(), JSON.stringify(state.study));
    renderStudy();
    toast('学习卡整理好了，做个小测巩固一下吧。');
  } catch (error) { renderStudy(); toast(error.message, true); }
  finally { state.busy = false; updateActions(); }
}
function renderStudy() {
  $('card-count').textContent = state.study?.cards.length || 0;
  $('study-mode').textContent = state.study ? state.study.mode === 'demo' ? '演示 · 摘录卡与原文填空' : '在线模型 · 生成内容请核对' : '尚未生成';
  if (!state.study) {
    const empty = node('div', 'study-empty panel');
    const image = node('img'); image.src = personaConfig().image; image.alt = '';
    empty.append(image, node('h3', '', '知识还在路上'), node('p', '', '导入文章后，生成你的第一组学习卡。'));
    $('study-content').replaceChildren(empty); return;
  }
  const data = state.study; const content = $('study-content'); content.replaceChildren();
  content.append(node('h2', 'study-heading', state.current.title));
  const cards = node('div', 'study-cards');
  data.cards.forEach((card, index) => {
    const item = node('section', 'study-card panel');
    item.append(node('div', 'card-number', String(index + 1).padStart(2, '0')), node('h3', '', card.title), node('p', '', card.body), citationButton(card.source_id, data.sources, 'study'));
    cards.append(item);
  });
  content.append(cards, node('h2', 'study-heading', '小测一下，你掌握了吗？'));
  const quizzes = node('div', 'quiz-list');
  data.quiz.forEach((quiz, index) => {
    const item = node('section', 'quiz-card panel');
    item.append(node('h3', '', `${String(index + 1).padStart(2, '0')} / ${quiz.question}`));
    const options = node('div', 'quiz-options'); const buttons = [];
    quiz.options.forEach((option, number) => {
      const button = node('button', 'quiz-option', `${String.fromCharCode(65 + number)}. ${option}`);
      buttons.push(button);
      button.addEventListener('click', () => {
        buttons.forEach((choice, idx) => { choice.disabled = true; if (idx === quiz.answer) choice.classList.add('correct'); });
        if (number !== quiz.answer) button.classList.add('wrong');
        const feedback = node('div', 'quiz-feedback', `${number === quiz.answer ? '✓ 答对啦！' : `再核对一下原文，正确选项是 ${String.fromCharCode(65 + quiz.answer)}。`}\n${quiz.explanation} `);
        feedback.append(citationButton(quiz.source_id, data.sources, 'study'));
        item.append(feedback);
      });
      options.append(button);
    });
    item.append(options); quizzes.append(item);
  });
  content.append(quizzes, sourcesDetails(data.sources, 'study'), node('p', 'study-footnote', '引用编号校验只表示来源存在。学习卡缓存于当前浏览器，可导出备份；删除文章会清除关联缓存。'));
}
function exportMarkdown() {
  if (!state.study || !state.current) return;
  const data = state.study;
  const lines = [`# ${state.current.title}`, '', `模式：${data.mode === 'demo' ? '演示 · 原文摘录' : '在线模型生成'}`, ...(state.current.url ? [`来源：${state.current.url}`] : []), '', '## 学习卡', ''];
  data.cards.forEach((card, i) => lines.push(`### ${i + 1}. ${card.title}`, '', `${card.body} [${card.source_id}]`, ''));
  lines.push('## 自测', '');
  data.quiz.forEach((quiz, i) => lines.push(`### ${i + 1}. ${quiz.question}`, '', ...quiz.options.map((option, n) => `${String.fromCharCode(65 + n)}. ${option}`), '', `答案：${String.fromCharCode(65 + quiz.answer)}。${quiz.explanation} [${quiz.source_id}]`, ''));
  lines.push('## 原文片段', '');
  data.sources.forEach((source) => lines.push(`### [${source.id}]`, '', source.text, ''));
  lines.push('---', '由 Mochi Reader 整理。引用合法不等于事实正确，请核对原文。');
  const url = URL.createObjectURL(new Blob([lines.join('\n')], { type: 'text/markdown;charset=utf-8' }));
  const link = node('a'); link.href = url; link.download = `mochi-${state.current.title.replace(/[<>:"/\\|?*\u0000-\u001f]/g, '_').slice(0, 70)}.md`; document.body.append(link); link.click(); link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
  toast('学习笔记已导出。');
}

async function capturePage() {
  try {
    const [tab] = await chrome.tabs.query({ active: true, lastFocusedWindow: true });
    if (!tab?.id) throw new Error('请先切换到要阅读的网页。');
    const [result] = await chrome.scripting.executeScript({ target: { tabId: tab.id }, func: () => {
      const selected = window.getSelection()?.toString().trim();
      const candidate = document.querySelector('article') || document.querySelector('main') || document.body;
      // Preserve paragraph and code-block boundaries before extracting text.
      const clone = candidate.cloneNode(true);
      clone.querySelectorAll('script,style,nav,header,footer,aside,form,button,input,textarea,select,[hidden],[aria-hidden="true"]').forEach((item) => item.remove());
      clone.querySelectorAll('p,div,section,article,h1,h2,h3,h4,h5,h6,pre,blockquote,li,tr').forEach((block) => { block.prepend('\n\n'); block.append('\n\n'); });
      clone.querySelectorAll('br').forEach((br) => br.replaceWith('\n'));
      const content = selected || clone.textContent.replace(/[\t ]+/g, ' ').replace(/\n\s*\n/g, '\n\n').trim();
      return { title: document.title.slice(0, 200), url: location.href.split('#')[0], text: content.slice(0, 80000), truncated: content.length > 80000 };
    } });
    if (!result?.result?.text || result.result.text.length < 30) throw new Error('可读内容太少，请选中一段正文，或手动粘贴。');
    fillImport(result.result);
    toast(result.result.truncated ? '正文超过 8 万字，已截取前 8 万字；请检查后导入。' : '已填入当前页面内容，请检查后导入。');
  } catch (error) {
    toast(error.message.includes('Cannot access') || error.message.includes('permission') ? '无法读取此页面。请在普通网页点击插件图标后重试，或手动粘贴。' : error.message, true);
  }
}

$('new-reading').addEventListener('click', openImport);
$('change-reading').addEventListener('click', openImport);
$('import-button').addEventListener('click', openImport);
$('fill-sample').addEventListener('click', () => fillImport(sampleArticle));
$('sample-button').addEventListener('click', () => importArticle(sampleArticle).catch((error) => toast(error.message, true)));
$('import-form').addEventListener('submit', (event) => { event.preventDefault(); importArticle({ title: $('article-title').value.trim(), url: $('article-url').value.trim(), text: $('article-text').value.trim() }).catch((error) => toast(error.message, true)); });
$('chat-form').addEventListener('submit', (event) => { event.preventDefault(); ask($('question').value); });
$('question').addEventListener('keydown', (event) => { if (event.key === 'Enter' && !event.shiftKey && !event.isComposing) { event.preventDefault(); if (!$('send-button').disabled) ask($('question').value); } });
$('explain-button').addEventListener('click', () => ask('请讲解这篇文章的重点，给出原文引用，并说明容易误解的地方。'));
$('study-button').addEventListener('click', () => generateStudy());
$('quiz-button').addEventListener('click', () => generateStudy());
$('generate-cards').addEventListener('click', () => generateStudy(true));
$('export-button').addEventListener('click', exportMarkdown);
$('nav-read').addEventListener('click', () => showView('read'));
$('mobile-read').addEventListener('click', () => showView('read'));
$('nav-cards').addEventListener('click', () => showView('cards'));
$('mobile-cards').addEventListener('click', () => showView('cards'));
$('settings-button').addEventListener('click', openSettings);
$('help-button').addEventListener('click', openSettings);
$('retry-connection').addEventListener('click', async () => { await connect(); if (!state.settings) await loadSettings(); });
$('settings-form').addEventListener('submit', saveSettings);
$('test-api').addEventListener('click', testSettings);
$('clear-api-key').addEventListener('click', clearAPIKey);
$('api-base').addEventListener('input', updateSettingsHint);
$('toggle-api-key').addEventListener('click', () => { const show = $('api-key').type === 'password'; $('api-key').type = show ? 'text' : 'password'; $('toggle-api-key').textContent = show ? '隐藏' : '显示'; $('toggle-api-key').setAttribute('aria-label', show ? '隐藏密钥' : '显示密钥'); $('toggle-api-key').setAttribute('aria-pressed', String(show)); });
$('settings-dialog').addEventListener('close', clearKeyInput);
$('capture-button').addEventListener('click', capturePage);
$('stop-button').addEventListener('click', () => state.controller?.abort());
$('persona').addEventListener('change', () => { state.history = []; writeLocal('mochi.persona', $('persona').value); resetChat(); loadSavedStudy(); });
$('delete-document').addEventListener('click', async () => {
  if (!state.current || state.busy || !confirm('删除这篇本地文章和当前浏览器中的关联学习卡？')) return;
  const id = state.current.id;
  try {
    await api(`/documents/${encodeURIComponent(id)}`, { method: 'DELETE' });
    for (const persona of ['whale', 'mochi', 'senpai']) writeLocal(`mochi.study.${id}.${persona}`, null);
    writeLocal('mochi.active', null);
    state.current = null; state.study = null; state.history = [];
    $('source-empty').classList.remove('hidden'); $('source-article').classList.add('hidden'); $('source-article').replaceChildren(); $('delete-document').classList.add('hidden');
    $('source-state').textContent = '等待导入'; $('source-meta').textContent = '支持粘贴文本 / 浏览器插件读取当前页'; resetChat(); renderStudy(); await refreshDocuments(); toast('本地文章已删除。');
  } catch (error) { toast(error.message, true); }
});
document.querySelectorAll('[data-close]').forEach((button) => button.addEventListener('click', () => button.closest('dialog').close()));
document.querySelectorAll('dialog').forEach((dialog) => dialog.addEventListener('click', (event) => { if (event.target === dialog) { const box = dialog.getBoundingClientRect(); if (event.clientX < box.left || event.clientX > box.right || event.clientY < box.top || event.clientY > box.bottom) dialog.close(); } }));
applyPersona();
updateActions();
connect();

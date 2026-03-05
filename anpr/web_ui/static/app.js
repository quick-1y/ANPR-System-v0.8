let config = null;
let subscriberId = null;
let pollTimer = null;

async function loadConfig() {
  const response = await fetch('/api/config');
  config = await response.json();
}

async function fetchJson(url, options = {}) {
  const response = await fetch(url, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || 'request_failed');
  }
  return data;
}

function renderChannels(rows) {
  const tbody = document.querySelector('#channelsTable tbody');
  tbody.innerHTML = '';
  for (const row of rows) {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${row.channel_id}</td>
      <td>${row.name}</td>
      <td>${row.source}</td>
      <td>${row.status}</td>
      <td>${row.video_profile || '-'}</td>
    `;
    tbody.appendChild(tr);
  }
}

function renderEvents(events) {
  const container = document.getElementById('eventsContainer');
  for (const event of events.reverse()) {
    const card = document.createElement('div');
    card.className = 'card';
    card.innerHTML = `
      <div><strong>${event.plate}</strong> (${(event.confidence * 100).toFixed(1)}%)</div>
      <div>Канал: ${event.channel_id}</div>
      <div>Время: ${new Date(event.timestamp_utc).toLocaleTimeString()}</div>
    `;
    container.prepend(card);
  }
  while (container.children.length > 40) {
    container.removeChild(container.lastChild);
  }
}

async function refreshChannels() {
  const channels = await fetchJson(`${config.core_base_url}/channels`);
  const streams = await fetchJson(`${config.video_base_url}/video/streams`);
  const streamMap = new Map((streams.items || []).map((item) => [item.stream_id, item.selected_profile]));
  const rows = (channels.items || []).map((item) => ({
    ...item,
    video_profile: streamMap.get(item.channel_id),
  }));
  renderChannels(rows);
}

async function subscribeEvents() {
  const payload = await fetchJson(`${config.events_base_url}/events/subscribe`, { method: 'POST' });
  subscriberId = payload.subscriber_id;
  document.getElementById('subscriberInfo').textContent = `Подписка активна: ${subscriberId.slice(0, 8)}...`;
  if (pollTimer) {
    clearInterval(pollTimer);
  }
  pollTimer = setInterval(pollEvents, 1000);
}

async function pollEvents() {
  if (!subscriberId) {
    return;
  }
  const payload = await fetchJson(`${config.events_base_url}/events/poll?subscriber_id=${subscriberId}&limit=25`);
  if (payload.items && payload.items.length) {
    renderEvents(payload.items);
  }
}

async function createChannelAndStream(formData) {
  const channel = {
    id: formData.get('id'),
    name: formData.get('name'),
    source: formData.get('source'),
    roi: { enabled: formData.get('roi_enabled') === 'on' },
  };

  await fetchJson(`${config.core_base_url}/channels`, {
    method: 'POST',
    body: JSON.stringify(channel),
  });

  await fetchJson(`${config.video_base_url}/video/streams`, {
    method: 'POST',
    body: JSON.stringify({
      stream_id: channel.id,
      source: channel.source,
      profile: formData.get('video_profile'),
    }),
  });
}

window.addEventListener('DOMContentLoaded', async () => {
  try {
    await loadConfig();
    document.getElementById('refreshChannelsBtn').addEventListener('click', refreshChannels);
    document.getElementById('subscribeBtn').addEventListener('click', subscribeEvents);

    document.getElementById('channelForm').addEventListener('submit', async (event) => {
      event.preventDefault();
      const status = document.getElementById('formStatus');
      status.textContent = '';
      try {
        const formData = new FormData(event.target);
        await createChannelAndStream(formData);
        status.textContent = 'Канал и видеопоток созданы';
        await refreshChannels();
      } catch (error) {
        status.textContent = `Ошибка: ${error.message}`;
      }
    });

    await refreshChannels();
  } catch (error) {
    document.getElementById('formStatus').textContent = `Ошибка инициализации: ${error.message}`;
  }
});

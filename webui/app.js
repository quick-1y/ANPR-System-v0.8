const channelsBox = document.getElementById('channels');
const eventsBox = document.getElementById('events');
const form = document.getElementById('add-channel-form');

async function fetchChannels() {
  const response = await fetch('/api/channels');
  const channels = await response.json();
  channelsBox.innerHTML = '';
  for (const channel of channels) {
    const card = document.createElement('div');
    card.className = 'card';
    card.innerHTML = `
      <h3>${channel.name}</h3>
      <img id="snap-${channel.id}" src="/api/channels/${channel.id}/snapshot?t=${Date.now()}" alt="${channel.name}" />
      <div class="meta"><span>Источник: ${channel.source}</span><span>ID: ${channel.id}</span></div>
      <button data-id="${channel.id}">Удалить</button>
    `;
    card.querySelector('button').onclick = async () => {
      await fetch(`/api/channels/${channel.id}`, { method: 'DELETE' });
      fetchChannels();
    };
    channelsBox.appendChild(card);
  }
}

setInterval(() => {
  document.querySelectorAll('img[id^="snap-"]').forEach((img) => {
    img.src = img.src.split('?')[0] + '?t=' + Date.now();
  });
}, 1000);

form.onsubmit = async (e) => {
  e.preventDefault();
  const name = document.getElementById('channel-name').value;
  const source = document.getElementById('channel-source').value;
  await fetch('/api/channels', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name, source, roi: {} }),
  });
  form.reset();
  fetchChannels();
};

const eventSource = new EventSource('/api/events/stream');
eventSource.onmessage = (msg) => {
  const items = JSON.parse(msg.data);
  for (const event of items.reverse()) {
    const row = document.createElement('div');
    row.className = 'event';
    row.textContent = `[${new Date(event.timestamp * 1000).toLocaleTimeString()}] ${event.channel}: ${event.plate} (${event.confidence.toFixed(2)})`;
    eventsBox.prepend(row);
  }
};

fetchChannels();

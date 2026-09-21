(() => {
  let session = '';
  let lastEvent = 0;
  let pendingFiles = [];
  let selectedBookmarks = [];
  let recorder = null;
  let recordedChunks = [];
  let refreshing = false;
  let humanActive = false;
  let disconnected = false;
  let waiting = false;
  let audioContext = null;
  let refreshTimer = null;
  let heartbeatTimer = null;
  const transcript = document.querySelector('#transcript');
  const request = document.querySelector('#request');
  const notice = document.querySelector('#notice');
  const sendButton = document.querySelector('#send');

  function registerHumanActivity() {
    humanActive = true;
    if (!audioContext) {
      const AudioContext = window.AudioContext || window.webkitAudioContext;
      if (AudioContext) audioContext = new AudioContext();
    } else if (audioContext.state === 'suspended') {
      audioContext.resume().catch(() => {});
    }
  }

  function ding() {
    if (!audioContext) return;
    const oscillator = audioContext.createOscillator();
    const gain = audioContext.createGain();
    oscillator.frequency.value = 880;
    gain.gain.setValueAtTime(0.12, audioContext.currentTime);
    gain.gain.exponentialRampToValueAtTime(
      0.001, audioContext.currentTime + 0.18
    );
    oscillator.connect(gain).connect(audioContext.destination);
    oscillator.start();
    oscillator.stop(audioContext.currentTime + 0.18);
  }

  function disconnect(message = 'Zeno si è disconnesso per inattività.') {
    if (disconnected) return;
    disconnected = true;
    clearInterval(refreshTimer);
    clearInterval(heartbeatTimer);
    request.disabled = true;
    sendButton.disabled = true;
    document.querySelector('#record').disabled = true;
    document.querySelector('#upload-file').disabled = true;
    notice.textContent = `[${message}]`;
    document.querySelector('#status').textContent = 'Zeno disconnesso';
  }

  async function api(action, options = {}) {
    const method = options.method || 'GET';
    let url = `./?action=${encodeURIComponent(action)}`;
    if (session) url += `&session=${session}`;
    if (options.query) url += `&${options.query}`;
    const response = await fetch(url, {
      method,
      body: options.body,
      credentials: 'same-origin',
      keepalive: options.keepalive || false,
    });
    const data = await response.json();
    if (!response.ok || data.error) {
      if (response.status === 401) disconnect(data.error || 'Sessione web chiusa.');
      throw new Error(data.error || `HTTP ${response.status}`);
    }
    return data;
  }

  function eventNode(event) {
    const node = document.createElement('article');
    node.className = `event ${event.event_type}`;
    node.dataset.id = event.id;
    const meta = document.createElement('span');
    meta.className = 'meta';
    const speaker = event.event_type === 'user' ? (event.user_name || 'Utente') : 'Zeno';
    const labels = {
      user: 'richiesta',
      commentary: 'attività in corso',
      files: 'file coinvolti',
      diff: 'modifiche',
      artifact: 'contenuto da aprire',
      final: 'risposta',
      spontaneous: 'iniziativa',
      system: 'sistema',
    };
    meta.textContent = `${speaker} · ${event.created_at} · ${labels[event.event_type] || event.event_type}`;
    const body = document.createElement('div');
    if (event.event_type === 'artifact') {
      const file = JSON.parse(event.body);
      const open = document.createElement('button');
      open.type = 'button';
      open.className = 'artifact-open';
      open.textContent = `Apri ${file.name}`;
      open.addEventListener('click', () => openViewer(file));
      body.append(open);
    } else {
      body.textContent = event.body;
    }
    const bookmark = document.createElement('button');
    bookmark.className = `bookmark${event.bookmarked ? ' active' : ''}`;
    bookmark.type = 'button';
    bookmark.textContent = '◆';
    bookmark.title = 'Segnalibro';
    bookmark.addEventListener('click', async () => {
      const form = new FormData();
      form.append('event_id', event.id);
      const result = await api('bookmark', {method: 'POST', body: form});
      bookmark.classList.toggle('active', result.bookmarked);
      await refresh(true);
    });
    node.append(meta, body, bookmark);
    return node;
  }

  function renderBookmarks(items) {
    const box = document.querySelector('#bookmarks');
    box.replaceChildren();
    for (const item of items) {
      const row = document.createElement('button');
      row.type = 'button';
      row.className = 'bookmark-row';
      row.dataset.id = item.event_id;
      row.textContent = `${item.created_at} · ${item.body.slice(0, 70)}`;
      if (selectedBookmarks.includes(item.event_id)) row.classList.add('selected');
      row.addEventListener('click', () => {
        const id = item.event_id;
        if (selectedBookmarks.includes(id)) {
          selectedBookmarks = selectedBookmarks.filter(value => value !== id);
        } else {
          if (selectedBookmarks.length === 2) selectedBookmarks.shift();
          selectedBookmarks.push(id);
        }
        renderBookmarks(items);
      });
      box.append(row);
    }
    document.querySelector('#copy-range').disabled = selectedBookmarks.length !== 2;
  }

  function renderStatus(runtime, companions = []) {
    if (companions.length > 0) {
      document.querySelector('#status').textContent =
        `Zeno sta parlando anche con ${companions.join(', ')}`;
      return;
    }
    let text = 'Zeno ' + runtime.status.toLowerCase().replaceAll('_', ' ');
    if (runtime.actor) text += ` con ${runtime.actor}`;
    document.querySelector('#status').textContent = text;
  }

  async function refresh(full = false) {
    if (refreshing) return;
    refreshing = true;
    try {
      const after = full ? 0 : lastEvent;
      const data = await api('history', {query: `after=${after}`});
      if (full) {
        transcript.replaceChildren();
        lastEvent = 0;
      }
      const nearBottom = transcript.scrollHeight - transcript.scrollTop - transcript.clientHeight < 100;
      for (const event of data.events) {
        transcript.append(eventNode(event));
        lastEvent = Math.max(lastEvent, event.id);
        if (!full && event.event_type === 'artifact'
            && sessionStorage.getItem('izeno-opened-artifact') !== String(event.id)) {
          openViewer(JSON.parse(event.body));
          sessionStorage.setItem('izeno-opened-artifact', String(event.id));
        }
        if (['final', 'system'].includes(event.event_type)) waiting = false;
        if (!full && event.event_type === 'spontaneous') ding();
      }
      renderBookmarks(data.bookmarks);
      renderStatus(data.runtime, data.companions);
      if (nearBottom || full) transcript.scrollTop = transcript.scrollHeight;
      notice.textContent = waiting ? 'Zeno sta lavorando; attività, file e modifiche compariranno qui.' : '';
    } catch (error) {
      notice.textContent = error.message;
    } finally {
      refreshing = false;
    }
  }

  async function upload(file) {
    const form = new FormData();
    form.append('file', file, file.name || 'registrazione.webm');
    const result = await api('upload', {method: 'POST', body: form});
    pendingFiles.push(result.file);
    const chip = document.createElement('button');
    chip.type = 'button';
    chip.className = 'attachment';
    chip.textContent = `${result.file.kind}: ${result.file.name}`;
    chip.addEventListener('click', () => openViewer(result.file));
    document.querySelector('#attachments').append(chip);
    return result.file;
  }

  function openViewer(file) {
    const body = document.querySelector('#viewer-body');
    body.replaceChildren();
    if (file.kind === 'image') {
      const image = document.createElement('img');
      image.src = file.url;
      image.alt = file.name;
      body.append(image);
    } else if (file.kind === 'audio') {
      const audio = document.createElement('audio');
      audio.src = file.url;
      audio.controls = true;
      body.append(audio);
    } else {
      const download = document.createElement('a');
      download.href = file.url;
      download.textContent = `Scarica ${file.name}`;
      body.append(download);
    }
    document.querySelector('#viewer').showModal();
  }

  async function send() {
    const body = request.value.trim();
    if (!body && pendingFiles.length === 0) return;
    sendButton.disabled = true;
    waiting = true;
    notice.textContent = 'Zeno sta lavorando; attività, file e modifiche compariranno qui.';
    try {
      const form = new FormData();
      form.append('body', body);
      form.append('files', pendingFiles.map(file => file.id).join(','));
      await api('send', {method: 'POST', body: form});
      request.value = '';
      pendingFiles = [];
      document.querySelector('#attachments').replaceChildren();
      await refresh();
    } catch (error) {
      waiting = false;
      if (!disconnected) notice.textContent = error.message;
    } finally {
      if (!disconnected) sendButton.disabled = false;
    }
  }

  async function toggleRecording() {
    const button = document.querySelector('#record');
    if (recorder && recorder.state === 'recording') {
      recorder.stop();
      button.textContent = '🎙 Registra';
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({audio: true});
      recordedChunks = [];
      recorder = new MediaRecorder(stream);
      recorder.addEventListener('dataavailable', event => {
        if (event.data.size) recordedChunks.push(event.data);
      });
      recorder.addEventListener('stop', async () => {
        stream.getTracks().forEach(track => track.stop());
        const blob = new Blob(recordedChunks, {type: recorder.mimeType || 'audio/webm'});
        const file = new File([blob], `voce-${Date.now()}.webm`, {type: blob.type});
        await upload(file);
        notice.textContent = 'Registrazione caricata; invio e trascrizione locale in corso.';
        await send();
      });
      recorder.start();
      button.textContent = '■ Ferma';
    } catch (error) {
      notice.textContent = `Microfono non disponibile: ${error.message}`;
    }
  }

  async function start() {
    const opened = await api('open', {method: 'POST'});
    session = opened.session;
    await refresh(true);
    refreshTimer = setInterval(() => refresh(), 1500);
    heartbeatTimer = setInterval(async () => {
      const form = new FormData();
      if (humanActive) form.append('active', '1');
      humanActive = false;
      try {
        await api('heartbeat', {method: 'POST', body: form});
      } catch (error) {
        if (!disconnected) notice.textContent = error.message;
      }
    }, 10000);
  }

  document.querySelector('#send').addEventListener('click', send);
  request.addEventListener('keydown', event => {
    if (event.key === 'Enter' && (event.ctrlKey || event.metaKey)) send();
  });
  document.querySelector('#upload-file').addEventListener('change', event => {
    if (event.target.files[0]) upload(event.target.files[0]).catch(error => notice.textContent = error.message);
    event.target.value = '';
  });
  document.querySelector('#record').addEventListener('click', toggleRecording);
  document.querySelector('#copy-range').addEventListener('click', async () => {
    const data = await api('copy', {query: `first=${selectedBookmarks[0]}&second=${selectedBookmarks[1]}`});
    await navigator.clipboard.writeText(data.text);
    notice.textContent = 'Intervallo copiato negli appunti.';
  });
  document.querySelector('#close-viewer').addEventListener('click', () => document.querySelector('#viewer').close());
  for (const eventName of ['pointerdown', 'keydown', 'touchstart', 'wheel']) {
    window.addEventListener(eventName, registerHumanActivity, {passive: true});
  }
  window.addEventListener('pagehide', () => {
    if (!session) return;
    const form = new FormData();
    form.append('session', session);
    navigator.sendBeacon('./?action=close', form);
  });
  start().catch(error => notice.textContent = error.message);
})();

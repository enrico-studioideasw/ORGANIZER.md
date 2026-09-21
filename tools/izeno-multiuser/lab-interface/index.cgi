#!/usr/local/bin/php-cgi-ewbd
<?php

declare(strict_types=1);

require dirname(__DIR__) . '/lib.php';

const FILE_ROOT = '/home/noc/EWB2026/shared-state/zeno-console-files';
const SHARED_MODE = 1;

function console_user(): array
{
    $user = current_user();
    if ($user === null) {
        http_response_code(401);
        echo '<!doctype html><meta charset="utf-8"><p>Accedi prima a '
            . '<a href="../">Forum-one</a>.</p>';
        exit;
    }
    $statement = db()->prepare(
        'SELECT enabled FROM zeno_console_access WHERE user_id = ?'
    );
    $statement->bind_param('i', $user['id']);
    $statement->execute();
    $access = $statement->get_result()->fetch_assoc();
    if ($access === null || (int) $access['enabled'] !== 1) {
        http_response_code(403);
        echo '<!doctype html><meta charset="utf-8"><p>Questo account non è '
            . 'abilitato alla console di Zeno.</p>';
        exit;
    }
    return $user;
}

function api_response(array $payload, int $status = 200): never
{
    http_response_code($status);
    header('Content-Type: application/json; charset=utf-8');
    header('Cache-Control: no-store, private');
    echo json_encode($payload, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    echo "\n";
    exit;
}

function api_error(string $message, int $status = 400): never
{
    api_response(['error' => $message], $status);
}

function session_token(array $user): string
{
    $token = trim((string) ($_REQUEST['session'] ?? ''));
    if (!preg_match('/^[a-f0-9]{64}$/', $token)) {
        api_error('Sessione web non valida.', 401);
    }
    $statement = db()->prepare(
        'SELECT token, close_reason FROM zeno_console_sessions
         WHERE token = ? AND user_id = ?'
    );
    $statement->bind_param('si', $token, $user['id']);
    $statement->execute();
    $session = $statement->get_result()->fetch_assoc();
    if ($session === null) {
        api_error('Sessione web scaduta.', 401);
    }
    if ($session['close_reason'] === 'inactive') {
        api_error('Zeno si è disconnesso per inattività.', 401);
    }
    if ($session['close_reason'] !== 'open') {
        api_error('Sessione web chiusa.', 401);
    }
    return $token;
}

function queue_presence(int $userId, string $event): void
{
    $statement = db()->prepare(
        'INSERT INTO zeno_console_presence_queue (user_id, event_type)
         VALUES (?, ?)'
    );
    $statement->bind_param('is', $userId, $event);
    $statement->execute();
}

function open_session(array $user): never
{
    $result = db()->query(
        'SELECT DISTINCT s.user_id
         FROM zeno_console_sessions s
         WHERE s.close_reason = \'open\'
           AND s.last_seen >= DATE_SUB(NOW(), INTERVAL 120 SECOND)'
    );
    $activeUsers = array_map('intval', array_column(
        $result->fetch_all(MYSQLI_ASSOC), 'user_id'
    ));
    if (!in_array((int) $user['id'], $activeUsers, true)
        && count($activeUsers) >= 2) {
        api_error('La console condivisa ha già due interlocutori.', 409);
    }
    $token = bin2hex(random_bytes(32));
    $agent = mb_substr((string) ($_SERVER['HTTP_USER_AGENT'] ?? ''), 0, 255);
    $statement = db()->prepare(
        'INSERT INTO zeno_console_sessions (token, user_id, user_agent)
         VALUES (?, ?, ?)'
    );
    $statement->bind_param('sis', $token, $user['id'], $agent);
    $statement->execute();
    queue_presence((int) $user['id'], 'open');
    $timeout = mb_strtolower((string) $user['name']) === 'enrico' ? 3600 : 900;
    api_response([
        'session' => $token,
        'user' => $user['name'],
        'idle_timeout' => $timeout,
    ]);
}

function heartbeat(array $user): never
{
    $token = session_token($user);
    $active = (int) ($_POST['active'] ?? 0) === 1;
    $sql = $active
        ? 'UPDATE zeno_console_sessions
           SET last_seen = NOW(), last_activity = NOW()
           WHERE token = ? AND user_id = ?'
        : 'UPDATE zeno_console_sessions SET last_seen = NOW()
           WHERE token = ? AND user_id = ?';
    $statement = db()->prepare($sql);
    $statement->bind_param('si', $token, $user['id']);
    $statement->execute();
    api_response(['ok' => true]);
}

function close_session(array $user): never
{
    $token = session_token($user);
    $statement = db()->prepare(
        'UPDATE zeno_console_sessions
         SET close_reason = \'closed\', closed_at = NOW(), last_seen = NOW()
         WHERE token = ? AND user_id = ? AND close_reason = \'open\''
    );
    $statement->bind_param('si', $token, $user['id']);
    $statement->execute();
    if ($statement->affected_rows === 1) {
        queue_presence((int) $user['id'], 'close');
    }
    api_response(['ok' => true]);
}

function runtime_status(): array
{
    $result = db()->query(
        'SELECT status, actor, updated_at FROM zeno_console_runtime
         WHERE singleton = 1'
    );
    return $result->fetch_assoc() ?: [
        'status' => 'SCONOSCIUTO', 'actor' => null, 'updated_at' => null
    ];
}

function active_companions(array $user): array
{
    $statement = db()->prepare(
        'SELECT DISTINCT u.name
         FROM zeno_console_sessions s
         JOIN users u ON u.id = s.user_id
         WHERE s.close_reason = \'open\' AND s.user_id <> ?
           AND s.last_seen >= DATE_SUB(NOW(), INTERVAL 120 SECOND)
         ORDER BY u.name'
    );
    $statement->bind_param('i', $user['id']);
    $statement->execute();
    return array_column($statement->get_result()->fetch_all(MYSQLI_ASSOC), 'name');
}

function history(array $user): never
{
    session_token($user);
    $after = max(0, (int) ($_GET['after'] ?? 0));
    if ($after === 0) {
        $eventsSource =
            '(SELECT * FROM zeno_console_events
              WHERE user_id = ? ORDER BY id DESC LIMIT 100)';
        $where = '';
    } else {
        $eventsSource = 'zeno_console_events';
        $where = 'WHERE e.user_id = ? AND e.id > ?';
    }
    $statement = db()->prepare(
        'SELECT e.id, e.request_id, e.user_id, e.event_type, e.body,
                e.created_at, u.name AS user_name,
                CASE WHEN b.event_id IS NULL THEN 0 ELSE 1 END AS bookmarked
         FROM ' . $eventsSource . ' e
         LEFT JOIN users u ON u.id = e.user_id
         LEFT JOIN zeno_console_bookmarks b
           ON b.event_id = e.id AND b.user_id = ?
         ' . $where . ' ORDER BY e.id LIMIT 500'
    );
    if ($after === 0) {
        $statement->bind_param('ii', $user['id'], $user['id']);
    } else {
        $statement->bind_param('iii', $user['id'], $user['id'], $after);
    }
    $statement->execute();
    $events = [];
    $result = $statement->get_result();
    while ($row = $result->fetch_assoc()) {
        $row['id'] = (int) $row['id'];
        $row['bookmarked'] = (bool) $row['bookmarked'];
        $events[] = $row;
    }
    $statement = db()->prepare(
        'SELECT b.event_id, b.label, e.body, e.event_type, e.created_at
         FROM zeno_console_bookmarks b
         JOIN zeno_console_events e ON e.id = b.event_id
         WHERE b.user_id = ? AND e.user_id = ? ORDER BY e.id'
    );
    $statement->bind_param('ii', $user['id'], $user['id']);
    $statement->execute();
    $bookmarks = [];
    $result = $statement->get_result();
    while ($row = $result->fetch_assoc()) {
        $row['event_id'] = (int) $row['event_id'];
        $bookmarks[] = $row;
    }
    api_response([
        'events' => $events,
        'bookmarks' => $bookmarks,
        'runtime' => runtime_status(),
        'companions' => active_companions($user),
    ]);
}

function send_request(array $user): never
{
    $session = session_token($user);
    $body = trim((string) ($_POST['body'] ?? ''));
    if (mb_strlen($body) > 131072) {
        api_error('La richiesta supera 131072 caratteri.');
    }
    $fileIds = array_values(array_unique(array_filter(array_map(
        'intval', explode(',', (string) ($_POST['files'] ?? ''))
    ))));
    if ($body === '' && $fileIds === []) {
        api_error('Scrivi un messaggio oppure allega una registrazione audio.');
    }
    $connection = db();
    $connection->begin_transaction();
    try {
        $statement = $connection->prepare(
            'INSERT INTO zeno_console_requests
             (user_id, session_token, body, shared_mode, error_text)
             VALUES (?, ?, ?, ?, \'\')'
        );
        $sharedMode = SHARED_MODE;
        $statement->bind_param('issi', $user['id'], $session, $body, $sharedMode);
        $statement->execute();
        $requestId = (int) $connection->insert_id;
        $statement = $connection->prepare(
            'INSERT INTO zeno_console_events
             (request_id, user_id, event_type, body)
             VALUES (?, ?, \'user\', ?)'
        );
        $statement->bind_param('iis', $requestId, $user['id'], $body);
        $statement->execute();
        foreach ($fileIds as $fileId) {
            if ($fileId < 1) {
                continue;
            }
            $statement = $connection->prepare(
                'INSERT INTO zeno_console_request_files (request_id, file_id)
                 SELECT ?, id FROM zeno_console_files
                 WHERE id = ? AND user_id = ? AND request_id IS NULL'
            );
            $statement->bind_param('iii', $requestId, $fileId, $user['id']);
            $statement->execute();
            if ($statement->affected_rows === 1) {
                $statement = $connection->prepare(
                    'UPDATE zeno_console_files SET request_id = ? WHERE id = ?'
                );
                $statement->bind_param('ii', $requestId, $fileId);
                $statement->execute();
            }
        }
        $connection->commit();
    } catch (Throwable $error) {
        $connection->rollback();
        throw $error;
    }
    queue_presence((int) $user['id'], 'activity');
    $statement = db()->prepare(
        'UPDATE zeno_console_sessions SET last_activity = NOW()
         WHERE token = ? AND user_id = ?'
    );
    $statement->bind_param('si', $session, $user['id']);
    $statement->execute();
    api_response(['ok' => true, 'request_id' => $requestId]);
}

function toggle_bookmark(array $user): never
{
    session_token($user);
    $eventId = positive_id($_POST['event_id'] ?? null, 'event_id');
    $statement = db()->prepare(
        'DELETE FROM zeno_console_bookmarks WHERE user_id = ? AND event_id = ?'
    );
    $statement->bind_param('ii', $user['id'], $eventId);
    $statement->execute();
    $bookmarked = false;
    if ($statement->affected_rows === 0) {
        $label = mb_substr(trim((string) ($_POST['label'] ?? '')), 0, 100);
        $statement = db()->prepare(
            'INSERT INTO zeno_console_bookmarks (user_id, event_id, label)
             SELECT ?, id, ? FROM zeno_console_events
             WHERE id = ? AND user_id = ?'
        );
        $statement->bind_param(
            'isii', $user['id'], $label, $eventId, $user['id']
        );
        $statement->execute();
        $bookmarked = $statement->affected_rows === 1;
    }
    api_response(['ok' => true, 'bookmarked' => $bookmarked]);
}

function copy_between(array $user): never
{
    session_token($user);
    $first = positive_id($_GET['first'] ?? null, 'first');
    $second = positive_id($_GET['second'] ?? null, 'second');
    $low = min($first, $second);
    $high = max($first, $second);
    $statement = db()->prepare(
        'SELECT event_id FROM zeno_console_bookmarks
         WHERE user_id = ? AND event_id IN (?, ?)'
    );
    $statement->bind_param('iii', $user['id'], $low, $high);
    $statement->execute();
    if ($statement->get_result()->num_rows !== 2) {
        api_error('Seleziona due segnalibri validi.', 403);
    }
    $statement = db()->prepare(
        'SELECT e.event_type, e.body, e.created_at, u.name AS user_name
         FROM zeno_console_events e
         LEFT JOIN users u ON u.id = e.user_id
         WHERE e.id BETWEEN ? AND ? AND e.user_id = ? ORDER BY e.id'
    );
    $statement->bind_param('iii', $low, $high, $user['id']);
    $statement->execute();
    $parts = [];
    $result = $statement->get_result();
    while ($row = $result->fetch_assoc()) {
        $speaker = $row['event_type'] === 'user'
            ? ($row['user_name'] ?? 'Utente') : 'Zeno';
        $parts[] = '[' . $row['created_at'] . '] ' . $speaker . "\n" . $row['body'];
    }
    api_response(['text' => implode("\n\n", $parts)]);
}

function upload_file(array $user): never
{
    session_token($user);
    if (!isset($_FILES['file']) || !is_uploaded_file($_FILES['file']['tmp_name'])) {
        api_error('File mancante.');
    }
    $upload = $_FILES['file'];
    if ((int) $upload['size'] < 1 || (int) $upload['size'] > 20 * 1024 * 1024) {
        api_error('Il file deve essere compreso fra 1 byte e 20 MiB.');
    }
    $finfo = new finfo(FILEINFO_MIME_TYPE);
    $mime = (string) $finfo->file($upload['tmp_name']);
    if (str_starts_with($mime, 'image/')) {
        $kind = 'image';
    } elseif (str_starts_with($mime, 'audio/') || $mime === 'video/webm') {
        $kind = 'audio';
    } else {
        $kind = 'document';
    }
    $token = bin2hex(random_bytes(32));
    $directory = FILE_ROOT . '/' . substr($token, 0, 2);
    if (!is_dir($directory) && !mkdir($directory, 0770, true) && !is_dir($directory)) {
        api_error('Impossibile preparare l’area di scambio.', 500);
    }
    $path = $directory . '/' . $token;
    if (!move_uploaded_file($upload['tmp_name'], $path)) {
        api_error('Salvataggio del file non riuscito.', 500);
    }
    chmod($path, 0660);
    $name = mb_substr(basename((string) $upload['name']), 0, 255);
    $size = (int) $upload['size'];
    $statement = db()->prepare(
        'INSERT INTO zeno_console_files
         (token, user_id, kind, original_name, stored_path, mime_type, size_bytes)
         VALUES (?, ?, ?, ?, ?, ?, ?)'
    );
    $statement->bind_param(
        'sissssi', $token, $user['id'], $kind, $name, $path, $mime, $size
    );
    $statement->execute();
    api_response([
        'ok' => true,
        'file' => [
            'id' => (int) db()->insert_id,
            'name' => $name,
            'kind' => $kind,
            'url' => './?action=file&token=' . $token,
        ],
    ]);
}

function serve_file(array $user): never
{
    $token = trim((string) ($_GET['token'] ?? ''));
    if (!preg_match('/^[a-f0-9]{64}$/', $token)) {
        api_error('File non valido.', 404);
    }
    $statement = db()->prepare(
        'SELECT stored_path, mime_type, original_name, kind FROM zeno_console_files
         WHERE token = ? AND user_id = ?'
    );
    $statement->bind_param('si', $token, $user['id']);
    $statement->execute();
    $file = $statement->get_result()->fetch_assoc();
    if ($file === null || !is_readable($file['stored_path'])) {
        api_error('File non disponibile.', 404);
    }
    header('Content-Type: ' . $file['mime_type']);
    header('Content-Length: ' . filesize($file['stored_path']));
    header('Content-Disposition: '
        . ($file['kind'] === 'document' ? 'attachment' : 'inline') . '; filename="'
        . rawurlencode($file['original_name']) . '"');
    header('Cache-Control: no-store, private');
    header('X-Content-Type-Options: nosniff');
    header('X-Robots-Tag: noindex, nofollow, noarchive');
    readfile($file['stored_path']);
    exit;
}

$user = console_user();
$action = (string) ($_REQUEST['action'] ?? 'page');

try {
    match ($action) {
        'open' => open_session($user),
        'heartbeat' => heartbeat($user),
        'close' => close_session($user),
        'history' => history($user),
        'send' => send_request($user),
        'bookmark' => toggle_bookmark($user),
        'copy' => copy_between($user),
        'upload' => upload_file($user),
        'file' => serve_file($user),
        'page' => null,
        default => api_error('Azione sconosciuta.', 404),
    };
} catch (Throwable $error) {
    if ($action !== 'page') {
        api_error('Errore console: ' . $error->getMessage(), 500);
    }
    throw $error;
}

?><!doctype html>
<html lang="it">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>iZeno laboratorio condiviso</title>
<link rel="stylesheet" href="style.css">
</head>
<body>
<main>
<header>
  <div><a href="../">Forum-one</a> · <strong>iZeno laboratorio condiviso</strong></div>
  <div id="status" class="status">connessione…</div>
</header>
<section class="workspace">
  <aside>
    <h2>Segnalibri</h2>
    <p class="hint">Selezionane due per copiare l’intervallo.</p>
    <div id="bookmarks"></div>
    <button id="copy-range" type="button" disabled>Copia fra i due</button>
  </aside>
  <section id="transcript" class="transcript" aria-live="polite"></section>
</section>
<section class="composer">
  <div id="attachments" class="attachments"></div>
  <textarea id="request" rows="5" placeholder="Scrivi a Zeno…"></textarea>
  <div class="controls">
    <label class="button">Upload
      <input id="upload-file" type="file" hidden>
    </label>
    <button id="record" type="button">🎙 Registra</button>
    <button id="send" type="button" class="primary">Invia</button>
  </div>
  <div id="notice" class="notice"></div>
</section>
</main>
<dialog id="viewer">
  <button id="close-viewer" type="button" class="close">Chiudi</button>
  <div id="viewer-body"></div>
</dialog>
<script>window.IZENO_USER = <?= json_encode($user['name'], JSON_UNESCAPED_UNICODE) ?>;</script>
<script src="app.js?v=20260921-multi1"></script>
</body>
</html>

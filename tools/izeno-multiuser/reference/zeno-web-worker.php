#!/usr/bin/php
<?php

declare(strict_types=1);

const MAIN_SOCKET = '/run/zeno-identity/zeno.sock';
const CONTROL_SOCKET = '/run/zeno-identity/control.sock';
const STATUS_FILE = '/run/zeno-identity/status.json';
const STT_SOCKET = '/run/zeno-stt/stt.sock';
const TICK_PROMPT = <<<'PROMPT'
[Tick spontaneo verificato dal demone; non e' una richiesta dell'utente]
sa fem?

La console web e' aperta ma non ci sono stati messaggi recenti. Questo tick
crea soltanto un momento nel quale puoi iniziare tu una conversazione. Se hai
una domanda, un collegamento o un pensiero concreto che valga la pena portare
adesso, scrivi un solo messaggio breve e naturale. Non inventare urgenze, non
trasformare automaticamente il tick in lavoro e non produrre un resoconto di
stato. Se non hai davvero nulla da dire, rispondi esattamente con __SILENZIO__.
PROMPT;

$config = require '/etc/forum-one.php';
mysqli_report(MYSQLI_REPORT_ERROR | MYSQLI_REPORT_STRICT);
$db = new mysqli(
    $config['db_host'],
    $config['db_user'],
    $config['db_password'],
    $config['db_name']
);
$db->set_charset('utf8mb4');

function log_line(string $message): void
{
    fwrite(STDOUT, '[' . date('c') . '] ' . $message . "\n");
    fflush(STDOUT);
}

function send_control(string $actor, string $event): bool
{
    $socket = @stream_socket_client('unix://' . CONTROL_SOCKET, $errno, $error, 2);
    if ($socket === false) {
        log_line('Controllo non raggiungibile: ' . $error);
        return false;
    }
    fwrite($socket, json_encode([
        'actor' => $actor,
        'event' => $event,
    ], JSON_UNESCAPED_UNICODE) . "\n");
    $answer = fgets($socket);
    fclose($socket);
    return trim((string) $answer) === 'OK';
}

function expire_sessions(mysqli $db): void
{
    $result = $db->query(
        'SELECT s.token, s.user_id,
                CASE
                  WHEN s.last_seen < DATE_SUB(NOW(), INTERVAL 120 SECOND)
                    THEN \'dropped\'
                  ELSE \'inactive\'
                END AS reason
         FROM zeno_console_sessions s
         JOIN users u ON u.id = s.user_id
         WHERE s.close_reason = \'open\'
           AND (s.last_seen < DATE_SUB(NOW(), INTERVAL 120 SECOND)
             OR (LOWER(u.name) = \'enrico\'
                 AND s.last_activity < DATE_SUB(NOW(), INTERVAL 60 MINUTE))
             OR (LOWER(u.name) <> \'enrico\'
                 AND s.last_activity < DATE_SUB(NOW(), INTERVAL 15 MINUTE)))'
    );
    $expired = $result->fetch_all(MYSQLI_ASSOC);
    foreach ($expired as $session) {
        $statement = $db->prepare(
            'UPDATE zeno_console_sessions
             SET close_reason = ?, closed_at = NOW()
             WHERE token = ? AND close_reason = \'open\''
        );
        $statement->bind_param('ss', $session['reason'], $session['token']);
        $statement->execute();
        if ($statement->affected_rows === 1) {
            $statement = $db->prepare(
                'INSERT INTO zeno_console_presence_queue (user_id, event_type)
                 VALUES (?, \'drop\')'
            );
            $statement->bind_param('i', $session['user_id']);
            $statement->execute();
        }
    }
}

function store_spontaneous(mysqli $db, string $body): void
{
    $statement = $db->prepare(
        'INSERT INTO zeno_console_events
         (request_id, user_id, event_type, body)
         VALUES (NULL, NULL, \'spontaneous\', ?)'
    );
    $statement->bind_param('s', $body);
    $statement->execute();
}

function web_actor_is_present(mysqli $db, string $actor): bool
{
    $statement = $db->prepare(
        'SELECT COUNT(*)
         FROM zeno_console_sessions s
         JOIN users u ON u.id = s.user_id
         JOIN zeno_console_runtime r ON r.singleton = 1
         WHERE s.close_reason = \'open\'
           AND s.last_seen >= DATE_SUB(NOW(), INTERVAL 120 SECOND)
           AND u.name = ? AND r.status = \'OCCUPATO\' AND r.actor = ?'
    );
    $statement->bind_param('ss', $actor, $actor);
    $statement->execute();
    return (int) $statement->get_result()->fetch_column() > 0;
}

function execute_spontaneous(mysqli $db, string $actor): void
{
    if (!web_actor_is_present($db, $actor)) {
        return;
    }
    $envelope = json_encode([
        'actor' => $actor,
        'text' => TICK_PROMPT,
        'local_images' => [],
    ], JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    $socket = @stream_socket_client('unix://' . MAIN_SOCKET, $errno, $error, 5);
    if ($socket === false) {
        throw new RuntimeException('Demone non raggiungibile per sa fem?: ' . $error);
    }
    stream_set_timeout($socket, 3600);
    fwrite($socket, "ZENO-WEB/1\n" . $envelope . "\r\n\r\n");
    stream_socket_shutdown($socket, STREAM_SHUT_WR);
    $answer = '';
    while (($line = fgets($socket)) !== false) {
        $event = json_decode(trim($line), true);
        if (!is_array($event)) {
            continue;
        }
        if (($event['type'] ?? '') === 'error') {
            fclose($socket);
            throw new RuntimeException((string) ($event['text'] ?? 'sa fem? rifiutato'));
        }
        if (($event['type'] ?? '') === 'final') {
            $answer = trim((string) ($event['text'] ?? ''));
        }
    }
    fclose($socket);
    if ($answer !== '' && $answer !== '__SILENZIO__') {
        store_spontaneous($db, $answer);
        log_line('sa fem? web: messaggio pubblicato per ' . $actor);
    } else {
        log_line('sa fem? web: silenzio per ' . $actor);
    }
}

function deliver_presence(mysqli $db): void
{
    $result = $db->query(
        'SELECT q.id, q.event_type, u.name
         FROM zeno_console_presence_queue q
         JOIN users u ON u.id = q.user_id
         WHERE q.delivered_at IS NULL ORDER BY q.id LIMIT 20'
    );
    while ($row = $result->fetch_assoc()) {
        if (!send_control($row['name'], $row['event_type'])) {
            return;
        }
        $statement = $db->prepare(
            'UPDATE zeno_console_presence_queue SET delivered_at = NOW()
             WHERE id = ? AND delivered_at IS NULL'
        );
        $statement->bind_param('i', $row['id']);
        $statement->execute();
    }
}

function mirror_status(mysqli $db): void
{
    if (!is_readable(STATUS_FILE)) {
        return;
    }
    $status = json_decode((string) file_get_contents(STATUS_FILE), true);
    if (!is_array($status) || !isset($status['status'])) {
        return;
    }
    $actor = $status['actor'] ?? null;
    if ($status['status'] === 'DISPONIBILE') {
        $result = $db->query(
            'SELECT GROUP_CONCAT(DISTINCT u.name ORDER BY u.name SEPARATOR ", ")
             FROM zeno_console_sessions s
             JOIN users u ON u.id = s.user_id
             WHERE s.close_reason = \'open\'
             AND s.last_seen >= DATE_SUB(NOW(), INTERVAL 120 SECOND)'
        );
        $webActors = trim((string) $result->fetch_column());
        if ($webActors !== '') {
            $status['status'] = 'OCCUPATO';
            $actor = $webActors;
        }
    }
    $statement = $db->prepare(
        'UPDATE zeno_console_runtime
         SET status = ?, actor = ?, updated_at = NOW() WHERE singleton = 1'
    );
    $statement->bind_param('ss', $status['status'], $actor);
    $statement->execute();
}

function claim_request(mysqli $db): ?array
{
    $db->begin_transaction();
    try {
        $result = $db->query(
            'SELECT r.id, r.user_id, r.body, r.shared_mode, u.name
             FROM zeno_console_requests r
             JOIN users u ON u.id = r.user_id
             WHERE r.status = \'queued\' ORDER BY r.id LIMIT 1 FOR UPDATE'
        );
        $request = $result->fetch_assoc();
        if ($request === null) {
            $db->commit();
            return null;
        }
        $statement = $db->prepare(
            'UPDATE zeno_console_requests
             SET status = \'processing\', started_at = NOW() WHERE id = ?'
        );
        $statement->bind_param('i', $request['id']);
        $statement->execute();
        $db->commit();
        return $request;
    } catch (Throwable $error) {
        $db->rollback();
        throw $error;
    }
}

function request_files(mysqli $db, int $requestId): array
{
    $statement = $db->prepare(
        'SELECT f.kind, f.original_name, f.stored_path
         FROM zeno_console_request_files rf
         JOIN zeno_console_files f ON f.id = rf.file_id
         WHERE rf.request_id = ? ORDER BY f.id'
    );
    $statement->bind_param('i', $requestId);
    $statement->execute();
    return $statement->get_result()->fetch_all(MYSQLI_ASSOC);
}

function transcribe_audio(string $path): string
{
    $socket = @stream_socket_client('unix://' . STT_SOCKET, $errno, $error, 5);
    if ($socket === false) {
        throw new RuntimeException('Trascrizione non raggiungibile: ' . $error);
    }
    stream_set_timeout($socket, 360);
    fwrite($socket, json_encode(['path' => $path], JSON_UNESCAPED_SLASHES) . "\n");
    $line = fgets($socket);
    $meta = stream_get_meta_data($socket);
    fclose($socket);
    if ($meta['timed_out']) {
        throw new RuntimeException('Trascrizione audio scaduta.');
    }
    $response = json_decode((string) $line, true);
    if (!is_array($response) || !($response['ok'] ?? false)) {
        throw new RuntimeException(
            'Trascrizione audio fallita: ' . ($response['error'] ?? 'risposta non valida')
        );
    }
    return trim((string) ($response['text'] ?? ''));
}

function store_event(
    mysqli $db,
    int $requestId,
    int $userId,
    string $type,
    string $body
): void {
    $allowed = ['commentary', 'files', 'diff', 'final', 'system'];
    if (!in_array($type, $allowed, true) || $body === '') {
        return;
    }
    $statement = $db->prepare(
        'INSERT INTO zeno_console_events
         (request_id, user_id, event_type, body) VALUES (?, ?, ?, ?)'
    );
    $statement->bind_param('iiss', $requestId, $userId, $type, $body);
    $statement->execute();
}

function finish_request(mysqli $db, int $requestId, bool $ok, string $error = ''): void
{
    $status = $ok ? 'completed' : 'failed';
    $statement = $db->prepare(
        'UPDATE zeno_console_requests
         SET status = ?, error_text = ?, completed_at = NOW() WHERE id = ?'
    );
    $statement->bind_param('ssi', $status, $error, $requestId);
    $statement->execute();
}

function execute_request(mysqli $db, array $request): void
{
    $files = request_files($db, (int) $request['id']);
    $images = [];
    $attachmentLines = [];
    $audioTexts = [];
    foreach ($files as $file) {
        $attachmentLine = '- ' . $file['kind'] . ': ' . $file['original_name'];
        if ($file['kind'] === 'document' && is_readable($file['stored_path'])) {
            $attachmentLine .= ' (' . $file['stored_path'] . ')';
        }
        $attachmentLines[] = $attachmentLine;
        if ($file['kind'] === 'image' && is_readable($file['stored_path'])) {
            $images[] = $file['stored_path'];
        } elseif ($file['kind'] === 'audio' && is_readable($file['stored_path'])) {
            $transcript = transcribe_audio($file['stored_path']);
            if ($transcript === '') {
                throw new RuntimeException(
                    'La registrazione audio non contiene parole riconosciute.'
                );
            }
            $audioTexts[] = $transcript;
        }
    }
    $text = trim($request['body']);
    if ($audioTexts !== []) {
        $spoken = implode("\n", $audioTexts);
        $text .= ($text === '' ? '' : "\n\n")
            . "[Trascrizione verificata dell'audio]\n" . $spoken;
    }
    if ($attachmentLines !== []) {
        $text .= "\n\n[Allegati verificati dalla console web]\n"
            . implode("\n", $attachmentLines);
    }
    $envelope = json_encode([
        'actor' => $request['name'],
        'text' => $text,
        'local_images' => $images,
        'shared' => (bool) $request['shared_mode'],
    ], JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    $socket = @stream_socket_client('unix://' . MAIN_SOCKET, $errno, $error, 5);
    if ($socket === false) {
        throw new RuntimeException('Demone non raggiungibile: ' . $error);
    }
    stream_set_timeout($socket, 3600);
    fwrite($socket, "ZENO-WEB/1\n" . $envelope . "\r\n\r\n");
    stream_socket_shutdown($socket, STREAM_SHUT_WR);
    while (($line = fgets($socket)) !== false) {
        $event = json_decode(trim($line), true);
        if (!is_array($event)) {
            continue;
        }
        $type = $event['type'] ?? '';
        if ($type === 'done') {
            continue;
        }
        if ($type === 'error') {
            throw new RuntimeException((string) ($event['text'] ?? 'Richiesta rifiutata.'));
        }
        if ($type === 'files') {
            $body = implode("\n", $event['paths'] ?? []);
        } else {
            $body = (string) ($event['text'] ?? '');
        }
        store_event(
            $db,
            (int) $request['id'],
            (int) $request['user_id'],
            $type,
            $body
        );
    }
    $meta = stream_get_meta_data($socket);
    fclose($socket);
    if ($meta['timed_out']) {
        throw new RuntimeException('Tempo massimo della risposta superato.');
    }
}

log_line('Worker iZeno web avviato');
$tickActor = null;
$tickDue = null;
$result = $db->query(
    'SELECT u.name
     FROM zeno_console_requests r
     JOIN users u ON u.id = r.user_id
     JOIN zeno_console_sessions s ON s.token = r.session_token
     WHERE r.status = \'completed\' AND s.close_reason = \'open\'
     ORDER BY r.completed_at DESC LIMIT 1'
);
$lastActor = $result->fetch_column();
if (is_string($lastActor) && $lastActor !== '') {
    $tickActor = $lastActor;
    $tickDue = microtime(true) + random_int(120, 360);
}
while (true) {
    try {
        expire_sessions($db);
        deliver_presence($db);
        mirror_status($db);
        $request = claim_request($db);
        if ($request !== null) {
            log_line('Richiesta ' . $request['id'] . ' da ' . $request['name']);
            try {
                execute_request($db, $request);
                finish_request($db, (int) $request['id'], true);
                $tickActor = $request['name'];
                $tickDue = microtime(true) + random_int(120, 360);
            } catch (Throwable $error) {
                store_event(
                    $db,
                    (int) $request['id'],
                    (int) $request['user_id'],
                    'system',
                    'Errore: ' . $error->getMessage()
                );
                finish_request(
                    $db, (int) $request['id'], false, $error->getMessage()
                );
                log_line('Richiesta fallita: ' . $error->getMessage());
            }
        }
        if ($tickDue !== null && microtime(true) >= $tickDue) {
            $actor = (string) $tickActor;
            $tickDue = null;
            $tickActor = null;
            execute_spontaneous($db, $actor);
        }
    } catch (Throwable $error) {
        log_line('Errore ciclo worker: ' . $error->getMessage());
    }
    usleep(500000);
}

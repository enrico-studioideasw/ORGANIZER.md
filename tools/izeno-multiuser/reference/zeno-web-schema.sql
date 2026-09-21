USE forum_one;

CREATE TABLE IF NOT EXISTS zeno_console_access (
    user_id BIGINT UNSIGNED NOT NULL,
    enabled TINYINT UNSIGNED NOT NULL DEFAULT 1,
    granted_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id),
    CONSTRAINT zeno_console_access_user
        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS zeno_console_sessions (
    token CHAR(64) NOT NULL,
    user_id BIGINT UNSIGNED NOT NULL,
    opened_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_seen DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    closed_at DATETIME NULL,
    close_reason ENUM('open', 'closed', 'dropped') NOT NULL DEFAULT 'open',
    user_agent VARCHAR(255) NOT NULL DEFAULT '',
    PRIMARY KEY (token),
    KEY zeno_sessions_user (user_id, last_seen),
    CONSTRAINT zeno_sessions_user_fk
        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS zeno_console_requests (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    user_id BIGINT UNSIGNED NOT NULL,
    session_token CHAR(64) NOT NULL,
    body TEXT NOT NULL,
    shared_mode TINYINT UNSIGNED NOT NULL DEFAULT 0,
    status ENUM('queued', 'processing', 'completed', 'failed')
        NOT NULL DEFAULT 'queued',
    error_text TEXT NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    started_at DATETIME NULL,
    completed_at DATETIME NULL,
    PRIMARY KEY (id),
    KEY zeno_requests_queue (status, id),
    CONSTRAINT zeno_requests_user_fk
        FOREIGN KEY (user_id) REFERENCES users (id),
    CONSTRAINT zeno_requests_session_fk
        FOREIGN KEY (session_token) REFERENCES zeno_console_sessions (token)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS zeno_console_events (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    request_id BIGINT UNSIGNED NULL,
    user_id BIGINT UNSIGNED NULL,
    event_type ENUM(
        'user', 'commentary', 'files', 'diff', 'final', 'system',
        'spontaneous', 'artifact'
    )
        NOT NULL,
    body MEDIUMTEXT NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY zeno_events_request (request_id, id),
    CONSTRAINT zeno_events_request_fk
        FOREIGN KEY (request_id) REFERENCES zeno_console_requests (id)
        ON DELETE SET NULL,
    CONSTRAINT zeno_events_user_fk
        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE SET NULL
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS zeno_console_files (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    token CHAR(64) NOT NULL,
    user_id BIGINT UNSIGNED NOT NULL,
    request_id BIGINT UNSIGNED NULL,
    kind ENUM('image', 'audio', 'document') NOT NULL,
    original_name VARCHAR(255) NOT NULL,
    stored_path VARCHAR(1024) NOT NULL,
    mime_type VARCHAR(100) NOT NULL,
    size_bytes BIGINT UNSIGNED NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY zeno_files_token (token),
    KEY zeno_files_request (request_id),
    CONSTRAINT zeno_files_user_fk
        FOREIGN KEY (user_id) REFERENCES users (id),
    CONSTRAINT zeno_files_request_fk
        FOREIGN KEY (request_id) REFERENCES zeno_console_requests (id)
        ON DELETE SET NULL
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS zeno_console_request_files (
    request_id BIGINT UNSIGNED NOT NULL,
    file_id BIGINT UNSIGNED NOT NULL,
    PRIMARY KEY (request_id, file_id),
    CONSTRAINT zeno_request_files_request_fk
        FOREIGN KEY (request_id) REFERENCES zeno_console_requests (id)
        ON DELETE CASCADE,
    CONSTRAINT zeno_request_files_file_fk
        FOREIGN KEY (file_id) REFERENCES zeno_console_files (id)
        ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS zeno_console_bookmarks (
    user_id BIGINT UNSIGNED NOT NULL,
    event_id BIGINT UNSIGNED NOT NULL,
    label VARCHAR(100) NOT NULL DEFAULT '',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, event_id),
    CONSTRAINT zeno_bookmarks_user_fk
        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
    CONSTRAINT zeno_bookmarks_event_fk
        FOREIGN KEY (event_id) REFERENCES zeno_console_events (id)
        ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS zeno_console_presence_queue (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    user_id BIGINT UNSIGNED NOT NULL,
    event_type ENUM('open', 'activity', 'close', 'drop') NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    delivered_at DATETIME NULL,
    PRIMARY KEY (id),
    KEY zeno_presence_pending (delivered_at, id),
    CONSTRAINT zeno_presence_user_fk
        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS zeno_console_runtime (
    singleton TINYINT UNSIGNED NOT NULL,
    status VARCHAR(32) NOT NULL,
    actor VARCHAR(100) NULL,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (singleton)
) ENGINE=InnoDB;

INSERT INTO zeno_console_runtime (singleton, status, actor)
VALUES (1, 'AVVIO', NULL)
ON DUPLICATE KEY UPDATE singleton = singleton;

INSERT INTO zeno_console_access (user_id, enabled)
SELECT id, 1 FROM users WHERE is_admin = 1
ON DUPLICATE KEY UPDATE enabled = VALUES(enabled);

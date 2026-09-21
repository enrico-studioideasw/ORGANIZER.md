ALTER TABLE zeno_console_requests
    ADD COLUMN IF NOT EXISTS shared_mode TINYINT UNSIGNED NOT NULL DEFAULT 0
    AFTER body;

-- Run on the console database after backing it up.
ALTER TABLE zeno_console_sessions
    ADD COLUMN IF NOT EXISTS last_activity DATETIME NOT NULL
    DEFAULT CURRENT_TIMESTAMP AFTER last_seen;

-- If the live enum contains additional custom values, preserve them too.
ALTER TABLE zeno_console_sessions
    MODIFY COLUMN close_reason ENUM('open', 'closed', 'dropped', 'inactive')
    NOT NULL DEFAULT 'open';

CREATE INDEX IF NOT EXISTS zeno_events_user ON zeno_console_events (user_id, id);

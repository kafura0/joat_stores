-- =============================================================================
-- MISSING TABLES — Run AFTER supabase_seed.sql
-- Creates Django framework tables that the seed script doesn't cover
-- =============================================================================

-- django.contrib.sessions
CREATE TABLE IF NOT EXISTS django_session (
    session_key  VARCHAR(40) PRIMARY KEY,
    session_data TEXT NOT NULL,
    expire_date  TIMESTAMP NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_session_expire_date ON django_session (expire_date);

-- django.contrib.sites
CREATE TABLE IF NOT EXISTS django_site (
    id     SERIAL PRIMARY KEY,
    domain VARCHAR(100) NOT NULL,
    name   VARCHAR(50)  NOT NULL
);
INSERT INTO django_site (id, domain, name) VALUES (1, 'localhost', 'joat stores')
ON CONFLICT (id) DO NOTHING;

-- django.contrib.admin
CREATE TABLE IF NOT EXISTS django_admin_log (
    id              SERIAL PRIMARY KEY,
    action_time     TIMESTAMP NOT NULL DEFAULT NOW(),
    object_id       TEXT,
    object_repr     VARCHAR(200) NOT NULL,
    action_flag     SMALLINT NOT NULL,
    change_message  TEXT NOT NULL DEFAULT '',
    content_type_id INTEGER REFERENCES django_content_type(id) ON DELETE SET NULL,
    user_id         INTEGER NOT NULL REFERENCES users_user(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_admin_log_action_time     ON django_admin_log (action_time);
CREATE INDEX IF NOT EXISTS idx_admin_log_content_type_id ON django_admin_log (content_type_id);
CREATE INDEX IF NOT EXISTS idx_admin_log_user_id         ON django_admin_log (user_id);

-- rest_framework_simplejwt.token_blacklist
CREATE TABLE IF NOT EXISTS token_blacklist_outstandingtoken (
    id         BIGSERIAL PRIMARY KEY,
    jti        UUID NOT NULL UNIQUE,
    token      TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    user_id    INTEGER REFERENCES users_user(id) ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS idx_outstandingtoken_user_id ON token_blacklist_outstandingtoken (user_id);

CREATE TABLE IF NOT EXISTS token_blacklist_blacklistedtoken (
    id             BIGSERIAL PRIMARY KEY,
    blacklisted_at TIMESTAMP NOT NULL DEFAULT NOW(),
    token_id       INTEGER NOT NULL UNIQUE REFERENCES token_blacklist_outstandingtoken(id) ON DELETE CASCADE
);

-- allauth.account
CREATE TABLE IF NOT EXISTS account_emailaddress (
    id        SERIAL PRIMARY KEY,
    email     VARCHAR(254) NOT NULL,
    verified  BOOLEAN NOT NULL DEFAULT FALSE,
    "primary" BOOLEAN NOT NULL DEFAULT FALSE,
    user_id   INTEGER NOT NULL REFERENCES users_user(id) ON DELETE CASCADE,
    CONSTRAINT account_emailaddress_user_id_email_uniq UNIQUE (user_id, email)
);
CREATE INDEX IF NOT EXISTS idx_account_emailaddress_email ON account_emailaddress (email);
CREATE INDEX IF NOT EXISTS idx_account_emailaddress_user  ON account_emailaddress (user_id);

CREATE TABLE IF NOT EXISTS account_emailconfirmation (
    id               SERIAL PRIMARY KEY,
    created          TIMESTAMP NOT NULL DEFAULT NOW(),
    sent             TIMESTAMP,
    key              VARCHAR(64) NOT NULL UNIQUE,
    email_address_id INTEGER NOT NULL REFERENCES account_emailaddress(id) ON DELETE CASCADE
);

-- allauth.socialaccount
CREATE TABLE IF NOT EXISTS socialaccount_socialaccount (
    id          SERIAL PRIMARY KEY,
    provider    VARCHAR(200) NOT NULL,
    uid         VARCHAR(191) NOT NULL,
    last_login  TIMESTAMP NOT NULL,
    date_joined TIMESTAMP NOT NULL,
    extra_data  JSONB NOT NULL DEFAULT '{}'::jsonb,
    user_id     INTEGER NOT NULL REFERENCES users_user(id) ON DELETE CASCADE,
    CONSTRAINT socialaccount_socialaccount_provider_uid_uniq UNIQUE (provider, uid)
);

CREATE TABLE IF NOT EXISTS socialaccount_socialapp (
    id          SERIAL PRIMARY KEY,
    provider    VARCHAR(30) NOT NULL,
    name        VARCHAR(40) NOT NULL,
    client_id   VARCHAR(191) NOT NULL,
    secret      VARCHAR(191) NOT NULL,
    key         VARCHAR(191) NOT NULL DEFAULT '',
    provider_id VARCHAR(200) NOT NULL DEFAULT '',
    settings    JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS socialaccount_socialapp_sites (
    id           SERIAL PRIMARY KEY,
    socialapp_id INTEGER NOT NULL REFERENCES socialaccount_socialapp(id) ON DELETE CASCADE,
    site_id      INTEGER NOT NULL REFERENCES django_site(id) ON DELETE CASCADE,
    CONSTRAINT socialaccount_socialapp_sites_uniq UNIQUE (socialapp_id, site_id)
);

CREATE TABLE IF NOT EXISTS socialaccount_socialtoken (
    id            SERIAL PRIMARY KEY,
    token         TEXT NOT NULL,
    token_secret  TEXT NOT NULL DEFAULT '',
    expires_at    TIMESTAMP,
    account_id    INTEGER NOT NULL REFERENCES socialaccount_socialaccount(id) ON DELETE CASCADE,
    app_id        INTEGER REFERENCES socialaccount_socialapp(id) ON DELETE SET NULL,
    CONSTRAINT socialaccount_socialtoken_app_account_uniq UNIQUE (app_id, account_id)
);

-- django_celery_beat
CREATE TABLE IF NOT EXISTS django_celery_beat_crontabschedule (
    id            SERIAL PRIMARY KEY,
    minute        VARCHAR(240) NOT NULL DEFAULT '*',
    hour          VARCHAR(96)  NOT NULL DEFAULT '*',
    day_of_week   VARCHAR(64)  NOT NULL DEFAULT '*',
    day_of_month  VARCHAR(124) NOT NULL DEFAULT '*',
    month_of_year VARCHAR(64)  NOT NULL DEFAULT '*',
    timezone      VARCHAR(100) NOT NULL DEFAULT 'UTC'
);

CREATE TABLE IF NOT EXISTS django_celery_beat_intervalschedule (
    id     SERIAL PRIMARY KEY,
    every  INTEGER NOT NULL,
    period VARCHAR(24) NOT NULL
);

CREATE TABLE IF NOT EXISTS django_celery_beat_clockedschedule (
    id           SERIAL PRIMARY KEY,
    clocked_time TIMESTAMP NOT NULL
);

CREATE TABLE IF NOT EXISTS django_celery_beat_solarschedule (
    id        SERIAL PRIMARY KEY,
    event     VARCHAR(24) NOT NULL,
    latitude  DECIMAL(9,6) NOT NULL,
    longitude DECIMAL(9,6) NOT NULL,
    CONSTRAINT django_celery_beat_solarschedule_event_lat_long_uniq UNIQUE (event, latitude, longitude)
);

CREATE TABLE IF NOT EXISTS django_celery_beat_periodictask (
    id              SERIAL PRIMARY KEY,
    name            VARCHAR(200) NOT NULL UNIQUE,
    task            VARCHAR(200) NOT NULL,
    args            TEXT NOT NULL DEFAULT '[]',
    kwargs          TEXT NOT NULL DEFAULT '{}',
    queue           VARCHAR(200),
    exchange        VARCHAR(200),
    routing_key     VARCHAR(200),
    expires         TIMESTAMP,
    enabled         BOOLEAN NOT NULL DEFAULT TRUE,
    last_run_at     TIMESTAMP,
    total_run_count INTEGER NOT NULL DEFAULT 0,
    date_changed    TIMESTAMP NOT NULL,
    description     TEXT NOT NULL DEFAULT '',
    crontab_id      INTEGER REFERENCES django_celery_beat_crontabschedule(id) ON DELETE CASCADE,
    interval_id     INTEGER REFERENCES django_celery_beat_intervalschedule(id) ON DELETE CASCADE,
    solar_id        INTEGER REFERENCES django_celery_beat_solarschedule(id) ON DELETE CASCADE,
    clocked_id      INTEGER REFERENCES django_celery_beat_clockedschedule(id) ON DELETE CASCADE,
    one_off         BOOLEAN NOT NULL DEFAULT FALSE,
    start_time      TIMESTAMP,
    priority        INTEGER,
    headers         TEXT NOT NULL DEFAULT '{}',
    expire_seconds  INTEGER
);

CREATE TABLE IF NOT EXISTS django_celery_beat_periodictasks (
    ident       SMALLINT PRIMARY KEY DEFAULT 1,
    last_update TIMESTAMP NOT NULL
);

SELECT 'Migration tables created successfully!' AS status;

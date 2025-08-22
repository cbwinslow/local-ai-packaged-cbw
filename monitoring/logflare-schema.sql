-- Create schema migrations table
CREATE TABLE IF NOT EXISTS schema_migrations (
    version bigint NOT NULL,
    inserted_at timestamp without time zone,
    PRIMARY KEY (version)
);

-- Create system metrics table
CREATE TABLE IF NOT EXISTS system_metrics (
    id SERIAL PRIMARY KEY,
    all_logs_logged boolean DEFAULT false,
    node varchar(255),
    inserted_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);

-- Create sources table
CREATE TABLE IF NOT EXISTS sources (
    id SERIAL PRIMARY KEY,
    name varchar(255),
    service_name varchar(255),
    token varchar(255),
    public_token varchar(255),
    favorite boolean DEFAULT false,
    bigquery_table_ttl integer,
    api_quota integer,
    webhook_notification_url text,
    slack_hook_url text,
    bq_table_partition_type varchar(255),
    custom_event_message_keys text[],
    log_events_updated_at timestamp without time zone,
    notifications_every integer,
    lock_schema boolean DEFAULT false,
    validate_schema boolean DEFAULT false,
    drop_lql_filters boolean DEFAULT false,
    drop_lql_string text,
    v2_pipeline boolean DEFAULT false,
    disable_tailing boolean DEFAULT false,
    suggested_keys text[],
    transform_copy_fields text[],
    user_id integer,
    notifications jsonb,
    inserted_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);

-- Create users table
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email varchar(255),
    provider varchar(255),
    token text,
    api_key varchar(255),
    old_api_key varchar(255),
    email_preferred varchar(255),
    name varchar(255),
    image text,
    email_me_product boolean DEFAULT false,
    admin boolean DEFAULT false,
    phone varchar(255),
    bigquery_project_id varchar(255),
    bigquery_dataset_location varchar(255),
    bigquery_dataset_id varchar(255),
    bigquery_udfs_hash varchar(255),
    bigquery_processed_bytes_limit bigint,
    api_quota integer,
    valid_google_account boolean DEFAULT false,
    provider_uid varchar(255),
    company varchar(255),
    billing_enabled boolean DEFAULT false,
    endpoints_beta boolean DEFAULT false,
    metadata jsonb,
    preferences jsonb,
    partner_upgraded boolean DEFAULT false,
    partner_id integer,
    inserted_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);

-- Create backends table
CREATE TABLE IF NOT EXISTS backends (
    id SERIAL PRIMARY KEY,
    name varchar(255),
    description text,
    token varchar(255),
    type varchar(255),
    config_encrypted text,
    user_id integer REFERENCES users(id),
    metadata jsonb,
    inserted_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);

-- Create sources_backends table
CREATE TABLE IF NOT EXISTS sources_backends (
    source_id integer REFERENCES sources(id),
    backend_id integer REFERENCES backends(id),
    PRIMARY KEY (source_id, backend_id)
);

-- Grant privileges to supabase_admin
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO supabase_admin;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO supabase_admin;

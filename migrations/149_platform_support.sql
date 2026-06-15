-- Platform support chatbot (the support widget on agentnexlify.com).
--
-- Stores public support conversations from the marketing-site widget and tracks
-- per-session transcript email so the platform owner gets each conversation
-- once. These are platform-level tables (not tenant-scoped) — they are the
-- AgentNexLiFy operator's own support inbox, accessed only via the backend
-- service key, so no client_id column and no RLS policy are needed.

create table if not exists platform_support_messages (
    id uuid primary key default gen_random_uuid(),
    session_id text not null,
    role text not null check (role in ('user', 'assistant')),
    content text not null,
    created_at timestamptz not null default now()
);

create index if not exists idx_platform_support_messages_session
    on platform_support_messages (session_id, created_at);

create table if not exists platform_support_sessions (
    session_id text primary key,
    started_at timestamptz not null default now(),
    last_activity_at timestamptz not null default now(),
    transcript_sent_at timestamptz,
    reporter_email text,
    page_url text
);

-- Dashboard "Send a message" support form (POST /api/v1/support/contact).
-- The endpoint inserted here all along but the table was never created, so the
-- form 500'd before this change. Same platform-inbox concern as the tables
-- above: service-key-only access, no client_id, no RLS policy needed.
create table if not exists support_messages (
    id uuid primary key default gen_random_uuid(),
    name text not null,
    email text not null,
    message text not null,
    created_at timestamptz not null default now()
);

-- Enable RLS (no policies). Backend uses the service-role key, which bypasses
-- RLS; anon/authenticated roles get no access. Matches the rest of public.*.
alter table platform_support_messages enable row level security;
alter table platform_support_sessions enable row level security;
alter table support_messages enable row level security;

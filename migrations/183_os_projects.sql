-- Migration 183: multi-department OS Projects (suite item 4 - orchestration).
--
-- One owner ask becomes an approvable PLAN of department steps, executed
-- sequentially through the normal engine turn path. See
-- specs/os-projects_spec.md. client_id scope - os_* family. RLS on, no
-- policies (service-role only), matching the rest of the os_* tables.

CREATE TABLE IF NOT EXISTS os_projects (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id   uuid NOT NULL,
    title       text NOT NULL,
    ask         text NOT NULL,
    status      text NOT NULL DEFAULT 'draft',
    error       text,
    created_at  timestamptz NOT NULL DEFAULT now(),
    updated_at  timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS os_project_steps (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id     uuid NOT NULL,
    project_id    uuid NOT NULL REFERENCES os_projects(id) ON DELETE CASCADE,
    position      integer NOT NULL,
    department    text NOT NULL,
    objective     text NOT NULL,
    status        text NOT NULL DEFAULT 'pending',
    agent_run_id  uuid,
    thread_id     uuid,
    created_at    timestamptz NOT NULL DEFAULT now(),
    updated_at    timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS os_projects_client_idx
    ON os_projects (client_id);
CREATE INDEX IF NOT EXISTS os_projects_active_idx
    ON os_projects (status, updated_at)
    WHERE status IN ('approved', 'running');
CREATE INDEX IF NOT EXISTS os_project_steps_project_idx
    ON os_project_steps (project_id, position);
CREATE INDEX IF NOT EXISTS os_project_steps_client_idx
    ON os_project_steps (client_id);

ALTER TABLE os_projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE os_project_steps ENABLE ROW LEVEL SECURITY;

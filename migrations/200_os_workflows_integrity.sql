-- 200_os_workflows_integrity.sql
-- Forward hardening for M9.2 (do NOT edit applied 199).
--
-- 1) Composite tenant integrity: steps must share client_id with parent workflow.
-- 2) Atomic create RPC so workflow + steps never partially persist.

-- Parent unique key for composite FK.
ALTER TABLE os_workflows
    DROP CONSTRAINT IF EXISTS os_workflows_id_client_id_key;
ALTER TABLE os_workflows
    ADD CONSTRAINT os_workflows_id_client_id_key UNIQUE (id, client_id);

-- Replace workflow_id-only FK with (workflow_id, client_id).
ALTER TABLE os_workflow_steps
    DROP CONSTRAINT IF EXISTS os_workflow_steps_workflow_id_fkey;
ALTER TABLE os_workflow_steps
    DROP CONSTRAINT IF EXISTS os_workflow_steps_workflow_client_fkey;
ALTER TABLE os_workflow_steps
    ADD CONSTRAINT os_workflow_steps_workflow_client_fkey
    FOREIGN KEY (workflow_id, client_id)
    REFERENCES os_workflows (id, client_id)
    ON DELETE CASCADE;

COMMENT ON CONSTRAINT os_workflow_steps_workflow_client_fkey ON os_workflow_steps IS
    'M9 tenant integrity: step client_id must match parent workflow client_id.';

-- Atomic workflow + steps insert. Returns the workflow row as jsonb with
-- embedded steps array. Raises on any failure (no partial durable state).
CREATE OR REPLACE FUNCTION create_os_workflow(
    p_client_id uuid,
    p_owner_goal text,
    p_steps jsonb,
    p_workflow_id uuid DEFAULT NULL
)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_workflow_id uuid;
    v_now timestamptz := now();
    v_step jsonb;
    v_steps jsonb := '[]'::jsonb;
    v_ordinal integer := 0;
    v_step_id uuid;
    v_deps uuid[];
    v_row os_workflow_steps%ROWTYPE;
    v_workflow os_workflows%ROWTYPE;
BEGIN
    IF p_client_id IS NULL THEN
        RAISE EXCEPTION 'client_id required';
    END IF;
    IF p_owner_goal IS NULL OR length(trim(p_owner_goal)) = 0 THEN
        RAISE EXCEPTION 'owner_goal required';
    END IF;
    IF p_steps IS NULL OR jsonb_typeof(p_steps) <> 'array' THEN
        RAISE EXCEPTION 'steps must be a json array';
    END IF;

    v_workflow_id := COALESCE(p_workflow_id, gen_random_uuid());

    INSERT INTO os_workflows (id, client_id, owner_goal, status, row_version, created_at, updated_at)
    VALUES (v_workflow_id, p_client_id, p_owner_goal, 'planned', 1, v_now, v_now)
    RETURNING * INTO v_workflow;

    FOR v_step IN SELECT value FROM jsonb_array_elements(p_steps)
    LOOP
        v_step_id := COALESCE((v_step->>'id')::uuid, gen_random_uuid());
        v_deps := COALESCE(
            ARRAY(
                SELECT jsonb_array_elements_text(COALESCE(v_step->'dependencies', '[]'::jsonb))::uuid
            ),
            '{}'::uuid[]
        );

        INSERT INTO os_workflow_steps (
            id, workflow_id, client_id, ordinal, description, dependencies,
            department, tool_intent, state, risk_level, execution_id,
            verification_state, error, retry_count, max_retries, row_version,
            created_at, updated_at
        )
        VALUES (
            v_step_id,
            v_workflow_id,
            p_client_id,
            COALESCE((v_step->>'ordinal')::integer, v_ordinal),
            v_step->>'description',
            v_deps,
            v_step->>'department',
            v_step->'tool_intent',
            COALESCE(v_step->>'state', 'planned'),
            COALESCE((v_step->>'risk_level')::smallint, 1),
            NULLIF(v_step->>'execution_id', '')::uuid,
            v_step->>'verification_state',
            v_step->>'error',
            COALESCE((v_step->>'retry_count')::integer, 0),
            COALESCE((v_step->>'max_retries')::integer, 2),
            1,
            v_now,
            v_now
        )
        RETURNING * INTO v_row;

        v_steps := v_steps || jsonb_build_array(to_jsonb(v_row));
        v_ordinal := v_ordinal + 1;
    END LOOP;

    RETURN to_jsonb(v_workflow) || jsonb_build_object('steps', v_steps);
END;
$$;

REVOKE ALL ON FUNCTION create_os_workflow(uuid, text, jsonb, uuid) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION create_os_workflow(uuid, text, jsonb, uuid) TO service_role;

COMMENT ON FUNCTION create_os_workflow(uuid, text, jsonb, uuid) IS
    'M9 atomic workflow create: inserts workflow + all steps in one transaction.';

-- AgentNexLiFy Database Schema

-- Clients: real estate agents who are our customers
CREATE TABLE IF NOT EXISTS clients (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    agent_name TEXT NOT NULL,
    agent_type TEXT NOT NULL DEFAULT 'agent',
    brokerage_name TEXT,
    service_area TEXT NOT NULL,
    bot_name TEXT NOT NULL DEFAULT 'Aria',
    calendly_link TEXT,
    notification_email TEXT,
    notification_phone TEXT,
    widget_api_key TEXT UNIQUE NOT NULL,
    active BOOLEAN NOT NULL DEFAULT true,
    custom_instructions TEXT,
    brand_color TEXT NOT NULL DEFAULT '#6cff5c'
);

CREATE INDEX IF NOT EXISTS idx_clients_widget_api_key ON clients (widget_api_key);
CREATE INDEX IF NOT EXISTS idx_clients_active ON clients (active);

-- Leads: prospective buyers/sellers captured by the chatbot
CREATE TABLE IF NOT EXISTS leads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    conversation_id UUID,  -- set after conversation table exists
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    name TEXT,
    email TEXT,
    phone TEXT,
    lead_type TEXT,  -- buyer, seller, both, investor, unknown
    timeline TEXT,
    budget TEXT,
    pre_approved BOOLEAN,
    areas_of_interest TEXT,
    must_haves TEXT,
    lead_score INTEGER CHECK (lead_score BETWEEN 1 AND 10),
    lead_temperature TEXT CHECK (lead_temperature IN ('hot', 'warm', 'cold')),
    conversation_summary TEXT,
    next_steps TEXT,
    status TEXT NOT NULL DEFAULT 'new' CHECK (status IN ('new', 'contacted', 'appointment_booked', 'closed', 'lost')),
    appointment_date TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_leads_client_id ON leads (client_id);
CREATE INDEX IF NOT EXISTS idx_leads_lead_score ON leads (lead_score);
CREATE INDEX IF NOT EXISTS idx_leads_status ON leads (status);
CREATE INDEX IF NOT EXISTS idx_leads_lead_temperature ON leads (lead_temperature);

-- Conversations: chat sessions between leads and the AI agent
CREATE TABLE IF NOT EXISTS conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    channel TEXT NOT NULL DEFAULT 'web',
    session_id TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'completed', 'handed_off')),
    lead_id UUID REFERENCES leads(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_conversations_client_id ON conversations (client_id);
CREATE INDEX IF NOT EXISTS idx_conversations_session_id ON conversations (session_id);
CREATE INDEX IF NOT EXISTS idx_conversations_status ON conversations (status);

-- Add FK from leads back to conversations now that both tables exist
ALTER TABLE leads
    ADD CONSTRAINT fk_leads_conversation_id
    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE SET NULL;

-- Messages: individual messages within a conversation
CREATE TABLE IF NOT EXISTS messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system', 'tool_use', 'tool_result')),
    content TEXT NOT NULL,
    metadata JSONB
);

CREATE INDEX IF NOT EXISTS idx_messages_conversation_id ON messages (conversation_id);
CREATE INDEX IF NOT EXISTS idx_messages_created_at ON messages (created_at);

-- Row Level Security
ALTER TABLE clients ENABLE ROW LEVEL SECURITY;
ALTER TABLE leads ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE messages ENABLE ROW LEVEL SECURITY;

-- Service role can do everything (backend uses service key)
CREATE POLICY service_all_clients ON clients FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY service_all_leads ON leads FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY service_all_conversations ON conversations FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY service_all_messages ON messages FOR ALL USING (true) WITH CHECK (true);

-- OB-41: Multi-user teams with RBAC (owner / analyst / viewer)
-- Sprint 05 — v1.2.0

CREATE TABLE IF NOT EXISTS team_members (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id       UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    user_email   VARCHAR(255) NOT NULL,
    role         VARCHAR(20)  NOT NULL DEFAULT 'viewer'
                     CHECK (role IN ('owner', 'analyst', 'viewer')),
    invited_at   TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    accepted_at  TIMESTAMPTZ
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_team_members_org_email
    ON team_members(org_id, user_email);

CREATE INDEX IF NOT EXISTS idx_team_members_org
    ON team_members(org_id);

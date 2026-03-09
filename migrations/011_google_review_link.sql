-- Google Review Link for review request automation template
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS google_review_link TEXT;

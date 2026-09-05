BEGIN;

CREATE TABLE merchants (
  id text PRIMARY KEY,
  name text NOT NULL,
  timezone text NOT NULL DEFAULT 'Asia/Kolkata',
  default_language text NOT NULL DEFAULT 'hi-IN',
  invoice_settings jsonb NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE users (
  id text PRIMARY KEY,
  merchant_id text NOT NULL REFERENCES merchants(id),
  role text NOT NULL,
  identity text NOT NULL,
  session_metadata jsonb NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE customers (
  id text PRIMARY KEY,
  merchant_id text NOT NULL REFERENCES merchants(id),
  canonical_name text NOT NULL,
  aliases text[] NOT NULL DEFAULT '{}',
  phone text,
  address text,
  credit_limit_minor bigint NOT NULL DEFAULT 0
);

CREATE TABLE skus (
  id text PRIMARY KEY,
  merchant_id text NOT NULL REFERENCES merchants(id),
  canonical_label text NOT NULL,
  aliases text[] NOT NULL DEFAULT '{}',
  base_unit text NOT NULL,
  units_per_case integer NOT NULL DEFAULT 1,
  selling_price_minor bigint NOT NULL,
  stock integer NOT NULL DEFAULT 0,
  tax_metadata jsonb NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE voice_jobs (
  id text PRIMARY KEY,
  merchant_id text NOT NULL REFERENCES merchants(id),
  audio_key text,
  transcript text,
  language text,
  provider_request_id text,
  state text NOT NULL,
  prompt_version text NOT NULL DEFAULT 'v1',
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE draft_commands (
  voice_job_id text NOT NULL REFERENCES voice_jobs(id),
  revision integer NOT NULL,
  payload jsonb NOT NULL,
  evidence jsonb NOT NULL DEFAULT '{}'::jsonb,
  confidence jsonb NOT NULL DEFAULT '{}'::jsonb,
  validation_errors jsonb NOT NULL DEFAULT '[]'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (voice_job_id, revision)
);

CREATE TABLE clarifications (
  id text PRIMARY KEY,
  voice_job_id text NOT NULL REFERENCES voice_jobs(id),
  field_path text NOT NULL,
  question text NOT NULL,
  answer jsonb,
  resolved_at timestamptz
);

CREATE TABLE sales_orders (
  id text PRIMARY KEY,
  merchant_id text NOT NULL REFERENCES merchants(id),
  customer_id text NOT NULL REFERENCES customers(id),
  voice_job_id text NOT NULL UNIQUE REFERENCES voice_jobs(id),
  delivery_date date NOT NULL,
  total_minor bigint NOT NULL,
  currency char(3) NOT NULL DEFAULT 'INR',
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE order_items (
  id text PRIMARY KEY,
  order_id text NOT NULL REFERENCES sales_orders(id),
  sku_id text NOT NULL REFERENCES skus(id),
  quantity integer NOT NULL CHECK (quantity > 0),
  unit text NOT NULL,
  unit_price_minor bigint NOT NULL,
  line_total_minor bigint NOT NULL
);

CREATE TABLE inventory_movements (
  id text PRIMARY KEY,
  merchant_id text NOT NULL REFERENCES merchants(id),
  sku_id text NOT NULL REFERENCES skus(id),
  source_type text NOT NULL,
  source_id text NOT NULL,
  delta integer NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE invoices (
  id text PRIMARY KEY,
  order_id text NOT NULL UNIQUE REFERENCES sales_orders(id),
  invoice_number text NOT NULL UNIQUE,
  total_minor bigint NOT NULL,
  status text NOT NULL,
  pdf_asset_key text
);

CREATE TABLE ledger_entries (
  id text PRIMARY KEY,
  merchant_id text NOT NULL REFERENCES merchants(id),
  customer_id text NOT NULL REFERENCES customers(id),
  source_type text NOT NULL,
  source_id text NOT NULL,
  amount_minor bigint NOT NULL,
  direction text NOT NULL CHECK (direction IN ('debit', 'credit')),
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE outbox_events (
  id text PRIMARY KEY,
  merchant_id text NOT NULL REFERENCES merchants(id),
  event_type text NOT NULL,
  payload jsonb NOT NULL,
  delivered_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX inventory_source_once ON inventory_movements(source_type, source_id, sku_id);
CREATE UNIQUE INDEX ledger_source_once ON ledger_entries(source_type, source_id);

COMMIT;

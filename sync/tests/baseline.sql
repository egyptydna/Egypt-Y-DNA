-- Disposable CI database only. Never run this baseline against the hosted project.
create role anon;
create role authenticated;
create role service_role bypassrls;
create table public."Modern_published_samples" (
 id bigint generated always as identity primary key,
 name text default '—',kit_number text default '—',test_type text default '—',
 y_dna text default '—',y_dna_alias text,snp_path text default '—',full_snp_path text default '—',
 governorate text default '—',y_link_1 text default '—',y_link_2 text default '—',created_at timestamptz default now(),
 mt_dna text default '—',"full_mtDNA_path" text default '—',mt_link_1 text default '—',mt_link_2 text default '—'
);
alter table public."Modern_published_samples" enable row level security;
create policy archive_read on public."Modern_published_samples" for select to anon,authenticated using(true);
grant select on public."Modern_published_samples" to anon,authenticated;
grant all on public."Modern_published_samples" to service_role;
grant usage,select on sequence public."Modern_published_samples_id_seq" to service_role;
create table public."Ancient_published_samples" (id bigint primary key);
create table public."Modern_study_samples" (id bigint primary key);
create table public.ancient_related_samples (id bigint primary key);

-- Minimal GoTrue fixtures for owner-authorization tests only.
create schema auth;
create table auth.users(id uuid primary key,email text,encrypted_password text,email_confirmed_at timestamptz,deleted_at timestamptz,banned_until timestamptz,last_sign_in_at timestamptz);
create table auth.sessions(id uuid primary key,user_id uuid references auth.users(id));
create function auth.uid() returns uuid language sql stable as $$select (nullif(current_setting('request.jwt.claims',true),'')::jsonb->>'sub')::uuid$$;
create function auth.jwt() returns jsonb language sql stable as $$select coalesce(nullif(current_setting('request.jwt.claims',true),'')::jsonb,'{}'::jsonb)$$;

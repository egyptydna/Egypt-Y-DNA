-- New files require explicit publication approval; source rows stay behind
-- their file's publication policy even when individual row flags are true.
alter table public.ydna_uploaded_files alter column published set default false;

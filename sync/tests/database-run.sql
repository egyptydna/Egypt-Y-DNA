\set ON_ERROR_STOP on
begin;
\i sync/tests/database.sql
rollback;

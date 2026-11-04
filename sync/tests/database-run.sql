\set ON_ERROR_STOP on
begin;
\i sync/tests/database.sql
\i sync/tests/country-counts-database.sql
\i sync/tests/licensed-trees-database.sql
rollback;

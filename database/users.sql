begin;
\echo ***Ignore any errors about file_host_group not existing, if present.***
drop owned by file_host_group;
drop role if exists file_host_group;
commit;
\echo ***There should be no errors past this point***
begin;
create role file_host_group;
grant usage on schema public to file_host_group;
alter default privileges in schema public
    grant usage, select on sequences to file_host_group;
commit;

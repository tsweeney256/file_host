begin;

set local client_min_messages=warning;
alter table if exists registration_confirmation
    drop constraint if exists registration_confirmation_site_user_id_fkey;
alter table if exists file
    drop constraint if exists file_site_user_id_fkey;
alter table if exists login
    drop constraint if exists login_site_user_id_fkey;
alter table if exists password_reset
    drop constraint if exists password_reset_site_user_id_fkey;
drop table if exists registration_confirmation;
drop table if exists site_user;
drop table if exists file;
drop table if exists login;
drop table if exists password_reset;
drop function if exists now_utc();
reset client_min_messages;

create function now_utc() returns timestamp as $$
    select now() at time zone 'utc';
$$ language sql;
grant execute on function now_utc() to file_host_group;

-- "site_user" because the SQL standards comittee has no restraint
-- when it comes to keywords
create table site_user (
    site_user_id bigserial primary key,
    email varchar(256) unique not null,
    password varchar(128) not null,
    api_key varchar(128),
    data_limit bigint,
    role smallint not null default 1,
    num_invites smallint,
    creation_time timestamp not null default now_utc(),
    last_action_time timestamp not null default now_utc(),
    never_auto_delete_account boolean not null default false,
    deleted boolean not null default false
);
grant select, insert, update on table site_user to file_host_group;

create table registration_confirmation(
    registration_confirmation_id bigserial primary key,
    site_user_id bigserial unique not null references site_user(site_user_id),
    url varchar unique not null,
    redeemed boolean not null default false
);
grant select, insert, update on table
    registration_confirmation to file_host_group;

create table file (
    file_id bigserial primary key,
    site_user_id bigint not null references site_user(site_user_id),
    url varchar(12) unique not null,
    deletion_url varchar(12) unique not null,
    name varchar(256) not null,
    size bigint not null,
    mime_type varchar(256) not null default 'application/octet-stream',
    date_added timestamp not null default now_utc(),
    deleted boolean not null default false
);
grant select, insert, update on table file to file_host_group;

create table login (
    login_id bigserial primary key,
    site_user_id bigint not null references site_user(site_user_id),
    ip cidr not null
);
grant select, insert, update on table login to file_host_group;

create table password_reset (
    password_reset_id bigserial primary key,
    site_user_id bigint not null references site_user(site_user_id),
    ip cidr not null,
    url varchar(24),
    date_added timestamp not null default now_utc(),
    redeemed boolean not null default false
);
grant select, insert, update on table password_reset to file_host_group;

commit;

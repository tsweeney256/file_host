begin;

set local client_min_messages=warning;
create extension if not exists "pgcrypto";
drop function if exists create_registration_confirmation_entry(
                                        v_site_user_id bigint);
drop function if exists confirm_registration(bigint, varchar, interval);
drop function if exists create_password_reset_entry(varchar, cidr, interval);
drop function if exists reset_site_user_password(
                                        bigint, varchar, varchar, interval);
drop function if exists random_url(int);
reset client_min_messages;

-- multiply length by 4/3 and round up to the nearest multiple of 4
-- to get the length of the string
create function random_url(length int) returns varchar as $$
declare
    url varchar;
begin
    url := encode(public.gen_random_bytes(length) ,'base64');
    url := replace(url, '/', '_');
    url := replace(url, '+', '-');
    return url;
end;
$$ language plpgsql;
grant execute on function random_url(int) to file_host_group;

create function create_registration_confirmation_entry(
    v_site_user_id bigint) returns varchar as $$
declare
    v_url varchar;
begin
    loop
    begin
        select random_url(18) into v_url;
        insert into registration_confirmation (site_user_id, url)
            values (v_site_user_id, v_url);
        return v_url;
        exception when unique_violation then --loop again
    end;
    end loop;
end;
$$ language plpgsql;
revoke execute on function
    create_registration_confirmation_entry(
        v_site_user_id bigint) from public;
grant execute on function
    create_registration_confirmation_entry(
        v_site_user_id bigint) to file_host_group;

create function confirm_registration(
    v_site_user_id bigint,
    v_confirmation_url varchar,
    v_expire_after interval) returns varchar as $$
begin
    perform from registration_confirmation inner join site_user
        on registration_confirmation.site_user_id = site_user.site_user_id
        where site_user.site_user_id = v_site_user_id
        and url = v_confirmation_url
        and now_utc() < creation_time + v_expire_after
        and redeemed = false;
    if not found then
        return 'failure_wrong_id';
    end if;
    update site_user set status_id = 2
        where site_user_id = v_site_user_id;
    update registration_confirmation set redeemed = true
        where site_user_id = v_site_user_id;
    return 'success';
end;
$$ language plpgsql;
revoke execute on function
    confirm_registration(bigint, varchar, interval) from public;
grant execute on function
    confirm_registration(bigint, varchar, interval) to file_host_group;

create function create_password_reset_entry(
    v_email varchar,
    v_ip cidr,
    v_expire_after interval) returns record as $$
declare
    v_password_reset_entry record;
    v_site_user_id bigint;
    v_ret record;
    v_url text;
begin
    select site_user_id into v_site_user_id from site_user
        where email = v_email and status_id < 4;
    if v_site_user_id is null then
        select 'failure_not_account', null::bigint, null::text into v_ret;
        return v_ret;
    end if;
    select * into v_password_reset_entry from password_reset
        where site_user_id = v_site_user_id and redeemed = false
        and now_utc() < date_added + v_expire_after;
    if not found then
        loop
        begin
            select random_url(18) into v_url;
            insert into password_reset (site_user_id, ip, url)
                values (v_site_user_id, v_ip, v_url);
            select 'success', v_site_user_id, v_url  into v_ret;
            return v_ret;
            exception when unique_violation then -- loop again
        end;
        end loop;
    end if;
    select 'failure_existing_request', null::bigint, null::text into v_ret;
    return v_ret;
end;
$$ language plpgsql;
revoke execute on function
    create_password_reset_entry(varchar, cidr, interval) from public;
grant execute on function
    create_password_reset_entry(varchar, cidr, interval) to file_host_group;

create function reset_site_user_password(
    v_site_user_id bigint,
    v_reset_url varchar,
    v_new_password_hash varchar,
    v_expire_after interval) returns varchar as $$
declare
    v_entry record;
begin
    select * into v_entry from password_reset
    where site_user_id = v_site_user_id and url = v_reset_url;
    if not found then
        return 'failure_wrong_id';
    else
        select * into v_entry from password_reset
        where site_user_id = v_site_user_id
        order by password_reset_id desc limit 1;
        if v_entry.date_added + v_expire_after < now_utc() then
            return 'failure_expired';
        elseif v_entry.redeemed is true then
            return 'failure_redeemed';
        elseif v_entry.url <> v_reset_url then
            select * into v_entry from password_reset
            where site_user_id = v_site_user_id and url = v_reset_url;
            if v_entry.redeemed is true and
                v_entry.date_added + v_expire_after > now_utc() then
                return 'failure_redeemed_exisiting_request';
            else
                return 'failure_expired';
            end if;
        else
            update site_user set password = v_new_password_hash
            where site_user_id = v_site_user_id;

            update password_reset set redeemed = true
            where password_reset_id = v_entry.password_reset_id;
            return 'success';
        end if;
    end if;
end;
$$ language plpgsql;
revoke execute on function
    reset_site_user_password(bigint, varchar, varchar, interval) from public;
grant execute on function
    reset_site_user_password(bigint, varchar, varchar, interval)
    to file_host_group;

commit;

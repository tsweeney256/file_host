import os
import re
import unittest
from functools import partial
from file_host import create_app
from werkzeug.exceptions import NotFound
import file_host.blueprints as blueprints
from file_host.helpers import get_db_connection
from flask import (current_app, g, make_response, _request_ctx_stack,
                   session, url_for)


user_tables = [
    'login',
    'password_reset',
    'registration_confirmation',
    'site_user',
]


class TestRequestWrapper():

    def __init__(self, context, view, *args, **kwargs):
        self.context = context
        self._view = view
        self._args = args
        self._kwargs = kwargs

    def __enter__(self):
        self.context.__enter__()
        self.response = make_response(self._view(*self._args, **self._kwargs))
        return self

    def __exit__(self, *args):
        self.context.__exit__(*args)

    def run(self):
        with self:
            pass

    def follow_redirect(self):
        return follow_redirect(self.context, self.response)


def follow_redirect(request_context, response):
    # This is probably hacky and bad, but I was left with no choice
    # TODO: Make this not hacky and bad
    app = request_context.app
    environ = request_context.request.environ
    endpoint, kwargs = request_context.url_adapter.match(
        response.location, method='GET')
    original_method = environ['REQUEST_METHOD']
    environ['REQUEST_METHOD'] = 'GET'
    ret = app.make_response(app.view_functions[endpoint](**kwargs))
    environ['REQUEST_METHOD'] = original_method
    return ret


class MyTests(unittest.TestCase):

    def assertFlashed(self, expected_flashes, assert_no_extra_flashes=True,
                      request_context=None):
        """Must be in a request context to call this function
        args:
        expected_flashes: may be an iterable of flashes of the form
            ('category', 'message'), a single flash of the mentioned form,
            or None
        assert_no_extra_flashes: defaults to True
        request_context: the request context. defaults to the top request
            context on the stack"""

        if request_context is None:
            request_context = _request_ctx_stack.top
        flashes = request_context.flashes
        flashes = [] if flashes is None else flashes
        num_expected_flashes = 0
        if expected_flashes is not None:
            if isinstance(expected_flashes[0], str):
                self.assertIn(expected_flashes, flashes)
                num_expected_flashes = 1
            else:
                for ef in expected_flashes:
                    self.assertIn(ef, flashes)
                    num_expected_flashes = len(expected_flashes)
        if assert_no_extra_flashes:
            num_flashes = 0 if flashes is None else len(flashes)
            assert_msg = ('Extra flashed messages. Flashed messages are {}'
                          .format(str(flashes)))
            assert num_expected_flashes == num_flashes, assert_msg

    def assertRedirect(self, response, page, code=None):
        match = re.match(
            'http(s)?://{}'.format(current_app.config['SERVER_NAME']),
            response.location)
        loc = (response.location if match is None
               else response.location[match.end(0):])
        self.assertEqual(loc, url_for(page, _external=False))
        if code:
            self.assertEqual(response.status_code, code)
        else:
            self.assertIn(response.status_code,
                          [300, 301, 302, 303, 304, 305, 307])

    def assert_post_registration(self, flashes, redirect_loc,
                                 update_user_id=True, status_code=200,
                                 **kwargs):
        with self.post_registration(**kwargs) as ret:
            response = ret.response
            if update_user_id:
                self.site_user_id += 1
            if redirect_loc:
                self.assertRedirect(ret.response, redirect_loc)
                response = ret.follow_redirect()
            self.assertFlashed(flashes)
            self.assertEqual(response.status_code, status_code)
            return g.get('registration_confirmation_url', None)

    def assert_get_confirm_registration(
            self, flashes, site_user_id, confirmation_url=None,
            redirect_loc=None, status_code=200, email=None, password=None,
            create_user=False):
        new_url = None
        if create_user:
            self.post_registration(email, password).run()
            new_url = g.registration_confirmation_url
            self.site_user_id += 1
        try:
            with self.get_confirm_registration(
                    site_user_id,
                    confirmation_url if confirmation_url else new_url) as ret:
                response = ret.response
                if redirect_loc:
                    self.assertRedirect(ret.response, redirect_loc)
                    response = ret.follow_redirect()
                self.assertFlashed(flashes)
                self.assertEqual(response.status_code, status_code)
                return confirmation_url if confirmation_url else new_url
        except NotFound:
            self.assertEqual(status_code, 404)
        return None

    def assert_post_login(self, flashes, redirect_loc, email, password,
                          status_code=200, create_user=False):
        if create_user:
            self.post_registration(email, password).run()
            self.site_user_id += 1
        with self.post_login(email, password) as ret:
            response = ret.response
            if redirect_loc:
                self.assertRedirect(ret.response, redirect_loc)
                self.assertEqual(self.site_user_id, session['site_user_id'])
                response = ret.follow_redirect()
            else:
                self.assertNotIn('site_user_id', session)
            self.assertFlashed(flashes)
            self.assertEqual(response.status_code, status_code)

    def assert_post_request_password_reset(
            self, flashes, email, password=None,
            status_code=200, create_user=False):
        if create_user:
            self.post_registration(email, password).run()
            self.site_user_id += 1
        with self.post_request_password_reset(email) as ret:
            self.assertFlashed(flashes)
            self.assertEqual(ret.response.status_code, status_code)
            if hasattr(g, 'password_reset_url'):
                return g.password_reset_url
            else:
                return None

    def assert_post_reset_password(
            self, flashes, site_user_id, password, reset_url=None,
            email=None, login=False, password_confirmation=None,
            redirect_loc=None, status_code=200, create_user=False,
            request_reset=False):
        if create_user:
            self.post_registration(email, 'original password').run()
            self.site_user_id += 1
        generated_reset_url = None
        if request_reset:
            with self.post_request_password_reset(email):
                generated_reset_url = g.password_reset_url
        if reset_url is None:
            reset_url = generated_reset_url
        with self.post_reset_password(site_user_id, reset_url, password,
                                      password_confirmation) as ret:
            response = ret.response
            if redirect_loc:
                self.assertRedirect(ret.response, redirect_loc)
                response = ret.follow_redirect()
            self.assertEqual(response.status_code, status_code)
            if login:
                self.assertEqual(site_user_id, session['site_user_id'])
            self.assertFlashed(flashes)
        if login:
            self.assert_post_login(
                flashes=None, redirect_loc='index.index',
                email=email, password=password)
        return generated_reset_url

    def post_registration(self, email, password, password_confirmation=None):
        if password_confirmation is None:
            password_confirmation = password
        ctx = self.app.test_request_context(
            url_for('user.register'),
            method='POST',
            data={
                'email': email,
                'password': password,
                'password_confirmation': password_confirmation
            })
        return TestRequestWrapper(ctx, blueprints.user.views.register)

    def get_confirm_registration(self, site_user_id, confirmation_url):
        ctx = self.app.test_request_context(
            url_for('user.confirm_registration',
                    site_user_id=site_user_id,
                    confirmation_url=confirmation_url))
        return TestRequestWrapper(
            ctx, blueprints.user.views.confirm_registration,
            site_user_id=site_user_id, confirmation_url=confirmation_url)

    def post_login(self, email, password):
        ctx = self.app.test_request_context(
            url_for('user.login'),
            method='POST',
            data={
                'email': email,
                'password': password,
            })
        return TestRequestWrapper(ctx, blueprints.user.views.login)

    def post_request_password_reset(self, email):
        ctx = self.app.test_request_context(
            url_for('user.request_password_reset'),
            method='POST',
            data={
                'email': email
            })
        return TestRequestWrapper(
            ctx, blueprints.user.views.request_password_reset)

    def post_reset_password(self, site_user_id, reset_url, password,
                            password_confirmation=None):
        if password_confirmation is None:
            password_confirmation = password
        ctx = self.app.test_request_context(
            url_for('user.reset_password', site_user_id=site_user_id,
                    reset_url=reset_url),
            method='POST',
            data={
                'password': password,
                'password_confirmation': password_confirmation
            })
        return TestRequestWrapper(ctx, blueprints.user.views.reset_password,
                                  site_user_id=site_user_id,
                                  reset_url=reset_url)

    def setUp(self):
        self.app = create_app(
            os.path.dirname(os.path.realpath(__file__)) + '/settings.py')
        self.app_context = self.app.app_context()
        self.app_context.push()
        self.client = self.app.test_client()
        self.url_adapter = self.app.url_map.bind(
            self.app.config['SERVER_NAME'])
        self.site_user_id = 0

    def tearDown(self):
        self.app_context.pop()

        # Some might say its overkill to create a whole app just to load
        # superuser db settings. To that I say:
        super_app = create_app(os.path.dirname(os.path.realpath(__file__)) +
                               '/superuser_settings.py')
        with super_app.app_context():
            with get_db_connection() as db:
                cursor = db.cursor()
                for table in user_tables:
                    cursor.execute('delete from {};'.format(table))
                    cursor.execute('alter sequence {}_{}_id_seq restart;'
                                   .format(table, table))

    def test_password_confirmation(self):
        with self.app.test_request_context():
            is_valid_password = blueprints.user.views._is_valid_password
            self.assertFalse(is_valid_password('', ''))
            self.assertFalse(is_valid_password('a', 'A'))
            self.assertFalse(is_valid_password('a', 'b'))

    def _assert_multi_func(self, func, flashes, flash_append, data):
        """Template for functions like assert_malformed_email()"""

        if flashes is None:
            flashes = []
        flashes.append(flash_append)
        for d in data:
            func(flashes=flashes, **d)

    def assert_malformed_email(self, func, flashes=None):
        """
        Runs provided function object while assigning to it an email kwarg
        and the provided flashes kwarg with an additional appended message.
        flashes may be a list of flashes of the form ('category', 'message')
        or it may be None, in which case this function will create the list.
        """
        flash_append = ('message', 'Improperly formatted email')
        test_emails = ['bad.email', 'bademail', 'b.ad.em.ma.@il']
        data = [{'email': val} for val in test_emails]
        self._assert_multi_func(func, flashes, flash_append, data)

    def assert_passwords_mismatch(self, func, flashes=None):
        """works exactly like assert_malformed_email"""

        flash_append = ('message', 'Passwords do not match')
        test_passwords = ['a', 'A', 'a', 'A']
        test_password_confirmations = ['b', 'b', 'B', 'B']
        data = [{'password': a, 'password_confirmation': b} for a, b in
                zip(test_passwords, test_password_confirmations)]
        self._assert_multi_func(func, flashes, flash_append, data)

    def assert_password_blank(self, func, flashes=None):
        """works exactly like assert_malformed_email"""

        flash_append = ('message', 'Password may not be empty')
        data = [{'password': ''}]
        self._assert_multi_func(func, flashes, flash_append, data)

    def test_index(self):
        ret = self.client.get(url_for('index.index'))
        self.assertRedirect(ret, 'user.login')
        with self.app.test_request_context(url_for('index.index')):
            session['site_user_id'] = 1
            response = make_response(blueprints.index.views.index())
            response = self.app.process_response(response)
        self.assertEqual(response.status_code, 200)

    def test_registration(self):
        success_flash = ('message', 'A confirmation email has been sent. '
                         'Please check your inbox.')
        duplicate_flash = ('message',
                           'This email is already associated with an account')
        user, password = 'blah@localhost', 'blah'
        user2, password2 = 'hooplah@localhost', 'hooplah'
        # page is available
        resp = self.client.get(url_for('user.register'))
        self.assertEqual(resp.status_code, 200)
        # registration works when empty
        self.assert_post_registration(
            flashes=success_flash, redirect_loc='user.login',
            email=user, password=password)
        # no duplicates allowed
        self.assert_post_registration(
            flashes=duplicate_flash, redirect_loc=None,
            email=user, password=password)
        # registration works when not empty and after previous failure
        self.assert_post_registration(
            flashes=success_flash, redirect_loc='user.login',
            email=user2, password=password2)
        # reject malformed emails
        func = partial(self.assert_post_registration, redirect_loc=None,
                       update_user_id=False, password='password')
        self.assert_malformed_email(func)
        # reject password mismatches
        func = partial(self.assert_post_registration, redirect_loc=None,
                       update_user_id=False, email='pass.word@mismatch')
        self.assert_passwords_mismatch(func)
        self.assert_password_blank(func)

        # TODO: Test registration prevention when logged in

    def test_confirm_registration(self):
        success_flash = ('message', 'Registration confirmed. You have '
                         'automatically been signed in')
        user, password = 'blah@localhost', 'blah'
        user2, password2 = 'hooplah@localhost', 'hooplah'

        # fails when bad url and no users
        self.assert_get_confirm_registration(
            flashes=None, site_user_id=1, confirmation_url='bad',
            status_code=404)

        # confirm first user
        first_url = self.assert_get_confirm_registration(
            flashes=success_flash, site_user_id=self.site_user_id+1,
            email=user, password=password, redirect_loc='index.index',
            create_user=True)

        # fails when already redeemed
        self.assert_get_confirm_registration(
            flashes=None, site_user_id=self.site_user_id+1,
            confirmation_url=first_url, status_code=404)

        # fails when bad url and one user
        self.assert_get_confirm_registration(
            flashes=None, site_user_id=1, confirmation_url='bad',
            status_code=404)

        # fails when correct user and bad confirmation url
        self.post_registration(user2, password2).run()
        second_url = g.registration_confirmation_url
        self.site_user_id += 1
        self.assert_get_confirm_registration(
            flashes=None, site_user_id=self.site_user_id,
            confirmation_url='bad', status_code=404)

        # fails when expired
        original_expiration = current_app.config['CONFIRM_EXPR']
        current_app.config['CONFIRM_EXPR'] = '0 days'
        self.assert_get_confirm_registration(
            flashes=None, site_user_id=self.site_user_id,
            confirmation_url=second_url, status_code=404)
        current_app.config['CONFIRM_EXPR'] = original_expiration
        # confirm second user
        self.assert_get_confirm_registration(
            flashes=success_flash, site_user_id=self.site_user_id,
            confirmation_url=second_url, redirect_loc='index.index')

    def test_login(self):
        success_flash = None
        failure_flash = ('message', 'Invalid email or password')

        # page is available
        resp = self.client.get(url_for('user.register'))
        self.assertEqual(resp.status_code, 200)
        # login fails if no accounts exist
        self.assert_post_login(flashes=failure_flash, redirect_loc=None,
                               email='doesnt', password='exist')
        # test login of first user
        test_user, test_pass = 'blah@localhost', 'blah'
        self.assert_post_login(flashes=success_flash,
                               redirect_loc='index.index', create_user=True,
                               email=test_user, password=test_pass)
        # login fails with non-existent account with non-empty database
        self.assert_post_login(flashes=failure_flash, redirect_loc=None,
                               email='doesnt', password='exist')
        # test login of second user
        test_user2, test_pass2 = 'hooplah@localhost', 'hooplah'
        self.assert_post_login(flashes=success_flash,
                               redirect_loc='index.index', create_user=True,
                               email=test_user2, password=test_pass2)
        # test completely wrong password
        self.assert_post_login(flashes=failure_flash, redirect_loc=None,
                               email=test_user, password='wrong')
        # test logging in with different user's password
        self.assert_post_login(flashes=failure_flash, redirect_loc=None,
                               email=test_user, password=test_user2)
        # TODO: Test preventing login when already logged in

    def test_request_password_reset(self):
        nonexistent_flash = ('message',
                             'That email is not associated with any account')
        success_flash = ('message',
                         'Your password reset request has been sent. '
                         'Please check your email for further instructions.')
        existing_request = ('message',
                            'A request to reset the given account\'s password '
                            'has already been filed. Please check your email '
                            'for the instructions to reset your password.')

        # page is available
        resp = self.client.get(url_for('user.request_password_reset'))
        self.assertEqual(resp.status_code, 200)
        # test request for nonexistent account when empty
        user, password = 'blah@localhost', 'blah'
        self.assert_post_request_password_reset(
            flashes=nonexistent_flash, email=user)
        # test request for existing account
        self.assert_post_request_password_reset(
            flashes=success_flash, email=user, password=password,
            create_user=True)
        # test when active request is unclaimed
        self.assert_post_request_password_reset(
            flashes=existing_request, email=user)
        # test request for nonexistent account again when not empty
        self.assert_post_request_password_reset(
            flashes=nonexistent_flash, email='nonexistent')
        # test request for sexond existing account
        user2, password2 = 'hooplah@localhost', 'hooplah'
        self.assert_post_request_password_reset(
            flashes=success_flash, email=user2, password=password2,
            create_user=True)
        # test request when active request is unclaimed for second user
        self.assert_post_request_password_reset(
            flashes=existing_request, email=user)

    def test_reset_password(self):
        user, password = 'blah@localhost', 'blah'
        invalid_params = ('message',
                          'Invalid parameters. Future invalid attempts will '
                          'result in a ban')
        success = ('message',
                   'Your password has been reset and you have been signed in.')
        redeemed = ('message',
                    'This password reset URL has already been used to reset '
                    'your password. Please request another reset.')
        request_success = ('message',
                           'Your password reset request has been sent. '
                           'Please check your email for further instructions.')
        redeemed_existing = ('message',
                             'This password reset URL has already been used '
                             'to reset your password. You have already filed '
                             'a new request to reset your password. Please '
                             'check your email for further instructions.')
        expired_request = ('message', 'This password reset URL has already '
                           'expired. Please request another reset.')

        true_reset_time = current_app.config['CONFIRM_EXPR']
        # page is available
        resp = self.client.get(
            url_for('user.reset_password', site_user_id=0, reset_url=0))
        self.assertEqual(resp.status_code, 200)
        # block invalid site_user_id and reset_url
        self.assert_post_reset_password(
            flashes=invalid_params, site_user_id=0, reset_url='0',
            email='nonexistent', password='whatever')
        # block expired request
        current_app.config['CONFIRM_EXPR'] = '0 days'
        first_url = self.assert_post_reset_password(
            flashes=expired_request, site_user_id=self.site_user_id+1,
            password=password, email=user, create_user=True,
            request_reset=True, redirect_loc='user.request_password_reset')
        current_app.config['CONFIRM_EXPR'] = true_reset_time
        # Reset password
        self.assert_post_reset_password(
            flashes=success, site_user_id=self.site_user_id, password="new",
            email=user, login=True, reset_url=first_url,
            redirect_loc='index.index')
        # block redeemed request
        self.assert_post_reset_password(
            flashes=redeemed, site_user_id=self.site_user_id,
            password=password, reset_url=first_url,
            redirect_loc='user.request_password_reset')
        # block invalid reset_url with existing user_id and no valid request
        self.assert_post_reset_password(
            flashes=invalid_params, site_user_id=self.site_user_id,
            password=password, reset_url='0')
        # block invalid reset_url with existing user_id and valid request
        second_url = self.assert_post_request_password_reset(
            flashes=request_success, email=user)
        self.assert_post_reset_password(
            flashes=invalid_params, site_user_id=self.site_user_id,
            password=password, reset_url='0')
        # block redeemed request when valid request exists
        self.assert_post_reset_password(
            flashes=redeemed_existing, site_user_id=self.site_user_id,
            password=password, reset_url=first_url)
        # Reset second password
        self.assert_post_reset_password(
            flashes=success, site_user_id=self.site_user_id,
            password=password, reset_url=second_url,
            redirect_loc='index.index')
        # Reset password of second user
        user2, password2 = 'user2@localhost', 'password2'
        self.assert_post_reset_password(
            flashes=success, site_user_id=self.site_user_id+1, email=user2,
            password=password2, create_user=True, request_reset=True,
            redirect_loc='index.index')
        # block older reset_urls when newer exist
        current_app.config['CONFIRM_EXPR'] = '0 days'
        loop_urls = []
        num_loops = 5
        for i in range(num_loops):
            loop_urls.append(self.assert_post_request_password_reset(
                flashes=request_success, email=user2))
        current_app.config['CONFIRM_EXPR'] = true_reset_time
        for i in range(num_loops-1):
            self.assert_post_reset_password(
                flashes=expired_request, site_user_id=self.site_user_id,
                password="something", reset_url=loop_urls[i],
                redirect_loc='user.request_password_reset')
        # Reset newest password when older ones exist
        self.assert_post_reset_password(
            flashes=success, site_user_id=self.site_user_id,
            password="new", reset_url=loop_urls[-1],
            redirect_loc='index.index')
        # Reject password mismatch and blank passwords
        pass_mismatch_url = self.assert_post_request_password_reset(
            flashes=request_success, email="new@localhost", password="hooplah",
            create_user=True)
        func = partial(self.assert_post_reset_password, redirect_loc=None,
                       reset_url=pass_mismatch_url,
                       site_user_id=self.site_user_id)
        self.assert_passwords_mismatch(func)
        self.assert_password_blank(func)


if __name__ == '__main__':
    unittest.main()

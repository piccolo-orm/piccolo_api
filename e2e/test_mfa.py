from playwright.async_api import Page

from .pages import LoginPage, MFASetupPage, RegisterPage


def test_mfa_signup(page: Page, mfa_app):
    """
    Make sure we create an account and sign up for MFA.
    """
    register_page = RegisterPage(page=page)
    register_page.reset()
    register_page.login()

    login_page = LoginPage(page=page)
    login_page.reset()
    login_page.login()

    mfa_setup_page = MFASetupPage(page=page)
    mfa_setup_page.reset()

    # Test an incorrect password
    # TODO - assert response code is correct
    mfa_setup_page.register(password="fake_password_123")

    # Test the correct password
    # TODO - make sure it navigated to the right page
    mfa_setup_page.register()

    mfa_setup_page.reset()

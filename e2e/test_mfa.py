from playwright.async_api import Page

from .pages import LoginPage, MFARegisterPage, RegisterPage


def test_login(page: Page, mfa_app):
    """
    Make sure we can register, sign up for MFA.
    """
    register_page = RegisterPage(page=page)
    register_page.reset()
    register_page.login()

    login_page = LoginPage(page=page)
    login_page.reset()
    login_page.login()

    mfa_register_page = MFARegisterPage(page=page)
    mfa_register_page.reset()

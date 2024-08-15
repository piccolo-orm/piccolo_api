"""
By using pages we can make out test more scalable.

https://playwright.dev/docs/pom
"""

from playwright.sync_api import Page


class LoginPage:
    url = "http://localhost:8000/login/"

    def __init__(self, page: Page):
        self.page = page
        self.username_input = page.locator('input[name="username"]')
        self.password_input = page.locator('input[name="password"]')
        self.button = page.locator("button")

    def reset(self):
        self.page.goto(self.url)

    def login(self):
        self.username_input.fill("piccolo")
        self.password_input.fill("piccolo123")
        self.button.click()


class RegisterPage:
    url = "http://localhost:8000/register/"

    def __init__(self, page: Page):
        self.page = page
        self.username_input = page.locator("[name=username]")
        self.email_input = page.locator("[name=email]")
        self.password_input = page.locator("[name=password]")
        self.confirm_password_input = page.locator("[name=confirm_password]")
        self.button = page.locator("button")

    def reset(self):
        self.page.goto(self.url)

    def login(self):
        self.username_input.fill("piccolo")
        self.email_input.fill("test@piccolo-orm.com")
        self.password_input.fill("piccolo123")
        self.confirm_password_input.fill("piccolo123")
        self.button.click()


class MFARegisterPage:
    url = "http://localhost:8000/private/mfa-register/"

    def __init__(self, page: Page):
        self.page = page

    def reset(self):
        self.page.goto(self.url)

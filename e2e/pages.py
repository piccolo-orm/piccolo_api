"""
By using pages we can make out test more scalable.

https://playwright.dev/docs/pom
"""

from playwright.sync_api import Page

USERNAME = "piccolo"
PASSWORD = "piccolo123"


class LoginPage:
    url = "http://localhost:8000/login/"

    def __init__(self, page: Page):
        self.page = page
        self.username_input = page.locator('input[name="username"]')
        self.password_input = page.locator('input[name="password"]')
        self.button = page.locator("button")

    def reset(self):
        self.page.goto(self.url)

    def login(self, username: str = USERNAME, password: str = PASSWORD):
        self.username_input.fill(username)
        self.password_input.fill(password)
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

    def login(self, username: str = USERNAME, password: str = PASSWORD):
        self.username_input.fill(username)
        self.email_input.fill("test@piccolo-orm.com")
        self.password_input.fill(password)
        self.confirm_password_input.fill(password)
        self.button.click()


class MFASetupPage:
    url = "http://localhost:8000/private/mfa-setup/"

    def __init__(self, page: Page):
        self.page = page
        self.password_input = page.locator("[name=password]")
        self.button = page.locator("button")

    def reset(self):
        self.page.goto(self.url)

    def register(self, password: str = PASSWORD):
        self.password_input.fill(password)
        self.button.click()

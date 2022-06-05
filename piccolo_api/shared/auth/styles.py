from dataclasses import dataclass


@dataclass
class Styles:
    """
    Used to set CSS styles in endpoints such as
    :func:`session_login <piccolo_api.session_auth.endpoints.session_login>`,
    :func:`session_logout <piccolo_api.session_auth.endpoints.session_logout>`,
    and :func:`register <piccolo_api.register.endpoints.register>`.

    """

    background_color: str = "#eef2f5"
    foreground_color: str = "white"
    text_color: str = "black"
    error_text_color: str = "red"
    button_color: str = "#419EF8"
    button_text_color: str = "white"

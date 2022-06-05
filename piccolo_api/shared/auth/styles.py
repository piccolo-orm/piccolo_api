from dataclasses import dataclass


@dataclass
class Styles:
    background_color: str = "#eef2f5"
    foreground_color: str = "white"
    text_color: str = "black"
    error_text_color: str = "red"
    button_color: str = "#419EF8"
    button_text_color: str = "white"

import math
import secrets
import string
import typing as t

DEFAULT_CHARACTERS = string.ascii_lowercase + string.digits


def _get_random_string(length: int, characters: t.Sequence[str]) -> str:
    """
    :param length:
        How long to make the string.
    :param characters:
        Which characters to randomly pick from.

    """
    return "".join(secrets.choice(characters) for _ in range(length))


def generate_recovery_code(
    length: int = 12,
    characters: t.Sequence[str] = DEFAULT_CHARACTERS,
    separator: str = "-",
):
    """
    :param length:
        How long the recovery code should be, excluding the separator. Must
        be at least 10 (it's unusual for a recovery code to be shorter than
        this).
    :param characters:
        Which characters to randomly pick from. Recovery codes tend to be
        case insensitive, and just use a-z and 0-9 (presumably to make them
        less error prone for users).
    :param separator:
        The recovery code will have this character in the middle, making it
        easier for users to read (e.g. ``abc123-xyz789``). Specify an empty
        string if you want to disable this behaviour.

    """
    if length < 10:
        raise ValueError("The length must be at least 10.")

    random_string = _get_random_string(length=length, characters=characters)

    if separator:
        split_at = math.ceil(length / 2)

        return separator.join(
            [random_string[:split_at], random_string[split_at:]]
        )

    return random_string

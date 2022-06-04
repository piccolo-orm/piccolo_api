import inspect
import typing as t
from dataclasses import dataclass

import httpx

Dict = t.Dict[str, t.Any]
Response = t.Optional[str]
Validator = t.Union[
    t.Callable[[Dict], Response],
    t.Callable[[Dict], t.Awaitable[Response]],
]


@dataclass
class Captcha:
    """
    Used to create CAPTCHA's for adding bot protection to endpoints.

    :param form_html:
        Any HTML which needs inserting into the form to make the CAPTCHA work.
    :param validator:
        A callback (either an async or normal function), which is passed the
        form data, and is used to verify with the CAPTCHA provider's API that
        the token is valid. To indicate that validation has failed, return a
        string containing an error message which will be shown to the user.

    """

    form_html: t.Optional[str] = None
    validator: t.Optional[Validator] = None

    async def validate(self, form_data: t.Dict[str, t.Any]) -> t.Optional[str]:
        if self.validator:
            if inspect.iscoroutinefunction(self.validator):
                return await self.validator(form_data)  # type: ignore
            elif inspect.isfunction(self.validator):
                return self.validator(form_data)

        return None


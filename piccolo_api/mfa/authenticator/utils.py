from __future__ import annotations

import typing as t
from base64 import b64encode
from io import BytesIO

if t.TYPE_CHECKING:  # pragma: no cover
    import qrcode


def get_qrcode() -> qrcode:  # pragma: no cover
    try:
        import qrcode
    except ImportError as e:
        print(
            "Install pip install piccolo_api[authenticator] to use this "
            "feature."
        )
        raise e

    return qrcode


def get_b64encoded_qr_image(data: str) -> str:
    """
    Creates a QR code from ``data``, and returns a base64 PNG image, which can
    be used in a HTML document as follows:

    .. code-block:: html

        <img src="data:image/png;base64,{{ qrcode_image }}" />

    """
    qrcode = get_qrcode()

    qr = qrcode.QRCode(version=1, box_size=4, border=5)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffered = BytesIO()
    img.save(buffered)
    return b64encode(buffered.getvalue()).decode("utf-8")

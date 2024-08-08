from base64 import b64encode
from io import BytesIO

import qrcode


def get_b64encoded_qr_image(data):
    qr = qrcode.QRCode(version=1, box_size=4, border=5)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffered = BytesIO()
    img.save(buffered)
    return b64encode(buffered.getvalue()).decode("utf-8")

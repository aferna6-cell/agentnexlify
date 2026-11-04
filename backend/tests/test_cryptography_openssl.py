"""Official cryptography wheels must embed OpenSSL 4.0.3 or newer.

50.0.1 is no longer an admissible install. This checks the wheel that
pip actually imported, not the requirements text.
"""

import cryptography
from cryptography.hazmat.backends.openssl import backend


def test_installed_cryptography_embeds_openssl_4_0_3():
    parts = tuple(int(piece) for piece in cryptography.__version__.split(".")[:3])
    assert parts >= (50, 0, 2)

    text = backend.openssl_version_text()
    openssl_parts = tuple(int(piece) for piece in text.split()[1].split(".")[:3])
    assert openssl_parts >= (4, 0, 3), text

from unittest.mock import patch

def test_it():
    with patch('backend.services.embeddings.httpx.AsyncClient'):
        pass

from backend.services.managed_agents import VALUE
from unittest.mock import patch

def test_it():
    with patch('backend.services.managed_agents.time.sleep'):
        assert VALUE == 1

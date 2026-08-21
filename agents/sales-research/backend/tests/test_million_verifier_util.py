import pytest
from unittest.mock import patch, MagicMock
from utils.email_verifier import verify_email

@pytest.mark.asyncio
async def test_verify_email_ok():
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"status": "ok"}
    
    with patch("httpx.AsyncClient.get", return_value=mock_response):
        status = await verify_email("test@example.com", "fake_key")
        assert status == "ok"

@pytest.mark.asyncio
async def test_verify_email_invalid():
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"status": "invalid"}
    
    with patch("httpx.AsyncClient.get", return_value=mock_response):
        status = await verify_email("test@example.com", "fake_key")
        assert status == "invalid"

@pytest.mark.asyncio
async def test_verify_email_error():
    with patch("httpx.AsyncClient.get", side_effect=Exception("API Error")):
        status = await verify_email("test@example.com", "fake_key")
        assert status == "error"

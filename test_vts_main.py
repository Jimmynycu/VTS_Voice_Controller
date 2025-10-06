
import asyncio
import pytest
from unittest.mock import MagicMock, AsyncMock
import sys

# Mock the modules that will be imported by the script we are testing
# This is necessary because we are in a different environment
sys_modules = {
    "vts_client": MagicMock(),
    "open_llm_vtuber.asr.sherpa_onnx_asr": MagicMock(),
    "sounddevice": MagicMock()
}

@pytest.fixture
def mock_imports(monkeypatch):
    for name, mock in sys_modules.items():
        monkeypatch.setitem(sys.modules, name, mock)
    return sys_modules

# We need to import the main script after mocking the imports
@pytest.fixture
def vts_main(mock_imports):
    from vts_main import asr_callback, main
    return {
        "asr_callback": asr_callback,
        "main": main
    }

@pytest.mark.asyncio
async def test_asr_callback_triggers_expression(vts_main, mock_imports):
    """Test that the asr_callback triggers a VTS expression when a keyword is found."""
    # 1. Setup
    # Get the mocked VTSClient instance
    mock_vts_client_instance = mock_imports['vts_client'].VTSClient.return_value
    mock_vts_client_instance.trigger_expression = AsyncMock()

    # Set the global vts_client and expression_map in the vts_main module
    import vts_main
    vts_main.vts_client = mock_vts_client_instance
    vts_main.expression_map = {
        "happy": "happy.exp3.json",
        "angry": "angry.exp3.json"
    }

    # 2. Call the function
    vts_main.asr_callback("I am so happy today!")

    # Allow the created task to run
    await asyncio.sleep(0)

    # 3. Assert
    mock_vts_client_instance.trigger_expression.assert_called_once_with("happy.exp3.json")

@pytest.mark.asyncio
async def test_asr_callback_no_trigger(vts_main, mock_imports):
    """Test that the asr_callback does not trigger an expression if no keyword is found."""
    # 1. Setup
    mock_vts_client_instance = mock_imports['vts_client'].VTSClient.return_value
    mock_vts_client_instance.trigger_expression = AsyncMock()

    import vts_main
    vts_main.vts_client = mock_vts_client_instance
    vts_main.expression_map = {
        "happy": "happy.exp3.json",
    }

    # 2. Call the function
    vts_main.asr_callback("This is a neutral sentence.")

    # 3. Assert
    mock_vts_client_instance.trigger_expression.assert_not_called()


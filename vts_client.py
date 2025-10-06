import asyncio
import os
from loguru import logger
import pyvts

class VTSClient:
    """Client to interact with the VTube Studio API."""

    def __init__(self, host: str, port: int, token_file: str):
        self.host = host
        self.port = port
        self.token_file = token_file
        self.vts = pyvts.vts(plugin_info={
            "plugin_name": "VTS Voice Controller",
            "developer": "Gemini",
            "authentication_token_path": self.token_file,
        })
        self.request_lock = asyncio.Lock() # New: Initialize a lock for serializing requests

    async def connect(self):
        """Connect to VTube Studio."""
        try:
            await self.vts.connect()
            logger.info("Connected to VTube Studio.")
        except Exception as e:
            logger.error(f"Failed to connect to VTube Studio: {e}")
            raise

    async def authenticate(self):
        """Authenticate with VTube Studio using the pyvts library's methods."""
        try:
            async with self.request_lock: # New: Use lock for authentication request
                await self.vts.request_authenticate_token()
                authenticated = await self.vts.request_authenticate()
            if authenticated:
                logger.info("Authenticated successfully with VTube Studio.")
            else:
                logger.warning("Authentication failed. Please allow the plugin in VTube Studio.")
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            raise

    async def trigger_expression(self, hotkey_id: str):
        """Trigger an expression in VTube Studio using its hotkey ID."""
        request = self.vts.vts_request.requestTriggerHotKey(hotkey_id)
        try:
            async with self.request_lock: # New: Use lock for trigger request
                response = await self.vts.request(request)
            # Check if the hotkeyID is present in the response data, indicating success
            if "hotkeyID" in response.get("data", {}):
                 logger.info(f"Triggered expression: {hotkey_id}")
            else:
                 # If hotkeyID is not in data, it might be an error or unexpected response
                 logger.warning(f"Failed to trigger expression {hotkey_id}. Response: {response}")
        except Exception as e:
            logger.error(f"Failed to trigger expression '{hotkey_id}': {e}")

    async def disconnect(self):
        """Disconnect from VTube Studio."""
        if self.vts.get_connection_status() == 1:
            await self.vts.close()
            logger.info("Disconnected from VTube Studio.")

    async def get_hotkey_list(self):
        """Get a list of all hotkeys for the current model."""
        logger.info("Requesting hotkey list from VTube Studio...")
        request = self.vts.vts_request.requestHotKeyList()
        try:
            async with self.request_lock: # New: Use lock for hotkey list request
                response = await self.vts.request(request)
            return response
        except Exception as e:
            logger.error(f"Failed to get hotkey list: {e}")
            raise

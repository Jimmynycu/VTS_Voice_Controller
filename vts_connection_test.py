import asyncio
import yaml
from vts_client import VTSClient
from loguru import logger

async def main():
    """
    Tests the connection to VTube Studio using settings from vts_config.yaml.
    """
    try:
        with open("vts_config.yaml", 'r') as f:
            config = yaml.safe_load(f)
        vts_settings = config['vts_settings']
        logger.info("Configuration loaded.")
    except FileNotFoundError:
        logger.error("vts_config.yaml not found. Please ensure the file exists.")
        return
    except Exception as e:
        logger.error(f"Error loading configuration: {e}")
        return

    vts_client = VTSClient(
        host=vts_settings['host'],
        port=vts_settings['port'],
        token_file=vts_settings['token_file']
    )

    try:
        await vts_client.connect()
        await vts_client.authenticate()
        logger.success("Successfully connected and authenticated with VTube Studio!")
    except Exception as e:
        logger.error(f"An error occurred during connection or authentication: {e}")
    finally:
        if vts_client:
            await vts_client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())

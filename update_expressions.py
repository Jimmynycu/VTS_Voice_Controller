import asyncio
import yaml
from vts_client import VTSClient
from loguru import logger

CONFIG_PATH = "vts_config.yaml"

async def main():
    """Connects to VTube Studio, fetches all expression hotkeys, and updates the config file."""
    # 1. Load Configuration to get connection settings
    try:
        with open(CONFIG_PATH, 'r') as f:
            config = yaml.safe_load(f)
        vts_settings = config['vts_settings']
        logger.info("Configuration loaded.")
    except FileNotFoundError:
        logger.error(f"Configuration file not found at {CONFIG_PATH}. Please create it.")
        return
    except Exception as e:
        logger.error(f"Error loading configuration: {e}")
        return

    vts_client = None
    try:
        # 2. Initialize and connect VTSClient
        vts_client = VTSClient(
            host=vts_settings['host'],
            port=vts_settings['port'],
            token_file=vts_settings['token_file']
        )
        await vts_client.connect()
        await vts_client.authenticate()

        # 3. Get the list of hotkeys
        hotkey_data = await vts_client.get_hotkey_list()

        if 'data' in hotkey_data and 'availableHotkeys' in hotkey_data['data']:
            logger.info(f"Found {len(hotkey_data['data']['availableHotkeys'])} hotkeys.")
            new_expressions = {}
            expression_count = 0

            # 4. Filter for expression hotkeys
            for hotkey in hotkey_data['data']['availableHotkeys']:
                if hotkey.get('type') == "ToggleExpression":
                    expression_count += 1
                    keyword = hotkey.get('name')
                    hotkey_id = hotkey.get('hotkeyID')
                    if keyword and hotkey_id:
                        # Use the hotkey name as the voice command keyword
                        new_expressions[keyword] = hotkey_id
                        logger.info(f"Found expression: '{keyword}' -> {hotkey_id}")
            
            if expression_count == 0:
                logger.warning("No expression hotkeys found in your VTube Studio model.")
                logger.warning("Please set up expressions with hotkeys in VTube Studio first.")
                return

            # 5. Update and save the configuration file
            config['expressions'] = new_expressions
            with open(CONFIG_PATH, 'w') as f:
                yaml.dump(config, f, default_flow_style=False, sort_keys=False)
            logger.success(f"Successfully updated {len(new_expressions)} expressions in {CONFIG_PATH}")

        else:
            logger.error("Could not retrieve hotkey list from VTube Studio.")
            logger.error(f"Response: {hotkey_data}")

    except Exception as e:
        logger.error(f"An error occurred: {e}")
    finally:
        if vts_client:
            await vts_client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())

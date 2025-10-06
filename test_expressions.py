import asyncio
import yaml
import importlib
import vts_client # Changed
import vts_main # Changed
from loguru import logger

CONFIG_PATH = "vts_config.yaml"

async def main():
    """A script to test VTS expression triggering by manually entering text."""
    
    # Reload modules to ensure latest code is used
    importlib.reload(vts_client)
    importlib.reload(vts_main)

    # 1. Load Configuration
    try:
        with open(CONFIG_PATH, 'r') as f:
            config = yaml.safe_load(f)
        vts_settings = config['vts_settings']
        expression_map = config.get('expressions', {})
        logger.info("Configuration loaded.")
        if not expression_map:
            logger.warning("No expressions found in config. Please run update_expressions.py first.")
            return
        logger.info(f"Keywords to test: {list(expression_map.keys())}")
    except Exception as e:
        logger.error(f"Error loading configuration: {e}")
        return

    vts_client_instance = None
    try:
        # 2. Initialize and connect VTSClient
        vts_client_instance = vts_client.VTSClient(
            host=vts_settings['host'],
            port=vts_settings['port'],
            token_file=vts_settings['token_file']
        )
        await vts_client_instance.connect()
        await vts_client_instance.authenticate()
        logger.success("Successfully connected to VTube Studio.")

        # 3. Start input loop
        logger.info("Enter a keyword to test, or type 'exit' to quit.")
        while True:
            try:
                # Run the blocking input() in a separate thread to not block asyncio
                test_text = await asyncio.to_thread(input, "Enter text: ")
                if test_text.lower() in ['exit', 'quit']:
                    break
                
                # 4. Call the asr_callback with the test text and required arguments
                await vts_main.asr_callback(test_text, vts_client_instance, expression_map)

            except (KeyboardInterrupt, EOFError):
                break

    except Exception as e:
        logger.error(f"An error occurred: {e}")
    finally:
        # 5. Disconnect
        if vts_client_instance:
            await vts_client_instance.disconnect()
        logger.info("Test finished.")

if __name__ == "__main__":
    asyncio.run(main())

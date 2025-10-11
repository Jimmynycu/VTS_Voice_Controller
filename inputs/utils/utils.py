import os
import aiohttp
import asyncio
import tarfile
from loguru import logger

async def ensure_model_downloaded_and_extracted(model_url: str, model_base_dir: str, progress_callback=None) -> str:
    """Downloads and extracts the ASR model if not already present."""
    model_name = model_url.split("/")[-1].replace(".tar.bz2", "")
    model_dir = os.path.join(model_base_dir, model_name)
    archive_path = os.path.join(model_base_dir, os.path.basename(model_url))

    if os.path.exists(model_dir) and os.path.exists(os.path.join(model_dir, "tokens.txt")):
        logger.info(f"✅ Model already extracted at {model_dir}.")
        return model_dir

    os.makedirs(model_base_dir, exist_ok=True)

    logger.info(f"Downloading ASR model from {model_url}...")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(model_url) as response:
                response.raise_for_status()
                total_size = int(response.headers.get('content-length', 0))
                downloaded_size = 0

                if progress_callback:
                    await progress_callback(0)

                with open(archive_path, 'wb') as f:
                    while True:
                        chunk = await response.content.read(8192)
                        if not chunk:
                            break
                        f.write(chunk)
                        downloaded_size += len(chunk)
                        if progress_callback and total_size > 0:
                            progress = int((downloaded_size / total_size) * 100)
                            await progress_callback(progress)

                if progress_callback:
                    await progress_callback(100)

        logger.info("Download complete.")

        logger.info(f"Extracting model to {model_dir}...")
        with tarfile.open(archive_path, "r:bz2") as tar:
            tar.extractall(path=model_base_dir)
        logger.info("Extraction complete.")

    except aiohttp.ClientError as e:
        logger.error(f"Failed to download model: {e}")
        raise
    except tarfile.TarError as e:
        logger.error(f"Failed to extract model: {e}")
        raise
    except Exception as e:
        logger.error(f"An unexpected error occurred during model download/extraction: {e}")
        raise
    finally:
        if os.path.exists(archive_path):
            os.remove(archive_path)

    return model_dir

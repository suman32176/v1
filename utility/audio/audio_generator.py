import edge_tts
import logging
import asyncio

async def generate_audio(text, output_filename):
    try:
        communicate = edge_tts.Communicate(text, "en-AU-WilliamNeural")
        await communicate.save(output_filename)
        logging.info(f"Audio generated successfully: {output_filename}")
    except Exception as e:
        logging.error(f"Error generating audio: {str(e)}")
        raise

async def generate_audio_with_retry(text, output_filename, max_retries=3):
    for attempt in range(max_retries):
        try:
            await generate_audio(text, output_filename)
            return
        except Exception as e:
            if attempt < max_retries - 1:
                logging.warning(f"Audio generation attempt {attempt + 1} failed. Retrying...")
                await asyncio.sleep(1)  # Wait for 1 second before retrying
            else:
                logging.error(f"All audio generation attempts failed.")
                raise
import os
import json
import edge_tts
import asyncio
import whisper_timestamped as whisper
from utility.audio.audio_generator import generate_audio
from utility.captions.timed_captions_generator import generate_timed_captions
from utility.video.background_video_generator import generate_video_url
from utility.render.render_engine import get_output_media
from utility.video.video_search_query_generator import getVideoSearchQueriesTimed, merge_empty_intervals
import argparse

# Determine which API client to use
if len(os.environ.get("GROQ_API_KEY", "")) > 30:
    from groq import Groq
    model = "mixtral-8x7b-32768"
    client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
else:
    from openai import OpenAI
    OPENAI_API_KEY = os.getenv('OPENAI_KEY')
    model = "gpt-4o"
    client = OpenAI(api_key=OPENAI_API_KEY)

def generate_script(topic, video_type='short'):
    if video_type == 'short':
        prompt = (
            """You are a seasoned content writer for a YouTube Shorts channel, specializing in facts videos. 
            Your facts shorts are concise, each lasting less than 50 seconds (approximately 140 words). 
            They are incredibly engaging and original. When a user requests a specific type of facts short, you will create it.

            For instance, if the user asks for:
            Weird facts
            You would produce content like this:

            Weird facts you don't know:
            - Bananas are berries, but strawberries aren't.
            - A single cloud can weigh over a million pounds.
            - There's a species of jellyfish that is biologically immortal.
            - Honey never spoils; archaeologists have found pots of honey in ancient Egyptian tombs that are over 3,000 years old and still edible.
            - The shortest war in history was between Britain and Zanzibar on August 27, 1896. Zanzibar surrendered after 38 minutes.
            - Octopuses have three hearts and blue blood.

            You are now tasked with creating the best short script based on the user's requested type of 'facts'.

            Keep it brief, highly interesting, and unique.

            Stictly output the script in a JSON format like below, and only provide a parsable JSON object with the key 'script'.

            # Output
            {"script": "Here is the script ..."}
            """
        )
    else:  # Long video script generation
       prompt = (
            """You are an expert content writer tasked with creating an in-depth, fact-based script for a YouTube video designed to captivate and inform viewers. Each script should present a thorough exploration of the topic, integrating rich, well-researched information in a continuous, engaging narrative. Aim to write a single, uninterrupted paragraph with around 1,200 to 1,400 words, providing approximately 10 minutes of content that flows seamlessly and logically.

            **Guidelines**:
            - Write in a continuous paragraph without section headers, dialogue, or phrases like "Hello and welcome" or "In conclusion."
            - Organize the facts in a clear, cohesive narrative, avoiding lists or bullet points.
            - Each fact should connect smoothly to the next, forming a cohesive storyline that keeps viewers engaged from start to finish.

            For example, if the topic is "The history of money," your script might begin as follows:

            "The history of money is a fascinating journey that reveals the evolution of human societies and economies, tracing back to the earliest systems of trade where bartering was the primary method of exchange. In these early communities, people relied on direct exchange, trading goods like livestock, grains, and tools, but this system had significant limitations, primarily because it required what economists call a 'double coincidence of wants'—in other words, each person in the trade had to want precisely what the other offered. This inefficiency led ancient societies to explore the idea of commodity money, where items like shells, beads, and grains represented a common standard of value and could be traded more easily. Around 600 BC, the Kingdom of Lydia in what is now modern-day Turkey introduced the first coins made from electrum, a naturally occurring alloy of gold and silver, marking a revolutionary shift in trade and commerce. These early coins standardized value, allowing merchants to conduct transactions over longer distances and fostering a more reliable economy. As trade networks expanded, different civilizations developed their own currencies; for instance, the Roman Empire minted coins stamped with the image of the emperor, which not only served as currency but also reinforced the emperor's presence across the vast empire. By the Tang Dynasty in China (618–907 AD), paper money had emerged as a groundbreaking innovation. Initially, it was used as promissory notes for merchants to facilitate larger transactions over long distances. The concept of paper currency soon spread, and by the Song Dynasty, it had become an official state-sanctioned currency, reducing the need to carry heavy metal coins and enhancing the efficiency of trade along the Silk Road. During the medieval period, banking institutions in Europe began issuing promissory notes, which functioned much like early forms of banknotes, allowing merchants to deposit large sums with banks and withdraw them elsewhere using these notes as proof of credit. This system laid the groundwork for modern banking and the concept of credit. In the 17th century, the Bank of England issued the first official banknotes, which were backed by the gold standard, meaning each note represented a specific amount of gold held by the bank. The gold standard was a stabilizing force in the global economy for centuries, until the early 20th century when many countries moved away from it, leading to the introduction of fiat currency, where money’s value is not based on physical commodities but on government regulation. In the late 20th century, digital banking and electronic transfers further revolutionized money, enabling instant transactions across the globe without the need for physical cash. The advent of digital wallets and cryptocurrencies like Bitcoin in the 21st century has introduced new debates and possibilities around decentralization, security, and the future of currency. Cryptocurrencies operate on blockchain technology, a decentralized ledger that provides transparency and security without relying on traditional financial institutions. Today, the world is witnessing the rise of digital central bank currencies, as governments seek to balance the benefits of digital currency with regulatory oversight, raising questions about privacy, control, and the evolving role of money in society. From bartering livestock to instant digital transactions, the evolution of money is a testament to human innovation and adaptability, reflecting changes in social structures, technology, and the global economy."

            Continue with this style for the entire topic, weaving each fact seamlessly into the next to form a continuous paragraph. Conclude with a thoughtful summary on the topic’s evolution or significance.

            **Output Instructions**:
            - Output only a valid JSON object with the key 'script' containing the entire paragraph as shown in the example below.
            - Ensure the output is in strict JSON format without additional text.

            # Output Example
            {"script": "The full paragraph script goes here..."}
            """
        )





    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": topic}
            ]
        )
        
        content = response.choices[0].message.content
        print("Raw Response:", content)  # Debugging response
        
        if not content or (not content.startswith('{') and not content.startswith('[')):
            print("Error: Invalid response received from API.")
            return "Error: Invalid response received from API."
        
        script = json.loads(content)["script"]
    except json.JSONDecodeError as e:
        print("JSON decoding error:", str(e))
        print("Response content was:", content)  # Show the content that caused the error
        return "Error: Could not decode JSON response."
    except Exception as e:
        print("An error occurred:", str(e))
        return "Error: An unexpected error occurred."

    return script

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate a video from a topic.")
    parser.add_argument("topic", type=str, help="The topic for the video")
    parser.add_argument("--video_type", type=str, choices=['short', 'long'], default='short', help="Type of video to generate")

    args = parser.parse_args()
    SAMPLE_TOPIC = args.topic
    SAMPLE_FILE_NAME = "audio_tts.wav"
    VIDEO_SERVER = "pexel"

    # Generate the script based on the video type
    response = generate_script(SAMPLE_TOPIC, args.video_type)
    print("Generated Script:", response)

    if "Error" in response:
        print("Exiting due to script generation error.")
    else:
        asyncio.run(generate_audio(response, SAMPLE_FILE_NAME))

        timed_captions = generate_timed_captions(SAMPLE_FILE_NAME)
        print("Timed Captions:", timed_captions)

        search_terms = getVideoSearchQueriesTimed(response, timed_captions)
        print("Search Terms:", search_terms)

        background_video_urls = None
        if search_terms is not None:
            background_video_urls = generate_video_url(search_terms, VIDEO_SERVER)
            print("Background Video URLs:", background_video_urls)
        else:
            print("No background video")

        background_video_urls = merge_empty_intervals(background_video_urls)

        if background_video_urls is not None:
            video = get_output_media(SAMPLE_FILE_NAME, timed_captions, background_video_urls, VIDEO_SERVER)
            print("Output Video:", video)
        else:
            print("No video")

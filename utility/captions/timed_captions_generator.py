import whisper_timestamped as whisper
from whisper_timestamped import load_model, transcribe_timestamped
import re
import logging
from functools import lru_cache

@lru_cache(maxsize=1)
def load_whisper_model(model_size):
    return load_model(model_size)

def generate_timed_captions(audio_filename, model_size="base"):
    try:
        WHISPER_MODEL = load_whisper_model(model_size)
        gen = transcribe_timestamped(WHISPER_MODEL, audio_filename, verbose=False, fp16=False)
        return getCaptionsWithTime(gen)
    except Exception as e:
        logging.error(f"Error generating timed captions: {str(e)}")
        return None

def splitWordsBySize(words, maxCaptionSize):
    captions = []
    current_caption = []
    current_length = 0
    for word in words:
        word_length = len(word)
        if current_length + word_length + 1 <= maxCaptionSize:
            current_caption.append(word)
            current_length += word_length + 1
        else:
            captions.append(' '.join(current_caption))
            current_caption = [word]
            current_length = word_length
    if current_caption:
        captions.append(' '.join(current_caption))
    return captions

def getTimestampMapping(whisper_analysis):
    locationToTimestamp = {}
    index = 0
    for segment in whisper_analysis['segments']:
        for word in segment['words']:
            newIndex = index + len(word['text']) + 1
            locationToTimestamp[(index, newIndex)] = word['end']
            index = newIndex
    return locationToTimestamp

def cleanWord(word):
    return re.sub(r'[^\w\s\-_"\'\']', '', word)

def interpolateTimeFromDict(word_position, d):
    for key, value in d.items():
        if key[0] <= word_position <= key[1]:
            return value
    return None

def getCaptionsWithTime(whisper_analysis, maxCaptionSize=15, considerPunctuation=False):
    try:
        wordLocationToTime = getTimestampMapping(whisper_analysis)
        position = 0
        start_time = 0
        CaptionsPairs = []
        text = whisper_analysis['text']
        
        if considerPunctuation:
            sentences = re.split(r'(?<=[.!?]) +', text)
            words = [word for sentence in sentences for word in splitWordsBySize(sentence.split(), maxCaptionSize)]
        else:
            words = text.split()
            words = [cleanWord(word) for word in splitWordsBySize(words, maxCaptionSize)]
        
        for word in words:
            position += len(word) + 1
            end_time = interpolateTimeFromDict(position, wordLocationToTime)
            if end_time and word:
                CaptionsPairs.append(((start_time, end_time), word))
                start_time = end_time

        return CaptionsPairs
    except Exception as e:
        logging.error(f"Error processing captions: {str(e)}")
        return None
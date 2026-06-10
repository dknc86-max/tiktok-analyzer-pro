import time
import os
from faster_whisper import WhisperModel

def test_faster_whisper():
    print("Loading faster-whisper small.en model...")
    start = time.time()
    # device "cpu", compute_type "int8" is well-supported and fast
    model = WhisperModel("small.en", device="cpu", compute_type="int8")
    print(f"Model loaded in {time.time() - start:.2f}s")
    
    # Check if there's a test audio file we can use
    test_audio = "vid_2.mp4"
    if os.path.exists(test_audio):
        print(f"Transcribing {test_audio}...")
        start = time.time()
        segments, info = model.transcribe(test_audio, beam_size=5)
        text = " ".join([segment.text for segment in segments])
        print(f"Transcription finished in {time.time() - start:.2f}s")
        print(f"Result (first 100 chars): {text[:100]}")
    else:
        print(f"Test audio {test_audio} not found.")

if __name__ == "__main__":
    test_faster_whisper()

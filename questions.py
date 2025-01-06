import streamlit as st
import requests
import json
from docx import Document
from PyPDF2 import PdfReader
from elevenlabs import ElevenLabs
from elevenlabs import VoiceSettings
import pygame
import tempfile
import speech_recognition as sr
from google.cloud import speech
from google.oauth2 import service_account
import os

# Define the Chatbot API URL and headers
api_url = "https://llm.kindo.ai/v1/chat/completions"
headers = {
    "api-key": "09e75bff-6192-436d-936e-2d0f9230a3a6-a896f6311e363485",  # Replace with your API key
    "content-type": "application/json"
}

# Initialize ElevenLabs client
elevenlabs_client = ElevenLabs(api_key="ae38aba75e228787e91ac4991fc771f8")  # Replace with your ElevenLabs API key

# Function to extract text from PDF
def extract_text_from_pdf(uploaded_pdf):
    pdf_reader = PdfReader(uploaded_pdf)
    text = ""
    for page in pdf_reader.pages:
        text += page.extract_text()
    return text

# Function to extract text from Word file (if needed in the future)
def extract_text_from_word(file):
    doc = Document(file)
    text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
    return text

# Function to query the Chatbot API
def ask_question(question, context, model_name="azure/gpt-4o"):
    messages = [
        {"role": "system", "content": "You are Navin Kale, the co-founder of Swayam Talks. Answer in English and in short paragraphs, not more than 100 words. Use natural human speech, you can also pause in between sentences for a more human-like response."},
        {"role": "user", "content": f"Context: {context}\n\nQuestion: {question}"}
    ]
    
    data = {
        "model": model_name,
        "messages": messages
    }
    
    response = requests.post(api_url, headers=headers, data=json.dumps(data))
    if response.status_code == 200:
        return response.json().get('choices', [{}])[0].get('message', {}).get('content', "").strip()
    else:
        st.error(f"API request failed with status code {response.status_code}")
        return None

# Function to play audio using pygame (with pause functionality)
def play_audio_stream(audio_stream):
    pygame.mixer.init()

    # Save audio stream to a temporary file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as temp_audio:
        for chunk in audio_stream:
            temp_audio.write(chunk)
        temp_audio_name = temp_audio.name

    # Load and play the audio file
    pygame.mixer.music.load(temp_audio_name)
    pygame.mixer.music.play(loops=0, start=0.0)

    # Return the audio file path so it can be used for pause/resume functionality
    return temp_audio_name

# Function to convert text to speech
def text_to_speech(text, voice_id="voice_id"):
    try:
        audio_stream = elevenlabs_client.text_to_speech.convert_as_stream(
            voice_id=voice_id,
            text=text, 
            model_id="eleven_multilingual_v2", 
            voice_settings=VoiceSettings(stability=0.5,
                                         similarity_boost=0.75,
                                         style=0.0)
        )
        # Play the audio stream
        temp_audio_name = play_audio_stream(audio_stream)
        return temp_audio_name
    except Exception as e:
        st.error(f"Text-to-speech conversion failed: {e}")

# Function to capture speech and convert it to text using Google Cloud Speech-to-Text (with API key)
def speech_to_text():
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        st.write("Say something...")
        audio = recognizer.listen(source)
        try:
            # API Key for Google Cloud Speech-to-Text API
            api_key = "AIzaSyA1G84NtL0tWbZ-32KGtfEID6AclLb-dU8"  # Replace with your actual Google API Key

            # Using the Speech Client from Google Cloud with the API Key
            client = speech.SpeechClient(credentials=service_account.Credentials.from_api_key(api_key))
            
            # Converts speech to text
            audio_content = audio.get_wav_data()

            # Send audio to Google Cloud Speech API
            audio_recognition = speech.RecognitionAudio(content=audio_content)
            config = speech.RecognitionConfig(
                encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
                sample_rate_hertz=16000,
                language_code="en-US",
            )

            response = client.recognize(config=config, audio=audio_recognition)

            # Extract and return the recognized text
            recognized_text = ""
            for result in response.results:
                recognized_text += result.alternatives[0].transcript

            st.write(f"Recognized: {recognized_text}")
            return recognized_text
        except Exception as e:
            st.error(f"Error with speech recognition: {e}")
            return ""

# Streamlit app
def main():
    st.title("Swayam Talks Chatbot")

    # Initialize session state for Q&A history
    if "qa_history" not in st.session_state:
        st.session_state.qa_history = []

    if "audio_playing" not in st.session_state:
        st.session_state.audio_playing = False

    if "audio_path" not in st.session_state:
        st.session_state.audio_path = None

    # Upload PDF file
    uploaded_pdf = st.file_uploader("Upload a PDF file", type=["pdf"])
    if uploaded_pdf:
        try:
            # Extract text from the uploaded PDF
            context = extract_text_from_pdf(uploaded_pdf)
        except Exception as e:
            st.error(f"Error extracting text from PDF: {e}")
            return

        # Input for questions (either type or speak)
        question_type = st.radio("How do you want to ask the question?", ("Type", "Speak"))

        if question_type == "Type":
            question = st.text_input("Ask a question:")
        elif question_type == "Speak":
            question = speech_to_text()

        if question:
            # Get the answer from the API
            answer = ask_question(question, context, model_name="azure/gpt-4o")
            if answer:
                # Add question and answer to session state
                st.session_state.qa_history.append((question, answer))
                
                # Convert answer to speech
                st.session_state.audio_path = text_to_speech(answer, voice_id="okq89CVMFdUItYbOQspc")  # Replace with your ElevenLabs voice ID
                st.session_state.audio_playing = True

    # Display Play/Pause button if audio is playing
    if st.session_state.audio_playing:
        play_pause_button = st.button("Pause" if st.session_state.audio_playing else "Play")

        if play_pause_button:
            if pygame.mixer.music.get_busy():
                pygame.mixer.music.stop()
                st.session_state.audio_playing = False
            else:
                # Restart audio from the beginning (not true "resume")
                pygame.mixer.music.load(st.session_state.audio_path)
                pygame.mixer.music.play()
                st.session_state.audio_playing = True

    # Display Q&A history
    if st.session_state.qa_history:
        st.write("### Question-Answer History:")
        for i, (q, a) in enumerate(st.session_state.qa_history, 1):
            with st.expander(f"Q{i}: {q}") as exp:
                st.write(a)

if __name__ == "__main__":
    main()

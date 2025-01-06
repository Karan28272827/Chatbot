import streamlit as st
import requests
import json
from docx import Document
from PyPDF2 import PdfReader
from google.cloud import speech
from google.oauth2 import service_account
from gtts import gTTS
import simpleaudio as sa
import tempfile
import os

# Define the Chatbot API URL and headers
api_url = "https://llm.kindo.ai/v1/chat/completions"
headers = {
    "api-key": "09e75bff-6192-436d-936e-2d0f9230a3a6-a896f6311e363485",  # Replace with your API key
    "content-type": "application/json"
}

# Function to extract text from PDF
def extract_text_from_pdf(uploaded_pdf):
    pdf_reader = PdfReader(uploaded_pdf)
    text = ""
    for page in pdf_reader.pages:
        text += page.extract_text()
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

# Function to convert text to speech using gTTS and play it
def text_to_speech(text):
    try:
        # Convert text to speech using gTTS
        tts = gTTS(text=text, lang='en')
        
        # Save the audio to a temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as temp_audio:
            tts.save(temp_audio.name)
            temp_audio_path = temp_audio.name
        
        # Use simpleaudio to play the audio file
        wave_obj = sa.WaveObject.from_wave_file(temp_audio_path)
        play_obj = wave_obj.play()
        play_obj.wait_done()

        # Remove the temporary file after playback
        os.remove(temp_audio_path)
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
                text_to_speech(answer)

    # Display Q&A history
    if st.session_state.qa_history:
        st.write("### Question-Answer History:")
        for i, (q, a) in enumerate(st.session_state.qa_history, 1):
            with st.expander(f"Q{i}: {q}") as exp:
                st.write(a)

if __name__ == "__main__":
    main()

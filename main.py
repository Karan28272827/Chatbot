import streamlit as st
import requests
import json
import re
 
 
# API configuration
API_URL = "https://llm.kindo.ai/v1/chat/completions"
HEADERS = {
    "api-key": "09e75bff-6192-436d-936e-2d0f9230a3a6-a896f6311e363485",  # Replace with your API key
    "content-type": "application/json"
}


# Function to read SRT file
def read_srt_file(file):
    content = file.read().decode("utf-8")
    return re.split(r"\n\n", content.strip())
 
 
# Function to write SRT file
def write_srt_file(subtitles, output_file_path):
    with open(output_file_path, "w", encoding="utf-8") as file:
        for index, subtitle in enumerate(subtitles, start=1):
            subtitle_lines = subtitle.splitlines()
            if subtitle_lines[0].isdigit():
                subtitle_lines = subtitle_lines[1:]
            file.write(str(index) + "\n" + "\n".join(subtitle_lines) + "\n\n")
 
 
# Contextual Agent
def contextual_agent(subtitles, model_name):
    full_text = " ".join([re.sub(r"\d+\n.*? --> .*?\n", "", s) for s in subtitles])
    messages = [{"role": "user", "content": f"Analyze the context and tone of the text: {full_text}"}]
    response = requests.post(API_URL, headers=HEADERS, json={"model": model_name, "messages": messages})
    if response.status_code == 200:
        return response.json().get("choices", [{}])[0].get("message", {}).get("content", "").strip()
    else:
        raise Exception(f"Contextual Agent API Error: {response.status_code}")
 
 
# Translation Agent
def translation_agent(input_text, context, model_name):
    messages = [
        {
            "role": "user",
            "content": f"Translate this text from Hindi to English (US) while preserving context '{context}': {input_text}"
        }
    ]
    response = requests.post(API_URL, headers=HEADERS, json={"model": model_name, "messages": messages})
    if response.status_code == 200:
        return response.json().get("choices", [{}])[0].get("message", {}).get("content", "").strip()
    else:
        raise Exception(f"Translation Agent API Error: {response.status_code}")
 
 
# Quality Check Agent
def quality_check_agent(translation, context, model_name):
    messages = [
        {
            "role": "user",
            "content": f"Check the quality of this translation given the context '{context}'. "
                       f"Rate it out of 1 based on literalism, humor retention, and target culture adaptation: {translation}"
        }
    ]
    response = requests.post(API_URL, headers=HEADERS, json={"model": model_name, "messages": messages})
    if response.status_code == 200:
        score = response.json().get("choices", [{}])[0].get("message", {}).get("content", "").strip()
        try:
            return float(score)
        except ValueError:
            return 0.0
    else:
        raise Exception(f"Quality Check Agent API Error: {response.status_code}")
 
 
# Coordinator Agent
def coordinator_agent(subtitles, model_name):
    context = contextual_agent(subtitles, model_name)
    translated_subtitles = []
 
    for subtitle in subtitles:
        lines = subtitle.splitlines()
        if len(lines) > 2:
            original_text = " ".join(lines[2:])
            translation = translation_agent(original_text, context, model_name)
 
            # Quality check loop
            score = quality_check_agent(translation, context, model_name)
            while score < 0.8:
                translation = translation_agent(original_text, context, model_name)
                score = quality_check_agent(translation, context, model_name)
 
            lines[2:] = [translation]
            translated_subtitles.append("\n".join(lines))
        else:
            translated_subtitles.append(subtitle)
 
    return translated_subtitles
 
 
# Streamlit App
def main():
    st.title("Agent-Based SRT Translator")
    st.sidebar.header("Upload and Configuration")
 
    uploaded_file = st.sidebar.file_uploader("Upload an SRT file", type=["srt"])
    model_name = st.sidebar.text_input("Model Name", value="azure/gpt-4o")
    output_path = st.sidebar.text_input("Output SRT File Path", value="output.srt")
 
    if st.sidebar.button("Translate"):
        if uploaded_file:
            subtitles = read_srt_file(uploaded_file)
            translated_subtitles = coordinator_agent(subtitles, model_name)
            write_srt_file(translated_subtitles, output_path)
            st.success(f"Translation completed! File saved to {output_path}")
        else:
            st.error("Please upload an SRT file.")
 
 
if __name__ == "__main__":
    main()
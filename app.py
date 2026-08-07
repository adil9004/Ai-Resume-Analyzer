import streamlit as st
import pdfplumber
import os
from dotenv import load_dotenv
from google import genai

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

st.set_page_config(page_title="AI Resume Analyzer", page_icon="📄")
st.title("📄 AI Resume Analyzer")
st.write("Upload your resume (PDF) and get instant AI-powered feedback.")

uploaded_file = st.file_uploader("Upload your resume (PDF only)", type=["pdf"])


def extract_text_from_pdf(file):
    """Reads a PDF file and pulls out all the text from every page."""
    text = ""
    with pdfplumber.open(file) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text


def analyze_resume(resume_text):
    """Sends resume text to Gemini and asks for structured feedback."""
    prompt = f"""
    You are an expert resume reviewer and career coach.
    Analyze the following resume and respond in this exact structure:

    ## Overall Score
    Give a score out of 100 based on clarity, structure, and impact.

    ## Top 3 Strengths
    List them as bullet points.

    ## Top 3 Areas for Improvement
    List them as bullet points.

    ## Missing Keywords / Skills
    Suggest keywords that could help this resume pass ATS (Applicant
    Tracking System) filters for relevant roles.

    ## Example Rewrite
    Pick one weak bullet point from the resume and rewrite it to be
    stronger, showing a "Before" and "After".

    Resume:
    {resume_text}
    """

    response = client.models.generate_content(
        model="gemini-3.5-flash",
        contents=prompt,
    )
    return response.text


if uploaded_file is not None:
    with st.spinner("Reading your resume..."):
        resume_text = extract_text_from_pdf(uploaded_file)

    if resume_text.strip() == "":
        st.error("Couldn't extract text from this PDF. Try a different file (avoid scanned/image-only PDFs).")
    else:
        st.success("Resume text extracted successfully!")

        if st.button("Analyze Resume"):
            with st.spinner("Analyzing with AI... this may take a few seconds"):
                try:
                    result = analyze_resume(resume_text)
                    st.subheader("📊 Analysis Result")
                    st.markdown(result)
                except Exception as e:
                    st.error(f"Something went wrong: {e}")
else:
    st.info("Upload a PDF resume above to get started.")
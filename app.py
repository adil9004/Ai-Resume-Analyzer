import streamlit as st
import pdfplumber
import os
from dotenv import load_dotenv
from google import genai
from database import init_db, save_analysis, get_all_analyses, delete_analysis
from agent import run_agent_steps

# Load environment variables and initialize database
load_dotenv()
init_db()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

st.set_page_config(page_title="AI Resume Analyzer", page_icon="📄", layout="wide")
st.title("📄 AI Resume Analyzer")

# Create tabs for navigation
tab1, tab2, tab3 = st.tabs(["🔍 Analyze Resume", "📜 Analysis History", "🤖 Job Application Assistant"])

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


# Tab 1: Analyze Resume
with tab1:
    st.write("Upload your resume (PDF) and get instant AI-powered feedback.")
    uploaded_file = st.file_uploader("Upload your resume (PDF only)", type=["pdf"])

    if uploaded_file is not None:
        file_key = f"analyze_{uploaded_file.name}_{uploaded_file.size}"
        
        if "extracted_text_cache" not in st.session_state:
            st.session_state.extracted_text_cache = {}
            
        if file_key not in st.session_state.extracted_text_cache:
            with st.spinner("Reading your resume..."):
                resume_text = extract_text_from_pdf(uploaded_file)
                st.session_state.extracted_text_cache[file_key] = resume_text
        else:
            resume_text = st.session_state.extracted_text_cache[file_key]

        if resume_text.strip() == "":
            st.error("Couldn't extract text from this PDF. Try a different file (avoid scanned/image-only PDFs).")
        else:
            st.success("Resume text extracted successfully!")

            # Check if we have already analyzed this resume to prevent duplicate API runs on page reruns
            if "analyses_cache" not in st.session_state:
                st.session_state.analyses_cache = {}

            if file_key not in st.session_state.analyses_cache:
                with st.spinner("Analyzing with AI... this may take a few seconds"):
                    try:
                        result = analyze_resume(resume_text)
                        
                        # Save the analysis result to database
                        save_analysis(uploaded_file.name, resume_text, result)
                        
                        st.session_state.analyses_cache[file_key] = result
                    except Exception as e:
                        st.error(f"Something went wrong: {e}")
                        result = None
            else:
                result = st.session_state.analyses_cache[file_key]

            if result:
                st.subheader("📊 Analysis Result")
                st.markdown(result)
    else:
        st.info("Upload a PDF resume above to get started.")


# Tab 2: Analysis History
with tab2:
    st.write("View and manage your past resume analyses.")
    
    # Retrieve records from the database
    analyses = get_all_analyses()
    
    if not analyses:
        st.info("No past analyses found. Start by analyzing a resume in the first tab!")
    else:
        for row in analyses:
            # Display each analysis in an expander
            record_title = f"📄 {row['filename']} — {row['timestamp']}"
            with st.expander(record_title):
                st.markdown("### 📊 AI Analysis Report")
                st.markdown(row['analysis_result'])
                
                # Option to view the original resume text
                with st.expander("🔍 View Original Resume Text", expanded=False):
                    st.text(row['resume_text'])
                
                # Delete button
                if st.button("Delete this analysis", key=f"del_{row['id']}"):
                    delete_analysis(row['id'])
                    st.success(f"Deleted analysis for {row['filename']}!")
                    st.rerun()



# Tab 3: Job Application Assistant
with tab3:
    st.write("Upload a resume and paste a job description to run a 4-step AI agent process that helps you apply.")
    
    # Input field for Job Description
    job_desc = st.text_area("Paste Job Description:", height=200, placeholder="Paste the job description from the job posting...")
    
    # File uploader for Resume (reusing pdf text extractor)
    assistant_file = st.file_uploader("Upload your resume (PDF only)", type=["pdf"], key="assistant_resume_uploader")
    
    assistant_resume_text = ""
    if assistant_file is not None:
        file_key = f"assistant_{assistant_file.name}_{assistant_file.size}"
        
        if "extracted_text_cache" not in st.session_state:
            st.session_state.extracted_text_cache = {}
            
        if file_key not in st.session_state.extracted_text_cache:
            with st.spinner("Reading your resume..."):
                assistant_resume_text = extract_text_from_pdf(assistant_file)
                st.session_state.extracted_text_cache[file_key] = assistant_resume_text
        else:
            assistant_resume_text = st.session_state.extracted_text_cache[file_key]
            
        if assistant_resume_text.strip() == "":
            st.error("Couldn't extract text from this PDF. Try a different file.")
        else:
            st.success("Resume text extracted successfully!")

    # Set up session state for storing assistant analysis results so they persist across reruns
    if "assistant_results" not in st.session_state:
        st.session_state.assistant_results = None

    # Disable the assistant button if the necessary inputs are not provided
    btn_disabled = not (job_desc.strip() and assistant_resume_text.strip())

    if st.button("Run Application Assistant", key="run_assistant_btn", disabled=btn_disabled):
        # Reset the results in state while running
        st.session_state.assistant_results = None
        
        # Start the generator from agent.py
        agent_generator = run_agent_steps(client, job_desc, assistant_resume_text)
        try:
            step_msg, results = next(agent_generator)
            while step_msg != "Complete":
                # Create a spinner for the active step and step through the generator
                with st.spinner(step_msg):
                    step_msg, results = next(agent_generator)
            st.session_state.assistant_results = results
            st.success("Job Application Assistant completed all steps successfully!")
        except Exception as e:
            st.error(f"Something went wrong during agent execution: {e}")

    # Display results when they are available in session state
    if st.session_state.assistant_results is not None:
        res = st.session_state.assistant_results
        
        st.subheader("🎯 Assistant Results")
        
        with st.expander("📋 Step 1: Key Requirements & Skills", expanded=True):
            st.markdown(res.get("step1", ""))
            
        with st.expander("⚖️ Step 2: Compare with Resume (Matches & Gaps)", expanded=True):
            st.markdown(res.get("step2", ""))
            
        with st.expander("✉️ Step 3: Tailored Cover Letter", expanded=True):
            st.markdown(res.get("step3", ""))
            
        with st.expander("✍️ Step 4: Suggested Resume Bullet-Point Edits", expanded=True):
            st.markdown(res.get("step4", ""))

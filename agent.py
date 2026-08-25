import os
from google import genai

def run_agent_steps(client, job_description, resume_text):
    """
    Runs a 4-step AI agent process using Gemini.
    Yields (step_name, current_results_dict) to allow the calling app to show step-by-step progress.
    """
    results = {}
    
    # Step 1: Extract key requirements and skills from the job description.
    yield "Step 1: Extracting job requirements...", results
    step1_prompt = f"""
    You are an expert technical recruiter and talent acquisition specialist.
    Analyze the following job description and extract the key requirements.
    Your output should include:
    1. Key Technical Skills (languages, frameworks, tools)
    2. Required Soft Skills & Competencies
    3. Required Experience Level and Qualifications
    4. Core Responsibilities & Deliverables

    Job Description:
    {job_description}

    Provide a well-structured summary using clear markdown headings and bullet points.
    """
    response1 = client.models.generate_content(
        model="gemini-3.5-flash",
        contents=step1_prompt,
    )
    results["step1"] = response1.text
    
    # Step 2: Compare those requirements against the resume text and identify matches and gaps.
    yield "Step 2: Comparing with your resume...", results
    step2_prompt = f"""
    You are an expert career consultant.
    Compare the key job requirements extracted from the job description against the candidate's resume.
    
    Key Job Requirements:
    {results["step1"]}

    Candidate Resume:
    {resume_text}

    Analyze and identify:
    1. Matched Skills/Experience: What is already well-represented in the resume.
    2. Missing / Gap Areas: What requirements are missing or weak in the resume.
    3. Alignment Score: Give an estimated fit percentage (0-100%) with a brief justification.

    Provide a clear, structured comparison with matched points and gaps.
    """
    response2 = client.models.generate_content(
        model="gemini-3.5-flash",
        contents=step2_prompt,
    )
    results["step2"] = response2.text
    
    # Step 3: Generate a tailored cover letter based on the comparison.
    yield "Step 3: Generating tailored cover letter...", results
    step3_prompt = f"""
    You are an expert professional writer and career coach.
    Write a highly tailored, compelling professional cover letter for the candidate applying to this job. 
    Use the candidate's resume and the comparison of matches and gaps to create a cover letter that:
    1. Grabs attention in the opening paragraph.
    2. Highlights matched key achievements and relevant skills.
    3. Addresses or bridges any key gap areas gracefully using transferable skills or enthusiasm for learning.
    4. Concludes with a strong call to action.

    Candidate Resume:
    {resume_text}

    Job Requirements & Comparison:
    {results["step2"]}

    Ensure the cover letter is written in a professional, engaging tone. Use placeholders like [Candidate Name], [Hiring Manager Name], [Company Name], and [Date] where appropriate.
    """
    response3 = client.models.generate_content(
        model="gemini-3.5-flash",
        contents=step3_prompt,
    )
    results["step3"] = response3.text
    
    # Step 4: Suggest specific resume bullet-point edits to better match the job.
    yield "Step 4: Suggesting bullet-point edits...", results
    step4_prompt = f"""
    You are an expert resume writer.
    Suggest specific actionable bullet-point edits to the candidate's resume based on the job requirements.
    For each suggestion, identify a weak or generic bullet point from the resume, and provide:
    1. The Original Bullet Point (from the resume)
    2. The Revised Bullet Point (tailored with high-impact action verbs, keywords from the job description, and metric-focused wording where possible)
    3. Explanation / Why: Briefly explain why this edit makes the resume stronger and more aligned with the job description.

    Candidate Resume:
    {resume_text}

    Job Requirements & Comparison:
    {results["step2"]}

    Provide at least 3 high-impact bullet-point suggestions.
    """
    response4 = client.models.generate_content(
        model="gemini-3.5-flash",
        contents=step4_prompt,
    )
    results["step4"] = response4.text
    
    yield "Complete", results

from flask import Flask, render_template, request
import os
import pandas as pd
from werkzeug.utils import secure_filename
from openai import AzureOpenAI
import base64

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5MB limit
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Azure OpenAI Configuration
endpoint = os.getenv("ENDPOINT_URL", "https://ai-aihackthonhub282549186415.openai.azure.com")  
deployment = os.getenv("DEPLOYMENT_NAME", "gpt-4")  
subscription_key = os.getenv("AZURE_OPENAI_API_KEY", "Fj1KPt7grC6bAkNja7daZUstpP8wZTXsV6Zjr2FOxkO7wsBQ5SzQJQQJ99BCACHYHv6XJ3w3AAAAACOGL3Xg")  

# Initialize Azure OpenAI client
client = AzureOpenAI(  
    azure_endpoint=endpoint,  
    api_key=subscription_key,  
    api_version="2024-05-01-preview",
)

# Load or create job dataset
def load_job_data():
    base_jobs = [
        {
            "Job Title": "Data Scientist",
            "Company Name": "Tech Innovations",
            "Location": "San Francisco",
            "Industry": "Technology",
            "Rating": 4.5,
            "Required Skills": "python,machine learning,data analysis,statistics",
            "Salary": 120000
        },
        {
            "Job Title": "Software Engineer",
            "Company Name": "Code Masters",
            "Location": "Remote",
            "Industry": "Technology",
            "Rating": 4.2,
            "Required Skills": "java,python,software development,algorithms",
            "Salary": 110000
        },
        {
            "Job Title": "Marketing Specialist",
            "Company Name": "Brand Vision",
            "Location": "New York",
            "Industry": "Marketing",
            "Rating": 3.9,
            "Required Skills": "digital marketing,social media,content creation",
            "Salary": 75000
        }
    ]
    return pd.DataFrame(base_jobs)

jobs_df = load_job_data()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() == 'pdf'

def extract_skills_from_resume(filepath):
    """Extract skills from resume using Azure OpenAI"""
    try:
        with open(filepath, 'rb') as f:
            encoded_resume = base64.b64encode(f.read()).decode('ascii')
        
        messages = [
            {
                "role": "system",
                "content": "You are a career assistant that extracts skills from resumes. Return only a comma-separated list of technical skills."
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Extract all technical skills from this resume. Return only a comma-separated list."
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:application/pdf;base64,{encoded_resume}"
                        }
                    }
                ]
            }
        ]
        
        completion = client.chat.completions.create(
            model=deployment,
            messages=messages,
            max_tokens=300,
            temperature=0.1
        )
        
        skills = completion.choices[0].message.content
        return [skill.strip() for skill in skills.split(',') if skill.strip()]
    
    except Exception as e:
        print(f"Error processing resume: {str(e)}")
        return ["python", "data analysis"]  # Fallback skills

def generate_ai_recommendation(user_profile, matched_jobs):
    """Generate personalized recommendation using Azure OpenAI"""
    try:
        prompt = f"""
        User Profile:
        Name: {user_profile['name']}
        Skills: {', '.join(user_profile['skills'])}
        Degree: {user_profile['degree']}
        Interests: {user_profile['interests']}
        
        Generate a very concise (1-2 sentence) career recommendation summary that:
        1. Mentions the best matched job role
        2. Provides a link to view full details
        
        Example format:
        "Based on your profile, we recommend [Job Title] as your best match. <a href='/details'>View full career analysis</a>"
        """
        
        messages = [
            {
                "role": "system",
                "content": "You are a career counselor. Provide very brief recommendations with links to full details."
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
        
        completion = client.chat.completions.create(
            model=deployment,
            messages=messages,
            max_tokens=200,
            temperature=0.7
        )
        
        return completion.choices[0].message.content
    
    except Exception as e:
        print(f"Error generating AI recommendation: {str(e)}")
        return f"<p>Based on your skills in {', '.join(user_profile['skills'][:3])}, we recommend exploring these career options. <a href='/details?name={user_profile['name']}&skills={','.join(user_profile['skills'])}&degree={user_profile['degree']}&interests={user_profile['interests']}'>View full analysis</a></p>"

def generate_detailed_analysis(name, skills, degree, interests):
    """Generate detailed career analysis using Azure OpenAI"""
    try:
        prompt = f"""
        Generate a comprehensive career analysis for:
        Name: {name}
        Skills: {', '.join(skills)}
        Degree: {degree}
        Interests: {interests}
        
        Include:
        1. Career path recommendations (3 options)
        2. Skill gaps to address
        3. Suggested courses/certifications
        4. Salary expectations
        5. Job market trends for recommended roles
        
        Format with HTML tags for proper display.
        """
        
        messages = [
            {
                "role": "system",
                "content": "You are a professional career counselor. Provide detailed, well-formatted career advice with HTML formatting."
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
        
        completion = client.chat.completions.create(
            model=deployment,
            messages=messages,
            max_tokens=1000,
            temperature=0.7
        )
        
        return completion.choices[0].message.content
    
    except Exception as e:
        print(f"Error generating detailed analysis: {str(e)}")
        return "<p>Detailed analysis could not be generated at this time.</p>"

@app.route('/details')
def details():
    # Get all the data from session or request args
    name = request.args.get('name', 'User')
    skills = request.args.get('skills', '').split(',')
    degree = request.args.get('degree', '')
    interests = request.args.get('interests', '')
    
    # Generate a more detailed analysis using AI
    detailed_analysis = generate_detailed_analysis(name, skills, degree, interests)
    
    return render_template('details.html', 
                         analysis=detailed_analysis,
                         name=name,
                         skills=skills,
                         degree=degree,
                         interests=interests)

def match_jobs(user_skills, user_interests, user_degree):
    """Match jobs using AI-enhanced matching"""
    try:
        # First get base matches
        matched_jobs = []
        for _, job in jobs_df.iterrows():
            required_skills = str(job['Required Skills']).lower().split(',')
            match_count = sum(1 for skill in user_skills if skill.lower() in required_skills)
            
            if match_count > 0:
                matched_jobs.append({
                    'Job Title': job['Job Title'],
                    'Company': job['Company Name'],
                    'Location': job['Location'],
                    'Industry': job['Industry'],
                    'Match Score': match_count,
                    'Rating': job['Rating'],
                    'Salary': job['Salary']
                })
        
        matched_jobs.sort(key=lambda x: (-x['Match Score'], -x['Rating']))
        top_jobs = matched_jobs[:5]
        
        # Enhance with AI-generated jobs
        prompt = f"""
        Generate 2 additional personalized job recommendations for:
        - Skills: {', '.join(user_skills)}
        - Degree: {user_degree}
        - Interests: {user_interests}
        
        Return in this exact format:
        Job Title|Company Name|Location|Industry|Required Skills|Salary
        
        Example:
        AI Research Assistant|University Labs|Boston|Education|python,machine learning,research|65000
        """
        
        messages = [
            {
                "role": "system",
                "content": "Generate personalized job recommendations in the exact specified format."
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
        
        completion = client.chat.completions.create(
            model=deployment,
            messages=messages,
            max_tokens=300,
            temperature=0.7
        )
        
        # Parse AI-generated jobs
        ai_jobs = []
        for line in completion.choices[0].message.content.split('\n'):
            if '|' in line:
                parts = line.split('|')
                if len(parts) == 6:
                    ai_jobs.append({
                        'Job Title': parts[0],
                        'Company Name': parts[1],
                        'Location': parts[2],
                        'Industry': parts[3],
                        'Required Skills': parts[4],
                        'Salary': int(parts[5]) if parts[5].isdigit() else 70000
                    })
        
        # Add AI-generated jobs with high match scores
        for job in ai_jobs:
            required_skills = job['Required Skills'].lower().split(',')
            match_count = sum(1 for skill in user_skills if skill.lower() in required_skills)
            
            top_jobs.append({
                'Job Title': job['Job Title'],
                'Company': job['Company Name'],
                'Location': job['Location'],
                'Industry': job['Industry'],
                'Match Score': match_count + 2,  # Slight boost for AI-generated
                'Rating': 4.0,  # Default rating for AI jobs
                'Salary': job['Salary']
            })
        
        # Re-sort with AI jobs
        top_jobs.sort(key=lambda x: (-x['Match Score'], -x['Rating']))
        return top_jobs[:5]  # Return top 5
    
    except Exception as e:
        print(f"Error in AI job matching: {str(e)}")
        return matched_jobs[:5]  # Fallback to base matches

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        form_data = {
            'name': request.form.get('name', ''),
            'interests': request.form.get('interests', ''),
            'skills': request.form.get('skills', ''),
            'degree': request.form.get('degree', ''),
            'working': request.form.get('working', ''),
            'specialization': request.form.get('specialization', ''),
            'percentage': request.form.get('percentage', ''),
            'certifications': request.form.get('certifications', '')
        }
        
        # Process skills
        form_skills = []
        if form_data['skills']:
            form_skills = [s.strip().lower() for s in form_data['skills'].split(',')]
        
        # Process resume
        resume_skills = []
        resume_file = None
        if 'resume' in request.files:
            file = request.files['resume']
            if file.filename != '' and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                resume_skills = extract_skills_from_resume(filepath)
                resume_file = filename
        
        all_skills = list(set(form_skills + resume_skills))
        
        # Get job matches (now with AI-enhanced matching)
        matched_jobs = match_jobs(all_skills, form_data['interests'], form_data['degree'])
        matched_jobs_df = pd.DataFrame(matched_jobs)
        
        # Generate AI-powered recommendation text
        ai_recommendation = generate_ai_recommendation({
            **form_data,
            'skills': all_skills
        }, matched_jobs_df)
        
        return render_template('home.html',
                            form_data=form_data,
                            jobs=matched_jobs,
                            skills=all_skills,
                            ai_recommendation=ai_recommendation,
                            resume_uploaded=resume_file is not None)
    
    return render_template('home.html',
                         form_data={k:'' for k in ['name','interests','skills','degree',
                                                 'working','specialization','percentage',
                                                 'certifications']},
                         jobs=None,
                         skills=None,
                         ai_recommendation=None,
                         resume_uploaded=False)

if __name__ == '__main__':
    app.run(debug=True, port=5001)
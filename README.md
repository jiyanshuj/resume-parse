# Resume Parser API

A powerful FastAPI-based resume parsing service that extracts structured information from resumes using Google's Gemini AI, stores data in MongoDB, and hosts files on Cloudinary.

## 🚀 Features

- **AI-Powered Resume Parsing**: Utilizes Google Gemini AI (gemini-2.0-flash-lite) to extract comprehensive information from resumes
- **PDF Processing**: Extracts and processes text from PDF documents
- **Cloud Storage**: Integrates with Cloudinary for secure resume file storage
- **MongoDB Integration**: Stores user profiles with automatic indexing and timestamps
- **RESTful API**: Clean and well-documented API endpoints
- **CRUD Operations**: Complete Create, Read, Update, Delete functionality for user profiles
- **CORS Enabled**: Ready for frontend integration
- **Production Ready**: Configured for deployment on Render.com

## 📋 Extracted Information

The API extracts the following information from resumes:

- **Personal Information**: First name, last name, full name, email, phone, location
- **Professional Details**: Willing to relocate status, current company, role
- **Skills**: 
  - Technical skills (programming languages, frameworks, tools)
  - Soft skills (communication, leadership, etc.)
  - Combined skills list
- **Social Links**: LinkedIn, GitHub, Portfolio URLs
- **Experience**: Company, role, duration, description
- **Education**: Degree, institution, year
- **Certifications**: List of all certifications
- **Projects**: Name, description, technologies used

## 🛠️ Tech Stack

- **Framework**: FastAPI 0.109.0
- **Server**: Uvicorn with standard extras
- **AI/ML**: Google Generative AI (Gemini API)
- **Database**: MongoDB with Motor (async driver)
- **Cloud Storage**: Cloudinary
- **PDF Processing**: PyPDF2
- **Validation**: Pydantic 2.8.2 with email validation
- **Python Version**: 3.12.3

## 📦 Installation

### Prerequisites

- Python 3.12.3
- MongoDB instance (local or cloud)
- Cloudinary account
- Google Gemini API key

### Setup

1. **Clone the repository**
```bash
git clone <repository-url>
cd resume-parse
```

2. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Environment Variables**

Create a `.env` file in the root directory:

```env
# MongoDB Configuration
MONGODB_URL=mongodb://localhost:27017
# or for MongoDB Atlas:
# MONGODB_URL=

# Cloudinary Configuration
CLOUDINARY_CLOUD_NAME=your_cloud_name
CLOUDINARY_API_KEY=your_api_key
CLOUDINARY_API_SECRET=your_api_secret

# Google Gemini API
GEMINI_API_KEY=your_gemini_api_key
```

5. **Run the application**
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`

## 📚 API Documentation

Once the server is running, access:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

### Endpoints

#### 1. Health Check
```
GET /
```
Returns API status and available endpoints.

#### 2. Upload Resume
```
POST /api/users/upload
```
**Form Data**:
- `file`: Resume file (PDF, DOC, DOCX) - Max 5MB
- `clerk_id`: User's unique identifier
- `user_role`: User role (default: "job_seeker")

**Response**:
```json
{
  "message": "Resume uploaded and parsed successfully",
  "cloudinary_url": "https://...",
  "result": { /* parsed resume data */ },
  "profile": { /* saved user profile */ }
}
```

#### 3. Get User Profile
```
GET /api/users/me?clerk_id={clerk_id}
```
Retrieves user profile by clerk_id.

#### 4. Update User Profile
```
PATCH /api/users/{clerk_id}
```
**Body**: JSON object with fields to update

#### 5. Delete User Profile
```
DELETE /api/users/{clerk_id}
```
Deletes user profile permanently.

## 🗂️ Project Structure

```
resume-parse/
├── main.py              # FastAPI application & API endpoints
├── parse.py             # Resume parsing logic with Gemini AI
├── db.py                # MongoDB operations & database helpers
├── requirements.txt     # Python dependencies
├── runtime.txt          # Python version specification
├── render.yaml          # Render.com deployment configuration
└── __pycache__/         # Python cache files
```

## 🔧 Configuration Files

### `render.yaml`
Configures deployment on Render.com:
- Service type: Web
- Environment: Python
- Build command: Install dependencies
- Start command: Uvicorn server on port 10000

## 🔒 Security Features

- Input validation using Pydantic models
- File type validation (PDF, DOC, DOCX only)
- File size limit (5MB maximum)
- Unique index on clerk_id to prevent duplicates
- Error handling for all endpoints
- CORS configuration (customize origins for production)

## 🚀 Deployment

### Render.com Deployment

1. Connect your repository to Render
2. Render will automatically detect the `render.yaml` configuration
3. Add environment variables in Render dashboard:
   - `MONGODB_URL`
   - `CLOUDINARY_CLOUD_NAME`
   - `CLOUDINARY_API_KEY`
   - `CLOUDINARY_API_SECRET`
   - `GEMINI_API_KEY`
4. Deploy!

The application will be available at your Render URL on port 10000.

## 🧪 Testing

### Using cURL
```bash
# Upload resume
curl -X POST "http://localhost:8000/api/users/upload" \
  -F "file=@/path/to/resume.pdf" \
  -F "clerk_id=user_123" \
  -F "user_role=job_seeker"

# Get profile
curl "http://localhost:8000/api/users/me?clerk_id=user_123"
```

### Using Python
```python
import requests

# Upload resume
with open('resume.pdf', 'rb') as f:
    files = {'file': f}
    data = {'clerk_id': 'user_123', 'user_role': 'job_seeker'}
    response = requests.post('http://localhost:8000/api/users/upload', 
                           files=files, data=data)
    print(response.json())
```

## 📝 Data Models

### UserProfile
- `clerk_id`: Unique user identifier (string, required)
- `first_name`, `last_name`, `full_name`: Name fields
- `email`: Email address with validation
- `phone`: Phone number
- `location`: Geographic location
- `willing_to_relocate`: Boolean flag
- `role`: User role (default: "job_seeker")
- `current_company`: Current employer
- `resume_url`: Cloudinary URL of resume
- `resume_filename`: Original filename
- `technical_skills`: List of technical skills
- `soft_skills`: List of soft skills
- `skills`: Combined skills list
- `social_links`: LinkedIn, GitHub, Portfolio
- `experience`: Array of work experience objects
- `education`: Array of education objects
- `certifications`: List of certifications
- `projects`: Array of project objects
- `created_at`, `updated_at`: Timestamps

## 🐛 Error Handling

The API includes comprehensive error handling:
- 400: Bad Request (invalid file type, size, or parameters)
- 404: Not Found (profile doesn't exist)
- 500: Internal Server Error (parsing, database, or upload failures)

All errors return JSON with a `detail` field explaining the issue.

## 🔄 Database Operations

- **Upsert**: Creates new profile or updates existing one
- **Automatic Timestamps**: `created_at` and `updated_at` managed automatically
- **Unique Index**: Ensures one profile per clerk_id
- **Async Operations**: All database operations are asynchronous for better performance

---

**Built with ❤️ using FastAPI, MongoDB, and Google Gemini AI**

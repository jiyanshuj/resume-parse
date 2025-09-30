from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict, Any
import cloudinary
import cloudinary.uploader
from dotenv import load_dotenv
import os
import tempfile
from contextlib import asynccontextmanager

# Import local modules
from parse import parse_resume
from db import (
    connect_to_mongo, 
    close_mongo_connection, 
    get_user_profile,
    upsert_user_profile,
    update_user_profile,
    transform_parsed_resume_to_profile
)

load_dotenv()

# Configure Cloudinary
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET")
)


# Lifespan context manager for startup/shutdown events
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await connect_to_mongo()
    yield
    # Shutdown
    await close_mongo_connection()


# Initialize FastAPI app
app = FastAPI(
    title="Resume Parser API",
    description="API for parsing resumes and managing user profiles",
    version="1.0.0",
    lifespan=lifespan
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Pydantic Models
class SocialLinks(BaseModel):
    linkedin: Optional[str] = None
    github: Optional[str] = None
    portfolio: Optional[str] = None


class Experience(BaseModel):
    company: Optional[str] = None
    position: Optional[str] = None
    duration: Optional[str] = None
    description: Optional[str] = None


class Education(BaseModel):
    degree: Optional[str] = None
    institution: Optional[str] = None
    year: Optional[str] = None


class Project(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    technologies: List[str] = []


class UserProfileUpdate(BaseModel):
    clerk_id: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    willing_to_relocate: Optional[bool] = False
    role: Optional[str] = "job_seeker"
    current_company: Optional[str] = None
    resume_filename: Optional[str] = None
    resume_url: Optional[str] = None
    technical_skills: List[str] = []
    soft_skills: List[str] = []
    skills: List[str] = []
    social_links: Optional[SocialLinks] = None
    experience: List[Experience] = []
    education: List[Education] = []
    certifications: List[str] = []
    projects: List[Project] = []


# Helper Functions
async def upload_to_cloudinary(file_path: str, filename: str, clerk_id: str) -> str:
    """Upload file to Cloudinary and return URL"""
    try:
        # Upload to Cloudinary with public_id as clerk_id for easy management
        result = cloudinary.uploader.upload(
            file_path,
            folder="resumes",
            public_id=f"{clerk_id}_{filename}",
            resource_type="auto",
            overwrite=True
        )
        return result["secure_url"]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cloudinary upload failed: {str(e)}")


# API Endpoints
@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "message": "Resume Parser API is running",
        "version": "1.0.0",
        "endpoints": {
            "upload": "/api/users/upload",
            "get_profile": "/api/users/me",
            "update_profile": "/api/users/{clerk_id}",
            "delete_profile": "/api/users/{clerk_id}"
        }
    }


@app.post("/api/users/upload")
async def upload_resume(
    file: UploadFile = File(...),
    clerk_id: str = Form(...),
    user_role: str = Form(default="job_seeker")
):
    """
    Upload and parse resume PDF
    - Uploads file to Cloudinary
    - Parses resume using Gemini AI
    - Saves/updates user profile in MongoDB
    """
    # Validate file type
    if not file.filename.lower().endswith(('.pdf', '.doc', '.docx')):
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Only PDF, DOC, and DOCX files are allowed."
        )
    
    # Validate file size (5MB limit)
    file_content = await file.read()
    if len(file_content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File size exceeds 5MB limit")
    
    try:
        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
            temp_file.write(file_content)
            temp_file_path = temp_file.name
        
        # Upload to Cloudinary
        cloudinary_url = await upload_to_cloudinary(
            temp_file_path, 
            file.filename, 
            clerk_id
        )
        
        # Parse resume using Gemini AI
        parsed_data = await parse_resume(temp_file_path)
        
        # Clean up temp file
        os.unlink(temp_file_path)
        
        # Transform parsed data to profile schema
        profile_data = transform_parsed_resume_to_profile(
            parsed_data,
            clerk_id,
            cloudinary_url,
            file.filename
        )
        
        # Upsert profile in MongoDB
        saved_profile = await upsert_user_profile(clerk_id, profile_data)
        
        return {
            "message": "Resume uploaded and parsed successfully",
            "cloudinary_url": cloudinary_url,
            "result": parsed_data,
            "profile": saved_profile
        }
        
    except Exception as e:
        # Clean up temp file if it exists
        if 'temp_file_path' in locals():
            try:
                os.unlink(temp_file_path)
            except:
                pass
        
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process resume: {str(e)}"
        )


@app.get("/api/users/me")
async def get_user_profile_endpoint(clerk_id: str = Query(...)):
    """Get user profile by clerk_id"""
    try:
        profile = await get_user_profile(clerk_id)
        
        if not profile:
            raise HTTPException(status_code=404, detail="User profile not found")
        
        return profile
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch profile: {str(e)}"
        )


@app.patch("/api/users/{clerk_id}")
async def update_user_profile_endpoint(
    clerk_id: str,
    profile_update: UserProfileUpdate
):
    """Update user profile"""
    try:
        # Ensure clerk_id matches
        if profile_update.clerk_id != clerk_id:
            raise HTTPException(
                status_code=400,
                detail="Clerk ID mismatch"
            )
        
        # Convert Pydantic model to dict and remove None values
        update_data = profile_update.dict(exclude_none=True, exclude={"clerk_id"})
        
        # Convert nested Pydantic models to dicts
        if "social_links" in update_data and update_data["social_links"]:
            update_data["social_links"] = dict(update_data["social_links"])
        
        if "experience" in update_data:
            update_data["experience"] = [dict(exp) for exp in update_data["experience"]]
        
        if "education" in update_data:
            update_data["education"] = [dict(edu) for edu in update_data["education"]]
        
        if "projects" in update_data:
            update_data["projects"] = [dict(proj) for proj in update_data["projects"]]
        
        # Update profile
        updated_profile = await update_user_profile(clerk_id, update_data)
        
        if not updated_profile:
            raise HTTPException(status_code=404, detail="User profile not found")
        
        return updated_profile
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update profile: {str(e)}"
        )


@app.delete("/api/users/{clerk_id}")
async def delete_user_profile_endpoint(clerk_id: str):
    """Delete user profile"""
    try:
        from db import delete_user_profile
        
        deleted = await delete_user_profile(clerk_id)
        
        if not deleted:
            raise HTTPException(status_code=404, detail="User profile not found")
        
        return {"message": "Profile deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete profile: {str(e)}"
        )


# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal server error: {str(exc)}"}
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
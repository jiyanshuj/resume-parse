from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import DuplicateKeyError
from datetime import datetime
from typing import Optional, Dict, Any
import os
from dotenv import load_dotenv

load_dotenv()

# MongoDB Configuration
MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
DATABASE_NAME = "users"
COLLECTION_NAME = "Profile"

# Global database client
client: Optional[AsyncIOMotorClient] = None
database = None


async def connect_to_mongo():
    """Connect to MongoDB"""
    global client, database
    try:
        print(f"🔌 Connecting to MongoDB: {MONGODB_URL}")
        client = AsyncIOMotorClient(MONGODB_URL)
        database = client[DATABASE_NAME]
        
        # Test the connection
        await client.admin.command('ping')
        print(f"✅ Successfully pinged MongoDB server")
        
        # Create unique index on clerk_id
        await database[COLLECTION_NAME].create_index("clerk_id", unique=True)
        
        print(f"✅ Connected to MongoDB: {DATABASE_NAME}.{COLLECTION_NAME}")
        
        # List all databases to verify connection
        db_list = await client.list_database_names()
        print(f"📊 Available databases: {db_list}")
        
        return database
    except Exception as e:
        print(f"❌ Error connecting to MongoDB: {e}")
        raise


async def close_mongo_connection():
    """Close MongoDB connection"""
    global client
    if client:
        client.close()
        print("✅ MongoDB connection closed")


def get_database():
    """Get database instance"""
    if database is None:
        raise Exception("Database not initialized. Call connect_to_mongo() first.")
    return database


async def create_user_profile(profile_data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new user profile"""
    db = get_database()
    collection = db[COLLECTION_NAME]
    
    # Add timestamps
    profile_data["created_at"] = datetime.utcnow()
    profile_data["updated_at"] = datetime.utcnow()
    
    try:
        result = await collection.insert_one(profile_data)
        profile_data["_id"] = str(result.inserted_id)
        return profile_data
    except DuplicateKeyError:
        raise ValueError(f"User with clerk_id {profile_data.get('clerk_id')} already exists")


async def get_user_profile(clerk_id: str) -> Optional[Dict[str, Any]]:
    """Get user profile by clerk_id"""
    db = get_database()
    collection = db[COLLECTION_NAME]
    
    profile = await collection.find_one({"clerk_id": clerk_id})
    if profile:
        profile["_id"] = str(profile["_id"])
    return profile


async def update_user_profile(clerk_id: str, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Update user profile"""
    db = get_database()
    collection = db[COLLECTION_NAME]
    
    # Add updated timestamp
    update_data["updated_at"] = datetime.utcnow()
    
    result = await collection.find_one_and_update(
        {"clerk_id": clerk_id},
        {"$set": update_data},
        return_document=True
    )
    
    if result:
        result["_id"] = str(result["_id"])
    return result


async def delete_user_profile(clerk_id: str) -> bool:
    """Delete user profile"""
    db = get_database()
    collection = db[COLLECTION_NAME]
    
    result = await collection.delete_one({"clerk_id": clerk_id})
    return result.deleted_count > 0


async def upsert_user_profile(clerk_id: str, profile_data: Dict[str, Any]) -> Dict[str, Any]:
    """Create or update user profile (upsert operation)"""
    db = get_database()
    collection = db[COLLECTION_NAME]
    
    print(f"🔍 Attempting to upsert profile for clerk_id: {clerk_id}")
    print(f"🔍 Database: {db.name}, Collection: {collection.name}")
    
    # Add updated timestamp
    profile_data["updated_at"] = datetime.utcnow()
    
    # Remove created_at from profile_data if it exists (to avoid conflict)
    profile_data.pop("created_at", None)
    
    result = await collection.find_one_and_update(
        {"clerk_id": clerk_id},
        {
            "$set": profile_data,
            "$setOnInsert": {"created_at": datetime.utcnow()}
        },
        upsert=True, 
        return_document=True
    )
    
    if result:
        result["_id"] = str(result["_id"])
        print(f"✅ Profile upserted successfully: {clerk_id}")
    else:
        print(f"⚠️ Upsert returned None for clerk_id: {clerk_id}")
    
    return result


# Profile data transformation helpers
def transform_parsed_resume_to_profile(parsed_data: Dict[str, Any], clerk_id: str, 
                                       cloudinary_url: str, filename: str) -> Dict[str, Any]:
    """Transform parsed resume data to profile schema"""
    return {
        "clerk_id": clerk_id,
        # Personal Information
        "first_name": parsed_data.get("First Name"),
        "last_name": parsed_data.get("Last Name"),
        "full_name": parsed_data.get("Full Name"),
        "email": parsed_data.get("Email"),
        "phone": parsed_data.get("Phone Number"),
        "location": parsed_data.get("Location"),
        "willing_to_relocate": parsed_data.get("Willing to relocate", False),
        
        # Professional Information
        "role": "job_seeker",
        "current_company": None,
        
        # Resume Information
        "resume_url": cloudinary_url,
        "resume_filename": filename,
        
        # Skills
        "technical_skills": parsed_data.get("Technical Skills", []),
        "soft_skills": parsed_data.get("Soft Skills", []),
        "skills": parsed_data.get("Skills", []),
        
        # Social Links
        "social_links": {
            "linkedin": parsed_data.get("LinkedIn Profile"),
            "github": parsed_data.get("GitHub Profile"),
            "portfolio": parsed_data.get("Portfolio URL")
        },
        
        # Experience
        "experience": [
            {
                "company": exp.get("Company"),
                "position": exp.get("Role"),
                "duration": exp.get("Duration"),
                "description": exp.get("Description")
            }
            for exp in parsed_data.get("Experience", [])
        ],
        
        # Education
        "education": [
            {
                "degree": edu.get("Degree"),
                "institution": edu.get("University"),
                "year": edu.get("Year")
            }
            for edu in parsed_data.get("Education", [])
        ],
        
        # Certifications
        "certifications": parsed_data.get("Certifications", []),
        
        # Projects
        "projects": [
            {
                "name": proj.get("Name"),
                "description": proj.get("Description"),
                "technologies": proj.get("Technologies", [])
            }
            for proj in parsed_data.get("Projects", [])
        ]
    }

##change
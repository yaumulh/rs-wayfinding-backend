from fastapi import FastAPI, APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
import uuid
from datetime import datetime, timezone
import aiofiles
import shutil

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create uploads directory
UPLOADS_DIR = ROOT_DIR / 'uploads'
UPLOADS_DIR.mkdir(exist_ok=True)

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Define Models
class Location(BaseModel):
    model_config = ConfigDict(extra="ignore")
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: Optional[str] = None
    coordinates: dict  # {x: float, y: float, z: float}
    icon_url: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class LocationCreate(BaseModel):
    name: str
    description: Optional[str] = None
    coordinates: dict
    icon_url: Optional[str] = None

class LocationUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    coordinates: Optional[dict] = None
    icon_url: Optional[str] = None

class AdminPinVerify(BaseModel):
    pin: str

class AdminSettings(BaseModel):
    model_config = ConfigDict(extra="ignore")
    pin: str = "1234"  # Default PIN

# Initialize admin settings
@app.on_event("startup")
async def initialize_admin():
    logger.info("Initializing admin settings...")
    try:
        existing = await db.admin_settings.find_one({"_id": "admin"})
        logger.info(f"Existing admin settings: {existing}")
        if not existing:
            await db.admin_settings.insert_one({
                "_id": "admin",
                "pin": "1234"
            })
            logger.info("Admin settings initialized with PIN 1234")
        else:
            logger.info("Admin settings already exist")
    except Exception as e:
        logger.error(f"Error initializing admin settings: {e}")

# Routes
@app.get("/")
async def root():
    return {"message": "Hospital AR Navigation API"}

@api_router.get("/")
async def api_root():
    return {"message": "Hospital AR Navigation API"}

# Admin PIN verification
@api_router.post("/admin/verify-pin")
async def verify_admin_pin(data: AdminPinVerify):
    logger.info(f"Verifying PIN: {data.pin}")
    settings = await db.admin_settings.find_one({"_id": "admin"})
    logger.info(f"Admin settings found: {settings}")
    if settings and settings.get("pin") == data.pin:
        logger.info("PIN verified successfully")
        return {"success": True, "message": "PIN verified"}
    logger.warning(f"PIN verification failed for PIN: {data.pin}")
    raise HTTPException(status_code=401, detail="Invalid PIN")

# Location endpoints
@api_router.get("/locations", response_model=List[Location])
async def get_locations():
    locations = await db.locations.find({}, {"_id": 0}).to_list(1000)
    for loc in locations:
        if isinstance(loc.get('created_at'), str):
            loc['created_at'] = datetime.fromisoformat(loc['created_at'])
    return locations

@api_router.get("/locations/{location_id}", response_model=Location)
async def get_location(location_id: str):
    location = await db.locations.find_one({"id": location_id}, {"_id": 0})
    if not location:
        raise HTTPException(status_code=404, detail="Location not found")
    if isinstance(location.get('created_at'), str):
        location['created_at'] = datetime.fromisoformat(location['created_at'])
    return location

@api_router.post("/locations", response_model=Location, status_code=201)
async def create_location(location: LocationCreate):
    location_dict = location.model_dump()
    location_obj = Location(**location_dict)
    
    doc = location_obj.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    
    await db.locations.insert_one(doc)
    return location_obj

@api_router.put("/locations/{location_id}", response_model=Location)
async def update_location(location_id: str, location_update: LocationUpdate):
    existing = await db.locations.find_one({"id": location_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Location not found")
    
    update_data = {k: v for k, v in location_update.model_dump().items() if v is not None}
    
    if update_data:
        await db.locations.update_one(
            {"id": location_id},
            {"$set": update_data}
        )
    
    updated = await db.locations.find_one({"id": location_id}, {"_id": 0})
    if isinstance(updated.get('created_at'), str):
        updated['created_at'] = datetime.fromisoformat(updated['created_at'])
    return updated

@api_router.delete("/locations/{location_id}")
async def delete_location(location_id: str):
    result = await db.locations.delete_one({"id": location_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Location not found")
    return {"success": True, "message": "Location deleted"}

# File upload endpoint
@api_router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    try:
        # Generate unique filename
        file_extension = Path(file.filename).suffix
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        file_path = UPLOADS_DIR / unique_filename
        
        # Save file
        async with aiofiles.open(file_path, 'wb') as f:
            content = await file.read()
            await f.write(content)
        
        # Return URL
        file_url = f"/api/uploads/{unique_filename}"
        return {"success": True, "url": file_url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Serve uploaded files
@api_router.get("/uploads/{filename}")
async def get_uploaded_file(filename: str):
    file_path = UPLOADS_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path)

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()

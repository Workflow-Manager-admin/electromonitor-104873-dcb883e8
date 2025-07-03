from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import database, models
from .endpoints import router as api_router

app = FastAPI(
    title="EB Electricity Monitor API",
    description="APIs for EB officers and customers to manage and monitor electricity usage, bills, and notifications.",
    version="1.0.0",
    openapi_tags=[
        {"name": "auth", "description": "Authentication and registration"},
        {"name": "users", "description": "User management"},
        {"name": "usage", "description": "Electricity usage readings"},
        {"name": "bills", "description": "Bills and billing status"},
        {"name": "notifications", "description": "Push/email notifications"},
        {"name": "analytics", "description": "Analytics for officer dashboard"},
        {"name": "dashboards", "description": "Officer & customer dashboard endpoints"},
    ]
)

# The following lines ensure the SQLAlchemy models are registered for migration/discovery tools
_ = (models, database.Base)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/", tags=["misc"])
def health_check():
    """PUBLIC_INTERFACE: Simple health check endpoint."""
    return {"message": "Healthy"}

# Mount the REST API endpoints
app.include_router(api_router)

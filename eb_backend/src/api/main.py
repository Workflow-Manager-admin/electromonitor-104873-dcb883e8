from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import database, models

app = FastAPI()

# The following lines ensure the SQLAlchemy models are registered for migration/discovery tools
_ = (models, database.Base)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def health_check():
    """PUBLIC_INTERFACE: Simple health check endpoint."""
    return {"message": "Healthy"}

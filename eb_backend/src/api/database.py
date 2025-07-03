import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# PUBLIC_INTERFACE
def get_mysql_db_url():
    """Get the MySQL database URL from environment variables."""
    user = os.environ.get("MYSQL_USER")
    password = os.environ.get("MYSQL_PASSWORD")
    host = os.environ.get("MYSQL_URL")
    db = os.environ.get("MYSQL_DB")
    port = os.environ.get("MYSQL_PORT", "3306")
    return f"mysql+mysqlconnector://{user}:{password}@{host}:{port}/{db}"

SQLALCHEMY_DATABASE_URL = get_mysql_db_url()

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# PUBLIC_INTERFACE
def get_db():
    """Yield database session for FastAPI dependency injection."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

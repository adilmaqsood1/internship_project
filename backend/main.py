from fastapi import FastAPI, Depends, Query
from sqlalchemy import create_engine, Column, Integer, String, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from pydantic import BaseModel
from typing import List
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import requests
import json
import os

# FastAPI app
app = FastAPI()

app.mount("/css", StaticFiles(directory="frontend/css"), name="css")

# Serve index.html when accessing the root route "/"
@app.get("/")
def serve_index():
    return FileResponse(os.path.join("frontend", "index.html"))

# Database setup
DATABASE_URL = "sqlite:///./search_history.db"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Define the search history model
class SearchHistory(Base):
    __tablename__ = "search_history"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True)
    query = Column(String, index=True)

# Create the tables
Base.metadata.create_all(bind=engine)

# Dependency to get the database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Pydantic model for returning product data
class Product(BaseModel):
    id: int
    title: str
    category: str
    price: float
    image: str

# Load sample product data from a JSON file
with open("backend/products.json") as f:
    products = json.load(f)["products"]

# AI Recommendation API (mock function)
def fetch_recommendations(query: str):
    # Example: external API call for AI-based recommendations
    api_url = "https://example.com/recommendation_api"
    response = requests.post(api_url, json={"query": query})
    if response.status_code == 200:
        return response.json().get("recommendations", [])
    return []

# Search endpoint with recommendations
@app.get("/search", response_model=List[Product])
def search_products(user_id: str, query: str = Query(..., min_length=1), db: Session = Depends(get_db)):
    query_lower = query.lower()
    search_results = []

    # Save search query to the database
    search_history = SearchHistory(user_id=user_id, query=query)
    db.add(search_history)
    db.commit()

    # Filter products by title or category
    for product in products:
        if query_lower in product["title"].lower() or query_lower in product["category"].lower():
            search_results.append(product)

    # Fetch AI-powered recommendations
    recommendations = fetch_recommendations(query)

    return {"search_results": search_results, "recommendations": recommendations}

# Fetch user search history
@app.get("/history/{user_id}")
def get_search_history(user_id: str, db: Session = Depends(get_db)):
    history = db.query(SearchHistory).filter(SearchHistory.user_id == user_id).all()
    return {"history": [item.query for item in history]}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
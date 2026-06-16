from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Ren Event Ticketing System",
    description="Backend API for Ren Event Ticketing Platform",
    version="0.1.0"
)

# CORS - allows frontend to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "Ren Event Ticketing System API is running! 🚀"}

@app.get("/health")
async def health():
    return {"status": "healthy"}
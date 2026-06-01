from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.database import init_db
from api.routers import auth, dashboard, products, search, admin, pipeline

app = FastAPI(title="Sentiment Intelligence Platform API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    init_db()


@app.get("/health")
def health():
    return {"status": "ok", "service": "sentiment-api"}


app.include_router(auth.router)
app.include_router(dashboard.router)
app.include_router(products.router)
app.include_router(search.router)
app.include_router(admin.router)
app.include_router(pipeline.router)

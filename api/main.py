from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.database import init_db
from api.routers.admin import config as admin_config
from api.routers.admin import dashboard as admin_dashboard
from api.routers.admin import logs as admin_logs
from api.routers.admin import pipeline as admin_pipeline
from api.routers.admin import products as admin_products
from api.routers.admin import users as admin_users
from api.routers.admin.keywords import router as admin_keywords
from api.routers.admin.channels_suggestion import router as admin_channels_suggestion
from api.routers.admin.backfill import router as admin_backfill
from api.routers.public import auth, products, search
from api.routers.user import auth as user_auth
from api.routers.user import dashboard as user_dashboard
from api.routers.user import products as user_products

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
app.include_router(user_auth.router)
app.include_router(products.router)
app.include_router(search.router)
app.include_router(user_products.router)
app.include_router(user_dashboard.router)
app.include_router(admin_dashboard.router)
app.include_router(admin_config.router)
app.include_router(admin_products.router)
app.include_router(admin_logs.router)
app.include_router(admin_pipeline.router)
app.include_router(admin_users.router)
app.include_router(admin_keywords)
app.include_router(admin_channels_suggestion)
app.include_router(admin_backfill)

from fastapi import FastAPI
from .graph_api import router as graph_router
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

app = FastAPI(title="Blockchain Graph Dashboard")

app.include_router(graph_router)

app.mount("/static", StaticFiles(directory="src/web/static"), name="static")


@app.get("/")
def root():
    return FileResponse("src/web/static/graph.html")
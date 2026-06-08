import os

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from .backend.graph_api import router as graph_router
from .backend.meta_api import router as metadata_router

app = FastAPI(title="Blockchain Graph Dashboard")

app.include_router(graph_router)
app.include_router(metadata_router)

app.mount("/static", StaticFiles(directory="src/web/static"), name="static")

@app.get("/")
def root():
    return FileResponse("src/web/static/home/home.html")
    
@app.get("/graph")
def graph_page():
    return FileResponse("src/web/static/graph/graph.html")
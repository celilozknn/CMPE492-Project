from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from .backend.graph_api import router as graph_router
from .backend.meta_api import router as metadata_router
from .backend.flow_api import router as flow_router
from .backend.ecosystem_api import router as ecosystem_router

app = FastAPI(
    title="ChainFlow Dashboard",
    docs_url=None,
    redoc_url=None,
    openapi_url=None
)

app.include_router(graph_router)
app.include_router(metadata_router)
app.include_router(flow_router)
app.include_router(ecosystem_router)

app.mount("/static", StaticFiles(directory="src/web/static"), name="static")

@app.get("/")
def root():
    return FileResponse("src/web/static/home/home.html")
    
@app.get("/graph")
def graph_page():
    return FileResponse("src/web/static/pagerank/pagerank.html")

@app.get("/flow")
def flow_page():
    return FileResponse("src/web/static/flow_explorer/flow_explorer.html")

@app.get("/ecosystem")
def ecosystem_page():
    return FileResponse("src/web/static/ecosystem/ecosystem.html")
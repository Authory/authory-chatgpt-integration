import os
import uvicorn
from fastapi import FastAPI, File, HTTPException, Depends, Body, UploadFile
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.staticfiles import StaticFiles
import requests

from models.api import (
    DeleteRequest,
    DeleteResponse,
    QueryRequest,
    QueryResponse,
    UpsertRequest,
    UpsertResponse,
)
from datastore.factory import get_datastore
from services.file import get_document_from_file


app = FastAPI()
app.mount("/.well-known", StaticFiles(directory=".well-known"), name="static")

# Create a sub-application, in order to access just the query endpoint in an OpenAPI schema, found at http://0.0.0.0:8000/sub/openapi.json when the app is running locally
sub_app = FastAPI(
    title="Authory Archive Search Plugin",
    description="A Plugin to allow ChatGPT to access your full Authory archive.",
    version="0.0.1",
    servers=[{"url": "https://authory.com"}],
)
app.mount("/sub", sub_app)

bearer_scheme = HTTPBearer()
BEARER_TOKEN = os.environ.get("BEARER_TOKEN")
assert BEARER_TOKEN is not None

AUTHORY_API_BASE_PATH = os.environ.get("AUTHORY_API_BASE_PATH")
assert AUTHORY_API_BASE_PATH is not None

class AuthoryAuthorizationCredentials():
    user_id: str
    scheme: str
    credentials: str

    def __init__(self, scheme: str, credentials: str, user_id: str) -> None:
         self.scheme = scheme
         self.user_id = user_id
         self.credentials = credentials
    

def validate_admin_token(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)):
    if credentials.scheme != "Bearer" or credentials.credentials != BEARER_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid or missing token")
    return credentials

def validate_authory_token(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)):
    if credentials.scheme != "Bearer":
        raise HTTPException(status_code=401, detail="Invalid or missing token")
    
    token = credentials.credentials

    response = requests.get(f"{AUTHORY_API_BASE_PATH}/api/v1/list-collections?key={token}")

    if response.status_code != 200:
        raise HTTPException(status_code=403, details="Authentication with Authory failed.")

    response_json = response.json()

    user_id = response_json["user"]["slug"]

    res = AuthoryAuthorizationCredentials(credentials.scheme, credentials.credentials, user_id)

    return res


@app.post(
    "/upsert-file",
    response_model=UpsertResponse,
)
async def upsert_file(
    file: UploadFile = File(...),
    token: AuthoryAuthorizationCredentials = Depends(validate_admin_token),
):
    document = await get_document_from_file(file)

    try:
        ids = await datastore.upsert([document])
        return UpsertResponse(ids=ids)
    except Exception as e:
        print("Error:", e)
        raise HTTPException(status_code=500, detail=f"str({e})")


@app.post(
    "/upsert",
    response_model=UpsertResponse,
)
async def upsert(
    request: UpsertRequest = Body(...),
    token: AuthoryAuthorizationCredentials = Depends(validate_admin_token),
):

    try:
        ids = await datastore.upsert(request.documents)
        return UpsertResponse(ids=ids)
    except Exception as e:
        print("Error:", e)
        raise HTTPException(status_code=500, detail="Internal Service Error")


@app.post(
    "/query",
    response_model=QueryResponse,
)
async def query_main(
    request: QueryRequest = Body(...),
    token: AuthoryAuthorizationCredentials = Depends(validate_authory_token),
):
    
    for queries in request.queries:
        queries.filter.author = token.user_id

    try:
        results = await datastore.query(
            request.queries,
        )
        return QueryResponse(results=results)
    except Exception as e:
        print("Error:", e)
        raise HTTPException(status_code=500, detail="Internal Service Error")


@sub_app.post(
    "/query",
    response_model=QueryResponse,
    # NOTE: We are describing the the shape of the API endpoint input due to a current limitation in parsing arrays of objects from OpenAPI schemas. This will not be necessary in future.
    description="Accepts search query objects array each with query and optional filter. Break down complex questions into sub-questions. Refine results by criteria, e.g. time / source, don't do this often. Split queries if ResponseTooLargeError occurs.",
)
async def query(
    request: QueryRequest = Body(...),
    token: AuthoryAuthorizationCredentials = Depends(validate_admin_token),
):
    try:
        results = await datastore.query(
            request.queries,
        )
        return QueryResponse(results=results)
    except Exception as e:
        print("Error:", e)
        raise HTTPException(status_code=500, detail="Internal Service Error")


@app.delete(
    "/delete",
    response_model=DeleteResponse,
)
async def delete(
    request: DeleteRequest = Body(...),
    token: AuthoryAuthorizationCredentials = Depends(validate_authory_token),
):
    if not (request.ids or request.filter or request.delete_all):
        raise HTTPException(
            status_code=400,
            detail="One of ids, filter, or delete_all is required",
        )
    try:
        success = await datastore.delete(
            ids=request.ids,
            filter=request.filter,
            delete_all=request.delete_all,
        )
        return DeleteResponse(success=success)
    except Exception as e:
        print("Error:", e)
        raise HTTPException(status_code=500, detail="Internal Service Error")


@app.on_event("startup")
async def startup():
    global datastore
    datastore = await get_datastore()


def start():
    uvicorn.run("server.main:app", host="0.0.0.0", port=8000, reload=True)

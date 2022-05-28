from fastapi import FastAPI
from fastapi import Request
from fastapi.responses import JSONResponse
import json


app = FastAPI(title="FAQ_API", version="0.1.0")

from sentence_transformers import SentenceTransformer

model = SentenceTransformer(
    "sentence-transformers/bert-base-nli-mean-tokens", device="cpu"
)


@app.post("/encode")
async def encode(request: Request):
    body = await request.body()
    body_json = json.loads(body)
    embeddings = model.encode(body_json["sentences"])
    return JSONResponse(content={"embeddings": embeddings.tolist()})


if __name__ == "__main__":
    # uvicorn app:app --reload
    # python -m uvicorn app:app --reload --port 8082
    pass

from fastapi import FastAPI
from fastapi.responses import JSONResponse
import api_key as ak


from es import search_knn, get_qas

app = FastAPI(title="FAQ_API", version="0.1.0")


@app.get("/search/{email}")
def search(
    email: str, 
    api_key: str, 
    query: str = None, 
    show_list: str = None, 
    max_results: int = 10
):
    if api_key != ak.get_api_key(email):
        return JSONResponse(content={"error": "Invalid API key"})

    if show_list == "yes":
        qas = get_qas(email)
        res = [x["_source"] for x in qas["hits"]["hits"]]
        return JSONResponse(content={"results": res})

    if query is None:
        return JSONResponse(content={"error": "No query provided"})     

    res = search_knn(query=query, login_email=email, max_results=max_results)
    return JSONResponse(
        content={
            "results": res,
            "query": query,
            "email": email,
            "max_results": max_results,
        }
    )


if __name__ == "__main__":
    # uvicorn app:app --reload
    # python -m uvicorn app:app --reload --port 8081
    pass

# -*-coding:utf-8-*-
import os, sys
import time
from dotenv import load_dotenv
import logger as mylog
import requests
from elasticsearch import Elasticsearch

load_dotenv()
ELASTIC_PASSWORD = os.environ["ELASTIC_PASSWORD"]
ELASTIC_CA_CERTS = os.environ["ELASTIC_CA_CERTS"]
DEFAULT_INDEX_NAME = os.environ["DEFAULT_INDEX_NAME"]
DEFAULT_PIPELINE_ID = os.environ["DEFAULT_PIPELINE_ID"]

EMB_API_URL = os.environ["EMB_API_URL"]
EMB_CLIENT_SECRET = os.environ["EMB_CLIENT_SECRET"]

log = mylog.get_logger(__name__)

es = Elasticsearch(
    "https://localhost:9200",
    ca_certs=ELASTIC_CA_CERTS,
    basic_auth=("elastic", ELASTIC_PASSWORD),
)


def create_index(index_name=DEFAULT_INDEX_NAME):
    """
    Create index for KNN search
    https://www.elastic.co/guide/en/elasticsearch/reference/current/dense-vector.html
    https://www.elastic.co/guide/en/elasticsearch/reference/current/knn-search-api.html
    """
    # create index, if the index does not exists
    if not es.indices.exists(index=index_name):
        log.info("{} No index. Let's create one".format(index_name))

        mappings = {
            "properties": {
                "login_email": {"type": "keyword"},
                "text_field": {"type": "text"},
                "text_embedding": {
                    "type": "dense_vector",
                    "dims": 768,
                    "index": True,
                    "similarity": "cosine",
                },
                "answer": {"type": "text"},
            }
        }

        es.indices.create(index=index_name, mappings=mappings)
        log.info("{} Index created".format(index_name))


def create_pipeline(pipeline_id, index_name=DEFAULT_INDEX_NAME):
    """
    [
        {
            "inference": {
            "model_id": "sentence-transformers__bert-base-nli-mean-tokens"
            }
        },
        {
            "rename": {
            "field": "ml.inference.predicted_value",
            "target_field": "text_embedding"
            }
        }
    ]
    Create a pipeline for the given model_id
    """
    # create a pipeline for the given model_id
    # rename is more efficient than set
    pipeline = {
        "description": "Pipeline for {}".format(pipeline_id),
        "processors": [
            {"inference": {"model_id": pipeline_id}},
            {
                "rename": {
                    "field": "ml.inference.predicted_value",
                    "target_field": "text_embedding",
                }
            },
        ],
    }
    res = es.ingest.put_pipeline(id=pipeline_id, body=pipeline)


def add_qa(
    login_email, q, a, pipeline_id=DEFAULT_PIPELINE_ID, index_name=DEFAULT_INDEX_NAME
):
    """
    POST my-data-stream/_doc?pipeline=embedding
    {
        "login_email": "hunkim@gmail.com"
        "text_field": "What is the best way to learn Python?"
        "answer": "Use Python's built-in online Python tutorial."
    }
    """

    doc = {
        "login_email": login_email,
        "text_field": q,
        "answer": a,
    }

    res = es.index(index=index_name, pipeline=pipeline_id, document=doc)

    doc["_id"] = res["_id"]

    log.info("Inserted {}".format(doc))

    return doc


def del_qa(doc_id, index_name=DEFAULT_INDEX_NAME):
    """
    DELETE faq_search/_doc/doc_id
    """
    res = es.delete(index=index_name, id=doc_id)
    log.info("Deleted {}".format(doc_id))
    return res


# get all for debugging
def _get_all(index_name=DEFAULT_INDEX_NAME):
    """
    GET faq_search/_search
    {
        "query": {
            "match_all": {}
        }
    }
    """
    res = es.search(index=DEFAULT_INDEX_NAME, query={"match_all": {}}, size=1000)
    return res


# get all names, dates, and emails from the given login_email
def get_qas(login_email, index_name=DEFAULT_INDEX_NAME):
    """
    GET faq_search/_search
        {
        "query": {
            "match": {
            "login_email": "test1"
            }
        }
    }
    """
    # get all names, dates, and emails fro the given login_email
    res = es.search(
        index=index_name,
        query={"match": {"login_email": login_email}},
        source=["text_field", "answer"],
        size=10000,
    )
    return res


def _get_embedding(text, pipeline_id):
    """
    FIXME: This is a hack, since they don't have a pipeline for search, 
           we need create a function to get embedding using simulate

    POST _ingest/pipeline/embedding/_simulate
    {
      "docs": [
        {
          "_source": {
            "text_field": "The quick brown fox jumps over the lazy dog."
          }
        }
      ]
    }
    """
    docs = [{"_source": {"text_field": text}}]

    # simulate the pipeline
    res = es.ingest.simulate(id=pipeline_id, docs=docs)

    # check if res has text_embedding
    if (
        "doc" in res["docs"][0]
        and "_source" in res["docs"][0]["doc"]
        and "text_embedding" in res["docs"][0]["doc"]["_source"]
    ):
        return res["docs"][0]["doc"]["_source"]
    else:
        return None


def _get_embedding_from_api(sentence):
    """
    Get embedding from FastAPI with huggingface
    """

    headers = {"auth_token": EMB_CLIENT_SECRET}
    sentences = {"sentences": [sentence]}

    response = requests.post(EMB_API_URL, headers=headers, json=sentences)
    return response.json()


def search_knn(
    query,
    login_email,
    max_results=10,
    index_name=DEFAULT_INDEX_NAME,
):
    """
    search knn
    https://www.elastic.co/guide/en/elasticsearch/reference/current/knn-search-api.html
    """
    log.info("Input question: {}".format(query))

    encode_start_time = time.time()
    query_embedding = _get_embedding(query, "embedding")["text_embedding"]
    encode_end_time = time.time()

    encode_api_start_time = time.time()
    query_embedding_from_api = _get_embedding_from_api(query)["embeddings"][0]
    encode_api_end_time = time.time()

    # assert query_embedding == query_embedding_from_api
    log.info("Encode simulate time: {}".format(encode_end_time - encode_start_time))
    log.info("Encode API      time: {}".format(encode_api_end_time - encode_api_start_time))
    
    filter = []
    assert login_email is not None

    filter = [{"term": {"login_email": login_email}}]

    sem_search = es.knn_search(
        index=index_name,
        knn={
            "field": "text_embedding",
            "query_vector": query_embedding,
            "k": max_results,
            # must be less than 10000
            "num_candidates": min(max_results * 50, 10000),
        },
        filter=filter,
        source=["text_field", "answer"],
    )

    log.info(
        "Computing the embedding took {:.3f} seconds, embedding API took {:.3f} seconds, KNN API with ES took {:.3f} seconds".format(
            encode_end_time - encode_start_time,
            encode_api_end_time - encode_api_start_time,
            sem_search["took"] / 1000,
        )
    )

    log.debug("\nSemantic Search results:")
    result_list = []
    for hit in sem_search["hits"]["hits"][0:max_results]:
        hit["_source"]["score"] = hit["_score"]
        result_list.append(hit["_source"])
        log.debug("\t{}".format(hit["_source"]["text_field"][:80]))

    return result_list


def delete_index(index_name=DEFAULT_INDEX_NAME):
    if es.indices.exists(index=index_name):
        es.indices.delete(index=index_name)
        log.info("{} Index deleted".format(index_name))
    else:
        log.info("{} Index does not exist".format(index_name))


if __name__ == "__main__":
    print(_get_embedding("The quick brown fox jumps over the lazy dog.", "embedding"))
    print(_get_embedding_from_api("The quick brown fox jumps over the lazy dog."))

    qas = [
        {"login_email": "test1", "q": "What is the meaning of life?", "a": "42"},
        {"login_email": "test1", "q": "Sung's office?", "a": "6251"},
        {"login_email": "test1", "q": "Birthday?", "a": "6/31"},
    ]

    # create index
    create_index()

    # if argument includes "add", add qas
    if len(sys.argv) > 1 and sys.argv[1] == "add":
        for qa in qas:
            add_qa(
                qa["login_email"], qa["q"], qa["a"], pipeline_id="embedding"
            )  # insert to index
            # Sleep for a while to reflect the insert
            time.sleep(5)

    # get all
    res = _get_all()
    print(res)

    res = get_qas("test1")
    print(res)

    res = search_knn("What is the meaning of life?", "test1")
    print(res)

    # if argument includes "del", delete index
    if len(sys.argv) > 1 and sys.argv[1] == "del":
        # delete index
        delete_index()

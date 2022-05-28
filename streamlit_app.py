import streamlit as st
import es
import os
import logger as mylog

from dotenv import load_dotenv
import streamlit_google_oauth as oauth
import api_key as ak

load_dotenv()
client_id = os.environ["GOOGLE_CLIENT_ID"]
client_secret = os.environ["GOOGLE_CLIENT_SECRET"]
redirect_uri = os.environ["GOOGLE_REDIRECT_URI"]
SEARCH_API_URL = os.environ["SEARCH_API_URL"]


logger = mylog.get_logger(__name__)


def load_qas(login_email):
    all_data = es.get_qas(login_email)
    display_data = [x["_source"] for x in all_data["hits"]["hits"]]
    ids = [{"_id": x["_id"]} for x in all_data["hits"]["hits"]]

    for i, x in enumerate(display_data):
        x["_id"] = ids[i]["_id"]

    return display_data


def del_qa(id):
    print("delete" + id)
    es.del_qa(id)
    # remove from list qa list's id is the same
    qalist = [x for x in st.session_state.qalist if x["_id"] != id]
    st.session_state.qalist = qalist
    logger.info(f"Deleted QA {id}")


def main(user_id=None, user_email=None):
    st.write(
        f"""
        ## 🎂 FAQ Vector Search 
        Just put name questiom and answers, and it will make a vector FAQ search.
        """
    )

    # Define initial state.
    if "qalist" not in st.session_state:
        st.session_state.qalist = load_qas(user_email)

    # Show widgets to add new QA.
    st.write(
        "<style>.main * div.row-widget.stRadio > div{flex-direction:row;}</style>",
        unsafe_allow_html=True,
    )

    with st.expander("REST API", expanded=False):
        api_key = ak.get_api_key(user_email)
        api_url = f"{SEARCH_API_URL}/{user_email}?api_key={api_key}"
        st.write("* Search: ", api_url + "&query=text")
        st.write("* List: ", api_url + "&show_list=yes")

    with st.expander("FAQ Search Test", expanded=True):
        query = st.text_input("Query")
        if st.button("Search"):
            res = es.search_knn(query=query, login_email=user_email)
            for i, r in enumerate(res, start=1):
                st.write(i, r["text_field"], r["answer"], r["score"])

    with st.expander("Add New QA", expanded=True):
        question = st.text_input("Question")
        answer = st.text_area("Answer")
        if st.button("Add New Question"):
            res = es.add_qa(user_email, question, answer)
            st.session_state.qalist.append(res)
            logger.info(f"Added QA {question}: {answer}")

    with st.expander("FAQ List", expanded=True):
        for i, b in enumerate(st.session_state.qalist):
            col1, col2, col3, col5 = st.columns([0.05, 0.2, 0.3, 0.15])
            # format_str = (
            #        '<span style="color: grey; text-decoration: line-through;">{}</span>'
            #    )
            format_str = "{}"
            col1.write(i + 1)
            col2.markdown(
                format_str.format(b["text_field"]),
                unsafe_allow_html=True,
            )

            col3.markdown(
                format_str.format(b["answer"]),
                unsafe_allow_html=True,
            )

            # col4.markdown(
            #    format_str.format(b["email"]),
            #    unsafe_allow_html=True,
            # )

            col5.button("Delete", key=b["_id"], on_click=del_qa, args=(b["_id"],))


#  streamlit run app.py --server.runOnSave=true --server.enableCORS=false --server.enableXsrfProtection=false --server.port=6666
if __name__ == "__main__":
    st.set_page_config(page_title="FAQ Vector Search", layout="wide")

    login_info = oauth.login(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
        login_button_text="Continue with Google",
        logout_button_text="Logout",
    )
    if login_info:
        user_id, user_email = login_info
        main(user_id=user_id, user_email=user_email)
    else:
        st.write("## 🎂 FAQ Vector Search")

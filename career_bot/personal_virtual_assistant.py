import os
import streamlit as st
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.chat_models import ChatOpenAI
from langchain.chains import ConversationalRetrievalChain
from langchain.document_loaders.csv_loader import CSVLoader
from langchain.vectorstores import FAISS
# from langchain.vectorstores import Chroma
# from langchain.prompts import PromptTemplate
from langchain.prompts import load_prompt
from streamlit import session_state as ss
from pymongo import MongoClient
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
import uuid
import json
import time

import datetime

def is_valid_json(data):
    try:
        json.loads(data)
        return True
    except json.JSONDecodeError:
        return False


if "mongodB_pass" in os.environ:
    mongodB_pass = os.getenv("mongodB_pass")
else: mongodB_pass = st.secrets["mongodB_pass"]
#HUTta2fUrfqSb2C
# Setting up a mongo_db connection to store conversations for deeper analysis
uri = "mongodb+srv://dbUser:"+mongodB_pass+"@cluster0.wjuga1v.mongodb.net/?retryWrites=true&w=majority"

@st.cache_resource
def init_connection():
    return MongoClient(uri, server_api=ServerApi('1'))
client = init_connection()


db = client['conversations_db']
conversations_collection = db['conversations']


if "OPENAI_API_KEY" in os.environ:
    openai_api_key = os.getenv("OPENAI_API_KEY")
else: openai_api_key = st.secrets["OPENAI_API_KEY"]
    
# else:
#     openai_api_key = st.sidebar.text_input(
#         label="#### Your OpenAI API key 👇",
#         placeholder="Paste your openAI API key, sk-",
#         type="password")
    

#Creating Streamlit title and adding additional information about the bot
st.title("Art Kreimer's resume bot")
with st.expander("⚠️Disclaimer"):
    st.write("""This is a work in progress chatbot based on a large language model. It can answer questions about Art Kreimer""")

path = os.path.dirname(__file__)


# Loading prompt to query openai
prompt_template = path+"/templates/template4.json"
prompt = load_prompt(prompt_template)
#prompt = template.format(input_parameter=user_input)

# loading embedings
faiss_index = path+"/faiss_index"

# Loading CSV file
data_source = path+"/data/about_art_chatbot_data_v3.csv"

# Function to store conversation
def store_conversation(conversation_id, user_message, bot_message, answered):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    data = {
        "conversation_id": conversation_id,
        "timestamp": timestamp,
        "user_message": user_message,
        "bot_message": bot_message,
        "answered": answered
    }
    conversations_collection.insert_one(data)

embeddings = OpenAIEmbeddings()

#using FAISS as a vector DB
if os.path.exists(faiss_index):
        vectors = FAISS.load_local(faiss_index, embeddings)
    
else:
    # Creating embeddings for the docs
    if data_source :
        loader = CSVLoader(file_path=data_source, encoding="utf-8")
        #loader.
        data = loader.load()
        vectors = FAISS.from_documents(data, embeddings)
        vectors.save_local("faiss_index")

retriever=vectors.as_retriever(search_type="similarity", search_kwargs={"k":6, "include_metadata":True, "score_threshold":0.6})
#Creating langchain retreval chain 
chain = ConversationalRetrievalChain.from_llm(llm = ChatOpenAI(temperature=0.0,model_name='gpt-3.5-turbo', openai_api_key=openai_api_key), 
                                                retriever=retriever,return_source_documents=True,verbose=True,chain_type="stuff",
                                                max_tokens_limit=4097, combine_docs_chain_kwargs={"prompt": prompt})


def conversational_chat(query):
    with st.spinner("Thinking..."):
        # time.sleep(1)
        # Be conversational and ask a follow up questions to keep the conversation going"
        result = chain({"system": 
        "You are a Resume Bot, a comprehensive, interactive resource for exploring Artiom (Art) Kreimer's background, skills, and expertise. Be polite and provide answers based on the provided context only. Use only the provided data and not prior knowledge.", 
                        "question": query, 
                        "chat_history": st.session_state['history']})
    
    if (is_valid_json(result["answer"])):              
        data = json.loads(result["answer"])
    else:
        data = json.loads('{"answered":"false", "response":"Hmm... Something is not right. I\'m experiencing technical difficulties. Try asking your question again or ask another question about Art Kreimer\'s professional background and qualifications. Thank you for your understanding.", "questions":["What is Art\'s professional experience?","What projects has Art worked on?","What are Art\'s career goals?"]}')
    # Access data fields
    answered = data.get("answered")
    response = data.get("response")
    questions = data.get("questions")

    full_response="--"

    st.session_state['history'].append((query, response))
    
    if ('I am tuned to only answer questions' in response) or (response == ""):
        full_response = """Unfortunately, I can't answer this question. My capabilities are limited to providing information about Art Kreimer's professional background and qualifications. If you have other inquiries, I recommend reaching out to Art on [LinkedIn](https://www.linkedin.com/in/artkreimer/). I can answer questions like: \n - What is Art Kreimer's educational background? \n - Can you list Art Kreimer's professional experience? \n - What skills does Art Kreimer possess? \n"""
        store_conversation(st.session_state["uuid"], query, full_response, answered)
        
    else: 
        markdown_list = ""
        for item in questions:
            markdown_list += f"- {item}\n"
        full_response = response + "\n\n What else would you like to know about Art? You can ask me: \n" + markdown_list
        store_conversation(st.session_state["uuid"], query, full_response, answered)
    return(full_response)

if "uuid" not in st.session_state:
    st.session_state["uuid"] = str(uuid.uuid4())

if "openai_model" not in st.session_state:
    st.session_state["openai_model"] = "gpt-3.5-turbo"

if "messages" not in st.session_state:
    st.session_state.messages = []
    with st.chat_message("assistant"):
        message_placeholder = st.empty()

        welcome_message = """
            Welcome! I'm **Resume Bot**, specialized in providing information about Art Kreimer's professional background and qualifications. Feel free to ask me questions such as:

            - What is Art Kreimer's educational background?
            - Can you outline Art Kreimer's professional experience?
            - What skills and expertise does Art Kreimer bring to the table?

            I'm here to assist you. What would you like to know?
            """
        message_placeholder.markdown(welcome_message)
        

if 'history' not in st.session_state:
    st.session_state['history'] = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Ask me about Art Kreimer"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        
        user_input=prompt
        st.markdown(prompt)

    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""
        full_response = conversational_chat(user_input)
        message_placeholder.markdown(full_response)
    st.session_state.messages.append({"role": "assistant", "content": full_response})

import json
import os
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain.agents import create_react_agent, AgentExecutor
from langchain_community.agent_toolkits.load_tools import load_tools
from langchain import hub

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import WebBaseLoader
from langchain_community.vectorstores import Chroma
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnableSequence

import bs4

OPENAI_API_KEY = os.environ['OPENAI_API_KEY']

llm = ChatOpenAI(model="gpt-3.5-turbo")


# query = """
# Vou viajar para Londres em agosto de 2024.
# Quero que faça um roteiro de viagem para mim com eventos que irão ocorrer na da viagem e com o preço de passagem de São Paulo para Londres.
# """


def research_agent(query, llm):

    tools = load_tools(['ddg-search', 'wikipedia'], llm=llm)

    prompt = hub.pull("hwchase17/react")

    agent = create_react_agent(llm, tools, prompt)

    agent_executor = AgentExecutor(
        agent=agent, tools=tools, prompt=prompt)

    web_context = agent_executor.invoke({"input": query})
    return web_context['output']


# print(research_agent(query, llm))


def load_data():
    loader = WebBaseLoader(
        web_paths=("https://www.dicasdeviagem.com/inglaterra/",),
        bs_kwargs=dict(parse_only=bs4.SoupStrainer(
            class_=("postcontentwrap", "pagetitleloading background-imaged loading-dark")))
    )

    docs = loader.load()
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000, chunk_overlap=200)
    splits = text_splitter.split_documents(docs)
    vectorstore = Chroma.from_documents(
        documents=splits, embedding=OpenAIEmbeddings())

    retriever = vectorstore.as_retriever()
    return retriever


def get_relevant_docs(query):
    retriever = load_data()
    relevant_documents = retriever.invoke(query)
    return relevant_documents


def supervisor_agent(query, llm, web_context, relevant_documents):
    prompt_template = """
    Você é um gerente de uma agência de viagens.
    Sua resposta final deverá ser um roteiro completo e detalhado.
    Utilize o contexto de eventos e preços de passagens, o input do usuário e também
    os documentos relevantes para elaborar o roteiro.
    Contexto: {web_context}
    Documento relevante: {relevant_documents}
    Usuário: {query}
    Assistente:
    """

    prompt = PromptTemplate(
        input_variables=['web_context', 'relevant_documents', 'query'],
        template=prompt_template
    )

    sequence = RunnableSequence(prompt | llm)

    response = sequence.invoke(
        {"web_context": web_context, "relevant_documents": relevant_documents, "query": query})

    return response


def get_response(query, llm):
    web_context = research_agent(query, llm)
    relevant_documents = get_relevant_docs(query)
    response = supervisor_agent(query, llm, web_context, relevant_documents)
    return response


print(get_response("Vou viajar de maringá para ushuaia e preciso de um roteiro com preços de passagem", llm).content)


def lambda_handler(event, context):
    body = json.loads(event.get('body', {}))
    query = body.get('question', 'Parametro question não fornecido')
    try:
        response = get_response(query, llm).content
        print("response", response)
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json"
            },
            "body": json.dumps({
                "message": "Tarefa concluída com sucesso",
                "details": response,
            }),
        }
    except Exception as e:
        print("Exception: ", str(e))
        return {
            "statusCode": 400,
            "headers": {
                "Content-Type": "application/json"
            },
            "body": {
                "message": str(e)
            }
        }
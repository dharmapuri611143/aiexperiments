import streamlit as st
from elasticsearch import Elasticsearch
from google.cloud import storage
from vertexai.language_models import TextEmbeddingModel, TextGenerationModel
import base64
import pandas as pd
import openpyxl
# Initialize Elasticsearch connection
es_host = 'https://34.27.33.112:9200'
es = Elasticsearch(
    hosts=[es_host],
    verify_certs=False,
    basic_auth=("elastic", "042H1Zx2R3ztB05kPxdL0UN1")
)
index_name = 'dc_poc_rules_test0.4'

# Initialize TextEmbeddingModel
embedding_model = TextEmbeddingModel.from_pretrained("textembedding-gecko@001")

# Initialize storage client
storage_client = storage.Client()

# Main function to process user input
def user_input(user_question):
    response_text, final_response = search_question_and_generate_response1(user_question)
    st.success(f" AI Justification : {response_text}")
    st.info(f" Data Classification Type: {final_response}")


# Function to search questions and generate responses
def search_questions_and_generate_responses(questions):
    given_info = "is belong to which information classification level? Result should be in one word either of Confidential or Restricted or Internal or Public"
    questions = [question + " " + given_info for question in questions]

    # Search for the nearest neighbors
    embeddings = embedding_model.get_embeddings(questions)
    script_queries = [{
        "script_score": {
            "query": {"match_all": {}},
            "script": {
                "source": "cosineSimilarity(params.query_vector, 'embedding') + 1.0",
                "params": {"query_vector": embedding.values}
            }
        }
    } for embedding in embeddings]

    # Execute the searches
    responses = []
    for script_query in script_queries:
        res = es.search(index=index_name, query=script_query)

        final_text = "Final Result"

        # Retrieve text content from storage
        for bucket in storage_client.list_buckets():
            bucket_name = bucket.name
            try:
                source_blob_name = res["hits"]["hits"][0]['_id'].replace("gs://", "").replace(bucket_name + "/", "")
                blob = storage_client.bucket(bucket_name).blob(source_blob_name)
                text_content = blob.download_as_text()
                if text_content:
                    index = source_blob_name.rfind("/") + 1
                    retreivefilename = source_blob_name[index:].replace(".txt", ".pdf")
                    print("Match from Storage", bucket_name)
                    final_text += text_content
            except Exception as e:
                print(f"No Matches from Storage in {bucket_name}: {e}")

        parameters = {
            "temperature": 0.2,
            "max_output_tokens": 256,
            "top_p": 0.8,
            "top_k": 40
        }

        prompt = f"""
        If it is helpful, use the following information when answering questions:
        {final_text}
        {questions}
        """

        # Initialize TextGenerationModel
        generation_model = TextGenerationModel.from_pretrained("text-bison@001")

        # Generate response
        response = generation_model.predict(prompt, **parameters)

        # Check if response contains classification keywords
        classification_keywords = ["internal", "public", "restricted", "confidential"]
        found_classifications = []
        for keyword in classification_keywords:
            if keyword in response.text.lower():
                found_classifications.append(keyword)

        if len(found_classifications) == 1:
            finalResponse = found_classifications[0]
        elif len(found_classifications) > 1:
            finalResponse = "CHECK REMARKS"
        else:
            finalResponse = "not found"
        responses.append((response.text, finalResponse))
    return responses


# Function to search question and generate response
def search_question_and_generate_response1(question):
    given_info = "is belong to which information classification level? Result should be in one word either of Confidential or Restricted or Internal or Public"
    question += " " + given_info

    # Search for the nearest neighbors
    embeddings = embedding_model.get_embeddings([question])
    script_query = {
        "script_score": {
            "query": {"match_all": {}},
            "script": {
                "source": "cosineSimilarity(params.query_vector, 'embedding') + 1.0",
                "params": {"query_vector": embeddings[0].values}
            }
        }
    }

    # Execute the search
    res = es.search(index=index_name, query=script_query)

    final_text = "Final Result"

    # Retrieve text content from storage
    for bucket in storage_client.list_buckets():
        bucket_name = bucket.name
        try:
            source_blob_name = res["hits"]["hits"][0]['_id'].replace("gs://", "").replace(bucket_name + "/", "")
            blob = storage_client.bucket(bucket_name).blob(source_blob_name)
            text_content = blob.download_as_text()
            if text_content:
                index = source_blob_name.rfind("/") + 1
                retreivefilename = source_blob_name[index:].replace(".txt", ".pdf")
                print("Match from Storage", bucket_name)
                final_text += text_content
        except Exception as e:
            print(f"No Matches from Storage in {bucket_name}: {e}")

    parameters = {
        "temperature": 0.2,
        "max_output_tokens": 256,
        "top_p": 0.8,
        "top_k": 40
    }

    prompt = f"""
    If it is helpful, use the following information when answering questions:
    {final_text}
    {question}
    """

    # Initialize TextGenerationModel
    generation_model = TextGenerationModel.from_pretrained("text-bison@001")

    # Generate response
    response = generation_model.predict(prompt, **parameters)

    # Check if response contains classification keywords
    classification_keywords = ["internal", "public", "restricted", "confidential"]
    found_classifications = []
    finalResponse = "NOT FOUND"
    for keyword in classification_keywords:
       if keyword in response.text.lower():
        found_classifications.append(keyword)

    if len(found_classifications) == 1:
        finalResponse = found_classifications[0]
    elif len(found_classifications) > 1:
        for keyword in found_classifications:
            if ("is: "+keyword in response.text.lower() or "is "+keyword in response.text.lower() or "is a "+keyword in response.text.lower() or "is: "+keyword in response.text.lower() or "is "+keyword in response.text.lower() or "is a "+keyword in response.text.lower()):
              finalResponse = keyword
              break

    return response.text, finalResponse


# Function to process questions and generate output Excel file
import openpyxl

# Function to process questions and generate output Excel file
def process_questions(uploaded_file):
    if uploaded_file is not None:
        if uploaded_file.type == 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet':  
            df = pd.read_excel(uploaded_file)
            if df is not None:
                responses = []
                textresponses = []
                for index, row in df.iterrows():
                    if not pd.isnull(row[1]):
                        response_text, final_response  = search_question_and_generate_response1(row[1])
                        finalrespons = '';
                        responses.append(final_response)
                        textresponses.append(response_text)
                    else:
                        responses.append("")
                        textresponses.append("") 

                df['Classification Type'] = responses
                df['Additional Remarks by AI'] = textresponses
                output_file_path = 'output.xlsx'
                df.to_excel(output_file_path, index=False)
                # Adjust column widths based on content length
                wb = openpyxl.load_workbook(output_file_path)
                ws = wb.active
                for col in ws.columns:
                    max_length = 0
                    column = col[0].column_letter  # Get the column name
                    for cell in col:
                        try:  # Necessary to avoid error on empty cells
                            if len(str(cell.value)) > max_length:
                                max_length = len(cell.value)
                        except:
                            pass
                    adjusted_width = (max_length + 2) * 1.2
                    ws.column_dimensions[column].width = adjusted_width
                wb.save(output_file_path)

                st.markdown(get_download_link(output_file_path), unsafe_allow_html=True)
            else:
                st.error("Failed to process Excel file.")
        else:
            st.error("Please upload an Excel file.")
    else:
        st.error("Please upload a file.")

# Function to generate a download link
def get_download_link(file_path):
    with open(file_path, 'rb') as f:
        data = f.read()
    b64 = base64.b64encode(data).decode()
    href = f'<a href="data:application/octet-stream;base64,{b64}" download="{file_path}">Download Excel file</a>'
    return href

# Main function
def main():
    st.set_page_config("Data Classification Advisor !!")
    st.header("Data Classification Advisor !!")

    # Text input for user question
    user_question = st.text_input("Ask Me and I Will Tell You: Your Data Classification Type")
    
    # Button to process questions
    if st.button("Submit"):
        st.empty()
        with st.spinner("Processing"):
            user_input(user_question)
    
    # File uploader for Excel file
    uploaded_file = st.sidebar.file_uploader("Upload Excel file", type=["xlsx", "xls"], accept_multiple_files=False)

    # Button to process questions
    if st.sidebar.button("Process Data"):
        st.empty()
        with st.spinner("Processing"):
            process_questions(uploaded_file)

# Execute main function
if __name__ == "__main__":
    main()

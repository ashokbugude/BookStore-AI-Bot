import gradio as gr
import json
import os
from datetime import datetime
from elasticsearch import Elasticsearch
from openai import OpenAI


f = open('./database/schema/bookstore.json')
books_json = json.load(f)
f.close()

def load_env_file(file_path=".env"):
    with open(file_path, "r") as file:
        for line in file:
            # Skip comments and empty lines
            if line.startswith("#") or not line.strip():
                continue

            # Split line into key-value pairs
            key, value = map(str.strip, line.split("=", 1))

            # Set environment variable
            os.environ[key] = value

load_env_file()

OPENAI_API_KEY=os.environ.get('OPENAI_API_KEY')
ELASTIC_SEARCH_URL=os.environ.get('ELASTIC_SEARCH_URL')
ELASTIC_SEARCH_API_KEY=os.environ.get('ELASTIC_SEARCH_API_KEY')

print(OPENAI_API_KEY)
print(ELASTIC_SEARCH_URL)
print(ELASTIC_SEARCH_API_KEY)

OpenAIClient = OpenAI(api_key=OPENAI_API_KEY)

client = Elasticsearch(
  ELASTIC_SEARCH_URL,
  api_key=ELASTIC_SEARCH_API_KEY
)


prompt = """As owner and conversational agent of online bookstore, respond to customer queries with below information.\n
         Elastic Search Schemas:\n
         books - """ + json.dumps(books_json) + """
         Below are the policies\n
         Payment Policy:

        We accept major credit cards, debit cards, and other secure payment methods.
        Payment must be completed at the time of purchase.
        All transactions are processed through a secure payment gateway to ensure the safety of your financial information.
        Shipping Policy:

        We offer standard and expedited shipping options.
        Shipping costs and estimated delivery times are provided at the checkout.
        Orders are usually processed and shipped within [X] business days.
        Customers will receive a tracking number to monitor the status of their shipment.
        Return Policy:

        Returns are accepted within [X] days of receiving the order.
        Items must be in their original condition, unopened, and with all packaging intact.
        Customers are responsible for return shipping costs unless the return is due to an error on our part.
        Refunds will be processed within [X] business days after receiving the returned item.
        Privacy Policy:

        We respect your privacy and protect your personal information.
        Customer data is used solely for processing orders and improving our services.
        We do not share or sell customer information to third parties.
        Payment information is securely processed and not stored on our servers.
        Customer Service:

        Our customer service team is available [X] hours a day, [X] days a week.
        Contact us via [email/phone/live chat] for any inquiries, assistance, or feedback.
        We strive to respond to customer queries within [X] business days.
        Product Availability:

        Product availability is subject to change without notice.
        In the event of a stock issue, customers will be notified, and alternative options may be offered.
        Promotions and Discounts:

        Promotions and discounts may be offered periodically.
        Terms and conditions for each promotion will be clearly communicated.
        Security:

        We use secure sockets layer (SSL) technology to protect your personal and payment information.
        Our website is regularly monitored for security vulnerabilities.
        International Shipping:

        International shipping is available with specific terms and conditions.
        Customers are responsible for any customs duties or taxes applicable in their country.
        Terms of Service:

        By using our website, you agree to comply with our terms of service.
        We reserve the right to update or modify our policies at any time.
         """
messages = [
    {"role":"system", "content": prompt}
]

# API key should have cluster monitor rights
print(client.info())

def get_chat_gpt_response(user_input):
    messages.append({
        "role":"user", "content": user_input
    })
    response = OpenAIClient.chat.completions.create(
      model="gpt-3.5-turbo",
      messages=messages
    )
    return response.choices[0].message.content

def add_to_cart(customer_id, book_id, quantity):
    timestamp = datetime.now().isoformat()

    cart_item = {
        "customer_id": customer_id,
        "book_id": book_id,
        "quantity": quantity,
        "timestamp": timestamp
    }

    client.index(index="cart", body=cart_item)

def contains_element(string, elements):
    lowercase_string = string.lower()
    lowercase_elements = [element.lower() for element in elements]
    return any(element in lowercase_string for element in lowercase_elements)

def get_response(user_input):
    if contains_element(user_input, ['find','search', 'list', 'available']):
        try:
            book_query = get_chat_gpt_response("Generate elastic search query using match_phrase as json for below user request considering the schema structures.\n" + user_input)
            result = client.search(index="bookstore", body=book_query)
            message = ''
            if len(result['hits']['hits']) == 0:
                message = 'Sorry, this book is currently unavailable. We will update you as soon as its available.Is there anything else I can help you with?'
            else:
                message = 'The book(s) are available with below details\n\n'                
                for hit in result['hits']['hits']:
                    message+="Title: " + hit['_source']['title'] +"\n" + "Author: " + hit['_source']['author'] + "\n" + "Description: " + hit['_source']['description'] + "\n\n"
                return message
        except Exception as ex:
            print(f"Unexpected error: {ex}")
            message = "Sorry, I could not process your request. If you are searching for books in our store, try querying using any of the below formats\n"
            message += " find book with title as <title_name>\n or \n find books with genre as <genre> \n or \n find books with author as <author>"
            return message
    elif contains_element(user_input, ['similar']):
        try:
            book_query = get_chat_gpt_response("Generate elastic search query as json limiting results to 5 for below user request considering the schema structures.\n" + user_input)
            result = client.search(index="bookstore", body=book_query)
            message = ''
            if len(result['hits']['hits']) == 0:
                message = 'Sorry, there are no results currently.Is there anything else I can help you with?'
            else:
                message = 'Below are the recommended book(s) \n\n'                
                for hit in result['hits']['hits']:
                    message+="Title: " + hit['_source']['title'] +"\n" + "Author: " + hit['_source']['author'] + "\n" + "Description: " + hit['_source']['description'] + "\n\n"
                output_message = get_chat_gpt_response("Stop Generating elastic search query and Convert below text into meaningful descriptive sentences and use non-contextual information to provide additional information\n" + message)
                message = output_message + "\n\n Would you like more information on any of these books?"
        except Exception as ex:
            print(f"Unexpected error: {ex}")
            message = "Sorry, I could not process your request. If you are looking for books written by particular author and similar to a title in our store, try querying using below format\n"
            message += "Recommend books similar to 'Machine Learning Yearning' by authors like 'Andrew Ng'"
    elif contains_element(user_input, ['recommend','recommended','recommendations']):
        try:
            book_query = get_chat_gpt_response("Generate elastic search query using match_phrase as json limiting results to 5 for below user request considering the schema structures.\n" + user_input)
            result = client.search(index="bookstore", body=book_query)
            message = ''
            if len(result['hits']['hits']) == 0:
                message = 'Sorry, there are no recommendations currently.Is there anything else I can help you with?'
            else:
                message = 'Below are the recommended book(s) \n\n'                
                for hit in result['hits']['hits']:
                    message+="Title: " + hit['_source']['title'] +"\n" + "Author: " + hit['_source']['author'] + "\n" + "Description: " + hit['_source']['description'] + "\n\n"
                output_message = get_chat_gpt_response("Stop Generating elastic search query and Convert below text into meaningful descriptive sentences and use non-contextual information to provide additional information\n" + message)
                message = output_message + "\n\n Would you like more information on any of these books?"
        except Exception as ex:
            print(f"Unexpected error: {ex}")
            message = "Sorry, I could not process your request. If you are looking for recommendations for books in our store, try querying using below format\n"
            message += " Can you recommend a book on machine learning?"
    elif contains_element(user_input,['add','cart']):
        try:
            user_input = 'What is the title and author of the book referenced by below sentence and above context.\n' + user_input
            title_author_message = get_chat_gpt_response(user_input)
            message = 'Get title and author from below sentence and convert to json response.\n' + title_author_message
            title_author_text = get_chat_gpt_response(message)
            title_author = json.loads(title_author_text)
            title = title_author['title']
            author = title_author['author']
            book_query = {
                "query": {
                    "match": {
                        "title": title
                    },
                    "match": {
                        "author": author
                    }
                }
            }

            result = client.search(index="bookstore", body=book_query)
            if len(result['hits']['hits']) == 0:
                message = 'Sorry, this book is currently unavailable. We will update you as soon as its available.Is there anything else I can help you with?'
            else:
                for hit in result['hits']['hits']:
                    if hit['_source']['stock_quantity'] == 0:
                        message = 'Sorry, this book is currently unavailable. We will update you as soon as its available.Is there anything else I can help you with?'
                    else:
                        book_id = hit['_id']
                        update_body = {
                                            "script": {
                                                "source": "ctx._source.stock_quantity -= params.quantity",
                                                "lang": "painless",
                                                "params": {
                                                    "quantity": 1
                                                }
                                            }
                                        }
                        response = client.update(index="bookstore", id=book_id, body=update_body)
                        print(response)
                        
                        customer_id = 1
                        quantity = 1
                        add_to_cart(customer_id, int(book_id), quantity)
                        message = ''' I've added \'''' + title + '''\' to your cart. You can proceed to checkout whenever you're ready. Is there anything else I can help you with?'''
        except Exception as ex:
            print(f"Unexpected error: {ex}")
            message = "Sorry, I could not process your request. If you are looking to add book to cart, try querying using below format\n"
            message += "Can you add book with title 'The Great Gatsby' to the cart?"
    elif contains_element(user_input,['status']):
        try:
            book_query = get_chat_gpt_response("Generate elastic search query as json for below user request considering the schema structures.\n" + user_input)
            result = client.search(index="order", body=book_query)
            message = ''
            if len(result['hits']['hits']) == 0:
                message = 'Sorry, Order is not found.Try specifying correct order number'
            else:             
                for hit in result['hits']['hits']:
                    message="The status of your order is : " + hit['_source']['status']
                message += "\n\n Is there anything else I can help you with?"
        except Exception as ex:
            print(f"Unexpected error: {ex}")
            message = "Sorry, I could not process your request. If you are looking to know the status of your order, try querying using below format\n"
            message += "what is the status of order with id 'ORD005'"
    elif contains_element(user_input,['return']):
        try:
            order_text = get_chat_gpt_response("Get order id as json from below user request.\n" + user_input)
            order_json = json.loads(order_text)
            order_id = order_json['order_id']
            order_query = {
                "query": {
                    "match": {
                        "order_id": order_id
                    }
                }
            }
            result = client.search(index="order", body=order_query)
            message = ''
            if len(result['hits']['hits']) == 0:
                message = 'Sorry, Order is not found.Try specifying correct order number.'
            else:
                for hit in result['hits']['hits']:
                    order_id = hit['_id']
                    update_body = {
                                        "script": {
                                            "source": "ctx._source.status = params.status",
                                            "lang": "painless",
                                            "params": {
                                                "status":"return in progress"
                                            }
                                        }
                                    }
                    response = client.update(index="order", id=order_id, body=update_body)
                    print(response)
                    message="The order status is set to be returned. The delivery agent would be visiting your place to pick up the item"
                message += "\n\n Is there anything else I can help you with?"
        except Exception as ex:
            print(f"Unexpected error: {ex}")
            message = "Sorry, I could not process your request. If you are looking to return your order, try querying using below format\n"
            message += "Return order with id 'ORD005'"
    else:
        message = get_chat_gpt_response(user_input)
    return message    

def gradio_interface(user_input):
    try:    
        response = get_response(user_input)
    except Exception as e:
        print(f"Unexpected error: {e}")
        response = 'Apologies, I could not process your query. Could you pls rephrase your query.'
        
    return response

iface = gr.Interface(fn=gradio_interface, inputs="text", outputs="text")
iface.launch()
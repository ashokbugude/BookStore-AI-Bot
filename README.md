# BookStore-AI-Bot

A conversational agent for an online bookstore capable of answering predefined queries. Utilize a pre-trained Large Language Model (LLM) for generating responses.

## Setup

**1. Install the requirements in requirements file.**

```shell
pip install -r requirements.txt
```

**2. Set environment variables**

```shell
OPENAI_API_KEY= <OpenAI API Key>
ELASTIC_SEARCH_URL= <Elastic search url>
ELASTIC_SEARCH_API_KEY= <Elastic search api key>
```

**3. Initialise database**

1. Import database schemas from database/schemas folder
2. Import sample data from database/docs folder


**4. Run the application**

```shell
python main.py
```

url would be displayed in the terminal. Open it in browser



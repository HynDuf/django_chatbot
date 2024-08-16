from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib import auth
from django.contrib.auth.models import User
from django.utils import timezone

from .models import Chat, Talk

import os
from dotenv import load_dotenv
from langchain_community.document_loaders import CSVLoader
from langchain_community.vectorstores import FAISS
from langchain_cohere import CohereEmbeddings, ChatCohere
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain

load_dotenv()  # Load environment variables from .env
COHERE_API_KEY = os.getenv("COHERE_API_KEY")
os.environ["COHERE_API_KEY"] = COHERE_API_KEY

# 1. Vectorise the sales response csv data
loader = CSVLoader(file_path="iqtree_faq.csv")
documents = loader.load()

embeddings = CohereEmbeddings(model="embed-english-light-v3.0")

# Create the FAISS vector store from documents
try:
    db = FAISS.from_documents(documents, embeddings)
except ValueError as e:
    print("Error creating FAISS vector store:", e)
    raise

# 2. Function for similarity search
def retrieve_info(query):
    similar_response = db.similarity_search(query, k=4)
    page_contents_array = [doc.page_content for doc in similar_response]
    return page_contents_array

# 3. Setup LLMChain & prompts
llm = ChatCohere(model="command-r")

template = """
You are a personal assistant. 
I will share a message with you and you will give me the best answer based on my private information. 

Below is a message I received from the prospect:
{message}

Here is the private information I give you:
{private_info}

Please response cohesively. Make sure you only use the private information when the message is related to them. If the message is about something completely different, just ignore the private information. Besides, Just give the response and remove redundant details.
"""

prompt = PromptTemplate(
    input_variables=["message", "private_info"],
    template=template
)

chain = LLMChain(llm=llm, prompt=prompt)

# 4. Retrieval augmented generation
def generate_response(message):
    private_info = retrieve_info(message)
    response = chain.run(message=message, private_info=private_info)
    return response

def truncate_title(title):
    return title if len(title) <= 22 else title[:19] + '...'

# Create your views here.
def chatbot(request, talk_id=None):
    # Fetch all talks for the current user
    talks = Talk.objects.filter(user=request.user).order_by('-updated_at')
    selected_talk = None

    # If a talk_id is provided, fetch the specific talk, otherwise leave selected_talk as None
    if talk_id:
        selected_talk = get_object_or_404(Talk, id=talk_id, user=request.user)

    # Handle POST request for sending a message
    if request.method == 'POST':
        message = request.POST.get('message')
        if message:
            # Create a new talk if none is selected or provided
            if not selected_talk:
                selected_talk = Talk.objects.create(
                    user=request.user, 
                    title=truncate_title(message)  # Use the first 20 characters of the message as the title
                )
            else:
                selected_talk.title = truncate_title(message)  # Update the title to the latest
            response = generate_response(message)
            chat = Chat(user=request.user, talk=selected_talk, message=message, response=response)
            chat.save()
            selected_talk.updated_at = timezone.now()
            selected_talk.save()
            return JsonResponse({
                'message': message,
                'response': response,
                'talks': list(talks.values('id', 'title'))
            })

    # Get chats for the selected talk, if any
    chats = Chat.objects.filter(talk=selected_talk).order_by('created_at') if selected_talk else []

    return render(request, 'chatbot.html', {'chats': chats, 'talks': talks, 'selected_talk': selected_talk})

def home_redirect(request):
    if request.user.is_authenticated:
        return redirect('chatbot')  # Redirect to the chat page
    else:
        return redirect('login')  # Redirect to the login page

def login(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = auth.authenticate(request, username=username, password=password)
        if user is not None:
            auth.login(request, user)
            return redirect('chatbot')
        else:
            error_message = 'Invalid username or password'
            return render(request, 'login.html', {'error_message': error_message})
    else:
        return render(request, 'login.html')

def register(request):
    if request.method == 'POST':
        username = request.POST['username']
        email = request.POST['email']
        password1 = request.POST['password1']
        password2 = request.POST['password2']

        if password1 == password2:
            try:
                user = User.objects.create_user(username, email, password1)
                user.save()
                auth.login(request, user)
                return redirect('chatbot')
            except:
                error_message = 'Error creating account'
                return render(request, 'register.html', {'error_message': error_message})
        else:
            error_message = 'Passwords do not match'
            return render(request, 'register.html', {'error_message': error_message})
    return render(request, 'register.html')

def logout(request):
    auth.logout(request)
    return redirect('login')

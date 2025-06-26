import os
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

# === Configure Flask ===
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY")

# === Configure Gemini 2.0 Flash ===
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel(model_name="gemini-2.0-flash")

# === In-memory data ===
chat_history = []
feedback_data = []
concerns = []
users = {}  # Simple in-memory user store

# === Helper Functions ===
def analyze_sentiment(text):
    try:
        response = model.generate_content(
            f"Analyze the sentiment of this feedback and respond with ONLY one word: Positive, Neutral, or Negative.\n\nFeedback: {text}"
        )
        sentiment = response.text.strip()
        return sentiment if sentiment in ["Positive", "Neutral", "Negative"] else "Neutral"
    except Exception as e:
        print(f"[Sentiment Error]: {e}")
        return "Neutral"

def generate_ai_response(prompt):
    try:
        response = model.generate_content(
            f"""
You are an Indian government assistant AI.

When answering the user question, always respond in this structured format with 5 sections:

1. 🧪 **Details of the PAN Card or for any other government services**
2. 📄 **Required Documents**
3. 🌐 **Official Government Website** (as a clickable highlighted hyperlink)
4. 📝 **Procedure to Apply**
5. 🔐 **Secure Platforms to Apply** (list them clearly)

Each point must be:
- In a separate paragraph
- Plain HTML supported (like <b>, <a>, <br>)
- Use bold titles
- Include links like <a href='https://www.incometax.gov.in' target='_blank'>incometax.gov.in</a>

User's question: {prompt}
or give the answers according to the user questions
"""
        )
        return response.text.strip() if response and hasattr(response, "text") else "Sorry, I couldn't generate a full response right now."
    except Exception as e:
        print(f"[AI Response Error]: {e}")
        return "I'm unable to process your request at this time. Please try again later."

# === Routes ===
@app.route('/')
def home():
    sentiment_counts = {
        'positive': len([f for f in feedback_data if f['sentiment'] == 'Positive']),
        'neutral': len([f for f in feedback_data if f['sentiment'] == 'Neutral']),
        'negative': len([f for f in feedback_data if f['sentiment'] == 'Negative'])
    }

    quick_guide = [
        {"title": "PAN Card", "description": "Apply or update your PAN card online.", "image": "static/images/pan.png", "link": "/services/pan"},
        {"title": "Aadhaar", "description": "Aadhaar card linking and updates.", "image": "static/images/aadhaar.png", "link": "/services/aadhaar"},
        {"title": "Voter ID", "description": "Register or modify your Voter ID.", "image": "static/images/voter.png", "link": "/services/voter"},
        {"title": "Driving License", "description": "Learn how to apply or renew DL.", "image": "static/images/dl.png", "link": "/services/dl"},
        {"title": "Ration Card", "description": "Access food security benefits.", "image": "static/images/ration.png", "link": "/services/ration"}
    ]

    latest_updates = [
        {"title": "Digital India Expansion", "description": "New rural e-services launched this month.", "image": "static/images/digital-india.png", "link": "https://www.digitalindia.gov.in"},
        {"title": "Budget 2025 Highlights", "description": "Read key updates on tax and welfare schemes.", "image": "static/images/budget.png", "link": "https://www.indiabudget.gov.in"},
        {"title": "AI in Governance", "description": "Explore how AI is transforming citizen services.", "image": "static/images/ai-news.png", "link": "https://meity.gov.in"}
    ]

    return render_template('index.html', sentiment_counts=sentiment_counts, now=datetime.now(), quick_guide=quick_guide, latest_updates=latest_updates)

@app.route('/ai-assistant')
def ai_assistant():
    return redirect(url_for('chat'))

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/services')
def services():
    return render_template('services.html')

@app.route('/services/pan')
def pan():
    return render_template('pan.html')

@app.route('/services/aadhaar')
def aadhaar():
    return render_template('aadhaar.html')

@app.route('/services/dl')
def dl():
    return render_template('dl.html')

@app.route('/services/ration')
def ration():
    return render_template('ration.html')

@app.route('/services/voter')
def voter():
    return render_template('voter.html')

@app.route('/chat')
def chat():
    return render_template('chat.html', chat_history=chat_history, now=datetime.now())

@app.route('/ask', methods=['POST'])
def ask_question():
    question = request.form.get('question')
    language = request.form.get('language', 'English')
    user = session.get('user', {})
    email = user.get('email', 'anonymous')

    if question:
        prompt = f"{question}. Respond in {language}."
        ai_response = generate_ai_response(prompt)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

        chat_history.append({'role': 'user', 'content': question, 'timestamp': timestamp})
        chat_history.append({'role': 'ai', 'content': ai_response, 'timestamp': timestamp})
    else:
        flash("Please enter a question.", "warning")

    return redirect(url_for('chat'))

@app.route('/feedback', methods=['POST'])
def submit_feedback():
    feedback_text = request.form.get('feedback')
    if feedback_text:
        sentiment = analyze_sentiment(feedback_text)
        feedback_data.append({'text': feedback_text, 'sentiment': sentiment, 'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M"), 'user': "anonymous"})
        return render_template('chat.html', sentiment=sentiment, chat_history=chat_history)
    else:
        flash("Feedback cannot be empty.", "danger")
    return redirect(url_for('chat'))

@app.before_request
def set_language_preference():
    if 'language' not in session:
        session['language'] = 'English'

@app.route('/concern', methods=['POST'])
def submit_concern():
    concern_text = request.form.get('concern')
    concern_type = request.form.get('concern_type')
    if concern_text:
        concerns.append({
            'id': len(concerns) + 1,
            'text': concern_text,
            'type': concern_type,
            'status': 'Open',
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M"),
            'user': "anonymous"
        })
        return render_template('chat.html', concern_submitted=len(concerns), chat_history=chat_history)
    else:
        flash("Concern cannot be empty.", "danger")
    return redirect(url_for('chat'))

@app.route('/dashboard')
def dashboard():
    sentiment_counts = {
        'positive': len([f for f in feedback_data if f['sentiment'] == 'Positive']),
        'neutral': len([f for f in feedback_data if f['sentiment'] == 'Neutral']),
        'negative': len([f for f in feedback_data if f['sentiment'] == 'Negative'])
    }
    total_interactions = len(chat_history) // 2
    total_feedback = sum(sentiment_counts.values())

    return render_template('dashboard.html', sentiment_counts=sentiment_counts, total_interactions=total_interactions, total_feedback=total_feedback, recent_concerns=concerns[-5:][::-1], now=datetime.now())

@app.route('/healthz')
def health_check():
    return "OK", 200

# === Auth Routes ===
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        if email in users and users[email]['password'] == password:
            session['user'] = {'name': users[email]['name'], 'email': email}
            flash("Login successful!", "success")
            return redirect(url_for('home'))
        else:
            flash("Invalid credentials.", "danger")

    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')

        if email in users:
            flash("Email already registered.", "danger")
        else:
            users[email] = {'name': name, 'email': email, 'password': password}
            session['user'] = {'name': name, 'email': email}
            flash("Signup successful!", "success")
            return redirect(url_for('home'))

    return render_template('signup.html')

@app.route('/logout')
def logout():
    session.pop('user', None)
    flash("You have been logged out.", "info")
    return redirect(url_for('home'))

# === Start App ===
if __name__ == '__main__':
    app.run(debug=True)

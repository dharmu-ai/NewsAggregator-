from flask import Flask, render_template, request, url_for
import requests
import streamlit as st
from bs4 import BeautifulSoup
from datetime import datetime

app = Flask(__name__)

# ---------- Utility: simple categorizer ----------
CATEGORY_KEYWORDS = {
    "World":       ["world", "global", "ukraine", "india", "china", "europe", "middle east", "africa", "america"],
    "Business":    ["business", "market", "stocks", "economy", "inflation", "trade", "bank", "startup"],
    "Technology":  ["tech", "technology", "ai", "artificial intelligence", "software", "app", "iphone", "android", "robot", "chip"],
    "Sports":      ["sport", "sports", "football", "cricket", "tennis", "match", "tournament", "olympic", "goal", "ipl"],
    "Entertainment":["film", "movie", "bollywood", "hollywood", "tv", "series", "music", "celebrity", "show"],
    "Science":     ["science", "space", "nasa", "research", "study", "astronomy"],
    "Health":      ["health", "covid", "vaccine", "hospital", "disease", "mental"],
    "Environment": ["climate", "environment", "weather", "heat", "flood", "wildfire", "energy"],
    "Education":   ["education", "university", "school", "students", "exam"],
    "Politics":    ["election", "politics", "government", "parliament", "minister", "policy"],
    "Spiritual":   ["spiritual", "meditation", "prayer", "mindfulness", "inner peace", "faith", "religion"],
    "Cyber Security": ["cyber", "security", "hacking", "data breach", "malware", "phishing", "ransomware"],
    "Animals":     ["animals", "wildlife", "pets", "nature", "zoo", "endangered", "species"]
}

ALL_CATEGORIES = ["All"] + list(CATEGORY_KEYWORDS.keys())

def guess_category(title: str) -> str:
    t = title.lower()
    for cat, keys in CATEGORY_KEYWORDS.items():
        if any(k in t for k in keys):
            return cat
    return "World"

# ---------- Scraper with robust selector + fallback ----------
def get_bbc_news(max_items=20):
    url = "https://www.bbc.com/news"
    headers = {"User-Agent": "Mozilla/5.0"}
    news_list = []

    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        # BBC often uses <a data-testid="internal-link"> with nested <h3>
        items = soup.select("a[data-testid='internal-link'] h3")[:max_items]

        for idx, tag in enumerate(items, start=1):
            title = tag.get_text(strip=True)
            if not title:
                continue

            parent_a = tag.find_parent("a")
            href = parent_a.get("href") if parent_a else None

            if href and href.startswith("/"):
                link = "https://www.bbc.com" + href
            elif href:
                link = href
            else:
                link = "https://www.bbc.com/news"

            news_list.append({
                "id": idx,
                "title": title,
                "url": link,
                "content": f"This is a short summary for: {title}.",
                "category": guess_category(title)
            })

    except Exception as e:
        print("⚠️ Error fetching BBC:", e)

    # Fallback if scraping fails
    if not news_list:
        fallback = [
        ("AI is Transforming the World", "Technology", "https://www.bbc.com/news/technology"),
        ("Markets Rally as Inflation Cools", "Business", "https://www.bbc.com/news/business"),
        ("Global Leaders Meet for Summit", "World", "https://www.bbc.com/news/world"),
        ("Major Finals Set to Thrill Fans", "Sports", "https://www.bbc.com/sport"),
        ("discovering the beatiful adventures","travel","https://www.bbc.com/travel"),
        ("Exploring the Depths of the Ocean", "Environment", "https://www.bbc.com/news/science-environment"),
        ("Green Energy Adoption Surges", "Environment", "https://www.bbc.com/future/columns/climate-change"),
        ("Universities Roll Out New Programs", "Education", "https://www.bbc.com/news/education"),
        ("Elections Around the Corner", "Politics", "https://www.bbc.com/news/politics"),
        ("New Species Discovered in Amazon", "Science", "https://www.bbc.com/news/science-environment"),
        ("Mental Health Awareness Rises", "Health", "https://www.bbc.com/news/health"),
        ("Blockbuster Movie Breaks Records", "Entertainment", "https://www.bbc.com/news/entertainment_and_arts"),
        ("Cyber Security Threats on the Rise", "Cyber Security", "https://www.bbc.com/news/technology"),
        ("The Rise of Electric Vehicles", "Technology", "https://www.bbc.com/news/technology"),
        ("AI-Powered Healthcare Innovations", "Health", "https://www.bbc.com/news/health"),
        ("Amazing Wildlife Discoveries", "Animals", "https://www.bbc.com/news/science-environment")

    ]

        for i, (title, cat, url) in enumerate(fallback, start=1):
            news_list.append({
                "id": i,
                "title": title,
                "url": url,
                "content": f"This is a short summary for: {title}.",
                "category": cat
            })

    return news_list

# ---------- Routes ----------
@app.route("/")
def index():
    query = request.args.get("q", "").strip().lower()
    category = request.args.get("category", "All")
    news_list = get_bbc_news(max_items=30)

    # Filter by category
    if category and category != "All":
        news_list = [n for n in news_list if n.get("category") == category]

    # Filter by search query
    if query:
        news_list = [
            n for n in news_list
            if query in n["title"].lower() or query in n["content"].lower()
        ]

    # Reassign IDs
    for i, n in enumerate(news_list, start=1):
        n["id"] = i

    last_updated = datetime.now().strftime("%d %b %Y, %I:%M %p")
    return render_template(
        "news.html",
        news_list=news_list,
        last_updated=last_updated,
        query=query,
        category=category,
        categories=ALL_CATEGORIES
    )

@app.route("/news/<int:news_id>")
def detail(news_id):
    news_list = get_bbc_news(max_items=30)

    if 1 <= news_id <= len(news_list):
        news_item = news_list[news_id - 1]
    else:
        news_item = news_list[0]

    return render_template("detail.html", news=news_item)


@app.route('/ask', methods=['POST'])
def ask():
    try:
        data = request.get_json(force=True)
        question = data.get('question') if isinstance(data, dict) else None
        if not question:
            return jsonify({'answer': '⚠️ No question provided.'}), 400

        # If Gemini available and configured, call the model
        if genai_available and model is not None:
            try:
                response = model.generate_content(question)
                answer = getattr(response, 'text', None) or str(response)
            except Exception as e:
                answer = f'⚠️ Gemini error: {e}'
        else:
            # Fallback: simple echo or canned reply
            answer = f"(local) You asked: {question}"

        return jsonify({'answer': answer})
    except Exception as e:
        return jsonify({'answer': f'⚠️ Server error: {e}'}), 500

import os
from flask import Flask, render_template, request, jsonify
from datetime import datetime

# Gemini API setup (hardcoded for now)
GEMINI_API_KEY = "YOUR_GEMINI_API_KEY_HERE"  # Replace with your actual API key

try:
    import google.generativeai as genai
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel("models/gemini-2.0-flash")
    genai_available = True
except Exception as _e:
    model = None
    genai_available = False

if __name__ == "__main__":
    app.run(debug=True)

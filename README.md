***Voyage AI: Smart Travel Planner Chatbot***

Overview
Voyage AI is a conversational travel planning assistant that helps users explore travel destinations, discover activities, and get tailored recommendations. Built with Streamlit for an interactive interface and powered by modular APIs, It aims to provide a simple yet engaging way to plan trips.

The project is structured into frontend and backend components for clarity and scalability. The backend handles destination data and logic, while the frontend delivers a smooth, user-friendly experience.

Features :

Interactive Chatbot: Ask about travel destinations and get instant responses.
Destination Highlights: Each city includes curated activities, local attractions, and experiences.
Extensible Data: Easily add more locations and activities to expand the chatbot’s knowledge.
Streamlit Interface: Deployed as a web application with a clean, modern interface.
Modular Design: Separated into backend (API logic) and frontend (UI), making it easier to maintain.

Tech Stack :

Python 3.10+
Streamlit (for UI)
FastAPI (for backend API service)
Pyngrok (for tunneling in development)
Uvicorn (to serve the backend API)

Project Structure
Voyage_AI/
│
├── backend/
│   ├── main.py           # FastAPI backend logic for destinations
│   └── requirements.txt  # Backend dependencies
│
├── frontend/
│   ├── app.py            # Streamlit frontend interface
│   └── requirements.txt  # Frontend dependencies
│
├── README.md             # Project documentation
└── data/                 # (Optional) Store external data files if required

Installation and Setup
1. Clone the Repository
git clone https://github.com/your-username/Voyage_AI.git
cd Voyage_AI

2. Backend Setup
cd backend
pip install -r requirements.txt
uvicorn main:app --reload

3. Frontend Setup
cd frontend
pip install -r requirements.txt
streamlit run app.py

Deployment : 

You can deploy the project directly using Streamlit Community Cloud or other hosting platforms.
If using Streamlit Cloud, deploy the frontend/app.py file.
Ensure the backend is hosted separately (or mocked within the frontend if deploying as a single app).

Usage :

Open the Streamlit app in your browser.
Type in a travel query such as:
“Tell me about Paris”
“What can I do in Tokyo?”
“Suggest activities in London”
The chatbot responds with curated activities and highlights.

Current Destinations Covered :

Paris
London
Tokyo
New York
Sydney
(Easily extendable — more cities can be added in the backend logic.)

Future Enhancements

Integration with real travel APIs for live flight, hotel, and weather information.
Personalized recommendations based on user preferences.
Multi-language support.
Expanded database of destinations and experiences.

License
This project is licensed under the MIT License. You are free to use, modify, and distribute it.

Contributors
Developed by Anirudha Pujari with guidance on modular project design, deployment practices, and travel chatbot functionality.

# PSS Intelligent Citizen Service Assistant (ICSA) 
 
AI-powered chatbot enhancement for PUP Caloocan's Planning and Standards System (PSS). 
 
## Tech Stack 
- FastAPI (Python) - RAG chatbot backend 
- React + Vite - Frontend 
- pgvector - Vector similarity search 
- ClickHouse - Analytics logging 
- Groq/Llama 3.1 - LLM inference 
 
## Setup
 
1. **Configure Environment Variables**
   Before running the application, copy the example environment file:
   ```bash
   cp .env.example .env
   ```
 
2. **Start Services**
   Run the following to start the backend services:
   ```bash
   docker-compose up -d
   ```

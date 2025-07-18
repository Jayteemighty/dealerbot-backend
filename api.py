from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import json
import os
from pathlib import Path
from dotenv import load_dotenv
from dealerbot import query_dealerbot_agent, compare_vehicles
from submit_form import submit_inquiry
from database import store_chat, fetch_all_chats
from session_manager import session_manager
from feedback import FeedbackManager
from typing import Dict, Any, Optional

SCRIPT_DIR = Path(__file__).parent
VEHICLE_DATA = SCRIPT_DIR / "vehicle_data.json"

load_dotenv()  # Loads the variables from .env
PRODUCTION_MODE = os.getenv("PRODUCTION_MODE", "false").lower() == "true"

app = FastAPI()

# CORS configuration
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://ladus-ace.github.io",
    "http://ladus-ace.github.io/dealerbot_fe/",
    "https://dealerbot.netlify.app",
    "https://dealerbot-fe.vercel.app",
    "https://web.postman.co",
    "https://ladus.io/dealerbot/",
    "https://bjfrontend.vercel.app"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize feedback manager
feedback_manager = FeedbackManager()

@app.post("/user_query")
async def handle_query(request: Request):
    """
    Handle the incoming query from the frontend.
    """
    try:
        data = await request.json()
        user_query = data.get('query', '')
        session_id = data.get('session_id')

        # Validate query
        if not user_query or not user_query.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Query cannot be empty"
            )

        # Create a new session if none exists
        if not session_id:
            session_id = session_manager.create_session()
        
        # Process the query using the dealerbot agent with session context
        response = query_dealerbot_agent(user_query, session_id)

        # --- Consistent response structure ---
        response_type = "formatted"
        message = None
        data_field = None

        if isinstance(response, dict):
            # If already has type/message/data, use them
            response_type = response.get("type", "formatted")
            message = response.get("message")
            data_field = response.get("data")
            # If dict is just raw vehicle data (all vehicles), set type and data
            if response_type == "raw_data" and not message:
                message = "Here is the full vehicle inventory."
        else:
            # If response is a string, treat as formatted message
            message = response

        # Save the user query and response to the database with roles
        try:
            store_chat([
                {
                    "role": "user",
                    "message": user_query,
                    "session_id": session_id
                },
                {
                    "role": "bot",
                    "message": json.dumps(message),
                    "session_id": session_id
                }
            ])
        except Exception as e:
            print(f"[DB ERROR] Failed to store chat: {e}")

        return {
            "type": response_type,
            "message": message,
            "data": data_field,
            "session_id": session_id
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@app.post("/compare_vehicles")
async def handle_vehicle_comparison(request: Request):
    """
    Handle vehicle comparison requests.
    Expects a JSON array of vehicle data objects to compare.
    """
    try:
        data = await request.json()
        vehicles_data = data.get('vehicles', [])
        session_id = data.get('session_id')
        
        if not vehicles_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No vehicles provided for comparison"
            )
            
        if len(vehicles_data) < 2:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least two vehicles are required for comparison"
            )
            
        # Compare the vehicles with session context
        comparison = compare_vehicles(vehicles_data, session_id)
        
        # Update session with comparison data if session exists
        if session_id:
            session_manager.update_session(session_id, {
                'last_comparison': comparison,
                'last_vehicles': vehicles_data
            })
        
        # Parse the comparison response
        try:
            comparison_json = json.loads(comparison)
            return {
                "comparison": comparison_json,
                "session_id": session_id
            }
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to parse comparison response"
            )
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@app.post("/clear_session")
async def clear_session(request: Request):
    """
    Clear a session's context.
    """
    try:
        data = await request.json()
        session_id = data.get('session_id')
        
        if not session_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No session ID provided"
            )
            
        if session_manager.clear_session(session_id):
            return {"message": "Session cleared successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@app.post("/submit-inquiry")
async def submit_inquiry_endpoint(request: Request):
    try:
        data = await request.json()
        name = data.get("name", "")
        phone = data.get("phone", "")
        email = data.get("email", "")
        inquiry_type = data.get("inquiry_type", "")
        details = data.get("details", "")

        if not all([name, phone, email, inquiry_type, details]):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="All fields are required"
            )

        success, error_message = submit_inquiry(name, phone, email, inquiry_type, details)
        
        if success:
            return {
                "message": "Got it! I've passed your message along. A DealerBot team member will be in touch shortly via phone or email to assist you further"
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=error_message
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@app.post("/store_chat")
async def store_chat_api(request: Request):
    """API endpoint to store chat messages in the database."""
    try:
        chat_data = await request.json()
        
        if not isinstance(chat_data, list):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid input format, expected a list of messages"
            )
        
        store_chat(chat_data)
        return {"message": "Chat stored successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@app.post("/feedback")
async def handle_feedback(request: Request):
    """
    Handle user feedback submission.
    Expects a JSON object with session_id and feedback type.
    """
    try:
        data = await request.json()
        session_id = data.get('session_id')
        feedback_type = data.get('feedback')
        message = data.get('message')  # Optional message

        if not session_id or not feedback_type:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Session ID and feedback type are required"
            )

        if feedback_type not in ['positive', 'negative']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid feedback type"
            )

        # Store the feedback
        success = feedback_manager.store_feedback(session_id, feedback_type, message)
        
        if success:
            return {
                "message": "Thank you for your feedback!",
                "status": "success"
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to store feedback"
            )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@app.get("/all_vehicles")
async def get_all_vehicles():
    """
    Get all vehicles from the scraped data
    """
    try:
        # Load vehicle data directly from the JSON file
        with open(VEHICLE_DATA, "r", encoding='utf-8') as file:
            vehicle_data = json.load(file)
        
        # Flatten the data structure
        all_vehicles = []
        for category in vehicle_data.values():
            if isinstance(category, dict):
                all_vehicles.extend(category.values())
        
        return {
            "success": True,
            "count": len(all_vehicles),
            "vehicles": all_vehicles
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load vehicle data: {str(e)}"
        )

if __name__ == "__main__":
    if PRODUCTION_MODE : 
        app.run(ssl_context=("ssl/cert.pem", "ssl/key.pem"), host="0.0.0.0", port=5002)
    else :
        app.run(host="0.0.0.0", port=5002)
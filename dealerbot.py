# -*- coding: utf-8 -*-
from crewai import Agent, Crew, Task # type: ignore
from langchain_openai import ChatOpenAI # type: ignore
from openai import OpenAI # type: ignore
from dotenv import load_dotenv # type: ignore
import ast
import json
import os
import re
from session_manager import session_manager
from datetime import datetime
import unicodedata
load_dotenv() 

# Load FAQ and Booking Data
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
VEHICLE_DATA = os.path.join(SCRIPT_DIR, "vehicle_data.json")

# Set OpenAI API key
openai_api_key = os.environ["OPENAI_API_KEY"]


# Agents Setup
dealerbot_controller_agent = Agent(
    name="Dealerbot Crew Coordinator Agent",
    role="Accepts user query and figures out which agent to offload it to for the appropriate response.",
    goal="Output the requested word after performing analysis on which agent to offload task to.",
    backstory="""The main orchestrator in Delaerbot's agentic crew. You are aware of the conversation context and 
    can use previous interactions to better understand the current query. You consider:
    - The last query and response
    - Any vehicles that were recently discussed
    - The conversation history
    - The user's apparent interests and needs""",
    llm=ChatOpenAI(model="gpt-4")
)

data_request_analyzer_agent = Agent(
    name="Data Request Analyzer Agent",
    role="Determines if a user query requires raw vehicle data or a formatted response",
    goal="Quickly analyze if the user needs raw vehicle data or a conversational response",
    backstory="You are a simple analyzer that determines if a user needs raw vehicle data for display purposes or a conversational response. You focus on identifying specific phrases and patterns that indicate a need for detailed data.",
    llm=ChatOpenAI(model="gpt-3.5-turbo")  # Using a lighter model for this simple task
)

response_formatter_agent = Agent(
    name="Response Formatter Agent",
    role="Formats raw data into natural, conversational responses",
    goal="Transform raw data and responses into helpful, conversational answers that directly address the user's query",
    backstory="""You are an expert at taking raw data and transforming it into natural, helpful responses. You:
    - Understand the context of the user's question
    - Format data in a way that directly answers their query
    - Add appropriate follow-up questions or suggestions
    - Maintain a friendly, professional tone
    - Ensure responses are clear and easy to understand
    - Add relevant context when needed
    - Handle both positive and negative responses appropriately""",
    llm=ChatOpenAI(model="gpt-4")
)

ford_expert_agent = Agent(
    name="Ford Expert Agent",
    role="Expert on all things Ford, specializing in vehicle recommendations and general Ford knowledge",
    goal="Provide accurate, helpful information about Ford vehicles and answer general Ford-related questions",
    backstory="""You are a Ford product specialist with extensive knowledge of:
    - Ford's entire vehicle lineup
    - Vehicle features and capabilities
    - Target demographics for each model
    - Ford's history and innovations
    - Vehicle comparisons and recommendations
    - Ford's technology and safety features
    - Ford's electric and hybrid offerings
    - Ford's performance vehicles
    - Ford's commercial vehicles
    
    You can provide detailed recommendations based on specific needs and preferences,
    explain Ford's unique features and technologies, and answer general questions about Ford vehicles.""",
    llm=ChatOpenAI(model="gpt-4")
)

user_interest_agent = Agent(
    name="Dealerbot User Interest Agent",
    role="Figures out what matters to user from the provided query.",
    goal="Output the requested word after performing analysis on which agent to offload task to.",
    backstory="Figures out what quality matters to the user.",
    llm=ChatOpenAI(model="gpt-4")
)

provided_identifier_agent = Agent(
    name="Dealerbot Identifier extractor Agent",
    role="Accepts user query and identifies what the identifier provided by the user is.",
    goal="Output the requested information after performing analysis on which agent to offload task to.",
    backstory="Extracts the main identifier and it's value in what the user wants.",
    llm=ChatOpenAI(model="gpt-4")
)

vehicle_comparison_agent = Agent(
    name="Vehicle Comparison Agent",
    role="Compares multiple vehicles and highlights their differences",
    goal="Provide a clear, concise comparison of multiple vehicles, focusing on their differences",
    backstory="""You are an expert at comparing vehicles and highlighting their key differences. You:
    - Focus on the most important differences that would matter to a buyer
    - Organize comparisons in a logical way (price, performance, features, etc.)
    - Highlight unique features of each vehicle
    - Provide clear, easy-to-understand comparisons
    - Consider different buyer priorities (family, performance, efficiency, etc.)
    - Format the comparison in a structured way
    - Include both technical specifications and practical differences""",
    llm=ChatOpenAI(model="gpt-4")
)

all_vehicles_query_agent = Agent(
    name="All Vehicles Query Detector",
    role="Determines if the user is requesting to see all vehicles for a given make, model, type, or the entire inventory.",
    goal="Return 'true' if the user wants to see all vehicles (not just a summary or a single vehicle), otherwise 'false'.",
    backstory="You are a lightweight classifier that, given a user query and context, determines if the user is explicitly asking to see all vehicles for a category (make, model, type) or making a general inquiry about them. You do not rely on hardcoded keywords, but on intent.",
    llm=ChatOpenAI(model="gpt-3.5-turbo")
)

customer_relations_agent = Agent(
    name="Customer Relations Agent",
    role="Friendly conversationalist and customer relations specialist",
    goal="Engage users in friendly conversation, handle greetings, small talk, and gently steer the conversation back to Ford vehicles when appropriate.",
    backstory="You are the friendly face of DealerBot. You handle general conversation, greetings, and off-topic queries with warmth and professionalism. If the user is off-topic, you gently and politely try to bring the conversation back to Ford vehicles, but never pushy.",
    llm=ChatOpenAI(model="gpt-4")
)


# ---- Executor Functions ----
def handle_ford_expert_query(user_query, history_context):
    """Handle general Ford-related queries using the Ford expert agent."""
    expert_task = Task(
        description=(
            f"Answer the following Ford-related question: '{user_query}'\n"
            f"{history_context}\n"
            "Provide a detailed, helpful response that:\n"
            "1. Directly addresses the user's question\n"
            "2. Includes specific Ford models and features when relevant\n"
            "3. Explains why certain vehicles might be suitable\n"
            "4. Mentions any unique Ford technologies or features\n"
            "5. Is conversational but professional\n"
            "6. Focuses only on Ford vehicles and technologies\n"
            "7. Provides specific model names and trim levels when making recommendations\n"
            "8. Includes relevant safety features and capabilities\n"
            "9. Considers different needs (family, performance, efficiency, etc.)\n"
            "10. Stays within Ford's current lineup and technologies"
        ),
        agent=ford_expert_agent,
        expected_output="A detailed, helpful response about Ford vehicles that directly answers the user's question."
    )

    expert_crew = Crew(agents=[ford_expert_agent], tasks=[expert_task])
    return expert_crew.kickoff().raw.strip()

def return_vehicle_data(inquiry):
    # Load vehicle data from JSON file
    with open(VEHICLE_DATA, "r") as file:
        vehicle_data = json.load(file)

    # Collect all vehicles from all categories
    all_vehicles = []
    for category in vehicle_data.values():
        all_vehicles.extend(vehicle.copy() for vehicle in category.values())

    # Start with all vehicles and apply each filter sequentially
    filtered_vehicles = all_vehicles
    for key, value in inquiry.items():
        if value is None or value == "Unknown":
            continue
        inquiry_val = str(value).strip().lower()
        # Handle nested keys (e.g., parsed_name[make])
        if '[' in key and ']' in key:
            outer_key, inner_key = key.split('[')
            inner_key = inner_key.rstrip(']')
            debug_pairs = []
            for vehicle in filtered_vehicles:
                if isinstance(vehicle, dict) and outer_key in vehicle and isinstance(vehicle[outer_key], dict) and inner_key in vehicle[outer_key]:
                    data_val = str(vehicle[outer_key][inner_key]).strip().lower()
                    debug_pairs.append((inquiry_val, data_val, vehicle.get('vehicle_name', vehicle.get('vin', 'unknown'))))
            filtered_vehicles = [
                vehicle for vehicle in filtered_vehicles
                if isinstance(vehicle, dict)
                and outer_key in vehicle
                and isinstance(vehicle[outer_key], dict)
                and inner_key in vehicle[outer_key]
                and inquiry_val in str(vehicle[outer_key][inner_key]).strip().lower()
            ]
        else:
            debug_pairs = []
            for vehicle in filtered_vehicles:
                if isinstance(vehicle, dict) and key in vehicle:
                    data_val = str(vehicle[key]).strip().lower()
                    debug_pairs.append((inquiry_val, data_val, vehicle.get('vehicle_name', vehicle.get('vin', 'unknown'))))
            filtered_vehicles = [
                vehicle for vehicle in filtered_vehicles
                if isinstance(vehicle, dict)
                and key in vehicle
                and inquiry_val in str(vehicle[key]).strip().lower()
            ]
    return filtered_vehicles if filtered_vehicles else "Not in stock"

def analyze_vehicle_query(user_query):
    """Analyze a vehicle-specific query to determine interest and search parameters."""
    interest_task = Task(
        description=(
            f"Analyze the following user query: '{user_query}' and determine what the user's main interest is. "
            "Output the exact interest the user wants."
            "Your response must be concise and direct with a simple one word response, your options are : "
            "parsed_name[year], parsed_name[make], parsed_name[model], parsed_name[trim], parsed_name[vehicle_type], "
            "price, annual_mileage, specifications[horsepower], specifications[epa_range], specifications[torque], "
            "specifications[exterior_color], specifications[interior_color], specifications[wheel_type], specifications[drive], "
            "features[exterior], features[interior], features[functional], warranty, vin."
        ),
        agent=user_interest_agent,
        expected_output="A one word answer matching one of the specified options.",
    )
    inquiry_task = Task(
        description=(
            f"Analyze the following user query: '{user_query}' and determine what the user's main search parameter(s) is/are. "
            "Output the exact search parameter(s) the user wants. "
            "Your response MUST be a python dictionary type output with the identifier(s) and the corresponding values from the user query. "
            "Your identifier options are:\n"
            "- parsed_name[year]\n"
            "- parsed_name[make]\n"
            "- parsed_name[model]\n"
            "- parsed_name[trim]\n"
            "- parsed_name[vehicle_type]\n"
            "- price\n"
            "- annual_mileage\n"
            "- specifications[horsepower]\n"
            "- specifications[epa_range]\n"
            "- specifications[torque]\n"
            "- specifications[exterior_color]\n"
            "- specifications[interior_color]\n"
            "- specifications[wheel_type]\n"
            "- specifications[drive]\n"
            "- features[exterior]\n"
            "- features[interior]\n"
            "- features[functional]\n"
            "- warranty\n"
            "- vin\n\n"
            "If there is an identifier that is not in the list, ignore it. "
            "If there is one that is in the list, but the value is not defined by the user, assign the value of 'Unknown' to it. "
            "\n"
            "IMPORTANT: Always extract and assign as many relevant identifiers as possible from the user query. If the query contains any combination of year, make, model, trim, or other identifiers, split and assign each to the correct key. Use the known values from the inventory when possible. This applies to all combinations, not just model and trim.\n"
            "\nExamples:\n"
            "- 'Do you have any 2024 Ford Escape vehicles in stock?' -> {'parsed_name[year]': '2024', 'parsed_name[make]': 'Ford', 'parsed_name[model]': 'Escape'}\n"
            "- 'Show me all 2025 Bronco Black Diamond SUVs' -> {'parsed_name[year]': '2025', 'parsed_name[model]': 'Bronco', 'parsed_name[trim]': 'Black Diamond', 'parsed_name[vehicle_type]': 'SUV'}\n"
            "- 'Are there any 2025 ST-Line trims available?' -> {'parsed_name[year]': '2025', 'parsed_name[trim]': 'ST-Line'}\n"
            "- 'What is the horsepower of the 2024 Bronco?' -> {'parsed_name[year]': '2024', 'parsed_name[model]': 'Bronco', 'specifications[horsepower]': 'Unknown'}\n"
            "- 'Do you have any Ford vehicles?' -> {'parsed_name[make]': 'Ford'}\n"
            "- 'Tell me about the Escape ST-Line' -> {'parsed_name[model]': 'Escape', 'parsed_name[trim]': 'ST-Line'}\n"
        ),
        agent=provided_identifier_agent,
        expected_output="Only a STRICT python dictionary containing whatever the parameters the user wants to make the search by, where the key(s) must be from the specified list."
    )

    interest_crew = Crew(agents=[user_interest_agent], tasks=[interest_task])
    interest_decision = interest_crew.kickoff().raw.strip()
    inquiry_crew = Crew(agents=[provided_identifier_agent], tasks=[inquiry_task])
    inquiry_decision = inquiry_crew.kickoff().raw.strip()

    interest = interest_decision
    print(f"Interest: {interest}")
    print("" + "-" * 50)
    try:
        inquiry = ast.literal_eval(inquiry_decision)
        print(f"Inquiry Decision: {inquiry_decision}")
        print("" + "-" * 50)
    except Exception:
        inquiry = {}  # fallback if parsing fails

    print(f"Inquiry: {inquiry}")
    print("" + "-" * 50)
    return interest, inquiry

def get_vehicle_data(user_query):
    """Get specific vehicle data based on the query."""
    interest, inquiry = analyze_vehicle_query(user_query)
    vehicles = return_vehicle_data(inquiry)
    def get_nested_value(vehicle, interest):
        if '[' in interest and ']' in interest:
            outer, inner = interest.split('[')
            inner = inner.rstrip(']')
            return vehicle.get(outer, {}).get(inner, "Unknown")
        else:
            return vehicle.get(interest, "Unknown")
    # Only extract fields that are in the inquiry and not 'Unknown', and are not just search filters
    requested_fields = [k for k, v in inquiry.items() if v == 'Unknown']
    # If the agent didn't mark any as 'Unknown', fallback to the main interest
    if not requested_fields:
        requested_fields = [interest]
    if vehicles != "Not in stock":
        if len(requested_fields) == 1:
            return [get_nested_value(vehicle, requested_fields[0].strip().lower()) for vehicle in vehicles]
        results = []
        for vehicle in vehicles:
            result = {}
            for field in requested_fields:
                result[field] = get_nested_value(vehicle, field)
            results.append(result)
        return results
    else:
        return "Not in stock"

def format_response(user_query, raw_response):
    print(f"Passing to formatter agent: user_query='{user_query}', raw_response='{raw_response}'")
    format_task = Task(
        description=(
            f"Format the following response into a natural, conversational answer.\n\n"
            f"User's query: '{user_query}'\n"
            f"Raw response: {raw_response}\n\n"
            "Your response should:\n"
            "1. Directly answer the user's question\n"
            "2. Be conversational and friendly\n"
            "3. Include relevant details from the raw response\n"
            "4. Add appropriate follow-up questions or suggestions\n"
            "5. Handle both positive and negative responses naturally\n"
            "6. Maintain a professional but approachable tone\n"
            "7. Format lists and data in an easy-to-read way\n"
            "8. Add context when needed to make the response more helpful\n"
            "9. NEVER suggest visiting any external website or contacting another dealership.\n"
            "10. If the information is missing or unknown, use this fallback: 'I'm sorry, I don't have that specific information right now. Would you like me to pass along your inquiry to a team member and have them get in touch with you?'\nIMPORTANT; ALWAYS KEEP RESPONSES SHORT AND TO THE POINT, assume the user is impatient and you need to close the deal as soon as possible."
        ),
        agent=response_formatter_agent,
        expected_output="A natural, conversational response that directly answers the user's query while incorporating the raw data in a helpful way."
    )

    format_crew = Crew(agents=[response_formatter_agent], tasks=[format_task])
    return format_crew.kickoff().raw.strip()

def analyze_data_request(user_query):
    """Determine if the user needs raw vehicle data or a formatted response."""
    analyzer_task = Task(
        description=(
            f"Analyze the following user query: '{user_query}'\n\n"
            "Determine if this is a request for raw vehicle data that should be displayed in detail, "
            "or if it's a general inquiry that should get a conversational response.\n\n"
            "Return exactly one of these two responses:\n"
            "1. 'raw_data' - If the user is asking to see detailed vehicle information\n"
            "2. 'formatted' - If the user is making a general inquiry\n\n"
            "Consider these examples:\n"
            "- 'Show me the details of the 2024 Escape' -> 'raw_data'\n"
            "- 'What's the price of the 2024 Escape?' -> 'formatted'\n"
            "- 'Do you have any Mustangs?' -> 'formatted'\n"
            "- 'Show me the specs for the F-150' -> 'raw_data'\n"
            "- 'Tell me about your inventory' -> 'formatted'"
        ),
        agent=data_request_analyzer_agent,
        expected_output="Either 'raw_data' or 'formatted'"
    )

    analyzer_crew = Crew(agents=[data_request_analyzer_agent], tasks=[analyzer_task])
    return analyzer_crew.kickoff().raw.strip()

def is_all_vehicles_query_agent(user_query, history_context=""):
    task = Task(
        description=(
            f"Given the following user query and context, determine if the user is requesting to see all vehicles for a make, model, type, year, or trim.\n"
            f"User query: '{user_query}'\n"
            f"Context: {history_context}\n"
            "Return 'true' if the user wants to see all vehicles matching a specific make, model, type, year, or trim (not just a summary or a single vehicle), otherwise return 'false'.\n"
            "If the user says 'show me all vehicles' with NO filter, return 'false' and do NOT return the entire inventory.\n"
            "If the user requests to see all vehicles and context shows that the user wants a specific vwhicle, return true.\n"
            "Examples of 'all' queries: 'Show me all Escape vehicles', 'Show me every Bronco', 'Show all 2024 Mustangs', 'Show me the Escape vehicles', 'What Escape vehicles do you have?', etc.\n"
            "Examples of NOT 'all' queries: 'Show me all vehicles' (no filter), 'Do you have any Escapes?', 'Is there a Bronco in stock?', 'Tell me about the F-150', 'What is the price of the Mustang?', etc."
        ),
        agent=all_vehicles_query_agent,
        expected_output="'true' or 'false'"
    )
    crew = Crew(agents=[all_vehicles_query_agent], tasks=[task])
    result = crew.kickoff().raw.strip().lower()
    return result == 'true'

def handle_customer_relations_query(user_query, history_context):
    """Handle general conversation and customer relations queries."""
    relations_task = Task(
        description=(
            f"Engage in a friendly, conversational way with the user.\n"
            f"User's message: '{user_query}'\n"
            f"{history_context}\n"
            "If the conversation is off-topic, gently and politely steer it back to Ford vehicles, but do not be pushy.\n"
            "Always be warm, professional, and helpful."
        ),
        agent=customer_relations_agent,
        expected_output="A friendly, conversational response that gently steers the user back to Ford vehicles if needed."
    )
    relations_crew = Crew(agents=[customer_relations_agent], tasks=[relations_task])
    return relations_crew.kickoff().raw.strip()

def query_dealerbot_agent(user_query, session_id=None):
    """Main entry point for the dealerbot system. Routes queries to appropriate handlers."""
    # Special handling for initialize query
    if user_query.lower() == "initialize":
        return "Session initialized"

    # Get session context if available
    session_context = None
    conversation_history = []
    if session_id:
        session = session_manager.get_session(session_id)
        if session:
            session_context = session['context']
            conversation_history = session_context.get('conversation_history', [])

    # Format conversation history for context, but limit to last 3 interactions
    history_context = ""
    if conversation_history:
        history_context = "\nLast few interactions:\n"
        for msg in conversation_history[-3:]:
            history_context += f"User: {msg['query']}\n"
            response_summary = str(msg['response'])
            if len(response_summary) > 200:
                response_summary = response_summary[:200] + "..."
            history_context += f"Assistant: {response_summary}\n"

    # --- Handle 'all vehicles' queries ---
    if is_all_vehicles_query_agent(user_query, history_context):
        # Extract filters from the query
        _, inquiry = analyze_vehicle_query(user_query)
        filters = [k for k in inquiry.keys() if k in [
            'parsed_name[make]', 'parsed_name[model]', 'parsed_name[vehicle_type]', 'parsed_name[year]', 'parsed_name[trim]'] and inquiry[k] != 'Unknown']
        if not filters:
            return {"type": "info", "message": "Please specify a make, model, type, year, or trim to see all matching vehicles. For example, 'Show me all Escape vehicles'.", "data": None}
        # Return all vehicles matching the filter as raw_data
        vehicles = return_vehicle_data(inquiry)
        return {"type": "raw_data", "data": vehicles}

    controller_task = Task(
        description=(
            f"Analyze this query: '{user_query}'\n"
            f"{history_context}\n"
            "Choose one: 'Specific Vehicle', 'Inventory Search', 'Ford Expert', 'Customer Relations', 'Follow-up', or 'Show Form'\n\n"
            "Guidelines:\n"
            "- Specific Vehicle: Questions about vehicle properties (e.g., specs, features, price, color, trim, VIN, etc.)\n"
            "- Inventory Search: Checking stock availability\n"
            "- Ford Expert: General Ford questions, recommendations, suitability, or opinion-based queries (e.g., 'Is X good for Y?', 'Would you recommend...?', 'Is this a good fit for...?')\n"
            "- Customer Relations: Greetings, small talk, off-topic conversation, or general chit-chat (e.g., 'Hi, how are you?', 'What's the weather?', 'Tell me a joke', etc.). If the user's query is not about Ford vehicles or is just a greeting, use this.\n"
            "- Follow-up: Responses to previous info (e.g., 'show me', 'yes')\n"
            "- Show Form: Test drive/quote/contact requests\n\n"
            "IMPORTANT: If the user asks whether a vehicle is suitable for a particular lifestyle, family, pets, or requests a recommendation or opinion, route to 'Ford Expert', even if a specific model or trim is mentioned., but if the user is just making small talk, greeting, or is off-topic, route to 'Customer Relations'.\n"
            "Examples:\n"
            "- 'Hi, how are you doing today?' => Customer Relations\n"
            "- 'What's your favorite color?' => Customer Relations\n"
            "- 'Tell me a joke' => Customer Relations\n"
            "- 'Do you have any Escape vehicles in stock?' => Inventory Search\n"
            "- 'What is the horsepower of the Escape ST-Line?' => Specific Vehicle\n"
            "- 'Would you recommend the Bronco Sport for camping?' => Ford Expert\n"
            "- 'Do you think the Escape ST-Line is good for a mother of 3 and 2 dogs like myself?' => Ford Expert\n"
            "- 'Would you recommend the Bronco Sport for camping?' => Ford Expert\n"
            "- 'Is the Mustang a good car for winter driving?' => Ford Expert\n"
            "- 'What is the horsepower of the Escape ST-Line?' => Specific Vehicle\n"
            "- 'Would you recommend the Bronco Sport for camping?' => Ford Expert\n"
        ),
        agent=dealerbot_controller_agent,
        expected_output="One of: 'Specific Vehicle', 'Inventory Search', 'Ford Expert', 'Customer Relations', 'Follow-up', or 'Show Form'"
    )

    controller_crew = Crew(agents=[dealerbot_controller_agent], tasks=[controller_task])
    routing_decision = controller_crew.kickoff().raw.strip()

    print(f"[Dealerbot Routing Decision] Query: '{user_query}' => Routing: '{routing_decision}'")
    
    response = None
    
    if routing_decision == "Show Form":
        response = "Show Form"
    
    elif routing_decision == "Follow-up" and session_context:
        # Handle follow-up queries using session context
        if session_context.get('last_vehicles'):
            response = session_context['last_vehicles']
        elif session_context.get('last_response'):
            response = format_response(user_query, session_context['last_response'])
        else:
            response = format_response(user_query, "I'm not sure what you're referring to. Could you please rephrase your question?")
    
    elif routing_decision == "Specific Vehicle":
        vehicle_data = get_vehicle_data(user_query)
        if vehicle_data != "Not in stock":
            response = format_response(user_query, vehicle_data)
        else:
            response = format_response(user_query, "Not in stock")
    
    elif routing_decision == "Inventory Search":
        _, inquiry = analyze_vehicle_query(user_query)
        vehicles = return_vehicle_data(inquiry)
        # Only return formatted summary, never vehicle data
        # Create a minimal context for the agent
        vehicle_info = {
            'available': vehicles != "Not in stock",
            'count': len(vehicles) if vehicles != "Not in stock" else 0,
            'model': inquiry.get('parsed_name[model]', 'vehicle')
        }
        inventory_task = Task(
            description=(
                f"Create a natural response about vehicle availability.\n"
                f"Query: '{user_query}'\n"
                f"Available: {vehicle_info['available']}\n"
                f"Count: {vehicle_info['count']}\n"
                f"Model: {vehicle_info['model']}\n\n"
                "Be conversational and offer to show details or provide specific information."
            ),
            agent=ford_expert_agent,
            expected_output="A natural response about vehicle availability"
        )
        expert_crew = Crew(agents=[ford_expert_agent], tasks=[inventory_task])
        response = expert_crew.kickoff().raw.strip()
        if session_id:
            context_updates = {
                'last_query': user_query,
                'last_response': response,
                'last_vehicles': vehicles,
                'conversation_history': conversation_history + [{
                    'query': user_query,
                    'response': response,
                    'timestamp': datetime.now().isoformat()
                }]
            }
            session_manager.update_session(session_id, context_updates)
        return {"type": "formatted", "message": format_response(user_query, response), "data": None}
    
    elif routing_decision == "Ford Expert":
        expert_response = handle_ford_expert_query(user_query, history_context)
        response = format_response(user_query, expert_response)

    elif routing_decision == "Customer Relations":
        relations_response = handle_customer_relations_query(user_query, history_context)
        response = format_response(user_query, relations_response)

    # Update session with the current query, response, and any additional context
    if session_id:
        context_updates = {
            'last_query': user_query,
            'last_response': response,
            'conversation_history': conversation_history + [{
                'query': user_query,
                'response': response,
                'timestamp': datetime.now().isoformat()
            }]
        }
        
        # Add vehicles to context if this was an inventory search
        if routing_decision == "Inventory Search" and vehicles != "Not in stock":
            context_updates['last_vehicles'] = vehicles
            
        session_manager.update_session(session_id, context_updates)

    return response

def compare_vehicles(vehicles_data, session_id=None):
    """Compare multiple vehicles and highlight their differences."""
    # Get session context for user preferences if available
    user_context = None
    if session_id:
        session = session_manager.get_session(session_id)
        if session:
            user_context = session['context']

    comparison_task = Task(
        description=(
            f"Compare these vehicles considering the user's context:\n"
            f"User context: {json.dumps(user_context) if user_context else 'No previous context'}\n"
            f"Vehicles to compare: {json.dumps(vehicles_data, indent=2)}\n\n"
            "Create a practical comparison focusing on:\n"
            "1. Value Proposition - Price vs Features analysis\n"
            "2. Practical Use Cases - Which vehicle suits which lifestyle/needs\n"
            "3. Key Differentiators - Most important differences that affect daily use\n"
            "4. Running Costs - Fuel efficiency, warranty implications\n"
            "5. Family Friendliness - Space, safety features, convenience\n"
            "6. Technology & Comfort - Key features that improve daily driving\n\n"
            "Format your response as a JSON object with these sections:\n"
            "- summary: Brief overview of the comparison\n"
            "- key_differences: Most important practical differences\n"
            "- best_for: Which vehicle is best for different use cases\n"
            "- value_analysis: Price vs features breakdown\n"
            "- practical_considerations: Daily use implications\n"
            "- recommendation: Personalized recommendation based on user context\n\n"
            "Focus on PRACTICAL differences that matter in real-world use."
        ),
        agent=vehicle_comparison_agent,
        expected_output="A practical, user-focused comparison in JSON format."
    )

    comparison_crew = Crew(agents=[vehicle_comparison_agent], tasks=[comparison_task])
    return comparison_crew.kickoff().raw.strip()

# Example usage
# print(query_dealerbot_agent("Which Ford SUV is best for a mother of three?"))




# NOTE : Can use kickoff_for_each(input) to run the agent for each input in a list
# ---- Example Usage ----
# datasets = [
#   { "ages": [25, 30, 35, 40, 45] },
#   { "ages": [20, 25, 30, 35, 40] },
#   { "ages": [30, 35, 40, 45, 50] }
# ]

# # Execute the crew
# result = analysis_crew.kickoff_for_each(inputs=datasets)
from crewai import Agent, Task, Crew # type: ignore
from langchain_openai import ChatOpenAI # type: ignore
from typing import Dict, List, Any
import json
import os
from dotenv import load_dotenv

load_dotenv()

openai_api_key = os.environ["OPENAI_API_KEY"]

# Initialize the LLM
llm = ChatOpenAI(model="gpt-4")

# Create the data processing agent
data_processor_agent = Agent(
    name="Vehicle Data Processor",
    role="Process and structure vehicle data, especially vehicle names and types",
    goal="Extract and structure vehicle information, including parsing vehicle names into year, make, model, trim, and determining vehicle type",
    backstory="""You are an expert at processing and structuring vehicle data, with particular expertise in parsing vehicle names and determining vehicle types.
    You can accurately extract year, make, model, and trim information from vehicle names and determine the vehicle type (e.g., SUV, Truck, Sedan, etc.) based on the model name and features.
    You have extensive knowledge of Ford's vehicle lineup and can accurately categorize vehicles based on their characteristics.""",
    llm=llm
)

def parse_vehicle_name(vehicle_name: str) -> Dict[str, str]:
    """Parse a vehicle name into its components using the AI agent."""
    parse_task = Task(
        description=f"""Parse the following vehicle name into its components and determine the vehicle type:
        Vehicle Name: {vehicle_name}
        
        Extract the following components:
        - year (4-digit number)
        - make (manufacturer name, e.g., Ford)
        - model (base model name, e.g., Escape)
        - trim (trim level or special edition name, if any)
        - vehicle_type (one of: SUV, Truck, Sedan, Van, Electric, Hybrid, Performance)
        
        Return the components in a JSON structure.
        Example format:
        {{
            "year": "2024",
            "make": "Ford",
            "model": "Escape",
            "trim": "SEL Hybrid",
            "vehicle_type": "SUV"
        }}
        
        Vehicle Type Guidelines:
        - SUV: Models like Escape, Explorer, Expedition, Bronco
        - Truck: Models like F-150, Ranger, Super Duty
        - Van: Models like Transit, E-Series
        - Electric: Models like Mustang Mach-E, F-150 Lightning
        - Hybrid: Models with hybrid powertrains
        - Performance: Models like Mustang
        - Sedan: Traditional car models
        
        If any component is not present, set it to an empty string.
        Note: If no make is detected, automatically set it to "Ford" since this is a Ford vehicle.
        """,
        agent=data_processor_agent,
        expected_output="A JSON object with year, make, model, trim, and vehicle_type fields"
    )

    # Create and run the crew for this specific task
    crew = Crew(
        agents=[data_processor_agent],
        tasks=[parse_task],
        verbose=False
    )

    # Get the parsed result
    result = crew.kickoff()
    
    try:
        # Parse the result into a dictionary
        if isinstance(result, str):
            if '```json' in result:
                json_str = result.split('```json')[1].split('```')[0]
                parsed_data = json.loads(json_str)
            else:
                parsed_data = json.loads(result)
        else:
            result_str = str(result)
            if '```json' in result_str:
                json_str = result_str.split('```json')[1].split('```')[0]
                parsed_data = json.loads(json_str)
            else:
                parsed_data = json.loads(result_str)
                
        # Ensure all required fields are present
        required_fields = ['year', 'make', 'model', 'trim', 'vehicle_type']
        for field in required_fields:
            if field not in parsed_data:
                parsed_data[field] = None
                
        # If make is empty or None, set it to Ford
        if not parsed_data['make']:
            parsed_data['make'] = "Ford"
                
        return parsed_data
    except Exception as e:
        print(f"Error parsing vehicle name '{vehicle_name}': {str(e)}")
        # Return a default structure if parsing fails
        return {
            "year": None,
            "make": "Ford",  # Default to Ford
            "model": None,
            "trim": None,
            "vehicle_type": None,
            "original_name": vehicle_name
        }

def process_vehicle_data(raw_data: Dict[str, Any]) -> Dict[str, Any]:
    """Process the raw vehicle data and parse vehicle names."""
    processed_data = {}
    
    for model_key, model_data in raw_data.items():
        processed_data[model_key] = {}
        for vin, vehicle_data in model_data.items():
            # Copy the original data
            processed_vehicle = vehicle_data.copy()
            
            # Parse the vehicle name if it exists
            if 'vehicle_name' in vehicle_data:
                name_components = parse_vehicle_name(vehicle_data['vehicle_name'])
                # Add the parsed components to the vehicle data
                processed_vehicle.update({
                    'parsed_name': name_components
                })
            
            processed_data[model_key][vin] = processed_vehicle
    
    return processed_data

def save_processed_data(data: Dict[str, Any], filename: str = 'processed_vehicle_data.json'):
    """Save the processed data to a JSON file."""
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)
    print(f"Processed data saved to {filename}")

def main():
    print("Starting vehicle data processing...")
    # Load the raw vehicle data
    try:
        with open('vehicle_data.json', 'r') as f:
            raw_data = json.load(f)
    except Exception as e:
        print(f"Error loading vehicle data: {str(e)}")
        return

    processed_data = process_vehicle_data(raw_data)
    
    if processed_data:
        save_processed_data(processed_data)
        print("Data processing completed successfully!")
    else:
        print("Data processing failed!")

if __name__ == "__main__":
    main() 
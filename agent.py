from google.adk.agents.llm_agent import Agent
from typing import Optional, Dict, Any
import requests
from datetime import datetime
import re
import wikipedia 


SERPAPI_API_KEY = #insert your api key here

# Airport Mapping
AIRPORT_MAPPING = {
    "london heathrow": "LHR", 
    "london gatwick" : "LGW",
    "london luton"   : "LTN",   
    "barcelona": "BCN",     
    "chicago": "ORD",       
    "new york": "JFK",      
    "paris": "CDG",         
    "tokyo": "NRT",         
    "bucharest": "OTP",     
    "belgrade": "BEG",      
    "abu dhabi": "AUH",     
    "berlin": "BER",        
    "warsaw": "WAW",        
    "krakow": "KRK",        
    "astana": "NQZ",        
    "beijing": "PEK",
    "austin": "AUS",
    "ljubljana": "LJU",     
    "rome": "FCO",          
    "athens": "ATH",        
    "hong kong": "HKG",     
    "montreal": "YUL",      
    "sydney": "SYD",        
    "auckland": "AKL",       
    "marrakech": "RAK",     
    "doha": "DOH",           
    "cape town": "CPT",     
    "gdansk": "GDN",         
    "riga": "RIX",          
    "vilnius": "VNO",       
    "tallinn": "TLL",       
    "helsinki": "HEL",      
    "sibiu": "SBZ",         
    "vienna": "VIE", 
    "shanghai": "PVG",      
    "dubai": "DXB",         
    "singapore": "SIN",     
    "frankfurt": "FRA",     
    "madrid": "MAD",        
    "lisbon": "LIS",        
    "mexico city": "MEX",   
    "buenos aires": "EZE",  
    "rio de janeiro": "GIG", 
    "cairo": "CAI",
}
# ---------------------------------------

def _format_date_for_api(date_str: str) -> Optional[str]:
    """
    Attempts to parse a natural language date string into the 'YYYY-MM-DD' format.
    Returns None if parsing fails.
    """
    if not date_str:
        return None
    
    # 1. Simple cleanup: remove ordinal suffixes (like 'st', 'nd', 'rd', 'th')
    cleaned_date_str = re.sub(r'(\d)(st|nd|rd|th)', r'\1', date_str).strip()
    
    # 2. Try multiple common date formats - Use the most common English formats first.
    formats_to_try = [
        '%Y-%m-%d',         # e.g., 2025-10-12 
        '%d %B %Y',         # e.g., 12 October 2025
        '%d %b %Y',         # e.g., 12 Oct 2025
        '%B %d %Y',         # e.g., October 12 2025 
        '%B %d, %Y',        # e.g., October 12, 2025
        '%m/%d/%Y',         # e.g., 10/12/2025
        '%d/%m/%Y',         # e.g., 12/10/2025
    ]
    
    for fmt in formats_to_try:
        try:
            return datetime.strptime(cleaned_date_str, fmt).strftime('%Y-%m-%d')
        except ValueError:
            continue
            
    # If standard parsing fails, return a unique marker string instead of the original string
    return "PARSE_FAILURE_MARKER"

def _resolve_airport_code(location_name: str) -> str:
    """
    Checks if the location is an airport code or a known city,
    returning the appropriate code or the original string if unknown.
    """
    location_name_lower = location_name.strip().lower()
    
    # If it looks like an airport code (3 letters), return it as is
    if re.match(r'^[a-z]{3}$', location_name_lower):
        return location_name.upper()

    # If it's a known city, return the mapped code
    return AIRPORT_MAPPING.get(location_name_lower, location_name)


def get_flights(
    origin_name: Optional[str] = None,
    destination_name: Optional[str] = None,
    # Adding optional date arguments is helpful for a flight search tool
    departure_date: Optional[str] = None,
    return_date: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Searches Google Flights via SerpApi for flights.
    Requires at least 'origin_name' and 'destination_name' (airport codes preferred,
    but common city names like 'London' will be automatically mapped to a primary airport).
    Date strings will be automatically formatted to YYYY-MM-DD for the API.
    
    A good example of a get request is:
    https://serpapi.com/search.json?engine=google_flights&departure_id=PEK&arrival_id=AUS&outbound_date=2025-10-11&return_date=2025-10-17&currency=USD&hl=en
    """
    if not origin_name or not destination_name:
        return {"error": "Please provide both origin and destination airports or cities."}
    
    departure_id = _resolve_airport_code(origin_name)
    arrival_id = _resolve_airport_code(destination_name)

    if len(departure_id) > 5 or len(arrival_id) > 5:
        return {"error": f"Could not determine a valid airport code for one of the locations. Please ask the user to provide a 3-letter airport code (e.g., LHR, BCN)."}
    # ---------------------------
    
    # Date Formatting Fix
    outbound_date_formatted = _format_date_for_api(departure_date) if departure_date else None
    return_date_formatted = _format_date_for_api(return_date) if return_date else None
    
    if outbound_date_formatted == "PARSE_FAILURE_MARKER" or return_date_formatted == "PARSE_FAILURE_MARKER":
        return {"error": "Failed to convert one or more dates to the required YYYY-MM-DD format. Please ask the user to provide a simple date format (e.g., 'October 12, 2025')."}
    # ---------------------------

    # Constructing the query parameters
    params = {
        "engine": "google_flights",
        "api_key": SERPAPI_API_KEY,
        "hl": "en", 
        "gl": "us",
        "departure_id": departure_id, 
        "arrival_id": arrival_id,     
    }

    if outbound_date_formatted:
        params["outbound_date"] = outbound_date_formatted
    if return_date_formatted:
        params["return_date"] = return_date_formatted

    try:
        response = requests.get("https://serpapi.com/search.json", params=params)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        if response and response.status_code == 400:
             return {"error": f"Flight search failed. SerpAPI returned 400 Bad Request. Ensure the airport codes ({departure_id} to {arrival_id}) are valid and the dates are in the correct format."}
        return {"error": f"Flight search failed due to API connection error: {e}"}

def book_flight(flight_code: str) -> Dict[str, Any]:
    """
    If the client, likes a flight you can use this function to generate a direct booking URL.
    Generates a direct booking URL for a specific flight code after the user has selected a flight from the get_flights results.
    The flight code must be a carrier code followed by the flight number (e.g., 'BA-452').
    """
    if not flight_code:
        return {"error": "A flight code is required to generate the booking link."}
        
    airpaz_url = f"https://www.airpaz.com/en/flight/code/{flight_code}"
    
    # Returning both URL and instructions for the LLM to present to client
    return {
        "booking_url": airpaz_url,
        "instructions": "Please note that the user will need to select the dates and complete the booking process on the external site."
    }


def get_hotels(
    query: str, 
    check_in_date: Optional[str] = None, 
    check_out_date: Optional[str] = None,
    adults: Optional[int] = None,
    children: Optional[int] = None,
    ) -> Dict[str, Any]:
    """
    Searches Google Hotels via SerpApi for hotels. 
    The 'query' argument is required and should be a simple location string (e.g., 'Paris, France').
    The check-in/out dates are required but if the client has already given dates for their flights use the outbound flight as the check in date and the return flight as the checkout date. Date strings will be automatically formatted to YYYY-MM-DD.
    
    A good example of a get request with optional parameters is:
    https://serpapi.com/search.json?engine=google_hotels&q=Bali+Resorts&check_in_date=2025-10-11&check_out_date=2025-10-12&adults=2&currency=USD&gl=us&hl=en
    """
    if not query:
        return {"error": "A search query (location) is required to find hotels."}
    if not check_in_date or not check_out_date:
        return {"error": "Both check-in and check-out dates are required for a hotel search."}

    # --- Date Formatting Fix ---
    check_in_date_formatted = _format_date_for_api(check_in_date)
    check_out_date_formatted = _format_date_for_api(check_out_date)

    if check_in_date_formatted == "PARSE_FAILURE_MARKER" or check_out_date_formatted == "PARSE_FAILURE_MARKER":
        return {"error": "Failed to convert one or more dates to the required YYYY-MM-DD format. Please ask the user to provide a simple date format (e.g., 'October 12, 2025')."}
    # ---------------------------
    
    #Query Cleanup
    cleaned_query = query.strip()
        
    params = {
        "engine": "google_hotels",
        "api_key": SERPAPI_API_KEY,
        "q": cleaned_query,
        "hl": "en",
        "gl": "us",
        "check_in_date": check_in_date_formatted,
        "check_out_date": check_out_date_formatted,
    }

    if adults is not None:
        params["adults"] = adults
    
    if children is not None:
        params["children"] = children
    
    try:
        # Changed base URL to include .json to align with docstring example
        response = requests.get("https://serpapi.com/search.json", params=params)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        if response and response.status_code == 400:
             return {"error": f"Hotel search failed. SerpAPI returned 400 Bad Request. Ensure the location query is simple and valid and dates are YYYY-MM-DD."}
        return {"error": f"Hotel search failed due to API connection error: {e}"}

def destination_description(query: str) -> Dict[str, Any]:
  """
  Searches Wikipedia for the full content of a given destination's page. 
  The LLM agent can then use this content to answer specific questions (e.g., currency, cuisine).
  The function returns the full page content which the agent should incorporate into its response.
  """

  
  try:
    page = wikipedia.page(query, auto_suggest=True, redirect=True)
    return {"content": page.content} 
  except wikipedia.exceptions.PageError:
    return {"error": f"Could not find a Wikipedia page for '{query}'. Please try a different name."}
  except wikipedia.exceptions.DisambiguationError as e:
    suggestions = e.options
    if suggestions:
        try:
            page = wikipedia.page(suggestions[0], auto_suggest=True, redirect=True)
            return {"content": page.content}
        except:
            return {"error": f"Multiple matches found for '{query}' (e.g., {', '.join(suggestions[:5])}), but unable to resolve. Please try a more specific query."}
    return {"error": f"Multiple matches found for '{query}', but unable to resolve. Please try a more specific query."}
  except Exception as e:
    return {"error": f"An unexpected error occurred while fetching information: {e}"}


root_agent = Agent(
    model='gemini-2.5-flash',
    name='root_agent',
    description='A travel assistant to help find flights, hotels, and get destination information.',
    instruction='You are a friendly travel assistant. Today is October 12th 2025. You have access to tools to search for flights, hotels, and destination details, as well as the book_flight tool that gives the client a url to proceed with their booking. Before calling a tool, always gather the necessary information from the user (origin, destination, dates for flights; simple query for hotels/descriptions). Use your reasoning to convert user input (like city names and natural language dates) into the specific formats required by the functions. E.g. If the user says I would like to fly from London to Dubai, ask them London Heathrow, Luton, Stansted or Gatwick?. Respond to the client in natural language, summarizing the tool\'s dictionary output.',
    tools=[get_flights, get_hotels, destination_description, book_flight]
)

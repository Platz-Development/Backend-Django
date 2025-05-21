import requests
from decimal import Decimal, ROUND_HALF_UP



def get_currency_from_country(country_name):
    
    country_name = country_name.title()
    country_currency_map = {
    # Full names
    
    'Germany': 'EUR',
    'France': 'EUR',
    'Italy': 'EUR',
    'Spain': 'EUR',
    

}

    return country_currency_map.get(country_name, 'EUR')

def convert_currency(amount, from_currency, to_currency):
    api_key = '5fe91761dd0f51207eb11bb8'  # Replace with your API key
    url = f'https://api.exchangerate-api.com/v4/latest/{from_currency}'
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        exchange_rate = data['rates'][to_currency]
        converted_amount = amount * exchange_rate
        return Decimal(str(converted_amount)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)  # Round to 2 decimal places
    except Exception as e:
        print(f"Error converting currency: {e}")
        return None
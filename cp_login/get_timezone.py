import pytz

def get_timezone_by_country(country):
   
    normalized_input = country.strip().lower()
    
    country_map = {
        # Asia
        'india': 'Asia/Kolkata',
        'in': 'Asia/Kolkata',
        'ind': 'Asia/Kolkata',
        'indian': 'Asia/Kolkata',
        
        'china': 'Asia/Shanghai',
        'cn': 'Asia/Shanghai',
        'chn': 'Asia/Shanghai',
        
        'japan': 'Asia/Tokyo',
        'jp': 'Asia/Tokyo',
        'jpn': 'Asia/Tokyo',
        
        'singapore': 'Asia/Singapore',
        'sg': 'Asia/Singapore',
        'sgp': 'Asia/Singapore',
        
        'uae': 'Asia/Dubai',
        'united arab emirates': 'Asia/Dubai',
        'ae': 'Asia/Dubai',
        
        # Europe
        'uk': 'Europe/London',
        'united kingdom': 'Europe/London',
        'gb': 'Europe/London',
        'england': 'Europe/London', 
        
        'germany': 'Europe/Berlin',
        'de': 'Europe/Berlin',
        'deu': 'Europe/Berlin',
        
        'france': 'Europe/Paris',
        'fr': 'Europe/Paris',
        'fra': 'Europe/Paris',
        
        'spain': 'Europe/Madrid',
        'es': 'Europe/Madrid',
        'esp': 'Europe/Madrid',
        
        'italy': 'Europe/Rome',
        'it': 'Europe/Rome',
        'ita': 'Europe/Rome',
        
        # Americas
        'usa': 'America/New_York',
        'united states': 'America/New_York',
        'us': 'America/New_York',
        'america': 'America/New_York',
        
        'canada': 'America/Toronto',
        'ca': 'America/Toronto',
        'can': 'America/Toronto',
        
        'brazil': 'America/Sao_Paulo',
        'br': 'America/Sao_Paulo',
        'bra': 'America/Sao_Paulo',
        
        'mexico': 'America/Mexico_City',
        'mx': 'America/Mexico_City',
        'mex': 'America/Mexico_City',
        
        # Africa
        'south africa': 'Africa/Johannesburg',
        'za': 'Africa/Johannesburg',
        'zaf': 'Africa/Johannesburg',
        
        'egypt': 'Africa/Cairo',
        'eg': 'Africa/Cairo',
        'egy': 'Africa/Cairo',
        
        # Oceania
        'australia': 'Australia/Sydney',
        'au': 'Australia/Sydney',
        'aus': 'Australia/Sydney',
        
        'new zealand': 'Pacific/Auckland',
        'nz': 'Pacific/Auckland',
        'nzl': 'Pacific/Auckland',
    }
    
    return country_map.get(normalized_input)

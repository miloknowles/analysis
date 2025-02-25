import numpy as np
from datetime import datetime, timedelta

def calculate_solar_flux_df(df):
  """
  Calculate solar flux (W/m²) for a given latitude and hour.
  """
  df["solar_flux"] = df.apply(lambda row: calculate_solar_flux(row["latitude"], row["hour"], row["day_of_year"]), axis=1)
  return df

def calculate_solar_flux(latitude, hour, day_of_year=None):
  """
  Calculate solar flux (W/m²) for a given latitude and hour.
  
  Parameters:
  latitude : float
      Latitude in degrees (-90 to 90)
  hour : float
      Hour of the day (0-24)
  day_of_year : int, optional
      Day of the year (1-365). If None, uses current date.
      
  Returns:
  float : Solar flux in W/m²
  """
  if day_of_year is None:
      day_of_year = datetime.now().timetuple().tm_yday
  
  # Convert to radians
  lat_rad = np.radians(latitude)
  
  # Solar constant (W/m²)
  solar_constant = 1361
  
  # Calculate declination angle (δ)
  # Using Cooper's equation
  declination = 23.45 * np.sin(np.radians(360/365 * (day_of_year - 81)))
  declination_rad = np.radians(declination)
  
  # Calculate hour angle (ω)
  # Convert hour to solar hour angle (-180 to +180 degrees)
  hour_angle = (hour - 12) * 15
  hour_angle_rad = np.radians(hour_angle)
  
  # Calculate solar elevation angle (α)
  sin_elevation = (np.sin(lat_rad) * np.sin(declination_rad) + 
                  np.cos(lat_rad) * np.cos(declination_rad) * 
                  np.cos(hour_angle_rad))
  elevation_angle = np.arcsin(sin_elevation)
  
  # If sun is below horizon, return 0
  if sin_elevation <= 0:
      return 0
  
  # Calculate atmospheric mass number
  air_mass = 1 / sin_elevation
  
  # Simple atmospheric transmission model
  # Using Meinel's formula for atmospheric transmission
  transmission = 0.7 ** air_mass
  
  # Calculate actual solar flux considering Earth-Sun distance variation
  # Using Spencer's formula for radius vector
  B = 2 * np.pi * (day_of_year - 1) / 365
  radius_vector = (1.000110 + 0.034221 * np.cos(B) + 0.001280 * np.sin(B) +
                  0.000719 * np.cos(2*B) + 0.000077 * np.sin(2*B))
  
  # Calculate final solar flux
  flux = (solar_constant / (radius_vector ** 2)) * sin_elevation * transmission
  
  return max(0, flux)


def generate_daily_profile(latitude, day_of_year=None):
    """
    Generate solar flux profile for an entire day.
    
    Parameters:
    latitude : float
        Latitude in degrees (-90 to 90)
    day_of_year : int, optional
        Day of the year (1-365)
        
    Returns:
    tuple : (hours, flux_values)
    """
    hours = np.linspace(0, 24, 145)  # 10-minute resolution
    flux_values = [calculate_solar_flux(latitude, hour, day_of_year) 
                  for hour in hours]
    return hours, flux_values



# Example usage
if __name__ == "__main__":
    # Calculate solar flux for 45°N latitude at noon on summer solstice
    latitude = 0.0
    hour = 12
    day_of_year = 172  # June 21st
    
    flux = calculate_solar_flux(latitude, hour, day_of_year)
    print(f"Solar flux at {latitude}°N, hour {hour}, day {day_of_year}: {flux:.2f} W/m²")
    
    # Generate daily profile
    hours, flux_values = generate_daily_profile(latitude, day_of_year)
    print("\nDaily profile (selected hours):")
    for h, f in zip(hours[::6], flux_values[::6]):
        print(f"Hour {h:.1f}: {f:.2f} W/m²")
from typing import Dict, List
import numpy as np
from pydantic import BaseModel

# Constants
AIR_DENSITY = 1.225  # kg/m³
AIR_SPECIFIC_HEAT = 1005  # J/(kg·K)
JOULE_TO_WH = 1/3600  # conversion factor


class Params(BaseModel):
  u_value: float          # W/m²·K
  height: float          # m
  infiltration_rate: float  # air changes per hour
  thermal_mass: float    # J/m²·K
  glazing_transmittance: float  # fraction of solar radiation transmitted
  latitude: float        # degrees
  orientation: float     # degrees from south


def calculate_solar_radiation(
  hour: float,
  day_of_year: int,
  latitude: float,
  glazing_transmittance: float
) -> float:
  """Calculate solar radiation for a given hour and day.

  The return value represents the direct solar radiation hitting a
  horizontal surface inside the greenhouse after passing through.

  We account for:
  - The atmospheric attenuation of the sun's rays.
  - The greenhouse glazing/covering transmission losses.
  
  Args:
    hour: float - The hour of the day (0-23)
    day_of_year: int - The day of the year (1-365)
    latitude: float - The latitude of the greenhouse
    glazing_transmittance: float - The transmittance of the glazing
    
  Returns:
    float - The solar radiation in W/m²
  """
  # Solar declination
  declination = 23.45 * np.sin(2 * np.pi * (day_of_year - 81) / 365)
  
  # Hour angle (15° per hour from solar noon)
  hour_angle = 15 * (hour - 12)
  
  # Solar altitude
  lat_rad = np.radians(latitude)
  decl_rad = np.radians(declination)
  hour_rad = np.radians(hour_angle)
  
  sin_altitude = (np.sin(lat_rad) * np.sin(decl_rad) + 
                  np.cos(lat_rad) * np.cos(decl_rad) * np.cos(hour_rad))
  solar_altitude = np.arcsin(np.clip(sin_altitude, -1, 1))

  # If the sun is below the horizon, return 0.
  if sin_altitude <= 0:
    return 0
  
  # Clear sky radiation
  air_mass = 1 / sin_altitude
  
  # Solar constant in W/m²
  solar_constant_w_m2 = 1080
  relative_attenuation_factor = np.exp(-0.1 * air_mass)
  dir_normal = solar_constant_w_m2 * relative_attenuation_factor
  
  # Account for glazing angle
  incident_angle = np.arccos(sin_altitude)
  transmittance = glazing_transmittance * (1 - 0.5 * incident_angle)
  
  return dir_normal * sin_altitude * transmittance


def calculate_conduction(u_value: float, delta_t: float) -> float:
  """Calculate conduction heat transfer.
  
  Args:
    u_value: float - The U-value of the greenhouse
    delta_t: float - The temperature difference between the inside and outside
    
  Returns:
    float - The conduction heat transfer in W/m²
  """
  return u_value * delta_t  # W/m²


def calculate_infiltration(height: float, infiltration_rate: float,  delta_t: float) -> float:
  """Calculate infiltration heat transfer.
  
  Args:
    height: float - The height of the greenhouse
    infiltration_rate: float - The infiltration rate of the greenhouse
    delta_t: float - The temperature difference between the inside and outside
    
  Returns:
    float - The infiltration heat transfer in W/m²
  """
  return (height * infiltration_rate * AIR_DENSITY *  AIR_SPECIFIC_HEAT * delta_t * JOULE_TO_WH)  # Wh/m²


def calculate_thermal_mass(thermal_mass: float, delta_t: float, 
                        hour: float) -> float:
  """Calculate thermal mass effect.
  
  Args:
    thermal_mass: float - The thermal mass of the greenhouse
    delta_t: float - The temperature difference between the inside and outside
    hour: float - The hour of the day (0-23)
    
  Returns:
    float - The thermal mass effect in W/m²
  """
  return (thermal_mass * delta_t/24 *  np.sin(2 * np.pi * hour / 24) * JOULE_TO_WH)  # Wh/m²


def calculate_hourly_energy(
  params: Params,
  outdoor_temp: float, 
  hour: float,
  day_of_year: int, 
  target_temp: float
) -> Dict[str, float]:
  """Calculate energy balance for one hour.
  
  Args:
    params: Params - The parameters of the greenhouse
    outdoor_temp: float - The outdoor temperature
    hour: float - The hour of the day (0-23)
    day_of_year: int - The day of the year (1-365)
    target_temp: float - The target temperature inside the greenhouse
    
  Returns:
    Dict[str, float] - The energy balance for the hour
  """
  delta_t = target_temp - outdoor_temp
  
  conduction_heat_transfer_w_m2 = calculate_conduction(params.u_value, delta_t)
  
  infiltration_heat_transfer_w_m2 = calculate_infiltration(
    params.height, 
    params.infiltration_rate, 
    delta_t
  )
  
  solar_radiation_w_m2 = calculate_solar_radiation(
    hour, 
    day_of_year, 
    params.latitude, 
    params.glazing_transmittance
  )
  
  thermal_mass_heat_transfer_w_m2 = calculate_thermal_mass(
    params.thermal_mass, 
    delta_t, 
    hour
  )
  
  # Net energy
  total_heat_transfer_w_m2 = (
    conduction_heat_transfer_w_m2 + 
    infiltration_heat_transfer_w_m2 - 
    solar_radiation_w_m2 - 
    thermal_mass_heat_transfer_w_m2
  )
  
  return {
    'conduction': conduction_heat_transfer_w_m2,
    'infiltration': infiltration_heat_transfer_w_m2,
    'solar': solar_radiation_w_m2,
    'thermal_mass': thermal_mass_heat_transfer_w_m2,
    'total': total_heat_transfer_w_m2,
    'type': 'heating' if total_heat_transfer_w_m2 > 0 else 'cooling'
  }


def simulate_day(params: Params, temperatures: List[float], target_temp: float, day_of_year: int) -> Dict:
  """Simulate entire day of greenhouse operation."""
  hourly_results = []

  for hour in range(24):
    results = calculate_hourly_energy(
      params, temperatures[hour], hour, day_of_year, target_temp
    )
    hourly_results.append(results)

  # Convert to kWh/m²
  daily_cooling_hours = list(filter(lambda x: x['type'] == 'cooling', hourly_results))
  daily_heating_hours = list(filter(lambda x: x['type'] == 'heating', hourly_results))

  total_cooling_load_kwh = sum(map(lambda x: x['total'], daily_cooling_hours)) / 1000
  total_heating_load_kwh = sum(map(lambda x: x['total'], daily_heating_hours)) / 1000
  
  return {
    'hourly_results': hourly_results,
    'daily_cooling_hours': daily_cooling_hours,
    'daily_heating_hours': daily_heating_hours,
    'total_cooling_load_kwh': abs(total_cooling_load_kwh),
    'total_heating_load_kwh': abs(total_heating_load_kwh)
  }


if __name__ == "__main__":
  # Example parameters
  params: Params = Params(
    u_value=4.0,            # W/m²·K
    height=4.0,             # m
    infiltration_rate=0.5,  # air changes per hour
    thermal_mass=100000,    # J/m²·K
    glazing_transmittance=0.8,  # fraction
    latitude=40,            # degrees North
    orientation=0           # degrees from South
  )
  
  # Example winter day temperatures
  winter_temps = [
    -2, -3, -3, -4, -4, -4,  # Midnight to 5am
    -3, -2,  0,  2,  4,  6,  # 6am to 11am
    7,  8,  8,  7,  5,  3,  # Noon to 5pm
    2,  1,  0, -1, -1, -2   # 6pm to 11pm
  ]
  
  # Simulate a winter day (day 15 = January 15)
  target_temp_deg_C = 23
  results = simulate_day(params, winter_temps, target_temp=target_temp_deg_C, day_of_year=15)
  print(results)
  
  print("\nDaily totals (kWh/m²):")
  print(f"Total cooling load: {results['total_cooling_load_kwh']:.2f}")
  print(f"Total heating load: {results['total_heating_load_kwh']:.2f}")

  electricity_price_per_kwh = 0.12
  natural_gas_price_per_kwh = 0.03
  cooling_cop = 8.0
  heating_cop = 0.85
  
  daily_cooling_cost = results['total_cooling_load_kwh'] * electricity_price_per_kwh / cooling_cop
  daily_heating_cost = results['total_heating_load_kwh'] * natural_gas_price_per_kwh / heating_cop
  
  print(f"Daily cooling cost: ${daily_cooling_cost:.3f}/m²")
  print(f"Daily heating cost: ${daily_heating_cost:.3f}/m²")
  print(f"Daily total energy cost: ${daily_cooling_cost + daily_heating_cost:.3f}/m²")

  # Calculate total annual cost
  annual_cooling_cost = daily_cooling_cost * 365
  annual_heating_cost = daily_heating_cost * 365
  annual_total_cost = annual_cooling_cost + annual_heating_cost
  
  print(f"Annual cooling cost: ${annual_cooling_cost:.3f}/m²")
  print(f"Annual heating cost: ${annual_heating_cost:.3f}/m²")
  print(f"Annual total cost: ${annual_total_cost:.3f}/m²")
  
  
  
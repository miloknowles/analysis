import pandas as pd
import requests


def download_year(year: int, station_ids: list[str]):
  """Download an entire year of data for a list of station ids.
  
  Data source:
    https://www.ncei.noaa.gov/oa/global-historical-climatology-network/index.html#hourly/access/by-year/2023/parquet/
  """
  failed_ids = []
  succeed_ids = []
  print(f"Downloading data from {len(station_ids)} stations for year {year}")

  # https://www.ncei.noaa.gov/oa/global-historical-climatology-network/hourly/access/by-year/2023/parquet/GHCNh_AGM00060371_2023.parquet
  base_url = "https://www.ncei.noaa.gov/oa/global-historical-climatology-network/hourly/access/by-year/{}/parquet/{}"

  for station_id in station_ids:
    station_id = station_id.strip()
    print(f"Downloading data for station {station_id}")

    download_filename = f"GHCNh_{station_id}_{year}.parquet"
    output_filename = f"./ghcn_hourly_data/GHCNh_{station_id}_{year}.parquet"

    # Download the file from the NOAA website
    url = base_url.format(year, download_filename)
    print(url)
    response = requests.get(url)
    print(response.status_code)

    if response.status_code != 200:
      print(f"FAILED: {response.status_code}")
      failed_ids.append(station_id)
      continue

    succeed_ids.append(station_id)

    # Save the file to the local directory
    with open(output_filename, 'wb') as f:
      f.write(response.content)

  return succeed_ids, failed_ids


if __name__ == "__main__":
  YEAR = 2023
  OFFSET = None
  LIMIT = None

  with open("ghcn_station_ids.txt", "r") as f:
    station_ids = f.readlines()

  if OFFSET is not None and OFFSET > 0:
    station_ids = station_ids[OFFSET:]

  if LIMIT is not None and LIMIT > 0:
    station_ids = station_ids[:LIMIT]

  succeed_ids, failed_ids = download_year(YEAR, station_ids)

  print(f"{len(succeed_ids)} succeeded, {len(failed_ids)} failed")

  with open("ghcn_succeed_ids.txt", "w") as f:
    for id in succeed_ids:
      f.write(id)

  with open("ghcn_failed_ids.txt", "w") as f:
    for id in failed_ids:
      f.write(id)
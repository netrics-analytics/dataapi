import pandas
import requests
from pandas import json_normalize
from datetime import datetime, timedelta

''' CALLING GraphQL '''
def fetch_graphql_data(APIKey, endpoint, query, variables=None):
    headers = {
        'Content-Type': 'application/json',
        'Authorization': APIKey #AUTHENTICATION
    }
    response = requests.post(endpoint, json={'query': query, 'variables': variables}, headers=headers)
    response.raise_for_status()  # Raise an exception for HTTP errors
    response_data = response.json()
    if 'errors' in response_data:
        raise Exception(f"GraphQL query failed: {response_data['errors']}")
    return response_data

def fetch_all_data(APIKey, endpoint, query, variables=None, page_size=1000):
    variables = variables or {}
    variables['first'] = page_size
    all_items = []
    has_next_page = True
    after_cursor = None

    while has_next_page:
        variables['after'] = after_cursor
        response_data = fetch_graphql_data(APIKey, endpoint, query, variables)
        data = response_data['data']['conversionPath']
        nodes = data['nodes']
        page_info = data['pageInfo']

        all_items.extend(nodes)
        after_cursor = page_info['endCursor']
        has_next_page = page_info['hasNextPage']

    return all_items

# Define your GraphQL endpoint and query
endpoint = 'https://api.stackadapt.com/graphql'
query = '''
query($startTime: ISO8601DateTime, $endTime: ISO8601DateTime, $first: Int, $after: String, $campaignIds: [ID!], $trackerIds: [ID!]) {
  conversionPath(
        filterBy: {
          campaignIds: $campaignIds,
          trackerIds: $trackerIds,
          startTime: $startTime,
          endTime: $endTime
        },
        first: $first,
        after: $after
    ) {
        totalCount
        pageInfo {
            hasNextPage
            hasPreviousPage
            startCursor
            endCursor
        }
        nodes {
            id
            attributionType
            impressionToConversionTime
            clickToConversionTime
            firstImpressionTime
            clickCount
            impressionCount
            impressionToConversionTime
            firstStats {
                clickTime
                clickToConversionTime
                device
                domain
                impressionTime
                impressionToConversionTime
                timeOnSite
            }
            lastStats {
                clickTime
                clickToConversionTime
                device
                domain
                impressionTime
                impressionToConversionTime
                timeOnSite
            }
            conversionExtra
            campaign {
                id
                name
                campaignGroup {
                    id
                    name
                }
                campaignStatus {
                    state
                    status
                }   
            }
            conversionPixel {
                id
                name
                description
                conversionType
                countType
            }
            advertiser {
                id
                name
            }
            ad {
                id
                name
            }
            conversionStats {
                conversionTime
                conversionUrl
                device
            }
        }
    }
}
'''

def extract_timezone_offset_in_minutes(iso_date):
    try:
        # Parse the ISO 8601 date string
        dt = datetime.fromisoformat(iso_date)
        
        # Extract the timezone offset if available
        if dt.tzinfo:
            offset = dt.tzinfo.utcoffset(dt)
            # Convert the offset to minutes
            offset_minutes = offset.total_seconds() / 60
            return int(offset_minutes)
        else:
            return 'No timezone info'
    except ValueError:
        return 'Invalid date format'

'''CALLING FUNCTION'''
def pullData(APIKey, startDate, endDate, query = query, endpoint = endpoint, campaignIds = [], trackerIds = []):
    variables = {"startTime": startDate + "T00:00:00+0000", "endTime": endDate + "T23:59:59+0000", "campaignIds": campaignIds, "trackerIds": trackerIds}
    data = fetch_all_data(APIKey, endpoint, query, variables)
    data = pandas.DataFrame(json_normalize(data,sep="_"))
    data = data.fillna('')
    data['timeDifferenceFromUTCinMins'] = data['conversionStats_conversionTime'].apply(extract_timezone_offset_in_minutes).astype(int)
    # data= data.drop(columns=["conversionExtra"])
    return data.to_dict(orient='records')
    # return data

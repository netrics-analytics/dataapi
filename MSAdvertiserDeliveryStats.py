import pandas
import requests
from pandas import json_normalize
from datetime import timedelta,datetime


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
        data = response_data['data']['advertiserDelivery']['records']
        nodes = data['nodes']
        page_info = data['pageInfo']

        all_items.extend(nodes)
        after_cursor = page_info['endCursor']
        has_next_page = page_info['hasNextPage']

    return all_items

# Define your GraphQL endpoint and query
endpoint = 'https://api.stackadapt.com/graphql'

query = '''
    query($startTime: ISO8601Date, $endTime: ISO8601Date, $first: Int, $after: String, $granularity: DeliveryStatsGranularity!) {
      advertiserDelivery(
        dataType: TABLE,
        date: {
          from: $startTime,
          to: $endTime
        },
        granularity: $granularity
      ) {
        ...on AdvertiserDeliveryOutcome {
          records(
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
              advertiser {
                id
                name
              }
              granularity {
                startTime
                endTime
                type
              }
              metrics {
                atos
                atosUnits
                audioCompeletionRate
                clickConversions
                clickSecondaryConversions
                clicks
                conversionRevenue
                conversions
                cookieConversions
                cost
                ctr
                cvr
                ecpa
                ecpc
                ecpcl
                ecpe
                ecpm
                ecpv
                engagementRate
                engagements
                frequency
                ga4AverageSessionDuration
                ga4BounceRate
                ga4EngagedSessions
                ga4Sessions
                ga4TotalUsers
                impressionConversions
                impressionSecondaryConversions
                impressions
                ipConversions
                pageStarts
                pageTimeUnits
                profit
                rcpa
                rcpc
                rcpcl
                rcpe
                rcpm
                revenue
                revenueFee
                roas
                secondaryConversions
                techFee
                totalTime
                tpCpcCost
                tpCpmCost
                uniqueConversions
                uniqueImpressions
                videoCompletionRate
                videoCompletions
                videoQ1Playbacks
                videoQ2Playbacks
                videoQ3Playbacks
                videoStarts
                viewRate
              }
            }
          }
        }
      }
    }
'''

'''CALLING FUNCTION'''
def pullData(APIKey, startDate, endDate,granularity,query = query, endpoint = endpoint):
    variables = {"startTime": startDate + "T00:00:00+0000", "endTime": (datetime.strptime(endDate, '%Y-%m-%d') + timedelta(days=1)).strftime('%Y-%m-%d') + "T00:00:00+0000", "granularity": granularity}
    print(variables)
    data = fetch_all_data(APIKey, endpoint, query, variables)
    data = pandas.DataFrame(json_normalize(data,sep="_"))
    data = data.fillna('')
    return data.to_dict(orient='records')
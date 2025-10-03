import pandas
import requests
from pandas import json_normalize
from datetime import timedelta,datetime
import time
import random

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

def fetch_all_data(APIKey, endpoint, query, variables=None, page_size=1000, max_retries=10, retry_delay=1):
    variables = variables or {}
    variables['first'] = page_size
    all_items = []
    has_next_page = True
    after_cursor = None
    retries = 0

    while has_next_page:
        try:
            variables['after'] = after_cursor
            response_data = fetch_graphql_data(APIKey, endpoint, query, variables)

            # Check if the response is valid
            if not response_data or 'data' not in response_data:
                raise ValueError("Invalid response data received")

            data = response_data['data'].get('campaignGroupInsight', {})
            
            if not data or 'records' not in data:
                # Handle the case where 'records' is missing
                raise ValueError("Missing 'records' in response data")

            records = data['records']
            nodes = records.get('nodes', [])
            page_info = records.get('pageInfo', {})

            if not isinstance(nodes, list):
                raise ValueError("Invalid 'nodes' data format")
            
            if not isinstance(page_info, dict):
                raise ValueError("Invalid 'pageInfo' data format")
            
            if not nodes:
                # If no nodes are returned, retry the request
                print("No records found. Retrying...")
                retries += 1
                if retries > max_retries:
                    raise RuntimeError("Max retries reached without finding records.")
                time.sleep(retry_delay)  # Wait before retrying
                continue  # Retry the same page
            else:
                all_items.extend(nodes)
                retries = 0  # Reset retries after a successful fetch

            # Get pagination information
            after_cursor = page_info.get('endCursor')
            has_next_page = page_info.get('hasNextPage', False)

        except ValueError as e:
            # Specifically handle "Missing 'records' in response data" error
            if str(e) == "Missing 'records' in response data":
                print(f"Retry due to missing 'records': {e}")
                retries += 1
                if retries > max_retries:
                    raise RuntimeError("Max retries reached due to missing 'records'.")
                time.sleep(retry_delay)  # Wait before retrying
                continue  # Retry the same page
            else:
                # Handle other ValueError cases
                print(f"Data error: {e}")
                break
        
        except Exception as e:
            # Log or handle unexpected errors
            print(f"Unexpected error: {e}")
            retries += 1
            if retries > max_retries:
                print("Max retries reached. Exiting.")
                break  # Exit loop after max retries
            # Exponential backoff for retry
            delay = retry_delay * (2 ** retries) + random.uniform(0, 1)
            print(f"Retrying after {delay:.2f} seconds...")
            time.sleep(delay)

    return all_items

# Define your GraphQL endpoint and query
endpoint = 'https://api.stackadapt.com/graphql'

query = '''
    query($startTime: ISO8601Date, $endTime: ISO8601Date, $first: Int, $after: String){
        campaignGroupInsight(
            attributes: [DATE],
            date: {
                from: $startTime,
                to: $endTime
            }
        ) {
            ... on CampaignGroupInsightOutcome {
            records(
                    first: $first,
                    after: $after
                ) { 
                pageInfo{
                    endCursor
                    hasNextPage
                    hasPreviousPage
                    startCursor
                }
                nodes{
                    attributes{
                        date
                    }
                    campaignGroup{
                        id
                        name
                        advertiser{
                            id
                            name
                        }
                        budgetAllocation{
                            allocationType    
                        }    
                        budgetRollover
                        budgetType
                        campaignGroupStatus{
                            state
                            status
                        }
                        domainExclusions
                        freqCapExpiry
                        freqCapLimit
                        isArchived
                        isInventoryPackagesStrict
                        marginRateType
                        pacing{
                            dailySpendNeeded{
                                dailySpendNeeded
                            }
                            flightPacing{
                                lifetimeBudget
                                totalProjectedSpend
                            }
                            projectedDailySpend{
                                currentPacePercentVar
                                projectedDailySpend
                            }
                        }
                        performanceBasedBudget
                        revenuePricing
                        revenueType
                        timezone
                    }
                    metrics{
                        atos
                        audioCompeletionRate
                        audioCompletions
                        audioQ1Playbacks
                        audioQ2Playbacks
                        audioQ3Playbacks
                        audioStarts
                        averageImpressionTime
                        clickConversionRate
                        clickConversions
                        clickSecondaryConversions
                        clicks
                        conversionRevenue
                        conversionRevenuePercentage
                        conversions
                        cookieConversions
                        cost
                        costPercentage
                        ctr
                        cvr
                        ecpa
                        ecpc
                        ecpcl
                        ecpcv
                        ecpe
                        ecpm
                        engagementRate
                        engagements
                        frequency
                        impressionConversionRate
                        impressionConversions
                        impressionSecondaryConversions
                        impressions
                        impressionsPercentage
                        pageStarts
                        profit
                        profitPercentage
                        rcpa
                        rcpc
                        rcpcl
                        rcpe
                        rcpm
                        revenue
                        revenuePercentage
                        roas
                        secondaryConversions
                        totalTime
                        uniqueImpressions
                        videoCompletionRate
                        videoCompletions
                        videoQ1Playbacks
                        videoQ2Playbacks
                        videoQ3Playbacks
                        videoStarts
                        viewRate
                        views
                    }   
                }
            }
        }
    }
}

'''

'''CALLING FUNCTION'''
def pullData(APIKey, startDate, endDate, query = query, endpoint = endpoint):
    variables = {"startTime": startDate + "T00:00:00+0000", "endTime": (datetime.strptime(endDate, '%Y-%m-%d') + timedelta(days=1)).strftime('%Y-%m-%d') + "T00:00:00+0000"}
    data = fetch_all_data(APIKey, endpoint, query, variables)
    data = pandas.DataFrame(json_normalize(data,sep="_"))
    data = data.fillna('')
    print(len(data))
    return data.to_dict(orient='records')
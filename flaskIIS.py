import pandas as pd
from flask import Flask, request, jsonify, abort
from flask_httpauth import HTTPBasicAuth
import MSConversionJourney as mcj
import MSAdvertiserDeliveryStats as mads
import MSCampaignGroupInsights as mcgi
import MSCampaignInsights as mci
import iMarketConversionJourney as icj
import Cred

# Create Flask application
app = Flask(__name__)
auth = HTTPBasicAuth()

users = Cred.apiUsers

@auth.verify_password
def verify_password(username, password):
    if username in users and users[username] == password:
        return username

# Restrict iMarketSolutions to a particular route 
def restrict_access():
    username = auth.current_user()
    if username == 'iMarketSolutions' and request.endpoint not in ['iMarketSolutions']:
        abort(403)  # Forbidden access

@app.route("/conversionJourney")
@auth.login_required
def getConversionJourney():
    restrict_access()
    APIKey = 'Bearer '+ str(request.headers.get('APIKey'))
    startDate = request.args.get('startDate')
    endDate = request.args.get('endDate')

    campaignIds = request.args.get('campaignIds', '')
    campaignIds = [id.strip() for id in campaignIds.split(',') if id.strip()]

    trackerIds = request.args.get('trackerIds', '')
    trackerIds = [id.strip() for id in trackerIds.split(',') if id.strip()]

    df = mcj.pullData(APIKey, startDate = startDate, endDate = endDate, campaignIds = campaignIds, trackerIds = trackerIds)
    df = {
        "#records": len(df),
        "data": df
    }
    return jsonify(df)

@app.route("/advertiserDeliveryStats")
@auth.login_required
def getAdvertiserDeliveryStats():
    restrict_access()
    APIKey = 'Bearer '+ str(request.headers.get('APIKey'))
    startDate = request.args.get('startDate')
    endDate = request.args.get('endDate')
    granularity = request.args.get('granularity')

    df = mads.pullData(APIKey, startDate = startDate, endDate = endDate, granularity = granularity)
    df = {
        "#records": len(df),
        "data": df
    }
    return jsonify(df)

@app.route("/campaignGroupInsights")
@auth.login_required
def getCampaignGroupInsights():
    restrict_access()
    APIKey = 'Bearer '+ str(request.headers.get('APIKey'))
    startDate = request.args.get('startDate')
    endDate = request.args.get('endDate')

    df = mcgi.pullData(APIKey = APIKey,startDate = startDate, endDate = endDate)
    df = {
        "#records": len(df),
        "data": df
    }
    return jsonify(df)

@app.route("/campaignInsights")
@auth.login_required
def getCampaignInsights():
    restrict_access()
    APIKey = 'Bearer '+ str(request.headers.get('APIKey'))
    startDate = request.args.get('startDate')
    endDate = request.args.get('endDate')

    df = mci.pullData(APIKey = APIKey,startDate = startDate, endDate = endDate)
    df = {
        "#records": len(df),
        "data": df
    }
    return jsonify(df)

@app.route("/iMarketSolutions/conversionJourney", methods=['GET'])
@auth.login_required
def getIMConversionJourney():
     
    startDate = request.args.get('startDate')
    endDate = request.args.get('endDate')
   
    advertiserID = request.args.get('AdvertiserID', '')
    advertiserID = [id.strip() for id in advertiserID.split(',') if id.strip()]

    try:
        if startDate and endDate and pd.to_datetime(startDate).date() > pd.to_datetime(endDate).date():
            return jsonify({"error": "startDate cannot be greater than endDate"}), 400
        
        data = icj.getData(startDate, endDate, advertiserID)
    
    except Exception as e:
        return jsonify({"error": str(e)}), 400

    # Convert the DataFrame to a dictionary
    df_dict = {
        "#records": len(data),
        "data": data.to_dict(orient='records')
    }

    return jsonify(df_dict)
    
if __name__ == '__main__':
    app.run(debug=True)

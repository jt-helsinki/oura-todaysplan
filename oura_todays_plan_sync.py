import os
import requests
from datetime import datetime
from datetime import timedelta
from string import Template
import json

def _oura_header(oura_api_key):
    return { "Authorization": "Bearer %s" % (oura_api_key) }


def request_oura_sleep_data(session, oura_api_key):
    response_data = session.get( "https://api.ouraring.com/v1/sleep", headers = _oura_header( oura_api_key ) ).json()
    return response_data["sleep"]


def request_oura_readiness_data(session, oura_api_key):
    response_data = session.get( "https://api.ouraring.com/v1/readiness", headers = _oura_header( oura_api_key ) ).json()
    return response_data["readiness"]


def combine_oura_data(sleep_data, readiness_data):
    assert len( sleep_data ) == len( readiness_data )

    item_list = []
    index = 0
    for item in sleep_data:
        date, year, day_of_year = _summary_date_to_date_plus_one_day( item )
        combined_data = { }
        combined_data["date_time"] = date
        combined_data["year"] = year
        combined_data["day_of_year"] = day_of_year
        combined_data["sleep"] = item
        combined_data["readiness"] = readiness_data[index]
        item_list.append( combined_data )
        index = index + 1
    return item_list

def request_todays_plan_user_by_email(session, header, athlete_email, todays_plan_base_url = os.environ.get( "TODAYS_PLAN_BASE_URL" )):
    response_data = session.get( "https://%s/rest/users" % (todays_plan_base_url), headers = header, params = { "email": athlete_email } ).json()
    return response_data["id"]

def request_todays_plan_login(session, todays_plan_api_key, todays_plan_username, todays_plan_password, athlete_email, todays_plan_base_url = os.environ.get( "TODAYS_PLAN_BASE_URL" )):
    request_body = {
        "username": todays_plan_username,
        "password": todays_plan_password
    }
    response_data = session.get( "https://%s/rest/auth/login" % (todays_plan_base_url), params = request_body ).json()
    token = response_data["token"]
    user = response_data["user"]
    header = {
        "Authorization": "Bearer %s" % (token),
        "Content-Type": "application/json",
        "tp-nodecorate": "true",
        "Api-Key": todays_plan_api_key
    }
    user_id = request_todays_plan_user_by_email(session, header, athlete_email)
    return header, user, user_id


def post_oura_data_to_todays_plan(session, header, user_id, combined_oura_data, todays_plan_base_url = os.environ.get( "TODAYS_PLAN_BASE_URL" )):

    for item in combined_oura_data:
        date_time = item["date_time"]
        year = item["year"]
        day_of_year = item["day_of_year"]
        sleep_data = item["sleep"]
        readiness_data = item["readiness"]
        url = Template( "https://${todays_plan_base_url}/rest/users/day/set/${user_id}/${year}/${day_of_year}" ).substitute(
            todays_plan_base_url = todays_plan_base_url, user_id = user_id, year = year, day_of_year = day_of_year )
        hrv_comment = Template(
            "Readiness: ${readiness_score}, HR avg: ${hr_average}, Sleep: ${sleep_score}, Temp: ${temperature_delta} " ).substitute(
            readiness_score = readiness_data["score"], hr_average = sleep_data["hr_average"], sleep_score = sleep_data["score"], breath_average = sleep_data["breath_average"],
            temperature_delta = sleep_data["temperature_delta"] )
        request_body = {
            "sleep": {
                "uuid": f"oura-sleep-{year}-{day_of_year}",
                "source": "oura",
                "isMainSleep": True,
                "sleepEfficiency": int(sleep_data["score_efficiency"]),
                "sleepTimeInBed": int(sleep_data["duration"] / 60),
                "sleepMinsAsleep": int(sleep_data["total"] / 60),
                "sleepMinsAwake": int(sleep_data["awake"] / 60),
                "sleepMinsToFallAsleep": int(sleep_data["onset_latency"] / 60),
                "timeOfWaking": int(datetime.fromisoformat( sleep_data["bedtime_end"] ).timestamp() * 1000),
                "timeInBed": int(datetime.fromisoformat( sleep_data["bedtime_start"] ).timestamp() * 1000),
                "sleepRemMins": int(sleep_data["rem"] / 60)
            },
            "hrv": {
                "hrv": int(sleep_data["rmssd"]),
                "comment": hrv_comment
            },
            "restingBpm": sleep_data["hr_lowest"]
        }
        response_data = session.post( url, headers = header, data = json.dumps(request_body) )

        if response_data.json() == True:
            print(f"Sync OK for sleep record: oura-sleep-{year}-{day_of_year}")
        else:
            print(f"Error for sleep record: oura-sleep-{year}-{day_of_year}: {response_data.json()}")

def _summary_date_to_date_plus_one_day(item):
    summary_date = datetime.fromisoformat( item["summary_date"] ) + timedelta( days = 1 ) + timedelta( hours = 7 )
    year = summary_date.year
    day_of_year = summary_date.timetuple().tm_yday
    return summary_date, year, day_of_year


def main():
    oura_api_key = os.environ.get( "OURA_API_KEY" )
    todays_plan_api_key = os.environ.get( "TODAYS_PLAN_API_KEY" )
    todays_plan_username = os.environ.get( "TODAYS_PLAN_USERNAME" )
    todays_plan_password = os.environ.get( "TODAYS_PLAN_PASSWORD" )
    athlete_email = os.environ.get( "ATHLETE_EMAIL" )



    oura_session = requests.Session()
    sleep_data = request_oura_sleep_data( oura_session, oura_api_key )
    readiness_data = request_oura_readiness_data( oura_session, oura_api_key )
    combined_oura_data = combine_oura_data( sleep_data, readiness_data )

    todays_plan_session = requests.Session()
    header, user, user_id = request_todays_plan_login( todays_plan_session, todays_plan_api_key, todays_plan_username, todays_plan_password, athlete_email)

    post_oura_data_to_todays_plan( todays_plan_session, header, user_id, combined_oura_data )


    print('''
██████╗░░█████╗░████████╗░█████╗░  ░██████╗██╗░░░██╗███╗░░██╗░█████╗░███████╗██████╗░
██╔══██╗██╔══██╗╚══██╔══╝██╔══██╗  ██╔════╝╚██╗░██╔╝████╗░██║██╔══██╗██╔════╝██╔══██╗
██║░░██║███████║░░░██║░░░███████║  ╚█████╗░░╚████╔╝░██╔██╗██║██║░░╚═╝█████╗░░██║░░██║
██║░░██║██╔══██║░░░██║░░░██╔══██║  ░╚═══██╗░░╚██╔╝░░██║╚████║██║░░██╗██╔══╝░░██║░░██║
██████╔╝██║░░██║░░░██║░░░██║░░██║  ██████╔╝░░░██║░░░██║░╚███║╚█████╔╝███████╗██████╔╝
╚═════╝░╚═╝░░╚═╝░░░╚═╝░░░╚═╝░░╚═╝  ╚═════╝░░░░╚═╝░░░╚═╝░░╚══╝░╚════╝░╚══════╝╚═════╝░
        ''')



if __name__ == "__main__":
    main()

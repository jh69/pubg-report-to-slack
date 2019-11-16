import requests
from loguru import logger
import arrow

import time, os, sys, json, random

minimum_sleep = int(os.environ.get("MINIMUM_SLEEP", 1800))

try:
    userids = [
        i.strip() for i in os.environ.get("USER_IDS", "").split(",") if len(i) > 0
    ]
except Exception as e:
    logger.error(f"There was an issue with the USER_IDS env variable: {str(e)}")
    exit(1)

slackurl = os.environ.get("SLACK_WEBHOOK_URL", "")
if len(slackurl) < 10:
    posting_to_slack = False
    logger.warning("no slack webhook url found")
else:
    posting_to_slack = True

seen_before = json.load(open("seen_before.json", "r"))
for uid in userids:
    if uid not in list(seen_before):
        seen_before[uid] = []

pubg = json.loads(open("pubg_dictionary.json", "r").read())


def post_to_slack(posttext, slackurl):
    slackheaders = {"Content-type": "application/json"}
    payload = {
        "text": posttext,
        "username": "PUBG Report",
        "icon_emoji": ":poultry_leg:",
    }
    data = json.dumps(payload)
    try:
        r = requests.post(slackurl, headers=slackheaders, data=data)
        if r.status_code > 201:
            logger.error(f"slack problem: {r.status_code}, {r.text}")
    except Exception as e:
        logger.error(
            f"Could not reach slack. Error: {str(e)} - slackurl: {slackurl} - data: {data}"
        )
    time.sleep(0.1)
    return


def save_seen_befores(seen_before_dict):
    open("seen_before.json", "w").write(json.dumps(seen_before_dict))
    return


def look_for_streams(uid):
    url = f"https://api.pubg.report/v1/players/{uid}/streams"
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/78.0.3904.97 Safari/537.36"
    }
    r = requests.get(url, headers=headers)
    return r.text


def build_report_on_new_stream(streamobject):
    s = streamobject[0]
    report = f"[{pubg[s['Map']]}/{s['Mode']}] "
    report += f"*{s['Killer']}* was seen killing *{s['Victim']}* "
    report += f"using {pubg[s['DamageCauser']]} from {s['Distance']}m "
    report += f"- Watch: https://pubg.report/streams/{s['MatchID']}/{s['AttackID']}"
    return report


def parse_streams_list(jsontext, uid):
    try:
        jdata = json.loads(jsontext)
    except Exception as e:
        logger.warning(f"Could not parse JSON from api: {str(e)}")
        return None
    for i in jdata:
        # if i:
        if i not in seen_before[uid]:
            seen_before[uid].append(i)
            if len(seen_before[uid]) > 50:
                seen_before[uid].pop(0)
            save_seen_befores(seen_before)
            report = build_report_on_new_stream(jdata[i])
            # print(report)
            if posting_to_slack == True:
                post_to_slack(report, slackurl)
            else:
                print(report)
        else:
            logger.debug(f"already seen {i}, skipping notification")


while True:
    for uid in userids:
        logger.debug(f"Checking {uid}")
        parse_streams_list(look_for_streams(uid), uid)
        time.sleep(30)
    sleeplength = minimum_sleep + random.randint(0, 300)
    logger.debug(f"Sleeping for {sleeplength}s")
    time.sleep(sleeplength)

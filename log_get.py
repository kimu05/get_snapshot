import boto3
import datetime

DIFF_JST_FROM_UTC = 21
now = datetime.datetime.utcnow() + datetime.timedelta(hours=DIFF_JST_FROM_UTC)
today = datetime.datetime(now.year, now.month, now.day, 0, 0, 0, 0)
yesterday = today - datetime.timedelta(days=1)
today_unix = int(today.timestamp()*1000)
yesterday_unix = int(yesterday.timestamp()*1000)
prefix = "/aws/lambca/test"

print(now)

print(yesterday_unix)

client = boto3.client('logs')
#next_token = ''
#response = {}
response = client.filter_log_events(
    logGroupName=prefix,
    startTime = yesterday_unix,
    endTime = today_unix
)

events = response["events"]
#timestamp = response["events"]["timestamp"]
#print(response)
#print(events)



if events != []:
    print("前日の変更あり")




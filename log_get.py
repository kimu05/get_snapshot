import boto3
import datetime
now = datetime.datetime.now()
today = datetime.datetime(now.year, now.month, now.day, 0, 0, 0, 0)
yesterday = today - datetime.timedelta(days=1)
today_unix = int(today.timestamp()*1000)
yesterday_unix = int(yesterday.timestamp()*1000)
prefix = "/aws/lambca/test"

client = boto3.client('logs')
#next_token = ''
#response = {}
response = client.filter_log_events(
    logGroupName=prefix,
    startTime = yesterday_unix,
    endTime = today_unix
)

events = response["events"]
#print(events)

if events != []:
    print("前日の変更あり")




#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# 特定のタグを含むEBSボリュームのスナップショットを作成する。
#   Python 3.6
#
#   （参考）
#   https://qiita.com/HorieH/items/66bb68d12bd8fdbbd076
#
# EBSボリュームが存在するリージョンでLambda関数を作成すること。
#
# 対象とするボリュームのタグで、
# Key: <TAGKEYの文字列>, Value: <保存世代数> 
# を設定すること。
#
TAGKEY = 'Backup-Generation'
 
import boto3
import collections
import time
from botocore.client import ClientError
import os
import datetime

client = boto3.client('ec2', os.environ['AWS_REGION'])

def lambda_handler(event, context):
    events = events_get()
    if events == True:
        descriptions = create_snapshots()
        delete_old_snapshots(descriptions)

def events_get():
    now = datetime.datetime.now()
    today = datetime.datetime(now.year, now.month, now.day, 0, 0, 0, 0)
    yesterday = today - datetime.timedelta(days=1)
    today_unix = int(today.timestamp()*1000)
    yesterday_unix = int(yesterday.timestamp()*1000)
    prefix = "/aws/lambca/test"
    
    client = boto3.client('logs')

    response = client.filter_log_events(
        logGroupName=prefix,
        startTime = yesterday_unix,
        endTime = today_unix
    )
    
    events = response["events"]
    #print(events)
    
    if events != []:
        return True
        print("前日の変更あり")
    return 


def create_snapshots():
    volumes = get_volumes([TAGKEY])
 
    descriptions = {}
 
    for v in volumes:
        tags = { t['Key']: t['Value'] for t in v['Tags'] }
        generation = int( tags.get(TAGKEY, 0) )
 
        if generation < 1:
            continue
 
        volume_id = v['VolumeId']
        description = volume_id if tags.get('Name') is '' else '%s(%s)' % (volume_id, tags['Name'])
        description = 'Auto Snapshot ' + description
 
        snapshot = _create_snapshot(volume_id, description)
        print('create snapshot %s(%s)' % (snapshot['SnapshotId'], description))
 
        descriptions[description] = generation
 
    return descriptions
 
def get_volumes(tag_names):
    volumes = client.describe_volumes(
        Filters=[
            {
                'Name': 'tag-key',
                'Values': tag_names
            }
        ]
    )['Volumes']
 
    return volumes
 
def delete_old_snapshots(descriptions):
    snapshots_descriptions = get_snapshots_descriptions(list(descriptions.keys()))
 
    for description, snapshots in snapshots_descriptions.items():
        delete_count = len(snapshots) - descriptions[description]
 
        if delete_count <= 0:
            continue
 
        snapshots.sort(key=lambda x:x['StartTime'])
 
        old_snapshots = snapshots[0:delete_count]
 
        for s in old_snapshots:
            _delete_snapshot(s['SnapshotId'])
            print('delete snapshot %s(%s)' % (s['SnapshotId'], s['Description']))
 
def get_snapshots_descriptions(descriptions):
    snapshots = client.describe_snapshots(
        Filters=[
            {
                'Name': 'description',
                'Values': descriptions,
            }
        ]
    )['Snapshots']
 
    groups = collections.defaultdict(lambda: [])
    { groups[ s['Description'] ].append(s) for s in snapshots }
 
    return groups
 
def _create_snapshot(id, description):
    for i in range(1, 3):
        try:
            return client.create_snapshot(VolumeId=id,Description=description)
        except ClientError as e:
            print(str(e))
        time.sleep(1)
    raise Exception('cannot create snapshot ' + description)
 
def _delete_snapshot(id):
    for i in range(1, 3):
        try:
            return client.delete_snapshot(SnapshotId=id)
        except ClientError as e:
            print(str(e))
            if e.response['Error']['Code'] == 'InvalidSnapshot.InUse':
                return;
        time.sleep(1)
    raise Exception('cannot delete snapshot ' + id)
 
# EOF
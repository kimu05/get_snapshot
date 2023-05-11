#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# 特定のタグを含むEBSボリュームのスナップショットを作成する。
#   Python 3.6
#
#   （参考）
#   https://qiita.com/HorieH/items/66bb68d12bd8fdbbd076
#
 
import boto3
import collections
import time
from botocore.client import ClientError
import os
import datetime

ec2 = boto3.client('ec2')

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
    return 

def create_snapshots():
    instances = get_instances(['Backup-Generation'])

    descriptions = {}

    for i in instances:
        tags = {t['Key']: t['Value'] for t in i['Tags']}
        generation = int(tags.get('Backup-Generation', 0))

        if generation < 1:
            continue

        for b in i['BlockDeviceMappings']:
            if b.get('Ebs') is None:
                continue

            volume_id = b['Ebs']['VolumeId']
            description = volume_id if tags.get('Name') is '' else '%s(%s)' % (volume_id, tags['Name'])
            description = 'Auto Snapshot ' + description

            snapshot = _create_snapshot(volume_id, description)
            print('create snapshot %s(%s)' % (snapshot['SnapshotId'], description))

            descriptions[description] = generation

    return descriptions


def get_instances(tag_names):
    reservations = ec2.describe_instances(
        Filters=[
            {
                'Name': 'tag-key',
                'Values': tag_names
            }
        ]
    )['Reservations']

    return sum([
        [i for i in r['Instances']]
        for r in reservations
    ], [])


def delete_old_snapshots(descriptions):
    snapshots_descriptions = get_snapshots_descriptions(list(descriptions.keys()))

    for description, snapshots in snapshots_descriptions.items():
        delete_count = len(snapshots) - descriptions[description]

        if delete_count <= 0:
            continue

        snapshots.sort(key=lambda x: x['StartTime'])

        old_snapshots = snapshots[0:delete_count]

        for s in old_snapshots:
            _delete_snapshot(s['SnapshotId'])
            print('delete snapshot %s(%s)' % (s['SnapshotId'], s['Description']))
 


def get_snapshots_descriptions(descriptions):
    snapshots = ec2.describe_snapshots(
        Filters=[
            {
                'Name': 'description',
                'Values': descriptions,
            }
        ]
    )['Snapshots']

    groups = collections.defaultdict(lambda: [])
    {groups[s['Description']].append(s) for s in snapshots}

    return groups


def _create_snapshot(id, description):
    for i in range(1, 3):
        try:
            return ec2.create_snapshot(VolumeId=id, Description=description)
        except ClientError as e:
            print(str(e))
            time.sleep(1)
    raise Exception('cannot create snapshot ' + description)


def _delete_snapshot(id):
    for i in range(1, 3):
        try:
            return ec2.delete_snapshot(SnapshotId=id)
        except ClientError as e:
            print(str(e))
            time.sleep(1)
    raise Exception('cannot delete snapshot ' + id)

#EOF
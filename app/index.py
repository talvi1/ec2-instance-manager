from flask import render_template, redirect, url_for, request
from app import manager
import boto3
from datetime import datetime, timedelta
from operator import itemgetter





@manager.route('/home', methods=['GET'])
def home_page():
    
    ec2 = boto3.resource('ec2')
    instances = ec2.instances.all()
    client = boto3.client('cloudwatch')
    metric_name = 'CPUUtilization'
    namespace = 'AWS/EC2'
    statistic = 'Average'

    cpu = client.get_metric_statistics(
        Period=1 * 60,
        StartTime=datetime.utcnow() - timedelta(seconds=30 * 60),
        EndTime=datetime.utcnow() - timedelta(seconds=0 * 60),
        MetricName=metric_name,
        Namespace=namespace,  # Unit='Percent',
        Statistics=[statistic],
        Dimensions=[{'Name': 'InstanceId', 'Value': 'i-073587260f04b73ce'}]
    )
  #  print(cpu)
    cpu_stats = []
    for point in cpu['Datapoints']:
        hour = point['Timestamp'].hour
        minute = point['Timestamp'].minute
        time = hour + minute/60
        cpu_stats.append([time,point['Average']])

    cpu_stats = sorted(cpu_stats, key=itemgetter(0))
    print(cpu_stats)
    for instance in instances:
        if (instance.tags[0]['Key'] == 'worker'):
            print(instance.id)
            print(instance.state)
            #print(instance.tags)
    return render_template('home.html')
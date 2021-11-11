from flask import render_template, redirect, url_for, request
from app import manager
import boto3
from datetime import datetime, timedelta




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
        StartTime=datetime.utcnow() - timedelta(seconds=60 * 60),
        EndTime=datetime.utcnow() - timedelta(seconds=0 * 60),
        MetricName=metric_name,
        Namespace=namespace,  # Unit='Percent',
        Statistics=[statistic],
        Dimensions=[{'Name': 'InstanceId', 'Value': 'i-05b1e1d83bfbf9abe'}]
    )
    print(cpu)

    for instance in instances:
        if (instance.tags[0]['Key'] == 'worker'):
            print(instance.id)
            #print(instance.tags)
    return render_template('home.html')
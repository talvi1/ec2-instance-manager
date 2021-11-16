from flask import render_template, redirect, url_for, request
from app import manager
import boto3
from datetime import datetime, timedelta
from operator import itemgetter




@manager.route('/', methods=['GET'])
@manager.route('/home', methods=['GET'])
def home_page():
    
    ec2 = boto3.resource('ec2')
    instances = ec2.instances.all()
    client = boto3.client('cloudwatch')
    metric_name = 'CPUUtilization'
    namespace = 'AWS/EC2'
    statistic = 'Average'
    active_instances = []
    for x, instance in enumerate(instances):
        if (instance.tags[0]['Key'] == 'worker' and instance.state['Name'] == 'running'):           
            active_instances.append(instance.instance_id)
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
    return render_template('home.html', num=len(active_instances))

@manager.route('/workers', methods=['GET'])
def workers():
    ec2 = boto3.resource('ec2')
    instances = ec2.instances.all()
    client = boto3.client('cloudwatch')
    metric_name = 'CPUUtilization'
    namespace = 'AWS/EC2'
    statistic = 'Average'
    active_instances = []
    for x, instance in enumerate(instances):
        if (instance.tags[0]['Key'] == 'worker' and instance.state['Name'] == 'running'):           
            active_instances.append(instance.instance_id)
    cpu = []
    for x, instance_id in enumerate(active_instances):

        cpu.append([instance_id, client.get_metric_statistics(
        Period=1 * 60,
        StartTime=datetime.utcnow() - timedelta(seconds=30 * 60),
        EndTime=datetime.utcnow() - timedelta(seconds=0 * 60),
        MetricName=metric_name,
        Namespace=namespace,  # Unit='Percent',
        Statistics=[statistic],
        Dimensions=[{'Name': 'InstanceId', 'Value': instance_id}]
        )])
        #print(instance_id)
    cpu_stats = []
    for x in range(len(cpu)):
        temp = []
        for point in cpu[x][1]['Datapoints']:
            hour = point['Timestamp'].hour
            minute = point['Timestamp'].minute
            time = hour + minute/60
            temp.append([time, point['Average']])
        temp = sorted(temp, key=itemgetter(0))
        cpu_stats.append([str(cpu[x][0]), temp])

    # for point in cpu['Datapoints']:
    #     hour = point['Timestamp'].hour
    #     minute = point['Timestamp'].minute
    #     time = hour + minute/60
    #     cpu_stats.append([time,point['Average']])

    cpu_stats = sorted(cpu_stats, key=itemgetter(0))
    return render_template('workers.html', value=cpu_stats)

@manager.route('/auto-scale-policy', methods=['GET', 'POST'])
def auto_scaler_configuration():
    if request.method == "POST":
        cpu_increase = request.form.get('cpu_increase')
        cpu_decrease = request.form.get('cpu_decrease')
        ratio_increase = request.form.get('ratio_increase')
        ratio_decrease = request.form.get('ratio_decrease')
        print(cpu_increase)
        print(cpu_decrease)
        print(ratio_increase)
        print(ratio_decrease)
    return render_template('auto-scaler.html')
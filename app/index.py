from flask import render_template, redirect, url_for, request, g
from app import manager
import boto3
from multiprocessing.connection import Client
from datetime import datetime, timedelta
from operator import itemgetter
from app.config import db_config, db_config_manager
import mysql.connector

def connect_to_database():
    return mysql.connector.connect(user=db_config['user'], 
                                    password=db_config['password'], 
                                    host=db_config['host'],
                                    database=db_config['database'])

def connect_to_database_manager():
    return mysql.connector.connect(user=db_config_manager['user'], 
                                    password=db_config_manager['password'], 
                                    host=db_config_manager['host'],
                                    database=db_config_manager['database'])
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = connect_to_database()
    return db

def get_db_manager():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = connect_to_database_manager()
    return db

@manager.route('/', methods=['GET', 'POST'])
@manager.route('/home', methods=['GET', 'POST'])
def home_page():
    ec2 = boto3.resource('ec2')
    ec2_client = boto3.client('ec2')
    instances = ec2.instances.all()
    client = boto3.client('cloudwatch')
    metric_name = 'CPUUtilization'
    namespace = 'AWS/EC2'
    statistic = 'Average'
    active_instances = []
    stopped_instances = []
    pending_instances = []
    stopping_instances = []

    for x, instance in enumerate(instances):
        if (instance.tags[0]['Key'] == 'worker' and instance.state['Name'] == 'running'):           
            active_instances.append(instance.instance_id)
        elif (instance.tags[0]['Key'] == 'worker' and instance.state['Name'] == 'stopped'):
            stopped_instances.append(instance.instance_id)
        elif (instance.tags[0]['Key'] == 'worker' and instance.state['Name'] == 'pending'):           
            pending_instances.append(instance.instance_id)
        elif (instance.tags[0]['Key'] == 'worker' and instance.state['Name'] == 'stopping'):
            stopping_instances.append(instance.instance_id)
        num = [len(active_instances), len(stopped_instances), len(pending_instances), len(stopping_instances)]

    return render_template('home.html', num=num)

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
        if (instance.tags[0]['Key'] == 'worker'):           
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

    http_rate = []
    for x, instance_id in enumerate(active_instances):
        http_rate.append([instance_id, client.get_metric_statistics(
    Namespace='HTTP Request Rate',
    MetricName='HTTP Requests Per Minute',
    Dimensions=[
        {
            'Name': 'Instance ID',
            'Value': instance_id
        },
    ],
    StartTime=datetime.utcnow() - timedelta(seconds=30 * 60),
    EndTime=datetime.utcnow() - timedelta(seconds=0 * 60),
    Period=60,
    Statistics=[
        'Average',
    ])])
    http_stats = []
    for x in range(len(http_rate)):
        temp = []
        for point in http_rate[x][1]['Datapoints']:
            hour = point['Timestamp'].hour
            minute = point['Timestamp'].minute
            time = hour + minute/60
            temp.append([time, point['Average']])
        temp = sorted(temp, key=itemgetter(0))
        http_stats.append([str(http_rate[x][0]), temp])

    return render_template('workers.html', http=http_stats, cpu=cpu_stats)

@manager.route('/auto-scale-policy', methods=['GET', 'POST'])
def auto_scaler_configuration():
    if request.method == "POST":
        cpu_increase = request.form.get('cpu_increase')
        cpu_decrease = request.form.get('cpu_decrease')
        ratio_increase = request.form.get('ratio_increase')
        ratio_decrease = request.form.get('ratio_decrease')

    return render_template('auto-scaler.html')

@manager.route('/add-remove', methods=['GET', 'POST'])
def add_remove():
    if request.method == "POST":
        ec2 = boto3.resource('ec2')
        ec2_client = boto3.client('ec2')
        instances = ec2.instances.all()
        active_instances = []
        stopped_instances = []
        pending_instances = []
        stopping_instances = []
        for x, instance in enumerate(instances):
            if (instance.tags[0]['Key'] == 'worker' and instance.state['Name'] == 'running'):           
                active_instances.append(instance.instance_id)
            elif (instance.tags[0]['Key'] == 'worker' and instance.state['Name'] == 'stopped'):
                stopped_instances.append(instance.instance_id)
            elif (instance.tags[0]['Key'] == 'worker' and instance.state['Name'] == 'pending'):           
                pending_instances.append(instance.instance_id)
            elif (instance.tags[0]['Key'] == 'worker' and instance.state['Name'] == 'stopping'):
                stopping_instances.append(instance.instance_id)
            num = [len(active_instances), len(stopped_instances), len(pending_instances), len(stopping_instances)]
        if request.form.get('add') == 'added': 
            if (len(active_instances)+len(pending_instances)) == 6:
                error_msg = "Max workers already started, additional workers can't be added."
            elif len(stopped_instances) == 0:
                error_msg = "Workers are busy right now, please try adding additional working in a few minutes."
            else:
                add = stopped_instances.pop()
                response = ec2_client.start_instances(InstanceIds=[add])
                error_msg = "Worker Added!"
            return render_template('home.html', num=num, error=error_msg)
        elif request.form.get('remove') == 'removed':
            if len(active_instances) == 1:
                error_msg = "Minimum workers already running, additional workers can't be removed."
            else:
                remove = active_instances.pop()
                response = ec2_client.stop_instances(
                    InstanceIds=[remove])
                error_msg = "Worker Removed!"
            return render_template('home.html', num=num, error=error_msg)
    return redirect("/home")

@manager.route('/stop-application', methods=['GET', 'POST'])
def stop_application():
    if request.method == "POST":
        if request.form.get('stop') == 'stopped': 
            ec2_client = boto3.client('ec2')

    return redirect("/home")

@manager.route('/delete-application-data', methods=['GET', 'POST'])
def delete_application_data():
    if request.method == "POST":
        if request.form.get('delete') == 'deleted': 
            ec2_client = boto3.client('ec2')
            s3 = boto3.resource('s3')
            bucket = s3.Bucket('webapp-images-ece1779')
            bucket.objects.all().delete()
            con = get_db()
            cursor = con.cursor()
            query = '''TRUNCATE images;'''                         
            cursor.execute(query,())
            con.commit()
    return redirect("/home")
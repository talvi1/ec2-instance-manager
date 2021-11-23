from flask import render_template, redirect, url_for, request, g
import boto3
from datetime import datetime, timedelta
from operator import itemgetter
import mysql.connector
from app import manager
from app.config import db_config, db_config_manager

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
    """
    home_page() - Shows basic worker statsc such as active, stopped, being started and being stopped # of instances.
    Gets the # of active workers for the past 30 minutes from manager database and displays them to the webpage.
    """
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

    con = get_db_manager()
    cursor = con.cursor()
    query = '''SELECT * FROM workers;'''                         
    cursor.execute(query,())
    result = cursor.fetchall()
    myls = []
    if (len(result) >= 30):
        myls = result[-30:]
    else:
        myls = result
    temp = []
    for x in range(len(myls)):
        date_time_str = myls[x][2]
        date_time_obj = datetime.strptime(date_time_str, '%Y-%m-%d %H:%M:%S.%f')
        hour = date_time_obj.hour
        minute = date_time_obj.minute
        time = hour + minute/60
        temp.append([time, myls[x][1]])
        
    return render_template('home.html', num=num, worker=temp)

@manager.route('/workers', methods=['GET'])
def workers():
    """
    workers() - Displays detailed charts of each worker's cpu utilization and http request rate. 
    """
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
    '''
    auto_scaler_configuration() - puts the admin's auto-scaler configuration into the manager database to be used by the background scaler
    '''
    if request.method == "POST":
        cpu_increase = request.form.get('cpu_increase')
        cpu_decrease = request.form.get('cpu_decrease')
        ratio_increase = request.form.get('ratio_increase')
        ratio_decrease = request.form.get('ratio_decrease')
        scaling_option = request.form.get('option')
        con = get_db_manager()
        cursor = con.cursor()
        query = '''INSERT INTO scaling (increase, decrease, expand, shrink, auto) VALUES (%s, %s, %s, %s, %s);'''                         
        cursor.execute(query,(cpu_increase, cpu_decrease, ratio_increase, ratio_decrease, scaling_option))
        con.commit()

    return render_template('auto-scaler.html')

@manager.route('/add-remove', methods=['GET', 'POST'])
def add_remove():
    '''
    add_remove() - Manually adds or removes worker instances.
    '''
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
    '''
    stop_application() - Stops all running instances and stops the manager. 
    '''
    if request.method == "POST":
        if request.form.get('stop') == 'stopped': 
            ec2 = boto3.resource('ec2')
            ec2_client = boto3.client('ec2')
            instances = ec2.instances.all()
            active_instances = []
            for x, instance in enumerate(instances):
                if (instance.tags[0]['Key'] == 'worker' and instance.state['Name'] == 'running'):           
                    active_instances.append(instance.instance_id)
            for x in range(len(active_instances)):
                response = ec2_client.stop_instances(InstanceIds=[active_instances[x]])
            
            
            ec2_client.stop_instances(InstanceIds=['i-083fb7b1707d80af1'])
            

    return redirect("/home")

@manager.route('/delete-application-data', methods=['GET', 'POST'])
def delete_application_data():
    '''
    delete_application_data() - deletes all user application data from s3 and rds
    '''
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

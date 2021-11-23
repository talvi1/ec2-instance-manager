import boto3

from datetime import datetime, timedelta
from operator import itemgetter
from app.config import db_config_manager
import mysql.connector
from time import sleep

def connect_to_database_manager():
    return mysql.connector.connect(user=db_config_manager['user'], 
                                    password=db_config_manager['password'], 
                                    host=db_config_manager['host'],
                                    database=db_config_manager['database'])



def auto_scaler():
    '''
    auto_scaler() - automatically scales user instances based on average cpu utilization
    '''
    run = True
    sleep(4*60)
    while run:
        policy = get_policy()
        print('Running in ' + policy["scaling"] + ' mode.')
        if (policy["scaling"] == 'auto'):
            cpu_avg = get_worker_avg_cpu_util()
            print('CPU Utilization:' + str(cpu_avg))
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

            if cpu_avg > float(policy["cpu_incr"]):
                if (len(active_instances)+len(pending_instances)) == 6:
                    pass
                elif len(stopped_instances) == 0:
                    pass
                elif len(pending_instances) >=1:
                    pass
                else:
                    if int(policy["ratio_incr"]) == 1:
                        need_run = 1
                    else:
                        need_run = len(active_instances)*int(policy["ratio_incr"])

                    run = 0
                    if need_run < len(stopped_instances):
                        run = need_run
                    elif need_run >= len(stopped_instances):
                        run = len(stopped_instances)
                    for x in range(run):
                        add = stopped_instances.pop()
                        response = ec2_client.start_instances(InstanceIds=[add])
                        print('Started Instance:' + add)
            elif cpu_avg <= float(policy["cpu_decr"]):
                if (len(active_instances)) == 1:
                    pass
                elif len(stopping_instances) >=1:
                    pass
                else:
                    need_stop = int(len(active_instances)*int(policy["ratio_decr"])/100)
                    stop = 0
                    if need_stop < len(active_instances):
                        stop = need_stop
                    elif need_stop >= en(active_instances):
                        stop = len(stopped_instances)
                    for x in range(stop):
                        remove = active_instances.pop()
                        response = ec2_client.stop_instances(InstanceIds=[remove])
                        print('Stopped Instance:' + remove)
                

        elif (policy["scaling"] == 'manual'):
            pass
        publish_active_status()
        sleep(60)

def get_policy():
    policy = {"cpu_incr": 70, "cpu_decr": 30, "ratio_incr": 1, "ratio_decr": 1, 'scaling': 'auto'}
    con = connect_to_database_manager()
    cursor = con.cursor()
    query = '''SELECT * FROM scaling ORDER BY ID DESC LIMIT 1;'''                         
    cursor.execute(query,())
    result = cursor.fetchone()
    con.close()
    cursor.close()
    policy["cpu_incr"] = result[1]
    policy["cpu_decr"] = result[2]
    policy["ratio_incr"] = result[3]
    policy["ratio_decr"] = result[4]
    policy["scaling"] = result[5]
    return policy
    


def get_worker_avg_cpu_util():
    '''
    get_worker_avg_cpu_util() - gets average worker cpu utilization.
    '''
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
        Period=2 * 60,
        StartTime=datetime.utcnow() - timedelta(seconds=2 * 60),
        EndTime=datetime.utcnow() - timedelta(seconds=0 * 60),
        MetricName=metric_name,
        Namespace=namespace,  # Unit='Percent',
        Statistics=[statistic],
        Dimensions=[{'Name': 'InstanceId', 'Value': instance_id}]
        )])
    cpu_stats = []
    for x in range(len(cpu)):
        for point in cpu[x][1]['Datapoints']:
            cpu_stats.append(point['Average'])
    avg = sum(cpu_stats)/len(cpu_stats)
    return avg

def publish_active_status():
    ec2 = boto3.resource('ec2')
    ec2_client = boto3.client('ec2')
    instances = ec2.instances.all()
    active_instances = []
    for x, instance in enumerate(instances):
        if (instance.tags[0]['Key'] == 'worker' and instance.state['Name'] == 'running'):           
            active_instances.append(instance.instance_id)
    running = len(active_instances)
    con = connect_to_database_manager()
    cursor = con.cursor()
    time_now = datetime.utcnow()
    val = (running, time_now)
    query = "INSERT INTO workers (numworker, time) VALUES (%s, %s);"                        
    cursor.execute(query,val)
    con.commit()
    con.close()
    cursor.close()

auto_scaler()
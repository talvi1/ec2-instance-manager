import boto3
from datetime import datetime, timedelta
from operator import itemgetter



policy = {"cpu_incr": 70, "cpu_decr": 30, "ratio_incr": 1, "ratio_decr": 1}




def get_worker_avg_cpu_util():
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


x = get_worker_avg_cpu_util()
print(x)
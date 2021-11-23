from flask import Flask
import boto3

manager = Flask(__name__)

from app import index
from app import config
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
if (len(active_instances) == 0):
    add = stopped_instances.pop()
    response = ec2_client.start_instances(InstanceIds=[add])
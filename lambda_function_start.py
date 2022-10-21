# Start ECS clusters

import json
import boto3

def lambda_handler(event, context):
    # Scale up to minimumScalingStepSize all services in ECS clusters tagged as always-running == 'no'
    client = boto3.client('ecs')
    clusters = client.list_clusters()
    #print(f"\n{clusters}")
    for cluster_arn in clusters['clusterArns']:
        tags = client.list_tags_for_resource(resourceArn=cluster_arn)['tags']
        #print(f"\n{tags}")
        for tag in tags:
            if tag['key'] == 'always-running' and tag['value'] == 'no':
                cluster_id = cluster_arn.split("cluster/")[1]
                services = client.list_services(cluster=cluster_arn, launchType='FARGATE', schedulingStrategy='REPLICA')
                #print(f"\n{services}")
                for service_arn in services['serviceArns']:
                    print(f"\n{service_arn}")
                    service_id = "service/"+service_arn.split("service/")[1]
                    desired_count = getServiceMinCapacity(service_id)
                    response = client.update_service(
                        cluster=cluster_arn,
                        service=service_arn,
                        desiredCount=desired_count,
                    )
                    print(f"\n{response}")
                print('Started cluster: ', cluster_id)

    return {
        'statusCode': 200,
        'body': json.dumps('Script finished')
    }

def getServiceMinCapacity(service_id):
    # If there's a minimum capacity defined then return that value.
    # Otherwise, return the default value.
    client = boto3.client('application-autoscaling')
    response = client.describe_scalable_targets(
            ServiceNamespace='ecs',
            ResourceIds=[service_id])
            
    default = 1
    if "ScalableTargets" in response and len(response['ScalableTargets']) > 0 :
        target = response['ScalableTargets'][0]
        if 'MinCapacity' in target and 'MaxCapacity' in target:
            return target['MinCapacity']
    else:
        return default

# Stop ECS clusters

import json
import boto3

def lambda_handler(event, context):
    # Scale down to 0 all services in ECS clusters tagged as always-running == 'no'
    client = boto3.client('ecs')
    clusters = client.list_clusters()
    for cluster_arn in clusters['clusterArns']:
        tags = client.list_tags_for_resource(resourceArn=cluster_arn)['tags']
        #print(f"\n{tags}")
        for tag in tags:
            if tag['key'] == 'always-running' and tag['value'] == 'no':
                #print(f"\n{cluster_arn}")
                cluster_id = cluster_arn.split("cluster/")[1]
                services = client.list_services(cluster=cluster_arn, launchType='FARGATE', schedulingStrategy='REPLICA')
                #print(f"\n{services}")
                for service_arn in services['serviceArns']:
                    print(f"\n{service_arn}")        
                    responseUpdate = client.update_service(
                        cluster=cluster_arn,
                        service=service_arn,
                        desiredCount=0,
                    )
                    print(f"\n{responseUpdate}")
                print('Stopped cluster: ', cluster_id)

    return {
        'statusCode': 200,
        'body': json.dumps('Script finished')
    }

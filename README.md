# ECS Clusters: Stopping nightly & starting daily on working days

## About The Project

This project aims to show how to create scheduled rules in AWS EventBridge to automate every night the auto-shutdown and every day the startup of all ECS clusters on working days whose tag with key "always-running" has the value "no".
By turning off the clusters at night and weekends we can reduce the AWS bill.

## Prerequistes

In order to check AWS configurations and the creation of resources and services we'll need to install the AWS client application (See the links section).

For this project, we'll create a new AWS profile. If we name it "default" we won't need to referent it in all AWS CLI commands.
If you already have an AWS profile created for other purposes, backup your ~/.aws/config and ~/.aws/credentials files.

```sh
mkdir ~/.aws
echo -e "[profile default]\nregion = us-east-1\noutput = json" > ~/.aws/config
echo -e "[default]\naws_access_key_id = AWS_ACCESS_KEY >\naws_secret_access_key = AWS_SECRET_KEY" > ~/.aws/credentials
```

If you prefer to create your infrastructure in a different region than "us-east-1", feel free to change it in the config file.
Replace "AWS_ACCESS_KEY" and AWS_SECRET_KEY with yours.

To check the profile is correctly configured execute the command:
```sh
aws configure
```

We'll also need to install jq JSON processor, as we are going to manipulate AWS CLI output in JSON format.

## Instructions

### Create the ECS clusters

Manually launch two ECS instances. These instances will be used solely as a means to test our lambda functions.

You can create the ECS instances using the AWS ECS web dashboard. You might change the region with yours.
https://us-east-1.console.aws.amazon.com/ecs/v2/clusters?region=us-east-1

You can also do it using the AWS CLI application.

Define environment variables with proper values to create some demo ECS instances.
```sh
REGION=us-east-1
CLUSTER_NAME=ECSCluster1
CAPACITY_PROVIDERS="FARGATE"
TASKDEF_FILE=task-definition.json
TASKDEF_NAME=TaskDefApp
SERVICE_NAME=SrvApp
COUNT=1
LAUNCH_TYPE=FARGATE
SUBNET_ID=$(aws ec2 describe-subnets --filters "Name=availability-zone,Values=${REGION}a" | jq ".Subnets[].SubnetId" | sed 's/"//g')
GROUP_NAME=default
SECURITY_GROUP_ID=$(aws ec2 describe-security-groups --filters "Name=group-name,Values=$GROUP_NAME" | jq ".SecurityGroups[].GroupId" | sed 's/"//g')
TAG_NAME=always-running
TAG_VALUE=no
```

Check the environment variables to confirm they have the expected values.
```sh
echo $REGION
echo $CLUSTER_NAME
echo $CAPACITY_PROVIDERS
echo $TASKDEF_FILE
echo $TASKDEF_NAME
echo $SERVICE_NAME
echo $COUNT
echo $LAUNCH_TYPE
echo $SUBNET_ID
echo $GROUP_NAME
echo $SECURITY_GROUP_ID
echo $TAG_NAME
echo $TAG_VALUE
```

Create a cluster with fargate capacity provider with always-running == 'no'
```sh
aws ecs create-cluster --cluster-name $CLUSTER_NAME --capacity-providers $CAPACITY_PROVIDERS --tags key=$TAG_NAME,value=$TAG_VALUE
```

List all available ECS cluster
```sh
aws ecs list-clusters
```

Get the details of ECS cluster
```sh
aws ecs describe-clusters --cluster $CLUSTER_NAME
```

Register the task definition
```sh
aws ecs register-task-definition --cli-input-json file://$PWD/$TASKDEF_FILE
```

List all available task definitions
```sh
aws ecs list-task-definitions
```

Get the details of ECS cluster task definition
```sh
aws ecs describe-task-definition --task-definition $TASKDEF_NAME:1
```

Create a service in the ECS cluster using task definition
```sh
aws ecs create-service \
--cluster $CLUSTER_NAME \
--service-name $SERVICE_NAME \
--task-definition $TASKDEF_NAME:1 \
--desired-count $COUNT \
--launch-type $LAUNCH_TYPE \
--network-configuration "awsvpcConfiguration={subnets=[$SUBNET_ID],securityGroups=[$SECURITY_GROUP_ID],assignPublicIp=ENABLED}"
```

List all the available cluster services
```sh
aws ecs list-services --cluster $CLUSTER_NAME
```

Get the details of ECS cluster service
```sh
aws ecs describe-services --cluster $CLUSTER_NAME --services $SERVICE_NAME
```

List all the task in your cluster
```sh
aws ecs list-tasks --cluster $CLUSTER_NAME
```

Get details of task in your cluster
```sh
TASK_ARN=$(aws ecs list-tasks --cluster $CLUSTER_NAME --query 'taskArns' --output text)
aws ecs describe-tasks --cluster $CLUSTER_NAME --tasks $TASK_ARN
```

Let's create another ECS instance but with the tag value "yes" for key "always-running".
```sh
CLUSTER_NAME=ECSCluster2
TAG_VALUE=yes

aws ecs create-cluster --cluster-name $CLUSTER_NAME --capacity-providers $CAPACITY_PROVIDERS --tags key=$TAG_NAME,value=$TAG_VALUE
aws ecs describe-clusters --cluster $CLUSTER_NAME

aws ecs create-service \
--cluster $CLUSTER_NAME \
--service-name $SERVICE_NAME \
--task-definition $TASKDEF_NAME:1 \
--desired-count $COUNT \
--launch-type $LAUNCH_TYPE \
--network-configuration "awsvpcConfiguration={subnets=[$SUBNET_ID],securityGroups=[$SECURITY_GROUP_ID],assignPublicIp=ENABLED}"
aws ecs describe-services --cluster $CLUSTER_NAME --services $SERVICE_NAME

TASK_ARN=$(aws ecs list-tasks --cluster $CLUSTER_NAME --query 'taskArns' --output text)
aws ecs describe-tasks --cluster $CLUSTER_NAME --tasks $TASK_ARN
```

### Create the IAM rules and policies

In this project we need to create a policy and a role that will be used by our lambda functions to have permissions to access ECS resources.

You can create the rules and policies using the IAM web dashboard. You might change the region with yours.
https://us-east-1.console.aws.amazon.com/iamv2/home?region=us-east-1#/home

You can also do it using the AWS CLI application.

Define environment variables with values to create the IAM rule and its corresponding policy.
```sh
POLICY_NAME=LambdaStartStopEcsInstancesPolicy
ROLE_NAME=LambdaStartStopEcsInstancesRole
```

Check the environment variables to confirm they have the expected values.
```sh
echo $POLICY_NAME
echo $ROLE_NAME
```

Now we create our lambda IAM policy.
```sh
aws iam create-policy --policy-name $POLICY_NAME --policy-document file://$PWD/iam-policy.json
```

Let's check if the policy has been created correctly.
```sh
aws iam list-policies --scope Local --query "Policies[?PolicyName==\`$POLICY_NAME\`]"
```

We can catch the policy ARN from the last command output or get it executing the following:
```sh
POLICY_ARN=$(aws iam list-policies --scope Local --query "Policies[?PolicyName==\`$POLICY_NAME\`].{Arn: Arn}" | jq ".[].Arn" | sed 's/"//g')
```

Check its value.
```sh
echo $POLICY_ARN
```

We'll need the policy ARN to attach it later to the IAM role.

Now we create the lambda IAM role.
```sh
aws iam create-role --role-name $ROLE_NAME --assume-role-policy-document file://$PWD/trust-policy.json
```

We attach the permissions policy to the role.
```sh
aws iam attach-role-policy --policy-arn $POLICY_ARN --role-name $ROLE_NAME
```

Let's check if the role has been created correctly.
```sh
aws iam list-roles --query "Roles[?RoleName==\`$ROLE_NAME\`]"
```

We can catch the role ARN from the last command output or get it executing the following command:
```sh
ROLE_ARN=$(aws iam list-roles --query "Roles[?RoleName==\`$ROLE_NAME\`].{Arn: Arn}" | jq ".[].Arn" | sed 's/"//g')
```

Check its value.
```sh
echo $ROLE_ARN
```

We'll need the role ARN to create the lambda functions.

### Create the lambda functions

You can create the lambda functions using the AWS Lambda web dashboard. You might change the region with yours.
https://us-east-1.console.aws.amazon.com/lambda/home?region=us-east-1#/functions

You can also do it using the AWS CLI application.

We'll define some environment variables to create the Lambda functions.
```sh
FUNCTION_NAME=StopECSInstances
FUNCTION_FILE=function_stop.zip
HANDLER=lambda_function_stop.lambda_handler
RUNTIME=python3.7
TIMEOUT=60
```

Check the environment variables to confirm they have the expected values.
```sh
echo $FUNCTION_NAME
echo $FUNCTION_FILE
echo $HANDLER
echo $RUNTIME
echo $TIMEOUT
```

We'll create the Lambda function that stops nightly all ECS clusters tagged as always-running=no on working days.
Later we'll do the same with the Lambda that starts daily all ECS clusters tagged as always-running=no on working days.
The Python code is contained in files both lambda_function_stop.py and lambda_start.py.

We'll need to zip it in order to pass it to the Lambda function through the AWS CLI application.
```sh
zip $FUNCTION_FILE lambda_function_stop.py
```

Now we create the Lambda function.
```sh
aws lambda create-function --function-name $FUNCTION_NAME --zip-file fileb://$PWD/$FUNCTION_FILE --handler $HANDLER --runtime $RUNTIME --timeout $TIMEOUT --role $ROLE_ARN
```

Let's check if the function has been created correctly.
```sh
aws lambda list-functions --query "Functions[?FunctionName==\`$FUNCTION_NAME\`]"
```

We can catch the function ARN from the last command output or get it executing the following command:
```sh
STOP_FUNCTION_ARN=$(aws lambda list-functions --query "Functions[?FunctionName==\`$FUNCTION_NAME\`].{FunctionArn: FunctionArn}" | jq ".[].FunctionArn" | sed 's/"//g')
```

Check its value.
```sh
echo $STOP_FUNCTION_ARN
```

We'll need the function ARN to create the EventBridge rules.

Now we do the same for the start Lambda function:
```sh
FUNCTION_NAME=StartECSInstances
FUNCTION_FILE=function_start.zip
HANDLER=lambda_function_start.lambda_handler
zip $FUNCTION_FILE lambda_function_start.py
aws lambda create-function --function-name $FUNCTION_NAME --zip-file fileb://$PWD/$FUNCTION_FILE --handler $HANDLER --runtime $RUNTIME --timeout $TIMEOUT --role $ROLE_ARN
START_FUNCTION_ARN=$(aws lambda list-functions --query "Functions[?FunctionName==\`$FUNCTION_NAME\`].{FunctionArn: FunctionArn}" | jq ".[].FunctionArn" | sed 's/"//g')
echo $START_FUNCTION_ARN
```

### Create the EventBridge rules

We want to schedule event rules to execute the start Lambda function daily and the stop Lambda function nightly.

You can create the event rules using the Amazon EventBridge web dashboard. You might change the region with yours.
https://us-east-1.console.aws.amazon.com/events/home?region=us-east-1#/rules

You can also do it using the AWS CLI application.

We'll define some environment variables to create the event rules.
```sh
RULE_NAME=StopECSInstancesNightly
CRON_EXPRESSION='cron(0 21 ? * MON-FRI *)'
TARGET_ID=StopECSInstancesId
```

In the cron expression time is expressed in UTC.

Check the environment variables to confirm they have the expected values.
```sh
echo $RULE_NAME
echo $CRON_EXPRESSION
echo $TARGET_ID
```

Now we create the event rule to stop ECS clusters, and we add the corresponding Lambda function as target.

```sh
# Stop ECS clusters event rule
aws events put-rule --name $RULE_NAME --schedule-expression $CRON_EXPRESSION
aws events put-targets --rule $RULE_NAME --targets "Id"=$TARGET_ID,"Arn"=$STOP_FUNCTION_ARN
```

Add the resource-based policy statement for the event rule to the lambda function.
```sh
FUNCTION_NAME=StopECSInstances
RULE_NAME=StopECSInstancesNightly
aws lambda add-permission \
--function-name $FUNCTION_NAME \
--statement-id $RULE_NAME \
--action 'lambda:InvokeFunction' \
--principal events.amazonaws.com \
--source-arn $STOP_FUNCTION_ARN
```

Let's check if the function has been created correctly.
```sh
aws events list-rules --query "Rules[?Name==\`$RULE_NAME\`]"
```

List attached targets by rule:
```sh
aws events list-targets-by-rule --rule $RULE_NAME
```

We also create the event rule to start ECS clusters, and we add the corresponding Lambda function as target.

```sh
# Start ECS instances event rule
RULE_NAME=StartECSInstancesDaily
CRON_EXPRESSION='cron(0 5 ? * MON-FRI *)'
TARGET_ID=StartECSInstancesId
aws events put-rule --name $RULE_NAME --schedule-expression $CRON_EXPRESSION
aws events put-targets --rule $RULE_NAME --targets "Id"="$TARGET_ID","Arn"="$START_FUNCTION_ARN"
```

Add the resource-based policy statement for the event rule to the lambda function.
```sh
FUNCTION_NAME=StartECSInstances
RULE_NAME=StartECSInstancesDaily
aws lambda add-permission \
--function-name $FUNCTION_NAME \
--statement-id $RULE_NAME \
--action 'lambda:InvokeFunction' \
--principal events.amazonaws.com \
--source-arn $START_FUNCTION_ARN
```

Let's check if the function has been created correctly.
```sh
aws events list-rules --query "Rules[?Name==\`$RULE_NAME\`]"
```
List attached targets by rule:
```sh
aws events list-targets-by-rule --rule $RULE_NAME
```

### Test lambda functions

We might not wait until night or early in the morning to test our Lambda functions.
There's the option of executing the Lambda functions manually from the AWS Lambda web dashboard.
But we also want to check if EventBridge rules are working correctly.
We can change the cron expression to a time close to our current time (expressed in UTC time zone).

Let's change the cron expression for the StopECSInstancesNightly event rule to a different time.

```sh
RULE_NAME=StopECSInstancesNightly
CRON_EXPRESSION='cron(0 17 ? * * *)'
aws events put-rule --name $RULE_NAME --schedule-expression $CRON_EXPRESSION
```

We can list the service tasks and see if the ones corresponding to cluster with tag always-running=no have stopped.
```sh
CLUSTER_NAME=ECSCluster1
aws ecs list-tasks --cluster $CLUSTER_NAME
CLUSTER_NAME=ECSCluster2
aws ecs list-tasks --cluster $CLUSTER_NAME
```

The following command shows how to retrieve base64-encoded logs for Lambda function StopECSInstances.
```sh
FUNCTION_NAME=StopECSInstances
aws lambda invoke --function-name $FUNCTION_NAME out --log-type Tail --query 'LogResult' --output text | base64 -d
```

Let's change the cron expression for the StartECSInstancesDaily event rule to a different time.

```sh
RULE_NAME=StartECSInstancesDaily
CRON_EXPRESSION='cron(5 17 ? * * *)'
aws events put-rule --name $RULE_NAME --schedule-expression $CRON_EXPRESSION
```

We can list the service tasks and see if the ones corresponding to cluster with tag always-running=no have started.
```sh
CLUSTER_NAME=ECSCluster1
aws ecs list-tasks --cluster $CLUSTER_NAME
CLUSTER_NAME=ECSCluster2
aws ecs list-tasks --cluster $CLUSTER_NAME
```

Retrieve the base64-encoded logs for Lambda function StartECSInstances.
```sh
FUNCTION_NAME=StartECSInstances
aws lambda invoke --function-name $FUNCTION_NAME out --log-type Tail --query 'LogResult' --output text | base64 -d
```

Now we can finally set the cron expressions to their original values.
```sh
RULE_NAME=StopECSInstancesNightly
CRON_EXPRESSION='cron(0 21 ? * MON-FRI *)'
aws events put-rule --name $RULE_NAME --schedule-expression $CRON_EXPRESSION
RULE_NAME=StartECSInstancesDaily
CRON_EXPRESSION='cron(0 5 ? * MON-FRI *)'
aws events put-rule --name $RULE_NAME --schedule-expression $CRON_EXPRESSION
```

## Links
* AWS Free Tier: https://aws.amazon.com/free
* Installing or updating the latest version of the AWS CLI: https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html
* Install jq on Ubuntu 22.04: https://lindevs.com/install-jq-on-ubuntu

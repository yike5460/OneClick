
- [前言](#%e5%89%8d%e8%a8%80)
- [基本架构](#%e5%9f%ba%e6%9c%ac%e6%9e%b6%e6%9e%84)
- [Leaderboard的DynamoDB设计](#leaderboard%e7%9a%84dynamodb%e8%ae%be%e8%ae%a1)
  - [leaderboard table](#leaderboard-table)
  - [leaderboard GSI](#leaderboard-gsi)
- [安装步骤](#%e5%ae%89%e8%a3%85%e6%ad%a5%e9%aa%a4)
- [参考](#%e5%8f%82%e8%80%83)
- [License](#license)

## 前言

该代码库展示了如何利用无服务器服务实现将[DynamoDB流](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Streams.html "DynamoDB流")所触发的更新事件通过Lambda转发到[Amazon EventBridge](https://aws.amazon.com/eventbridge/ "Amazon EventBridge")事件总线，同时利用AWS SQS实现消息发送失败时的处理（死信队列）。需要提到目前架构下三种处理失败的消息会送到死信队列中：1）DynamoDB流触发的更新事件；2）所有针对Lambda失败的异步调用; 3)Lambda本身处理的失败事件。发送到Amazon EventBridge的消息，我们通过相应的规则分发到对应的Lambda函数实现后端Leaderboard表项的更新，Firehose的数据备份，最后我们还自动生成了对应的API GW和leaderGetLambda来实现该Leaderboard表项的查询。

## 基本架构

```shell
DDB Stream->fanoutLambda->EventBridge->Firehose->S3
                 |
                 |->consumerLambda->Leaderboard DDB
                                           |
API GW--------------GET-------------leaderGetLambda
```
DynamoDB表中的插入，更新和删除等操作通过DynamoDB流捕获，并用于触发AWS Lambda函数或其他后端服务（消费者）。目前单个DynamoDB流分片所能触发的后端服务（消费者）不能超过两个，超出部分将被限流。该代码库利用DynamoDB流触发后端Lambda函数，该Lambda函数捕获流事件并将其发布到Amazon EventBridge事件总线以触发数倍的后端服务（消费者），同时Lambda函数如果在所配置的重试次数之内无法将事件发布到Amazon EventBridge事件总线，它将把消息发送到SQS死信队列，用于后续调查定位。

## Leaderboard的DynamoDB设计
目前主表的分区键和排序键分别是id和metadata，我们采用N：M的设计模式来考虑Leaderboard表的设计。Leaderboard使用同样的id（跟参与者一一对应）作为分区键，projectScore，hackathonName作为属性（attribute），同时新建GSI，使用hackathonName作为分区键，projectScore作为排序键。
一句话，you have that attribute as a sort (RANGE) key within the given partition (HASH) key that you want to sort.

### leaderboard table
| Id  | metaData (hackathonName)  | projectScore  | userName  |
| ------------ | ------------ | ------------ | ------------ |
| 1  | StarWar  | 60  | userA  |
| 2  | StarWar  | 90  | userB  |
| 3  | StarWar  | 70  | userC  |
| 4  | WarCraft  | 100  | userD  |

### leaderboard GSI
| metaData (hackathonName)  | projectScore  | userName  |
| ------------ | ------------ | ------------ |
| StarWar  | 90  | userB  |
| StarWar  | 70  | userC  |
| StarWar  | 60  | userA  |
| WarCraft  | 100  | userD  |

## 安装步骤
在此我们会利用到SAM工具来实现关键服务的模版编排，编译测试和一键部署。[了解什么是SAM](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/what-is-sam.html "了解什么是SAM")以及如何[安装SAM](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-sam-cli-install.html "安装SAM")

步骤一：
确保您的SAM版本已是最新。
```shell
bash-3.2$ brew upgrade aws-sam-cli
bash-3.2$ sam --version
SAM CLI, version 0.47.0
```
创建您的AWS EventBridge事件总线，这里我们默认名称是fanoutBus
![Create EventBridge](https://github.com/yike5460/SAM/blob/master/img/Create-EventBridge.png)

步骤二：
编译并本地测试，其中的dynamodbStream.json为模拟DynamoDB流触发Lambda函数传递的event事件，包括数据的插入，更新和删除操作，利用SAM提供的本地镜像我们可以实现FanoutLambda函数的基本功能；XXXevent.json为模拟EventBridge传到后端消费服务的event事件，实现ConsumerLambda函数的进一步验证；apigw.json为对应的api gw发送过来的LeaderBoard查询事件，实现基本的Get功能测试。
```shell
bash-3.2$ sam build
bash-3.2$ sam local invoke "FanoutLambda" -e events/dynamodbStream.json
bash-3.2$ sam local invoke "ConsumerLambda" -e events/insertEvent.json
bash-3.2$ sam local invoke "ConsumerLambda" -e events/updateEvent.json
bash-3.2$ sam local invoke "ConsumerLambda" -e events/deleteEvent.json
bash-3.2$ sam local invoke "LeaderGet" -e events/apigw.json
```
您也可以通过如下命令生成自己的测试文件custom.json
```shell
bash-3.2$ sam local generate-event dynamodb update > events/custom.json
```

步骤三：
创建相应dynamoDB并使能DynamoDB流功能，记录下该DynamoDB流的ARN。该范例的dynamoDB为存储hackathon所有数据的主表。
![Create-DynamoDB-Stream](https://github.com/yike5460/SAM/blob/master/img/Create-DynamoDB-Stream.png)

准备部署所需参数，该模版包含以下参数：
1. DynamoDBStreamArn（必须），源DynamoDB流的ARN
2. EventBusName（必须），默认为fanoutBus，这里需要跟您之前创建的EventBridge事件总线名称一致
3. EventBridgeMaxAttempt（可选），Lambda将消息发送至EventBridge的重试次数

接下来部署服务，加入-g选项按照提示输入上述的模版参数
```shell
bash-3.2$ sam deploy -g
```
输出如下，其中FanoutDlqUrl为我们所创建的SQS死信队列，FanoutLambdaName为创建的实现消息Fanout的Lambda函数，ConsumerLambdaName为创建的接受EventBridge消息的后端消费服务。该示例中默认创建的EventBridge规则的源是“update.aws.dynamodb"，EventBridge根据该规则源将消息分发到对应的消费者ConsumerLambdaName，您也可以新增例如“operations.aws.dynamodb"的规则源来实现将不同的消息分发至其他消费者（如Firehose）。注意我们在fanout.py中我们也留下了部分注释的示例代码供您参考或直接放开来定制EventBridge的规则和目标，实现总线消息基于不同规则向不同消费者服务的分发（比如Firehose）。
```shell
------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
Outputs                                                                                                                                                                                              
------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
Key                 LeaderGet                                                                                                                                                                        
Description         LeaderGet function ARN                                                                                                                                                           
Value               arn:aws:lambda:ap-northeast-1:275937937240:function:fanout-LeaderGet-1HC6L64I7XI1A                                                                                               

Key                 LeaderGetIamRole                                                                                                                                                                 
Description         Implicit IAM Role created for LeaderGet function                                                                                                                                 
Value               arn:aws:iam::275937937240:role/fanout-LeaderGetRole-1C81F0QKL73TQ                                                                                                                

Key                 FanoutDlqUrl                                                                                                                                                                     
Description         Fanout DLQ URL                                                                                                                                                                   
Value               https://sqs.ap-northeast-1.amazonaws.com/275937937240/fanout-FanoutDLQ-1EUF4FXCD6NTS                                                                                             

Key                 LeaderGetApi                                                                                                                                                                     
Description         API Gateway endpoint URL for hack stage for LeaderGet function                                                                                                                   
Value               https://8xueetl87e.execute-api.ap-northeast-1.amazonaws.com/Prod/leaderBoard/                                                                                                    

Key                 ConsumerLambdaName                                                                                                                                                               
Description         Consumer Lambda Function Name                                                                                                                                                    
Value               fanout-ConsumerLambda-OL903LCB7J6N                                                                                                                                               

Key                 FanoutLambdaName                                                                                                                                                                 
Description         Fanout Lambda Function Name                                                                                                                                                      
Value               fanout-FanoutLambda-INLLGSJCVOT8                                                                                                                                                 
------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

Successfully created/updated stack - fanout in ap-northeast-1

步骤四：
为了让Lambda能自动创建EventBridge，在上步命令部署完毕后，我们需要更新已部署的Lambda的名为‘FanoutLambdaRolePolicy1’的IAM内联策略（仅测试）
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "VisualEditor0",
            "Effect": "Allow",
            "Action": "events:*",
            "Resource": "*"
        }
    ]
}
```
注意在版本更新后，我们在SAM模版中自动实现了该权限的添加，新的版本可以跳过上述步骤四

## 功能测试
尝试在您之前创建的DynamoDB中进行表项的新增，更新或者删除操作，通过Lambda集成的CloudWatch查看DynamoDB流事件是否正常触发到您的FanoutLambda，进一步查看ConsumerLambda的调试输出查看EventBridge的分发消息是否正常到达。
SAM提供了查看相应部署资源的log的功能，比如通过如下命令可以实时查看部署的Lambda函数的调试输出
```shell
bash-3.2$ sam logs -n ConsumerLambda --stack-name fanout -t --region ap-northeast-1
...
2020/04/15/[$LATEST]7c00236741094fc2ab323c56ff114e6d 2020-04-15T08:26:16.542000 [INFO]  2020-04-15T08:26:16.542Z        e066d271-31fd-44d7-9cc8-0a0c91873b70    update item successful
2020/04/15/[$LATEST]7c00236741094fc2ab323c56ff114e6d 2020-04-15T08:26:16.542000 [INFO]  2020-04-15T08:26:16.542Z        e066d271-31fd-44d7-9cc8-0a0c91873b70    {
    "ResponseMetadata": {
        "RequestId": "OLPN7IK9BFAUEF8HDF1Q80EKIBVV4KQNSO5AEMVJF66Q9ASUAAJG",
        "HTTPStatusCode": 200,
        "HTTPHeaders": {
            "server": "Server",
            "date": "Wed, 15 Apr 2020 08:26:16 GMT",
            "content-type": "application/x-amz-json-1.0",
            "content-length": "2",
            "connection": "keep-alive",
            "x-amzn-requestid": "OLPN7IK9BFAUEF8HDF1Q80EKIBVV4KQNSO5AEMVJF66Q9ASUAAJG",
            "x-amz-crc32": "2745614147"
        },
        "RetryAttempts": 0
    }
}
2020/04/15/[$LATEST]7c00236741094fc2ab323c56ff114e6d 2020-04-15T08:26:16.556000 END RequestId: e066d271-31fd-44d7-9cc8-0a0c91873b70
2020/04/15/[$LATEST]7c00236741094fc2ab323c56ff114e6d 2020-04-15T08:26:16.556000 REPORT RequestId: e066d271-31fd-44d7-9cc8-0a0c91873b70  Duration: 21.39 ms      Billed Duration: 100 msMemory Size: 256 MB     Max Memory Used: 72 MB
...
```
最后您可以看到所有在主表的新增，更新或者删除操作都会同步更新到我们的leaderboard表项。

## 参考

1. [Leaderboard的设计模式](https://aws.amazon.com/blogs/database/amazon-dynamodb-gaming-use-cases-and-design-patterns/ "Leaderboard的设计模式")

## License
This project is licensed under the Apache-2.0 License.
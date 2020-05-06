# SMS function
目前方案的后端可以选择[SNS(Simple Notification Service)](https://aws.amazon.com/sns/ "SNS(Simple Notification Service)")或者[Pinpoint](https://aws.amazon.com/pinpoint/ "Pinpoint")来实现，通过部署时参数输入来选择何种服务实现。两者均能实现短信消息的发送功能，细节差异如下表：
|   | 可用区域 | 发送状态 | 短信模版 | 语音 | 双向SMS消息 | 批量发送 |
| ------------ | ------------ | ------------ | ------------ | ------------ | ------------ | ------------ |
| SNS  | 全球可用，国内的SNS下的SMS待定 | 仅有HTTPStatusCode | 暂未支持  | 暂未支持 | 暂未支持 | 需要API实现 |
| Pinpoint | 目前6个可用区域，地域最近的是孟买和悉尼 | DeliveryStatus和StatusCode | 支持  | 支持 | 支持 | 需要API实现 |

注意Pinpoint有金额的限制，会影响能可发送短信的数量。点击此处[了解如何提高该限额](https://docs.aws.amazon.com/pinpoint/latest/userguide/channels-sms-awssupport-spend-threshold.html "了解如何提高该限额")

## install SAM
在此我们会利用到SAM工具来实现关键服务的模版编排，编译测试和一键部署。[了解什么是SAM](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/what-is-sam.html "了解什么是SAM")以及如何[安装SAM](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-sam-cli-install.html "安装SAM")

确保您的SAM版本已是最新(MACOS为例)。
```shell
bash-3.2$ brew upgrade aws-sam-cli
bash-3.2$ sam --version
SAM CLI, version 0.47.0
```
## 部署Pinpoint
新建Pinpoint项目，在General settings中勾选Enable the SMS channel for this project，其中的Account spending limit设置为最大值1，后续我们需要通过support的方式提升限额以作为生产环境使用，最后记录下该Project ID，类似1d205f0b0bb54f1a8499e1e60ce7f553这样的字符串

## 部署SAM（API Gateway，Lambda）
```shell
# sam build && sam local invoke "EventFanout" -e events/event.json
# sam deploy -g (其中SNSorPinpoint输入SNS或者Pinpoint，PinPointID输入您刚才创建的Project ID，注意您如果不用Pinpoint的话该选项可以忽略)
```
部署完毕后您会看到类似的输出，其中Value后的URL就是后续短信功能调用的URL。
```html
---------------------------------------------------------------------------------------------------------------------------
Outputs                                                                                                                   
---------------------------------------------------------------------------------------------------------------------------
...
Key                 SmsSendApiUrl                                                                                         
Description         API Gateway endpoint URL for Prod stage for SMS sending function                                      
Value               https://<xxxx>.execute-api.us-west-2.amazonaws.com/Prod/sms/                                      
---------------------------------------------------------------------------------------------------------------------------

```

## IAM policy （如果您选择Pinpoint作为后端发送服务，目前需要手动设置此项）
create Pinpoint policy and attach to deployed Lambda function manually
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "VisualEditor0",
            "Effect": "Allow",
            "Action": "mobiletargeting:*",
            "Resource": "*"
        }
    ]
}
```

## send SMS directly
其中URL为您部署的API Gateway所输出的URL，它作为您触发短信发送的RESFUL入口，目前仅支持POST操作
```shell
curl -H "Content-Type:application/json" -X POST -d '{"Number": "+123456", "SMS": "Test message from AWS!"}' https://<xxxx>.execute-api.us-west-2.amazonaws.com/Prod/sms
```
您也可以通过Postman来操作，见下图所示
![Postman](https://github.com/yike5460/OneClick/blob/master/sms/img/postman.png)
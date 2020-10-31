# 方案特性
- 短信发送
- 短信状态回执
其中短信状态回执信息的具体释义参见[sms属性](https://docs.aws.amazon.com/zh_cn/pinpoint/latest/developerguide/event-streams-data-sms.html#event-streams-data-sms-attributes "sms属性")

# 方案架构


# 方案部署
目前方案的后端可以选择[SNS(Simple Notification Service)](https://aws.amazon.com/sns/ "SNS(Simple Notification Service)")或者[Pinpoint](https://aws.amazon.com/pinpoint/ "Pinpoint")来实现，通过部署时参数输入来选择何种服务实现。两者均能实现短信消息的发送功能，细节差异如下表：
|   | 可用区域 | 发送状态 | 短信模版 | 语音 | 双向SMS消息 | 批量发送 |
| ------------ | ------------ | ------------ | ------------ | ------------ | ------------ | ------------ |
| SNS | 全球可用，国内的SNS下的SMS待定 | 仅有HTTPStatusCode | 暂未支持 | 暂未支持 | 暂未支持 | 需要API实现 |
| Pinpoint | 目前6个可用区域，地域最近的是孟买和悉尼 | DeliveryStatus和StatusCode，短信状态回执 | 支持 | 支持 | 支持 | 需要API实现 |

注意Pinpoint有金额的限制，会影响能可发送短信的数量。点击此处[了解如何提高该限额](https://docs.aws.amazon.com/pinpoint/latest/userguide/channels-sms-awssupport-spend-threshold.html "了解如何提高该限额")

目前该方案AWS Pinpoint服务限制如下：

![voiceQuota](https://github.com/yike5460/OneClick/blob/master/sms/img/voiceQuota.png)

![smsQuota](https://github.com/yike5460/OneClick/blob/master/sms/img/smsQuota.png)

点击此处[了解限额细节](https://docs.aws.amazon.com/zh_cn/pinpoint/latest/developerguide/quotas.html "了解限额细节")

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
# 测试短信发送
# sam build && sam local invoke "SMSGatewayFunction" -e events/httpAPI.json
# 测试短信模版创建
# sam build && sam local invoke "SMSGatewayFunction" -e events/createTemplate.json
# 测试短信回执
# sam build && sam local invoke "SMSDeliveryReceiptFunction" -e events/kinesis.json
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

## IAM policy （如果您选择Pinpoint作为后端发送服务，目前已经自动设置，可以忽略）
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

## Pinpoint stream event设置
将stream event设置为SAM创建好的Kinesis Data Stream，同时自动创建IAM Role

## VPC的创建（挂载到消息回执的Lambda函数）
通过wizard创建public和private vpc，记录对应的subnet id和security group id，用作SAM模版的参数。该配置的作用目前用于方便客户段白名单IP地址的配置，由于短信消息的回执状态需要通过URL POST的方式发送到客户指定的URL，白名单的方案意味着需要针对所有Lambda的源地址实现白名单，由于目前Lambda的IP网段同EC2网段复用，客户端的白名单将是一个巨大的量级，通过VPC+NAT Gatewa的方式只需要将NAT Gateway绑定的弹性IP加入到白名单即可。另外一种方式是客户端在每个region额外开启EC2实例来规避白名单造成的特性实现限制和额外费用开销。

## 通过HTTP接口发送短信
其中URL为您部署的API Gateway所输出的URL，它作为您触发短信发送的RESFUL入口，目前仅支持POST操作
```shell
curl --location --request POST 'https://xxxx.execute-api.us-west-2.amazonaws.com/Prod/sms?PhoneNumbers=+xxxx&SignName&TemplateCode&AccessKeyId&Action=&OutId=&SmsUpExtendCode=&TemplateParam=' \
--header 'X-Amz-Content-Sha256: xxxx' \
--header 'X-Amz-Date: 20200828T102741Z' \
--header 'Authorization: AWS4-HMAC-SHA256 Credential=xxxx/20200828/us-west-2/execute-api/aws4_request, SignedHeaders=host;x-amz-content-sha256;x-amz-date, Signature=xxxx' \
--header 'Content-Type: text/plain' \
--data-raw '<your short message to send>'
```

您也可以通过Postman来操作，见下图所示
![Postman](https://github.com/yike5460/OneClick/blob/master/sms/img/postman.png)

## 通过HTTP接口发送短信（批量发送）
```shell
curl --location --request POST 'https://xxxx.execute-api.us-west-2.amazonaws.com/Prod/smsBatch?PhoneNumberJson=[%22+xxxx%22,%22+xxxx%22]&SignNameJson&TemplateCode&AccessKeyId&Action=&OutId=&SmsUpExtendCodeJson=&TemplateParamJson=' \
--header 'X-Amz-Content-Sha256: xxxx' \
--header 'X-Amz-Date: 20200830T135441Z' \
--header 'Authorization: AWS4-HMAC-SHA256 Credential=xxxx/20200830/us-west-2/execute-api/aws4_request, SignedHeaders=host;x-amz-content-sha256;x-amz-date, Signature=xxxx' \
--header 'Content-Type: text/plain' \
--data-raw '<your short message to send>'
```

您也可以通过Postman来操作，见下图所示
![PostmanBatch](https://github.com/yike5460/OneClick/blob/master/sms/img/postmanBatch.png)

## 通过HTTP接口创建短信模版
```shell
curl --location --request POST 'https://xxxx.execute-api.us-west-2.amazonaws.com/Prod/smsTemplateCreate?TemplateType=0&TemplateName=AWSTemplateLambda&TemplateContent=content%20for%20AWS%20template&Remark=demo%20usage&Action=smsTemplateCreate&AccessKeyId=' \
--header 'X-Amz-Content-Sha256: xxxx' \
--header 'X-Amz-Date: 20200831T044404Z' \
--header 'Authorization: AWS4-HMAC-SHA256 Credential=xxxx/20200831/us-west-2/execute-api/aws4_request, SignedHeaders=host;x-amz-content-sha256;x-amz-date, Signature=xxxx' \
--header 'Content-Type: text/plain' \
--data-raw 'AWS Test Message'
```

您也可以通过Postman来操作，见下图所示
![PostmanCreateTemplate](https://github.com/yike5460/OneClick/blob/master/sms/img/postmanCreateTemplate.png)

您可以通过内置的Lambda函数实现短信回执消息自动发送到服务接收端，也可以通过手动的方式利用postman进行测试服务端的功能，见下图所示
![receiveStatusSend](https://github.com/yike5460/OneClick/blob/master/sms/img/receiveStatusSend.png)


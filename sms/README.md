# SMS function
注意目前这个方案Pinpoint有金额的限制，会影响能发送短信的数量。点击此处[了解如何提高该限额](https://docs.aws.amazon.com/pinpoint/latest/userguide/channels-sms-awssupport-spend-threshold.html "了解如何提高该限额")

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
sam build && sam local invoke "EventFanout" -e events/event.json
sam deploy -g (输入Project ID作为入参)
```
登陆到您的API gateway界面然后部署该API Gateway（Prod stage）

## IAM policy
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
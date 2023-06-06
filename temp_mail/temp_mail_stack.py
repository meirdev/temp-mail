import aws_cdk as cdk
from aws_cdk import (
    Stack,
    aws_apigatewayv2 as apigw,
    aws_dynamodb as ddb,
    aws_iam as iam,
    aws_lambda as _lambda,
    aws_lambda_event_sources as event_sources,
    aws_sns as sns,
)
from constructs import Construct


class TempMailStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        TTL = 60 * 10
        DOMAIN = "YOUR_DOMAIN"

        topic_messages = sns.Topic(
            self, "temp-mail-topic",
        )

        table_messages = ddb.Table(
            self, "temp-mail-messages",
            partition_key=ddb.Attribute(
                name="destination",
                type=ddb.AttributeType.STRING,
            ),
            sort_key=ddb.Attribute(
                name="timestamp",
                type=ddb.AttributeType.STRING,
            ),
            billing_mode=ddb.BillingMode.PAY_PER_REQUEST,
            time_to_live_attribute="ttl",
            removal_policy=cdk.RemovalPolicy.DESTROY,
        )

        table_mails = ddb.Table(
            self, "temp-mail-mails",
            partition_key=ddb.Attribute(
                name="mail",
                type=ddb.AttributeType.STRING,
            ),
            billing_mode=ddb.BillingMode.PAY_PER_REQUEST,
            time_to_live_attribute="ttl",
            removal_policy=cdk.RemovalPolicy.DESTROY,
        )

        table_mails.add_global_secondary_index(
            index_name="temp-mail-user-mail-index",
            partition_key=ddb.Attribute(
                name="user",
                type=ddb.AttributeType.STRING,
            ),
            projection_type=ddb.ProjectionType.ALL,
        )

        lambda_save_message = _lambda.Function(
            self, "temp-mail-save-message",
            runtime=_lambda.Runtime.PYTHON_3_10,
            code=_lambda.Code.from_asset("lambda"),
            handler="save_message.handler",
            environment={
                "MESSAGES_TABLE_NAME": table_messages.table_name,
                "TTL": str(TTL),
            },
        )

        table_messages.grant_write_data(lambda_save_message)

        lambda_generate_mail = _lambda.Function(
            self, "temp-mail-generate-mail",
            runtime=_lambda.Runtime.PYTHON_3_10,
            code=_lambda.Code.from_asset("lambda"),
            handler="generate_mail.handler",
            environment={
                "MAILS_TABLE_NAME": table_mails.table_name,
                "DOMAIN": DOMAIN,
                "TTL": str(TTL),
            },
        )

        table_mails.grant_read_write_data(lambda_generate_mail)

        lambda_check_inbox = _lambda.Function(
            self, "temp-mail-check-inbox",
            runtime=_lambda.Runtime.PYTHON_3_10,
            code=_lambda.Code.from_asset("lambda"),
            handler="check_inbox.handler",
            environment={
                "MESSAGES_TABLE_NAME": table_messages.table_name,
            },
        )

        table_messages.grant_read_write_data(lambda_check_inbox)

        lambda_verify_user = _lambda.Function(
            self, "temp-mail-verify-user",
            runtime=_lambda.Runtime.PYTHON_3_10,
            code=_lambda.Code.from_asset("lambda"),
            handler="verify_user.handler",
            environment={
                "MAILS_TABLE_NAME": table_mails.table_name,
            },
        )

        table_mails.grant_read_data(lambda_verify_user)

        api = apigw.CfnApi(
            self, "temp-mail-api",
            protocol_type="HTTP",
            name="temp-mail-api",
        )

        route_generate_mail = apigw.CfnRoute(
            self, "temp-mail-route-generate-mail",
            api_id=api.ref,
            route_key="POST /mail",
        )

        integration = apigw.CfnIntegration(
            self, "temp-mail-integration-generate-mail",
            api_id=api.ref,
            integration_type="AWS_PROXY",
            integration_uri=lambda_generate_mail.function_arn,
            payload_format_version="2.0",
        )

        route_generate_mail.add_property_override(
            "Target", f"integrations/{integration.ref}",
        )

        auth = apigw.CfnAuthorizer(
            self, "temp-mail-authorizer",
            api_id=api.ref,
            name="temp-mail-authorizer",
            authorizer_payload_format_version="2.0",
            authorizer_type="REQUEST",
            authorizer_uri=f"arn:aws:apigateway:{self.region}:lambda:path/2015-03-31/functions/{lambda_verify_user.function_arn}/invocations",
            identity_source=["$request.header.Authorization"],
            enable_simple_responses=True,
        )

        route_check_inbox = apigw.CfnRoute(
            self, "temp-mail-route-check-inbox",
            api_id=api.ref,
            route_key="GET /mail/inbox",
            authorization_type="CUSTOM",
            authorizer_id=auth.ref,
        )

        integration = apigw.CfnIntegration(
            self, "temp-mail-integration-check-inbox",
            api_id=api.ref,
            integration_type="AWS_PROXY",
            integration_uri=lambda_check_inbox.function_arn,
            payload_format_version="2.0",
        )

        route_check_inbox.add_property_override(
            "Target", f"integrations/{integration.ref}",
        )

        lambda_generate_mail.add_permission(
            "temp-mail-generate-mail-permission",
            principal=iam.ServicePrincipal("apigateway.amazonaws.com"),
            action="lambda:InvokeFunction",
            source_arn=f"arn:aws:execute-api:{self.region}:{self.account}:*",
        )

        lambda_check_inbox.add_permission(
            "temp-mail-check-inbox-permission",
            principal=iam.ServicePrincipal("apigateway.amazonaws.com"),
            action="lambda:InvokeFunction",
            source_arn=f"arn:aws:execute-api:{self.region}:{self.account}:*",
        )

        lambda_verify_user.add_permission(
            "temp-mail-verify-user-permission",
            principal=iam.ServicePrincipal("apigateway.amazonaws.com"),
            action="lambda:InvokeFunction",
            source_arn=f"arn:aws:execute-api:{self.region}:{self.account}:*",
        )

        lambda_save_message.add_event_source(
            event_sources.SnsEventSource(topic_messages),
        )

        apigw.CfnStage(
            self, "temp-mail-stage",
            api_id=api.ref,
            stage_name="prod",
            auto_deploy=True,
        )

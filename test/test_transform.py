import pytest
import boto3
import os
from moto import mock_aws
from src.lambda_functions.transform import lambda_handler as transform


@pytest.fixture(scope="function")
def aws_credentials():
    """Mocked AWS Credentials for S3 bucket."""
    os.environ["AWS_ACCESS_KEY_ID"] = "test"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "test"
    os.environ["AWS_SECURITY_TOKEN"] = "test"
    os.environ["AWS_SESSION_TOKEN"] = "test"
    os.environ["AWS_DEFAULT_REGION"] = "eu-west-2"


@pytest.fixture(scope="function")
def s3(aws_credentials):
    """Mocked S3 client with raw data bucket."""
    with mock_aws():
        s3 = boto3.client("s3")
        s3.create_bucket(
            Bucket="totesys-raw-data-000000",
            CreateBucketConfiguration={"LocationConstraint": "eu-west-2"},
        )
        s3.create_bucket(
            Bucket="totesys-processed-data-000000",
            CreateBucketConfiguration={"LocationConstraint": "eu-west-2"},
        )
        yield s3


class DummyContext:  # Dummy context class used for testing
    pass


event = {"time_prefix": "YYYY/MM/DD/HH:MM:SS/"}
context = DummyContext()


class TestTransform:

    @pytest.mark.it("parquet data lands in the processed bucket")
    def test_transform_lands_data_in_processed_data_bucket(self, s3):

        s3.put_object(
            Body="""test,test2,test3
                    1,2,3
                    5,6,7
                    8,9,10""",
            Bucket="totesys-raw-data-000000",
            Key="/history/YYYY/MM/DD/HH:MM:SS/sales_order.csv",
        )
        s3.put_object(
            Body="""test,test2,test3
                    1,2,3
                    5,6,7
                    8,9,10""",
            Bucket="totesys-raw-data-000000",
            Key="/history/YYYY/MM/DD/HH:MM:SS/design.csv",
        )
        s3.put_object(
            Body="""test,test2,test3
                    1,2,3
                    5,6,7
                    8,9,10""",
            Bucket="totesys-raw-data-000000",
            Key="/history/YYYY/MM/DD/HH:MM:SS/currency.csv",
        )
        s3.put_object(
            Body="""test,test2,test3
                    1,2,3
                    5,6,7
                    8,9,10""",
            Bucket="totesys-raw-data-000000",
            Key="/history/YYYY/MM/DD/HH:MM:SS/staff.csv",
        )
        s3.put_object(
            Body="""test,test2,test3
                    1,2,3
                    5,6,7
                    8,9,10""",
            Bucket="totesys-raw-data-000000",
            Key="/history/YYYY/MM/DD/HH:MM:SS/counterparty.csv",
        )
        s3.put_object(
            Body="""test,test2,test3
                    1,2,3
                    5,6,7
                    8,9,10""",
            Bucket="totesys-raw-data-000000",
            Key="/history/YYYY/MM/DD/HH:MM:SS/address.csv",
        )
        s3.put_object(
            Body="""test,test2,test3
                    1,2,3
                    5,6,7
                    8,9,10""",
            Bucket="totesys-raw-data-000000",
            Key="/history/YYYY/MM/DD/HH:MM:SS/department.csv",
        )
        s3.put_object(
            Body="""test,test2,test3
                    1,2,3
                    5,6,7
                    8,9,10""",
            Bucket="totesys-raw-data-000000",
            Key="/history/YYYY/MM/DD/HH:MM:SS/purchase_order.csv",
        )
        s3.put_object(
            Body="""test,test2,test3
                    1,2,3
                    5,6,7
                    8,9,10""",
            Bucket="totesys-raw-data-000000",
            Key="/history/YYYY/MM/DD/HH:MM:SS/payment_type.csv",
        )
        s3.put_object(
            Body="""test,test2,test3
                    1,2,3
                    5,6,7
                    8,9,10""",
            Bucket="totesys-raw-data-000000",
            Key="/history/YYYY/MM/DD/HH:MM:SS/payment.csv",
        )
        s3.put_object(
            Body="""test,test2,test3
                    1,2,3
                    5,6,7
                    8,9,10""",
            Bucket="totesys-raw-data-000000",
            Key="/history/YYYY/MM/DD/HH:MM:SS/transaction.csv",
        )

        expected_pq = {
            "/history/YYYY/MM/DD/HH:MM:SS//address.parquet": 0,
            "/history/YYYY/MM/DD/HH:MM:SS//design.parquet": 0,
            "/history/YYYY/MM/DD/HH:MM:SS//currency.parquet": 0,
            "/history/YYYY/MM/DD/HH:MM:SS//staff.parquet": 0,
            "/history/YYYY/MM/DD/HH:MM:SS//counterparty.parquet": 0,
            "/history/YYYY/MM/DD/HH:MM:SS//sales_order.parquet": 0,
            "/history/YYYY/MM/DD/HH:MM:SS//department.parquet": 0,
            "/history/YYYY/MM/DD/HH:MM:SS//purchase_order.parquet": 0,
            "/history/YYYY/MM/DD/HH:MM:SS//payment_type.parquet": 0,
            "/history/YYYY/MM/DD/HH:MM:SS//payment.parquet": 0,
            "/history/YYYY/MM/DD/HH:MM:SS//transaction.parquet": 0,
        }

        res = transform(event, context)
        proc_data_bucket_objects = s3.list_objects(
            Bucket="totesys-processed-data-000000"
        )["Contents"]

        for parquet in proc_data_bucket_objects:
            assert parquet["Key"] in expected_pq

        assert res == {"time_prefix": "YYYY/MM/DD/HH:MM:SS/"}

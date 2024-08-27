import boto3
import logging
import os
import csv
import json
import re
import subprocess
from datetime import datetime as dt
from pg8000.native import Connection, Error
from botocore.exceptions import ClientError
from io import StringIO

#for debugging
CSV_REGEX = r">\s*([A-Za-z0-9\.@:\-_\s,:]+)(?=\s\d+c\d+)|>\s*([A-Za-z0-9\.@:\-_\s,:]+)(?=\s\\)|>\s*([A-Za-z0-9\.@:\-_\s,:]+)(?=\s>)"

HISTORY_PATH = "/history/" 
SOURCE_PATH = "/source/"
SOURCE_FILE_SUFFIX = "_new"
DIFFERENCES_FILE_SUFFIX = "_differences"
DATA_TABLES = [
    "sales_order",
    "design",
    "currency",
    "staff",
    "counterparty",
    "address",
    "department",
    "purchase_order",
    "payment_type",
    "payment",
    "transaction",
]

def create_time_based_path():
    """
    Retrieves the current time at which the lambda function is invoked for use in
    the file structure and in returning a value for the lambda handler
    """
    current_time = dt.now()
    year = current_time.year
    month = current_time.month
    day = current_time.day
    hour = current_time.hour
    if len(str(month)) == 1:
        month = "0" + str(month)
    if len(str(day)) == 1:
        day = "0" + str(day)
    if len(str(hour)) == 1:
        hour = "0" + str(hour)
    minute = current_time.minute
    if len(str(minute)) == 1:
        minute = "0" + str(minute)
    second = current_time.second
    if len(str(second)) == 1:
        second = "0" + str(second)
    return f"{year}/{month}/{day}/{hour}:{minute}:{second}/"


def get_secret(secret_prefix="totesys-credentials-"):
    """
    Initialises a boto3 secrets manager client and retrieves secret from secrets manager
    based on argument given, with the default argument set to the database credentials.
    The secret returned should be a dictionary with 5 keys:
    user - the username for the database
    password - the password for the user
    host - the url of the server hosting the database
    port - which port we are using to connect with the database
    database - the name of the database that we want to connect to
    """
    session = boto3.session.Session()
    client = session.client(service_name="secretsmanager", region_name="eu-west-2")
    
    try:
        get_secrets_lists_response = client.list_secrets()
        for secret in get_secrets_lists_response['SecretList']:
            if secret['Name'].startswith(secret_prefix):
                secret_name = secret['Name']
                break
        secret_value_response = client.get_secret_value(SecretId=secret_name)
    except ClientError as e:
        logging.error(e)
        raise Exception(f"Can't retrieve secret due to {e}")

    return json.loads(secret_value_response["SecretString"])


def connect_to_bucket(client):
    """
    Searches for a raw data bucket within an AWS account and returns bucket name if
    bucket is found or raises exception if bucket is not found.
    """
    buckets = client.list_buckets()
    for bucket in buckets["Buckets"]:
        if bucket["Name"].startswith("totesys-raw-data-"):
            return bucket["Name"]
    logging.error("No raw data bucket found")
    raise Exception("No raw data bucket found")


def connect_to_db(credentials):
    """
    Uses the secret obtained in the get_secret method to establish a
    connection to the database
    """
    return Connection(
        user=credentials["user"],
        password=credentials["password"],
        host=credentials["host"],
        database=credentials["database"],
        port=credentials["port"],
    )


def query_db(dt_name, conn):
    """
    Does two queries to the database:
    1. Name of table's columns --> header of csv format file
    2. All table's content
    Returns data in csv format (header + data rows)
    """
    query = f"SELECT column_name FROM information_schema.columns WHERE table_name = '{dt_name}';"
    column_names = conn.run(query)
    header = []
    for column in column_names:
        header.append(column[0])

    query = f"SELECT * FROM {dt_name};"
    data_rows = conn.run(query)
    return [header] + data_rows


def create_and_upload_csv(data, client, bucket, tablename, time_path, first_call):
    """
    Converts a table from a database into a CSV file and uploads that CSV file to either:
    - first_call == True ? bucket/source as *_new.csv , and history/y/m/d/hh:mm:ss/*_differences.csv
    - first_call == False ? lamba ephemeral storage/tmp as *.csv
    The data argument is a list of lists.
    """
    file_to_save = StringIO()
    csv.writer(file_to_save).writerows(data)
    file_to_save = bytes(file_to_save.getvalue(), encoding="utf-8")

    try:
        if first_call:
            client.put_object(
                Body=file_to_save,
                Bucket=bucket,
                Key=f"{SOURCE_PATH}{tablename}{SOURCE_FILE_SUFFIX}.csv",
            )
            client.put_object(
                Body=file_to_save,
                Bucket=bucket,
                Key=f"{HISTORY_PATH}{time_path}{tablename}{DIFFERENCES_FILE_SUFFIX}.csv",
            )
        else:
            with open(f'/tmp/{tablename}_new.csv', 'wb') as csvfile:
                csvfile.write(file_to_save)
        
    except ClientError as e:
        logging.error(e)
        raise Exception("Failed to upload file")


def compare_csvs(dt_name):
    """
    Takes two csvs (dt_name.csv, dt_name_new.csv) located in /tmp
    and compares the differences between them, returning an
    empty csv if no differences found.

    Arg: datatable name (= prefix of csv file name)

    Returns:
    csv file containing all changes to database (if csv1 and csv2 are not equal)
    None (if dt_name.csv, dt_name_new.csv are equal)
    """
    csv_prev = f"/tmp/{dt_name}.csv"
    csv_new = f"/tmp/{dt_name}_new.csv"

    # read the header from the CSV file
    with open(csv_prev, "r", newline="") as csv_file:  # , newline=''
        csv_reader = csv.reader(csv_file, delimiter=",")
        header = []
        for row in csv_reader:
            header.append(row)
            break

    diff_output = subprocess.run(
        ["diff", csv_prev, csv_new], capture_output=True
    ).stdout
    differences = subprocess.run(["echo", diff_output], capture_output=True)

    #print(f"\n differences: {differences}")
    changes_to_table = re.findall(CSV_REGEX, differences.stdout.decode())
    #print(f"\nCHANGES TO TABLE: {changes_to_table}")
    filepath = f"{dt_name}_differences.csv"
    with open(f"/tmp/{filepath}", "w", newline="") as f:
        csvwriter = csv.writer(f)
        csvwriter.writerow(header[0])
        for change in changes_to_table:
            change_list = [k for k in list(change) if not "" == k]
            #print(f"\nchange_list: {change_list}")
            csvwriter.writerow(change_list[0].split(","))

    if changes_to_table == "\n":
        logging.info("No changes in table found")
    else:
        logging.info("Changes found in table")

    return filepath
"""
AWS Lambda Function for processing streaming data and storing it in S3 and DynamoDB.
- Extracts data from Kinesis stream
- Transforms and filters the data
- Loads the processed data into S3 and DynamoDB

This script is designed to be used within an AWS Lambda environment triggered by a Kinesis stream.

Author: Kruti Rajyaguru

Date: 07.03.2024

Requirements:
- boto3 library
- AWS credentials configured with appropriate permissions
"""

import boto3
import json
from datetime import datetime

# Initialize AWS clients
s3 = boto3.client('s3')
dynamodb_client = boto3.client('dynamodb')

# DynamoDB table for deduplication
table_name = 'EventsTable'

def is_complete(payload):
    """
    Check if payload contains all required fields.
    
    Parameters:
    - payload (dict): Dictionary containing event data
    
    Returns:
    - bool: True if all required fields are present, False otherwise
    """
    return all(field in payload for field in ["event_name", "created_at", "event_uuid"])

def is_valid_created_at(payload):
    """
    Check if 'created_at' field is of integer type.
    
    Parameters:
    - payload (dict): Dictionary containing event data
    
    Returns:
    - bool: True if 'created_at' is of integer type, False otherwise
    """
    return isinstance(payload.get("created_at"), int)

def is_valid_event_uuid(payload):
    """
    Check if 'event_uuid' field is a valid integer.
    
    Parameters:
    - payload (dict): Dictionary containing event data
    
    Returns:
    - bool: True if 'event_uuid' is a valid integer, False otherwise
    """
    try:
        payload['event_uuid'] = int(payload['event_uuid'])
    except ValueError:
        return False
    return True

def check_duplicate(event_uuid):
    """
    Check if event_uuid already exists in DynamoDB table.
    
    Parameters:
    - event_uuid (int): Event UUID
    
    Returns:
    - bool: True if event_uuid exists in DynamoDB table, False otherwise
    """
    response = dynamodb_client.get_item(
        TableName=table_name,
        Key={'event_uuid': {'S': str(event_uuid)}} # e.g. - {'event_uuid': '19334'}
    )
    return 'Item' in response

def lambda_handler(event, context):
    """
    Lambda function handler for processing streaming data.
    
    Parameters:
    - event (dict): AWS Lambda event data
    - context (object): Lambda context object
    
    Returns:
    - dict: Dictionary containing processing status and metrics
    """
    # Initialize counters
    total_events = len(event["Records"])
    unique_events = 0
    complete_events = 0
    valid_events = 0
    
    for record in event["Records"]:
        payload = json.loads(record["kinesis"]["data"])
        
        if not is_complete(payload):
            continue
        
        complete_events += 1
        
        event_uuid = payload['event_uuid']
        
        # Check for duplicate
        if check_duplicate(event_uuid):
            continue
        
        unique_events += 1

        if not is_valid_created_at(payload) or not is_valid_event_uuid(payload):
            continue

        valid_events += 1
        
        # Add additional fields to payload
        payload["created_datetime"] = datetime.utcfromtimestamp(payload["created_at"]).isoformat()
        event_parts = payload["event_name"].split(":")
        payload["event_type"] = event_parts[0]
        payload["event_subtype"] = event_parts[1] if len(event_parts) > 1 else None

        # Define the file path based on event date and type
        file_path = f'{datetime.utcfromtimestamp(payload["created_at"]).strftime("%Y/%m/%d")}/{payload["event_type"]}/{payload["event_subtype"]}/{payload["event_uuid"]}.json'
        
        # Upload payload to S3
        s3.put_object(Bucket='s3-target-bucket-070324', Key=file_path, Body=json.dumps(payload))

        # Add event_uuid to DynamoDB
        dynamodb_client.put_item(
            TableName=table_name,
            Item={'event_uuid': {'S': str(event_uuid)}}
        )
        
    # Metrics calculations
    uniqueness = (unique_events / total_events) * 100 if total_events else 0
    completeness = (complete_events / total_events) * 100 if total_events else 0
    validity = (valid_events / total_events) * 100 if total_events else 0

    # Return metrics and status
    return {'status': 'complete', 'total_events': total_events, 'unique_events(%)': uniqueness, 'complete_events(%)': completeness, 'valid_events(%)': validity}
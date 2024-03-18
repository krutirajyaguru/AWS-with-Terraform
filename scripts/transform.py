"""
AWS Lambda Function for processing streaming data and storing it in S3 and DynamoDB.
- Extracts data from Kinesis stream
- Validates and enriches the data
- Checks for duplicates in DynamoDB
- Loads the processed data into S3 and records event UUIDs in DynamoDB for deduplication

This script is designed to be used within an AWS Lambda environment triggered by a Kinesis stream.

Author: Kruti Rajyaguru
Date: 07.03.2024

Requirements:
- boto3 library
- AWS credentials configured with appropriate permissions
"""

import json
import boto3
import logging
from datetime import datetime
from typing import Dict, Any

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS SDK clients outside the Lambda handler for connection reuse
s3_client = boto3.client('s3')
dynamodb_client = boto3.client('dynamodb')

# Constants for configuration
CONFIG = {
    "table_name": "EventsTable",
    "bucket_name": "s3-target-bucket-070324",
    "required_fields": ["event_name", "created_at", "event_uuid"]
}

def validate_event(payload: Dict[str, Any]) -> bool:
    """
    Validate event structure and data.
    
    Parameters:
    - payload (dict): Dictionary containing event data
    
    Returns:
    - bool: True if the event is valid, False otherwise
    """
    if not all(field in payload for field in CONFIG["required_fields"]):
        logger.warning("Event missing required fields")
        return False

    if not isinstance(payload.get("created_at"), int):
        logger.warning("Invalid 'created_at' field type")
        return False

    try:
        payload['event_uuid'] = int(payload['event_uuid'])
    except ValueError:
        logger.warning("Invalid 'event_uuid' format")
        return False

    return True

def check_duplicate(event_uuid: int) -> bool:
    """
    Check for event UUID in DynamoDB to prevent duplicates.
    
    Parameters:
    - event_uuid (int): Event UUID
    
    Returns:
    - bool: True if the event UUID exists in DynamoDB, False otherwise
    """
    try:
        response = dynamodb_client.get_item(
            TableName=CONFIG["table_name"],
            Key={'event_uuid': {'S': str(event_uuid)}}
        )
        return 'Item' in response
    except Exception as e:
        logger.error(f"Error checking for duplicate: {e}")
        raise

def enrich_and_store_event(payload: Dict[str, Any]) -> None:
    """
    Enrich the event payload and store it in S3 and DynamoDB.
    
    Parameters:
    - payload (dict): Dictionary containing event data
    
    Returns:
    - None
    """
    # Enrichment
    payload["created_datetime"] = datetime.utcfromtimestamp(payload["created_at"]).isoformat()
    event_parts = payload["event_name"].split(":")
    payload["event_type"], payload["event_subtype"] = event_parts[0], event_parts[1] if len(event_parts) > 1 else None

    # Define S3 path
    file_path = f'{datetime.utcfromtimestamp(payload["created_at"]).strftime("%Y/%m/%d")}/{payload["event_type"]}/{payload["event_subtype"]}/{payload["event_uuid"]}.json'

    # Store in S3
    s3_client.put_object(Bucket=CONFIG["bucket_name"], Key=file_path, Body=json.dumps(payload))

    # Record in DynamoDB
    dynamodb_client.put_item(
        TableName=CONFIG["table_name"],
        Item={'event_uuid': {'S': str(payload["event_uuid"])}}
    )

def process_event(record: Dict[str, Any]) -> bool:
    """
    Process a single event record.
    
    Parameters:
    - record (dict): Record from the Kinesis stream
    
    Returns:
    - bool: True if the event is processed successfully, False otherwise
    """
    try:
        payload = json.loads(record["kinesis"]["data"])
        if not validate_event(payload) or check_duplicate(payload['event_uuid']):
            return False

        enrich_and_store_event(payload)
        return True
    except Exception as e:
        logger.error(f"Failed to process event: {e}")
        return False

def lambda_handler(event, context):
    """
    Lambda function entry point.
    
    Parameters:
    - event (dict): AWS Lambda event data
    - context (object): Lambda context object
    
    Returns:
    - dict: Dictionary containing processing status and metrics
    """
    # Process events
    processed_events = [process_event(record) for record in event["Records"]]
    success_count = sum(processed_events)

    # Calculate metrics
    metrics = {
        'total_events': len(event["Records"]),
        'successfully_processed': success_count,
        'success_rate': (success_count / len(event["Records"])) * 100 if event["Records"] else 0
    }

    # Log processing summary
    logger.info(f"Processing summary: {metrics}")

    # Return metrics and status
    return {'status': 'complete', **metrics}

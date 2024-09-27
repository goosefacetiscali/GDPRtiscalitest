import json
import boto3
import pandas as pd
import io
import logging
import os

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3 = boto3.client('s3')

tf_state_bucket = 'tf-state-gdpr-obfuscator'  
tf_state_key = 'tf-state'                      
def get_bucket_names_from_tf_state(bucket_name, object_key):
    """ Retrieves bucket names from the Terraform state file. """
    try:
        response = s3.get_object(Bucket=bucket_name, Key=object_key)
        data = json.loads(response['Body'].read().decode('utf-8'))
        input_bucket_name = data["outputs"]["gdpr_input_bucket"]["value"]
        processed_bucket_name = data["outputs"]["gdpr_processed_bucket"]["value"]
        invocation_bucket_name = data["outputs"]["gdpr_invocation_bucket"]["value"]
        
        return input_bucket_name, processed_bucket_name, invocation_bucket_name
    except Exception as e:
        logger.error(f"Failed to retrieve bucket names: {e}")
        return None, None, None

def get_keys_from_bucket(bucket_name):
    """ Retrieves the JSON key from the specified S3 bucket. """
    response = s3.list_objects_v2(Bucket=bucket_name)
    
    json_key = None
    
    if 'Contents' in response:
        for obj in response['Contents']:
            key = obj['Key']
            logger.info(f"Found key: {key}")  
            if key.endswith('.json') and not json_key:
                json_key = key 
                
    logger.info(f"JSON key found: {json_key}")  
    return json_key
def obfuscate_pii(bucket_name, s3_file_path, pii_fields):
    """ Obfuscates specified PII fields in a CSV file. """
    try:
        response = s3.get_object(Bucket=bucket_name, Key=s3_file_path)
        csv_data = response['Body'].read()
        
        # Read the CSV data into a DataFrame
        df = pd.read_csv(io.BytesIO(csv_data))
        logger.info(f"DataFrame before obfuscation:\n{df.head()}")  # Log the DataFrame before obfuscation
        
        # Obfuscate the specified PII fields
        for pii_field in pii_fields:
            if pii_field in df.columns:
                logger.info(f"Obfuscating field: {pii_field}")  # Log the field being obfuscated
                df[pii_field] = '***'  # Obfuscate PII fields
            else:
                logger.warning(f"Field '{pii_field}' not found in DataFrame columns.")

        # Convert the DataFrame back to CSV
        obfuscated_csv = df.to_csv(index=False)
        logger.info("Obfuscation complete.")  # Log completion of obfuscation
        return obfuscated_csv.encode('utf-8')  # Return the obfuscated CSV data

    except Exception as e:
        logger.error(f"Failed to process file: {e}")  # Log the error
        return None

def handler(event, context):
    """ Lambda function handler. """
    
            
    
    input_bucket_name, processed_bucket_name, invocation_bucket_name = get_bucket_names_from_tf_state(tf_state_bucket, tf_state_key)

    try:
        json_file_path = get_keys_from_bucket(invocation_bucket_name)  
        if not json_file_path:
            raise ValueError("No JSON file found in the invocation bucket.")
    except Exception as e:
        logger.error(f"Error retrieving JSON file from bucket: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps('Error retrieving JSON file from invocation bucket.')
        }

    try:
        response = s3.get_object(Bucket=invocation_bucket_name, Key=json_file_path)  
        json_content = json.loads(response['Body'].read().decode('utf-8'))
    except Exception as e:
        logger.error(f"Error reading JSON file: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps('Error reading JSON file.')
        }
    
    try:
        input_bucket = json_content.get('bucket_name')  
        csv_file_path = json_content.get('s3_file_path')  
        pii_fields = json_content.get('pii_fields', [])

        logger.info(f"CSV file path: {csv_file_path}, PII fields: {pii_fields}")

        if not input_bucket or not csv_file_path:
            raise ValueError("Bucket name or CSV file path not found in the JSON content.")
        
        obfuscated_csv_data = obfuscate_pii(input_bucket, csv_file_path, pii_fields)
        
        if obfuscated_csv_data:
            if processed_bucket_name:
                obfuscated_file_path = f"processed/{os.path.basename(csv_file_path)}"
                s3.put_object(Bucket=processed_bucket_name, Key=obfuscated_file_path, Body=obfuscated_csv_data)
                logger.info(f"Uploaded obfuscated CSV to {processed_bucket_name}/{obfuscated_file_path}")
            else:
                logger.error("Processed bucket name not found in JSON.")
                return {
                    'statusCode': 400,
                    'body': json.dumps('Processed bucket name not found.')
                }
        empty_bucket(input_bucket_name)
        empty_bucket(invocation_bucket_name)
        
        return {
            'statusCode': 200,
            'body': json.dumps('Processing completed successfully.')
        }
    
    except Exception as e:
        logger.error(f"Error processing JSON content: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps('Error processing JSON content.')
        }


def empty_bucket(bucket_name):
    """ Deletes all objects in the specified S3 bucket. """
    try:
        response = s3.list_objects_v2(Bucket=bucket_name)

        if 'Contents' in response:
            for obj in response['Contents']:
                s3.delete_object(Bucket=bucket_name, Key=obj['Key'])
            logger.info(f"All objects deleted from bucket: {bucket_name}")
        else:
            logger.info(f"No objects found in bucket: {bucket_name}")
    
    except Exception as e:
        logger.error(f"Failed to delete objects from bucket: {e}")

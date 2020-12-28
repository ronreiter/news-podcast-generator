from config import SERVICE_ACCOUNT_CREDS
from google.cloud import storage

storage_client = storage.Client.from_service_account_json(SERVICE_ACCOUNT_CREDS)

def upload_blob(bucket_name, blob_name, data):
    bucket = storage_client.get_bucket(bucket_name)
    blob = bucket.blob(blob_name)
    blob.upload_from_string(data)

def upload_file(bucket_name, blob_name, fn):
    bucket = storage_client.get_bucket(bucket_name)
    blob = bucket.blob(blob_name)
    blob.upload_from_filename(fn)

def blob_exists(bucket_name, blob_name):
    bucket = storage_client.get_bucket(bucket_name)
    blob = bucket.blob(blob_name)
    return blob.exists()
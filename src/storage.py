import os

from minio import Minio
from minio.error import S3Error


def make_minio_client(endpoint: str, access_key: str, secret_key: str, secure: bool = False) -> Minio:
    return Minio(endpoint, access_key=access_key, secret_key=secret_key, secure=secure)

def ensure_bucket(client: Minio, bucket: str):
    try:
        if not client.bucket_exists(bucket):
            client.make_bucket(bucket)
    except S3Error:
        raise

def upload_file(client: Minio, bucket: str, object_name: str, file_path: str):
    try:
        client.fput_object(bucket, object_name, file_path)
        return True
    except S3Error:
        return False

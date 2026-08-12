import os
import json
from botocore.exceptions import ClientError
import boto3
from dotenv import load_dotenv

# Muat variabel dari file .env
load_dotenv()

# Baca kredensial dari environment variables
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "http://localhost:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin")
MINIO_BUCKET_NAME = os.getenv("MINIO_BUCKET_NAME", "userdoc-avatars")

# Inisialisasi klien S3/MinIO
s3_client = boto3.client(
    "s3",
    endpoint_url=MINIO_ENDPOINT,
    aws_access_key_id=MINIO_ACCESS_KEY,
    aws_secret_access_key=MINIO_SECRET_KEY,
    config=boto3.session.Config(signature_version="s3v4")  # <-- Diperbaiki dari + menjadi =
)

def init_bucket():  # <-- Diperbaiki menjadi init_bucket
    """Memastikan bucket ada dan memiliki hak akses public (read-only)"""
    try:
        # Check apakah bucket sudah ada
        s3_client.head_bucket(Bucket=MINIO_BUCKET_NAME)  # <-- Indentasi diperbaiki
    except ClientError:
        # Jika belum ada, buat bucket baru
        s3_client.create_bucket(Bucket=MINIO_BUCKET_NAME)  # <-- Indentasi diperbaiki
        
        public_policy = {
            "Version": "2012-10-17",  # <-- Ditambahkan koma di akhir
            "Statement": [
                {
                    "Sid": "PublicRead",
                    "Effect": "Allow",
                    "Principal": "*",
                    "Action": ["s3:GetObject"],
                    "Resource": [f"arn:aws:s3:::{MINIO_BUCKET_NAME}/*"]
                }
            ]
        }
        s3_client.put_bucket_policy(
            Bucket=MINIO_BUCKET_NAME,
            Policy=json.dumps(public_policy)
        )

def upload_avatar(file_data, file_name: str, content_type: str) -> str:
    """Mengunggah file ke MinIO dan mengembalikan URL publik gambarnya"""
    # Pastikan bucket siap digunakan
    init_bucket()
    
    # Unggah data file ke MinIO
    s3_client.put_object(
        Bucket=MINIO_BUCKET_NAME,
        Key=file_name,
        Body=file_data,
        ContentType=content_type
    )
    
    # Susun URL publik file hasil upload
    file_url = f"{MINIO_ENDPOINT}/{MINIO_BUCKET_NAME}/{file_name}"
    return file_url
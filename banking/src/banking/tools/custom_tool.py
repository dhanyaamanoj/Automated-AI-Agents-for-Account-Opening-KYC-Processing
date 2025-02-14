# import boto3
# import os
# from typing import Any
# from crewai.tools import BaseTool
# from dotenv import load_dotenv

# # Load environment variables
# load_dotenv()

# # AWS credentials (from environment variables)
# aws_access_key_id = os.getenv("AWS_ACCESS_KEY_ID")
# aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY")
# aws_bucket_name = os.getenv("BUCKET_NAME")
# aws_region_name = os.getenv("AWS_REGION_NAME")

# # S3 parent folder and local paths
# parent_folder = "Dhanya"
# local_id_path = r"C:\Users\DHANYA MANOJ\Downloads\banking_crew_working\banking\local_id_path"

# class S3DownloadTool(BaseTool):
#     name: str = "S3 Download Tool"
#     description: str = "Downloads the id proofs from the S3 bucket and saves them locally."
#     arguments: str = {
#         'local_id_path': {'description': "Input local ID path", 'type': 'str'},
#     }

#     def connect_to_s3(self):
#         """Establish an S3 client connection using environment variables."""
#         try:
#             s3_client = boto3.client(
#                 's3',
#                 aws_access_key_id=aws_access_key_id,
#                 aws_secret_access_key=aws_secret_access_key,
#                 region_name=aws_region_name
#             )
#             print("Connected to S3")
#             return s3_client
#         except Exception as e:
#             print(f"Failed to connect to S3: {str(e)}")
#             return None

#     def download_file(self, s3, bucket_name: str, file_key: str, destination_path: str):
#         """Download a file from S3 to a local destination."""
#         try:
#             os.makedirs(os.path.dirname(destination_path), exist_ok=True)  # Ensure folder exists
#             s3.download_file(bucket_name, file_key, destination_path)
#             print(f"Downloaded: {file_key} -> {destination_path}")
#         except Exception as e:
#             print(f"Failed to download {file_key}: {str(e)}")

#     def download_files_from_s3(self, s3, bucket_name: str, s3_folder: str, local_folder: str, file_extensions: list):
#         """Download files from an S3 folder to a local folder."""
#         try:
#             response = s3.list_objects_v2(Bucket=bucket_name, Prefix=s3_folder)

#             if 'Contents' not in response:
#                 print(f"No files found in {s3_folder}")
#                 return
            
#             for item in response['Contents']:
#                 file_key = item['Key']
#                 file_name = os.path.basename(file_key)

#                 # Skip folders (empty file names)
#                 if not file_name:
#                     continue

#                 # Filter by file extension
#                 if file_extensions and not any(file_name.lower().endswith(ext) for ext in file_extensions):
#                     continue

#                 destination_path = os.path.join(local_folder, file_name)
                
#                 # Ensure proper permissions before writing
#                 try:
#                     if os.path.exists(destination_path):
#                         print(f"File already exists: {destination_path}, skipping download.")
#                         continue

#                     self.download_file(s3, bucket_name, file_key, destination_path)
#                 except PermissionError:
#                     print(f"Permission error: Unable to save file to {destination_path}. Try running as Administrator.")
                    
#         except Exception as e:
#             print(f"Error downloading files from {s3_folder}: {str(e)}")

#     def _run(self) -> str:
#         """Run the S3 download process for ID proofs."""
#         try:
#             s3 = self.connect_to_s3()
#             if not s3:
#                 return "S3 connection failed."

#             # Define S3 source path for ID proofs
#             id_proofs_s3_path = f"{parent_folder}/id_proof/"

#             # Ensure local path exists
#             os.makedirs(local_id_path, exist_ok=True)

#             # Download ID proofs (.jpg)
#             self.download_files_from_s3(s3, aws_bucket_name, id_proofs_s3_path, local_id_path, file_extensions=['.jpg','.pdf'])

#             return f"Download completed successfully. Files saved to {local_id_path}"
#         except Exception as e:
#             return f"An error occurred: {str(e)}"
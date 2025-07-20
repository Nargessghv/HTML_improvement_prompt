import os

from azure.storage.blob import BlobServiceClient
from dotenv import load_dotenv


class AzureBlobUploader:
    def __init__(self):
        load_dotenv()
        connection_string = os.getenv("LANGFUSE_AZURE_BLOB_CONNECTION_STRING")
        container_name = os.getenv("LANGFUSE_AZURE_BLOB_CONTAINER_NAME")

        if not connection_string or not container_name:
            raise ValueError("Azure Blob Storage credentials are not configured.")

        self.connection_string: str = connection_string
        self.container_name: str = container_name

        self.blob_service_client = BlobServiceClient.from_connection_string(
            self.connection_string
        )

    def upload_file(self, file_path: str, blob_name: str) -> str:
        """
        Uploads a file to Azure Blob Storage and returns its public URL.
        """
        blob_client = self.blob_service_client.get_blob_client(
            container=self.container_name, blob=blob_name
        )

        with open(file_path, "rb") as data:
            blob_client.upload_blob(data, overwrite=True)

        return blob_client.url

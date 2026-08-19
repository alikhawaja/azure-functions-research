"""
Demo: Azure Function using Managed Identity to access Key Vault and Storage.

No secrets, keys, or connection strings are stored anywhere in this file.
DefaultAzureCredential automatically uses the function app's managed identity
when this code runs in Azure.

Two HTTP-triggered endpoints:
  GET /api/get-secret   -> reads a secret from Key Vault
  GET /api/list-blobs   -> lists blobs in a Storage container

Before this will work, you must (see README.md for full steps):
  1. Turn on managed identity for this function app.
  2. Grant that identity "Key Vault Secrets User" on your Key Vault.
  3. Grant that identity "Storage Blob Data Reader" on your Storage account.
  4. Set the app settings KEY_VAULT_URL, SECRET_NAME, STORAGE_ACCOUNT_URL,
     and CONTAINER_NAME (see local.settings.json.example).
"""

import logging
import os

import azure.functions as func
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from azure.storage.blob import BlobServiceClient

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)

# One shared credential object. DefaultAzureCredential automatically picks
# the function app's managed identity when running in Azure, and falls back
# to your local Azure CLI login when running/testing on your own machine.
credential = DefaultAzureCredential()


@app.route(route="get-secret", methods=["GET"])
def get_secret(req: func.HttpRequest) -> func.HttpResponse:
    """Reads a secret from Key Vault using managed identity. No key or
    password is stored in this app — access is controlled purely by the
    role assigned to the function app's identity in Key Vault."""

    logging.info("get-secret function triggered")

    vault_url = os.environ.get("KEY_VAULT_URL")
    secret_name = os.environ.get("SECRET_NAME")

    if not vault_url or not secret_name:
        return func.HttpResponse(
            "Missing app settings: KEY_VAULT_URL and/or SECRET_NAME",
            status_code=500,
        )

    try:
        client = SecretClient(vault_url=vault_url, credential=credential)
        secret = client.get_secret(secret_name)

        # In a real app, never return a raw secret in an HTTP response.
        # This demo only echoes the secret's name and a masked value to
        # prove the identity-based access worked, without exposing it.
        masked_value = secret.value[:2] + "***" if secret.value else "***"

        return func.HttpResponse(
            f"Successfully read secret '{secret.name}' from Key Vault "
            f"using managed identity. Value starts with: {masked_value}",
            status_code=200,
        )
    except Exception as exc:
        logging.exception("Failed to read secret from Key Vault")
        return func.HttpResponse(
            f"Could not read secret. Check that the function app's managed "
            f"identity has the 'Key Vault Secrets User' role. Error: {exc}",
            status_code=500,
        )


@app.route(route="list-blobs", methods=["GET"])
def list_blobs(req: func.HttpRequest) -> func.HttpResponse:
    """Lists blob names in a Storage container using managed identity.
    No connection string or account key is stored in this app."""

    logging.info("list-blobs function triggered")

    account_url = os.environ.get("STORAGE_ACCOUNT_URL")
    container_name = os.environ.get("CONTAINER_NAME")

    if not account_url or not container_name:
        return func.HttpResponse(
            "Missing app settings: STORAGE_ACCOUNT_URL and/or CONTAINER_NAME",
            status_code=500,
        )

    try:
        blob_service_client = BlobServiceClient(
            account_url=account_url, credential=credential
        )
        container_client = blob_service_client.get_container_client(container_name)

        blob_names = [blob.name for blob in container_client.list_blobs()]

        return func.HttpResponse(
            f"Found {len(blob_names)} blob(s) in '{container_name}' using "
            f"managed identity: {blob_names}",
            status_code=200,
        )
    except Exception as exc:
        logging.exception("Failed to list blobs from Storage")
        return func.HttpResponse(
            f"Could not list blobs. Check that the function app's managed "
            f"identity has the 'Storage Blob Data Reader' role. Error: {exc}",
            status_code=500,
        )

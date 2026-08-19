# Task 3: Identity & Authentication

This file covers three things that all solve the same basic problem in different ways: **how do we prove who someone is, and how do we let our function talk to other Azure services without hardcoding secrets?**

1. **EasyAuth** — checks who is calling your function.
2. **Managed Identity** — lets your function log in to other Azure services, with no stored secrets.
3. **Key Vault references** — lets your app settings pull secrets from Key Vault automatically.

---

## 1. App Service Authentication (EasyAuth)

### What problem it solves

Normally, if you want to check "is this user logged in?" before running your code, you have to write that logic yourself — handle login redirects, validate tokens, manage sessions. That's a lot of work and easy to get wrong.

EasyAuth removes that work. It's a feature built into the Azure platform itself, sitting in front of your function app.

### How it works

1. You turn it on in the **Authentication** section of your function app, in the Azure portal.
2. You pick one or more **identity providers** (see list below).
3. Once it's on, **every incoming request passes through EasyAuth first**, before it ever reaches your function's code.
4. If the request isn't authenticated, EasyAuth can either block it, or redirect the user to log in with the provider you picked.
5. If the request is authenticated, EasyAuth passes along information about the user (like their name, email, ID) to your function through HTTP headers, so your code can use it without doing the login work itself.

This is why it's called a "turn-key" or "no-code" authentication layer — you don't write any authentication code. You just flip a setting.

### Identity providers it supports

EasyAuth supports several identity providers out of the box:

| Provider | What it is |
|---|---|
| Microsoft Entra ID | Microsoft's identity service (formerly Azure AD) — used for company/work accounts |
| Google | Sign in with a Google account |
| Facebook | Sign in with a Facebook account |
| GitHub | Sign in with a GitHub account |
| X (formerly Twitter) | Sign in with an X account |
| Apple | Sign in with Apple |
| Any OpenID Connect provider | A generic option — lets you plug in other identity systems that follow the OpenID Connect standard |

You can even turn on more than one provider at the same time, so users can choose how they want to sign in.

### Simple analogy

Think of EasyAuth like a security guard standing at the front door of a building. Every visitor has to show ID to the guard before they're allowed in. The guard doesn't work for any one company inside the building — the guard is provided by the building itself. Your function (the office inside) never has to check ID itself; by the time someone reaches your office, the guard has already confirmed who they are.

---

## 2. Managed Identity

### What problem it solves

Functions often need to talk to other Azure services — like reading a secret from Key Vault, or reading/writing a file in Storage. The old way of doing this was to store a password, connection string, or access key inside your app settings. That's risky: if that secret leaks, anyone with it can access your resources.

Managed Identity removes the need to store any secret at all.

### How it works

1. You turn on Managed Identity for your function app.
2. Azure automatically creates an **identity** for your function app inside Microsoft Entra ID (this is like giving your function its own "user account," but it's not a person — it's the app itself).
3. You then go to the resource you want your function to access (like a Key Vault or Storage account) and give that identity permission (a **role**), like "can read secrets" or "can read blobs."
4. From that point on, your function code can request a login token for that identity automatically, without you ever typing a password or connection string anywhere.

Azure handles creating, rotating, and protecting the credentials behind the scenes. You never see them, and they can't leak from your code, because they were never in your code.

### Two types

There are two kinds of managed identity, and the difference is about **who owns the identity and how long it lives**.

**System-assigned identity**
- Created and deleted automatically, tied directly to your function app.
- If you delete the function app, the identity is deleted too.
- Good for: a single function app that needs its own permissions, and nothing else needs to share them.

**User-assigned identity**
- Created separately, as its own standalone Azure resource.
- You then attach it to one or more function apps (or other resources).
- It keeps existing even if you delete a function app that was using it.
- Good for: multiple function apps that all need the same set of permissions — you set the permissions once, on one identity, and just attach it wherever needed.

### Simple analogy

Imagine every function app can carry an ID badge that opens certain doors in a building.

- A **system-assigned identity** is like a badge that's printed specifically for one employee, and gets destroyed the day that employee leaves.
- A **user-assigned identity** is like a shared badge that opens the same doors, which you can hand to any employee who needs it, and it keeps working even if one employee leaves.

### Demo: accessing Key Vault using Managed Identity

Here is a simple example showing the steps and code to read a secret from Key Vault using a system-assigned managed identity, in a Python Azure Function.

**Step 1: Turn on managed identity for the function app**

In the Azure portal:
- Go to your function app → **Identity** → **System assigned** tab → set **Status** to **On** → **Save**.

Or using the Azure CLI:
```bash
az functionapp identity assign --name my-function-app --resource-group my-resource-group
```

**Step 2: Give the identity permission on Key Vault**

In the Azure portal:
- Go to your Key Vault → **Access control (IAM)** → **Add role assignment**.
- Pick the role **Key Vault Secrets User**.
- Assign it to your function app's managed identity (search for the function app's name).

Or using the Azure CLI:
```bash
az role assignment create \
  --assignee <function-app-identity-object-id> \
  --role "Key Vault Secrets User" \
  --scope /subscriptions/<sub-id>/resourceGroups/<rg>/providers/Microsoft.KeyVault/vaults/<vault-name>
```

**Step 3: Use the identity in code**

You don't write any login code. You use `DefaultAzureCredential` from the Azure Identity SDK — it automatically finds and uses the managed identity when the code runs inside Azure.

```python
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

# No username, password, or connection string anywhere in this code.
credential = DefaultAzureCredential()

vault_url = "https://my-key-vault.vault.azure.net/"
client = SecretClient(vault_url=vault_url, credential=credential)

secret = client.get_secret("my-secret-name")
print(secret.value)
```

That's it. `DefaultAzureCredential` automatically detects that it's running as a function app with a managed identity, and gets a token for it behind the scenes. If you ran this same code on your own laptop (not inside Azure), it would fall back to trying your local Azure CLI login instead — that's part of what makes `DefaultAzureCredential` convenient for both testing locally and running in production.

The same pattern works for Azure Storage — just swap `SecretClient` for a Storage SDK client, like `BlobServiceClient`:

```python
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient

credential = DefaultAzureCredential()

account_url = "https://mystorageaccount.blob.core.windows.net"
blob_service_client = BlobServiceClient(account_url=account_url, credential=credential)

container_client = blob_service_client.get_container_client("my-container")
blob_list = container_client.list_blobs()
for blob in blob_list:
    print(blob.name)
```

Again — no key, no connection string. Just permission granted to the identity, and the SDK handles the rest.

---

## 3. Key Vault references in application settings

### What problem it solves

Even with managed identity, sometimes you still want to use plain app settings (environment variables) for configuration — for example, a database connection string used by a library that doesn't support managed identity directly. You don't want to paste the actual secret value into your app settings, because anyone who can view your app's configuration could then see it in plain text.

Key Vault references solve this.

### How it works

Instead of putting the real secret value into an app setting, you put a special reference string that points to the secret in Key Vault:

```
@Microsoft.KeyVault(SecretUri=https://my-key-vault.vault.azure.net/secrets/my-secret-name/)
```

When your function app starts up, Azure automatically resolves this reference — it goes to Key Vault, fetches the actual secret value, and makes it available to your app as if it were a normal setting. Your code just reads the app setting normally; it doesn't need to know it came from Key Vault at all.

### Requirements

- Your function app needs a **managed identity** (system-assigned or user-assigned).
- That identity needs the **Key Vault Secrets User** role (or equivalent access) on the Key Vault.
- Without both of these, the reference cannot be resolved, and the setting will show an error status in the portal instead of the real value.

### Why this is useful

- The actual secret value is never typed into your app settings, never shows up in deployment scripts, and never needs to be copy-pasted around.
- If the secret changes in Key Vault (say, a password rotation), your app setting automatically reflects the new value the next time it's resolved — you don't have to manually update it everywhere it's used.
- You get centralized secret management: one Key Vault, many apps can reference the same secrets, and access can be revoked in one place.

---

## 4. How all three fit together

| Feature | What it protects | Who/what it checks |
|---|---|---|
| EasyAuth | Your function app itself | Checks the identity of the caller (a person or client app) before running your code |
| Managed Identity | Other Azure resources your function talks to | Lets your function itself prove who *it* is, without any stored secret |
| Key Vault references | Secrets used in configuration | Keeps real secret values out of app settings, pulling them from Key Vault at runtime |

A well-secured function app usually uses all three together:
- EasyAuth to control who can call the function.
- Managed Identity so the function can reach Key Vault, Storage, or databases without stored credentials.
- Key Vault references for any remaining settings that still need a secret value, so nothing sensitive sits in plain text.

---

## Glossary

- **EasyAuth:** The nickname for Azure App Service Authentication — a built-in, no-code layer that checks who is calling your app.
- **Identity provider:** A service (like Entra ID, Google, GitHub) that handles login and confirms who a user is.
- **Managed Identity:** An automatically-managed identity Azure gives to a resource (like a function app), so it can authenticate to other Azure services without stored credentials.
- **System-assigned identity:** A managed identity tied to one resource's lifecycle — created and deleted along with it.
- **User-assigned identity:** A managed identity that exists as its own resource, and can be attached to multiple apps.
- **Role assignment:** Giving an identity permission to do something specific (like "read secrets") on a resource.
- **`DefaultAzureCredential`:** A helper from the Azure Identity SDK that automatically finds the right way to authenticate, including using managed identity when running inside Azure.
- **Key Vault reference:** A special string in an app setting that points to a secret in Key Vault instead of containing the secret itself.
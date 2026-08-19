# Task 4: Network Security Patterns

This file covers three things:

1. **IP restrictions**controlling access by IP address.
2. **Service endpoints vs private endpoints**two different ways to secure traffic to Azure services, and when to use each.
3. A full **production security checklist** for Azure Functions.

---

## 1. IP restrictions and access rules

### What they are

IP restrictions (also called **access restrictions**) work like a basic firewall sitting in front of your function app. You build a list of rules that say "allow this IP range" or "deny this IP range," and the platform checks every incoming request against that list before it reaches your function.

### How they work

- Each rule has a **priority number**. Rules are checked in order, from lowest number to highest.
- Rules can be based on:
  - A specific **IP address or IP range** (using CIDR notation, e.g. `203.0.113.0/24`)
  - A **service tag** (a Microsoft-managed group of IP ranges, like "AzureFrontDoor" or "ApiManagement")
  - A **virtual network subnet**, using service endpoints (see the next section)
- As soon as you add **one rule**, an **implicit "deny all"** is added automatically at the end of the list. So if you only add one "allow" rule, everything else is blocked by defaultyou don't need to manually add a deny-all rule yourself.

### Example use case

Say your company office has a fixed public IP address, and you only want people calling from the office (or from your CI/CD pipeline) to reach your function. You'd add allow rules for those specific IP ranges. Once added, anyone outside those ranges is automatically blocked.

### Key points

- IP restrictions work on **every** Azure Functions hosting plan, including the basic Consumption plan. This makes it the easiest and cheapest inbound security option available.
- There's no extra cost to use them.
- They only control **inbound** trafficwho can call in. They don't affect outbound traffic at all.
- They only apply to traffic coming through the **public endpoint**. If your function app also has a private endpoint, traffic arriving through the private endpoint **skips IP restrictions completely**that traffic is controlled separately, using Network Security Groups (NSGs) on the subnet instead.
- Downside: maintaining these lists by hand can get messy over time, especially if you need to allow many different partners or offices, each with their own IP range.

### Simple analogy

Think of IP restrictions like a guest list at the front door. The doorman checks each visitor's ID (their IP address) against a list, and only lets in the people (or ranges of people) on the list. Anyone not on the list is turned away, once the list has at least one entry.

---

## 2. Service endpoints vs private endpoints

These two features sound similar, but they solve slightly different problems. Both let a resource inside your VNet talk to an Azure service more securelybut they work in very different ways.

### Service endpoints

A service endpoint is a way of telling Azure: "let this specific subnet reach this Azure service directly and securely, over the Azure backbone network instead of the public internet route."

- The Azure service (like Storage or a database) **still has a public IP address**.
- What changes is that the service can now say "only accept traffic from this specific subnet," instead of accepting traffic from anywhere.
- Traffic from that subnet takes a more direct, secure path over Azure's internal network, rather than going out over the regular internet.
- No private IP address is createdthe target resource is still technically reachable from the public internet unless you also lock it down separately.

**For Azure Functions specifically:** to use a service endpoint-secured resource, you first set up regional VNet integration (connecting your function app to a subnet), and then configure the destination service (like Storage) to only accept traffic from that subnet.

### Private endpoints

A private endpoint goes a step further. Instead of just restricting *which subnet* can call a service, it gives the service an actual **private IP address** inside your VNet.

- The resource (Storage, Cosmos DB, or even your function app itself) gets a network interface with a private IP, directly inside your VNet.
- Once set up (and public access disabled), the resource has **no public IP path at all**. It's genuinely brought inside your private network.
- This is a stronger form of isolation, because there's no public entry point left to secureit simply doesn't exist anymore.

### Comparison

| | Service endpoint | Private endpoint |
|---|---|---|
| Does the target keep a public IP? | Yes | No (once public access is disabled) |
| What it restricts | Which subnet can reach the service | Brings the service into your VNet with a private IP |
| Strength of isolation | Mediumreduces exposure, but public path can still exist | Strongpublic path is fully removed |
| Cost | Free | Has a cost per private endpoint |
| DNS changes needed | No | Yesneed private DNS zones so names resolve to the private IP |
| Good for | Simpler setups, lower-sensitivity data, quick wins | Production systems, sensitive data, "zero public exposure" requirements |

### When to use each

- Use **service endpoints** when you want a fast, free way to restrict a service to specific subnets, and full public isolation isn't a strict requirement.
- Use **private endpoints** when you need to fully remove public exposurethis is usually the expectation for production systems handling sensitive data, or when a security review requires "no public network access."

---

## 3. Production security checklist

Here is a checklist covering the main areas needed to secure an Azure Functions app for production.

### HTTPS enforcement

- [ ] **HTTPS Only** is turned on, so any plain HTTP request is automatically redirected to HTTPS.
- [ ] No app setting or client code relies on calling the function over plain `http://`.

### Minimum TLS version

- [ ] **Minimum TLS version** is set to **TLS 1.2** or higher (in Function app → Configuration → General settings).
- [ ] Any client code calling your function also supports at least TLS 1.2, so the connection doesn't fail after you raise the minimum.

### CORS configuration

- [ ] **CORS (Cross-Origin Resource Sharing)** allowed origins list only includes the specific domains that actually need to call your function from a browser.
- [ ] The wildcard `*` is **not** used as an allowed origin in production. Using `*` allows any website in the world to call your function from a user's browser, which is rarely what you want.
- [ ] Unused or old CORS entries are cleaned up regularly.

### Authentication

- [ ] **App Service Authentication (EasyAuth)** is turned on, with an appropriate identity provider (see Task 3).
- [ ] Function-level keys are not used as the *only* protection for anything beyond simple internal testingkeys can leak and are not tied to a specific identity.
- [ ] If your function is only ever called by other internal systems (not end users), you've considered whether authentication should be handled by Managed Identity instead of, or in addition to, EasyAuth.

### Managed identity

- [ ] Managed identity (system-assigned or user-assigned) is turned on for the function app.
- [ ] The function app uses its managed identitynot stored keys or connection stringsto access Key Vault, Storage, databases, and any other Azure resource it depends on.
- [ ] Each identity is only given the **minimum permissions it actually needs** (e.g. "Key Vault Secrets User," not full "Owner" access).

### Network isolation

- [ ] The function app's hosting plan supports networking features (Flex Consumption, Premium, or Dedicatednot basic Consumption, if isolation is required).
- [ ] Inbound: a **private endpoint** is used if the function should not be reachable from the public internet at all.
- [ ] Outbound: **regional VNet integration** is set up so the function can reach private resources (databases, internal APIs) instead of relying on public endpoints.
- [ ] Downstream resources (Storage, Cosmos DB, databases) have **public network access disabled**, and are only reachable through private endpoints.
- [ ] If full private endpoints aren't in place yet, **IP restrictions** are configured as a baseline, so the function isn't wide open to the entire internet.

### Secrets management

- [ ] No secrets (passwords, connection strings, API keys) are hardcoded directly in function code.
- [ ] Secrets are stored in **Key Vault**, not in plain app settings.
- [ ] App settings that need a secret value use a **Key Vault reference** (`@Microsoft.KeyVault(...)`), rather than pasting the raw value in.
- [ ] Access to Key Vault is granted through **role assignments tied to managed identity**, not shared passwords.
- [ ] Old or unused secrets are rotated or removed regularly.

---

## Glossary

- **Access restriction / IP restriction:** A priority-ordered allow/deny list based on IP address, service tag, or subnet, controlling who can reach your app.
- **Service tag:** A Microsoft-managed group of IP ranges (e.g. representing Azure Front Door) that you can allow or deny in one rule, instead of listing individual IPs.
- **Service endpoint:** A way to restrict an Azure service to only accept traffic from a specific VNet subnet, while the service still keeps a public IP.
- **Private endpoint:** A private IP address that brings an Azure service inside your VNet, removing its public IP entirely once public access is disabled.
- **CORS:** A browser security feature that controls which websites are allowed to call your API from client-side JavaScript.
- **TLS:** The encryption protocol used to secure HTTPS traffic; a higher minimum version means older, weaker encryption methods are rejected.
- **NSG (Network Security Group):** A set of firewall-like rules applied to a subnet or network interface, used to control traffic that bypasses IP restrictions (like traffic through a private endpoint).
# Task 2: VNet Integration & Private Endpoints

This file explains two important features for Azure Functions networking:

1. **Regional VNet integration**: lets your function go OUT and reach private resources.
2. **Private endpoints**: lets you lock your function so only people IN the VNet can reach it.

Then we look at how both work together in one architecture, with a diagram.

---

## 1. Regional VNet integration (outbound)

### The problem it solves

By default, your function app lives outside any VNet. It can only talk to things that have a public address on the internet. But many real systems don't want their database, storage account, or internal API exposed to the public internet at all they hide it inside a VNet.

So the question is: **how does a function app reach something that is hidden inside a private network?**

That's what regional VNet integration is for.

### How it works

1. You create a **subnet** inside your VNet, just for this purpose. This subnet is not used for anything else.
2. You connect your function app to that subnet. This is called "VNet integration."
3. Your function app itself still lives outside the VNet (it's a managed Azure service, not a virtual machine sitting inside your network). But once integrated, any outbound call from your function can now be routed through that subnet, into the VNet.
4. From there, it can reach anything sitting privately inside that VNet: like:
   - A Cosmos DB or SQL database with a private endpoint
   - A storage account with a private endpoint
   - An internal API running on a VM or in an App Service, hidden from the public internet

### Key points

- Think of it like giving your function a "door" into the private network. Without the door, it can only talk to the public internet. With the door, it can also reach private things.
- Your function app does not move into the VNet. It just gets a way to route its outbound traffic through it.
- DNS matters here. If you want your function to correctly find a private resource (like a database's private IP instead of its public IP), your VNet needs to be set up with the right private DNS zones. Otherwise your function might try to reach the public address instead of the private one.
- On the Flex Consumption plan, **all** outbound traffic automatically goes through the VNet once integration is set up: you don't need extra settings.
- On Premium and Dedicated plans, you can turn on a setting called **"Route All"** to force all outbound traffic through the VNet (otherwise only some traffic goes through it by default).

### analogy

Imagine your function app is an employee working from home (outside the office building). Normally they can only call people using public phone lines. VNet integration is like giving them a special extension that connects into the office's internal phone system: now they can also call people inside the building directly, privately, without going through the public phone network.

---

## 2. Private endpoints (inbound)

### The problem it solves

Even if your function is protected by IP restrictions or login checks, it still has a **public web address** by default. Anyone on the internet can technically try to reach that address (even if they get blocked). Some organizations want to remove that public address completely: no public entry point should exist at all.

That's what private endpoints solve, but for inbound traffic to your function app itself.

### How it works

1. You create another subnet inside your VNet (a different one from the outbound integration subnet).
2. You create a **private endpoint** for your function app in that subnet.
3. This gives your function app a **private IP address** from inside the VNet.
4. Once this is set up, your function app is **only reachable through that private IP**. The public internet can no longer reach it at all.
5. Now, only things that are inside the VNet, or connected to it (through VPN, peering, or ExpressRoute), can call your function.

### Key points, kept simple

- This removes public exposure completely. It's stronger than IP restrictions, because IP restrictions just filter public traffic: private endpoints remove the public entry point entirely.
- Only available on Flex Consumption, Premium, and Dedicated plans. Not available on the basic Consumption plan.
- You usually need a **separate subnet** from the one used for outbound VNet integration. On Flex Consumption especially, the same subnet cannot be used for both purposes.
- DNS matters here too: clients inside the VNet need to resolve your function app's name to its private IP, not its public one. This is normally done using Azure Private DNS zones linked to the VNet.

### Simple analogy

Going back to the office analogy: a private endpoint is like removing the public phone number for your office completely, and only giving out an internal extension. Now, nobody outside the building can call in at all: only people already inside the building (or connected through a private line) can reach you.

---

## 3. Putting both together: a fully private architecture

Here's what it looks like when you use both features at once, plus a private database:

- **Inbound side:** A private endpoint gives the function app a private IP. Only clients inside the VNet (or connected to it) can call the function. No public access exists.
- **Outbound side:** Regional VNet integration lets the function app route its outbound calls through a subnet into the VNet.
- **Data side:** A Cosmos DB or Storage account also has a private endpoint, so it too has no public access. The function app reaches it privately, through the VNet, using its outbound integration.

This means:
- Nobody from the public internet can call the function.
- The function cannot be used to reach the database publicly either: the whole path stays private, start to finish.
- Public internet exposure is eliminated on both ends.

### Architecture diagram

The diagram below shows the full picture:

- A client on a network connected to the VNet reaches the function app only through its **private endpoint**.
- The function app uses **regional VNet integration** through a separate **integration subnet** to route outbound traffic.
- That traffic reaches a **private endpoint subnet**, which connects privately to the **Cosmos DB / Storage account**, which has public access turned off.

(See the diagram shared alongside this file.)
![alt text](image.png)
---

##  glossary

- **VNet (Virtual Network):** Your own private network inside Azure.
- **Subnet:** A smaller section inside a VNet, used for a specific purpose.
- **Private endpoint:** A private IP address that lets a resource (function app, database, storage account) be reached only from inside a VNet, removing its public address.
- **Regional VNet integration:** A feature that lets an Azure service (like a function app) route its outbound traffic into a VNet, so it can reach private resources.
- **Private DNS zone:** A DNS setup inside Azure that makes sure names resolve to private IP addresses instead of public ones, for resources inside a VNet.
- **Route All:** A setting that forces all outbound traffic through the VNet instead of only some of it.

---

## comparison table

| Feature | What it controls | Direction | Removes public access? |
|---|---|---|---|
| Regional VNet integration | What the function can reach | Outbound | No (this is about outbound, not exposure) |
| Private endpoint (on function app) | Who can call the function | Inbound | Yes: public access is removed |
| Private endpoint (on database/storage) | Who can call the database/storage | Inbound (to that resource) | Yes: public access is removed |
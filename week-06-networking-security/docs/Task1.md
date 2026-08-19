# Task 1: Networking Architecture

This file explains inbound vs outbound networking for Azure Functions, and shows which features you get on each hosting plan.

---

## 1. What is inbound vs outbound networking?

Think of your function app like a house.

- **Inbound** = who is allowed to knock on your door and come in.
- **Outbound** = where you are allowed to go once you leave the house.

Azure Functions gives you separate controls for each direction. You can lock down who can call your function, and separately control what your function is allowed to talk to.

### Inbound networking (traffic coming IN)

Inbound controls decide **who can reach your function app**.

The main inbound tools are:

1. **IP restrictions (access rules)**
   - You make a list of IP addresses or IP ranges that are allowed or blocked.
   - The list is checked in order, top to bottom.
   - If you add even one rule, everything else is blocked by default (this is called "deny all" at the end of the list).
   - Works on every plan, even the basic Consumption plan.

2. **Private endpoints**
   - This gives your function app a private IP address inside your Virtual Network (VNet).
   - Once this is on, your function app has **no public address at all**. Only people/systems inside your VNet (or connected to it) can reach it.
   - This is the strongest way to lock down inbound access.
   - Not available on the basic Consumption plan.

3. **Authentication (EasyAuth)**
   - This checks *who* is calling, not just *where* they are calling from.
   - Covered more in Task 3.

** Summary:** IP restrictions control location. Private endpoints remove public access completely. Authentication controls identity.

### Outbound networking (traffic going OUT)

Outbound controls decide **what your function app is allowed to reach**.

The main outbound tool is:

1. **Regional VNet integration**
   - Your function app itself still lives outside the VNet (it's a managed Azure service).
   - But you connect it to a VNet through a dedicated subnet.
   - Once connected, your function can privately reach things sitting inside that VNet — like a database, an internal API, or a storage account that also uses a private endpoint.
   - Without this, your function can only reach things over the public internet.

2. **Outbound IP restrictions / Route All**
   - Normally, only some of your app's outbound traffic goes through the VNet.
   - Turning on "Route All" forces **all** outbound traffic through the VNet, so you can apply network rules (like NSGs — Network Security Groups) to control exactly what it's allowed to reach.
   - On the Flex Consumption plan, all traffic already goes through the VNet automatically, so you don't need to turn this on.

**Summary:** VNet integration lets your function go visit private resources instead of only the public internet. Route All makes sure it can't sneak out any other way.

### Putting it together

| Direction | Question it answers | Main tools |
|---|---|---|
| Inbound | Who can call my function? | IP restrictions, private endpoints, authentication |
| Outbound | What can my function reach? | Regional VNet integration, outbound IP restrictions (Route All) |

---

## 2. Networking feature matrix by hosting plan

Not every hosting plan supports every networking feature. This matters a lot when picking a plan, because if you need private networking and pick the wrong plan, you simply cannot get it — you'd have to migrate later.

| Feature | Consumption | Flex Consumption | Premium | Dedicated / ASE |
|---|---|---|---|---|
| Inbound IP restrictions | Yes | Yes | Yes | Yes |
| Inbound private endpoints | No | Yes | Yes | Yes |
| Outbound VNet integration | No | Yes (Regional) | Yes (Regional) | Yes (Regional and Gateway) |
| VNet triggers (non-HTTP, e.g. Service Bus/Event Hub inside a VNet) | No | Yes | Yes | Yes |
| Outbound IP restrictions (Route All) | No | Not needed — all traffic already goes through the VNet | Yes | Yes |

### What this table means in plain words

- **Consumption plan** = the cheapest, simplest plan. It has zero VNet features. No private endpoints, no VNet integration. It can only use IP restrictions. If your project needs any kind of private networking, this plan is not an option. Microsoft is also pushing people away from Consumption and toward Flex Consumption for new projects.

- **Flex Consumption plan** = the new recommended serverless plan. It gets almost everything: private endpoints for inbound, VNet integration for outbound, and VNet triggers. It's serverless (pay for what you use) but still gets real networking features. Good default choice for most new projects.

- **Premium plan** = similar networking features to Flex Consumption, but it's a different billing/scaling model (you pay for pre-warmed instances, not pure pay-per-use). Good when you need more predictable performance alongside networking.

- **Dedicated plan / ASE (App Service Environment)** = the most powerful option. It's the only plan that supports "Gateway" VNet integration, which is needed for more advanced networking setups like connecting through a VPN or ExpressRoute back to an on-premises network. This is usually for large enterprise setups.

### Quick decision guide

- Need no networking at all, just cheapest option → **Consumption**
- Need private networking, want serverless pricing → **Flex Consumption**
- Need private networking, want predictable/pre-warmed performance → **Premium**
- Need advanced VPN/ExpressRoute-level networking, enterprise scale → **Dedicated / ASE**

---

## Quick glossary

- **VNet (Virtual Network):** Your own private network inside Azure. Things inside it get private IP addresses and can talk to each other without touching the public internet.
- **Subnet:** A smaller section inside a VNet. VNets are usually split into subnets for different purposes (e.g. one subnet for outbound traffic, one for private endpoints).
- **Private endpoint:** A private IP address that connects a resource (like your function app, or a database) directly into a VNet, removing its public address.
- **NSG (Network Security Group):** A set of rules that control what traffic is allowed in/out of a subnet or resource — basically a firewall for your VNet.
- **Route All:** A setting that forces all outbound traffic from your app through the VNet, instead of only some of it.
### GCP Development Environment Setup Guide

# TODO: Add overview of how the dev environment works
## Overview

The dev environment is a VM instance running in GCP.

## Prerequisites
In order to run the application in a GCP dev environment, you will need to set up the following:

Under the Infrastructure repository in Github follow the setup guide to:
1. Create a GCP project
2. Create a service account
3. Assign roles to the service account
4. Update GCP bootstrap API's
5. Create a storage bucket for terrraform state
6. Update API keys in secret manager secrets
7. Build the infrastructure in GCP via terraform
8.

## Connecting to the VM Instance

We use IAP (Identity-Aware Proxy) and SSH config to connect to the application.

### Step 1: Generate SSH Configuration

Execute the following commands on your local machine terminal to connect to the VM instance:

## Note
Remember to replace all placeholder values (marked with `<>`) with your actual configuration details.

```bash
gcloud compute config-ssh
gcloud compute ssh --zone "<ZONE>" "<VM_NAME>" --tunnel-through-iap --project "<PROJECT_ID>" --dry-run
```

You will receive an SSH configuration output similar to:

```bash
/usr/bin/ssh -t -i /Users/<USERNAME>/.ssh/google_compute_engine -o CheckHostIP=no -o HashKnownHosts=no -o HostKeyAlias=compute.<INSTANCE_ID> -o IdentitiesOnly=yes -o StrictHostKeyChecking=yes -o UserKnownHostsFile=/Users/<USERNAME>/.ssh/google_compute_known_hosts -o "ProxyCommand /Users/<USERNAME>/.config/gcloud/virtenv/bin/python3 /Users/<USERNAME>/google-cloud-sdk/lib/gcloud.py compute start-iap-tunnel '<INSTANCE_NAME>' '%p' --listen-on-stdin --project=<PROJECT_ID> --zone=<ZONE> --verbosity=warning" -o ProxyUseFdpass=no <USERNAME>@compute.<INSTANCE_ID>
```

### Step 2: Update SSH Config File

Use the output to update your SSH config file (`~/.ssh/config`). The configuration should look like this:

```bash
Host vm_name
  HostName <VM_IP_ADDRESS>
  User <GCP_ID>  # This is typically separated by underscores (e.g., name_company_ai)
  IdentityFile /Users/username/.ssh/google_compute_engine
  ProxyCommand ~/google-cloud-sdk/bin/gcloud compute ssh --zone <ZONE> --project <GCP_PROJECT_ID> <VM_USER> --tunnel-through-iap --ssh-flag="-o ServerAliveInterval=30" --ssh-flag="-o ServerAliveCountMax=2" -- -W localhost:22
```

### Step 3: Connect to the VM

1. Use your IDE's "Connect to Host" option (if available)
2. Once connected, you can clone your desired repository
3. Follow standard GitHub SSH setup procedures for repository access

### Deployment and testing

To start, we begin with the assumption a Docker image has been built and pushed to the Artifact Registry in GCP and exists in the VM.

```bash
docker run -it --name workflow-instance -e GOOGLE_CLOUD_PROJECT=<project-id> -e ENVIRONMENT=<environment> -p 8000:8000 -v <local-path>:/app/<app-directory> <image-id>
```

To follow logs in real-time:

```bash
docker logs -f workflow-instance
```

# LXDRunner

Experimental daemon using [LXD](https://linuxcontainers.org/lxd/introduction/#LXD) to run ephemeral GitHub Actions [self-hosted runners](https://docs.github.com/en/actions/hosting-your-own-runners/about-self-hosted-runners).

Why use LXD and self-hosted runners ?

- Trivial to switch between containers and VMs..
- High density and fast startup when running containers.
- Create your own OS images and get a pristine environment every time.
- Automatic download and provisioning of the latest GHA runner client.
- Access custom hardware: Serial, USB, and PCI attached devices such as phones, GPUs, etc.
- Access sensitive resources that must be handled locally.

## How it works

LXDRunner runs an API endpoint waiting on webhook events from GitHub. No LXD instances are running until needed so resource usage is minimal. Every time Actions runs a workflow an event is sent for each job. LXDRunner reacts to each [workflow_job](https://docs.github.com/en/developers/webhooks-and-events/webhooks/webhook-events-and-payloads#workflow_job) event in queued status by:

- Mapping workflow labels to a specific LXD config ( image, profile, container type, etc ) 
- Launching a pristine LXD instance based on matching config.
- Provisioning instance with the latest GHA runner client to complete the job.
- GHA runner automatically shuts down and deregisters when job is complete.
- Destroying the LXD instance, just like GitHub hosted runners.

### Periodic Events

- Every 24 hours: Checks for new version of actions runner
- Every 12 hours: Cleanup any offline runner registrations

### Scaling
KISS, based only on incoming webhooks from GitHub.  For each event 1 runner is launched on the fly.

Instances are ephemeral, automatically deregistered and shutdown on completion.

More complex scaling could be achieved using the GitHub API at the expense of job latency, higher API and resource usage.

After release of the ephemeral feature this is now the recommended scaling strategy. https://docs.github.com/en/actions/hosting-your-own-runners/autoscaling-with-self-hosted-runners

### Limitations:

- Workflow runs fail immediately if no runners with matching labels are registered. Remedy this by manually registering a runner with matching labels that is permanently left in the offline state. In this case runs will be queued.
- Runner provisioning is based on bash script. Probably doesn't work on anything other than Ubuntu/Debian based distros without modification.


## Setup:

LXDRunner works both with repo and organization runners. The service must be accessible over the internet in order to receive webhooks from GitHub. The API endpoint is protected by a secret and TLS. If you want to restrict access by IP you can retrieve a list of GitHub IPs using the [Meta API](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/about-githubs-ip-addresses)


### GitHub Setup

- Setup a PAT with access to the repos and orgs you want serviced. Copy this down you will need it.

  https://docs.github.com/en/github/authenticating-to-github/creating-a-personal-access-token

  Enable the following scopes:
  - repo
  - workflow
  - admin:org
  - admin:org_hook
  - admin:repo_hook

Repeat these steps once for each organization and/or user repo you want serviced.

- Setup a webhook pointing to the LXDRunner host. If servicing multiple orgs or user repos make sure they all use the same webhook secret

  https://docs.github.com/en/developers/webhooks-and-events/creating-webhooks#setting-up-a-webhook

  - **Payload URL**: https://your-hostname:your-port/hooks/lxdrunner
  - **Content type**: application/json
  - **Secret**: Create a strong secret and copy it down
  - Select **Let me select individual events** and choose:
     - Workflow runs
     - Workflow jobs
  - **Active**: Ensure its checked.

- Manually register one GHA runner for each set of labels that is always offline. This prevents workflow runs from failing immediately when no matching runners are registered. This placeholder runner should NOT have the prefix "lxdrunner"
  
  https://docs.github.com/en/actions/hosting-your-own-runners/adding-self-hosted-runners

### LXDRunner Manual Install

Requirements: Python 3.8 with pip

- Clone this repo. Setup python virtual env if needed.
- Install requirements: `pip install -r requirements.txt`
- Create configuration as detailed below.
- Run LXDRunner from directory : `python -m lxdrunner`
- You can install `lxdrunner` to default locations with: `pip install ./`

### LXDRunner Configuration

- Copy config.yml.example to config.yml
- Edit config.yml:
    - Set your GitHub PAT
    - Set your webhook secret
    - Setup remotes
    - Setup the runnermap. This section maps a set of actions workflow labels to specific LXD settings
      such as name, image source, profiles, container type, etc.
- Run some github actions workflows to test.

# Development

## TODO:

- Investigate race condition between cloudinit and setup script adduser
- Fix TLS verification
- Dedup queue
- Not sure pyLXD is thread-safe, investigate.
- Explore alt provisioning methods ( prebaked images, disks mounts, etc )
- Auto configuration of webhooks through API
- Auto registration of offline placeholder runners
- More logging
- More tests

## DONE:
- Limit workers per label-set
- Remote LXD server and image support
- Add support for multiple label maps
- Make changes for ephemeral fix. actions/runner issue 510
- During startup and periodically:
  - query GH for queued runs that might have been missed or lost.
  - cleanup offline runner registrations and expired LXD workers


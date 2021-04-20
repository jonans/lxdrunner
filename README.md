# LXDRunner

Experimental daemon using LXD to run ephemeral GitHub Actions self-hosted runners.

- Use containers or VMs via LXD
- Automatically downloads and provisions latest GHA runner client.
- Service repos under users and organizations.

## Setup:

### GitHub Setup

LXDRunner works both with user repos and organizations.

- Setup a PAT with access to the repos and orgs you want serviced

  https://docs.github.com/en/github/authenticating-to-github/creating-a-personal-access-token

  Enable the following scopes:
  - repo
  - workflow
  - admin:org
  - admin:org_hook
  - admin:repo_hook

These steps need to be completed once for each organization and/or user repo you want serviced.

- Setup webhooks pointing to the LXDRunner host. If servicing multiple orgs or user repos make sure they all use the same webhook secret

  https://docs.github.com/en/developers/webhooks-and-events/creating-webhooks#setting-up-a-webhook

  - Webhook URL should use the location "/hooks/lxdrunner"

    https://<your-host>:<port>/hooks/lxdrunner

  Select **Let me select individual events** and choose:
  - Check runs
  - Check suites

- Manually register one GHA runner with needed labels that is always offline. This prevents workflow runs from failing immediately when no matching runners are registered. This placeholder runner should NOT have the prefix "lxdrunner"

### LXDRunner Setup

Requirements: Python 3.8 with pip

- Clone this repo. Setup virtual env if needed.
- Install requirements: `pip install -r requirements.txt`
- Copy config.yml.example to config.yml
- Edit config.yml adding GitHub tokens from setup above, adjust other settings as needed.
- Copy needed LXD images locally, remotes are not yet supported.
- Start LXDRunner server : `python -m lxdrunner`
- Run some github actions workflows to test.
- You can install app as `lxdrunner` to run outside folder with: `pip install ./`

## How it works

LXDRunner runs an API endpoint waiting on webhook events from GitHub. No LXD instances are running until needed so resource usage is minimal. Every time Actions runs a workflow an event is sent for each job. LXDRunner reacts to each check_run event in queued status by:

- Launching a pristine LXD instance based on your config (image, profiles, type, etc)
- Provisioning instance with the latest GHA runner to complete the job.
- Shutting down and deregistering the runner client when complete.
- Destroying the LXD instance, just like GitHub hosted runners.

### Scaling
KISS, based only on incoming webhooks from GitHub.  For each event 1 runner is launched on the fly.

Instances are ephemeral, automatically deregistered and shutdown on completion.

More complex scaling could be achieved using the GitHub API at the expense of job latency, higher API and resource usage.

## Limitations:

The goal is to map workflow runner labels to different LXD configurations. Currently only a single active configuration is supported. Its not clear how to associate check_runs to labels using the GitHub API.

- Workflow runs fail immediately if no runners with matching labels are registered. Remedy this by manually registering a runner with matching labels that is permanently left in the offline state.
- Only local access via unix socket. Must run on same server as LXD.
- Only local images supported. Copy your remote images with auto update enabled.
- Runner provisioning is based on bash script. Probably doesn't work on anything other than Ubuntu/Debian based distros without modification.

## TODO:

- Associate check_runs to workflow runner labels for multiple configs
- Howto determine self-hosted vs github hosted runner event.
- Investigate race condition between cloudinit and setupscript adduser
- Don't think pyLXD is thread-safe, find alternative.
- Remote image and LXD server support
- Explore alt provisioning methods ( prebaked images, disks mounts, etc )
- During startup and periodically:
  - **DONE** query GH for queued runs that might have been missed or lost.
  - **DONE** cleanup offline runner registrations and expired LXD workers
- Auto configuration of webhooks through API
- Auto registration of offline placeholder runners
- More logging
- More tests

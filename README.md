# Bad Stats

A web app for exploring spotify api data based on flask and matplotlib.

## Development

In order to setup the development environment, certain environment variables need to be set:

- FLASK_APP=badstats
- FLASK_ENV=development
- FLASK_SECRET=dev
- CLIENTID=[the badstats clientid from spotify]
- CLIENTSECRET=[the badstats clientsecret from spotify]

This can be accomplished by creating a .env file and doing `source .env`  

The development environment uses a python venv. If there isn't a virtual environment already setup, go 
to the root of the repository and run:

    python -m venv venv

The project requires python 3, you may need to run `python3 -m venv venv` if you have python 2 installed
as well.

For local development, install the dev dependencies: `pip install -r requirements-dev.txt`. If you add or remove a package
be sure to do it from both requirements files as necessary.

Activate the virtual environment by running `source ./venv/bin/activate`. On Windows its a little different: 
`source ./venv/Scripts/activate` 

## Testing

Tests should be run with the venv activated. From the project root run `pytest`.

## Build

BadStats is packaged in a container image and run in a k8s cluster. The container is build automatically using GitHub actions
and hosted on the GitHub container registry. The build process will generate images for amd64 and arm64. 

To perform the container build manually, first build a custom buildx builder 
(if you don't already have one):

    docker buildx create --name mybuilder --use

Then from the project root, build the container as follows:

    docker buildx build --platform linux/amd64,linux/arm64 -t kclapper/badstats:latest -t kclapper/badstats:x.x.x --push .

`--push` can be omitted if not sending to a container registry.

### Windows Build

On Windows, custom buildx builder's don't work properly. Instead, use the default and
only build for one platform at a time.

## Deployment

BadStats is meant to be deployed on a k8s cluster. Configuration files can be 
found in the k8s-manifests foulder.
Since the database doesn't need to store any long lived data, there isn't much
concern wiping and recreating the persistent volume (other than possibly creating a bunch of useless files/folders).

## Notes

- If the BadStats container throws errors when it's run, make sure dependencies were updated in requirements.txt
- The container will install the latest verions of the dependencies. 
If there were breaking changes and the local dev environment isn't up to date, it may cause errors.

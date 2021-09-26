# Bad Stats Spotify Interrogator

A web app for exploring spotify api data. Primarily for seeing album distribution graphs. 
Based on flask and matplotlib.

## Development

In order to setup the development environment, certain environment variables need to be set:

- FLASK_APP=badstats
- FLASK_ENV=development
- FLASK_SECRET=dev
- CLIENTID=[the badstats clientid from spotify]
- CLIENTSECRET=[the badstats clientsecret from spotify]

I've been setting this up in a .env file and doing `source .env`  

The development environment uses a python venv. If there isn't a virtual environment already setup, go 
to the root of the repository and run:

    python -m venv venv

The project requires python 3, you may need to run `python3 -m venv venv` instead if you have python 2 installed
as well.  

Activate the virtual environment by running `source ./venv/bin/activate`. On Windows its a little different: 
`source ./venv/Scripts/activate` 

On my mac, I also wrote a small start.sh file which gets the environment variables from the .env file, activates the venv,
and starts the development server. `./start.sh` or `source start.sh`

## Testing

Tests aren't written yet. TBD.

## Build

Badstats will run on a K8s cluster so the build process is all about creating a container image and pushing it to docker hub.

First, if you've installed or removed any pip dependencies, you'll want to update the requirements.txt file because this is 
what docker will use to build the container image (As a side note, it's worth investigating updating the requirements file by hand
instead of using the following command):

    pip freeze >> requirements.txt

Since the Ki-Kluster runs arm64, the build process will generate images for amd64 and arm64. If you don't have a custom buildx
builder yet you'll need one:

    docker buildx create --name mybuilder --use

Then the build process is as follows:

    cd frontend
    docker buildx build --platform linux/amd64,linux/arm64 -t kpuc1997/badstats:latest -t kpuc1997/badstats:x.x.x .

## Deployment

All deployment is handled by badstats.yml. Since the database doesn't need to store any long lived data, there isn't much
concern wiping and recreating the persistent volume (other than possibly creating a bunch of useless files/folders).
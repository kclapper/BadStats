FROM python:3

WORKDIR /usr/src/app

COPY badstats/ badstats/
COPY manifest.in .
COPY setup.py .
COPY requirements.txt .

RUN pip install -r requirements.txt

RUN pip install waitress

# Expects three environment variables:
# CLIENTID - for Spotify
# CLIENTSECRET - for Spotify
# FLASK_SECRET - Random string for production mode
ENV FLASK_ENV=production

EXPOSE 8080
VOLUME /user/src/app/instance


CMD ["waitress-serve", "--call", "badstats:create_app"]
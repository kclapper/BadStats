FROM python:3

WORKDIR /usr/src/app

COPY badstats/ badstats/
COPY requirements.txt .

RUN pip install -r requirements.txt

# Expects three environment variables:
# CLIENTID - for Spotify
# CLIENTSECRET - for Spotify
# FLASK_SECRET - Random string for production mode
ENV FLASK_ENV=production

EXPOSE 8080
VOLUME /user/src/app/instance


CMD ["waitress-serve", "--call", "badstats:create_app"]